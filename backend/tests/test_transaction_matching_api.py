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
    Invoice,
    InvoiceStatus,
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


def _seed(client: TestClient) -> tuple[str, str]:
    """Create one unmatched debit transaction and one validated invoice."""
    session_local = client.testing_session_local  # type: ignore[attr-defined]
    db = session_local()
    try:
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
        transaction = BankTransaction(
            account_id=account.id,
            external_id="tx-1",
            booking_date=date(2026, 6, 12),
            amount=Decimal("-342.00"),
            currency="EUR",
            description="CB METRO NANTERRE",
        )
        invoice = Invoice(
            supplier_name="Metro",
            invoice_date=date(2026, 6, 10),
            status=InvoiceStatus.VALIDATED,
            total_ht=Decimal("285.00"),
            total_tva=Decimal("57.00"),
            total_ttc=Decimal("342.00"),
        )
        db.add_all([transaction, invoice])
        db.commit()
        return str(transaction.id), str(invoice.id)
    finally:
        db.close()


def test_run_matching_links_transaction(client: TestClient) -> None:
    transaction_id, invoice_id = _seed(client)

    response = client.post("/api/bank/matching/run")

    assert response.status_code == 200
    assert response.json()["matched_count"] == 1

    session_local = client.testing_session_local  # type: ignore[attr-defined]
    db = session_local()
    try:
        transaction = db.get(BankTransaction, UUID(transaction_id))
        assert transaction is not None
        assert str(transaction.matched_invoice_id) == invoice_id
        assert transaction.match_source == "auto"
    finally:
        db.close()


def test_match_suggestions_returns_candidates(client: TestClient) -> None:
    transaction_id, invoice_id = _seed(client)

    response = client.get(
        f"/api/bank/transactions/{transaction_id}/match-suggestions"
    )

    assert response.status_code == 200
    suggestions = response.json()
    assert len(suggestions) == 1
    assert suggestions[0]["id"] == invoice_id
    assert suggestions[0]["supplier_name"] == "Metro"
    assert suggestions[0]["total_ttc"] == "342.00"


def test_manual_match_and_unmatch(client: TestClient) -> None:
    transaction_id, invoice_id = _seed(client)

    matched = client.patch(
        f"/api/bank/transactions/{transaction_id}/match",
        json={"invoice_id": invoice_id},
    )
    assert matched.status_code == 200
    assert matched.json()["matched_invoice_id"] == invoice_id
    assert matched.json()["match_source"] == "manual"

    unmatched = client.delete(f"/api/bank/transactions/{transaction_id}/match")
    assert unmatched.status_code == 200
    assert unmatched.json()["matched_invoice_id"] is None
    assert unmatched.json()["match_source"] is None


def test_manual_match_rejects_unknown_invoice(client: TestClient) -> None:
    transaction_id, _ = _seed(client)

    response = client.patch(
        f"/api/bank/transactions/{transaction_id}/match",
        json={"invoice_id": "00000000-0000-0000-0000-000000000000"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "invoice_not_matchable"


def test_match_missing_transaction_returns_404(client: TestClient) -> None:
    _seed(client)

    response = client.patch(
        "/api/bank/transactions/00000000-0000-0000-0000-000000000000/match",
        json={"invoice_id": "00000000-0000-0000-0000-000000000000"},
    )

    assert response.status_code == 404
