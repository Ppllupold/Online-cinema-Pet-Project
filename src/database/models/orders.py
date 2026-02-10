from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, func, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Enum as SQLEnum

from src.database.models.base import Base

if TYPE_CHECKING:
    from src.database.models.accounts import UserModel
    from src.database.models.payments import Payment, PaymentItem


class StatusEnum(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    CANCELED = "canceled"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user: Mapped["UserModel"] = relationship(
        "UserModel",
        back_populates="orders",
        lazy="selectin",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    status: Mapped[StatusEnum] = mapped_column(
        SQLEnum(StatusEnum),
        nullable=False,
        server_default="PENDING",
    )

    total_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2, asdecimal=True),
        nullable=True,
    )

    order_items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        single_parent=True,
        lazy="selectin",
        passive_deletes=True,
    )

    payments: Mapped[list["Payment"]] = relationship(
        "Payment",
        back_populates="order",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<Order id={self.id} user_id={self.user_id} "
            f"status={self.status} total_amount={self.total_amount} created_at={self.created_at}>"
        )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)

    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order: Mapped["Order"] = relationship(
        "Order",
        back_populates="order_items",
        lazy="selectin",
    )

    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    movie: Mapped["MovieModel"] = relationship(
        "MovieModel",
    )

    price_at_order: Mapped[Decimal] = mapped_column(
        Numeric(10, 2, asdecimal=True),
        nullable=False,
    )

    payment_items: Mapped[list["PaymentItem"]] = relationship(
        "PaymentItem",
        back_populates="order_item",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<OrderItem id={self.id} order_id={self.order_id} "
            f"movie_id={self.movie_id} price_at_order={self.price_at_order}>"
        )
