from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models import (
    BankAccount,
    BankConnection,
    BankConnectionStatus,
    BankTransaction,
    BankTransactionRule,
)


@pytest.fixture
def client() -> Iterator[TestClient]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=engine
    )
    Base.metadata.create_all(bind=engine)

    def override_get_db() -> Iterator[Session]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    original_token = settings.internal_api_token
    settings.internal_api_token = "test-token"
    test_client = TestClient(app)
    test_client.testing_session_local = TestingSessionLocal  # type: ignore[attr-defined]
    test_client.headers.update({"X-Internal-API-Token": "test-token"})
    try:
        yield test_client
    finally:
        settings.internal_api_token = original_token
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)


def _seed_transaction(
    client: TestClient,
    description: str = "PAIEMENT METRO 342",
    external_id: str = "tx-1",
) -> str:
    session_local = client.testing_session_local  # type: ignore[attr-defined]
    db = session_local()
    try:
        connection = db.query(BankConnection).one_or_none()
        if connection is None:
            connection = BankConnection(
                provider="plaid",
                external_requisition_id="req-1",
                institution_id="ins-1",
                institution_name="Banque test",
                reference="ref-1",
                status=BankConnectionStatus.LINKED,
            )
            connection.accounts.append(
                BankAccount(
                    external_account_id="acc-1",
                    name="Compte courant",
                    currency="EUR",
                )
            )
            db.add(connection)
            db.flush()
        account = connection.accounts[0]
        transaction = BankTransaction(
            account_id=account.id,
            external_id=external_id,
            booking_date=date(2026, 6, 15),
            amount=Decimal("-42.00"),
            currency="EUR",
            description=description,
        )
        db.add(transaction)
        db.commit()
        return str(transaction.id)
    finally:
        db.close()


def test_list_rules_empty(client: TestClient) -> None:
    response = client.get("/api/bank/transaction-rules")

    assert response.status_code == 200
    assert response.json() == []


def test_update_transaction_category_manual(client: TestClient) -> None:
    transaction_id = _seed_transaction(client)

    response = client.patch(
        f"/api/bank/transactions/{transaction_id}/category",
        json={"category_code": "raw_materials_5_5"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["category_code"] == "raw_materials_5_5"
    assert body["category_source"] == "manual"
    assert client.get("/api/bank/transaction-rules").json() == []


def test_update_transaction_category_with_create_rule(client: TestClient) -> None:
    target_id = _seed_transaction(client, "CB METRO NANTERRE", "tx-target")
    sibling_id = _seed_transaction(client, "PAIEMENT METRO 89", "tx-sibling")
    unrelated_id = _seed_transaction(client, "EDF FACTURE", "tx-unrelated")

    response = client.patch(
        f"/api/bank/transactions/{target_id}/category",
        json={
            "category_code": "raw_materials_5_5",
            "create_rule": True,
            "rule_pattern": "METRO",
        },
    )

    assert response.status_code == 200
    assert response.json()["category_source"] == "manual"

    rules = client.get("/api/bank/transaction-rules").json()
    assert len(rules) == 1
    assert rules[0]["pattern"] == "METRO"
    assert rules[0]["category_code"] == "raw_materials_5_5"

    session_local = client.testing_session_local  # type: ignore[attr-defined]
    db = session_local()
    try:
        sibling = db.get(BankTransaction, UUID(sibling_id))
        unrelated = db.get(BankTransaction, UUID(unrelated_id))
        assert sibling is not None and unrelated is not None
        assert sibling.category_code == "raw_materials_5_5"
        assert sibling.category_source == "rule"
        assert unrelated.category_code is None
    finally:
        db.close()


def test_update_transaction_category_unknown_returns_400(
    client: TestClient,
) -> None:
    transaction_id = _seed_transaction(client)

    response = client.patch(
        f"/api/bank/transactions/{transaction_id}/category",
        json={"category_code": "not_a_category"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "unknown_category"


def test_update_transaction_category_duplicate_rule_returns_409(
    client: TestClient,
) -> None:
    first_id = _seed_transaction(client, "CB METRO 1", "tx-1")
    second_id = _seed_transaction(client, "CB METRO 2", "tx-2")
    client.patch(
        f"/api/bank/transactions/{first_id}/category",
        json={
            "category_code": "raw_materials_5_5",
            "create_rule": True,
            "rule_pattern": "METRO",
        },
    )

    response = client.patch(
        f"/api/bank/transactions/{second_id}/category",
        json={
            "category_code": "business_meals",
            "create_rule": True,
            "rule_pattern": "METRO",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "duplicate_rule_pattern"


def test_update_missing_transaction_returns_404(client: TestClient) -> None:
    response = client.patch(
        "/api/bank/transactions/00000000-0000-0000-0000-000000000000/category",
        json={"category_code": "raw_materials_5_5"},
    )

    assert response.status_code == 404


def test_delete_rule_keeps_categories_but_detaches_rule(
    client: TestClient,
) -> None:
    transaction_id = _seed_transaction(client, "CB METRO", "tx-1")
    client.patch(
        f"/api/bank/transactions/{transaction_id}/category",
        json={
            "category_code": "raw_materials_5_5",
            "create_rule": True,
            "rule_pattern": "METRO",
        },
    )
    sibling_id = _seed_transaction(client, "METRO AGAIN", "tx-2")
    # Recategorize the sibling through a second rule-creating call on it.
    client.patch(
        f"/api/bank/transactions/{sibling_id}/category",
        json={"category_code": "raw_materials_5_5"},
    )
    rules = client.get("/api/bank/transaction-rules").json()
    rule_id = rules[0]["id"]

    response = client.delete(f"/api/bank/transaction-rules/{rule_id}")

    assert response.status_code == 204
    assert client.get("/api/bank/transaction-rules").json() == []

    session_local = client.testing_session_local  # type: ignore[attr-defined]
    db = session_local()
    try:
        transaction = db.get(BankTransaction, UUID(transaction_id))
        assert transaction is not None
        assert transaction.category_code == "raw_materials_5_5"
        assert transaction.category_rule_id is None
        assert db.query(BankTransactionRule).count() == 0
    finally:
        db.close()


def test_delete_missing_rule_returns_404(client: TestClient) -> None:
    response = client.delete(
        "/api/bank/transaction-rules/00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404
