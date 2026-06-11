from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class InvoiceStatus(str, enum.Enum):
    DRAFT = "draft"
    NEEDS_REVIEW = "needs_review"
    VALIDATED = "validated"
    ARCHIVED = "archived"


class InvoiceSource(str, enum.Enum):
    MANUAL = "manual"
    AI_UPLOAD = "ai_upload"


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    supplier_name: Mapped[str] = mapped_column(String(255), nullable=False)
    invoice_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    invoice_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(
            InvoiceStatus,
            name="invoice_status",
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
        default=InvoiceStatus.DRAFT,
        index=True,
    )
    source: Mapped[InvoiceSource] = mapped_column(
        Enum(
            InvoiceSource,
            name="invoice_source",
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
        default=InvoiceSource.MANUAL,
    )
    document_import_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("document_imports.id", ondelete="SET NULL"), nullable=True
    )
    total_ht: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total_tva: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0
    )
    total_ttc: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0
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

    lines: Mapped[list[InvoiceLine]] = relationship(
        back_populates="invoice",
        cascade="all, delete-orphan",
        order_by="InvoiceLine.position",
    )


class InvoiceLine(Base):
    __tablename__ = "invoice_lines"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(nullable=False, default=0)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    vat_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    amount_ht: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    amount_tva: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    amount_ttc: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    ai_confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    needs_review_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    invoice: Mapped[Invoice] = relationship(back_populates="lines")
