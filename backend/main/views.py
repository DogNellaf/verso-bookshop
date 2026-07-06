from django.db import transaction
from rest_framework import filters, generics, permissions, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

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
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "author"]
    ordering_fields = ["title", "price"]


# ---- Auth ----

class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

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

    def get(self, request):
        return Response(UserSerializer(request.user).data)


# ---- Cart ----

def get_cart(user):
    cart, _ = Cart.objects.get_or_create(buyer=user)
    return cart


class CartView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        cart = get_cart(request.user)
        return Response(CartSerializer(cart).data)


class CartItemsView(APIView):
    """Add an item to the cart (or bump its quantity if already present)."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = AddCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        book = serializer.validated_data["book"]
        quantity = serializer.validated_data["quantity"]

        cart = get_cart(request.user)
        item, created = CartItem.objects.get_or_create(cart=cart, book=book)
        new_quantity = quantity if created else item.quantity + quantity
        if new_quantity > book.stock:
            raise ValidationError(
                {"quantity": f"Only {book.stock} in stock for '{book.title}'."}
            )
        item.quantity = new_quantity
        item.save()
        return Response(CartSerializer(cart).data, status=status.HTTP_201_CREATED)


class CartItemDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_item(self, request, pk):
        cart = get_cart(request.user)
        try:
            return cart.items.get(pk=pk)
        except CartItem.DoesNotExist:
            return None

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
        return Response(CartSerializer(item.cart).data)

    def delete(self, request, pk):
        item = self.get_item(request, pk)
        if item is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        cart = item.cart
        item.delete()
        return Response(CartSerializer(cart).data)


class CheckoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

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

        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


# ---- Orders ----

class OrderListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = OrderSerializer
    pagination_class = None

    def get_queryset(self):
        return (
            Order.objects.filter(buyer=self.request.user)
            .prefetch_related("items__book")
        )


class OrderDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = OrderSerializer

    def get_queryset(self):
        return (
            Order.objects.filter(buyer=self.request.user)
            .prefetch_related("items__book")
        )
