"""add bank transaction categorization rules

Revision ID: 20260702_0008
Revises: 20260622_0007
Create Date: 2026-07-02
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260702_0008"
down_revision: str | None = "20260622_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "bank_transaction_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("pattern", sa.String(length=255), nullable=False),
        sa.Column("category_code", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pattern", name="uq_bank_transaction_rules_pattern"),
    )

    op.add_column(
        "bank_transactions",
        sa.Column("category_code", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "bank_transactions",
        sa.Column("category_source", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "bank_transactions",
        sa.Column("category_rule_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_bank_transactions_category_rule_id",
        "bank_transactions",
        "bank_transaction_rules",
        ["category_rule_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_bank_transactions_category_code",
        "bank_transactions",
        ["category_code"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_bank_transactions_category_code", table_name="bank_transactions"
    )
    op.drop_constraint(
        "fk_bank_transactions_category_rule_id",
        "bank_transactions",
        type_="foreignkey",
    )
    op.drop_column("bank_transactions", "category_rule_id")
    op.drop_column("bank_transactions", "category_source")
    op.drop_column("bank_transactions", "category_code")
    op.drop_table("bank_transaction_rules")
