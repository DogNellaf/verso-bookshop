from decimal import Decimal
from unittest import mock

import stripe
from django.contrib.auth.models import User
from django.test import override_settings
from django.urls import reverse
from rest_framework import status

from main.models import Order, Payment
from main.payments.services import refund_payment
from main.scheduler import retry_refunds
from main.tests.helpers import AuthedAPITestCase, make_book

GOOD_CARD = {"card_number": "4242424242424242", "expiry": "12/40", "cvc": "123"}


class RefundTestCase(AuthedAPITestCase):
    def setUp(self):
        super().setUp()
        self.book = make_book(price=Decimal("10.00"), stock=5)
        self.client.post(reverse("api_cart_items"), {"book": self.book.pk, "quantity": 2})
        self.order_id = self.client.post(reverse("api_checkout")).data["id"]

    def pay_demo(self):
        payment = self.client.post(reverse("api_order_pay", args=[self.order_id])).data
        self.client.post(reverse("api_payment_demo_confirm", args=[payment["id"]]), GOOD_CARD)
        return Payment.objects.get(pk=payment["id"])

    def cancel(self):
        return self.client.post(reverse("api_order_cancel", args=[self.order_id]))


class DemoRefundTest(RefundTestCase):
    def test_cancelling_a_paid_order_refunds_and_restocks(self):
        payment = self.pay_demo()
        self.assertEqual(Order.objects.get(pk=self.order_id).status, Order.Status.PAID)

        response = self.cancel()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "cancelled")
        self.assertEqual(response.data["refund"], "refunded")

        payment.refresh_from_db()
        self.assertEqual(
            (payment.status, payment.refund_id), ("refunded", f"demo-refund-{payment.pk}")
        )
        self.book.refresh_from_db()
        self.assertEqual(self.book.stock, 5)

    def test_shipped_orders_cannot_be_cancelled(self):
        self.pay_demo()
        Order.objects.filter(pk=self.order_id).update(status=Order.Status.SHIPPED)
        response = self.cancel()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Payment.objects.get().status, "succeeded")

    def test_refund_happens_once(self):
        payment = self.pay_demo()
        self.cancel()
        refund_payment(payment.pk)
        payment.refresh_from_db()
        self.assertEqual(payment.refund_id, f"demo-refund-{payment.pk}")

    def test_unpaid_order_has_no_refund(self):
        response = self.cancel()
        self.assertIsNone(response.data["refund"])


@override_settings(
    PAYMENT_PROVIDER="stripe",
    STRIPE_SECRET_KEY="sk_test_dummy",
    STRIPE_WEBHOOK_SECRET="whsec_test",
)
class StripeRefundTest(RefundTestCase):
    def paid_stripe_payment(self, payment_intent="pi_1"):
        order = Order.objects.get(pk=self.order_id)
        order.status = Order.Status.PAID
        order.save()
        return Payment.objects.create(
            order=order,
            provider="stripe",
            amount=order.total,
            currency=order.currency,
            status=Payment.Status.SUCCEEDED,
            external_id="cs_1",
            provider_payment_id=payment_intent,
        )

    def test_cancel_refunds_through_stripe(self):
        payment = self.paid_stripe_payment()
        with mock.patch("stripe.Refund.create", return_value=mock.Mock(id="re_9")) as create:
            response = self.cancel()
        self.assertEqual(response.data["refund"], "refunded")
        self.assertEqual(create.call_args.kwargs["payment_intent"], "pi_1")
        payment.refresh_from_db()
        self.assertEqual(payment.refund_id, "re_9")

    def test_payment_intent_is_looked_up_when_missing(self):
        payment = self.paid_stripe_payment(payment_intent="")
        with (
            mock.patch(
                "stripe.checkout.Session.retrieve", return_value=mock.Mock(payment_intent="pi_x")
            ) as retrieve,
            mock.patch("stripe.Refund.create", return_value=mock.Mock(id="re_2")) as create,
        ):
            refund_payment(payment.pk)
        retrieve.assert_called_once_with("cs_1", api_key="sk_test_dummy")
        self.assertEqual(create.call_args.kwargs["payment_intent"], "pi_x")

    def test_failed_refund_is_retried_by_the_scheduler(self):
        payment = self.paid_stripe_payment()
        error = stripe.APIConnectionError("network down")
        with mock.patch("stripe.Refund.create", side_effect=error):
            response = self.cancel()
        self.assertEqual(response.data["refund"], "pending")
        payment.refresh_from_db()
        self.assertTrue(payment.needs_refund)
        self.assertEqual(payment.status, "succeeded")

        with mock.patch("stripe.Refund.create", return_value=mock.Mock(id="re_3")):
            self.assertEqual(retry_refunds(), "1 of 1 refund(s) sent")
        payment.refresh_from_db()
        self.assertEqual((payment.status, payment.needs_refund), ("refunded", False))

    def test_admin_can_refund_a_payment(self):
        payment = self.paid_stripe_payment()
        User.objects.create_superuser("admin", "a@example.com", "adminpass123")
        self.client.login(username="admin", password="adminpass123")
        with mock.patch("stripe.Refund.create", return_value=mock.Mock(id="re_4")):
            self.client.post(
                reverse("admin:main_payment_changelist"),
                {"action": "refund_selected", "_selected_action": [payment.pk]},
            )
        payment.refresh_from_db()
        self.assertEqual(payment.status, "refunded")
