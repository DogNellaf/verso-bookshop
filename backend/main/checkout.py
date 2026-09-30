"""Shipping and tax for a cart.

Shipping prices are set in USD per zone and converted like book prices. The
tax rate of the destination country applies to the goods and the shipping.
Everything is rounded to the minor unit of the order currency.
"""

from dataclasses import dataclass, field
from decimal import Decimal

from django.utils.translation import gettext as _
from rest_framework.exceptions import ValidationError

from main import currency
from main.models import ShippingMethod, ShippingZone, TaxRate

ZERO = Decimal("0.00")


def zone_for(country):
    """The zone listing the country, else the rest-of-the-world zone."""
    fallback = None
    for zone in ShippingZone.objects.all():
        if country in zone.countries:
            return zone
        if not zone.countries:
            fallback = zone
    return fallback


def shipping_countries():
    """Countries the shop ships to, or None when a zone covers the whole world."""
    zones = list(ShippingZone.objects.filter(methods__active=True).distinct())
    if any(not zone.countries for zone in zones):
        return None
    return sorted({code for zone in zones for code in zone.countries})


@dataclass
class MethodQuote:
    code: str
    name: str
    price: Decimal
    free: bool
    min_days: int
    max_days: int


@dataclass
class Quote:
    currency: str
    subtotal: Decimal
    shipping: Decimal
    tax_rate: Decimal
    tax_name: str
    tax: Decimal
    total: Decimal
    method: MethodQuote
    methods: list[MethodQuote] = field(default_factory=list)


def _method_quote(method, subtotal_usd, code, language):
    free = method.free_from is not None and subtotal_usd >= method.free_from
    return MethodQuote(
        code=method.code,
        name=method.name(language),
        price=ZERO if free else currency.convert(method.price, code),
        free=free,
        min_days=method.min_days,
        max_days=method.max_days,
    )


def quote(items, country, method_code=None, language="en"):
    """Price a list of cart items for a destination.

    ``items`` are (book, quantity) pairs. Raises ValidationError when the
    country isn't served or the method doesn't exist for it.
    """
    country = (country or "").upper()
    code = currency.effective_currency()
    zone = zone_for(country)
    methods = list(zone.methods.filter(active=True)) if zone else []
    if not methods:
        raise ValidationError({"country": _("Sorry, we don't ship to this country.")})

    subtotal_usd = sum((book.price * qty for book, qty in items), ZERO)
    subtotal = sum((currency.convert(book.price, code) * qty for book, qty in items), ZERO)
    quotes = [_method_quote(m, subtotal_usd, code, language) for m in methods]

    if method_code:
        chosen = next((q for q in quotes if q.code == method_code), None)
        if chosen is None:
            raise ValidationError(
                {"shipping_method": _("This shipping method isn't available for the country.")}
            )
    else:
        chosen = min(quotes, key=lambda q: q.price)

    tax = TaxRate.objects.filter(country=country).first()
    tax_rate = tax.rate if tax else ZERO
    tax_amount = currency.round_amount((subtotal + chosen.price) * tax_rate / 100, code)
    return Quote(
        currency=code,
        subtotal=subtotal,
        shipping=chosen.price,
        tax_rate=tax_rate,
        tax_name=tax.name if tax else "",
        tax=tax_amount,
        total=subtotal + chosen.price + tax_amount,
        method=chosen,
        methods=quotes,
    )


def find_method(country, method_code):
    zone = zone_for(country)
    return ShippingMethod.objects.filter(zone=zone, code=method_code, active=True).first()
