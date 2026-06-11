from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.schemas.forecast import (
    MonthlyForecastAssumptions,
    MonthlyForecastScenario,
    MonthlyForecastSummary,
    RiskLevel,
    RunwayForecastAssumptions,
    RunwayForecastMonth,
    RunwayForecastScenario,
    RunwayForecastSummary,
    RunwayScenarioKey,
    ScenarioKey,
)
from app.services.invoice_calculations import money
from app.services.performance_service import PerformanceService
from app.services.periods import month_start

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

    def runway_forecast(
        self,
        *,
        period_start: date,
        opening_cash: Decimal,
        months: int,
        reference_sales_ht: Decimal,
        custom_sales_drop_rate: Decimal,
        fixed_salaries: Decimal,
        variable_salary_rate: Decimal,
        social_charge_rate: Decimal,
        loan_repayments_cash: Decimal,
        monthly_vat_payable_estimate: Decimal,
        minimum_cash_threshold: Decimal,
    ) -> RunwayForecastSummary:
        normalized_period = month_start(period_start)
        performance_summary = PerformanceService(self.db).monthly_summary(
            normalized_period
        )
        operating_costs_ratio = self._operating_costs_ratio(performance_summary)
        notes = list(performance_summary.data_quality_notes)
        if operating_costs_ratio == 0:
            notes.append("forecast_operating_costs_ratio_missing")

        assumptions = RunwayForecastAssumptions(
            opening_cash=money(opening_cash),
            months=months,
            reference_sales_ht=money(reference_sales_ht),
            custom_sales_drop_rate=money(custom_sales_drop_rate),
            fixed_salaries=money(fixed_salaries),
            variable_salary_rate=money(variable_salary_rate),
            social_charge_rate=money(social_charge_rate),
            loan_repayments_cash=money(loan_repayments_cash),
            monthly_vat_payable_estimate=money(monthly_vat_payable_estimate),
            minimum_cash_threshold=money(minimum_cash_threshold),
        )
        scenario_inputs: tuple[tuple[RunwayScenarioKey, str, Decimal], ...] = (
            ("normal", "CA normal", Decimal("0")),
            (
                "custom_drop",
                f"Baisse choisie -{assumptions.custom_sales_drop_rate}%",
                assumptions.custom_sales_drop_rate,
            ),
            ("sales_minus_10", "CA -10%", Decimal("10")),
            ("sales_minus_20", "CA -20%", Decimal("20")),
            ("sales_minus_30", "CA -30%", Decimal("30")),
        )

        scenarios = [
            self._runway_scenario(
                key=key,
                label=label,
                sales_drop_rate=sales_drop_rate,
                period_start=normalized_period,
                operating_costs_ratio=operating_costs_ratio,
                assumptions=assumptions,
            )
            for key, label, sales_drop_rate in scenario_inputs
        ]

        return RunwayForecastSummary(
            period_start=normalized_period,
            assumptions=assumptions,
            scenarios=scenarios,
            data_quality_notes=notes,
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

    def _runway_scenario(
        self,
        *,
        key: RunwayScenarioKey,
        label: str,
        sales_drop_rate: Decimal,
        period_start: date,
        operating_costs_ratio: Decimal,
        assumptions: RunwayForecastAssumptions,
    ) -> RunwayForecastScenario:
        cash = assumptions.opening_cash
        rows = []
        first_critical_month = (
            period_start
            if assumptions.opening_cash < assumptions.minimum_cash_threshold
            else None
        )
        for month_index in range(assumptions.months):
            month = self._add_months(period_start, month_index)
            opening_cash = cash
            sales_multiplier = Decimal("1") - sales_drop_rate / Decimal("100")
            forecast_sales_ht = money(
                max(assumptions.reference_sales_ht * sales_multiplier, Decimal("0"))
            )
            operating_costs_ht = money(forecast_sales_ht * operating_costs_ratio)
            salaries = money(
                assumptions.fixed_salaries
                + forecast_sales_ht
                * assumptions.variable_salary_rate
                / Decimal("100")
            )
            social_charges = money(
                salaries * assumptions.social_charge_rate / Decimal("100")
            )
            ebe_forecast = money(
                forecast_sales_ht
                - operating_costs_ht
                - salaries
                - social_charges
            )
            vat_payable_estimate = self._scenario_vat_payable(
                forecast_sales_ht=forecast_sales_ht,
                assumptions=assumptions,
            )
            ending_cash_estimate = money(
                opening_cash
                + ebe_forecast
                - vat_payable_estimate
                - assumptions.loan_repayments_cash
            )
            risk_level = self._risk_level(
                ending_cash_estimate,
                minimum_cash_threshold=assumptions.minimum_cash_threshold,
            )
            if risk_level == "critical" and first_critical_month is None:
                first_critical_month = month

            rows.append(
                RunwayForecastMonth(
                    month=month,
                    opening_cash=opening_cash,
                    forecast_sales_ht=forecast_sales_ht,
                    salaries=salaries,
                    social_charges=social_charges,
                    operating_costs_ht=operating_costs_ht,
                    ebe_forecast=ebe_forecast,
                    vat_payable_estimate=vat_payable_estimate,
                    loan_repayments_cash=money(assumptions.loan_repayments_cash),
                    ending_cash_estimate=ending_cash_estimate,
                    risk_level=risk_level,
                )
            )
            cash = ending_cash_estimate

        runway_months = assumptions.months
        if first_critical_month is not None:
            runway_months = max(
                self._month_difference(period_start, first_critical_month), 0
            )
        ending_cash = (
            rows[-1].ending_cash_estimate if rows else assumptions.opening_cash
        )

        return RunwayForecastScenario(
            key=key,
            label=label,
            sales_drop_rate=money(sales_drop_rate),
            runway_months=runway_months,
            first_critical_month=first_critical_month,
            ending_cash_estimate=ending_cash,
            risk_level=(
                "critical"
                if first_critical_month is not None
                else self._risk_level(
                    ending_cash,
                    minimum_cash_threshold=assumptions.minimum_cash_threshold,
                )
            ),
            months=rows,
        )

    def _scenario_vat_payable(
        self,
        *,
        forecast_sales_ht: Decimal,
        assumptions: RunwayForecastAssumptions,
    ) -> Decimal:
        if assumptions.reference_sales_ht <= 0:
            return money(assumptions.monthly_vat_payable_estimate)
        return money(
            assumptions.monthly_vat_payable_estimate
            * forecast_sales_ht
            / assumptions.reference_sales_ht
        )

    def _operating_costs_ratio(self, performance_summary) -> Decimal:
        performance = performance_summary.performance
        if performance.sales_ht <= 0:
            return Decimal("0")
        return (
            performance.raw_materials_ht
            + performance.packaging_ht
            + performance.external_purchases_taxes_ht
        ) / performance.sales_ht

    def _risk_level(
        self,
        ending_cash: Decimal,
        *,
        minimum_cash_threshold: Decimal = Decimal("0"),
    ) -> RiskLevel:
        if ending_cash < minimum_cash_threshold:
            return "critical"
        if ending_cash < minimum_cash_threshold + Decimal("3000"):
            return "warning"
        return "ok"

    def _add_months(self, value: date, months: int) -> date:
        zero_based_month = value.month - 1 + months
        year = value.year + zero_based_month // 12
        month = zero_based_month % 12 + 1
        return date(year, month, 1)

    def _month_difference(self, start: date, end: date) -> int:
        return (end.year - start.year) * 12 + (end.month - start.month)
