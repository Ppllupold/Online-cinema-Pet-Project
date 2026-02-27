
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from src.database.models.payments import Payment, PaymentItem, PaymentStatusEnum
from src.database.models.orders import Order, StatusEnum


async def validate_order_for_payment(
    db: AsyncSession, order: Order, user_id: int
) -> None:

    if order.user_id != user_id:
        raise HTTPException(403, "Not your order")

    if order.status != StatusEnum.PENDING:
        raise HTTPException(400, f"Order is {order.status.value}, cannot be paid")

    if not order.order_items:
        raise HTTPException(400, "Order has no items")

    current_total = Decimal(0)
    for item in order.order_items:
        current_price = item.movie.price

        if current_price != item.price_at_order:
            raise HTTPException(
                400,
                f"Price changed for '{item.movie.name}': "
                f"was ${item.price_at_order}, now ${current_price}. "
                f"Please create a new order.",
            )

        current_total += item.price_at_order

    if current_total != order.total_amount:
        raise HTTPException(
            400,
            f"Order total mismatch: expected ${order.total_amount}, "
            f"calculated ${current_total}",
        )


async def create_payment(db: AsyncSession, order: Order, user_id: int) -> Payment:

    payment = Payment(
        user_id=user_id,
        order_id=order.id,
        amount=order.total_amount,
        status=PaymentStatusEnum.PENDING,
    )
    db.add(payment)
    await db.flush()

    for order_item in order.order_items:
        payment_item = PaymentItem(
            payment_id=payment.id,
            order_item_id=order_item.id,
            price_at_payment=order_item.price_at_order,
        )
        db.add(payment_item)

    await db.flush()
    await db.refresh(payment, ["items"])

    return payment


async def get_payment_by_id(db: AsyncSession, payment_id: int) -> Payment:
    payment = await db.get(Payment, payment_id)
    if not payment:
        raise HTTPException(404, "Payment not found")
    return payment


async def get_payment_by_stripe_session(
    db: AsyncSession, session_id: str
) -> Payment | None:
    payment = await db.scalar(
        select(Payment).where(Payment.external_payment_id == session_id)
    )
    return payment


async def update_payment_status(
    db: AsyncSession, payment: Payment, status: PaymentStatusEnum
) -> Payment:

    payment.status = status

    if status == PaymentStatusEnum.SUCCESSFUL:
        payment.order.status = StatusEnum.PAID
    elif status == PaymentStatusEnum.CANCELED:
        payment.order.status = StatusEnum.CANCELED

    await db.flush()
    await db.refresh(payment)
    return payment


async def get_user_payments(db: AsyncSession, user_id: int) -> list[Payment]:
    payments = await db.scalars(
        select(Payment)
        .where(Payment.user_id == user_id)
        .order_by(Payment.created_at.desc())
    )
    return list(payments.all())
