from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Cart, MovieModel, CartItem, OrderItem
from src.database.models.orders import StatusEnum, Order
from src.schemas.shopping import CartResponse, CartMovieItem


async def add_movie_to_cart(movie_id: int, db: AsyncSession, cart: Cart):
    movie = db.get(MovieModel, MovieModel.id == movie_id)
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found"
        )
    existing = await db.scalar(
        select(CartItem).where(
            CartItem.cart_id == cart.id, CartItem.movie_id == movie_id
        )
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Movie already in cart"
        )
    if await check_movie_purchased(movie_id, cart.user_id, db):
        raise HTTPException(409, "Movie already purchased")

    cart_item = CartItem(
        cart_id=cart.id,
        movie_id=movie_id,
    )
    db.add(cart_item)
    await db.flush()
    await db.refresh(cart_item)
    return cart_item


async def remove_movie_from_cart(movie_id: int, db: AsyncSession, cart: Cart) -> None:
    cart_item = await db.scalar(
        select(CartItem).where(
            CartItem.cart_id == cart.id, CartItem.movie_id == movie_id
        )
    )
    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Movie not in cart"
        )
    await db.delete(cart_item)
    await db.flush()


async def clear_cart(cart: Cart, db: AsyncSession) -> None:
    for item in cart.cart_items:
        await db.delete(item)
    await db.flush()


async def get_cart_items(db: AsyncSession, cart: Cart) -> CartResponse:

    if not cart.cart_items:
        return CartResponse(items=[], total_price=Decimal("0"), total_items=0)
    items = []
    for cart_item in cart.cart_items:
        item_data = {
            **cart_item.movie.__dict__,
            "added_at": cart_item.added_at,
        }
        items.append(CartMovieItem(**item_data))
    total_price = sum(item.price for item in items)

    return CartResponse(items=items, total_price=total_price, total_items=len(items))


async def check_movie_purchased(movie_id: int, user_id: int, db: AsyncSession) -> bool:
    order_item = await db.scalar(
        select(OrderItem)
        .join(Order)
        .where(
            OrderItem.movie_id == movie_id,
            Order.user_id == user_id,
            Order.status == StatusEnum.PAID,
        )
        .limit(1)
    )

    return order_item is not None
