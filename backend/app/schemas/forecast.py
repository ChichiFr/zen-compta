from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

RiskLevel = Literal["ok", "warning", "critical"]
ScenarioKey = Literal["normal", "sales_minus_10", "sales_minus_20"]
RunwayScenarioKey = Literal[
    "normal",
    "custom_drop",
    "sales_minus_10",
    "sales_minus_20",
    "sales_minus_30",
]


class MonthlyForecastAssumptions(BaseModel):
    opening_cash: Decimal = Field(ge=0)
    forecast_sales_ht: Decimal = Field(ge=0)
    fixed_salaries: Decimal = Field(ge=0)
    variable_salary_rate: Decimal = Field(ge=0)
    social_charge_rate: Decimal = Field(ge=0)
    loan_repayments_cash: Decimal = Field(ge=0)
    vat_collection_rate: Decimal = Field(ge=0)
    vat_deductible_estimate: Decimal


class MonthlyForecastScenario(BaseModel):
    key: ScenarioKey
    label: str
    forecast_sales_ht: Decimal
    salaries: Decimal
    social_charges: Decimal
    operating_costs_ht: Decimal
    ebe_forecast: Decimal
    vat_collected_estimate: Decimal
    vat_payable_estimate: Decimal
    vat_credit_estimate: Decimal
    loan_repayments_cash: Decimal
    ending_cash_estimate: Decimal
    risk_level: RiskLevel


class MonthlyForecastSummary(BaseModel):
    period_start: date
    assumptions: MonthlyForecastAssumptions
    scenarios: list[MonthlyForecastScenario]
    data_quality_notes: list[str]


class RunwayForecastAssumptions(BaseModel):
    opening_cash: Decimal = Field(ge=0)
    months: Literal[3, 6, 12]
    reference_sales_ht: Decimal = Field(ge=0)
    custom_sales_drop_rate: Decimal = Field(ge=0)
    fixed_salaries: Decimal = Field(ge=0)
    variable_salary_rate: Decimal = Field(ge=0)
    social_charge_rate: Decimal = Field(ge=0)
    loan_repayments_cash: Decimal = Field(ge=0)
    monthly_vat_payable_estimate: Decimal = Field(ge=0)
    minimum_cash_threshold: Decimal = Field(ge=0)


class RunwayForecastMonth(BaseModel):
    month: date
    opening_cash: Decimal
    forecast_sales_ht: Decimal
    salaries: Decimal
    social_charges: Decimal
    operating_costs_ht: Decimal
    ebe_forecast: Decimal
    vat_payable_estimate: Decimal
    loan_repayments_cash: Decimal
    ending_cash_estimate: Decimal
    risk_level: RiskLevel


class RunwayForecastScenario(BaseModel):
    key: RunwayScenarioKey
    label: str
    sales_drop_rate: Decimal
    runway_months: int
    first_critical_month: date | None
    ending_cash_estimate: Decimal
    risk_level: RiskLevel
    months: list[RunwayForecastMonth]


class RunwayForecastSummary(BaseModel):
    period_start: date
    assumptions: RunwayForecastAssumptions
    scenarios: list[RunwayForecastScenario]
    data_quality_notes: list[str]
