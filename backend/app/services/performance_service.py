from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Invoice,
    InvoiceLine,
    InvoiceStatus,
    MonthlyCashFlowInputs,
    MonthlySales,
)
from app.schemas.performance import (
    MonthlyCashFlowInputsRead,
    MonthlyCashFlowInputsUpsert,
    MonthlyNonOperatingCashFlowTable,
    MonthlyPerformanceSummary,
    MonthlyPerformanceTable,
)
from app.services.invoice_calculations import money
from app.services.invoice_categories import ALLOWED_CATEGORY_CODES
from app.services.periods import month_start, next_month_start

PERFORMANCE_CATEGORY_BUCKETS: dict[str, str] = {
    "raw_materials_5_5": "raw_materials_ht",
    "raw_materials_20": "raw_materials_ht",
    "alcohol_purchases": "raw_materials_ht",
    "lost_packaging_20": "packaging_ht",
    "maintenance": "external_purchases_taxes_ht",
    "purchase_transport": "external_purchases_taxes_ht",
    "cleaning_products": "external_purchases_taxes_ht",
    "discount": "external_purchases_taxes_ht",
    "hygiene_products": "external_purchases_taxes_ht",
    "administrative_supplies": "external_purchases_taxes_ht",
    "phone_internet": "external_purchases_taxes_ht",
    "fuel_purchases": "external_purchases_taxes_ht",
    "business_meals": "external_purchases_taxes_ht",
    "tips_donations": "external_purchases_taxes_ht",
    "point_of_sale_advertising": "external_purchases_taxes_ht",
    "other": "external_purchases_taxes_ht",
}
UNCATEGORIZED_BUCKET = "external_purchases_taxes_ht"
UNMAPPED_PERFORMANCE_CATEGORIES = ALLOWED_CATEGORY_CODES - set(
    PERFORMANCE_CATEGORY_BUCKETS
)
if UNMAPPED_PERFORMANCE_CATEGORIES:
    raise RuntimeError(
        "Performance category mapping is missing: "
        + ", ".join(sorted(UNMAPPED_PERFORMANCE_CATEGORIES))
    )


class PerformanceService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def upsert_inputs(
        self, payload: MonthlyCashFlowInputsUpsert
    ) -> MonthlyCashFlowInputs:
        period_start = month_start(payload.period_start)
        inputs = self.get_inputs_by_period(period_start)
        if inputs is None:
            inputs = MonthlyCashFlowInputs(period_start=period_start)
            self.db.add(inputs)

        inputs.salaries = money(payload.salaries)
        inputs.social_charges = money(payload.social_charges)
        inputs.investments_cash = money(payload.investments_cash)
        inputs.loan_repayments_cash = money(payload.loan_repayments_cash)

        self.db.commit()
        self.db.refresh(inputs)
        return inputs

    def get_inputs_by_period(
        self, period_start: date
    ) -> MonthlyCashFlowInputs | None:
        statement = select(MonthlyCashFlowInputs).where(
            MonthlyCashFlowInputs.period_start == month_start(period_start)
        )
        return self.db.scalar(statement)

    def monthly_summary(self, period_start: date) -> MonthlyPerformanceSummary:
        start = month_start(period_start)
        end = next_month_start(start)
        monthly_sales = self.db.scalar(
            select(MonthlySales).where(MonthlySales.period_start == start)
        )
        inputs = self.get_inputs_by_period(start)
        input_values = self._input_values(start, inputs)
        data_quality_notes = []

        if monthly_sales is None:
            data_quality_notes.append("monthly_sales_missing")
        if inputs is None:
            data_quality_notes.append("cash_flow_inputs_missing")

        sales_ht = money(monthly_sales.sales_ht if monthly_sales else Decimal("0"))
        vat_collected = money(
            monthly_sales.vat_collected if monthly_sales else Decimal("0")
        )
        invoice_line_totals = self._validated_invoice_line_totals(start, end)
        raw_materials_ht = invoice_line_totals["raw_materials_ht"]
        packaging_ht = invoice_line_totals["packaging_ht"]
        external_purchases_taxes_ht = invoice_line_totals[
            "external_purchases_taxes_ht"
        ]
        vat_deductible = invoice_line_totals["vat_deductible"]
        salaries = money(input_values.salaries)
        social_charges = money(input_values.social_charges)
        investments_cash = money(input_values.investments_cash)
        loan_repayments_cash = money(input_values.loan_repayments_cash)

        ebe_cash = money(
            sales_ht
            - raw_materials_ht
            - packaging_ht
            - salaries
            - social_charges
            - external_purchases_taxes_ht
        )
        vat_net_estimate = money(vat_collected - vat_deductible)
        vat_payable_estimate = money(max(vat_net_estimate, Decimal("0")))
        vat_credit_estimate = money(max(-vat_net_estimate, Decimal("0")))
        total_cash_outflow = money(
            investments_cash + loan_repayments_cash + vat_payable_estimate
        )
        forecast_relevant_cash_outflow = money(
            loan_repayments_cash + vat_payable_estimate
        )

        return MonthlyPerformanceSummary(
            period_start=start,
            inputs=input_values,
            performance=MonthlyPerformanceTable(
                sales_ht=sales_ht,
                raw_materials_ht=raw_materials_ht,
                packaging_ht=packaging_ht,
                salaries=salaries,
                social_charges=social_charges,
                external_purchases_taxes_ht=external_purchases_taxes_ht,
                ebe_cash=ebe_cash,
            ),
            non_operating_cash_flow=MonthlyNonOperatingCashFlowTable(
                investments_cash=investments_cash,
                loan_repayments_cash=loan_repayments_cash,
                vat_payable_estimate=vat_payable_estimate,
                vat_credit_estimate=vat_credit_estimate,
                total_cash_outflow=total_cash_outflow,
                forecast_relevant_cash_outflow=forecast_relevant_cash_outflow,
            ),
            vat_collected=vat_collected,
            vat_deductible=vat_deductible,
            data_quality_notes=data_quality_notes,
        )

    def _input_values(
        self,
        period_start: date,
        inputs: MonthlyCashFlowInputs | None,
    ) -> MonthlyCashFlowInputsRead:
        if inputs is None:
            return MonthlyCashFlowInputsRead(
                id=None,
                period_start=period_start,
                salaries=Decimal("0"),
                social_charges=Decimal("0"),
                investments_cash=Decimal("0"),
                loan_repayments_cash=Decimal("0"),
            )
        return MonthlyCashFlowInputsRead.model_validate(inputs)

    def _validated_invoice_line_totals(
        self, start: date, end: date
    ) -> dict[str, Decimal]:
        rows = self.db.execute(
            select(
                InvoiceLine.category,
                func.coalesce(func.sum(InvoiceLine.amount_ht), 0),
                func.coalesce(func.sum(InvoiceLine.amount_tva), 0),
            )
            .join(Invoice)
            .where(
                Invoice.status == InvoiceStatus.VALIDATED,
                Invoice.invoice_date >= start,
                Invoice.invoice_date < end,
            )
            .group_by(InvoiceLine.category)
        ).all()

        raw_materials_ht = Decimal("0")
        packaging_ht = Decimal("0")
        external_purchases_taxes_ht = Decimal("0")
        vat_deductible = Decimal("0")

        for category, amount_ht, amount_tva in rows:
            line_ht = money(amount_ht)
            vat_deductible += money(amount_tva)
            bucket = PERFORMANCE_CATEGORY_BUCKETS.get(
                category, UNCATEGORIZED_BUCKET
            )
            if bucket == "raw_materials_ht":
                raw_materials_ht += line_ht
            elif bucket == "packaging_ht":
                packaging_ht += line_ht
            else:
                external_purchases_taxes_ht += line_ht

        return {
            "raw_materials_ht": money(raw_materials_ht),
            "packaging_ht": money(packaging_ht),
            "external_purchases_taxes_ht": money(external_purchases_taxes_ht),
            "vat_deductible": money(vat_deductible),
        }
