"""add bank integration tables

Revision ID: 20260622_0006
Revises: 20260611_0005
Create Date: 2026-06-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260622_0006"
down_revision: str | None = "20260611_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bank_connection_status = postgresql.ENUM(
        "created",
        "linked",
        "expired",
        "revoked",
        name="bank_connection_status",
        create_type=False,
    )
    postgresql.ENUM(
        "created",
        "linked",
        "expired",
        "revoked",
        name="bank_connection_status",
    ).create(op.get_bind(), checkfirst=True)

    op.create_table(
        "bank_connections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("external_requisition_id", sa.String(length=100), nullable=False),
        sa.Column("institution_id", sa.String(length=100), nullable=False),
        sa.Column("institution_name", sa.String(length=255), nullable=False),
        sa.Column("reference", sa.String(length=100), nullable=False),
        sa.Column("status", bank_connection_status, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.UniqueConstraint("external_requisition_id"),
        sa.UniqueConstraint("reference"),
    )
    op.create_index("ix_bank_connections_provider", "bank_connections", ["provider"])
    op.create_index("ix_bank_connections_status", "bank_connections", ["status"])

    op.create_table(
        "bank_accounts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("connection_id", sa.Uuid(), nullable=False),
        sa.Column("external_account_id", sa.String(length=100), nullable=False),
        sa.Column("iban_last4", sa.String(length=4), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["connection_id"], ["bank_connections.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_account_id"),
    )
    op.create_index(
        "ix_bank_accounts_connection_id", "bank_accounts", ["connection_id"]
    )

    op.create_table(
        "bank_transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("booking_date", sa.Date(), nullable=False),
        sa.Column("value_date", sa.Date(), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("creditor_name", sa.String(length=255), nullable=True),
        sa.Column("debtor_name", sa.String(length=255), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["account_id"], ["bank_accounts.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "account_id",
            "external_id",
            name="uq_bank_transactions_account_external",
        ),
    )
    op.create_index(
        "ix_bank_transactions_account_id", "bank_transactions", ["account_id"]
    )
    op.create_index(
        "ix_bank_transactions_booking_date", "bank_transactions", ["booking_date"]
    )


def downgrade() -> None:
    op.drop_index("ix_bank_transactions_booking_date", table_name="bank_transactions")
    op.drop_index("ix_bank_transactions_account_id", table_name="bank_transactions")
    op.drop_table("bank_transactions")
    op.drop_index("ix_bank_accounts_connection_id", table_name="bank_accounts")
    op.drop_table("bank_accounts")
    op.drop_index("ix_bank_connections_status", table_name="bank_connections")
    op.drop_index("ix_bank_connections_provider", table_name="bank_connections")
    op.drop_table("bank_connections")
    sa.Enum(name="bank_connection_status").drop(op.get_bind(), checkfirst=True)
