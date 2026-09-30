"""Fetch current exchange rates for the configured currencies.

    python manage.py update_exchange_rates

Uses the free open.er-api.com feed by default (no key needed). Run it from
cron or a scheduler once a day.
"""

import json
import urllib.error
import urllib.request
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from main.currency import BASE_CURRENCY
from main.models import ExchangeRate


class Command(BaseCommand):
    help = "Update ExchangeRate rows from an online feed."

    def handle(self, *args, **options):
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

        updated = []
        for code in settings.CURRENCIES:
            if code == BASE_CURRENCY or code not in feed:
                continue
            rate = Decimal(str(feed[code])).quantize(Decimal("0.000001"))
            ExchangeRate.objects.update_or_create(currency=code, defaults={"rate": rate})
            updated.append(f"{code}={rate}")

        self.stdout.write(self.style.SUCCESS("Updated rates " + ", ".join(updated)))
