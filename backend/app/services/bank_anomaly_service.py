from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BankTransaction, Invoice, InvoiceStatus

RECENT_WINDOW_DAYS = 180


@dataclass(frozen=True)
class UnpaidInvoiceSummary:
    id: UUID
    supplier_name: str
    invoice_date: date | None
    invoice_number: str | None
    total_ttc: Decimal


@dataclass(frozen=True)
class BankAnomaliesSummary:
    unpaid_invoices_count: int


class BankAnomalyService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def summary(self) -> BankAnomaliesSummary:
        return BankAnomaliesSummary(
            unpaid_invoices_count=len(self.list_unpaid_invoices()),
        )

    def list_unpaid_invoices(self) -> list[UnpaidInvoiceSummary]:
        """Validated invoices in the last 6 months with no linked transaction."""
        cutoff = date.today() - timedelta(days=RECENT_WINDOW_DAYS)
        matched_ids = set(
            self.db.scalars(
                select(BankTransaction.matched_invoice_id).where(
                    BankTransaction.matched_invoice_id.is_not(None)
                )
            ).all()
        )
        invoices = self.db.scalars(
            select(Invoice)
            .where(
                Invoice.status == InvoiceStatus.VALIDATED,
                Invoice.invoice_date.is_not(None),
                Invoice.invoice_date >= cutoff,
            )
            .order_by(Invoice.invoice_date.desc())
        ).all()
        return [
            UnpaidInvoiceSummary(
                id=invoice.id,
                supplier_name=invoice.supplier_name,
                invoice_date=invoice.invoice_date,
                invoice_number=invoice.invoice_number,
                total_ttc=invoice.total_ttc,
            )
            for invoice in invoices
            if invoice.id not in matched_ids
        ]
