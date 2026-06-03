import re
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import (
    DocumentImport,
    DocumentImportStatus,
    Invoice,
    InvoiceSource,
    InvoiceStatus,
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
        invoice = Invoice(
            supplier_name="A verifier",
            status=InvoiceStatus.NEEDS_REVIEW,
            source=InvoiceSource.AI_UPLOAD,
            document_import_id=document_import.id,
            total_ht=0,
            total_tva=0,
            total_ttc=0,
        )

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
