from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies.db import get_db
from src.database.models import Cart, Order
from src.database.models.accounts import UserModel
from src.dependencies.auth import get_current_user, get_current_user_cart
from src.database.crud import orders as orders_crud
from src.schemas.orders import OrderListItem, OrderItemShort

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.get(
    "/",
    response_model=list[OrderListItem],
    summary="Get my orders",
    description=(
        "Returns a list of all orders placed by the currently authenticated user. "
        "Includes order status, total amount, and items for each order."
    ),
    responses={
        200: {"description": "List of orders returned"},
        401: {"description": "Not authenticated"},
    },
)
async def get_my_orders(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    orders = await orders_crud.get_orders(current_user.id, db)
    return [OrderListItem.model_validate(order) for order in orders]


@router.post(
    "/",
    response_model=OrderListItem,
    status_code=status.HTTP_201_CREATED,
    summary="Place an order from cart",
    description=(
        "Creates a new order from the current user's cart. "
        "The cart must not be empty. "
        "Prices are captured at the time of order creation. "
        "The cart is cleared after a successful order."
    ),
    responses={
        201: {"description": "Order placed successfully"},
        400: {"description": "Cart is empty"},
        401: {"description": "Not authenticated"},
    },
)
async def place_order(
    cart: Cart = Depends(get_current_user_cart), db: AsyncSession = Depends(get_db)
):
    order = await orders_crud.place_order(cart, db)
    return order


@router.post(
    "/{order_id}/cancel",
    status_code=status.HTTP_200_OK,
    summary="Cancel an order",
    description=(
        "Cancels a pending order by ID. "
        "Only orders with PENDING status can be cancelled. "
        "The order must belong to the currently authenticated user."
    ),
    responses={
        200: {"description": "Order cancelled successfully"},
        400: {"description": "Order cannot be cancelled (wrong status)"},
        403: {"description": "Order does not belong to current user"},
        404: {"description": "Order not found"},
        401: {"description": "Not authenticated"},
    },
)
async def cancel_order(
    order_id: int,
    cart: Cart = Depends(get_current_user_cart),
    db: AsyncSession = Depends(get_db),
):
    await orders_crud.cancel_order(order_id, cart, db)
    return {"message": "Order canceled"}