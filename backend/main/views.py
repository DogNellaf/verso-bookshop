from django.db import connection, transaction
from django.db.models import Prefetch, prefetch_related_objects
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import filters, generics, permissions, serializers, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from main.filters import BookFilter
from main.models import Book, Cart, CartItem, Order, OrderItem
from main.serializers import (
    AddCartItemSerializer,
    BookSerializer,
    CartSerializer,
    OrderSerializer,
    RegisterSerializer,
    UpdateCartItemSerializer,
    UserSerializer,
)


def tokens_for(user):
    refresh = RefreshToken.for_user(user)
    return {"refresh": str(refresh), "access": str(refresh.access_token)}


# ---- Books ----


class BookViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = BookFilter
    search_fields = ["title", "author"]
    ordering_fields = ["title", "author", "price"]


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


# ---- Auth ----


class ThrottledTokenObtainPairView(TokenObtainPairView):
    throttle_scope = "auth"


class ThrottledTokenRefreshView(TokenRefreshView):
    throttle_scope = "auth"


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = "auth"

    @extend_schema(
        request=RegisterSerializer,
        responses={
            201: inline_serializer(
                "RegisterResponse",
                {
                    "user": UserSerializer(),
                    "access": serializers.CharField(),
                    "refresh": serializers.CharField(),
                },
            )
        },
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {"user": UserSerializer(user).data, **tokens_for(user)},
            status=status.HTTP_201_CREATED,
        )


class CurrentUserView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses=UserSerializer)
    def get(self, request):
        return Response(UserSerializer(request.user).data)


# ---- Cart ----


def get_cart(user):
    cart, _ = Cart.objects.get_or_create(buyer=user)
    return cart


def cart_payload(cart):
    """Serialize a cart with its items and books fetched in a single query."""
    prefetch_related_objects(
        [cart], Prefetch("items", queryset=CartItem.objects.select_related("book"))
    )
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
            raise ValidationError({"quantity": f"Only {book.stock} in stock for '{book.title}'."})
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
            raise ValidationError(
                {"quantity": f"Only {item.book.stock} in stock for '{item.book.title}'."}
            )
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


class CheckoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=None, responses={201: OrderSerializer})
    def post(self, request):
        with transaction.atomic():
            cart = get_cart(request.user)
            items = list(cart.items.select_related("book"))
            if not items:
                raise ValidationError({"detail": "Your cart is empty."})

            # Lock the affected book rows to prevent overselling under
            # concurrent checkouts.
            book_ids = [item.book_id for item in items]
            locked = Book.objects.select_for_update().filter(id__in=book_ids)
            stock = {book.id: book for book in locked}

            errors = []
            for item in items:
                book = stock[item.book_id]
                if item.quantity > book.stock:
                    errors.append(f"'{book.title}': only {book.stock} left.")
            if errors:
                raise ValidationError({"detail": "Not enough stock.", "items": errors})

            order = Order.objects.create(buyer=request.user, status=Order.Status.PENDING)
            order_items = []
            for item in items:
                book = stock[item.book_id]
                order_items.append(
                    OrderItem(
                        order=order,
                        book=book,
                        title=book.title,
                        unit_price=book.price,
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
    return Order.objects.filter(buyer=user).prefetch_related("items__book")


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
    """Cancel a pending order and return its items to stock."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=None, responses=OrderSerializer)
    def post(self, request, pk):
        with transaction.atomic():
            order = get_object_or_404(Order.objects.select_for_update(), pk=pk, buyer=request.user)
            if order.status != Order.Status.PENDING:
                raise ValidationError(
                    {"detail": f"Only pending orders can be cancelled (status: {order.status})."}
                )

            items = list(order.items.all())
            book_ids = [item.book_id for item in items if item.book_id]
            books = {
                book.id: book for book in Book.objects.select_for_update().filter(id__in=book_ids)
            }
            for item in items:
                book = books.get(item.book_id)
                if book is not None:
                    book.stock += item.quantity
                    book.save(update_fields=["stock"])

            order.status = Order.Status.CANCELLED
            order.save(update_fields=["status"])

        return Response(OrderSerializer(user_orders(request.user).get(pk=order.pk)).data)
