from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.performance import (
    MonthlyCashFlowInputs,
    MonthlyCashFlowInputsRead,
    MonthlyCashFlowInputsUpsert,
    MonthlyPerformanceSummary,
)
from app.services.performance_service import PerformanceService

router = APIRouter(prefix="/performance", tags=["performance"])


def get_performance_service(db: Session = Depends(get_db)) -> PerformanceService:
    return PerformanceService(db)


@router.get("/monthly", response_model=MonthlyPerformanceSummary)
def get_monthly_performance(
    period_start: date,
    service: PerformanceService = Depends(get_performance_service),
) -> MonthlyPerformanceSummary:
    return service.monthly_summary(period_start=period_start)


@router.put("/monthly-inputs/{period_start}", response_model=MonthlyCashFlowInputsRead)
def upsert_monthly_cash_flow_inputs(
    period_start: date,
    payload: MonthlyCashFlowInputs,
    service: PerformanceService = Depends(get_performance_service),
) -> MonthlyCashFlowInputsRead:
    inputs = service.upsert_inputs(
        MonthlyCashFlowInputsUpsert(
            period_start=period_start,
            **payload.model_dump(),
        )
    )
    return MonthlyCashFlowInputsRead.model_validate(inputs)
