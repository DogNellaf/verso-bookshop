from decimal import Decimal
from unittest import mock

from django.urls import reverse
from rest_framework import status

from main import checkout as checkout_module
from main.models import Currency, Order, ShippingMethod, ShippingZone, TaxRate
from main.tests.helpers import AuthedAPITestCase, checkout, make_book


class CheckoutTestCase(AuthedAPITestCase):
    """Uses the default zones and tax rates created by the migrations."""

    def setUp(self):
        super().setUp()
        self.book = make_book(title="Dune", price=Decimal("10.00"), stock=10, weight=250)

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
        self.assertEqual((data["tax_rate"], data["tax"]), ("7.000", "1.89"))
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
        self.assertEqual((data["tax_rate"], data["tax"]), ("10.000", "143.91"))

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
        self.assertEqual(response.data["tax_rate"], "7.000")

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


class RegionalTaxTest(CheckoutTestCase):
    def rate(self, region="", postal=""):
        rate = checkout_module.tax_rate_for("US", region, postal)
        return rate.rate if rate else None

    def test_most_specific_rate_wins(self):
        self.assertEqual(self.rate("CA", "94103"), Decimal("7.25"))
        self.assertEqual(self.rate("NY", "10001"), Decimal("8.875"))  # Manhattan
        self.assertEqual(self.rate("NY", "14201"), Decimal("4"))  # Buffalo, state rate only
        self.assertEqual(self.rate("IL", "60601"), Decimal("10.25"))  # Chicago
        self.assertIsNone(self.rate("OR", "97403"))  # no sales tax
        self.assertIsNone(self.rate())  # state unknown yet

    def test_postal_codes_are_normalized(self):
        TaxRate.objects.create(country="GB", postal_prefix="sw1 a", rate=Decimal("1"))
        rate = checkout_module.tax_rate_for("GB", "", " SW1A 1AA")
        self.assertEqual(str(rate), "GB-SW1A 1%")

    def test_a_country_rate_is_the_fallback(self):
        TaxRate.objects.create(country="CA", rate=Decimal("5"), name="GST")
        TaxRate.objects.create(country="CA", region="ON", rate=Decimal("13"), name="HST")
        self.assertEqual(checkout_module.tax_rate_for("CA", "on").rate, Decimal("13"))
        self.assertEqual(checkout_module.tax_rate_for("CA", "QC").rate, Decimal("5"))

    def test_state_sales_tax_on_books_and_shipping(self):
        self.add(2)
        data = self.quote_for("US", region="CA", postal_code="94103")
        # 7.25% of $20 + $4.99
        self.assertEqual((data["tax_rate"], data["tax"]), ("7.250", "1.81"))
        self.assertEqual(data["tax_name"], "Sales tax")

    def test_rate_can_leave_shipping_untaxed(self):
        TaxRate.objects.filter(country="US", region="CA").update(tax_shipping=False)
        self.add(2)
        self.assertEqual(self.quote_for("US", region="CA")["tax"], "1.45")

    def test_local_rate_at_checkout(self):
        self.add(2)
        response = checkout(self.client, region="ny", postal_code="10001", city="New York")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        order = Order.objects.get()
        self.assertEqual((order.region, order.tax_rate), ("NY", Decimal("8.875")))
        self.assertEqual(order.tax_amount, Decimal("2.22"))  # 8.875% of $24.99

    def test_us_address_needs_a_state(self):
        self.add(1)
        for region in ("", "ZZ"):
            response = checkout(self.client, region=region)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("region", response.data)

    def test_quote_accepts_a_missing_state_but_not_a_wrong_one(self):
        self.add(1)
        self.assertEqual(self.quote_for("US")["tax"], "0.00")
        response = self.client.post(
            reverse("api_quote"), {"country": "US", "region": "ZZ"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_other_countries_take_any_region(self):
        self.add(1)
        response = checkout(self.client, country="DE", region="Bayern", city="Munich")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(Order.objects.get().region, "Bayern")

    def test_checkout_info_lists_us_states(self):
        regions = self.client.get(reverse("api_checkout_info")).data["regions"]
        self.assertEqual(len(regions["US"]), 51)
        self.assertIn({"code": "NY", "name": "New York"}, regions["US"])

    def quote_for(self, country, **extra):
        payload = {"country": country, **extra}
        response = self.client.post(reverse("api_quote"), payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return response.data


class WeightShippingTest(CheckoutTestCase):
    def test_price_grows_with_each_started_kilogram(self):
        self.add(5)  # 1250 g, $50 so the free threshold is off below
        ShippingMethod.objects.update(free_from=None)
        data = self.quote("US").data
        self.assertEqual(data["weight"], 1250)
        # First kilogram in the base price, one more started kilogram.
        self.assertEqual(data["shipping"], "6.49")
        prices = {m["code"]: m["price"] for m in data["methods"]}
        self.assertEqual(prices, {"standard": "6.49", "express": "18.99"})

    def test_heavy_order(self):
        self.book.weight = 3000
        self.book.save()
        self.add(3)  # 9 kg, $30
        prices = {m["code"]: m["price"] for m in self.quote("US").data["methods"]}
        self.assertEqual(prices, {"standard": "16.99", "express": "46.99"})

    def test_methods_over_their_weight_limit_are_hidden(self):
        self.book.weight = 3000
        self.book.save()
        self.add(4)  # 12 kg, express takes up to 10 kg
        data = self.quote("US").data
        self.assertEqual([m["code"] for m in data["methods"]], ["standard"])
        self.assertEqual(data["shipping"], "0.00")  # $40 ships free
        response = self.quote("US", "express")
        self.assertIn("shipping_method", response.data)

    def test_too_heavy_for_every_method(self):
        self.book.weight = 25000
        self.book.save()
        self.add(1)
        response = self.quote("US")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("split", str(response.data["weight"]))

    def test_order_keeps_the_weight(self):
        self.add(3)
        response = checkout(self.client)
        self.assertEqual(response.data["shipping_weight"], 750)

    def test_price_for_without_weight_pricing(self):
        method = ShippingMethod(price=Decimal("5"), per_kg=Decimal("0"))
        self.assertEqual(method.price_for(5000), Decimal("5"))
        self.assertTrue(method.fits(10**6))
