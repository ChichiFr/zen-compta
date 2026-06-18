from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.assistant import (
    AssistantDashboardSummary,
    AssistantHealthBrief,
    AssistantReviewSummary,
    AssistantUploadResult,
    AssistantValidationResult,
)
from app.services.assistant_service import AssistantService
from app.services.document_import_service import DocumentImportError
from app.services.invoice_service import InvoiceNotFoundError

router = APIRouter(prefix="/assistant", tags=["assistant"])


def get_assistant_service(
    db: Session = Depends(get_db),
) -> AssistantService:
    return AssistantService(db)


@router.post("/upload", response_model=AssistantUploadResult)
def assistant_upload(
    file: UploadFile,
    service: AssistantService = Depends(get_assistant_service),
) -> AssistantUploadResult:
    try:
        return service.upload_and_summarize(file)
    except DocumentImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.get("/review", response_model=AssistantReviewSummary)
def assistant_review(
    service: AssistantService = Depends(get_assistant_service),
) -> AssistantReviewSummary:
    return service.get_review_summary()


@router.get("/dashboard", response_model=AssistantDashboardSummary)
def assistant_dashboard(
    period_start: date,
    opening_cash: Decimal = Decimal("0"),
    service: AssistantService = Depends(get_assistant_service),
) -> AssistantDashboardSummary:
    return service.get_dashboard_summary(period_start, opening_cash)


@router.post("/validate/{invoice_id}", response_model=AssistantValidationResult)
def assistant_validate(
    invoice_id: UUID,
    service: AssistantService = Depends(get_assistant_service),
) -> AssistantValidationResult:
    try:
        return service.validate_invoice(invoice_id)
    except InvoiceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="invoice_not_found",
        ) from exc


@router.get("/health-brief", response_model=AssistantHealthBrief)
def assistant_health_brief(
    period_start: date,
    opening_cash: Decimal = Decimal("0"),
    service: AssistantService = Depends(get_assistant_service),
) -> AssistantHealthBrief:
    return service.get_health_brief(period_start, opening_cash)
