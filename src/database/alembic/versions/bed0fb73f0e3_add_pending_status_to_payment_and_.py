"""add pending status to payment and configure server defaults

Revision ID: bed0fb73f0e3
Revises: 482ded8c5296
Create Date: 2026-02-23 18:14:36.984988

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bed0fb73f0e3'
down_revision: Union[str, Sequence[str], None] = '482ded8c5296'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add PENDING value to payment_status_enum"""

    # Крок 1: Додати нове значення в enum
    # Використовуємо окрему транзакцію
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE payment_status_enum ADD VALUE IF NOT EXISTS 'pending'")

    # Крок 2: Тепер можна використати нове значення
    op.alter_column(
        'payments',
        'status',
        server_default='pending'
    )


def downgrade() -> None:
    """Revert default to successful"""

    # Повернути default
    op.alter_column(
        'payments',
        'status',
        server_default='successful'
    )

    # NOTE: PostgreSQL НЕ дозволяє видаляти enum values
