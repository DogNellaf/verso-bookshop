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


def mark_succeeded(payment_id, external_id="", provider_payment_id=""):
    """Record a successful payment and move the order to "paid". Idempotent.

    Money that arrives for an order cancelled in the meantime is refunded
    right away.
    """
    payment = _record_success(payment_id, external_id, provider_payment_id)
    if payment.needs_refund:
        payment = refund_payment(payment.pk)
    return payment


def _record_success(payment_id, external_id, provider_payment_id):
    with transaction.atomic():
        payment = Payment.objects.select_for_update().select_related("order").get(pk=payment_id)
        if payment.status == Payment.Status.SUCCEEDED:
            return payment
        order = Order.objects.select_for_update().get(pk=payment.order_id)

        payment.status = Payment.Status.SUCCEEDED
        payment.failure_reason = ""
        if external_id:
            payment.external_id = external_id
        if provider_payment_id:
            payment.provider_payment_id = provider_payment_id
        if order.status == Order.Status.PENDING:
            order.status = Order.Status.PAID
            order.save(update_fields=["status"])
        else:
            # The order was cancelled (or paid twice) while the customer was
            # on the payment page. The money goes back.
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


def refund_payment(payment_id):
    """Send a succeeded payment's money back through its provider.

    The row stays locked during the provider call, and providers use an
    idempotency key, so a payment is never refunded twice. When the provider
    fails, the payment keeps ``needs_refund`` and the scheduler retries it.
    """
    from main.payments import get_provider

    with transaction.atomic():
        payment = Payment.objects.select_for_update().get(pk=payment_id)
        if payment.status != Payment.Status.SUCCEEDED:
            return payment
        try:
            refund_id = get_provider(payment.provider).refund(payment)
        except Exception as exc:  # provider errors, missing keys, network
            logger.warning("Refund of payment %s failed: %s", payment.pk, exc)
            payment.needs_refund = True
            payment.failure_reason = f"Refund failed: {exc}"[:255]
            payment.save(update_fields=["needs_refund", "failure_reason", "updated_at"])
            return payment
        payment.status = Payment.Status.REFUNDED
        payment.refund_id = refund_id
        payment.needs_refund = False
        payment.failure_reason = ""
        payment.save()
        return payment


def refund_order(order):
    """Refund every succeeded payment of a cancelled order."""
    for payment_id in order.payments.filter(status=Payment.Status.SUCCEEDED).values_list(
        "pk", flat=True
    ):
        refund_payment(payment_id)
