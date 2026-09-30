from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import get_language
from django.utils.translation import gettext as _
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from main import currency
from main.models import Book, Cart, CartItem, Order, OrderItem, Payment

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
    return next(
        (t for t in book.translations.all() if t.language == language and is_published(t)),
        None,
    )


def is_published(translation):
    return translation.reviewed or settings.PUBLISH_UNREVIEWED_TRANSLATIONS


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


class AddressSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150)
    address_line1 = serializers.CharField(max_length=200)
    address_line2 = serializers.CharField(max_length=200, required=False, allow_blank=True)
    city = serializers.CharField(max_length=100)
    postal_code = serializers.CharField(max_length=20)
    country = serializers.CharField(max_length=2)
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True)

    def validate_country(self, value):
        from main.countries import COUNTRY_CODES

        value = value.upper()
        if value not in COUNTRY_CODES:
            raise serializers.ValidationError(_("Choose a country from the list."))
        return value


class QuoteRequestSerializer(serializers.Serializer):
    country = serializers.CharField(max_length=2)
    shipping_method = serializers.CharField(required=False, allow_blank=True)


class CheckoutSerializer(AddressSerializer):
    shipping_method = serializers.CharField()


class MethodQuoteSerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()
    price = serializers.DecimalField(max_digits=12, decimal_places=2)
    free = serializers.BooleanField()
    min_days = serializers.IntegerField()
    max_days = serializers.IntegerField()


class QuoteSerializer(serializers.Serializer):
    currency = serializers.CharField()
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2)
    shipping = serializers.DecimalField(max_digits=12, decimal_places=2)
    tax_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    tax_name = serializers.CharField()
    tax = serializers.DecimalField(max_digits=12, decimal_places=2)
    total = serializers.DecimalField(max_digits=12, decimal_places=2)
    method = MethodQuoteSerializer()
    methods = MethodQuoteSerializer(many=True)


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


CAPTURED_OR_REFUNDED = (
    Payment.Status.SUCCEEDED,
    Payment.Status.PARTIALLY_REFUNDED,
    Payment.Status.REFUNDED,
)


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    item_count = serializers.IntegerField(read_only=True)
    refund = serializers.SerializerMethodField(
        help_text="refunded, partial, pending (still being sent) or null"
    )
    refunded_amount = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "status",
            "subtotal",
            "shipping_cost",
            "tax_rate",
            "tax_amount",
            "total",
            "currency",
            "item_count",
            "created_at",
            "shipping_method",
            "delivery_min_days",
            "delivery_max_days",
            "full_name",
            "address_line1",
            "address_line2",
            "city",
            "postal_code",
            "country",
            "phone",
            "refund",
            "refunded_amount",
            "items",
        ]

    def _refunds(self, obj):
        payments = list(obj.payments.all())
        captured = sum(
            (p.amount for p in payments if p.status in CAPTURED_OR_REFUNDED), Decimal("0.00")
        )
        refunded = sum((p.refunded_amount() for p in payments), Decimal("0.00"))
        pending = any(p.needs_refund for p in payments)
        return captured, refunded, pending

    def get_refund(self, obj) -> str | None:
        captured, refunded, pending = self._refunds(obj)
        if pending:
            return "pending"
        if captured and refunded >= captured:
            return "refunded"
        if refunded:
            return "partial"
        return None

    @extend_schema_field(serializers.DecimalField(max_digits=12, decimal_places=2))
    def get_refunded_amount(self, obj):
        return str(self._refunds(obj)[1])
