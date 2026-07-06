from collections.abc import Iterator
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

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
)
from app.services.bank_anomaly_service import BankAnomalyService

_DEFAULT_INVOICE_DATE = object()


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


def _recent_date(days_ago: int = 10) -> date:
    return date.today() - timedelta(days=days_ago)


def _old_date() -> date:
    return date.today() - timedelta(days=365)


def _make_account(db: Session) -> BankAccount:
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


def _make_transaction(
    db: Session,
    account: BankAccount,
    *,
    amount: str,
    booking_date: date,
    external_id: str = "tx-1",
    description: str = "CB METRO",
    matched_invoice_id: UUID | None = None,
) -> BankTransaction:
    transaction = BankTransaction(
        account_id=account.id,
        external_id=external_id,
        booking_date=booking_date,
        amount=Decimal(amount),
        currency="EUR",
        description=description,
        matched_invoice_id=matched_invoice_id,
    )
    db.add(transaction)
    db.flush()
    return transaction


def _make_invoice(
    db: Session,
    *,
    supplier_name: str = "Metro",
    invoice_date: date | None | object = _DEFAULT_INVOICE_DATE,
    invoice_number: str | None = "F-001",
    total_ttc: str = "342.00",
    status: InvoiceStatus = InvoiceStatus.VALIDATED,
) -> Invoice:
    invoice = Invoice(
        supplier_name=supplier_name,
        invoice_date=(
            _recent_date()
            if invoice_date is _DEFAULT_INVOICE_DATE
            else invoice_date
        ),
        invoice_number=invoice_number,
        status=status,
        total_ht=Decimal("285.00"),
        total_tva=Decimal("57.00"),
        total_ttc=Decimal(total_ttc),
    )
    db.add(invoice)
    db.flush()
    return invoice


def test_summary_empty(db: Session) -> None:
    summary = BankAnomalyService(db).summary()

    assert summary.unpaid_invoices_count == 0


def test_unpaid_invoices_ignores_non_validated(db: Session) -> None:
    _make_invoice(db, status=InvoiceStatus.NEEDS_REVIEW)

    assert BankAnomalyService(db).list_unpaid_invoices() == []


def test_unpaid_invoices_ignores_matched(db: Session) -> None:
    account = _make_account(db)
    invoice = _make_invoice(db)
    _make_transaction(
        db,
        account,
        amount="-342.00",
        booking_date=_recent_date(),
        matched_invoice_id=invoice.id,
    )

    assert BankAnomalyService(db).list_unpaid_invoices() == []


def test_unpaid_invoices_ignores_old(db: Session) -> None:
    _make_invoice(db, invoice_date=_old_date())

    assert BankAnomalyService(db).list_unpaid_invoices() == []


def test_unpaid_invoices_ignores_missing_date(db: Session) -> None:
    _make_invoice(db, invoice_date=None)

    assert BankAnomalyService(db).list_unpaid_invoices() == []


def test_summary_returns_correct_counts(db: Session) -> None:
    for index in range(2):
        _make_invoice(db, supplier_name=f"Supplier {index}")

    summary = BankAnomalyService(db).summary()

    assert summary.unpaid_invoices_count == 2
