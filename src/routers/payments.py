from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.crud import payments as payments_crud
from src.database.models.accounts import UserModel
from src.database.models.orders import Order
from src.dependencies.auth import get_current_user
from src.dependencies.db import get_db
from src.payments.stripe_client import create_checkout_session
from src.schemas.payments import (
    PaymentInitiateResponse,
    PaymentDetailResponse,
    PaymentListItem,
)

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post(
    "/orders/{order_id}/pay",
    response_model=PaymentInitiateResponse,
    summary="Initiate payment for an order",
    description=(
        "Creates a Stripe Checkout session for the specified order. "
        "The order must be in PENDING status, belong to the current user, and have items with up-to-date prices. "
        "Returns a checkout URL to redirect the user to Stripe's payment page. "
        "The session expires after a set period — if not paid in time, the order can be retried."
    ),
    responses={
        200: {"description": "Checkout session created, redirect URL returned"},
        400: {"description": "Order is not payable (wrong status or price mismatch)"},
        403: {"description": "Order does not belong to current user"},
        404: {"description": "Order not found"},
        500: {"description": "Stripe error"},
        401: {"description": "Not authenticated"},
    },
)
async def initiate_payment(
    order_id: int,
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    order: Order | None = await db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    await payments_crud.validate_order_for_payment(db, order, user.id)

    payment = await payments_crud.create_payment(db, order, user.id)

    line_items = [
        {
            "price_data": {
                "currency": "usd",
                "product_data": {
                    "name": f"Order #{order.id}",
                    "description": f"{len(payment.items)} movie(s)",
                },
                "unit_amount": int(order.total_amount * 100),
            },
            "quantity": 1,
        }
    ]

    try:
        session = await create_checkout_session(
            order_id=order.id,
            payment_id=payment.id,
            amount=order.total_amount,
            customer_email=user.email,
            line_items=line_items,
        )
    except Exception as e:
        await db.delete(payment)
        await db.commit()
        raise HTTPException(500, f"Stripe error: {str(e)}")

    payment.external_payment_id = session.id

    return PaymentInitiateResponse(
        payment_id=payment.id,
        checkout_url=session.url,
        expires_at=session.expires_at,
    )


@router.get(
    "/{payment_id}",
    response_model=PaymentDetailResponse,
    summary="Get payment by ID",
    description=(
        "Returns detailed information about a specific payment. "
        "The payment must belong to the currently authenticated user."
    ),
    responses={
        200: {"description": "Payment details returned"},
        403: {"description": "Payment does not belong to current user"},
        404: {"description": "Payment not found"},
        401: {"description": "Not authenticated"},
    },
)
async def get_payment(
    payment_id: int,
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    payment = await payments_crud.get_payment_by_id(db, payment_id)

    if payment.user_id != user.id:
        raise HTTPException(403, "Not your payment")

    return payment


@router.get(
    "/",
    response_model=list[PaymentListItem],
    summary="Get my payments",
    description="Returns a list of all payments made by the currently authenticated user.",
    responses={
        200: {"description": "List of payments returned"},
        401: {"description": "Not authenticated"},
    },
)
async def get_my_payments(
    user: UserModel = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    payments = await payments_crud.get_user_payments(db, user.id)
    return [PaymentListItem.model_validate(p) for p in payments]


@router.get(
    "/payment-success",
    summary="Stripe payment success redirect",
    description=(
        "Landing page after a successful Stripe payment. "
        "Stripe redirects the user here with the session_id query parameter. "
        "Use GET /api/v1/orders to verify the order status."
    ),
    responses={
        200: {"description": "Payment success confirmation"},
    },
)
async def payment_success(session_id: str | None = None):
    return {
        "status": "success",
        "message": "Payment completed successfully",
        "session_id": session_id,
        "next_steps": "Check your email or GET /api/v1/orders to see your order",
    }


@router.get(
    "/payment-cancel",
    summary="Stripe payment cancel redirect",
    description=(
        "Landing page after a cancelled Stripe payment. "
        "Stripe redirects the user here if they close or cancel the checkout page."
    ),
    responses={
        200: {"description": "Payment cancellation confirmation"},
    },
)
async def payment_cancel():
    return {
        "status": "cancelled",
        "message": "Payment was cancelled",
        "next_steps": "Return to your cart and try again",
    }