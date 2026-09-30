from decimal import Decimal
from unittest import mock

import stripe
from django.contrib.auth.models import User
from django.test import override_settings
from django.urls import reverse
from rest_framework import status

from main.models import Order, Payment, Refund
from main.payments.services import RefundError, process_refund, request_refund
from main.scheduler import retry_refunds
from main.tests.helpers import AuthedAPITestCase, checkout, make_book

GOOD_CARD = {"card_number": "4242424242424242", "expiry": "12/40", "cvc": "123"}


class RefundTestCase(AuthedAPITestCase):
    """An order of $20 of books plus $4.99 shipping, so $24.99 in total."""

    def setUp(self):
        super().setUp()
        self.book = make_book(price=Decimal("10.00"), stock=5)
        self.client.post(reverse("api_cart_items"), {"book": self.book.pk, "quantity": 2})
        self.order_id = checkout(self.client).data["id"]

    def pay_demo(self):
        payment = self.client.post(reverse("api_order_pay", args=[self.order_id])).data
        self.client.post(reverse("api_payment_demo_confirm", args=[payment["id"]]), GOOD_CARD)
        return Payment.objects.get(pk=payment["id"])

    def cancel(self):
        return self.client.post(reverse("api_order_cancel", args=[self.order_id]))

    def order(self):
        return self.client.get(reverse("api_order", args=[self.order_id])).data


class DemoRefundTest(RefundTestCase):
    def test_cancelling_a_paid_order_refunds_and_restocks(self):
        payment = self.pay_demo()
        self.assertEqual(Order.objects.get(pk=self.order_id).status, Order.Status.PAID)

        response = self.cancel()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "cancelled")
        self.assertEqual(response.data["refund"], "refunded")
        self.assertEqual(response.data["refunded_amount"], "24.99")

        payment.refresh_from_db()
        refund = payment.refunds.get()
        self.assertEqual(payment.status, "refunded")
        self.assertEqual(
            (refund.amount, refund.provider_refund_id),
            (Decimal("24.99"), f"demo-refund-{refund.pk}"),
        )
        self.book.refresh_from_db()
        self.assertEqual(self.book.stock, 5)

    def test_partial_refunds_add_up(self):
        payment = self.pay_demo()
        first = request_refund(payment.pk, Decimal("5.00"), reason="Damaged cover")
        self.assertEqual(first.status, Refund.Status.SUCCEEDED)
        payment.refresh_from_db()
        self.assertEqual(payment.status, "partially_refunded")
        self.assertEqual(payment.refundable_amount(), Decimal("19.99"))
        self.assertEqual(
            (self.order()["refund"], self.order()["refunded_amount"]), ("partial", "5.00")
        )
        # The order stays paid, the customer keeps the books.
        self.assertEqual(Order.objects.get(pk=self.order_id).status, Order.Status.PAID)

        with self.assertRaises(RefundError):
            request_refund(payment.pk, Decimal("20.00"))

        # Cancelling refunds what is left.
        self.cancel()
        payment.refresh_from_db()
        self.assertEqual(payment.status, "refunded")
        self.assertEqual(
            sorted(payment.refunds.values_list("amount", flat=True)),
            [Decimal("5.00"), Decimal("19.99")],
        )
        self.assertEqual(self.order()["refunded_amount"], "24.99")

    def test_nothing_to_refund(self):
        payment = self.pay_demo()
        request_refund(payment.pk)
        with self.assertRaises(RefundError):
            request_refund(payment.pk)
        with self.assertRaises(RefundError):
            request_refund(payment.pk, Decimal("0"))

    def test_shipped_orders_cannot_be_cancelled(self):
        self.pay_demo()
        Order.objects.filter(pk=self.order_id).update(status=Order.Status.SHIPPED)
        response = self.cancel()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Payment.objects.get().status, "succeeded")

    def test_unpaid_order_has_no_refund(self):
        response = self.cancel()
        self.assertIsNone(response.data["refund"])
        self.assertEqual(response.data["refunded_amount"], "0.00")


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
        kwargs = create.call_args.kwargs
        self.assertEqual((kwargs["payment_intent"], kwargs["amount"]), ("pi_1", 2499))
        refund = payment.refunds.get()
        self.assertEqual(kwargs["idempotency_key"], f"verso-refund-{refund.pk}")
        self.assertEqual(refund.provider_refund_id, "re_9")

    def test_partial_refund_sends_the_amount_in_minor_units(self):
        payment = self.paid_stripe_payment()
        with mock.patch("stripe.Refund.create", return_value=mock.Mock(id="re_5")) as create:
            request_refund(payment.pk, Decimal("7.50"))
        self.assertEqual(create.call_args.kwargs["amount"], 750)

    def test_payment_intent_is_looked_up_when_missing(self):
        payment = self.paid_stripe_payment(payment_intent="")
        with (
            mock.patch(
                "stripe.checkout.Session.retrieve", return_value=mock.Mock(payment_intent="pi_x")
            ) as retrieve,
            mock.patch("stripe.Refund.create", return_value=mock.Mock(id="re_2")) as create,
        ):
            request_refund(payment.pk)
        retrieve.assert_called_once_with("cs_1", api_key="sk_test_dummy")
        self.assertEqual(create.call_args.kwargs["payment_intent"], "pi_x")

    def test_failed_refund_is_retried_by_the_scheduler(self):
        payment = self.paid_stripe_payment()
        error = stripe.APIConnectionError("network down")
        with mock.patch("stripe.Refund.create", side_effect=error):
            response = self.cancel()
        self.assertEqual(response.data["refund"], "pending")
        refund = payment.refunds.get()
        self.assertEqual((refund.status, refund.attempts), ("pending", 1))
        self.assertIn("network down", refund.error)

        with mock.patch("stripe.Refund.create", return_value=mock.Mock(id="re_3")):
            self.assertEqual(retry_refunds(), "1 of 1 refund(s) sent")
        payment.refresh_from_db()
        self.assertEqual((payment.status, payment.needs_refund), ("refunded", False))

    def test_refund_gives_up_after_many_attempts(self):
        payment = self.paid_stripe_payment()
        with mock.patch("stripe.Refund.create", side_effect=stripe.APIConnectionError("down")):
            refund = request_refund(payment.pk)
            for _ in range(9):
                refund = process_refund(refund.pk)
        self.assertEqual((refund.status, refund.attempts), ("failed", 10))
        payment.refresh_from_db()
        self.assertFalse(payment.needs_refund)
        # A failed refund frees the amount again.
        self.assertEqual(payment.refundable_amount(), Decimal("24.99"))


class RefundAdminTest(RefundTestCase):
    def setUp(self):
        super().setUp()
        self.payment = self.pay_demo()
        User.objects.create_superuser("admin", "a@example.com", "adminpass123")
        self.client.login(username="admin", password="adminpass123")

    def test_staff_refund_part_of_a_payment(self):
        response = self.client.post(
            reverse("admin:main_refund_add"),
            {"payment": self.payment.pk, "amount": "4.99", "reason": "Late delivery"},
        )
        self.assertEqual(response.status_code, 302)
        refund = Refund.objects.get()
        self.assertEqual(
            (refund.amount, refund.reason, refund.status),
            (Decimal("4.99"), "Late delivery", "succeeded"),
        )
        self.assertEqual(refund.created_by.username, "admin")

    def test_amount_above_what_is_left_is_rejected(self):
        response = self.client.post(
            reverse("admin:main_refund_add"), {"payment": self.payment.pk, "amount": "30.00"}
        )
        self.assertContains(response, "At most 24.99 USD is left to refund.")
        self.assertFalse(Refund.objects.exists())

    def test_empty_amount_refunds_everything_left(self):
        self.client.post(reverse("admin:main_refund_add"), {"payment": self.payment.pk})
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, "refunded")

    def test_payment_action_refunds_the_rest(self):
        request_refund(self.payment.pk, Decimal("10.00"))
        self.client.post(
            reverse("admin:main_payment_changelist"),
            {"action": "refund_selected", "_selected_action": [self.payment.pk]},
        )
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.refunded_amount(), Decimal("24.99"))
