"""Currencies for catalog prices.

Books are priced in US dollars. The SPA sends the currency it wants in the
``X-Currency`` header and the API converts prices using ``Currency`` rows.
Staff manage the list of currencies in the admin. The active currency is kept
in a context variable, the same way Django keeps the active language.
"""

from contextvars import ContextVar
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from django.core.cache import cache

BASE_CURRENCY = "USD"
CENT = Decimal("0.01")
_CACHE_KEY = "verso:currencies"

_active: ContextVar[str] = ContextVar("verso_currency", default=BASE_CURRENCY)


@dataclass(frozen=True)
class CurrencyInfo:
    code: str
    rate: Decimal
    decimals: int

    @property
    def quantum(self):
        return Decimal(1).scaleb(-self.decimals)


def currencies():
    """Enabled currencies that have a rate, keyed by code. Cached for a minute."""
    cached = cache.get(_CACHE_KEY)
    if cached is None:
        from main.models import Currency

        cached = {
            c.code: CurrencyInfo(c.code, c.rate, c.decimals)
            for c in Currency.objects.filter(enabled=True, rate__isnull=False)
        }
        cached.setdefault(BASE_CURRENCY, CurrencyInfo(BASE_CURRENCY, Decimal(1), 2))
        cache.set(_CACHE_KEY, cached, 60)
    return cached


def clear_rates_cache():
    cache.delete(_CACHE_KEY)


def info(code=None):
    """The currency with its rate, or the base currency when it isn't available."""
    table = currencies()
    return table.get(code or get_currency()) or table[BASE_CURRENCY]


def normalize(code):
    """Return an available currency code, or the base currency."""
    code = (code or "").strip().upper()
    return code if code in currencies() else BASE_CURRENCY


def activate(code):
    return _active.set((code or "").strip().upper() or BASE_CURRENCY)


def deactivate(token):
    _active.reset(token)


def get_currency():
    return _active.get()


def effective_currency(code=None):
    """The currency prices are actually shown in (USD when it isn't available)."""
    return info(code).code


def rate_for(code):
    found = currencies().get(code)
    return found.rate if found else None


def round_amount(amount, code=None):
    return Decimal(amount).quantize(info(code).quantum, rounding=ROUND_HALF_UP)


def convert(amount_usd, code=None):
    """Convert a USD amount, rounded to the currency's minor unit."""
    target = info(code)
    return (Decimal(amount_usd) * target.rate).quantize(target.quantum, rounding=ROUND_HALF_UP)


def to_usd(amount, code=None):
    """Convert an amount in the currency back to USD (for price filters)."""
    return Decimal(amount) / info(code).rate


class CurrencyMiddleware:
    """Activates the currency from ``X-Currency`` or ``?currency=`` for the request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        code = request.headers.get("X-Currency") or request.GET.get("currency")
        token = activate(code)
        try:
            return self.get_response(request)
        finally:
            deactivate(token)
