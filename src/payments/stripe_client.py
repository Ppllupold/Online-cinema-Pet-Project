# src/payments/stripe_client.py

import stripe
from decimal import Decimal

from src.config.settings import get_settings

settings = get_settings()
stripe.api_key = settings.STRIPE_SECRET_KEY


async def create_checkout_session(
    order_id: int,
    payment_id: int,
    amount: Decimal,
    customer_email: str,
    line_items: list[dict],
) -> stripe.checkout.Session:

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=line_items,
        mode="payment",
        success_url=f"{settings.BACKEND_URL}/api/v1/payments/payment-success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{settings.BACKEND_URL}/api/v1/payments/payment-cancel",
        customer_email=customer_email,
        metadata={
            "order_id": str(order_id),
            "payment_id": str(payment_id),
        },
    )

    return session


def construct_webhook_event(payload: bytes, sig_header: str):
    """Verify Stripe webhook signature"""
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
        return event
    except ValueError as e:
        raise ValueError(f"Invalid payload: {e}")
    except stripe.error.SignatureVerificationError as e:
        raise ValueError(f"Invalid signature: {e}")
