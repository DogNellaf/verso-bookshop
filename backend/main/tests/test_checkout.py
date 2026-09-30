from decimal import Decimal
from unittest import mock

from django.urls import reverse
from rest_framework import status

from main.models import Currency, Order, ShippingMethod, ShippingZone, TaxRate
from main.tests.helpers import AuthedAPITestCase, checkout, make_book


class CheckoutTestCase(AuthedAPITestCase):
    """Uses the default zones and tax rates created by the migrations."""

    def setUp(self):
        super().setUp()
        self.book = make_book(title="Dune", price=Decimal("10.00"), stock=10)

    def add(self, quantity):
        self.client.post(reverse("api_cart_items"), {"book": self.book.pk, "quantity": quantity})

    def quote(self, country, method=None, **headers):
        payload = {"country": country}
        if method:
            payload["shipping_method"] = method
        return self.client.post(reverse("api_quote"), payload, format="json", **headers)


class QuoteTest(CheckoutTestCase):
    def test_us_standard_shipping_without_tax(self):
        self.add(2)
        data = self.quote("US").data
        self.assertEqual(data["subtotal"], "20.00")
        self.assertEqual(data["shipping"], "4.99")
        self.assertEqual(data["tax"], "0.00")
        self.assertEqual(data["total"], "24.99")
        self.assertEqual(data["method"]["code"], "standard")
        self.assertEqual([m["code"] for m in data["methods"]], ["standard", "express"])

    def test_free_shipping_above_the_threshold(self):
        self.add(4)  # $40, free from $35
        data = self.quote("US").data
        self.assertEqual((data["shipping"], data["method"]["free"]), ("0.00", True))
        express = self.quote("US", "express").data
        self.assertEqual(express["shipping"], "14.99")

    def test_book_vat_in_germany(self):
        self.add(2)
        data = self.quote("DE").data
        # $20 + $6.99 shipping, 7% on both.
        self.assertEqual(data["shipping"], "6.99")
        self.assertEqual((data["tax_rate"], data["tax"]), ("7.00", "1.89"))
        self.assertEqual(data["total"], "28.88")

    def test_rest_of_the_world(self):
        self.add(1)
        data = self.quote("JP").data
        self.assertEqual(data["method"]["code"], "international")

    def test_quote_in_another_currency_and_language(self):
        Currency.objects.filter(code="RUB").update(rate=Decimal("90"))
        self.add(1)
        data = self.quote("RU", HTTP_X_CURRENCY="RUB", HTTP_ACCEPT_LANGUAGE="ru").data
        self.assertEqual(data["currency"], "RUB")
        self.assertEqual(data["subtotal"], "900.00")
        self.assertEqual(data["shipping"], "539.10")
        self.assertEqual(data["method"]["name"], "Почта России")
        self.assertEqual((data["tax_rate"], data["tax"]), ("10.00", "143.91"))

    def test_country_that_is_not_served(self):
        ShippingZone.objects.filter(countries=[]).delete()
        self.add(1)
        response = self.quote("JP")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("country", response.data)

    def test_unknown_method(self):
        self.add(1)
        response = self.quote("US", "courier")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("shipping_method", response.data)

    def test_empty_cart(self):
        self.assertEqual(self.quote("US").status_code, status.HTTP_400_BAD_REQUEST)


class CheckoutWithAddressTest(CheckoutTestCase):
    def test_order_stores_address_shipping_and_tax(self):
        self.add(2)
        response = checkout(
            self.client,
            country="DE",
            city="Berlin",
            postal_code="10115",
            phone="+49 30 123",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        order = Order.objects.get()
        self.assertEqual(
            (order.subtotal, order.shipping_cost, order.tax_amount, order.total),
            (Decimal("20.00"), Decimal("6.99"), Decimal("1.89"), Decimal("28.88")),
        )
        self.assertEqual((order.city, order.country, order.phone), ("Berlin", "DE", "+49 30 123"))
        self.assertEqual(order.shipping_method, "Standard")
        self.assertEqual((order.delivery_min_days, order.delivery_max_days), (4, 8))
        self.assertEqual(response.data["tax_rate"], "7.00")

    def test_address_is_required(self):
        self.add(1)
        response = checkout(self.client, full_name="", city="")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(set(response.data), {"full_name", "city"})

    def test_country_must_exist(self):
        self.add(1)
        response = checkout(self.client, country="XX")
        self.assertIn("country", response.data)

    def test_later_price_changes_do_not_touch_the_order(self):
        self.add(1)
        checkout(self.client)
        ShippingMethod.objects.update(price=Decimal("99"))
        TaxRate.objects.create(country="US", rate=Decimal("20"))
        order = self.client.get(reverse("api_orders")).data[0]
        self.assertEqual((order["shipping_cost"], order["tax_amount"]), ("4.99", "0.00"))

    def test_saved_address_is_offered_next_time(self):
        info = self.client.get(reverse("api_checkout_info")).data
        self.assertIsNone(info["saved_address"])
        self.assertIsNone(info["countries"])  # a rest-of-the-world zone exists

        self.add(1)
        checkout(self.client, city="Berlin", country="DE")
        info = self.client.get(reverse("api_checkout_info")).data
        self.assertEqual(info["saved_address"]["city"], "Berlin")

    def test_country_list_without_a_world_zone(self):
        ShippingZone.objects.filter(countries=[]).delete()
        countries = self.client.get(reverse("api_checkout_info")).data["countries"]
        self.assertIn("DE", countries)
        self.assertIn("RU", countries)
        self.assertNotIn("JP", countries)

    def test_stripe_receipt_has_shipping_and_tax_lines(self):
        self.add(2)
        order_id = checkout(self.client, country="DE").data["id"]
        session = mock.Mock(id="cs_1", url="https://checkout.stripe.com/x")
        with (
            self.settings(PAYMENT_PROVIDER="stripe", STRIPE_SECRET_KEY="sk_test"),
            mock.patch("stripe.checkout.Session.create", return_value=session) as create,
        ):
            self.client.post(reverse("api_order_pay", args=[order_id]))
        lines = create.call_args.kwargs["line_items"]
        amounts = [line["price_data"]["unit_amount"] * line["quantity"] for line in lines]
        self.assertEqual(sum(amounts), 2888)
        self.assertEqual(lines[1]["price_data"]["product_data"]["name"], "Standard")
