# src/schemas/payments.py

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, HttpUrl, computed_field

from src.database.models.payments import PaymentStatusEnum


class PaymentInitiateResponse(BaseModel):

    payment_id: int
    checkout_url: HttpUrl
    expires_at: datetime


class PaymentItemDetail(BaseModel):

    id: int
    price_at_payment: Decimal

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def movie_name(self) -> str:
        return self.order_item.movie.name if hasattr(self, "order_item") else "Unknown"


class PaymentDetailResponse(BaseModel):

    id: int
    order_id: int
    amount: Decimal
    status: PaymentStatusEnum
    created_at: datetime
    external_payment_id: str | None = None

    items: list[PaymentItemDetail] = []

    model_config = ConfigDict(from_attributes=True)


class PaymentListItem(BaseModel):

    id: int
    order_id: int
    amount: Decimal
    status: PaymentStatusEnum
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
