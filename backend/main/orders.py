from django.db import transaction
from django.utils.translation import gettext as _

from main.models import Book, Order
from main.payments.services import cancel_pending_payments, refund_order

CANCELLABLE = (Order.Status.PENDING, Order.Status.PAID)


class CannotCancel(Exception):
    pass


def cancel_order(order_id, buyer=None, only_status=None, reason="Order cancelled"):
    """Cancel an order, put its books back in stock and refund what was paid.

    ``buyer`` restricts the lookup to that user's orders. ``only_status``
    cancels only if the order is still in that status (the scheduler uses it
    so a payment that lands at the same moment wins). Returns the order.
    """
    with transaction.atomic():
        orders = Order.objects.select_for_update()
        if buyer is not None:
            orders = orders.filter(buyer=buyer)
        order = orders.get(pk=order_id)
        allowed = (only_status,) if only_status else CANCELLABLE
        if order.status not in allowed:
            raise CannotCancel(_("Orders that have been shipped can no longer be cancelled."))

        items = list(order.items.all())
        book_ids = [item.book_id for item in items if item.book_id]
        books = {book.id: book for book in Book.objects.select_for_update().filter(id__in=book_ids)}
        for item in items:
            book = books.get(item.book_id)
            if book is not None:
                book.stock += item.quantity
                book.save(update_fields=["stock"])

        order.status = Order.Status.CANCELLED
        order.save(update_fields=["status"])
        cancel_pending_payments(order)

    # Talk to the payment provider only after the cancellation is saved.
    refund_order(order, reason=reason)
    return order
