from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class BankConnectionStatus(str, enum.Enum):
    CREATED = "created"
    LINKED = "linked"
    EXPIRED = "expired"
    REVOKED = "revoked"


class BankConnection(Base):
    __tablename__ = "bank_connections"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    external_requisition_id: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True
    )
    institution_id: Mapped[str] = mapped_column(String(100), nullable=False)
    institution_name: Mapped[str] = mapped_column(String(255), nullable=False)
    reference: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    status: Mapped[BankConnectionStatus] = mapped_column(
        Enum(
            BankConnectionStatus,
            name="bank_connection_status",
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
        default=BankConnectionStatus.CREATED,
        index=True,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    provider_session_data: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    accounts: Mapped[list[BankAccount]] = relationship(
        back_populates="connection",
        cascade="all, delete-orphan",
    )


class BankAccount(Base):
    __tablename__ = "bank_accounts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    connection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("bank_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    external_account_id: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True
    )
    iban_last4: Mapped[str | None] = mapped_column(String(4), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    connection: Mapped[BankConnection] = relationship(back_populates="accounts")
    transactions: Mapped[list[BankTransaction]] = relationship(
        back_populates="account",
        cascade="all, delete-orphan",
        order_by="BankTransaction.booking_date.desc()",
    )


class BankTransaction(Base):
    __tablename__ = "bank_transactions"
    __table_args__ = (
        UniqueConstraint(
            "account_id",
            "external_id",
            name="uq_bank_transactions_account_external",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("bank_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    booking_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    value_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    creditor_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    debtor_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    raw_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    account: Mapped[BankAccount] = relationship(back_populates="transactions")
