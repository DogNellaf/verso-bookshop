"""Stripe Checkout.

The customer pays on a page hosted by Stripe. Stripe then calls our webhook,
which is the only place where an order becomes "paid". The redirect back to
the site carries no trust.
"""

from decimal import Decimal

import stripe
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def to_minor_units(amount, currency):
    """Stripe amounts are integers in the smallest unit (cents, or yen for JPY)."""
    from main.currency import info

    return int((Decimal(amount) * 10 ** info(currency).decimals).to_integral_value())


class StripeProvider:
    name = "stripe"

    def __init__(self):
        if not settings.STRIPE_SECRET_KEY:
            raise ImproperlyConfigured("PAYMENT_PROVIDER=stripe needs STRIPE_SECRET_KEY")
        self.api_key = settings.STRIPE_SECRET_KEY

    def start(self, payment):
        order = payment.order
        line_items = [
            {
                "quantity": item.quantity,
                "price_data": {
                    "currency": payment.currency.lower(),
                    "unit_amount": to_minor_units(item.unit_price, payment.currency),
                    "product_data": {"name": item.title},
                },
            }
            for item in order.items.all()
        ]
        # Shipping and tax as their own lines, so the Stripe receipt matches
        # the order total.
        for name, amount in (
            (order.shipping_method or "Shipping", order.shipping_cost),
            (f"Tax {order.tax_rate}%", order.tax_amount),
        ):
            if amount > 0:
                line_items.append(
                    {
                        "quantity": 1,
                        "price_data": {
                            "currency": payment.currency.lower(),
                            "unit_amount": to_minor_units(amount, payment.currency),
                            "product_data": {"name": name},
                        },
                    }
                )
        session = stripe.checkout.Session.create(
            api_key=self.api_key,
            mode="payment",
            line_items=line_items,
            client_reference_id=str(order.pk),
            metadata={"payment_id": str(payment.pk), "order_id": str(order.pk)},
            success_url=f"{settings.SITE_URL}/orders?paid={order.pk}",
            cancel_url=f"{settings.SITE_URL}/orders/{order.pk}/pay?cancelled=1",
        )
        payment.external_id = session.id
        payment.redirect_url = session.url
        payment.save(update_fields=["external_id", "redirect_url"])

    def refund(self, payment, refund):
        payment_intent = payment.provider_payment_id
        if not payment_intent:
            session = stripe.checkout.Session.retrieve(payment.external_id, api_key=self.api_key)
            payment_intent = session.payment_intent
        created = stripe.Refund.create(
            api_key=self.api_key,
            payment_intent=payment_intent,
            amount=to_minor_units(refund.amount, payment.currency),
            reason="requested_by_customer",
            metadata={"refund_id": str(refund.pk), "order_id": str(payment.order_id)},
            # Stripe answers a repeated request with the same refund.
            idempotency_key=f"verso-refund-{refund.pk}",
        )
        return created.id

    @staticmethod
    def parse_webhook(payload, signature):
        """Verify the Stripe signature and return the event as a plain dict."""
        event = stripe.Webhook.construct_event(payload, signature, settings.STRIPE_WEBHOOK_SECRET)
        return event.to_dict()
