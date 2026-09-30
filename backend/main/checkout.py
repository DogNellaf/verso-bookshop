"""Shipping and tax for a cart.

Shipping prices are set in USD per zone and converted like book prices. A
method has a base price for the first kilogram and a price for each started
kilogram above it, and it may have a weight limit. The most specific tax rate
for the address applies to the goods, and to the shipping if the rate says
so. Everything is rounded to the minor unit of the order currency.
"""

from dataclasses import dataclass, field
from decimal import Decimal

from django.utils.translation import gettext as _
from rest_framework.exceptions import ValidationError

from main import currency
from main.models import ShippingZone, TaxRate, normalize_postal

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
    weight: int
    method: MethodQuote
    methods: list[MethodQuote] = field(default_factory=list)


def _method_quote(method, subtotal_usd, weight, code, language):
    free = method.free_from is not None and subtotal_usd >= method.free_from
    return MethodQuote(
        code=method.code,
        name=method.name(language),
        price=ZERO if free else currency.convert(method.price_for(weight), code),
        free=free,
        min_days=method.min_days,
        max_days=method.max_days,
    )


def tax_rate_for(country, region="", postal_code=""):
    """The most specific tax rate matching the address, or None."""
    region = (region or "").upper().strip()
    postal = normalize_postal(postal_code or "")
    best = None
    for rate in TaxRate.objects.filter(country=country):
        if rate.region and rate.region != region:
            continue
        if rate.postal_prefix and not postal.startswith(rate.postal_prefix):
            continue
        key = (len(rate.postal_prefix), bool(rate.region))
        if best is None or key > best[0]:
            best = (key, rate)
    return best[1] if best else None


def quote(items, country, method_code=None, language="en", region="", postal_code=""):
    """Price a list of cart items for a destination.

    ``items`` are (book, quantity) pairs. Raises ValidationError when the
    country isn't served, the order is too heavy for every method, or the
    method doesn't exist for it.
    """
    country = (country or "").upper()
    code = currency.effective_currency()
    zone = zone_for(country)
    methods = list(zone.methods.filter(active=True)) if zone else []
    if not methods:
        raise ValidationError({"country": _("Sorry, we don't ship to this country.")})

    weight = sum((book.weight * qty for book, qty in items), 0)
    methods = [m for m in methods if m.fits(weight)]
    if not methods:
        raise ValidationError(
            {"weight": _("This order is too heavy to ship in one parcel. Please split it.")}
        )

    subtotal_usd = sum((book.price * qty for book, qty in items), ZERO)
    subtotal = sum((currency.convert(book.price, code) * qty for book, qty in items), ZERO)
    quotes = [_method_quote(m, subtotal_usd, weight, code, language) for m in methods]

    if method_code:
        chosen = next((q for q in quotes if q.code == method_code), None)
        if chosen is None:
            raise ValidationError(
                {"shipping_method": _("This shipping method isn't available for the order.")}
            )
    else:
        chosen = min(quotes, key=lambda q: q.price)

    tax = tax_rate_for(country, region, postal_code)
    tax_rate = tax.rate if tax else ZERO
    taxable = subtotal + (chosen.price if tax and tax.tax_shipping else ZERO)
    tax_amount = currency.round_amount(taxable * tax_rate / 100, code)
    return Quote(
        currency=code,
        subtotal=subtotal,
        shipping=chosen.price,
        tax_rate=tax_rate,
        tax_name=tax.name if tax else "",
        tax=tax_amount,
        total=subtotal + chosen.price + tax_amount,
        weight=weight,
        method=chosen,
        methods=quotes,
    )
