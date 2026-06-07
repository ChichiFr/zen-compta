import re
import uuid
from decimal import Decimal
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import (
    DocumentImport,
    DocumentImportStatus,
    Invoice,
    InvoiceLine,
    InvoiceSource,
    InvoiceStatus,
)
from app.services.invoice_calculations import (
    InvoiceLineDraft,
    calculate_line,
    calculate_totals,
    money,
)
from app.services.invoice_categories import (
    append_review_reason,
    normalize_category_code,
)
from app.services.invoice_extraction_service import (
    ExtractedInvoice,
    InvoiceExtractionError,
    build_invoice_extractor,
)

ALLOWED_CONTENT_TYPES = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


class DocumentImportError(Exception):
    pass


class DocumentImportService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_upload(self, upload: UploadFile) -> tuple[DocumentImport, Invoice]:
        content_type = upload.content_type or ""
        extension = ALLOWED_CONTENT_TYPES.get(content_type)
        if extension is None:
            raise DocumentImportError("unsupported_file_type")

        storage_dir = upload_storage_dir()
        storage_dir.mkdir(parents=True, exist_ok=True)

        import_id = uuid.uuid4()
        safe_original = sanitize_filename(upload.filename or "invoice")
        stored_filename = f"{import_id}{extension}"
        storage_path = storage_dir / stored_filename

        size_bytes = 0
        first_chunk = b""
        with storage_path.open("wb") as destination:
            while chunk := upload.file.read(1024 * 1024):
                if not first_chunk:
                    first_chunk = chunk[:64]
                size_bytes += len(chunk)
                if size_bytes > settings.max_upload_bytes:
                    destination.close()
                    storage_path.unlink(missing_ok=True)
                    raise DocumentImportError("file_too_large")
                destination.write(chunk)

        if not file_signature_matches(content_type, first_chunk):
            storage_path.unlink(missing_ok=True)
            raise DocumentImportError("file_signature_mismatch")

        document_import = DocumentImport(
            id=import_id,
            original_filename=safe_original,
            stored_filename=stored_filename,
            storage_path=str(storage_path),
            content_type=content_type,
            size_bytes=size_bytes,
            status=DocumentImportStatus.UPLOADED,
        )
        invoice = placeholder_invoice(document_import.id)

        extractor = build_invoice_extractor()
        if extractor is not None:
            try:
                extracted = extractor.extract(
                    path=storage_path,
                    filename=safe_original,
                    content_type=content_type,
                )
                invoice = invoice_from_extraction(document_import.id, extracted)
                document_import.status = DocumentImportStatus.EXTRACTION_COMPLETED
            except InvoiceExtractionError:
                document_import.status = DocumentImportStatus.EXTRACTION_FAILED

        self.db.add(document_import)
        self.db.add(invoice)
        self.db.commit()
        self.db.refresh(document_import)
        self.db.refresh(invoice)
        return document_import, invoice


def sanitize_filename(filename: str) -> str:
    name = Path(filename).name.strip()
    name = re.sub(r"[^A-Za-z0-9._ -]", "_", name)
    return name[:255] or "invoice"


def placeholder_invoice(document_import_id: uuid.UUID) -> Invoice:
    return Invoice(
        supplier_name="A verifier",
        status=InvoiceStatus.NEEDS_REVIEW,
        source=InvoiceSource.AI_UPLOAD,
        document_import_id=document_import_id,
        total_ht=0,
        total_tva=0,
        total_ttc=0,
    )


def invoice_from_extraction(
    document_import_id: uuid.UUID,
    extracted: ExtractedInvoice,
) -> Invoice:
    lines = []
    for index, extracted_line in enumerate(extracted.lines):
        if not extracted_line.description or extracted_line.amount_ht is None:
            continue
        if extracted_line.vat_rate is None:
            continue

        category, category_review_reason = normalize_category_code(
            extracted_line.category_code
        )
        calculated = calculate_line(
            InvoiceLineDraft(
                description=extracted_line.description,
                vat_rate=decimal_from_extracted_number(extracted_line.vat_rate),
                amount_ht=decimal_from_extracted_number(extracted_line.amount_ht),
                amount_tva=decimal_from_extracted_number(extracted_line.amount_tva)
                if extracted_line.amount_tva is not None
                else None,
                amount_ttc=decimal_from_extracted_number(extracted_line.amount_ttc)
                if extracted_line.amount_ttc is not None
                else None,
                needs_review_reason=append_review_reason(
                    extracted_line.needs_review_reason,
                    category_review_reason,
                ),
            )
        )
        lines.append(
            InvoiceLine(
                position=index,
                description=calculated.description,
                category=category,
                vat_rate=calculated.vat_rate,
                amount_ht=calculated.amount_ht,
                amount_tva=calculated.amount_tva,
                amount_ttc=calculated.amount_ttc,
                needs_review_reason=calculated.needs_review_reason,
            )
        )

    if not lines:
        raise InvoiceExtractionError("no_extractable_invoice_lines")

    totals = calculate_totals(
        [
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
            for line in lines
        ]
    )
    invoice = Invoice(
        supplier_name=(extracted.supplier_name or "A verifier").strip()
        or "A verifier",
        invoice_date=usable_invoice_date(extracted.invoice_date),
        invoice_number=extracted.invoice_number,
        status=InvoiceStatus.NEEDS_REVIEW,
        source=InvoiceSource.AI_UPLOAD,
        document_import_id=document_import_id,
        total_ht=totals.total_ht,
        total_tva=totals.total_tva,
        total_ttc=totals.total_ttc,
    )
    invoice.lines = lines

    if (
        extracted.total_ht is not None
        and money(decimal_from_extracted_number(extracted.total_ht)) != totals.total_ht
    ):
        mark_invoice_lines_for_review(invoice, "invoice_total_ht_mismatch")
    if (
        extracted.total_tva is not None
        and money(decimal_from_extracted_number(extracted.total_tva))
        != totals.total_tva
    ):
        mark_invoice_lines_for_review(invoice, "invoice_total_tva_mismatch")
    if (
        extracted.total_ttc is not None
        and money(decimal_from_extracted_number(extracted.total_ttc))
        != totals.total_ttc
    ):
        mark_invoice_lines_for_review(invoice, "invoice_total_ttc_mismatch")
    if extracted.needs_review_reason:
        mark_invoice_lines_for_review(invoice, extracted.needs_review_reason)
    if extracted.invoice_date is not None and invoice.invoice_date is None:
        mark_invoice_lines_for_review(invoice, "invalid_invoice_date")

    return invoice


def usable_invoice_date(value):
    if value is None:
        return None
    if value.year < 2000 or value.year > 2100:
        return None
    return value


def decimal_from_extracted_number(value: float) -> Decimal:
    return Decimal(str(value))


def mark_invoice_lines_for_review(invoice: Invoice, reason: str) -> None:
    if not invoice.lines:
        return
    invoice.lines[0].needs_review_reason = append_review_reason(
        invoice.lines[0].needs_review_reason,
        reason,
    )


def upload_storage_dir() -> Path:
    configured_path = Path(settings.upload_storage_dir)
    if configured_path.is_absolute():
        return configured_path.resolve()
    repo_root = Path(__file__).resolve().parents[3]
    return (repo_root / configured_path).resolve()


def file_signature_matches(content_type: str, first_chunk: bytes) -> bool:
    if content_type == "application/pdf":
        return first_chunk.startswith(b"%PDF-")
    if content_type == "image/jpeg":
        return first_chunk.startswith(b"\xff\xd8\xff")
    if content_type == "image/png":
        return first_chunk.startswith(b"\x89PNG\r\n\x1a\n")
    if content_type == "image/webp":
        return first_chunk.startswith(b"RIFF") and first_chunk[8:12] == b"WEBP"
    return False
