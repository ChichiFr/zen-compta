from collections.abc import Iterator
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import (
    BankAccount,
    BankConnection,
    BankConnectionStatus,
    BankTransaction,
    Invoice,
    InvoiceStatus,
    MonthlySales,
)
from app.services.home_dashboard_service import HomeDashboardService


@pytest.fixture
def db() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=engine
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def _add_sales(db: Session, period_start: date, sales_ht: str) -> None:
    db.add(
        MonthlySales(
            period_start=period_start,
            sales_ht=Decimal(sales_ht),
            vat_collected=Decimal("0.00"),
            sales_ttc=Decimal(sales_ht),
        )
    )
    db.flush()


def _add_invoice(
    db: Session,
    invoice_date: date | None,
    total_ht: str,
    status: InvoiceStatus = InvoiceStatus.VALIDATED,
) -> Invoice:
    invoice = Invoice(
        supplier_name="Metro",
        invoice_date=invoice_date,
        status=status,
        total_ht=Decimal(total_ht),
        total_tva=Decimal("0.00"),
        total_ttc=Decimal(total_ht),
    )
    db.add(invoice)
    db.flush()
    return invoice


def _add_linked_bank(db: Session) -> BankAccount:
    connection = BankConnection(
        provider="plaid",
        external_requisition_id="req-1",
        institution_id="ins-1",
        institution_name="Banque test",
        reference="ref-1",
        status=BankConnectionStatus.LINKED,
    )
    account = BankAccount(
        external_account_id="acc-1",
        name="Compte courant",
        currency="EUR",
    )
    connection.accounts.append(account)
    db.add(connection)
    db.flush()
    return account


def _add_transaction(
    db: Session,
    account: BankAccount,
    booking_date: date,
    amount: str,
    external_id: str,
) -> None:
    db.add(
        BankTransaction(
            account_id=account.id,
            external_id=external_id,
            booking_date=booking_date,
            amount=Decimal(amount),
            currency="EUR",
            description="TX",
        )
    )
    db.flush()


def test_summary_empty_returns_twelve_zero_months(db: Session) -> None:
    summary = HomeDashboardService(db).summary(date(2026, 7, 1))

    assert len(summary.monthly_series) == 12
    assert summary.monthly_series[0].month == date(2025, 8, 1)
    assert summary.monthly_series[-1].month == date(2026, 7, 1)
    assert all(
        point.sales_ht == Decimal("0.00") for point in summary.monthly_series
    )
    assert all(
        point.sales_prior_ht is None for point in summary.monthly_series
    )
    assert summary.bank_connected is False
    assert summary.bank_flow == []
    assert summary.unpaid_invoices_count == 0


def test_summary_maps_sales_to_months_with_prior_year(db: Session) -> None:
    _add_sales(db, date(2026, 7, 1), "12450.00")
    _add_sales(db, date(2025, 7, 1), "10400.00")
    _add_sales(db, date(2026, 6, 1), "11800.00")

    summary = HomeDashboardService(db).summary(date(2026, 7, 15))

    latest = summary.monthly_series[-1]
    assert latest.month == date(2026, 7, 1)
    assert latest.sales_ht == Decimal("12450.00")
    assert latest.sales_prior_ht == Decimal("10400.00")
    previous = summary.monthly_series[-2]
    assert previous.sales_ht == Decimal("11800.00")
    assert previous.sales_prior_ht is None


def test_summary_aggregates_validated_invoices_per_month(db: Session) -> None:
    _add_invoice(db, date(2026, 7, 3), "200.00")
    _add_invoice(db, date(2026, 7, 21), "150.50")
    _add_invoice(db, date(2026, 7, 10), "999.00", status=InvoiceStatus.NEEDS_REVIEW)
    _add_invoice(db, date(2025, 7, 5), "300.00")
    _add_invoice(db, None, "50.00")

    summary = HomeDashboardService(db).summary(date(2026, 7, 1))

    latest = summary.monthly_series[-1]
    assert latest.purchases_ht == Decimal("350.50")
    assert latest.purchases_prior_ht == Decimal("300.00")


def test_summary_bank_flow_is_cumulative(db: Session) -> None:
    account = _add_linked_bank(db)
    today = date.today()
    _add_transaction(db, account, today - timedelta(days=2), "-100.00", "tx-1")
    _add_transaction(db, account, today - timedelta(days=1), "250.00", "tx-2")
    _add_transaction(db, account, today - timedelta(days=1), "-50.00", "tx-3")
    _add_transaction(db, account, today - timedelta(days=60), "999.00", "tx-old")

    summary = HomeDashboardService(db).summary(date(2026, 7, 1))

    assert summary.bank_connected is True
    assert [point.cumulative_flow for point in summary.bank_flow] == [
        Decimal("-100.00"),
        Decimal("100.00"),
    ]
    assert summary.bank_net_flow == Decimal("100.00")


def test_summary_counts_unpaid_invoices(db: Session) -> None:
    _add_invoice(db, date.today() - timedelta(days=5), "342.00")

    summary = HomeDashboardService(db).summary(date(2026, 7, 1))

    assert summary.unpaid_invoices_count == 1
