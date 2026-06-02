from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.models import InvoiceStatus

CENT = Decimal("0.01")


@dataclass(frozen=True)
class InvoiceLineDraft:
    description: str
    vat_rate: Decimal
    amount_ht: Decimal
    amount_tva: Decimal | None = None
    amount_ttc: Decimal | None = None
    needs_review_reason: str | None = None


@dataclass(frozen=True)
class CalculatedInvoiceLine:
    description: str
    vat_rate: Decimal
    amount_ht: Decimal
    amount_tva: Decimal
    amount_ttc: Decimal
    needs_review_reason: str | None = None


@dataclass(frozen=True)
class InvoiceTotals:
    total_ht: Decimal
    total_tva: Decimal
    total_ttc: Decimal


@dataclass(frozen=True)
class InvoiceValidationInput:
    supplier_name: str | None
    invoice_date_present: bool
    lines: list[CalculatedInvoiceLine]
    status: InvoiceStatus


def money(value: Decimal | int | str) -> Decimal:
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def calculate_line(line: InvoiceLineDraft) -> CalculatedInvoiceLine:
    amount_ht = money(line.amount_ht)
    vat_rate = Decimal(line.vat_rate)
    expected_tva = money(amount_ht * vat_rate / Decimal("100"))
    amount_tva = money(line.amount_tva) if line.amount_tva is not None else expected_tva
    amount_ttc = (
        money(line.amount_ttc)
        if line.amount_ttc is not None
        else money(amount_ht + amount_tva)
    )

    review_reasons = [line.needs_review_reason] if line.needs_review_reason else []
    if amount_tva != expected_tva:
        review_reasons.append("vat_amount_mismatch")
    if amount_ttc != money(amount_ht + amount_tva):
        review_reasons.append("ttc_amount_mismatch")

    return CalculatedInvoiceLine(
        description=line.description.strip(),
        vat_rate=vat_rate,
        amount_ht=amount_ht,
        amount_tva=amount_tva,
        amount_ttc=amount_ttc,
        needs_review_reason=", ".join(review_reasons) or None,
    )


def calculate_totals(lines: list[CalculatedInvoiceLine]) -> InvoiceTotals:
    return InvoiceTotals(
        total_ht=money(sum((line.amount_ht for line in lines), Decimal("0"))),
        total_tva=money(sum((line.amount_tva for line in lines), Decimal("0"))),
        total_ttc=money(sum((line.amount_ttc for line in lines), Decimal("0"))),
    )


def validation_errors(invoice: InvoiceValidationInput) -> list[str]:
    errors: list[str] = []
    if not invoice.supplier_name or not invoice.supplier_name.strip():
        errors.append("supplier_required")
    if not invoice.invoice_date_present:
        errors.append("invoice_date_required")
    if not invoice.lines:
        errors.append("invoice_line_required")

    for index, line in enumerate(invoice.lines):
        prefix = f"line_{index + 1}"
        if not line.description:
            errors.append(f"{prefix}_description_required")
        if line.amount_ht < 0 or line.amount_tva < 0 or line.amount_ttc < 0:
            errors.append(f"{prefix}_negative_amount")
        if line.amount_ttc != money(line.amount_ht + line.amount_tva):
            errors.append(f"{prefix}_totals_do_not_reconcile")
        if line.needs_review_reason:
            errors.append(f"{prefix}_needs_review")

    return errors


def can_validate(invoice: InvoiceValidationInput) -> bool:
    return not validation_errors(invoice)

