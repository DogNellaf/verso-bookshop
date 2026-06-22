from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
import decimal


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


class Order(models.Model):
    buyer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="orders",
        verbose_name="Buyer",
    )
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name="orders",
        verbose_name="Book",
    )
    quantity = models.PositiveIntegerField(default=1, verbose_name="Quantity")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created at")

    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.buyer.username} — {self.book.title} × {self.quantity}"

    @property
    def total_price(self):
        return self.book.price * self.quantity
