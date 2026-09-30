import decimal

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.postgres.search import SearchVectorField
from django.core.validators import MinValueValidator
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


class ExchangeRate(models.Model):
    """How many units of a currency one US dollar buys.

    Catalog prices are stored in US dollars and converted on the fly.
    """

    currency = models.CharField(max_length=3, primary_key=True, verbose_name="Currency")
    rate = models.DecimalField(
        max_digits=14,
        decimal_places=6,
        validators=[MinValueValidator(decimal.Decimal("0.000001"))],
        verbose_name="Units per 1 USD",
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated at")

    class Meta:
        verbose_name = "Exchange rate"
        verbose_name_plural = "Exchange rates"
        ordering = ["currency"]

    def __str__(self):
        return f"1 USD = {self.rate} {self.currency}"

    def save(self, *args, **kwargs):
        from main.currency import clear_rates_cache

        super().save(*args, **kwargs)
        clear_rates_cache()

    def delete(self, *args, **kwargs):
        from main.currency import clear_rates_cache

        result = super().delete(*args, **kwargs)
        clear_rates_cache()
        return result


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
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created at")

    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.pk} ({self.buyer.username})"

    def recalculate_total(self, save=True):
        self.total = sum((item.subtotal for item in self.items.all()), decimal.Decimal("0.00"))
        if save:
            self.save(update_fields=["total"])
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
    refund_id = models.CharField(max_length=255, blank=True)
    redirect_url = models.URLField(max_length=1000, blank=True)
    failure_reason = models.CharField(max_length=255, blank=True)
    # Set while a refund is owed but has not gone through yet. The scheduler
    # retries these.
    needs_refund = models.BooleanField(default=False, verbose_name="Needs refund")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created at")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated at")

    class Meta:
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payment #{self.pk} for order #{self.order_id} ({self.status})"


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
