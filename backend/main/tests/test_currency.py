from decimal import Decimal
from io import StringIO
from unittest import mock

from django.core.management import CommandError, call_command
from django.test import TestCase
from django.urls import reverse

from main import currency
from main.models import ExchangeRate, Order
from main.tests.helpers import APITestCase, AuthedAPITestCase, make_book


def set_rates():
    ExchangeRate.objects.create(currency="EUR", rate=Decimal("0.9"))
    ExchangeRate.objects.create(currency="RUB", rate=Decimal("90.123"))


class ConversionTest(TestCase):
    def setUp(self):
        set_rates()

    def test_convert_rounds_to_cents(self):
        self.assertEqual(currency.convert(Decimal("10.00"), "EUR"), Decimal("9.00"))
        self.assertEqual(currency.convert(Decimal("12.99"), "RUB"), Decimal("1170.70"))
        self.assertEqual(currency.convert(Decimal("12.99"), "USD"), Decimal("12.99"))

    def test_unknown_currency_falls_back_to_usd(self):
        self.assertEqual(currency.normalize("jpy"), "USD")
        self.assertEqual(currency.normalize(" eur "), "EUR")

    def test_saving_a_rate_clears_the_cache(self):
        self.assertEqual(currency.rates()["EUR"], Decimal("0.9"))
        ExchangeRate.objects.filter(currency="EUR").update(rate=Decimal("2"))
        self.assertEqual(currency.rates()["EUR"], Decimal("0.9"))  # still cached
        rate = ExchangeRate.objects.get(currency="EUR")
        rate.rate = Decimal("0.5")
        rate.save()
        self.assertEqual(currency.rates()["EUR"], Decimal("0.5"))


class CurrencyApiTest(AuthedAPITestCase):
    def setUp(self):
        super().setUp()
        set_rates()
        self.book = make_book(title="Dune", price=Decimal("10.00"), stock=5)

    def test_book_price_in_the_requested_currency(self):
        url = reverse("book-detail", args=[self.book.pk])
        self.assertEqual(self.client.get(url).data["price"], "10.00")
        self.assertEqual(self.client.get(url).data["currency"], "USD")
        data = self.client.get(url, HTTP_X_CURRENCY="EUR").data
        self.assertEqual((data["price"], data["currency"]), ("9.00", "EUR"))
        data = self.client.get(url, {"currency": "rub"}).data
        self.assertEqual((data["price"], data["currency"]), ("901.23", "RUB"))

    def test_missing_rate_shows_dollars(self):
        ExchangeRate.objects.get(currency="RUB").delete()
        data = self.client.get(reverse("book-detail", args=[self.book.pk]), HTTP_X_CURRENCY="RUB")
        self.assertEqual((data.data["price"], data.data["currency"]), ("10.00", "USD"))

    def test_cart_totals_are_converted(self):
        self.client.post(reverse("api_cart_items"), {"book": self.book.pk, "quantity": 3})
        cart = self.client.get(reverse("api_cart"), HTTP_X_CURRENCY="RUB").data
        self.assertEqual(cart["currency"], "RUB")
        self.assertEqual(cart["items"][0]["subtotal"], "2703.69")
        self.assertEqual(cart["total_price"], "2703.69")

    def test_order_keeps_the_currency_and_prices_of_checkout(self):
        self.client.post(reverse("api_cart_items"), {"book": self.book.pk, "quantity": 2})
        order = self.client.post(reverse("api_checkout"), HTTP_X_CURRENCY="EUR").data
        self.assertEqual((order["currency"], order["total"]), ("EUR", "18.00"))
        self.assertEqual(order["items"][0]["unit_price"], "9.00")

        # A later rate change or another display currency doesn't touch it.
        ExchangeRate.objects.filter(currency="EUR").update(rate=Decimal("5"))
        again = self.client.get(reverse("api_order", args=[order["id"]]), HTTP_X_CURRENCY="RUB")
        self.assertEqual((again.data["currency"], again.data["total"]), ("EUR", "18.00"))
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
    def feed(self, payload):
        import json

        response = mock.MagicMock()
        response.__enter__.return_value = StringIO(json.dumps(payload))
        return mock.patch("urllib.request.urlopen", return_value=response)

    def test_updates_configured_currencies(self):
        payload = {"base_code": "USD", "rates": {"EUR": 0.8765, "RUB": 81.5, "JPY": 150}}
        with self.feed(payload):
            call_command("update_exchange_rates", stdout=StringIO())
        rates = dict(ExchangeRate.objects.values_list("currency", "rate"))
        self.assertEqual(rates, {"EUR": Decimal("0.876500"), "RUB": Decimal("81.500000")})

    def test_bad_feed_is_an_error(self):
        with self.feed({"base_code": "EUR", "rates": {}}), self.assertRaises(CommandError):
            call_command("update_exchange_rates", stdout=StringIO())
