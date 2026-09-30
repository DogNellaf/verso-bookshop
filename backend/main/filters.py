import django_filters

from main import currency
from main.models import Book


class BookFilter(django_filters.FilterSet):
    in_stock = django_filters.BooleanFilter(method="filter_in_stock", label="In stock")
    # Price bounds are given in the requested currency.
    min_price = django_filters.NumberFilter(method="filter_min_price")
    max_price = django_filters.NumberFilter(method="filter_max_price")

    class Meta:
        model = Book
        fields = ["in_stock", "min_price", "max_price"]

    def filter_in_stock(self, queryset, name, value):
        return queryset.filter(stock__gt=0) if value else queryset.filter(stock=0)

    def filter_min_price(self, queryset, name, value):
        return queryset.filter(price__gte=currency.to_usd(value))

    def filter_max_price(self, queryset, name, value):
        return queryset.filter(price__lte=currency.to_usd(value))
