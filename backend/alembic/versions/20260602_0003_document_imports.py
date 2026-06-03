"""create document imports table

Revision ID: 20260602_0003
Revises: 20260529_0002
Create Date: 2026-06-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260602_0003"
down_revision: str | None = "20260529_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    document_import_status = postgresql.ENUM(
        "uploaded",
        "extraction_pending",
        "extraction_failed",
        "extraction_completed",
        name="document_import_status",
        create_type=False,
    )
    postgresql.ENUM(
        "uploaded",
        "extraction_pending",
        "extraction_failed",
        "extraction_completed",
        name="document_import_status",
    ).create(op.get_bind(), checkfirst=True)

    op.create_table(
        "document_imports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("status", document_import_status, nullable=False),
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
    op.create_index(
        "ix_invoices_document_import_id",
        "invoices",
        ["document_import_id"],
    )
    op.create_foreign_key(
        "fk_invoices_document_import_id",
        "invoices",
        "document_imports",
        ["document_import_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_invoices_document_import_id",
        "invoices",
        type_="foreignkey",
    )
    op.drop_index("ix_invoices_document_import_id", table_name="invoices")
    op.drop_table("document_imports")
    sa.Enum(name="document_import_status").drop(op.get_bind(), checkfirst=True)
