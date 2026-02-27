from sqlalchemy.ext.asyncio import AsyncSession

from src.database.crud import payments as payments_crud
from src.database.models.payments import PaymentStatusEnum
from src.services.email import send_payment_status


async def handle_checkout_completed(session_id: str, db: AsyncSession) -> None:

    payment = await payments_crud.get_payment_by_stripe_session(db, session_id)

    if not payment:
        print(f"Warning: Payment not found for session {session_id}")
        return

    await payments_crud.update_payment_status(db, payment, PaymentStatusEnum.SUCCESSFUL)

    await db.commit()

    await db.refresh(payment, ["order", "user"])
    await send_payment_status(
        to_email=payment.user.email,
        order_id=payment.order.id,
        amount=float(payment.amount),
        status="successful",
    )


async def handle_checkout_expired(session_id: str, db: AsyncSession) -> None:
    payment = await payments_crud.get_payment_by_stripe_session(db, session_id)

    if payment:
        await payments_crud.update_payment_status(
            db, payment, PaymentStatusEnum.CANCELED
        )
        await db.commit()

    await db.refresh(payment, ["order", "user"])
    await send_payment_status(
        to_email=payment.user.email,
        order_id=payment.order.id,
        amount=float(payment.amount),
        status="failed",
    )
