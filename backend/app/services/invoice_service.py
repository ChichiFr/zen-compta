import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Invoice, InvoiceLine, InvoiceStatus
from app.schemas.invoice import InvoiceCreate
from app.services.invoice_calculations import (
    InvoiceLineDraft,
    InvoiceValidationInput,
    calculate_line,
    calculate_totals,
    validation_errors,
)
from app.services.periods import month_start, next_month_start


class InvoiceNotFoundError(Exception):
    pass


class InvoiceValidationError(Exception):
    def __init__(self, errors: list[str]) -> None:
        super().__init__(", ".join(errors))
        self.errors = errors


class InvoiceService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_invoice(self, payload: InvoiceCreate) -> Invoice:
        calculated_lines = [
            calculate_line(
                InvoiceLineDraft(
                    description=line.description,
                    vat_rate=line.vat_rate,
                    amount_ht=line.amount_ht,
                    amount_tva=line.amount_tva,
                    amount_ttc=line.amount_ttc,
                    needs_review_reason=line.needs_review_reason,
                )
            )
            for line in payload.lines
        ]
        totals = calculate_totals(calculated_lines)
        status = (
            InvoiceStatus.NEEDS_REVIEW
            if any(line.needs_review_reason for line in calculated_lines)
            else InvoiceStatus.DRAFT
        )

        invoice = Invoice(
            supplier_name=payload.supplier_name.strip(),
            invoice_date=payload.invoice_date,
            invoice_number=payload.invoice_number,
            source=payload.source,
            status=status,
            total_ht=totals.total_ht,
            total_tva=totals.total_tva,
            total_ttc=totals.total_ttc,
        )

        invoice.lines = [
            InvoiceLine(
                position=index,
                description=line.description,
                category=payload.lines[index].category,
                vat_rate=line.vat_rate,
                amount_ht=line.amount_ht,
                amount_tva=line.amount_tva,
                amount_ttc=line.amount_ttc,
                ai_confidence=payload.lines[index].ai_confidence,
                needs_review_reason=line.needs_review_reason,
            )
            for index, line in enumerate(calculated_lines)
        ]

        self.db.add(invoice)
        self.db.commit()
        return self.get_invoice(invoice.id)

    def list_invoices(self, period_start: date | None = None) -> list[Invoice]:
        statement = (
            select(Invoice)
            .options(selectinload(Invoice.lines))
            .where(Invoice.status != InvoiceStatus.ARCHIVED)
        )
        if period_start is not None:
            start = month_start(period_start)
            end = next_month_start(start)
            statement = statement.where(
                Invoice.invoice_date >= start,
                Invoice.invoice_date < end,
            )
        statement = statement.order_by(Invoice.created_at.desc())
        return list(self.db.scalars(statement).all())

    def get_invoice(self, invoice_id: uuid.UUID) -> Invoice:
        statement = (
            select(Invoice)
            .options(selectinload(Invoice.lines))
            .where(Invoice.id == invoice_id)
        )
        invoice = self.db.scalar(statement)
        if invoice is None:
            raise InvoiceNotFoundError(str(invoice_id))
        return invoice

    def validate_invoice(self, invoice_id: uuid.UUID) -> Invoice:
        invoice = self.get_invoice(invoice_id)
        errors = validation_errors(
            InvoiceValidationInput(
                supplier_name=invoice.supplier_name,
                invoice_date_present=invoice.invoice_date is not None,
                lines=[
                    calculate_line(
                        InvoiceLineDraft(
                            description=line.description,
                            vat_rate=line.vat_rate,
                            amount_ht=line.amount_ht,
                            amount_tva=line.amount_tva,
                            amount_ttc=line.amount_ttc,
                            needs_review_reason=line.needs_review_reason,
                        )
                    )
                    for line in invoice.lines
                ],
                status=invoice.status,
            )
        )
        if errors:
            raise InvoiceValidationError(errors)

        invoice.status = InvoiceStatus.VALIDATED
        self.db.commit()
        return self.get_invoice(invoice.id)
