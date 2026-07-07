from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.dashboard import DashboardSummary, HomeDashboardSummary
from app.services.dashboard_service import DashboardService
from app.services.home_dashboard_service import HomeDashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def get_dashboard_service(db: Session = Depends(get_db)) -> DashboardService:
    return DashboardService(db)


@router.get("/home", response_model=HomeDashboardSummary)
def get_home_dashboard(
    period_start: date,
    db: Session = Depends(get_db),
) -> HomeDashboardSummary:
    return HomeDashboardService(db).summary(period_start)


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(
    period_start: date,
    opening_cash: Decimal = Query(default=Decimal("0")),
    service: DashboardService = Depends(get_dashboard_service),
) -> DashboardSummary:
    return service.summary(period_start=period_start, opening_cash=opening_cash)


@router.get("/summary.csv", response_class=Response)
def export_dashboard_summary_csv(
    period_start: date,
    opening_cash: Decimal = Query(default=Decimal("0")),
    service: DashboardService = Depends(get_dashboard_service),
) -> Response:
    csv_body = service.summary_csv(
        period_start=period_start,
        opening_cash=opening_cash,
    )
    normalized_period = period_start.replace(day=1).isoformat()
    return Response(
        content=csv_body,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="zen-compta-dashboard-{normalized_period}.csv"'
            )
        },
    )


@router.get("/summary.xlsx", response_class=Response)
def export_dashboard_summary_xlsx(
    period_start: date,
    opening_cash: Decimal = Query(default=Decimal("0")),
    service: DashboardService = Depends(get_dashboard_service),
) -> Response:
    xlsx_body = service.summary_xlsx(
        period_start=period_start,
        opening_cash=opening_cash,
    )
    normalized_period = period_start.replace(day=1).isoformat()
    return Response(
        content=xlsx_body,
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": (
                f'attachment; filename="zen-compta-dashboard-{normalized_period}.xlsx"'
            )
        },
    )
