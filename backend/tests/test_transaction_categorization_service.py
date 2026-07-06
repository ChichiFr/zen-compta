from collections.abc import Iterator
from datetime import UTC, date, datetime
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
    BankTransactionRule,
)
from app.services.transaction_categorization_service import (
    DuplicateRulePatternError,
    EmptyRulePatternError,
    TransactionCategorizationService,
    UnknownCategoryError,
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
    description: str,
    external_id: str,
    category_code: str | None = None,
    category_source: str | None = None,
) -> BankTransaction:
    transaction = BankTransaction(
        account_id=account.id,
        external_id=external_id,
        booking_date=date(2026, 6, 15),
        amount=Decimal("-42.00"),
        currency="EUR",
        description=description,
        category_code=category_code,
        category_source=category_source,
    )
    db.add(transaction)
    db.flush()
    return transaction


def _make_rule(
    db: Session,
    pattern: str,
    category_code: str,
    created_at: datetime | None = None,
) -> BankTransactionRule:
    rule = BankTransactionRule(pattern=pattern, category_code=category_code)
    if created_at is not None:
        rule.created_at = created_at
    db.add(rule)
    db.flush()
    return rule


def test_categorize_transaction_no_rules(db: Session) -> None:
    account = _make_account(db)
    transaction = _make_transaction(db, account, "PAIEMENT METRO 342", "tx-1")

    TransactionCategorizationService(db).categorize_transaction(transaction)

    assert transaction.category_code is None
    assert transaction.category_source is None
    assert transaction.category_rule_id is None


def test_categorize_transaction_matching_rule(db: Session) -> None:
    account = _make_account(db)
    rule = _make_rule(db, "METRO", "raw_materials_5_5")
    transaction = _make_transaction(db, account, "PAIEMENT METRO 342 EUR", "tx-1")

    TransactionCategorizationService(db).categorize_transaction(transaction)

    assert transaction.category_code == "raw_materials_5_5"
    assert transaction.category_source == "rule"
    assert transaction.category_rule_id == rule.id


def test_categorize_transaction_case_insensitive(db: Session) -> None:
    account = _make_account(db)
    _make_rule(db, "metro", "raw_materials_5_5")
    transaction = _make_transaction(db, account, "CB METRO NANTERRE", "tx-1")

    TransactionCategorizationService(db).categorize_transaction(transaction)

    assert transaction.category_code == "raw_materials_5_5"


def test_categorize_transaction_first_rule_wins(db: Session) -> None:
    account = _make_account(db)
    older = _make_rule(
        db,
        "METRO",
        "raw_materials_5_5",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    _make_rule(
        db,
        "METRO NANTERRE",
        "business_meals",
        created_at=datetime(2026, 2, 1, tzinfo=UTC),
    )
    transaction = _make_transaction(db, account, "CB METRO NANTERRE", "tx-1")

    TransactionCategorizationService(db).categorize_transaction(transaction)

    assert transaction.category_code == "raw_materials_5_5"
    assert transaction.category_rule_id == older.id


def test_categorize_transaction_manual_not_overwritten(db: Session) -> None:
    account = _make_account(db)
    _make_rule(db, "METRO", "raw_materials_5_5")
    transaction = _make_transaction(
        db,
        account,
        "PAIEMENT METRO",
        "tx-1",
        category_code="business_meals",
        category_source="manual",
    )

    TransactionCategorizationService(db).categorize_transaction(transaction)

    assert transaction.category_code == "business_meals"
    assert transaction.category_source == "manual"


def test_set_manual_category_rejects_unknown(db: Session) -> None:
    account = _make_account(db)
    transaction = _make_transaction(db, account, "PAIEMENT METRO", "tx-1")

    with pytest.raises(UnknownCategoryError):
        TransactionCategorizationService(db).set_manual_category(
            transaction, "not_a_category"
        )


def test_set_manual_category_clears_rule_link(db: Session) -> None:
    account = _make_account(db)
    rule = _make_rule(db, "METRO", "raw_materials_5_5")
    transaction = _make_transaction(
        db,
        account,
        "PAIEMENT METRO",
        "tx-1",
        category_code="raw_materials_5_5",
        category_source="rule",
    )
    transaction.category_rule_id = rule.id

    TransactionCategorizationService(db).set_manual_category(
        transaction, "business_meals"
    )

    assert transaction.category_code == "business_meals"
    assert transaction.category_source == "manual"
    assert transaction.category_rule_id is None


def test_create_rule_rejects_duplicate(db: Session) -> None:
    service = TransactionCategorizationService(db)
    service.create_rule("METRO", "raw_materials_5_5")

    with pytest.raises(DuplicateRulePatternError):
        service.create_rule("METRO", "business_meals")


def test_create_rule_rejects_empty_pattern(db: Session) -> None:
    service = TransactionCategorizationService(db)

    with pytest.raises(EmptyRulePatternError):
        service.create_rule("   ", "raw_materials_5_5")


def test_create_rule_rejects_unknown_category(db: Session) -> None:
    service = TransactionCategorizationService(db)

    with pytest.raises(UnknownCategoryError):
        service.create_rule("METRO", "not_a_category")


def test_recategorize_all_reapplies_to_history(db: Session) -> None:
    account = _make_account(db)
    matching_descriptions = ["CB METRO 12", "METRO NANTERRE", "PAIEMENT METRO"]
    for index, description in enumerate(matching_descriptions):
        _make_transaction(db, account, description, f"tx-match-{index}")
    _make_transaction(db, account, "EDF FACTURE", "tx-other-1")
    _make_transaction(
        db,
        account,
        "METRO MANUEL",
        "tx-manual",
        category_code="business_meals",
        category_source="manual",
    )

    service = TransactionCategorizationService(db)
    service.create_rule("METRO", "raw_materials_5_5")
    applied = service.recategorize_all()

    assert applied == 3
    categorized = [
        tx
        for tx in db.query(BankTransaction).all()
        if tx.category_code == "raw_materials_5_5"
    ]
    assert len(categorized) == 3
    manual = (
        db.query(BankTransaction)
        .filter(BankTransaction.external_id == "tx-manual")
        .one()
    )
    assert manual.category_code == "business_meals"
    assert manual.category_source == "manual"
