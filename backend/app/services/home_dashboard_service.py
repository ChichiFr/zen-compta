from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    BankConnection,
    BankConnectionStatus,
    BankTransaction,
    Invoice,
    InvoiceStatus,
    MonthlySales,
)
from app.schemas.dashboard import (
    HomeBankFlowPoint,
    HomeDashboardSummary,
    HomeMonthlyPoint,
)
from app.services.bank_anomaly_service import BankAnomalyService
from app.services.invoice_calculations import money
from app.services.periods import month_start, shift_months

CHART_MONTHS = 12
BANK_FLOW_DAYS = 30


class HomeDashboardService:
    """Aggregates everything the home dashboard needs in one call.

    Read-only: sales come from the monthly manual entry, purchases from
    validated invoices only (human-validation rule), bank data from synced
    transactions.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def summary(self, period_start: date) -> HomeDashboardSummary:
        current = month_start(period_start)
        months = [
            shift_months(current, offset)
            for offset in range(-(CHART_MONTHS - 1), 1)
        ]
        earliest_prior = shift_months(months[0], -12)

        sales_by_month = self._sales_by_month(earliest_prior, current)
        purchases_by_month = self._purchases_by_month(earliest_prior, current)

        monthly_series = [
            HomeMonthlyPoint(
                month=month,
                sales_ht=sales_by_month.get(month, Decimal("0.00")),
                sales_prior_ht=sales_by_month.get(shift_months(month, -12)),
                purchases_ht=purchases_by_month.get(month, Decimal("0.00")),
                purchases_prior_ht=purchases_by_month.get(
                    shift_months(month, -12)
                ),
            )
            for month in months
        ]

        bank_connected = (
            self.db.scalar(
                select(BankConnection.id).where(
                    BankConnection.status == BankConnectionStatus.LINKED
                )
            )
            is not None
        )
        bank_flow = self._bank_flow() if bank_connected else []
        net_flow = (
            bank_flow[-1].cumulative_flow if bank_flow else Decimal("0.00")
        )

        return HomeDashboardSummary(
            period_start=current,
            monthly_series=monthly_series,
            bank_connected=bank_connected,
            bank_flow=bank_flow,
            bank_net_flow=net_flow,
            unpaid_invoices_count=BankAnomalyService(
                self.db
            ).summary().unpaid_invoices_count,
        )

    def _sales_by_month(
        self, earliest: date, latest: date
    ) -> dict[date, Decimal]:
        rows = self.db.scalars(
            select(MonthlySales).where(
                MonthlySales.period_start >= earliest,
                MonthlySales.period_start <= latest,
            )
        ).all()
        return {row.period_start: money(row.sales_ht) for row in rows}

    def _purchases_by_month(
        self, earliest: date, latest_month: date
    ) -> dict[date, Decimal]:
        end_exclusive = shift_months(latest_month, 1)
        rows = self.db.execute(
            select(Invoice.invoice_date, Invoice.total_ht).where(
                Invoice.status == InvoiceStatus.VALIDATED,
                Invoice.invoice_date.is_not(None),
                Invoice.invoice_date >= earliest,
                Invoice.invoice_date < end_exclusive,
            )
        ).all()
        totals: dict[date, Decimal] = defaultdict(lambda: Decimal("0"))
        for invoice_date, total_ht in rows:
            totals[month_start(invoice_date)] += total_ht
        return {month: money(total) for month, total in totals.items()}

    def _bank_flow(self) -> list[HomeBankFlowPoint]:
        cutoff = date.today() - timedelta(days=BANK_FLOW_DAYS)
        rows = self.db.execute(
            select(BankTransaction.booking_date, BankTransaction.amount)
            .where(BankTransaction.booking_date >= cutoff)
            .order_by(BankTransaction.booking_date.asc())
        ).all()
        daily: dict[date, Decimal] = defaultdict(lambda: Decimal("0"))
        for booking_date, amount in rows:
            daily[booking_date] += amount

        points: list[HomeBankFlowPoint] = []
        running = Decimal("0")
        for day in sorted(daily):
            running += daily[day]
            points.append(
                HomeBankFlowPoint(day=day, cumulative_flow=money(running))
            )
        return points
