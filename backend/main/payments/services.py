import logging
from decimal import Decimal

from django.db import transaction
from django.utils.translation import gettext as _

from main.models import Order, Payment, Refund

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
    payment, order_open = _record_success(payment_id, external_id, provider_payment_id)
    if not order_open:
        request_refund(payment.pk, reason="The order was cancelled before the payment arrived")
        payment.refresh_from_db()
    return payment


def _record_success(payment_id, external_id, provider_payment_id):
    with transaction.atomic():
        payment = Payment.objects.select_for_update().select_related("order").get(pk=payment_id)
        if payment.status in CAPTURED or payment.status == Payment.Status.REFUNDED:
            return payment, True  # already recorded, e.g. a repeated webhook
        order = Order.objects.select_for_update().get(pk=payment.order_id)

        payment.status = Payment.Status.SUCCEEDED
        payment.failure_reason = ""
        if external_id:
            payment.external_id = external_id
        if provider_payment_id:
            payment.provider_payment_id = provider_payment_id
        order_open = order.status == Order.Status.PENDING
        if order_open:
            order.status = Order.Status.PAID
            order.save(update_fields=["status"])
        else:
            # The order was cancelled (or paid twice) while the customer was
            # on the payment page. The caller sends the money back.
            logger.warning(
                "Payment %s arrived for order %s in status %s",
                payment.pk,
                order.pk,
                order.status,
            )
        payment.save()
        return payment, order_open


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


MAX_REFUND_ATTEMPTS = 10
CAPTURED = (Payment.Status.SUCCEEDED, Payment.Status.PARTIALLY_REFUNDED)


class RefundError(Exception):
    pass


def request_refund(payment_id, amount=None, reason="", user=None):
    """Refund all that is left of a payment, or a part of it.

    Creates a Refund row and sends it to the provider right away. Returns the
    Refund. Raises RefundError when the amount isn't available.
    """
    with transaction.atomic():
        payment = Payment.objects.select_for_update().get(pk=payment_id)
        refundable = payment.refundable_amount()
        if refundable <= 0:
            raise RefundError(_("This payment has nothing left to refund."))
        amount = refundable if amount is None else Decimal(amount)
        if amount <= 0 or amount > refundable:
            raise RefundError(
                _("You can refund at most %(amount)s %(currency)s.")
                % {"amount": refundable, "currency": payment.currency}
            )
        refund = Refund.objects.create(
            payment=payment, amount=amount, reason=reason[:255], created_by=user
        )
        payment.needs_refund = True
        payment.save(update_fields=["needs_refund", "updated_at"])
    return process_refund(refund.pk)


def process_refund(refund_id):
    """Send a pending refund to the provider.

    The refund and payment rows stay locked during the provider call, and the
    provider gets an idempotency key per refund, so money never goes back
    twice. A failed call leaves the refund pending for the scheduler, until
    MAX_REFUND_ATTEMPTS is reached.
    """
    from main.payments import get_provider

    with transaction.atomic():
        refund = Refund.objects.select_for_update().get(pk=refund_id)
        if refund.status != Refund.Status.PENDING:
            return refund
        payment = Payment.objects.select_for_update().get(pk=refund.payment_id)
        refund.attempts += 1
        try:
            refund.provider_refund_id = get_provider(payment.provider).refund(payment, refund)
        except Exception as exc:  # provider errors, missing keys, network
            logger.warning("Refund %s failed (attempt %s): %s", refund.pk, refund.attempts, exc)
            refund.error = str(exc)[:255]
            if refund.attempts >= MAX_REFUND_ATTEMPTS:
                refund.status = Refund.Status.FAILED
            refund.save()
            _update_payment(payment)
            return refund

        refund.status = Refund.Status.SUCCEEDED
        refund.error = ""
        refund.save()
        _update_payment(payment)
        return refund


def _update_payment(payment):
    refunded = payment.refunded_amount()
    if refunded >= payment.amount:
        payment.status = Payment.Status.REFUNDED
    elif refunded > 0:
        payment.status = Payment.Status.PARTIALLY_REFUNDED
    payment.needs_refund = payment.refunds.filter(status=Refund.Status.PENDING).exists()
    payment.save(update_fields=["status", "needs_refund", "updated_at"])


def refund_order(order, reason="Order cancelled"):
    """Refund whatever is left of every payment of a cancelled order."""
    for payment in order.payments.filter(status__in=CAPTURED):
        if payment.refundable_amount() > 0:
            request_refund(payment.pk, reason=reason)
