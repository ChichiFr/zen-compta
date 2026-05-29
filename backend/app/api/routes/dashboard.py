from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.dashboard import DashboardSummary
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def get_dashboard_service(db: Session = Depends(get_db)) -> DashboardService:
    return DashboardService(db)


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(
    period_start: date,
    opening_cash: Decimal = Query(default=Decimal("0")),
    service: DashboardService = Depends(get_dashboard_service),
) -> DashboardSummary:
    return service.summary(period_start=period_start, opening_cash=opening_cash)
