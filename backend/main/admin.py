from django import forms
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
    JobRun,
    Order,
    OrderItem,
    Payment,
)
from main.search import update_book_index

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


class ReviewOnEditForm(forms.ModelForm):
    """Saving a changed translation in the admin counts as reviewing it."""

    class Meta:
        model = BookTranslation
        fields = ["book", "language", "title", "author", "description", "reviewed"]

    def clean(self):
        cleaned = super().clean()
        text_changed = {"title", "author", "description"} & set(self.changed_data)
        if text_changed and "reviewed" not in self.changed_data:
            cleaned["reviewed"] = True
        return cleaned


class BookTranslationInline(admin.StackedInline):
    model = BookTranslation
    form = ReviewOnEditForm
    extra = 0
    fields = ("language", "title", "author", "description", "reviewed", "machine_translated")
    readonly_fields = ("machine_translated",)


@admin.register(BookTranslation)
class BookTranslationAdmin(admin.ModelAdmin):
    """A review queue for machine translations."""

    form = ReviewOnEditForm
    list_display = ("book", "language", "title", "machine_translated", "reviewed")
    list_filter = ("reviewed", "machine_translated", "language")
    search_fields = ("title", "book__title")
    readonly_fields = ("machine_translated",)
    actions = ("mark_reviewed",)

    @admin.action(description="Mark as reviewed")
    def mark_reviewed(self, request, queryset):
        # update() skips signals, so refresh the search index by hand.
        book_ids = set(queryset.values_list("book_id", flat=True))
        updated = queryset.update(reviewed=True)
        for book_id in book_ids:
            update_book_index(Book, book_id)
        self.message_user(request, f"{updated} translation(s) marked as reviewed.")


class TranslationStatusFilter(admin.SimpleListFilter):
    title = "translations"
    parameter_name = "translations"

    def lookups(self, request, model_admin):
        return [
            ("missing", "Missing some languages"),
            ("review", "Waiting for review"),
            ("complete", "All languages"),
        ]

    def queryset(self, request, queryset):
        full = len(machine_translation.TRANSLATED_LANGUAGES)
        queryset = queryset.annotate(translation_count=Count("translations"))
        if self.value() == "missing":
            return queryset.filter(translation_count__lt=full)
        if self.value() == "review":
            return queryset.filter(translations__reviewed=False).distinct()
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
        unreviewed = {t.language for t in obj.translations.all() if not t.reviewed}
        to_review = [c for c in machine_translation.TRANSLATED_LANGUAGES if c in unreviewed]
        parts = []
        if missing:
            parts.append("missing " + ", ".join(missing))
        if to_review:
            parts.append("to review " + ", ".join(to_review))
        return "; ".join(parts) or "all"

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
    actions = ("refund_selected",)
    search_fields = ("external_id", "order__buyer__username")
    readonly_fields = (
        "order",
        "provider",
        "amount",
        "currency",
        "external_id",
        "provider_payment_id",
        "refund_id",
        "redirect_url",
        "failure_reason",
        "created_at",
        "updated_at",
    )

    @admin.action(description="Refund selected payments")
    def refund_selected(self, request, queryset):
        from main.payments.services import refund_payment

        ids = queryset.filter(status=Payment.Status.SUCCEEDED).values_list("pk", flat=True)
        results = [refund_payment(pk) for pk in ids]
        failed = [p for p in results if p.status != Payment.Status.REFUNDED]
        self.message_user(
            request,
            f"Refunded {len(results) - len(failed)} payment(s), {len(failed)} failed.",
            messages.WARNING if failed else messages.SUCCESS,
        )


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ("currency", "rate", "updated_at")


@admin.register(JobRun)
class JobRunAdmin(admin.ModelAdmin):
    list_display = ("name", "last_started", "last_finished", "succeeded", "message")
    readonly_fields = ("name", "last_started", "last_finished", "succeeded", "message")

    def has_add_permission(self, request):
        return False
