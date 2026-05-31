import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.invoice import InvoiceCreate, InvoiceRead
from app.services.invoice_service import (
    InvoiceNotFoundError,
    InvoiceService,
    InvoiceValidationError,
)

router = APIRouter(prefix="/invoices", tags=["invoices"])


def get_invoice_service(db: Session = Depends(get_db)) -> InvoiceService:
    return InvoiceService(db)


@router.post("", response_model=InvoiceRead, status_code=status.HTTP_201_CREATED)
def create_invoice(
    payload: InvoiceCreate,
    service: InvoiceService = Depends(get_invoice_service),
) -> InvoiceRead:
    return service.create_invoice(payload)


@router.get("", response_model=list[InvoiceRead])
def list_invoices(
    period_start: date | None = Query(default=None),
    service: InvoiceService = Depends(get_invoice_service),
) -> list[InvoiceRead]:
    return service.list_invoices(period_start=period_start)


@router.get("/{invoice_id}", response_model=InvoiceRead)
def get_invoice(
    invoice_id: uuid.UUID,
    service: InvoiceService = Depends(get_invoice_service),
) -> InvoiceRead:
    try:
        return service.get_invoice(invoice_id)
    except InvoiceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="invoice_not_found") from exc


@router.post("/{invoice_id}/validate", response_model=InvoiceRead)
def validate_invoice(
    invoice_id: uuid.UUID,
    service: InvoiceService = Depends(get_invoice_service),
) -> InvoiceRead:
    try:
        return service.validate_invoice(invoice_id)
    except InvoiceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="invoice_not_found") from exc
    except InvoiceValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"errors": exc.errors},
        ) from exc
