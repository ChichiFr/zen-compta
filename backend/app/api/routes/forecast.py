from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.forecast import MonthlyForecastSummary, RunwayForecastSummary
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


@router.get("/runway", response_model=RunwayForecastSummary)
def get_runway_forecast(
    period_start: date,
    opening_cash: Decimal = Query(default=Decimal("0"), ge=0),
    months: int = Query(default=3, ge=3, le=12),
    reference_sales_ht: Decimal = Query(default=Decimal("45000"), ge=0),
    custom_sales_drop_rate: Decimal = Query(default=Decimal("20"), ge=0, le=100),
    fixed_salaries: Decimal = Query(default=Decimal("12000"), ge=0),
    variable_salary_rate: Decimal = Query(default=Decimal("0"), ge=0),
    social_charge_rate: Decimal = Query(default=Decimal("35"), ge=0),
    loan_repayments_cash: Decimal = Query(default=Decimal("2500"), ge=0),
    monthly_vat_payable_estimate: Decimal = Query(default=Decimal("3000"), ge=0),
    minimum_cash_threshold: Decimal = Query(default=Decimal("0"), ge=0),
    service: ForecastService = Depends(get_forecast_service),
) -> RunwayForecastSummary:
    if months not in {3, 6, 12}:
        raise HTTPException(
            status_code=422,
            detail="months_must_be_3_6_or_12",
        )
    if period_start.year > 9998:
        raise HTTPException(
            status_code=422,
            detail="period_start_too_late_for_runway_forecast",
        )
    return service.runway_forecast(
        period_start=period_start,
        opening_cash=opening_cash,
        months=months,
        reference_sales_ht=reference_sales_ht,
        custom_sales_drop_rate=custom_sales_drop_rate,
        fixed_salaries=fixed_salaries,
        variable_salary_rate=variable_salary_rate,
        social_charge_rate=social_charge_rate,
        loan_repayments_cash=loan_repayments_cash,
        monthly_vat_payable_estimate=monthly_vat_payable_estimate,
        minimum_cash_threshold=minimum_cash_threshold,
    )
