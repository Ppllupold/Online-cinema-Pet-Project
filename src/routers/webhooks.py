# src/routers/webhook_handlers.py

from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies.db import get_db
from src.payments.stripe_client import construct_webhook_event
from src.payments.webhook_handlers import (
    handle_checkout_completed,
    handle_checkout_expired,
)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post(
    "/stripe",
    summary="Handle Stripe webhook events",
    description=(
        "Receives and processes webhook events sent by Stripe. "
        "The request must include a valid `stripe-signature` header for payload verification. "
        "Handles the following events:\n\n"
        "- `checkout.session.completed` — marks the payment as successful and sends a confirmation email.\n"
        "- `checkout.session.expired` — marks the payment as cancelled and notifies the user.\n\n"
        "This endpoint is intended for Stripe servers only and should be registered in the Stripe dashboard."
    ),
    responses={
        200: {"description": "Event processed successfully"},
        400: {"description": "Missing or invalid stripe-signature header"},
    },
)
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not sig_header:
        raise HTTPException(400, "Missing stripe-signature header")

    try:
        event = construct_webhook_event(payload, sig_header)
    except ValueError as e:
        raise HTTPException(400, str(e))

    if event.type == "checkout.session.completed":
        session = event.data.object
        await handle_checkout_completed(session.id, db)

    elif event.type == "checkout.session.expired":
        session = event.data.object
        await handle_checkout_expired(session.id, db)

    return {"status": "ok"}