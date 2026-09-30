"""Fetch current exchange rates for every currency in the admin.

    python manage.py update_exchange_rates

Uses the free open.er-api.com feed by default (no key needed). The scheduler
runs it once a day. Currencies marked "manual rate" are left alone.
"""

import json
import urllib.error
import urllib.request
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from main.currency import BASE_CURRENCY
from main.models import Currency


def fetch_rates():
    try:
        request = urllib.request.Request(
            settings.EXCHANGE_RATES_URL, headers={"User-Agent": "verso/1.0"}
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.load(response)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise CommandError(f"Could not fetch exchange rates: {exc}") from exc

    feed = payload.get("rates") or {}
    if payload.get("base_code", BASE_CURRENCY) != BASE_CURRENCY or not feed:
        raise CommandError("Unexpected response from the exchange rate feed.")
    return feed


class Command(BaseCommand):
    help = "Update currency rates from an online feed."

    def handle(self, *args, **options):
        feed = fetch_rates()
        updated, missing = [], []
        for currency in Currency.objects.exclude(code=BASE_CURRENCY).filter(manual_rate=False):
            if currency.code not in feed:
                missing.append(currency.code)
                continue
            currency.rate = Decimal(str(feed[currency.code])).quantize(Decimal("0.000001"))
            currency.save(update_fields=["rate", "updated_at"])
            updated.append(f"{currency.code}={currency.rate}")

        message = "Updated rates " + (", ".join(updated) or "none")
        if missing:
            message += ". Not in the feed " + ", ".join(missing)
        self.stdout.write(self.style.SUCCESS(message))
