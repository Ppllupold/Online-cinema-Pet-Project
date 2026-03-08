from unittest.mock import patch, AsyncMock
from types import SimpleNamespace
from datetime import datetime
from sqlalchemy import select

import pytest

from src.database.crud.payments import create_payment
from src.database.models import Payment, UserModel
from src.database.models.payments import PaymentStatusEnum

INITIATE_PAYMENT = "/api/v1/payments/orders/"
PAYMENTS_CRUD = "/api/v1/payments/"
WEBHOOK = "/api/v1/webhooks/stripe"


@pytest.mark.asyncio
async def test_initiate_payment(
    db_session, auth_client, active_user_with_cart_items, create_valid_order
):
    with patch(
        "src.routers.payments.create_checkout_session", new_callable=AsyncMock
    ) as stripe_mock:
        stripe_mock.return_value = SimpleNamespace(
            id="cs_test_123",
            url="https://stripe.com/pay/xxx",
            expires_at=datetime(2011, 11, 11, 11, 11, 11),
        )
        response = await auth_client.post(
            f"{INITIATE_PAYMENT}{create_valid_order.id}/pay"
        )
        assert response.status_code == 200
        stripe_mock.assert_called_once()

        payment: Payment = await db_session.scalar(
            select(Payment).where(
                Payment.order_id == create_valid_order.id,
                Payment.user_id == active_user_with_cart_items.id,
            )
        )
        assert payment is not None
        assert payment.external_payment_id == stripe_mock.return_value.id
        assert payment.items is not None
        assert len(payment.items) == len(create_valid_order.order_items)


@pytest.mark.asyncio
async def test_get_payment(
    db_session, auth_client, active_user_with_cart_items, create_valid_order
):
    payment = await create_payment(
        db_session, create_valid_order, active_user_with_cart_items.id
    )
    response = await auth_client.get(f"{PAYMENTS_CRUD}{payment.id}")
    assert response.status_code == 200
    assert payment.user_id == active_user_with_cart_items.id


@pytest.mark.asyncio
async def test_get_payment_wrong_user(
    db_session, auth_client, active_user_with_cart_items, create_valid_order
):
    new_us = UserModel.create(
        email="email@gmail.com", raw_password="rjsfuhasdo#@859SCSNoak1Y@$Hf", group_id=1
    )
    db_session.add(new_us)
    await db_session.flush()
    await db_session.refresh(new_us)

    payment = await create_payment(db_session, create_valid_order, new_us.id)
    response = await auth_client.get(f"{PAYMENTS_CRUD}{payment.id}")
    assert response.status_code == 403


@pytest.mark.parametrize(
    ("type", "status"),
    [
        ("checkout.session.completed", PaymentStatusEnum.SUCCESSFUL),
        ("checkout.session.expired", PaymentStatusEnum.CANCELED),
    ],
)
@pytest.mark.asyncio
async def test_stripe_webhook(
    auth_client,
    active_user_with_cart_items,
    create_valid_order,
    db_session,
    type,
    status,
):
    auth_client.headers["stripe-signature"] = "SUPER_STRIPE_HEADER"
    payment = await create_payment(
        db_session, create_valid_order, active_user_with_cart_items.id
    )
    payment.external_payment_id = "cs_test_123"
    await db_session.flush()
    with patch("src.routers.webhooks.construct_webhook_event") as webhook_mock:
        webhook_mock.return_value = SimpleNamespace(
            type=type,
            data=SimpleNamespace(object=SimpleNamespace(id="cs_test_123")),
        )
        with patch(
            "src.payments.webhook_handlers.send_payment_status", new_callable=AsyncMock
        ) as email_mock:
            email_mock.return_value = True
            response = await auth_client.post(f"{WEBHOOK}")
            print(response.json())
            assert response.status_code == 200
            assert payment.status == status
            email_mock.assert_called_once()
