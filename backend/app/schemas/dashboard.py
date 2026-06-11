from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class DashboardSummary(BaseModel):
    period_start: date
    invoices_to_review_count: int
    validated_invoices_count: int
    validated_invoices_ht: Decimal
    validated_invoices_tva: Decimal
    validated_invoices_ttc: Decimal
    vat_deductible: Decimal
    vat_collected: Decimal
    vat_payable_estimate: Decimal
    opening_cash: Decimal
    sales_ht: Decimal
    sales_ttc: Decimal
    monthly_outflows: Decimal
    estimated_cash: Decimal
    cash_is_bank_connected: bool = False
