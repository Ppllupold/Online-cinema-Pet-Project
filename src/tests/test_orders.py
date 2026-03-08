from decimal import Decimal

import pytest

from src.database.crud.payments import validate_order_for_payment
from src.database.models import Order
from src.database.models.orders import StatusEnum, OrderItem
from sqlalchemy import select

ORDERS_URL = "/api/v1/orders/"


@pytest.mark.asyncio
async def test_get_orders(auth_client, active_user_with_cart_items, db_session):
    orders = [
        Order(
            user_id=active_user_with_cart_items.id,
            total_amount=Decimal("10"),
            status=StatusEnum.PENDING.value,
        )
        for _ in range(5)
    ]
    db_session.add_all(orders)
    await db_session.flush()
    await db_session.refresh(active_user_with_cart_items, ["orders"])
    response = await auth_client.get(ORDERS_URL)
    assert response.status_code == 200
    assert len(response.json()) == len(orders)


@pytest.mark.asyncio
async def test_place_order(auth_client, active_user_with_cart_items, db_session):
    cart_items_count = len(active_user_with_cart_items.cart.cart_items)

    response = await auth_client.post(ORDERS_URL)
    assert response.status_code == 201

    order = await db_session.scalar(
        select(Order).where(Order.user_id == active_user_with_cart_items.id)
    )
    await db_session.refresh(order, ["order_items"])
    assert order is not None
    assert len(order.order_items) == cart_items_count

    await db_session.refresh(active_user_with_cart_items.cart, ["cart_items"])
    assert active_user_with_cart_items.cart.cart_items == []


@pytest.mark.asyncio
async def test_place_order_movie_exist_in_pending_order(
    auth_client, active_user_with_cart_items, db_session
):
    pending_order = Order(
        user_id=active_user_with_cart_items.id, status=StatusEnum.PENDING.value
    )
    db_session.add(pending_order)
    await db_session.flush()
    await db_session.refresh(pending_order)

    order_items = [
        OrderItem(
            order_id=pending_order.id,
            movie_id=item.movie_id,
            price_at_order=item.movie.price,
        )
        for item in active_user_with_cart_items.cart.cart_items
    ]
    db_session.add_all(order_items)
    await db_session.flush()
    await db_session.refresh(pending_order, ["order_items"])

    response = await auth_client.post(ORDERS_URL)
    assert response.status_code == 409
    assert (
        response.json()["detail"]
        == f"You have pending order #{pending_order.id} with some of these movies"
    )


@pytest.mark.asyncio
async def test_cancel_order_success(
    auth_client, active_user_with_cart_items, db_session
):
    pending_order = Order(
        user_id=active_user_with_cart_items.id, status=StatusEnum.PENDING.value
    )
    db_session.add(pending_order)
    await db_session.flush()
    await db_session.refresh(pending_order)
    response = await auth_client.post(f"{ORDERS_URL}{pending_order.id}/cancel")

    print(f"order user_id: {pending_order.user_id}")
    print(response.json())
    assert response.status_code == 200
    assert response.json()["message"] == "Order canceled"


@pytest.mark.asyncio
async def test_cancel_order_not_found(
    auth_client, active_user_with_cart_items, db_session
):
    response = await auth_client.post(f"{ORDERS_URL}100/cancel")
    assert response.status_code == 404
    assert response.json()["detail"] == "Order not found"
