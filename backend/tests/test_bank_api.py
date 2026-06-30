from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes import bank as bank_routes
from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models import BankAccount, BankConnection, BankTransaction  # noqa: F401
from app.services.bank_aggregator import (
    AccountInfo,
    BankAggregator,
    RequisitionResult,
    TransactionInfo,
)
from app.services.bank_service import BankService


class FakeBankAggregator(BankAggregator):
    last_session_data: dict | None = None
    last_public_token: str | None = None

    def create_requisition(
        self,
        *,
        institution_id: str,
        reference: str,
        redirect_uri: str,
    ) -> RequisitionResult:
        return RequisitionResult(
            requisition_id="fake-requisition",
            auth_link="https://bank.example/auth",
            expires_at=None,
            session_data={"auth_token": "fake-token", "id_user": "fake-user"},
        )

    def get_requisition_accounts(
        self,
        requisition_id: str,
        session_data: dict | None = None,
    ) -> list[str]:
        FakeBankAggregator.last_session_data = session_data
        assert requisition_id in {"fake-requisition", "powens-conn-42", "item-123"}
        return ["fake-account"]

    def get_account_metadata(
        self,
        external_account_id: str,
        session_data: dict | None = None,
    ) -> AccountInfo:
        FakeBankAggregator.last_session_data = session_data
        assert external_account_id == "fake-account"
        return AccountInfo(
            external_account_id="fake-account",
            iban_last4="1234",
            name="Compte courant",
            currency="EUR",
        )

    def fetch_transactions(
        self,
        *,
        external_account_id: str,
        date_from: date,
        session_data: dict | None = None,
    ) -> list[TransactionInfo]:
        FakeBankAggregator.last_session_data = session_data
        assert external_account_id == "fake-account"
        return [
            TransactionInfo(
                external_id="tx-newer",
                booking_date=date(2026, 6, 10),
                value_date=date(2026, 6, 10),
                amount=Decimal("125.50"),
                currency="EUR",
                description="VIREMENT CLIENT",
                creditor_name=None,
                debtor_name="Client",
                raw_payload={"transactionId": "tx-newer"},
            ),
            TransactionInfo(
                external_id="tx-older",
                booking_date=date(2026, 6, 1),
                value_date=None,
                amount=Decimal("-42.00"),
                currency="EUR",
                description="CB FOURNISSEUR",
                creditor_name="Fournisseur",
                debtor_name=None,
                raw_payload={"transactionId": "tx-older"},
            ),
        ]

    def exchange_public_token(self, public_token: str) -> dict:
        FakeBankAggregator.last_public_token = public_token
        return {"access_token": "plaid-access-token", "item_id": "item-123"}


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

    def override_get_bank_service() -> Iterator[BankService]:
        db = TestingSessionLocal()
        try:
            service = BankService(db)
            service.aggregator = FakeBankAggregator()
            yield service
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[bank_routes.get_bank_service] = override_get_bank_service
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


def test_connect_creates_connection_and_returns_auth_link(client: TestClient) -> None:
    response = client.post("/api/bank/connect")

    assert response.status_code == 200
    body = response.json()
    assert body["auth_link"] == "https://bank.example/auth"
    assert body["connection"]["status"] == "created"
    assert body["connection"]["institution_id"] == "SANDBOXFINANCE_SFIN0000"


def test_callback_completes_connection(client: TestClient) -> None:
    created = client.post("/api/bank/connect").json()
    connection_id = created["connection"]["id"]
    reference = _connection_reference(client, connection_id)

    response = client.get("/api/bank/callback", params={"ref": reference})

    assert response.status_code == 200
    assert response.json()["status"] == "linked"


def test_callback_accepts_powens_connection_id(client: TestClient) -> None:
    created = client.post("/api/bank/connect").json()
    connection_id = created["connection"]["id"]
    reference = _connection_reference(client, connection_id)

    response = client.get(
        "/api/bank/callback",
        params={"ref": reference, "connection_id": "powens-conn-42"},
    )

    assert response.status_code == 200
    session_factory = client.testing_session_local  # type: ignore[attr-defined]
    with session_factory() as db:
        db_connection = db.get(BankConnection, UUID(connection_id))
        assert db_connection is not None
        assert db_connection.external_requisition_id == "powens-conn-42"


def test_callback_post_accepts_plaid_public_token(client: TestClient) -> None:
    FakeBankAggregator.last_public_token = None
    created = client.post("/api/bank/connect").json()
    connection_id = created["connection"]["id"]
    reference = _connection_reference(client, connection_id)

    response = client.post(
        "/api/bank/callback",
        json={"ref": reference, "public_token": "public-sandbox-token"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "linked"
    assert FakeBankAggregator.last_public_token == "public-sandbox-token"
    session_factory = client.testing_session_local  # type: ignore[attr-defined]
    with session_factory() as db:
        db_connection = db.get(BankConnection, UUID(connection_id))
        assert db_connection is not None
        assert db_connection.external_requisition_id == "item-123"
        assert db_connection.provider_session_data == {
            "access_token": "plaid-access-token",
            "item_id": "item-123",
        }


def test_provider_session_data_is_persisted_and_passed(
    client: TestClient,
) -> None:
    FakeBankAggregator.last_session_data = None
    created = client.post("/api/bank/connect").json()
    connection_id = created["connection"]["id"]
    reference = _connection_reference(client, connection_id)
    session_factory = client.testing_session_local  # type: ignore[attr-defined]

    with session_factory() as db:
        db_connection = db.get(BankConnection, UUID(connection_id))
        assert db_connection is not None
        assert db_connection.provider_session_data == {
            "auth_token": "fake-token",
            "id_user": "fake-user",
        }

    callback_response = client.get(
        "/api/bank/callback",
        params={"ref": reference},
    )

    assert callback_response.status_code == 200
    assert FakeBankAggregator.last_session_data == {
        "auth_token": "fake-token",
        "id_user": "fake-user",
    }

    FakeBankAggregator.last_session_data = None
    sync_response = client.post(f"/api/bank/connections/{connection_id}/sync")

    assert sync_response.status_code == 200
    assert FakeBankAggregator.last_session_data == {
        "auth_token": "fake-token",
        "id_user": "fake-user",
    }


def test_callback_is_idempotent_when_already_linked(client: TestClient) -> None:
    created = client.post("/api/bank/connect").json()
    connection_id = created["connection"]["id"]
    reference = _connection_reference(client, connection_id)

    first = client.get("/api/bank/callback", params={"ref": reference})
    second = client.get("/api/bank/callback", params={"ref": reference})

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["status"] == "linked"
    assert second.json()["status"] == "linked"
    # A second callback must not duplicate accounts.
    connections = client.get("/api/bank/connections").json()
    assert len(connections) == 1


def test_sync_transactions_is_idempotent(client: TestClient) -> None:
    connection_id = _linked_connection_id(client)

    first_response = client.post(f"/api/bank/connections/{connection_id}/sync")
    second_response = client.post(f"/api/bank/connections/{connection_id}/sync")

    assert first_response.status_code == 200
    assert first_response.json()["new_transactions_count"] == 2
    assert first_response.json()["total_transactions_count"] == 2
    assert second_response.status_code == 200
    assert second_response.json()["new_transactions_count"] == 0
    assert second_response.json()["total_transactions_count"] == 2


def test_list_transactions_returns_descending_dates(client: TestClient) -> None:
    connection_id = _linked_connection_id(client)
    client.post(f"/api/bank/connections/{connection_id}/sync")

    response = client.get(f"/api/bank/connections/{connection_id}/transactions")

    assert response.status_code == 200
    transactions = response.json()
    assert [transaction["booking_date"] for transaction in transactions] == [
        "2026-06-10",
        "2026-06-01",
    ]
    assert transactions[0]["description"] == "VIREMENT CLIENT"


def _linked_connection_id(client: TestClient) -> str:
    created = client.post("/api/bank/connect").json()
    connection_id = created["connection"]["id"]
    reference = _connection_reference(client, connection_id)
    client.get("/api/bank/callback", params={"ref": reference})
    return connection_id


def _connection_reference(client: TestClient, connection_id: str) -> str:
    response = client.get("/api/bank/connections")
    assert response.status_code == 200
    for connection in response.json():
        if connection["id"] == connection_id:
            session_factory = client.testing_session_local  # type: ignore[attr-defined]
            with session_factory() as db:
                db_connection = db.get(BankConnection, UUID(connection_id))
                assert db_connection is not None
                return db_connection.reference
    raise AssertionError("connection not found")
