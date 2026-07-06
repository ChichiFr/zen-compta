"""link bank transactions to invoices

Revision ID: 20260702_0009
Revises: 20260702_0008
Create Date: 2026-07-02
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260702_0009"
down_revision: str | None = "20260702_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "bank_transactions",
        sa.Column("matched_invoice_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "bank_transactions",
        sa.Column("match_source", sa.String(length=20), nullable=True),
    )
    op.create_foreign_key(
        "fk_bank_transactions_matched_invoice_id",
        "bank_transactions",
        "invoices",
        ["matched_invoice_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_bank_transactions_matched_invoice_id",
        "bank_transactions",
        ["matched_invoice_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_bank_transactions_matched_invoice_id", table_name="bank_transactions"
    )
    op.drop_constraint(
        "fk_bank_transactions_matched_invoice_id",
        "bank_transactions",
        type_="foreignkey",
    )
    op.drop_column("bank_transactions", "match_source")
    op.drop_column("bank_transactions", "matched_invoice_id")
