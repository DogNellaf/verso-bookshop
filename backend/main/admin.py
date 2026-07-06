from django.contrib import admin

from main.models import Book, Order


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "price", "stock")
    search_fields = ("title", "author")
    list_filter = ("author",)
    list_editable = ("price", "stock")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("buyer", "book", "quantity", "created_at")
    search_fields = ("buyer__username", "book__title")
    list_filter = ("created_at",)
    readonly_fields = ("created_at",)
