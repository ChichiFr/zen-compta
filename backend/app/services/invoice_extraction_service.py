from __future__ import annotations

import base64
from datetime import date
from pathlib import Path
from typing import Literal

from openai import OpenAI, OpenAIError
from pydantic import BaseModel, Field

from app.core.config import settings

INVOICE_EXTRACTION_PROMPT = """
You are an invoice extraction assistant for Zen Compta, a French restaurant
accounting tool.

Read one supplier invoice document and extract structured invoice data for
human review.

First classify the document as document_kind:
- invoice: exactly one supplier invoice.
- multiple_invoices: the document contains more than one invoice. Do not
  extract any lines.
- not_an_invoice: the document is not a supplier invoice (menu, receipt for a
  card terminal, bank statement, unrelated photo...). Do not extract any
  lines.

Rules:
- Never validate the invoice.
- Never invent missing information.
- If a value is unclear or missing, return null and add a review reason.
- Keep HT, TVA, and TTC separate.
- Multi-rate VAT must be represented at invoice-line level.
- VAT rates must be percentages such as 5.5, 10, or 20.
- Amounts must be decimal numbers with two digits when possible.
- Use French invoice conventions for dates, VAT, and totals.
- If invoice totals do not reconcile with lines, keep extracted values but add
  a review reason.
- For each line, choose exactly one category_code from the allowed list.
- Do not invent categories. If unsure, use other and add a review reason.
- For each line, report confidence between 0 and 1: how certain you are that
  the description, amounts, and VAT rate were read correctly. Use low values
  for blurry, cropped, handwritten, or ambiguous content.

Allowed category_code values:
raw_materials_5_5,
lost_packaging_20,
alcohol_purchases,
maintenance,
purchase_transport,
raw_materials_20,
cleaning_products,
discount,
hygiene_products,
administrative_supplies,
phone_internet,
fuel_purchases,
business_meals,
tips_donations,
point_of_sale_advertising,
other.
""".strip()


class InvoiceExtractionError(Exception):
    pass


class ExtractedInvoiceLine(BaseModel):
    description: str | None = None
    category_code: str | None = None
    vat_rate: float | None = Field(default=None, ge=0, le=100)
    amount_ht: float | None = Field(default=None, ge=0)
    amount_tva: float | None = Field(default=None, ge=0)
    amount_ttc: float | None = Field(default=None, ge=0)
    confidence: float | None = Field(default=None, ge=0, le=1)
    needs_review_reason: str | None = None


class ExtractedInvoice(BaseModel):
    document_kind: Literal["invoice", "multiple_invoices", "not_an_invoice"] = (
        "invoice"
    )
    supplier_name: str | None = None
    invoice_date: date | None = None
    invoice_number: str | None = None
    currency: str | None = "EUR"
    lines: list[ExtractedInvoiceLine] = Field(default_factory=list)
    total_ht: float | None = Field(default=None, ge=0)
    total_tva: float | None = Field(default=None, ge=0)
    total_ttc: float | None = Field(default=None, ge=0)
    needs_review_reason: str | None = None


class InvoiceExtractionService:
    def __init__(self, api_key: str, model: str) -> None:
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def extract(
        self,
        *,
        path: Path,
        filename: str,
        content_type: str,
    ) -> ExtractedInvoice:
        content = [
            file_input_content(path=path, filename=filename, content_type=content_type),
            {
                "type": "input_text",
                "text": "Extract this supplier invoice for Zen Compta.",
            },
        ]
        try:
            response = self.client.responses.parse(
                model=self.model,
                instructions=INVOICE_EXTRACTION_PROMPT,
                input=[{"role": "user", "content": content}],
                text_format=ExtractedInvoice,
                max_output_tokens=16000,
            )
        except OpenAIError as exc:
            raise InvoiceExtractionError(str(exc)) from exc

        if getattr(response, "status", None) == "incomplete":
            raise InvoiceExtractionError("extraction_truncated")
        if response.output_parsed is None:
            raise InvoiceExtractionError("empty_extraction_response")
        return response.output_parsed


def build_invoice_extractor() -> InvoiceExtractionService | None:
    if not settings.openai_api_key:
        return None
    return InvoiceExtractionService(
        api_key=settings.openai_api_key,
        model=settings.openai_invoice_model,
    )


def file_input_content(
    *,
    path: Path,
    filename: str,
    content_type: str,
) -> dict[str, str]:
    encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
    if content_type == "application/pdf":
        return {
            "type": "input_file",
            "filename": filename,
            "file_data": f"data:application/pdf;base64,{encoded}",
        }

    return {
        "type": "input_image",
        "image_url": f"data:{content_type};base64,{encoded}",
        "detail": "high",
    }
