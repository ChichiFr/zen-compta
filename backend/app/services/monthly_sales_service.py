from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import MonthlySales
from app.schemas.monthly_sales import MonthlySalesUpsert
from app.services.invoice_calculations import money
from app.services.periods import month_start


class MonthlySalesService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def upsert(self, payload: MonthlySalesUpsert) -> MonthlySales:
        period_start = month_start(payload.period_start)
        monthly_sales = self.get_by_period(period_start)
        if monthly_sales is None:
            monthly_sales = MonthlySales(period_start=period_start)
            self.db.add(monthly_sales)

        monthly_sales.sales_ht = money(payload.sales_ht)
        monthly_sales.vat_collected = money(payload.vat_collected)
        monthly_sales.sales_ttc = money(payload.sales_ttc)

        self.db.commit()
        self.db.refresh(monthly_sales)
        return monthly_sales

    def get_by_period(self, period_start: date) -> MonthlySales | None:
        statement = select(MonthlySales).where(
            MonthlySales.period_start == month_start(period_start)
        )
        return self.db.scalar(statement)

    def vat_collected_for_period(self, period_start: date) -> Decimal:
        monthly_sales = self.get_by_period(period_start)
        return money(monthly_sales.vat_collected if monthly_sales else Decimal("0"))
