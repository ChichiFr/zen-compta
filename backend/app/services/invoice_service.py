import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Invoice, InvoiceLine, InvoiceStatus
from app.schemas.invoice import InvoiceCreate, InvoiceUpdate
from app.services.invoice_calculations import (
    InvoiceLineDraft,
    InvoiceValidationInput,
    calculate_line,
    calculate_totals,
    validation_errors,
)
from app.services.periods import month_start, next_month_start
from app.services.tabular_exports import write_csv, write_xlsx


class InvoiceNotFoundError(Exception):
    pass


class InvoiceValidationError(Exception):
    def __init__(self, errors: list[str]) -> None:
        super().__init__(", ".join(errors))
        self.errors = errors


class InvoiceLockedError(Exception):
    pass


INVOICE_EXPORT_HEADERS = [
    "invoice_date",
    "supplier_name",
    "invoice_number",
    "status",
    "line_position",
    "line_description",
    "category",
    "vat_rate",
    "line_ht",
    "line_tva",
    "line_ttc",
    "invoice_total_ht",
    "invoice_total_tva",
    "invoice_total_ttc",
]


class InvoiceService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_invoice(self, payload: InvoiceCreate) -> Invoice:
        return self._save_invoice(payload)

    def update_invoice(self, invoice_id: uuid.UUID, payload: InvoiceUpdate) -> Invoice:
        invoice = self.get_invoice(invoice_id)
        if invoice.status == InvoiceStatus.VALIDATED:
            raise InvoiceLockedError("validated_invoice_cannot_be_edited")
        if invoice.status == InvoiceStatus.ARCHIVED:
            raise InvoiceLockedError("archived_invoice_cannot_be_edited")

        return self._save_invoice(payload, invoice=invoice)

    def _save_invoice(
        self,
        payload: InvoiceCreate | InvoiceUpdate,
        invoice: Invoice | None = None,
    ) -> Invoice:
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

        if invoice is None:
            invoice = Invoice()
            self.db.add(invoice)
            if isinstance(payload, InvoiceCreate):
                invoice.source = payload.source

        invoice.supplier_name = payload.supplier_name.strip()
        invoice.invoice_date = payload.invoice_date
        invoice.invoice_number = payload.invoice_number
        invoice.status = status
        invoice.total_ht = totals.total_ht
        invoice.total_tva = totals.total_tva
        invoice.total_ttc = totals.total_ttc

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

    def export_csv(self, period_start: date) -> str:
        return write_csv(
            INVOICE_EXPORT_HEADERS,
            self.export_rows(period_start=period_start),
        )

    def export_xlsx(self, period_start: date) -> bytes:
        return write_xlsx(
            "Invoices",
            INVOICE_EXPORT_HEADERS,
            self.export_rows(period_start=period_start),
        )

    def export_rows(self, period_start: date) -> list[tuple[object, ...]]:
        rows = []
        start = month_start(period_start)
        end = next_month_start(start)
        statement = (
            select(Invoice)
            .options(selectinload(Invoice.lines))
            .where(
                Invoice.status == InvoiceStatus.VALIDATED,
                Invoice.invoice_date >= start,
                Invoice.invoice_date < end,
            )
            .order_by(Invoice.created_at.desc())
        )
        for invoice in self.db.scalars(statement).all():
            for line in invoice.lines:
                rows.append(
                    (
                        invoice.invoice_date.isoformat()
                        if invoice.invoice_date
                        else "",
                        invoice.supplier_name,
                        invoice.invoice_number or "",
                        invoice.status.value,
                        line.position + 1,
                        line.description,
                        line.category or "",
                        line.vat_rate,
                        line.amount_ht,
                        line.amount_tva,
                        line.amount_ttc,
                        invoice.total_ht,
                        invoice.total_tva,
                        invoice.total_ttc,
                    )
                )
        return rows

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
        if invoice.status == InvoiceStatus.ARCHIVED:
            raise InvoiceValidationError(["archived_invoice_cannot_be_validated"])

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

    def archive_invoice(self, invoice_id: uuid.UUID) -> Invoice:
        invoice = self.get_invoice(invoice_id)
        if invoice.status == InvoiceStatus.VALIDATED:
            raise InvoiceLockedError("validated_invoice_cannot_be_archived")

        invoice.status = InvoiceStatus.ARCHIVED
        self.db.commit()
        return self.get_invoice(invoice.id)
