from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models import InvoiceSource, InvoiceStatus


class InvoiceLineInput(BaseModel):
    description: str = Field(min_length=1, max_length=1000)
    category: str | None = Field(default=None, max_length=120)
    vat_rate: Decimal = Field(ge=0, le=100)
    amount_ht: Decimal = Field(ge=0)
    amount_tva: Decimal | None = Field(default=None, ge=0)
    amount_ttc: Decimal | None = Field(default=None, ge=0)
    ai_confidence: Decimal | None = Field(default=None, ge=0, le=1)
    needs_review_reason: str | None = None


class InvoiceLineRead(BaseModel):
    id: UUID
    description: str
    category: str | None
    vat_rate: Decimal
    amount_ht: Decimal
    amount_tva: Decimal
    amount_ttc: Decimal
    needs_review_reason: str | None

    model_config = ConfigDict(from_attributes=True)


class InvoiceCreate(BaseModel):
    supplier_name: str = Field(min_length=1, max_length=255)
    invoice_date: date | None = None
    invoice_number: str | None = Field(default=None, max_length=100)
    source: InvoiceSource = InvoiceSource.MANUAL
    lines: list[InvoiceLineInput] = Field(default_factory=list)


class InvoiceRead(BaseModel):
    id: UUID
    supplier_name: str
    invoice_date: date | None
    invoice_number: str | None
    status: InvoiceStatus
    source: InvoiceSource
    total_ht: Decimal
    total_tva: Decimal
    total_ttc: Decimal
    lines: list[InvoiceLineRead]

    model_config = ConfigDict(from_attributes=True)
