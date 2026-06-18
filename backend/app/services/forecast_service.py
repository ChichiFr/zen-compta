from dataclasses import dataclass
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
from app.services.periods import month_start, shift_months

SCENARIO_MULTIPLIERS: tuple[tuple[ScenarioKey, str, Decimal], ...] = (
    ("normal", "CA prevu", Decimal("1")),
    ("sales_minus_10", "CA -10%", Decimal("0.9")),
    ("sales_minus_20", "CA -20%", Decimal("0.8")),
)

REFERENCE_HISTORY_MONTHS = 3


@dataclass(frozen=True)
class ReferenceHistory:
    """Ratios derived from the trailing reference months.

    Ratios are kept at full precision; only displayed amounts are rounded.
    """

    operating_costs_ratio: Decimal
    vat_collection_rate: Decimal
    monthly_vat_deductible: Decimal
    months_with_activity: int


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
        normalized_period = month_start(period_start)
        performance_summary = PerformanceService(self.db).monthly_summary(
            normalized_period
        )
        history = self._reference_history(normalized_period)
        notes = list(performance_summary.data_quality_notes)
        if history.months_with_activity < REFERENCE_HISTORY_MONTHS:
            notes.append("forecast_reference_partial_history")

        assumptions = MonthlyForecastAssumptions(
            opening_cash=money(opening_cash),
            forecast_sales_ht=money(forecast_sales_ht),
            fixed_salaries=money(fixed_salaries),
            variable_salary_rate=money(variable_salary_rate),
            social_charge_rate=money(social_charge_rate),
            loan_repayments_cash=money(loan_repayments_cash),
            vat_collection_rate=money(
                history.vat_collection_rate * Decimal("100")
            ),
            vat_deductible_estimate=money(history.monthly_vat_deductible),
        )
        scenarios = [
            self._scenario(
                key=key,
                label=label,
                sales_ht=money(assumptions.forecast_sales_ht * multiplier),
                operating_costs_ratio=history.operating_costs_ratio,
                vat_collection_rate=history.vat_collection_rate,
                assumptions=assumptions,
            )
            for key, label, multiplier in SCENARIO_MULTIPLIERS
        ]

        return MonthlyForecastSummary(
            period_start=performance_summary.period_start,
            assumptions=assumptions,
            scenarios=scenarios,
            data_quality_notes=notes,
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
        history = self._reference_history(normalized_period)
        operating_costs_ratio = history.operating_costs_ratio
        notes = list(performance_summary.data_quality_notes)
        if history.months_with_activity < REFERENCE_HISTORY_MONTHS:
            notes.append("forecast_reference_partial_history")
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

    def _reference_history(self, period_start: date) -> ReferenceHistory:
        performance = PerformanceService(self.db)
        total_sales_ht = Decimal("0")
        total_operating_costs_ht = Decimal("0")
        total_vat_collected = Decimal("0")
        total_vat_deductible = Decimal("0")
        months_with_activity = 0

        for offset in range(REFERENCE_HISTORY_MONTHS):
            month = shift_months(period_start, -offset)
            summary = performance.monthly_summary(month)
            sales_ht = summary.performance.sales_ht
            operating_costs_ht = (
                summary.performance.raw_materials_ht
                + summary.performance.packaging_ht
                + summary.performance.fixed_charges_ht
                + summary.performance.external_purchases_ht
            )
            if sales_ht > 0 or operating_costs_ht > 0 or summary.vat_deductible > 0:
                months_with_activity += 1
            total_sales_ht += sales_ht
            total_operating_costs_ht += operating_costs_ht
            total_vat_collected += summary.vat_collected
            total_vat_deductible += summary.vat_deductible

        operating_costs_ratio = Decimal("0")
        vat_collection_rate = Decimal("0")
        if total_sales_ht > 0:
            operating_costs_ratio = total_operating_costs_ht / total_sales_ht
            vat_collection_rate = total_vat_collected / total_sales_ht
        monthly_vat_deductible = Decimal("0")
        if months_with_activity > 0:
            monthly_vat_deductible = total_vat_deductible / months_with_activity

        return ReferenceHistory(
            operating_costs_ratio=operating_costs_ratio,
            vat_collection_rate=vat_collection_rate,
            monthly_vat_deductible=monthly_vat_deductible,
            months_with_activity=months_with_activity,
        )

    def _scenario(
        self,
        *,
        key: ScenarioKey,
        label: str,
        sales_ht: Decimal,
        operating_costs_ratio: Decimal,
        vat_collection_rate: Decimal,
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
        vat_collected_estimate = money(sales_ht * vat_collection_rate)
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
        monthly_drop_multiplier = Decimal("1") - sales_drop_rate / Decimal("100")
        for month_index in range(assumptions.months):
            month = shift_months(period_start, month_index)
            opening_cash = cash
            # Compound the drop month after month: M+1 = ref * (1-d),
            # M+2 = ref * (1-d)^2, etc. Reflects an activity that keeps
            # degrading instead of dropping once and stabilizing.
            compounded_multiplier = monthly_drop_multiplier ** (month_index + 1)
            forecast_sales_ht = money(
                max(
                    assumptions.reference_sales_ht * compounded_multiplier,
                    Decimal("0"),
                )
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

    def _month_difference(self, start: date, end: date) -> int:
        return (end.year - start.year) * 12 + (end.month - start.month)
