import logging

from django.db import transaction

from main.models import Order, Payment

logger = logging.getLogger(__name__)


def start_payment(order, provider):
    """Create a Payment for a pending order and let the provider prepare it."""
    payment = Payment.objects.create(
        order=order,
        provider=provider.name,
        amount=order.total,
        currency=order.currency,
    )
    provider.start(payment)
    return payment


def mark_succeeded(payment_id, external_id=""):
    """Record a successful payment and move the order to "paid". Idempotent."""
    with transaction.atomic():
        payment = Payment.objects.select_for_update().select_related("order").get(pk=payment_id)
        if payment.status == Payment.Status.SUCCEEDED:
            return payment
        order = Order.objects.select_for_update().get(pk=payment.order_id)

        payment.status = Payment.Status.SUCCEEDED
        payment.failure_reason = ""
        if external_id:
            payment.external_id = external_id
        if order.status == Order.Status.PENDING:
            order.status = Order.Status.PAID
            order.save(update_fields=["status"])
        else:
            # The order was cancelled (or paid twice) while the customer was
            # on the payment page. Keep the money on record for a refund.
            payment.needs_refund = True
            logger.warning(
                "Payment %s arrived for order %s in status %s",
                payment.pk,
                order.pk,
                order.status,
            )
        payment.save()
        return payment


def mark_failed(payment_id, reason):
    with transaction.atomic():
        payment = Payment.objects.select_for_update().get(pk=payment_id)
        if payment.status == Payment.Status.PENDING:
            payment.status = Payment.Status.FAILED
            payment.failure_reason = reason[:255]
            payment.save(update_fields=["status", "failure_reason", "updated_at"])
        return payment


def cancel_pending_payments(order):
    order.payments.filter(status=Payment.Status.PENDING).update(status=Payment.Status.CANCELLED)
