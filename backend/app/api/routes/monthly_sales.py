from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.monthly_sales import (
    MonthlySalesInput,
    MonthlySalesRead,
    MonthlySalesUpsert,
)
from app.services.monthly_sales_service import MonthlySalesService

router = APIRouter(prefix="/monthly-sales", tags=["monthly-sales"])


def get_monthly_sales_service(
    db: Session = Depends(get_db),
) -> MonthlySalesService:
    return MonthlySalesService(db)


@router.put("/{period_start}", response_model=MonthlySalesRead)
def upsert_monthly_sales(
    period_start: date,
    payload: MonthlySalesInput,
    service: MonthlySalesService = Depends(get_monthly_sales_service),
) -> MonthlySalesRead:
    return service.upsert(
        MonthlySalesUpsert(period_start=period_start, **payload.model_dump())
    )


@router.get("/{period_start}", response_model=MonthlySalesRead)
def get_monthly_sales(
    period_start: date,
    service: MonthlySalesService = Depends(get_monthly_sales_service),
) -> MonthlySalesRead:
    monthly_sales = service.get_by_period(period_start)
    if monthly_sales is None:
        raise HTTPException(status_code=404, detail="monthly_sales_not_found")
    return monthly_sales
