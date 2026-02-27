from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    CheckConstraint,
    Index,
    func,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database.models.base import Base

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.database.models.accounts import UserModel
    from src.database.models.orders import Order, OrderItem


class PaymentStatusEnum(str, Enum):
    PENDING = "PENDING"
    SUCCESSFUL = "successful"
    CANCELED = "canceled"
    REFUNDED = "refunded"


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    status: Mapped[PaymentStatusEnum] = mapped_column(
        SQLEnum(PaymentStatusEnum, name="payment_status_enum"),
        nullable=False,
        server_default="pending",
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    external_payment_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        index=True,
    )

    user: Mapped["UserModel"] = relationship(
        "UserModel",
        back_populates="payments",
        lazy="selectin",
    )

    order: Mapped["Order"] = relationship(
        "Order",
        back_populates="payments",
        lazy="selectin",
    )

    items: Mapped[list["PaymentItem"]] = relationship(
        "PaymentItem",
        back_populates="payment",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_payments_amount_nonneg"),
        Index("ix_payments_user_order", "user_id", "order_id"),
    )


class PaymentItem(Base):
    __tablename__ = "payment_items"

    id: Mapped[int] = mapped_column(primary_key=True)

    payment_id: Mapped[int] = mapped_column(
        ForeignKey("payments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    order_item_id: Mapped[int] = mapped_column(
        ForeignKey("order_items.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    price_at_payment: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    payment: Mapped["Payment"] = relationship(
        "Payment",
        back_populates="items",
        lazy="selectin",
    )

    order_item: Mapped["OrderItem"] = relationship(
        "OrderItem",
        back_populates="payment_items",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint("price_at_payment >= 0", name="ck_payment_items_price_nonneg"),
        UniqueConstraint(
            "payment_id", "order_item_id", name="uq_payment_items_payment_order_item"
        ),
    )
