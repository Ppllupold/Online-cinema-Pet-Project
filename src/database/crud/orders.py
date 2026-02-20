from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from src.database.crud.shopping import clear_cart
from src.database.models import Order, Cart, OrderItem, MovieModel
from src.database.models.orders import StatusEnum
from src.schemas.orders import OrderListItem, OrderItemShort

# crud/orders.py


async def get_orders(user_id: int, db: AsyncSession) -> list[OrderListItem]:
    orders = (await db.scalars(select(Order).where(Order.user_id == user_id))).all()

    return [
        OrderListItem(
            created_at=order.created_at,
            status=order.status,
            total_amount=order.total_amount,
            items=[
                OrderItemShort(movie_name=item.movie.name, price=item.price_at_order)
                for item in order.order_items
            ],
        )
        for order in orders
    ]


async def place_order(cart: Cart, db: AsyncSession) -> Order:

    await _validate_order(cart, db)

    total_amount = Decimal(sum(cart_item.movie.price for cart_item in cart.cart_items))

    order = Order(
        user_id=cart.user_id, total_amount=total_amount, status=StatusEnum.PENDING
    )
    db.add(order)
    await db.flush()

    order_items = [
        OrderItem(
            order_id=order.id,
            movie_id=cart_item.movie_id,
            price_at_order=cart_item.movie.price,
        )
        for cart_item in cart.cart_items
    ]
    db.add_all(order_items)

    await clear_cart(cart, db)

    await db.flush()
    await db.refresh(order)

    return order


async def _validate_order(cart: Cart, db: AsyncSession) -> None:
    if not cart.cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    movie_ids = [item.movie_id for item in cart.cart_items]
    movies = await db.scalars(select(MovieModel).where(MovieModel.id.in_(movie_ids)))
    if len(movies.all()) != len(movie_ids):
        raise HTTPException(400, "Some movies no longer available")

    existing_pending = await db.scalar(
        select(Order)
        .join(OrderItem)
        .where(
            Order.user_id == cart.user_id,
            Order.status == StatusEnum.PENDING,
            OrderItem.movie_id.in_(movie_ids),
        )
        .limit(1)
    )

    if existing_pending:
        raise HTTPException(
            409,
            f"You have pending order #{existing_pending.id} with some of these movies",
        )
