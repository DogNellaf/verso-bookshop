import json
from decimal import Decimal
from io import StringIO
from unittest import mock

from django.contrib.auth.models import User
from django.core.management import CommandError, call_command
from django.test import TestCase
from django.urls import reverse

from main import currency
from main.models import Currency, Order
from main.payments.stripe_provider import to_minor_units
from main.tests.helpers import APITestCase, AuthedAPITestCase, make_book


def set_rates():
    Currency.objects.update_or_create(code="EUR", defaults={"rate": Decimal("0.9")})
    Currency.objects.update_or_create(code="RUB", defaults={"rate": Decimal("90.123")})


def feed(payload):
    response = mock.MagicMock()
    response.__enter__.return_value = StringIO(json.dumps(payload))
    return mock.patch("urllib.request.urlopen", return_value=response)


class ConversionTest(TestCase):
    def setUp(self):
        set_rates()

    def test_convert_rounds_to_the_minor_unit(self):
        self.assertEqual(currency.convert(Decimal("10.00"), "EUR"), Decimal("9.00"))
        self.assertEqual(currency.convert(Decimal("12.99"), "RUB"), Decimal("1170.70"))
        self.assertEqual(currency.convert(Decimal("12.99"), "USD"), Decimal("12.99"))

    def test_currency_without_minor_units(self):
        Currency.objects.create(code="JPY", rate=Decimal("149.5"), decimals=0)
        self.assertEqual(currency.convert(Decimal("12.99"), "JPY"), Decimal("1942"))
        self.assertEqual(to_minor_units(Decimal("1942"), "JPY"), 1942)
        self.assertEqual(to_minor_units(Decimal("12.99"), "USD"), 1299)

    def test_unknown_or_disabled_currency_falls_back_to_usd(self):
        self.assertEqual(currency.normalize("jpy"), "USD")
        self.assertEqual(currency.normalize(" eur "), "EUR")
        Currency.objects.filter(code="EUR").update(enabled=False)
        currency.clear_rates_cache()
        self.assertEqual(currency.effective_currency("EUR"), "USD")

    def test_base_currency_is_always_one_and_enabled(self):
        usd = Currency.objects.get(code="USD")
        usd.rate, usd.enabled = Decimal("5"), False
        usd.save()
        usd.refresh_from_db()
        self.assertEqual((usd.rate, usd.enabled), (Decimal("1"), True))

    def test_saving_a_currency_clears_the_cache(self):
        self.assertEqual(currency.rate_for("EUR"), Decimal("0.9"))
        Currency.objects.filter(code="EUR").update(rate=Decimal("2"))
        self.assertEqual(currency.rate_for("EUR"), Decimal("0.9"))  # still cached
        eur = Currency.objects.get(code="EUR")
        eur.rate = Decimal("0.5")
        eur.save()
        self.assertEqual(currency.rate_for("EUR"), Decimal("0.5"))


class CurrencyApiTest(AuthedAPITestCase):
    def setUp(self):
        super().setUp()
        set_rates()
        self.book = make_book(title="Dune", price=Decimal("10.00"), stock=5)

    def test_currency_list(self):
        Currency.objects.create(code="GBP")  # no rate yet, not offered
        Currency.objects.create(code="JPY", rate=Decimal("150"), decimals=0)
        response = self.client.get(reverse("api_currencies"))
        self.assertEqual(
            response.data,
            [
                {"code": "EUR", "decimals": 2},
                {"code": "JPY", "decimals": 0},
                {"code": "RUB", "decimals": 2},
                {"code": "USD", "decimals": 2},
            ],
        )

    def test_book_price_in_the_requested_currency(self):
        url = reverse("book-detail", args=[self.book.pk])
        self.assertEqual(self.client.get(url).data["price"], "10.00")
        data = self.client.get(url, HTTP_X_CURRENCY="EUR").data
        self.assertEqual((data["price"], data["currency"]), ("9.00", "EUR"))
        data = self.client.get(url, {"currency": "rub"}).data
        self.assertEqual((data["price"], data["currency"]), ("901.23", "RUB"))

    def test_missing_rate_shows_dollars(self):
        Currency.objects.filter(code="RUB").update(rate=None)
        currency.clear_rates_cache()
        data = self.client.get(reverse("book-detail", args=[self.book.pk]), HTTP_X_CURRENCY="RUB")
        self.assertEqual((data.data["price"], data.data["currency"]), ("10.00", "USD"))

    def test_cart_totals_are_converted(self):
        self.client.post(reverse("api_cart_items"), {"book": self.book.pk, "quantity": 3})
        cart = self.client.get(reverse("api_cart"), HTTP_X_CURRENCY="RUB").data
        self.assertEqual(cart["currency"], "RUB")
        self.assertEqual(cart["items"][0]["subtotal"], "2703.69")
        self.assertEqual(cart["total_price"], "2703.69")

    def test_order_keeps_the_currency_and_prices_of_checkout(self):
        from main.tests.helpers import checkout_payload

        self.client.post(reverse("api_cart_items"), {"book": self.book.pk, "quantity": 2})
        order = self.client.post(
            reverse("api_checkout"), checkout_payload(), HTTP_X_CURRENCY="EUR", format="json"
        ).data
        self.assertEqual(order["currency"], "EUR")
        self.assertEqual(order["items"][0]["unit_price"], "9.00")
        total = order["total"]

        Currency.objects.filter(code="EUR").update(rate=Decimal("5"))
        currency.clear_rates_cache()
        again = self.client.get(reverse("api_order", args=[order["id"]]), HTTP_X_CURRENCY="RUB")
        self.assertEqual((again.data["currency"], again.data["total"]), ("EUR", total))
        self.assertEqual(Order.objects.get().currency, "EUR")


class PriceFilterCurrencyTest(APITestCase):
    def test_price_bounds_use_the_requested_currency(self):
        set_rates()
        make_book(title="Cheap", price=Decimal("5.00"))
        make_book(title="Pricey", price=Decimal("50.00"))
        response = self.client.get(
            reverse("book-list"), {"max_price": "1000"}, HTTP_X_CURRENCY="RUB"
        )
        self.assertEqual([b["title"] for b in response.data["results"]], ["Cheap"])


class UpdateRatesCommandTest(TestCase):
    def test_updates_every_currency_in_the_admin(self):
        Currency.objects.create(code="GBP")
        Currency.objects.update_or_create(
            code="RUB", defaults={"rate": Decimal("100"), "manual_rate": True}
        )
        payload = {
            "base_code": "USD",
            "rates": {"EUR": 0.8765, "RUB": 81.5, "GBP": 0.79, "JPY": 150},
        }
        out = StringIO()
        with feed(payload):
            call_command("update_exchange_rates", stdout=out)
        rates = dict(Currency.objects.values_list("code", "rate"))
        self.assertEqual(rates["EUR"], Decimal("0.876500"))
        self.assertEqual(rates["GBP"], Decimal("0.790000"))
        self.assertEqual(rates["RUB"], Decimal("100"))  # manual rate kept
        self.assertEqual(rates["USD"], Decimal("1"))
        self.assertNotIn("JPY", rates)

    def test_reports_codes_missing_from_the_feed(self):
        Currency.objects.create(code="XYZ")
        out = StringIO()
        with feed({"base_code": "USD", "rates": {"EUR": 0.9, "RUB": 90}}):
            call_command("update_exchange_rates", stdout=out)
        self.assertIn("Not in the feed XYZ", out.getvalue())

    def test_bad_feed_is_an_error(self):
        with feed({"base_code": "EUR", "rates": {}}), self.assertRaises(CommandError):
            call_command("update_exchange_rates", stdout=StringIO())


class CurrencyAdminTest(TestCase):
    def setUp(self):
        User.objects.create_superuser("admin", "a@example.com", "adminpass123")
        self.client.login(username="admin", password="adminpass123")

    def test_adding_a_currency_without_a_rate_fetches_it(self):
        payload = {"base_code": "USD", "rates": {"EUR": 0.9, "RUB": 90, "GBP": 0.79}}
        with feed(payload):
            self.client.post(
                reverse("admin:main_currency_add"),
                {"code": "GBP", "decimals": 2, "enabled": "on"},
            )
        self.assertEqual(Currency.objects.get(code="GBP").rate, Decimal("0.790000"))
        response = self.client.get(reverse("api_currencies"))
        self.assertIn({"code": "GBP", "decimals": 2}, response.json())
