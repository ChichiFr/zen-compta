from decimal import Decimal

from app.models import InvoiceStatus
from app.services.invoice_calculations import (
    InvoiceLineDraft,
    InvoiceValidationInput,
    calculate_line,
    calculate_totals,
    can_validate,
    validation_errors,
)


def test_calculates_single_twenty_percent_vat_line():
    line = calculate_line(
        InvoiceLineDraft(
            description="Electricite",
            vat_rate=Decimal("20"),
            amount_ht=Decimal("100.00"),
        )
    )

    assert line.amount_ht == Decimal("100.00")
    assert line.amount_tva == Decimal("20.00")
    assert line.amount_ttc == Decimal("120.00")
    assert line.needs_review_reason is None


def test_calculates_multi_rate_invoice_totals():
    lines = [
        calculate_line(
            InvoiceLineDraft(
                description="Matieres premieres",
                vat_rate=Decimal("5.5"),
                amount_ht=Decimal("100.00"),
            )
        ),
        calculate_line(
            InvoiceLineDraft(
                description="Service",
                vat_rate=Decimal("20"),
                amount_ht=Decimal("80.00"),
            )
        ),
    ]

    totals = calculate_totals(lines)

    assert totals.total_ht == Decimal("180.00")
    assert totals.total_tva == Decimal("21.50")
    assert totals.total_ttc == Decimal("201.50")


def test_flags_mismatched_vat_amount_for_review():
    line = calculate_line(
        InvoiceLineDraft(
            description="Facture incorrecte",
            vat_rate=Decimal("10"),
            amount_ht=Decimal("100.00"),
            amount_tva=Decimal("11.00"),
        )
    )

    assert line.amount_tva == Decimal("11.00")
    assert line.needs_review_reason == "vat_amount_mismatch"


def test_blocks_validation_when_required_fields_are_missing():
    invoice = InvoiceValidationInput(
        supplier_name="",
        invoice_date_present=False,
        lines=[],
        status=InvoiceStatus.DRAFT,
    )

    assert can_validate(invoice) is False
    assert validation_errors(invoice) == [
        "supplier_required",
        "invoice_date_required",
        "invoice_line_required",
    ]


def test_blocks_validation_when_line_still_needs_review():
    invoice = InvoiceValidationInput(
        supplier_name="Metro",
        invoice_date_present=True,
        lines=[
            calculate_line(
                InvoiceLineDraft(
                    description="Achats",
                    vat_rate=Decimal("10"),
                    amount_ht=Decimal("100.00"),
                    needs_review_reason="ai_low_confidence",
                )
            )
        ],
        status=InvoiceStatus.NEEDS_REVIEW,
    )

    assert can_validate(invoice) is False
    assert validation_errors(invoice) == ["line_1_needs_review"]


def test_allows_validation_when_invoice_is_complete():
    invoice = InvoiceValidationInput(
        supplier_name="Metro",
        invoice_date_present=True,
        lines=[
            calculate_line(
                InvoiceLineDraft(
                    description="Achats",
                    vat_rate=Decimal("10"),
                    amount_ht=Decimal("100.00"),
                )
            )
        ],
        status=InvoiceStatus.DRAFT,
    )

    assert can_validate(invoice) is True
    assert validation_errors(invoice) == []

