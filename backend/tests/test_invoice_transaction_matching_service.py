from collections.abc import Iterator
from datetime import date
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
)
from app.services.invoice_transaction_matching_service import (
    InvoiceNotMatchableError,
    InvoiceTransactionMatchingService,
    TransactionNotMatchableError,
)


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
    description: str = "CB PAIEMENT",
    external_id: str = "tx-1",
) -> BankTransaction:
    transaction = BankTransaction(
        account_id=account.id,
        external_id=external_id,
        booking_date=booking_date,
        amount=Decimal(amount),
        currency="EUR",
        description=description,
    )
    db.add(transaction)
    db.flush()
    return transaction


def _make_invoice(
    db: Session,
    *,
    supplier_name: str = "Metro",
    invoice_date: date | None = date(2026, 6, 10),
    total_ttc: str = "342.00",
    status: InvoiceStatus = InvoiceStatus.VALIDATED,
) -> Invoice:
    invoice = Invoice(
        supplier_name=supplier_name,
        invoice_date=invoice_date,
        status=status,
        total_ht=Decimal("285.00"),
        total_tva=Decimal("57.00"),
        total_ttc=Decimal(total_ttc),
    )
    db.add(invoice)
    db.flush()
    return invoice


def test_auto_match_exact_single_candidate(db: Session) -> None:
    account = _make_account(db)
    invoice = _make_invoice(db)
    transaction = _make_transaction(
        db,
        account,
        amount="-342.00",
        booking_date=date(2026, 6, 12),
        description="CB METRO NANTERRE",
    )

    matched = InvoiceTransactionMatchingService(db).auto_match_all()

    assert matched == 1
    assert transaction.matched_invoice_id == invoice.id
    assert transaction.match_source == "auto"


def test_auto_match_skips_ambiguous_amounts(db: Session) -> None:
    account = _make_account(db)
    _make_invoice(db, supplier_name="Metro")
    _make_invoice(db, supplier_name="Promocash")
    transaction = _make_transaction(
        db,
        account,
        amount="-342.00",
        booking_date=date(2026, 6, 12),
        description="CB PAIEMENT SANS NOM",
    )

    matched = InvoiceTransactionMatchingService(db).auto_match_all()

    assert matched == 0
    assert transaction.matched_invoice_id is None


def test_auto_match_disambiguates_by_supplier_name(db: Session) -> None:
    account = _make_account(db)
    metro = _make_invoice(db, supplier_name="Metro")
    _make_invoice(db, supplier_name="Promocash")
    transaction = _make_transaction(
        db,
        account,
        amount="-342.00",
        booking_date=date(2026, 6, 12),
        description="CB METRO NANTERRE",
    )

    matched = InvoiceTransactionMatchingService(db).auto_match_all()

    assert matched == 1
    assert transaction.matched_invoice_id == metro.id


def test_auto_match_supplier_name_ignores_accents_and_case(db: Session) -> None:
    account = _make_account(db)
    invoice = _make_invoice(db, supplier_name="Boulangerie Andrée")
    _make_invoice(db, supplier_name="Promocash")
    transaction = _make_transaction(
        db,
        account,
        amount="-342.00",
        booking_date=date(2026, 6, 12),
        description="CB BOULANGERIE ANDREE PARIS",
    )

    matched = InvoiceTransactionMatchingService(db).auto_match_all()

    assert matched == 1
    assert transaction.matched_invoice_id == invoice.id


def test_auto_match_respects_date_window(db: Session) -> None:
    account = _make_account(db)
    _make_invoice(db, invoice_date=date(2026, 3, 1))
    transaction = _make_transaction(
        db,
        account,
        amount="-342.00",
        booking_date=date(2026, 6, 12),
    )

    matched = InvoiceTransactionMatchingService(db).auto_match_all()

    assert matched == 0
    assert transaction.matched_invoice_id is None


def test_auto_match_skips_credits(db: Session) -> None:
    account = _make_account(db)
    _make_invoice(db)
    transaction = _make_transaction(
        db,
        account,
        amount="342.00",
        booking_date=date(2026, 6, 12),
    )

    matched = InvoiceTransactionMatchingService(db).auto_match_all()

    assert matched == 0
    assert transaction.matched_invoice_id is None


def test_auto_match_skips_non_validated_invoices(db: Session) -> None:
    account = _make_account(db)
    _make_invoice(db, status=InvoiceStatus.NEEDS_REVIEW)
    transaction = _make_transaction(
        db,
        account,
        amount="-342.00",
        booking_date=date(2026, 6, 12),
    )

    matched = InvoiceTransactionMatchingService(db).auto_match_all()

    assert matched == 0
    assert transaction.matched_invoice_id is None


def test_auto_match_does_not_reuse_matched_invoice(db: Session) -> None:
    account = _make_account(db)
    invoice = _make_invoice(db)
    first = _make_transaction(
        db,
        account,
        amount="-342.00",
        booking_date=date(2026, 6, 12),
        external_id="tx-1",
    )
    second = _make_transaction(
        db,
        account,
        amount="-342.00",
        booking_date=date(2026, 6, 13),
        external_id="tx-2",
    )

    matched = InvoiceTransactionMatchingService(db).auto_match_all()

    assert matched == 1
    linked = [
        tx for tx in (first, second) if tx.matched_invoice_id == invoice.id
    ]
    assert len(linked) == 1


def test_suggestions_sorted_best_first(db: Session) -> None:
    account = _make_account(db)
    exact_named = _make_invoice(
        db, supplier_name="Metro", invoice_date=date(2026, 6, 10)
    )
    exact_far = _make_invoice(
        db, supplier_name="Promocash", invoice_date=date(2026, 5, 1)
    )
    approx = _make_invoice(
        db,
        supplier_name="Sysco",
        invoice_date=date(2026, 6, 11),
        total_ttc="340.00",
    )
    transaction = _make_transaction(
        db,
        account,
        amount="-342.00",
        booking_date=date(2026, 6, 12),
        description="CB METRO NANTERRE",
    )

    suggestions = InvoiceTransactionMatchingService(db).suggestions(transaction)

    assert [invoice.id for invoice in suggestions] == [
        exact_named.id,
        exact_far.id,
        approx.id,
    ]


def test_suggestions_empty_for_credit(db: Session) -> None:
    account = _make_account(db)
    _make_invoice(db)
    transaction = _make_transaction(
        db,
        account,
        amount="342.00",
        booking_date=date(2026, 6, 12),
    )

    suggestions = InvoiceTransactionMatchingService(db).suggestions(transaction)

    assert suggestions == []


def test_match_manually_rejects_non_validated_invoice(db: Session) -> None:
    account = _make_account(db)
    invoice = _make_invoice(db, status=InvoiceStatus.NEEDS_REVIEW)
    transaction = _make_transaction(
        db,
        account,
        amount="-342.00",
        booking_date=date(2026, 6, 12),
    )

    with pytest.raises(InvoiceNotMatchableError):
        InvoiceTransactionMatchingService(db).match_manually(
            transaction, invoice.id
        )


def test_match_manually_rejects_credit_transaction(db: Session) -> None:
    account = _make_account(db)
    invoice = _make_invoice(db)
    transaction = _make_transaction(
        db,
        account,
        amount="342.00",
        booking_date=date(2026, 6, 12),
    )

    with pytest.raises(TransactionNotMatchableError):
        InvoiceTransactionMatchingService(db).match_manually(
            transaction, invoice.id
        )


def test_unmatch_clears_link(db: Session) -> None:
    account = _make_account(db)
    invoice = _make_invoice(db)
    transaction = _make_transaction(
        db,
        account,
        amount="-342.00",
        booking_date=date(2026, 6, 12),
    )
    service = InvoiceTransactionMatchingService(db)
    service.match_manually(transaction, invoice.id)
    assert transaction.matched_invoice_id == invoice.id

    service.unmatch(transaction)

    assert transaction.matched_invoice_id is None
    assert transaction.match_source is None
