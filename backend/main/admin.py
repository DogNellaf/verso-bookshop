from django.contrib import admin, messages
from django.db.models import Count
from django.utils.html import format_html

from main import machine_translation
from main.models import (
    Book,
    BookTranslation,
    Cart,
    CartItem,
    ExchangeRate,
    Order,
    OrderItem,
    Payment,
)

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


class BookTranslationInline(admin.StackedInline):
    model = BookTranslation
    extra = 0


class TranslationStatusFilter(admin.SimpleListFilter):
    title = "translations"
    parameter_name = "translations"

    def lookups(self, request, model_admin):
        return [("missing", "Missing some languages"), ("complete", "All languages")]

    def queryset(self, request, queryset):
        full = len(machine_translation.TRANSLATED_LANGUAGES)
        queryset = queryset.annotate(translation_count=Count("translations"))
        if self.value() == "missing":
            return queryset.filter(translation_count__lt=full)
        if self.value() == "complete":
            return queryset.filter(translation_count__gte=full)
        return queryset


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("cover_thumb", "title", "author", "price", "stock", "translation_status")
    list_display_links = ("cover_thumb", "title")
    search_fields = ("title", "author")
    list_filter = (StockFilter, TranslationStatusFilter, "author")
    actions = ("translate_missing",)
    list_editable = ("price", "stock")
    readonly_fields = ("cover_preview",)
    inlines = (BookTranslationInline,)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("translations")

    @admin.display(description="Translations")
    def translation_status(self, obj):
        missing = machine_translation.missing_languages(obj)
        if not missing:
            return "all"
        return "missing " + ", ".join(missing)

    @admin.action(description="Translate missing languages (DeepL)")
    def translate_missing(self, request, queryset):
        if not machine_translation.is_configured():
            self.message_user(
                request, "Set DEEPL_API_KEY to use machine translation.", messages.WARNING
            )
            return
        done = 0
        for book in queryset.prefetch_related("translations"):
            try:
                if machine_translation.translate_book(book):
                    done += 1
            except machine_translation.TranslationError as exc:
                self.message_user(request, f"{book.title}: {exc}", messages.ERROR)
                return
        self.message_user(request, f"Translated {done} book(s).", messages.SUCCESS)

    @admin.display(description="Cover")
    def cover_thumb(self, obj):
        if not obj.cover:
            return "-"
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


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    can_delete = False
    fields = (
        "provider",
        "status",
        "amount",
        "currency",
        "external_id",
        "needs_refund",
        "created_at",
    )
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "buyer", "status", "item_count", "total", "currency", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("buyer__username",)
    readonly_fields = ("total", "created_at")
    list_editable = ("status",)
    date_hierarchy = "created_at"
    inlines = (OrderItemInline, PaymentInline)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("buyer").prefetch_related("items")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order",
        "provider",
        "status",
        "amount",
        "currency",
        "needs_refund",
        "created_at",
    )
    list_filter = ("provider", "status", "needs_refund")
    search_fields = ("external_id", "order__buyer__username")
    readonly_fields = (
        "order",
        "provider",
        "amount",
        "currency",
        "external_id",
        "redirect_url",
        "failure_reason",
        "created_at",
        "updated_at",
    )


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ("currency", "rate", "updated_at")
