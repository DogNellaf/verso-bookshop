from django.contrib import admin
from django.utils.html import format_html

from main.models import Book, Cart, CartItem, Order, OrderItem

admin.site.site_header = "Verso administration"
admin.site.site_title = "Verso admin"
admin.site.index_title = "Store management"


class StockFilter(admin.SimpleListFilter):
    title = "stock"
    parameter_name = "stock_level"

    def lookups(self, request, model_admin):
        return [("out", "Out of stock"), ("low", "Low (1–3)"), ("ok", "In stock (4+)")]

    def queryset(self, request, queryset):
        if self.value() == "out":
            return queryset.filter(stock=0)
        if self.value() == "low":
            return queryset.filter(stock__gte=1, stock__lte=3)
        if self.value() == "ok":
            return queryset.filter(stock__gte=4)
        return queryset


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("cover_thumb", "title", "author", "price", "stock")
    list_display_links = ("cover_thumb", "title")
    search_fields = ("title", "author")
    list_filter = (StockFilter, "author")
    list_editable = ("price", "stock")
    readonly_fields = ("cover_preview",)

    @admin.display(description="Cover")
    def cover_thumb(self, obj):
        if not obj.cover:
            return "—"
        return format_html('<img src="{}" style="height:48px;border-radius:3px">', obj.cover.url)

    @admin.display(description="Preview")
    def cover_preview(self, obj):
        if not obj.cover:
            return "No cover uploaded"
        return format_html(
            '<img src="{}" style="max-height:240px;border-radius:4px">', obj.cover.url
        )


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
    exclude = ("book",)
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    def subtotal(self, obj):
        return obj.subtotal


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "buyer", "status", "item_count", "total", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("buyer__username",)
    readonly_fields = ("total", "created_at")
    list_editable = ("status",)
    date_hierarchy = "created_at"
    inlines = (OrderItemInline,)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("buyer").prefetch_related("items")
