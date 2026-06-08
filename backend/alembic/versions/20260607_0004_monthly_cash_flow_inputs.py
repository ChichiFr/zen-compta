"""create monthly cash flow inputs table

Revision ID: 20260607_0004
Revises: 20260602_0003
Create Date: 2026-06-07
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260607_0004"
down_revision: str | None = "20260602_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "monthly_cash_flow_inputs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("salaries", sa.Numeric(12, 2), nullable=False),
        sa.Column("social_charges", sa.Numeric(12, 2), nullable=False),
        sa.Column("investments_cash", sa.Numeric(12, 2), nullable=False),
        sa.Column("loan_repayments_cash", sa.Numeric(12, 2), nullable=False),
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
        sa.UniqueConstraint(
            "period_start",
            name="uq_monthly_cash_flow_inputs_period",
        ),
    )


def downgrade() -> None:
    op.drop_table("monthly_cash_flow_inputs")
