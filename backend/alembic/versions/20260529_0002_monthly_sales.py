"""create monthly sales table

Revision ID: 20260529_0002
Revises: 20260528_0001
Create Date: 2026-05-29
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260529_0002"
down_revision: str | None = "20260528_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "monthly_sales",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("sales_ht", sa.Numeric(12, 2), nullable=False),
        sa.Column("vat_collected", sa.Numeric(12, 2), nullable=False),
        sa.Column("sales_ttc", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("period_start", name="uq_monthly_sales_period"),
    )


def downgrade() -> None:
    op.drop_table("monthly_sales")
