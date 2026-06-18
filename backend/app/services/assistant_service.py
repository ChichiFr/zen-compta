from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.schemas.assistant import (
    AssistantDashboardSummary,
    AssistantHealthBrief,
    AssistantReviewSummary,
    AssistantUploadResult,
    AssistantValidationResult,
)
from app.schemas.invoice import InvoiceRead
from app.services.dashboard_service import DashboardService
from app.services.document_import_service import DocumentImportService
from app.services.invoice_service import InvoiceService, InvoiceValidationError
from app.services.nlp_summary_service import (
    NLPSummaryService,
    _fallback_dashboard_summary,
    _fallback_review_summary,
    _fallback_upload_summary,
    build_nlp_summary_service,
)


class AssistantService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.nlp: NLPSummaryService | None = build_nlp_summary_service()

    def upload_and_summarize(self, upload: UploadFile) -> AssistantUploadResult:
        doc_import_service = DocumentImportService(self.db)
        _doc_import, invoice = doc_import_service.create_upload(upload)

        invoice_data = _invoice_to_dict(InvoiceRead.model_validate(invoice))
        if self.nlp:
            summary = self.nlp.summarize_upload(invoice_data)
        else:
            summary = _fallback_upload_summary(invoice_data)
        if not summary:
            summary = _fallback_upload_summary(invoice_data)

        needs_action = any(
            line.get("needs_review_reason") for line in invoice_data.get("lines", [])
        )

        return AssistantUploadResult(
            invoice=InvoiceRead.model_validate(invoice),
            summary_text=summary,
            needs_action=needs_action,
        )

    def get_review_summary(self) -> AssistantReviewSummary:
        invoice_service = InvoiceService(self.db)
        invoices = invoice_service.list_invoices(imported_to_review=True)

        invoices_read = [InvoiceRead.model_validate(inv) for inv in invoices]
        invoices_data = [_invoice_to_dict(inv) for inv in invoices_read]

        if self.nlp and invoices_data:
            summary = self.nlp.summarize_review_queue(invoices_data)
        else:
            summary = _fallback_review_summary(invoices_data)
        if not summary:
            summary = _fallback_review_summary(invoices_data)

        return AssistantReviewSummary(
            invoices=invoices_read,
            summary_text=summary,
            count=len(invoices_read),
        )

    def get_dashboard_summary(
        self,
        period_start: date,
        opening_cash: Decimal,
    ) -> AssistantDashboardSummary:
        dashboard_service = DashboardService(self.db)
        dashboard = dashboard_service.summary(period_start, opening_cash)
        dashboard_data = dashboard.model_dump(mode="json")

        if self.nlp:
            summary = self.nlp.summarize_dashboard(dashboard_data, None)
        else:
            summary = _fallback_dashboard_summary(dashboard_data)
        if not summary:
            summary = _fallback_dashboard_summary(dashboard_data)

        alerts: list[str] = []
        if dashboard.invoices_to_review_count > 0:
            alerts.append(
                f"{dashboard.invoices_to_review_count} facture(s) "
                f"en attente de validation."
            )
        if dashboard.estimated_cash < Decimal("0"):
            alerts.append("Tresorerie estimee negative.")
        if dashboard.vat_payable_estimate > Decimal("1000"):
            alerts.append(
                f"TVA a payer elevee: {dashboard.vat_payable_estimate} EUR."
            )

        return AssistantDashboardSummary(
            dashboard=dashboard,
            summary_text=summary,
            alerts=alerts,
        )

    def validate_invoice(self, invoice_id: uuid.UUID) -> AssistantValidationResult:
        invoice_service = InvoiceService(self.db)
        try:
            invoice = invoice_service.validate_invoice(invoice_id)
            invoice_read = InvoiceRead.model_validate(invoice)
            return AssistantValidationResult(
                invoice=invoice_read,
                summary_text=(
                    f"Facture de {invoice_read.supplier_name} validee "
                    f"({invoice_read.total_ttc} EUR TTC). "
                    f"Elle compte maintenant dans vos totaux du mois."
                ),
                success=True,
            )
        except InvoiceValidationError as exc:
            invoice = invoice_service.get_invoice(invoice_id)
            invoice_read = InvoiceRead.model_validate(invoice)
            return AssistantValidationResult(
                invoice=invoice_read,
                summary_text=(
                    f"La facture ne peut pas etre validee: {', '.join(exc.errors)}. "
                    f"Corrigez les problemes puis reessayez."
                ),
                success=False,
            )

    def get_health_brief(
        self,
        period_start: date,
        opening_cash: Decimal,
    ) -> AssistantHealthBrief:
        dashboard_result = self.get_dashboard_summary(period_start, opening_cash)
        dashboard = dashboard_result.dashboard

        if dashboard.estimated_cash < Decimal("0"):
            risk_level = "critical"
        elif dashboard.estimated_cash < Decimal("2000"):
            risk_level = "warning"
        else:
            risk_level = "ok"

        return AssistantHealthBrief(
            text=dashboard_result.summary_text,
            risk_level=risk_level,
        )


def _invoice_to_dict(invoice_read: InvoiceRead) -> dict:
    return {
        "supplier_name": invoice_read.supplier_name,
        "invoice_date": (
            str(invoice_read.invoice_date)
            if invoice_read.invoice_date
            else None
        ),
        "invoice_number": invoice_read.invoice_number,
        "total_ht": str(invoice_read.total_ht),
        "total_tva": str(invoice_read.total_tva),
        "total_ttc": str(invoice_read.total_ttc),
        "status": invoice_read.status.value,
        "lines": [
            {
                "description": line.description,
                "category": line.category,
                "vat_rate": str(line.vat_rate),
                "amount_ht": str(line.amount_ht),
                "amount_tva": str(line.amount_tva),
                "amount_ttc": str(line.amount_ttc),
                "ai_confidence": (
                    str(line.ai_confidence)
                    if line.ai_confidence
                    else None
                ),
                "needs_review_reason": line.needs_review_reason,
            }
            for line in invoice_read.lines
        ],
    }
