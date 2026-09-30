from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import get_language
from rest_framework import serializers

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
    # Return a relative URL (e.g. /media/covers/x.jpg) so the same value works
    # behind the Vite dev proxy and the production nginx reverse proxy without
    # depending on the request's host/port.
    cover = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = ["id", "title", "author", "description", "price", "stock", "cover", "in_stock"]

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


class CartItemSerializer(serializers.ModelSerializer):
    book = BookSerializer(read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = CartItem
        fields = ["id", "book", "quantity", "subtotal"]


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total_quantity = serializers.IntegerField(read_only=True)

    class Meta:
        model = Cart
        fields = ["id", "items", "total_price", "total_quantity"]


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
        fields = ["id", "status", "total", "item_count", "created_at", "items"]
