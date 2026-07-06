import decimal

from django.contrib.auth.models import User
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

    class Meta:
        verbose_name = "Book"
        verbose_name_plural = "Books"
        ordering = ["title"]

    def __str__(self):
        return f"{self.title} — {self.author}"

    @property
    def in_stock(self):
        return self.stock > 0


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
        max_digits=10,
        decimal_places=2,
        default=decimal.Decimal("0.00"),
        verbose_name="Total",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created at")

    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.pk} — {self.buyer.username}"

    def recalculate_total(self, save=True):
        self.total = sum(
            (item.subtotal for item in self.items.all()), decimal.Decimal("0.00")
        )
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
    unit_price = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Unit price")
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
