
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict

from src.database.models.orders import StatusEnum


class OrderItemShort(BaseModel):

    movie_name: str
    price: Decimal

    model_config = ConfigDict(from_attributes=True)


class OrderListItem(BaseModel):

    id: int
    created_at: datetime
    status: StatusEnum
    total_amount: Decimal
    order_items: list[OrderItemShort]

    model_config = ConfigDict(from_attributes=True)
