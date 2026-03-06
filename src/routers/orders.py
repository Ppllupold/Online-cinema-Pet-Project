# src/routers/orders.py

from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies.db import get_db
from src.database.models import Cart, Order
from src.database.models.accounts import UserModel
from src.dependencies.auth import get_current_user, get_current_user_cart
from src.database.crud import orders as orders_crud
from src.schemas.orders import OrderListItem, OrderItemShort

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.get("/", response_model=list[OrderListItem])
async def get_my_orders(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    orders = await orders_crud.get_orders(current_user.id, db)
    return [OrderListItem.model_validate(order) for order in orders]


@router.post("/", response_model=OrderListItem, status_code=status.HTTP_201_CREATED)
async def place_order(
    cart: Cart = Depends(get_current_user_cart), db: AsyncSession = Depends(get_db)
):
    order = await orders_crud.place_order(cart, db)
    return order


@router.post("/{order_id}/cancel", status_code=status.HTTP_200_OK)
async def cancel_order(
    order_id: int,
    cart: Cart = Depends(get_current_user_cart),
    db: AsyncSession = Depends(get_db),
):
    await orders_crud.cancel_order(order_id, cart, db)
    return {"message": "Order canceled"}
