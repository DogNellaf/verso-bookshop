import django_filters

from main.models import Book


class BookFilter(django_filters.FilterSet):
    in_stock = django_filters.BooleanFilter(method="filter_in_stock", label="In stock")
    min_price = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr="lte")

    class Meta:
        model = Book
        fields = ["in_stock", "min_price", "max_price"]

    def filter_in_stock(self, queryset, name, value):
        return queryset.filter(stock__gt=0) if value else queryset.filter(stock=0)
