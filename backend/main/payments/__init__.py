"""Payment providers.

A provider starts a payment for an order and later reports whether it
succeeded. ``demo`` works without any account, ``stripe`` uses Stripe
Checkout. The active one is chosen with the PAYMENT_PROVIDER setting.
"""

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from main.payments.demo import DemoProvider
from main.payments.stripe_provider import StripeProvider

PROVIDERS = {provider.name: provider for provider in (DemoProvider, StripeProvider)}


def get_provider(name=None):
    name = name or settings.PAYMENT_PROVIDER
    try:
        return PROVIDERS[name]()
    except KeyError as exc:
        raise ImproperlyConfigured(f"Unknown PAYMENT_PROVIDER {name!r}") from exc
