"""create invoice domain tables

Revision ID: 20260528_0001
Revises:
Create Date: 2026-05-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260528_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    invoice_status = postgresql.ENUM(
        "draft",
        "needs_review",
        "validated",
        "archived",
        name="invoice_status",
        create_type=False,
    )
    invoice_source = postgresql.ENUM(
        "manual", "ai_upload", name="invoice_source", create_type=False
    )
    postgresql.ENUM(
        "draft",
        "needs_review",
        "validated",
        "archived",
        name="invoice_status",
    ).create(op.get_bind(), checkfirst=True)
    postgresql.ENUM(
        "manual", "ai_upload", name="invoice_source"
    ).create(op.get_bind(), checkfirst=True)

    op.create_table(
        "invoices",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("supplier_name", sa.String(length=255), nullable=False),
        sa.Column("invoice_date", sa.Date(), nullable=True),
        sa.Column("invoice_number", sa.String(length=100), nullable=True),
        sa.Column("status", invoice_status, nullable=False),
        sa.Column("source", invoice_source, nullable=False),
        sa.Column("document_import_id", sa.Uuid(), nullable=True),
        sa.Column("total_ht", sa.Numeric(12, 2), nullable=False),
        sa.Column("total_tva", sa.Numeric(12, 2), nullable=False),
        sa.Column("total_ttc", sa.Numeric(12, 2), nullable=False),
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
    )
    op.create_table(
        "invoice_lines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=120), nullable=True),
        sa.Column("vat_rate", sa.Numeric(5, 2), nullable=False),
        sa.Column("amount_ht", sa.Numeric(12, 2), nullable=False),
        sa.Column("amount_tva", sa.Numeric(12, 2), nullable=False),
        sa.Column("amount_ttc", sa.Numeric(12, 2), nullable=False),
        sa.Column("ai_confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("needs_review_reason", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_invoice_lines_invoice_id", "invoice_lines", ["invoice_id"])


def downgrade() -> None:
    op.drop_index("ix_invoice_lines_invoice_id", table_name="invoice_lines")
    op.drop_table("invoice_lines")
    op.drop_table("invoices")
    sa.Enum(name="invoice_source").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="invoice_status").drop(op.get_bind(), checkfirst=True)
