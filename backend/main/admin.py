from django.contrib import admin

from main.models import Book, Cart, CartItem, Order, OrderItem


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "price", "stock")
    search_fields = ("title", "author")
    list_filter = ("author",)
    list_editable = ("price", "stock")


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    autocomplete_fields = ("book",)


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("buyer", "total_quantity", "total_price", "updated_at")
    search_fields = ("buyer__username",)
    inlines = (CartItemInline,)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("title", "unit_price", "quantity", "subtotal")

    def subtotal(self, obj):
        return obj.subtotal


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "buyer", "status", "item_count", "total", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("buyer__username",)
    readonly_fields = ("total", "created_at")
    list_editable = ("status",)
    inlines = (OrderItemInline,)
