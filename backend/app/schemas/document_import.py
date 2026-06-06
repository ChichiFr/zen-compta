from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models import DocumentImportStatus
from app.schemas.invoice import InvoiceRead


class DocumentImportRead(BaseModel):
    id: UUID
    original_filename: str
    stored_filename: str
    content_type: str
    size_bytes: int
    status: DocumentImportStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentImportUploadRead(BaseModel):
    document_import: DocumentImportRead
    invoice: InvoiceRead
