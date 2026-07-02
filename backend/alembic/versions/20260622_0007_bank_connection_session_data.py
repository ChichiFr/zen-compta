"""add bank connection provider session data

Revision ID: 20260622_0007
Revises: 20260622_0006
Create Date: 2026-06-22
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260622_0007"
down_revision: str | None = "20260622_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "bank_connections",
        sa.Column(
            "provider_session_data",
            sa.JSON(),
            nullable=False,
            server_default="{}",
        ),
    )


def downgrade() -> None:
    op.drop_column("bank_connections", "provider_session_data")
