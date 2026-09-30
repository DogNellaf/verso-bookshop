from django.db import connection, transaction
from django.db.models import OuterRef, Prefetch, Subquery, prefetch_related_objects
from django.db.models.functions import Coalesce
from django.utils.translation import gettext as _
from django.utils.translation import ngettext
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import filters, generics, permissions, serializers, status, viewsets
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from main import checkout, currency
from main.filters import BookFilter
from main.models import Book, BookTranslation, Cart, CartItem, Order, OrderItem
from main.orders import CannotCancel, cancel_order
from main.search import BookSearchFilter
from main.serializers import (
    AddCartItemSerializer,
    AddressSerializer,
    BookSerializer,
    CartSerializer,
    CheckoutSerializer,
    OrderSerializer,
    QuoteRequestSerializer,
    QuoteSerializer,
    UpdateCartItemSerializer,
    current_language,
)


def stock_message(book):
    if book.stock == 0:
        return _("“%(title)s” is out of stock.") % {"title": book.title}
    return ngettext(
        "Only %(count)d copy of “%(title)s” is in stock.",
        "Only %(count)d copies of “%(title)s” are in stock.",
        book.stock,
    ) % {"count": book.stock, "title": book.title}


# ---- Books ----


class LocalizedOrderingFilter(filters.OrderingFilter):
    """Sort by title/author in the active language rather than the English original."""

    localized = {"title": "title_i18n", "author": "author_i18n"}

    def get_ordering(self, request, queryset, view):
        ordering = super().get_ordering(request, queryset, view) or []
        localized = []
        for field in ordering:
            name = field.lstrip("-")
            localized.append(field.replace(name, self.localized.get(name, name)))
        return localized


class BookViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BookSerializer
    # The search filter runs last so it can order by relevance when no
    # explicit ordering was asked for.
    filter_backends = [DjangoFilterBackend, LocalizedOrderingFilter, BookSearchFilter]
    filterset_class = BookFilter
    ordering_fields = ["title", "author", "price"]
    ordering = ["title"]

    def get_queryset(self):
        translated = BookTranslation.objects.filter(
            book=OuterRef("pk"), language=current_language()
        )
        return (
            Book.objects.prefetch_related("translations")
            .annotate(
                title_i18n=Coalesce(Subquery(translated.values("title")[:1]), "title"),
                author_i18n=Coalesce(Subquery(translated.values("author")[:1]), "author"),
            )
            .order_by("title_i18n")
        )


# ---- Currencies ----


class CurrencyListView(APIView):
    """Currencies the storefront can show prices in."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        responses=inline_serializer(
            "CurrencyInfo",
            {"code": serializers.CharField(), "decimals": serializers.IntegerField()},
            many=True,
        )
    )
    def get(self, request):
        table = currency.currencies()
        return Response(
            [{"code": code, "decimals": table[code].decimals} for code in sorted(table)]
        )


# ---- Health ----


class HealthView(APIView):
    """Liveness/readiness probe used by docker-compose."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = []

    @extend_schema(
        responses=inline_serializer("Health", {"status": serializers.CharField()}),
    )
    def get(self, request):
        connection.ensure_connection()
        return Response({"status": "ok"})


# ---- Cart ----


def get_cart(user):
    cart, _ = Cart.objects.get_or_create(buyer=user)
    return cart


def cart_payload(cart):
    """Serialize a cart with its items and books fetched in a single query."""
    items = CartItem.objects.select_related("book").prefetch_related("book__translations")
    prefetch_related_objects([cart], Prefetch("items", queryset=items))
    return CartSerializer(cart).data


class CartView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses=CartSerializer)
    def get(self, request):
        return Response(cart_payload(get_cart(request.user)))


class CartItemsView(APIView):
    """Add an item to the cart (or bump its quantity if already present)."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=AddCartItemSerializer, responses={201: CartSerializer})
    def post(self, request):
        serializer = AddCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        book = serializer.validated_data["book"]
        quantity = serializer.validated_data["quantity"]

        cart = get_cart(request.user)
        item, created = CartItem.objects.get_or_create(cart=cart, book=book)
        new_quantity = quantity if created else item.quantity + quantity
        if new_quantity > book.stock:
            raise ValidationError({"quantity": stock_message(book)})
        item.quantity = new_quantity
        item.save()
        return Response(cart_payload(cart), status=status.HTTP_201_CREATED)


class CartItemDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_item(self, request, pk):
        cart = get_cart(request.user)
        try:
            return cart.items.get(pk=pk)
        except CartItem.DoesNotExist:
            return None

    @extend_schema(request=UpdateCartItemSerializer, responses=CartSerializer)
    def patch(self, request, pk):
        item = self.get_item(request, pk)
        if item is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = UpdateCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quantity = serializer.validated_data["quantity"]
        if quantity > item.book.stock:
            raise ValidationError({"quantity": stock_message(item.book)})
        item.quantity = quantity
        item.save()
        return Response(cart_payload(item.cart))

    @extend_schema(responses=CartSerializer)
    def delete(self, request, pk):
        item = self.get_item(request, pk)
        if item is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        cart = item.cart
        item.delete()
        return Response(cart_payload(cart))


ADDRESS_FIELDS = (
    "full_name",
    "address_line1",
    "address_line2",
    "city",
    "postal_code",
    "country",
    "phone",
)


class CheckoutInfoView(APIView):
    """What the checkout form needs, the countries served and the last address."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        responses=inline_serializer(
            "CheckoutInfo",
            {
                "countries": serializers.ListField(child=serializers.CharField(), allow_null=True),
                "saved_address": AddressSerializer(allow_null=True),
            },
        )
    )
    def get(self, request):
        last = Order.objects.filter(buyer=request.user).exclude(country="").first()
        saved = {f: getattr(last, f) for f in ADDRESS_FIELDS} if last else None
        return Response({"countries": checkout.shipping_countries(), "saved_address": saved})


class QuoteView(APIView):
    """Shipping options, tax and total of the cart for a destination."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=QuoteRequestSerializer, responses=QuoteSerializer)
    def post(self, request):
        data = QuoteRequestSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        items = cart_items(request.user)
        if not items:
            raise ValidationError({"detail": _("Your cart is empty.")})
        result = checkout.quote(
            [(item.book, item.quantity) for item in items],
            data.validated_data["country"],
            data.validated_data.get("shipping_method") or None,
            current_language(),
        )
        return Response(QuoteSerializer(result).data)


def cart_items(user):
    return list(CartItem.objects.filter(cart__buyer=user).select_related("book"))


class CheckoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=CheckoutSerializer, responses={201: OrderSerializer})
    def post(self, request):
        form = CheckoutSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        data = form.validated_data

        with transaction.atomic():
            cart = get_cart(request.user)
            items = list(cart.items.select_related("book"))
            if not items:
                raise ValidationError({"detail": _("Your cart is empty.")})

            # Lock the affected book rows to prevent overselling under
            # concurrent checkouts.
            book_ids = [item.book_id for item in items]
            locked = Book.objects.select_for_update().filter(id__in=book_ids)
            stock = {book.id: book for book in locked}

            errors = []
            for item in items:
                book = stock[item.book_id]
                if item.quantity > book.stock:
                    errors.append(stock_message(book))
            if errors:
                raise ValidationError({"detail": _("Not enough stock."), "items": errors})

            priced = checkout.quote(
                [(stock[item.book_id], item.quantity) for item in items],
                data["country"],
                data["shipping_method"],
                current_language(),
            )
            order = Order.objects.create(
                buyer=request.user,
                status=Order.Status.PENDING,
                currency=priced.currency,
                shipping_cost=priced.shipping,
                tax_rate=priced.tax_rate,
                tax_amount=priced.tax,
                shipping_method=priced.method.name,
                delivery_min_days=priced.method.min_days,
                delivery_max_days=priced.method.max_days,
                **{f: data.get(f, "") for f in ADDRESS_FIELDS},
            )
            order_items = []
            for item in items:
                book = stock[item.book_id]
                order_items.append(
                    OrderItem(
                        order=order,
                        book=book,
                        title=book.title,
                        unit_price=currency.convert(book.price, priced.currency),
                        quantity=item.quantity,
                    )
                )
                book.stock -= item.quantity
                book.save(update_fields=["stock"])
            OrderItem.objects.bulk_create(order_items)
            order.recalculate_total()

            cart.items.all().delete()

        order = user_orders(request.user).get(pk=order.pk)
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


# ---- Orders ----


def user_orders(user):
    if not user.is_authenticated:  # schema generation calls this anonymously
        return Order.objects.none()
    return Order.objects.filter(buyer=user).prefetch_related(
        "items__book__translations", "payments__refunds"
    )


class OrderListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = OrderSerializer
    pagination_class = None

    def get_queryset(self):
        return user_orders(self.request.user)


class OrderDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = OrderSerializer

    def get_queryset(self):
        return user_orders(self.request.user)


class OrderCancelView(APIView):
    """Cancel a pending or paid order, restock the books and refund the money."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=None, responses=OrderSerializer)
    def post(self, request, pk):
        try:
            cancel_order(pk, buyer=request.user)
        except Order.DoesNotExist as exc:
            raise NotFound() from exc
        except CannotCancel as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        return Response(OrderSerializer(user_orders(request.user).get(pk=pk)).data)
