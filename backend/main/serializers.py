from decimal import Decimal

from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import get_language
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from main import currency
from main.models import Book, Cart, CartItem, Order, OrderItem

TRANSLATED_FIELDS = ("title", "author", "description")


def current_language():
    return (get_language() or "en").split("-")[0]


def translation_for(book, language=None):
    """The book's translation for the active language, or None for English.

    Iterates ``book.translations.all()`` so callers should prefetch it.
    """
    language = language or current_language()
    if language == "en":
        return None
    return next((t for t in book.translations.all() if t.language == language), None)


class BookSerializer(serializers.ModelSerializer):
    in_stock = serializers.BooleanField(read_only=True)
    # Price in the requested currency (see main.currency).
    price = serializers.SerializerMethodField()
    currency = serializers.SerializerMethodField()
    # Return a relative URL (e.g. /media/covers/x.jpg) so the same value works
    # behind the Vite dev proxy and the production nginx reverse proxy without
    # depending on the request's host/port.
    cover = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = [
            "id",
            "title",
            "author",
            "description",
            "price",
            "currency",
            "stock",
            "cover",
            "in_stock",
        ]

    @extend_schema_field(serializers.DecimalField(max_digits=12, decimal_places=2))
    def get_price(self, obj):
        return str(currency.convert(obj.price, currency.effective_currency()))

    def get_currency(self, obj) -> str:
        return currency.effective_currency()

    def get_cover(self, obj) -> str:
        return obj.cover.url if obj.cover else ""

    def to_representation(self, instance):
        data = super().to_representation(instance)
        translation = translation_for(instance)
        if translation is not None:
            for field in TRANSLATED_FIELDS:
                data[field] = getattr(translation, field)
        return data


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["username", "email", "password"]

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=validated_data["password"],
        )


# ---- Cart ----


def converted_unit_price(book):
    return currency.convert(book.price, currency.effective_currency())


class CartItemSerializer(serializers.ModelSerializer):
    book = BookSerializer(read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ["id", "book", "quantity", "subtotal"]

    @extend_schema_field(serializers.DecimalField(max_digits=12, decimal_places=2))
    def get_subtotal(self, obj):
        return str(converted_unit_price(obj.book) * obj.quantity)


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()
    total_quantity = serializers.IntegerField(read_only=True)
    currency = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ["id", "items", "total_price", "total_quantity", "currency"]

    @extend_schema_field(serializers.DecimalField(max_digits=12, decimal_places=2))
    def get_total_price(self, obj):
        # Sum rounded line totals so the total matches what the lines show.
        total = sum(
            (converted_unit_price(item.book) * item.quantity for item in obj.items.all()),
            Decimal("0.00"),
        )
        return str(total)

    def get_currency(self, obj) -> str:
        return currency.effective_currency()


class AddCartItemSerializer(serializers.Serializer):
    book = serializers.PrimaryKeyRelatedField(queryset=Book.objects.all())
    quantity = serializers.IntegerField(min_value=1, default=1)


class UpdateCartItemSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)


# ---- Orders ----


class OrderItemSerializer(serializers.ModelSerializer):
    book = BookSerializer(read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "book", "title", "unit_price", "quantity", "subtotal"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    item_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Order
        fields = ["id", "status", "total", "currency", "item_count", "created_at", "items"]
