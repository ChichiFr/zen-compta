from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.document_import import DocumentImportUploadRead
from app.services.document_import_service import (
    DocumentImportError,
    DocumentImportService,
)

router = APIRouter(prefix="/document-imports", tags=["document-imports"])


def get_document_import_service(
    db: Session = Depends(get_db),
) -> DocumentImportService:
    return DocumentImportService(db)


@router.post("", response_model=DocumentImportUploadRead)
def upload_document_import(
    file: UploadFile,
    service: DocumentImportService = Depends(get_document_import_service),
) -> DocumentImportUploadRead:
    try:
        document_import, invoice = service.create_upload(file)
    except DocumentImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return DocumentImportUploadRead(
        document_import=document_import,
        invoice=invoice,
    )
