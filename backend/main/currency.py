"""Currencies for catalog prices.

Books are priced in US dollars. The SPA sends the currency it wants in the
``X-Currency`` header and the API converts prices using ``ExchangeRate`` rows.
The active currency is kept in a context variable, the same way Django keeps
the active language.
"""

from contextvars import ContextVar
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.core.cache import cache

BASE_CURRENCY = "USD"
CENT = Decimal("0.01")
_RATES_CACHE_KEY = "verso:exchange-rates"

_active: ContextVar[str] = ContextVar("verso_currency", default=BASE_CURRENCY)


def normalize(code):
    """Return a supported currency code, or the base currency."""
    code = (code or "").strip().upper()
    return code if code in settings.CURRENCIES else BASE_CURRENCY


def activate(code):
    return _active.set(normalize(code))


def deactivate(token):
    _active.reset(token)


def get_currency():
    return _active.get()


def rates():
    """Units per 1 USD for every configured currency, cached for a minute."""
    cached = cache.get(_RATES_CACHE_KEY)
    if cached is None:
        from main.models import ExchangeRate

        cached = {r.currency: r.rate for r in ExchangeRate.objects.all()}
        cached[BASE_CURRENCY] = Decimal(1)
        cache.set(_RATES_CACHE_KEY, cached, 60)
    return cached


def clear_rates_cache():
    cache.delete(_RATES_CACHE_KEY)


def rate_for(currency):
    # A currency without a rate falls back to dollars rather than a wrong price.
    return rates().get(currency)


def convert(amount_usd, currency=None):
    """Convert a USD amount to the currency, rounded to cents."""
    currency = currency or get_currency()
    rate = rate_for(currency)
    if rate is None:
        rate = Decimal(1)
    return (Decimal(amount_usd) * rate).quantize(CENT, rounding=ROUND_HALF_UP)


def effective_currency(currency=None):
    """The currency prices are actually shown in (USD when a rate is missing)."""
    currency = currency or get_currency()
    return currency if rate_for(currency) is not None else BASE_CURRENCY


def to_usd(amount, currency=None):
    """Convert an amount in the currency back to USD (for price filters)."""
    rate = rate_for(currency or get_currency()) or Decimal(1)
    return Decimal(amount) / rate


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
