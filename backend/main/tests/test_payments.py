import hashlib
import hmac
import json
import time
from datetime import date
from decimal import Decimal
from unittest import mock

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.exceptions import ValidationError

from main.models import Order, Payment
from main.payments.demo import luhn_valid, validate_card
from main.payments.stripe_provider import to_minor_units
from main.tests.helpers import AuthedAPITestCase, checkout, make_book, make_user

GOOD_CARD = {"card_number": "4242 4242 4242 4242", "expiry": "12/40", "cvc": "123"}
WEBHOOK_SECRET = "whsec_test"


class CardValidationTest(TestCase):
    def test_luhn(self):
        self.assertTrue(luhn_valid("4242424242424242"))
        self.assertFalse(luhn_valid("4242424242424241"))

    def test_valid_card(self):
        self.assertEqual(validate_card("4242-4242 4242 4242", "1/30", "999"), "4242424242424242")

    def test_invalid_fields(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_card("1234", "13/30", "1", today=date(2026, 1, 1))
        self.assertEqual(set(ctx.exception.detail), {"card_number", "expiry", "cvc"})

    def test_expired_card(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_card("4242424242424242", "12/25", "123", today=date(2026, 1, 1))
        self.assertIn("expiry", ctx.exception.detail)


class PaymentTestCase(AuthedAPITestCase):
    def setUp(self):
        super().setUp()
        self.book = make_book(price=Decimal("10.00"), stock=5)
        self.client.post(reverse("api_cart_items"), {"book": self.book.pk, "quantity": 2})
        self.order_id = checkout(self.client).data["id"]

    def start(self):
        response = self.client.post(reverse("api_order_pay", args=[self.order_id]))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return response.data

    def order(self):
        return Order.objects.get(pk=self.order_id)


class DemoPaymentTest(PaymentTestCase):
    def confirm(self, payment_id, **card):
        return self.client.post(
            reverse("api_payment_demo_confirm", args=[payment_id]), {**GOOD_CARD, **card}
        )

    def test_successful_payment_marks_the_order_paid(self):
        payment = self.start()
        self.assertEqual((payment["provider"], payment["status"]), ("demo", "pending"))
        # $20 of books plus $4.99 standard shipping to the US, no tax there.
        self.assertEqual((payment["amount"], payment["currency"]), ("24.99", "USD"))

        response = self.confirm(payment["id"])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "succeeded")
        self.assertEqual(self.order().status, Order.Status.PAID)

    def test_declined_card(self):
        payment = self.start()
        response = self.confirm(payment["id"], card_number="4000 0000 0000 0002")
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(response.data["payment"]["status"], "failed")
        self.assertEqual(self.order().status, Order.Status.PENDING)

        # A new attempt can still succeed.
        retry = self.start()
        self.assertEqual(self.confirm(retry["id"]).status_code, status.HTTP_200_OK)
        self.assertEqual(self.order().status, Order.Status.PAID)

    def test_decline_message_is_translated(self):
        payment = self.start()
        response = self.client.post(
            reverse("api_payment_demo_confirm", args=[payment["id"]]),
            {**GOOD_CARD, "card_number": "4000000000009995"},
            HTTP_ACCEPT_LANGUAGE="ru",
        )
        self.assertEqual(response.data["detail"], "На карте недостаточно средств.")

    def test_invalid_card_keeps_the_payment_pending(self):
        payment = self.start()
        response = self.confirm(payment["id"], card_number="1234")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Payment.objects.get(pk=payment["id"]).status, "pending")

    def test_finished_payment_cannot_be_confirmed_again(self):
        payment = self.start()
        self.confirm(payment["id"])
        self.assertEqual(self.confirm(payment["id"]).status_code, status.HTTP_400_BAD_REQUEST)

    def test_only_pending_orders_can_be_paid(self):
        self.client.post(reverse("api_order_cancel", args=[self.order_id]))
        response = self.client.post(reverse("api_order_pay", args=[self.order_id]))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cancelling_the_order_cancels_its_pending_payment(self):
        payment = self.start()
        self.client.post(reverse("api_order_cancel", args=[self.order_id]))
        self.assertEqual(Payment.objects.get(pk=payment["id"]).status, "cancelled")

    def test_other_users_cannot_see_or_pay(self):
        payment = self.start()
        self.authenticate(make_user("other", "otherpass123"))
        self.assertEqual(
            self.client.get(reverse("api_payment", args=[payment["id"]])).status_code, 404
        )
        self.assertEqual(self.confirm(payment["id"]).status_code, 404)
        self.assertEqual(
            self.client.post(reverse("api_order_pay", args=[self.order_id])).status_code, 404
        )


def signed(payload):
    body = json.dumps(payload)
    timestamp = int(time.time())
    signature = hmac.new(
        WEBHOOK_SECRET.encode(), f"{timestamp}.{body}".encode(), hashlib.sha256
    ).hexdigest()
    return body, f"t={timestamp},v1={signature}"


@override_settings(
    PAYMENT_PROVIDER="stripe",
    STRIPE_SECRET_KEY="sk_test_dummy",
    STRIPE_WEBHOOK_SECRET=WEBHOOK_SECRET,
    SITE_URL="https://shop.example",
)
class StripePaymentTest(PaymentTestCase):
    def start_stripe(self):
        session = mock.Mock(id="cs_test_123", url="https://checkout.stripe.com/c/pay/cs_test_123")
        with mock.patch("stripe.checkout.Session.create", return_value=session) as create:
            payment = self.start()
        return payment, create

    def webhook(self, event_type, payment_id, payment_status="paid", sign=True):
        payload = {
            "id": "evt_1",
            "object": "event",
            "type": event_type,
            "data": {
                "object": {
                    "id": "cs_test_123",
                    "object": "checkout.session",
                    "payment_status": payment_status,
                    "payment_intent": "pi_123",
                    "metadata": {"payment_id": str(payment_id)},
                }
            },
        }
        body, header = signed(payload)
        if not sign:
            header = "t=1,v1=bad"
        return self.client.generic(
            "POST",
            reverse("api_stripe_webhook"),
            body,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE=header,
        )

    def test_start_creates_a_checkout_session(self):
        payment, create = self.start_stripe()
        self.assertEqual(payment["provider"], "stripe")
        self.assertEqual(payment["redirect_url"], "https://checkout.stripe.com/c/pay/cs_test_123")

        kwargs = create.call_args.kwargs
        self.assertEqual(kwargs["line_items"][0]["price_data"]["unit_amount"], 1000)
        self.assertEqual(kwargs["line_items"][0]["quantity"], 2)
        self.assertEqual(kwargs["metadata"]["payment_id"], str(payment["id"]))
        self.assertEqual(kwargs["success_url"], f"https://shop.example/orders?paid={self.order_id}")

    def test_signed_webhook_marks_the_order_paid(self):
        payment, _ = self.start_stripe()
        response = self.webhook("checkout.session.completed", payment["id"])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.order().status, Order.Status.PAID)
        # Stripe retries webhooks. A second delivery changes nothing.
        self.webhook("checkout.session.completed", payment["id"])
        self.assertEqual(Payment.objects.get(pk=payment["id"]).status, "succeeded")

    def test_unsigned_webhook_is_rejected(self):
        payment, _ = self.start_stripe()
        response = self.webhook("checkout.session.completed", payment["id"], sign=False)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.order().status, Order.Status.PENDING)

    def test_expired_session_fails_the_payment(self):
        payment, _ = self.start_stripe()
        self.webhook("checkout.session.expired", payment["id"], payment_status="unpaid")
        self.assertEqual(Payment.objects.get(pk=payment["id"]).status, "failed")
        self.assertEqual(self.order().status, Order.Status.PENDING)

    def test_money_for_a_cancelled_order_is_refunded_right_away(self):
        payment, _ = self.start_stripe()
        self.client.post(reverse("api_order_cancel", args=[self.order_id]))
        with mock.patch("stripe.Refund.create", return_value=mock.Mock(id="re_1")) as refund:
            self.webhook("checkout.session.completed", payment["id"])
        refund.assert_called_once()
        self.assertEqual(refund.call_args.kwargs["payment_intent"], "pi_123")
        self.assertTrue(refund.call_args.kwargs["idempotency_key"].startswith("verso-refund-"))
        self.assertEqual(refund.call_args.kwargs["amount"], 2499)
        stored = Payment.objects.get(pk=payment["id"])
        self.assertEqual(stored.status, "refunded")
        self.assertEqual(stored.refunds.get().provider_refund_id, "re_1")
        self.assertFalse(stored.needs_refund)
        self.assertEqual(self.order().status, Order.Status.CANCELLED)

    def test_demo_confirm_is_not_available_for_stripe_payments(self):
        payment, _ = self.start_stripe()
        response = self.client.post(
            reverse("api_payment_demo_confirm", args=[payment["id"]]), GOOD_CARD
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_config_reports_the_provider(self):
        self.assertEqual(
            self.client.get(reverse("api_payment_config")).data, {"provider": "stripe"}
        )

    def test_minor_units(self):
        self.assertEqual(to_minor_units(Decimal("1170.70"), "RUB"), 117070)
