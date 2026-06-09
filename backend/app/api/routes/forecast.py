from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.forecast import MonthlyForecastSummary
from app.services.forecast_service import ForecastService

router = APIRouter(prefix="/forecast", tags=["forecast"])


def get_forecast_service(db: Session = Depends(get_db)) -> ForecastService:
    return ForecastService(db)


@router.get("/monthly", response_model=MonthlyForecastSummary)
def get_monthly_forecast(
    period_start: date,
    opening_cash: Decimal = Query(default=Decimal("0"), ge=0),
    forecast_sales_ht: Decimal = Query(default=Decimal("0"), ge=0),
    fixed_salaries: Decimal = Query(default=Decimal("0"), ge=0),
    variable_salary_rate: Decimal = Query(default=Decimal("0"), ge=0),
    social_charge_rate: Decimal = Query(default=Decimal("35"), ge=0),
    loan_repayments_cash: Decimal = Query(default=Decimal("0"), ge=0),
    service: ForecastService = Depends(get_forecast_service),
) -> MonthlyForecastSummary:
    return service.monthly_forecast(
        period_start=period_start,
        opening_cash=opening_cash,
        forecast_sales_ht=forecast_sales_ht,
        fixed_salaries=fixed_salaries,
        variable_salary_rate=variable_salary_rate,
        social_charge_rate=social_charge_rate,
        loan_repayments_cash=loan_repayments_cash,
    )
