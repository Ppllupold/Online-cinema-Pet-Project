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


@router.post("/orders/{order_id}/pay", response_model=PaymentInitiateResponse)
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


@router.get("/payments/{payment_id}", response_model=PaymentDetailResponse)
async def get_payment(
    payment_id: int,
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

    payment = await payments_crud.get_payment_by_id(db, payment_id)

    if payment.user_id != user.id:
        raise HTTPException(403, "Not your payment")

    return payment


@router.get("/payments", response_model=list[PaymentListItem])
async def get_my_payments(
    user: UserModel = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):

    payments = await payments_crud.get_user_payments(db, user.id)
    return [PaymentListItem.model_validate(p) for p in payments]


@router.get("/payment-success")
async def payment_success(session_id: str | None = None):
    return {
        "status": "success",
        "message": "Payment completed successfully",
        "session_id": session_id,
        "next_steps": "Check your email or GET /api/v1/orders to see your order"
    }


@router.get("/payment-cancel")
async def payment_cancel():
    return {
        "status": "cancelled",
        "message": "Payment was cancelled",
        "next_steps": "Return to your cart and try again"
    }
