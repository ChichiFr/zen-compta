import csv
from collections.abc import Iterable
from datetime import date
from decimal import Decimal
from io import BytesIO, StringIO
from zipfile import ZIP_DEFLATED, ZipFile

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Invoice, InvoiceStatus, MonthlySales
from app.schemas.dashboard import DashboardSummary
from app.services.invoice_calculations import money
from app.services.periods import month_start, next_month_start


class DashboardService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def summary(self, period_start: date, opening_cash: Decimal) -> DashboardSummary:
        start = month_start(period_start)
        end = next_month_start(start)

        review_count = self.db.scalar(
            select(func.count(Invoice.id)).where(
                Invoice.status.in_([InvoiceStatus.DRAFT, InvoiceStatus.NEEDS_REVIEW]),
                Invoice.invoice_date >= start,
                Invoice.invoice_date < end,
            )
        )
        validated_count = self.db.scalar(
            select(func.count(Invoice.id)).where(
                Invoice.status == InvoiceStatus.VALIDATED,
                Invoice.invoice_date >= start,
                Invoice.invoice_date < end,
            )
        )
        invoice_totals = self.db.execute(
            select(
                func.coalesce(func.sum(Invoice.total_ht), 0),
                func.coalesce(func.sum(Invoice.total_tva), 0),
                func.coalesce(func.sum(Invoice.total_ttc), 0),
            ).where(
                Invoice.status == InvoiceStatus.VALIDATED,
                Invoice.invoice_date >= start,
                Invoice.invoice_date < end,
            )
        ).one()
        monthly_sales = self.db.scalar(
            select(MonthlySales).where(MonthlySales.period_start == start)
        )

        validated_ht = money(invoice_totals[0])
        vat_deductible = money(invoice_totals[1])
        validated_ttc = money(invoice_totals[2])
        vat_collected = money(
            monthly_sales.vat_collected if monthly_sales else Decimal("0")
        )
        sales_ht = money(monthly_sales.sales_ht if monthly_sales else Decimal("0"))
        sales_ttc = money(monthly_sales.sales_ttc if monthly_sales else Decimal("0"))
        vat_payable = money(vat_collected - vat_deductible)
        opening_cash_amount = money(opening_cash)
        estimated_cash = money(
            opening_cash_amount + sales_ttc - validated_ttc - vat_payable
        )

        return DashboardSummary(
            period_start=start,
            invoices_to_review_count=review_count or 0,
            validated_invoices_count=validated_count or 0,
            validated_invoices_ht=validated_ht,
            validated_invoices_tva=vat_deductible,
            validated_invoices_ttc=validated_ttc,
            vat_deductible=vat_deductible,
            vat_collected=vat_collected,
            vat_payable_estimate=vat_payable,
            opening_cash=opening_cash_amount,
            sales_ht=sales_ht,
            sales_ttc=sales_ttc,
            estimated_cash=estimated_cash,
        )

    def summary_csv(self, period_start: date, opening_cash: Decimal) -> str:
        return write_summary_csv(self.summary_rows(period_start, opening_cash))

    def summary_xlsx(self, period_start: date, opening_cash: Decimal) -> bytes:
        return write_summary_xlsx(self.summary_rows(period_start, opening_cash))

    def summary_rows(
        self, period_start: date, opening_cash: Decimal
    ) -> list[tuple[str, object]]:
        summary = self.summary(period_start=period_start, opening_cash=opening_cash)
        return [
            ("period_start", summary.period_start.isoformat()),
            ("sales_ht", summary.sales_ht),
            ("vat_collected", summary.vat_collected),
            ("sales_ttc", summary.sales_ttc),
            ("validated_invoices_count", summary.validated_invoices_count),
            ("validated_invoices_ht", summary.validated_invoices_ht),
            ("vat_deductible", summary.vat_deductible),
            ("validated_invoices_ttc", summary.validated_invoices_ttc),
            ("vat_payable_estimate", summary.vat_payable_estimate),
            ("opening_cash", summary.opening_cash),
            ("estimated_cash", summary.estimated_cash),
            ("invoices_to_review_count", summary.invoices_to_review_count),
            ("cash_is_bank_connected", summary.cash_is_bank_connected),
        ]


def write_summary_csv(rows: Iterable[tuple[str, object]]) -> str:
    output = StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["metric", "value"])
    for metric, value in rows:
        writer.writerow([metric, str(value)])
    return output.getvalue()


def write_summary_xlsx(rows: Iterable[tuple[str, object]]) -> bytes:
    sheet_rows = [("metric", "value"), *rows]
    cells = []
    for row_index, row in enumerate(sheet_rows, start=1):
        cell_values = []
        for column_index, value in enumerate(row, start=1):
            cell_ref = f"{chr(64 + column_index)}{row_index}"
            escaped_value = escape_xml(str(value))
            cell_values.append(
                f'<c r="{cell_ref}" t="inlineStr">'
                f"<is><t>{escaped_value}</t></is></c>"
            )
        cells.append(f'<row r="{row_index}">{"".join(cell_values)}</row>')

    worksheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{''.join(cells)}</sheetData>"
        "</worksheet>"
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Dashboard" sheetId="1" r:id="rId1"/></sheets>'
        "</workbook>"
    )
    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/'
        'relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/></Relationships>'
    )
    package_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/'
        'relationships/officeDocument" '
        'Target="xl/workbook.xml"/></Relationships>'
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-'
        'package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        "</Types>"
    )

    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", package_rels)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        archive.writestr("xl/worksheets/sheet1.xml", worksheet)
    return output.getvalue()


def escape_xml(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
