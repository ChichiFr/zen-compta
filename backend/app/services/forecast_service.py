from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.schemas.forecast import (
    MonthlyForecastAssumptions,
    MonthlyForecastScenario,
    MonthlyForecastSummary,
    RiskLevel,
    ScenarioKey,
)
from app.services.invoice_calculations import money
from app.services.performance_service import PerformanceService

SCENARIO_MULTIPLIERS: tuple[tuple[ScenarioKey, str, Decimal], ...] = (
    ("normal", "CA prevu", Decimal("1")),
    ("sales_minus_10", "CA -10%", Decimal("0.9")),
    ("sales_minus_20", "CA -20%", Decimal("0.8")),
)


class ForecastService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def monthly_forecast(
        self,
        *,
        period_start: date,
        opening_cash: Decimal,
        forecast_sales_ht: Decimal,
        fixed_salaries: Decimal,
        variable_salary_rate: Decimal,
        social_charge_rate: Decimal,
        loan_repayments_cash: Decimal,
    ) -> MonthlyForecastSummary:
        performance_summary = PerformanceService(self.db).monthly_summary(period_start)
        performance = performance_summary.performance
        vat_deductible_estimate = performance_summary.vat_deductible
        vat_collection_rate = Decimal("0")
        if performance.sales_ht > 0:
            vat_collection_rate = (
                performance_summary.vat_collected / performance.sales_ht
            )
        operating_costs_ratio = Decimal("0")
        if performance.sales_ht > 0:
            operating_costs_ratio = (
                (
                    performance.raw_materials_ht
                    + performance.packaging_ht
                    + performance.external_purchases_taxes_ht
                )
                / performance.sales_ht
            )

        assumptions = MonthlyForecastAssumptions(
            opening_cash=money(opening_cash),
            forecast_sales_ht=money(forecast_sales_ht),
            fixed_salaries=money(fixed_salaries),
            variable_salary_rate=money(variable_salary_rate),
            social_charge_rate=money(social_charge_rate),
            loan_repayments_cash=money(loan_repayments_cash),
            vat_collection_rate=money(vat_collection_rate * Decimal("100")),
            vat_deductible_estimate=money(vat_deductible_estimate),
        )
        scenarios = [
            self._scenario(
                key=key,
                label=label,
                sales_ht=money(assumptions.forecast_sales_ht * multiplier),
                operating_costs_ratio=operating_costs_ratio,
                assumptions=assumptions,
            )
            for key, label, multiplier in SCENARIO_MULTIPLIERS
        ]

        return MonthlyForecastSummary(
            period_start=performance_summary.period_start,
            assumptions=assumptions,
            scenarios=scenarios,
            data_quality_notes=performance_summary.data_quality_notes,
        )

    def _scenario(
        self,
        *,
        key: ScenarioKey,
        label: str,
        sales_ht: Decimal,
        operating_costs_ratio: Decimal,
        assumptions: MonthlyForecastAssumptions,
    ) -> MonthlyForecastScenario:
        operating_costs_ht = money(sales_ht * operating_costs_ratio)
        salaries = money(
            assumptions.fixed_salaries
            + sales_ht * assumptions.variable_salary_rate / Decimal("100")
        )
        social_charges = money(
            salaries * assumptions.social_charge_rate / Decimal("100")
        )
        ebe_forecast = money(
            sales_ht - operating_costs_ht - salaries - social_charges
        )
        vat_collected_estimate = money(
            sales_ht * assumptions.vat_collection_rate / Decimal("100")
        )
        vat_payable_estimate = money(
            max(
                vat_collected_estimate - assumptions.vat_deductible_estimate,
                Decimal("0"),
            )
        )
        vat_credit_estimate = money(
            max(
                assumptions.vat_deductible_estimate - vat_collected_estimate,
                Decimal("0"),
            )
        )
        ending_cash_estimate = money(
            assumptions.opening_cash
            + ebe_forecast
            - vat_payable_estimate
            - assumptions.loan_repayments_cash
        )

        return MonthlyForecastScenario(
            key=key,
            label=label,
            forecast_sales_ht=money(sales_ht),
            salaries=salaries,
            social_charges=social_charges,
            operating_costs_ht=operating_costs_ht,
            ebe_forecast=ebe_forecast,
            vat_collected_estimate=vat_collected_estimate,
            vat_payable_estimate=vat_payable_estimate,
            vat_credit_estimate=vat_credit_estimate,
            loan_repayments_cash=money(assumptions.loan_repayments_cash),
            ending_cash_estimate=ending_cash_estimate,
            risk_level=self._risk_level(ending_cash_estimate),
        )

    def _risk_level(self, ending_cash: Decimal) -> RiskLevel:
        if ending_cash < 0:
            return "critical"
        if ending_cash < Decimal("3000"):
            return "warning"
        return "ok"
