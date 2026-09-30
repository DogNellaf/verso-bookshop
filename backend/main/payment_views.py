import logging

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import permissions, serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from main.models import Order, Payment
from main.payments import get_provider
from main.payments.demo import DemoProvider, validate_card
from main.payments.services import mark_failed, mark_succeeded, start_payment
from main.payments.stripe_provider import StripeProvider

logger = logging.getLogger(__name__)


class PaymentSerializer(serializers.ModelSerializer):
    order = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "order",
            "provider",
            "status",
            "amount",
            "currency",
            "redirect_url",
            "failure_reason",
            "created_at",
        ]


class CardSerializer(serializers.Serializer):
    card_number = serializers.CharField()
    expiry = serializers.CharField(help_text="MM/YY")
    cvc = serializers.CharField()


class PaymentConfigView(APIView):
    """Which provider the SPA should show (card form or redirect)."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        responses=inline_serializer("PaymentConfig", {"provider": serializers.CharField()})
    )
    def get(self, request):
        return Response({"provider": settings.PAYMENT_PROVIDER})


class PaymentStartView(APIView):
    """Start paying for a pending order with the configured provider."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=None, responses={201: PaymentSerializer})
    def post(self, request, pk):
        with transaction.atomic():
            order = get_object_or_404(Order.objects.select_for_update(), pk=pk, buyer=request.user)
            if order.status != Order.Status.PENDING:
                raise ValidationError({"detail": _("Only pending orders can be paid.")})
            payment = start_payment(order, get_provider())
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)


class PaymentDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses=PaymentSerializer)
    def get(self, request, pk):
        payment = get_object_or_404(Payment, pk=pk, order__buyer=request.user)
        return Response(PaymentSerializer(payment).data)


class DemoConfirmView(APIView):
    """Pay a demo payment with a test card."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=CardSerializer, responses=PaymentSerializer)
    def post(self, request, pk):
        payment = get_object_or_404(
            Payment, pk=pk, order__buyer=request.user, provider=DemoProvider.name
        )
        if payment.status != Payment.Status.PENDING:
            raise ValidationError({"detail": _("This payment is already finished.")})

        card = CardSerializer(data=request.data)
        card.is_valid(raise_exception=True)
        data = card.validated_data
        number = validate_card(data["card_number"], data["expiry"], data["cvc"])

        failure = DemoProvider().charge(number)
        if failure:
            payment = mark_failed(payment.pk, failure)
            return Response(
                {"detail": failure, "payment": PaymentSerializer(payment).data},
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )
        payment = mark_succeeded(payment.pk, external_id=f"demo-{number[-4:]}")
        return Response(PaymentSerializer(payment).data)


class StripeWebhookView(APIView):
    """Receives Stripe events. Authenticated by the Stripe signature only."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = []

    @extend_schema(request=None, responses={200: None, 400: None})
    def post(self, request):
        try:
            event = StripeProvider.parse_webhook(
                request.body, request.headers.get("Stripe-Signature", "")
            )
        except Exception:  # bad payload or signature
            logger.warning("Rejected a Stripe webhook with an invalid signature")
            return Response(status=status.HTTP_400_BAD_REQUEST)

        session = event["data"]["object"]
        payment_id = (session.get("metadata") or {}).get("payment_id")
        if not payment_id or not Payment.objects.filter(pk=payment_id).exists():
            return Response(status=status.HTTP_200_OK)  # not ours, acknowledge

        if (
            event["type"] == "checkout.session.completed"
            and session.get("payment_status") == "paid"
        ):
            mark_succeeded(payment_id, external_id=session.get("id", ""))
        elif event["type"] in ("checkout.session.expired", "checkout.session.async_payment_failed"):
            mark_failed(payment_id, "Checkout session expired or failed.")
        return Response(status=status.HTTP_200_OK)
