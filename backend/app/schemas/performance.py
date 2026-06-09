from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MonthlyCashFlowInputs(BaseModel):
    salaries: Decimal = Field(default=Decimal("0"), ge=0)
    social_charges: Decimal = Field(default=Decimal("0"), ge=0)
    investments_cash: Decimal = Field(default=Decimal("0"), ge=0)
    loan_repayments_cash: Decimal = Field(default=Decimal("0"), ge=0)


class MonthlyCashFlowInputsUpsert(MonthlyCashFlowInputs):
    period_start: date


class MonthlyCashFlowInputsRead(MonthlyCashFlowInputs):
    id: UUID | None = None
    period_start: date

    model_config = ConfigDict(from_attributes=True)


class MonthlyPerformanceTable(BaseModel):
    sales_ht: Decimal
    raw_materials_ht: Decimal
    packaging_ht: Decimal
    salaries: Decimal
    social_charges: Decimal
    external_purchases_taxes_ht: Decimal
    ebe_cash: Decimal


class MonthlyNonOperatingCashFlowTable(BaseModel):
    investments_cash: Decimal
    loan_repayments_cash: Decimal
    vat_payable_estimate: Decimal
    vat_credit_estimate: Decimal
    total_cash_outflow: Decimal
    forecast_relevant_cash_outflow: Decimal


class MonthlyPerformanceSummary(BaseModel):
    period_start: date
    inputs: MonthlyCashFlowInputsRead
    performance: MonthlyPerformanceTable
    non_operating_cash_flow: MonthlyNonOperatingCashFlowTable
    vat_collected: Decimal
    vat_deductible: Decimal
    data_quality_notes: list[str]
