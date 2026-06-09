import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Numeric, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MonthlyCashFlowInputs(Base):
    __tablename__ = "monthly_cash_flow_inputs"
    __table_args__ = (
        UniqueConstraint(
            "period_start",
            name="uq_monthly_cash_flow_inputs_period",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    salaries: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    social_charges: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    investments_cash: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    loan_repayments_cash: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
