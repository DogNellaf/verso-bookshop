import decimal

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.postgres.search import SearchVectorField
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models


class Book(models.Model):
    title = models.CharField(max_length=255, verbose_name="Title")
    author = models.CharField(max_length=255, verbose_name="Author")
    description = models.TextField(verbose_name="Description")
    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(decimal.Decimal("0.01"))],
        verbose_name="Price",
    )
    stock = models.PositiveIntegerField(default=0, verbose_name="Stock")
    cover = models.ImageField(upload_to="covers/", blank=True, null=True, verbose_name="Cover")
    # Maintained by main.search. Titles and authors in every language, and on
    # PostgreSQL a full-text vector of the book and its translations.
    search_text = models.TextField(blank=True, default="", editable=False)
    search_document = SearchVectorField(null=True, editable=False)

    class Meta:
        verbose_name = "Book"
        verbose_name_plural = "Books"
        ordering = ["title"]

    def __str__(self):
        return f"{self.title} by {self.author}"

    @property
    def in_stock(self):
        return self.stock > 0


class BookTranslation(models.Model):
    """Title, author and description of a book in one of the UI languages.

    The fields on ``Book`` are the English originals; the API falls back to
    them when a translation is missing.
    """

    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name="translations",
        verbose_name="Book",
    )
    language = models.CharField(
        max_length=8,
        choices=[(code, name) for code, name in settings.LANGUAGES if code != "en"],
        verbose_name="Language",
    )
    title = models.CharField(max_length=255, verbose_name="Title")
    author = models.CharField(max_length=255, verbose_name="Author")
    description = models.TextField(verbose_name="Description")
    # Machine translations wait for a person to check them. Editing a
    # translation in the admin counts as a review.
    machine_translated = models.BooleanField(default=False, verbose_name="Machine translated")
    reviewed = models.BooleanField(default=True, verbose_name="Reviewed")

    class Meta:
        verbose_name = "Book translation"
        verbose_name_plural = "Book translations"
        ordering = ["language"]
        constraints = [
            models.UniqueConstraint(fields=["book", "language"], name="unique_book_language"),
        ]

    def __str__(self):
        return f"{self.book.title} [{self.language}]"


class Currency(models.Model):
    """A currency the storefront can show prices in.

    Catalog prices are stored in US dollars and converted with ``rate``.
    Staff add or disable currencies in the admin. The scheduler refreshes the
    rates from the feed unless ``manual_rate`` is set.
    """

    code = models.CharField(
        max_length=3,
        primary_key=True,
        validators=[RegexValidator(r"^[A-Z]{3}$", "Use a three letter ISO 4217 code.")],
        verbose_name="Code",
    )
    rate = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(decimal.Decimal("0.000001"))],
        verbose_name="Units per 1 USD",
        help_text="Leave empty to fetch it from the rate feed.",
    )
    decimals = models.PositiveSmallIntegerField(
        default=2,
        validators=[MaxValueValidator(3)],
        verbose_name="Decimal places",
        help_text="0 for currencies without minor units, such as JPY.",
    )
    enabled = models.BooleanField(default=True, verbose_name="Enabled")
    manual_rate = models.BooleanField(
        default=False,
        verbose_name="Manual rate",
        help_text="Keep the rate as entered instead of updating it from the feed.",
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated at")

    class Meta:
        verbose_name = "Currency"
        verbose_name_plural = "Currencies"
        ordering = ["code"]

    def __str__(self):
        return self.code

    def save(self, *args, **kwargs):
        from main.currency import BASE_CURRENCY, clear_rates_cache

        self.code = self.code.upper()
        if self.code == BASE_CURRENCY:
            self.rate, self.enabled = decimal.Decimal(1), True
        super().save(*args, **kwargs)
        clear_rates_cache()

    def delete(self, *args, **kwargs):
        from main.currency import clear_rates_cache

        result = super().delete(*args, **kwargs)
        clear_rates_cache()
        return result


def validate_country(code):
    from main.countries import COUNTRY_CODES

    if code not in COUNTRY_CODES:
        raise ValidationError(f"{code} is not an ISO 3166 country code.")


def validate_country_list(value):
    for code in value:
        validate_country(code)


class ShippingZone(models.Model):
    """A group of countries with its own shipping methods.

    A zone without countries covers every country no other zone lists.
    """

    name = models.CharField(max_length=100, verbose_name="Name")
    countries = models.JSONField(
        default=list,
        blank=True,
        validators=[validate_country_list],
        verbose_name="Countries",
        help_text='ISO codes, e.g. ["DE", "FR"]. Empty means the rest of the world.',
    )

    class Meta:
        verbose_name = "Shipping zone"
        verbose_name_plural = "Shipping zones"
        ordering = ["name"]

    def __str__(self):
        return self.name


class ShippingMethod(models.Model):
    zone = models.ForeignKey(
        ShippingZone, on_delete=models.CASCADE, related_name="methods", verbose_name="Zone"
    )
    code = models.SlugField(max_length=40, verbose_name="Code")
    # {"en": "Standard", "ru": "Стандартная", ...}; English is the fallback.
    names = models.JSONField(default=dict, verbose_name="Names")
    price = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Price (USD)")
    free_from = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Free from (USD)",
        help_text="Orders at or above this subtotal ship free.",
    )
    min_days = models.PositiveSmallIntegerField(default=3, verbose_name="Delivery from (days)")
    max_days = models.PositiveSmallIntegerField(default=7, verbose_name="Delivery to (days)")
    active = models.BooleanField(default=True, verbose_name="Active")
    position = models.PositiveSmallIntegerField(default=0, verbose_name="Position")

    class Meta:
        verbose_name = "Shipping method"
        verbose_name_plural = "Shipping methods"
        ordering = ["zone", "position", "price"]
        constraints = [
            models.UniqueConstraint(fields=["zone", "code"], name="unique_zone_method"),
        ]

    def __str__(self):
        return f"{self.zone}: {self.name()}"

    def name(self, language="en"):
        return self.names.get(language) or self.names.get("en") or self.code


class TaxRate(models.Model):
    """Tax added to orders shipped to a country (book rates, often reduced)."""

    country = models.CharField(
        max_length=2, primary_key=True, validators=[validate_country], verbose_name="Country"
    )
    rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(decimal.Decimal("0")), MaxValueValidator(100)],
        verbose_name="Rate, %",
    )
    name = models.CharField(max_length=40, default="VAT", verbose_name="Name")

    class Meta:
        verbose_name = "Tax rate"
        verbose_name_plural = "Tax rates"
        ordering = ["country"]

    def __str__(self):
        return f"{self.country} {self.rate}%"


class Cart(models.Model):
    """A persistent, per-user shopping cart."""

    buyer = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="cart",
        verbose_name="Buyer",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created at")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated at")

    class Meta:
        verbose_name = "Cart"
        verbose_name_plural = "Carts"

    def __str__(self):
        return f"Cart of {self.buyer.username}"

    @property
    def total_price(self):
        return sum((item.subtotal for item in self.items.all()), decimal.Decimal("0.00"))

    @property
    def total_quantity(self):
        return sum(item.quantity for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Cart",
    )
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name="cart_items",
        verbose_name="Book",
    )
    quantity = models.PositiveIntegerField(default=1, verbose_name="Quantity")
    added_at = models.DateTimeField(auto_now_add=True, verbose_name="Added at")

    class Meta:
        verbose_name = "Cart item"
        verbose_name_plural = "Cart items"
        ordering = ["added_at"]
        constraints = [
            models.UniqueConstraint(fields=["cart", "book"], name="unique_cart_book"),
        ]

    def __str__(self):
        return f"{self.book.title} × {self.quantity}"

    @property
    def subtotal(self):
        return self.book.price * self.quantity


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    buyer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="orders",
        verbose_name="Buyer",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Status",
    )
    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=decimal.Decimal("0.00"),
        verbose_name="Total",
    )
    # Prices of an order are fixed in the currency the customer paid in.
    currency = models.CharField(max_length=3, default="USD", verbose_name="Currency")
    subtotal = models.DecimalField(
        max_digits=12, decimal_places=2, default=decimal.Decimal("0.00"), verbose_name="Subtotal"
    )
    shipping_cost = models.DecimalField(
        max_digits=12, decimal_places=2, default=decimal.Decimal("0.00"), verbose_name="Shipping"
    )
    tax_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=decimal.Decimal("0.00"), verbose_name="Tax rate, %"
    )
    tax_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=decimal.Decimal("0.00"), verbose_name="Tax"
    )
    # Snapshot of the shipping choice and the address at checkout.
    shipping_method = models.CharField(max_length=100, blank=True, verbose_name="Shipping method")
    delivery_min_days = models.PositiveSmallIntegerField(null=True, blank=True)
    delivery_max_days = models.PositiveSmallIntegerField(null=True, blank=True)
    full_name = models.CharField(max_length=150, blank=True, verbose_name="Full name")
    address_line1 = models.CharField(max_length=200, blank=True, verbose_name="Address")
    address_line2 = models.CharField(max_length=200, blank=True, verbose_name="Address, line 2")
    city = models.CharField(max_length=100, blank=True, verbose_name="City")
    postal_code = models.CharField(max_length=20, blank=True, verbose_name="Postal code")
    country = models.CharField(max_length=2, blank=True, verbose_name="Country")
    phone = models.CharField(max_length=30, blank=True, verbose_name="Phone")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created at")

    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.pk} ({self.buyer.username})"

    def recalculate_total(self, save=True):
        """Subtotal from the lines, total with shipping and tax."""
        self.subtotal = sum((item.subtotal for item in self.items.all()), decimal.Decimal("0.00"))
        self.total = self.subtotal + self.shipping_cost + self.tax_amount
        if save:
            self.save(update_fields=["subtotal", "total"])
        return self.total

    @property
    def item_count(self):
        return sum(item.quantity for item in self.items.all())


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Order",
    )
    book = models.ForeignKey(
        Book,
        on_delete=models.SET_NULL,
        null=True,
        related_name="order_items",
        verbose_name="Book",
    )
    # Snapshot of the book's title and price at purchase time so order history
    # stays accurate even if the book is later edited or deleted.
    title = models.CharField(max_length=255, verbose_name="Title")
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Unit price")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Quantity")

    class Meta:
        verbose_name = "Order item"
        verbose_name_plural = "Order items"
        ordering = ["id"]

    def __str__(self):
        return f"{self.title} × {self.quantity}"

    @property
    def subtotal(self):
        return self.unit_price * self.quantity


class Payment(models.Model):
    """One attempt to pay for an order through a payment provider."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"
        PARTIALLY_REFUNDED = "partially_refunded", "Partially refunded"
        REFUNDED = "refunded", "Refunded"

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="payments",
        verbose_name="Order",
    )
    provider = models.CharField(max_length=20, verbose_name="Provider")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Status",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Amount")
    currency = models.CharField(max_length=3, verbose_name="Currency")
    # Session or charge id at the provider, e.g. a Stripe Checkout Session id.
    external_id = models.CharField(max_length=255, blank=True, db_index=True)
    # The provider's id of the captured money (a Stripe PaymentIntent), used
    # for refunds.
    provider_payment_id = models.CharField(max_length=255, blank=True)
    redirect_url = models.URLField(max_length=1000, blank=True)
    failure_reason = models.CharField(max_length=255, blank=True)
    # True while one of its refunds waits to go through. The scheduler retries
    # those.
    needs_refund = models.BooleanField(default=False, verbose_name="Needs refund")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created at")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated at")

    class Meta:
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payment #{self.pk} for order #{self.order_id} ({self.status})"

    def refunded_amount(self):
        return sum(
            (r.amount for r in self.refunds.all() if r.status == Refund.Status.SUCCEEDED),
            decimal.Decimal("0.00"),
        )

    def refundable_amount(self):
        """What is left to refund, counting refunds that are still on their way."""
        if self.status not in (self.Status.SUCCEEDED, self.Status.PARTIALLY_REFUNDED):
            return decimal.Decimal("0.00")
        taken = sum(
            (r.amount for r in self.refunds.all() if r.status != Refund.Status.FAILED),
            decimal.Decimal("0.00"),
        )
        return max(self.amount - taken, decimal.Decimal("0.00"))


class Refund(models.Model):
    """Money sent back for a payment, all of it or a part."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    payment = models.ForeignKey(
        Payment, on_delete=models.CASCADE, related_name="refunds", verbose_name="Payment"
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(decimal.Decimal("0.01"))],
        verbose_name="Amount",
    )
    reason = models.CharField(max_length=255, blank=True, verbose_name="Reason")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name="Status"
    )
    provider_refund_id = models.CharField(max_length=255, blank=True, verbose_name="Provider id")
    attempts = models.PositiveSmallIntegerField(default=0, verbose_name="Attempts")
    error = models.CharField(max_length=255, blank=True, verbose_name="Last error")
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Created by"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created at")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated at")

    class Meta:
        verbose_name = "Refund"
        verbose_name_plural = "Refunds"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Refund #{self.pk} of {self.amount} {self.payment.currency} ({self.status})"


class JobRun(models.Model):
    """The last run of a scheduled job (see the run_scheduler command)."""

    name = models.CharField(max_length=64, primary_key=True, verbose_name="Job")
    last_started = models.DateTimeField(null=True, verbose_name="Last started")
    last_finished = models.DateTimeField(null=True, verbose_name="Last finished")
    succeeded = models.BooleanField(default=False, verbose_name="Succeeded")
    message = models.TextField(blank=True, verbose_name="Message")

    class Meta:
        verbose_name = "Scheduled job"
        verbose_name_plural = "Scheduled jobs"
        ordering = ["name"]

    def __str__(self):
        return self.name
