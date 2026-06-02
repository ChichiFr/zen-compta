from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.services.invoice_calculations import money


class MonthlySalesInput(BaseModel):
    sales_ht: Decimal = Field(ge=0)
    vat_collected: Decimal = Field(ge=0)
    sales_ttc: Decimal = Field(ge=0)

    @model_validator(mode="after")
    def validate_sales_totals(self) -> "MonthlySalesInput":
        expected_ttc = money(self.sales_ht + self.vat_collected)
        if money(self.sales_ttc) != expected_ttc:
            raise ValueError("sales_ttc_must_equal_sales_ht_plus_vat_collected")
        return self


class MonthlySalesUpsert(MonthlySalesInput):
    period_start: date


class MonthlySalesRead(BaseModel):
    id: UUID
    period_start: date
    sales_ht: Decimal
    vat_collected: Decimal
    sales_ttc: Decimal

    model_config = ConfigDict(from_attributes=True)
