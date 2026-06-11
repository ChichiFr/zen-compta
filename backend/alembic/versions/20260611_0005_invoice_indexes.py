"""add indexes on invoices date and status

Revision ID: 20260611_0005
Revises: 20260607_0004
Create Date: 2026-06-11
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260611_0005"
down_revision: str | None = "20260607_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_invoices_invoice_date", "invoices", ["invoice_date"])
    op.create_index("ix_invoices_status", "invoices", ["status"])


def downgrade() -> None:
    op.drop_index("ix_invoices_status", table_name="invoices")
    op.drop_index("ix_invoices_invoice_date", table_name="invoices")
