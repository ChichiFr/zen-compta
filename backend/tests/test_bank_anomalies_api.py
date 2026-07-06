from collections.abc import Iterator
from datetime import date, timedelta
from decimal import Decimal

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


def _recent_date(days_ago: int = 10) -> date:
    return date.today() - timedelta(days=days_ago)


def _seed_account(db: Session) -> BankAccount:
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


def _seed(client: TestClient) -> None:
    session_local = client.testing_session_local  # type: ignore[attr-defined]
    with session_local() as db:
        account = _seed_account(db)
        db.add_all(
            [
                BankTransaction(
                    account_id=account.id,
                    external_id="tx-new",
                    booking_date=_recent_date(2),
                    amount=Decimal("-42.00"),
                    currency="EUR",
                    description="CB METRO",
                    category_code="raw_materials_5_5",
                ),
                BankTransaction(
                    account_id=account.id,
                    external_id="tx-old",
                    booking_date=_recent_date(12),
                    amount=Decimal("-84.00"),
                    currency="EUR",
                    description="CB PROMOCASH",
                ),
                Invoice(
                    supplier_name="Metro",
                    invoice_date=_recent_date(1),
                    invoice_number="M-001",
                    status=InvoiceStatus.VALIDATED,
                    total_ht=Decimal("285.00"),
                    total_tva=Decimal("57.00"),
                    total_ttc=Decimal("342.00"),
                ),
                Invoice(
                    supplier_name="Sysco",
                    invoice_date=_recent_date(9),
                    invoice_number="S-001",
                    status=InvoiceStatus.VALIDATED,
                    total_ht=Decimal("100.00"),
                    total_tva=Decimal("20.00"),
                    total_ttc=Decimal("120.00"),
                ),
            ]
        )
        db.commit()


def test_summary_endpoint_returns_counts(client: TestClient) -> None:
    _seed(client)

    response = client.get("/api/bank/anomalies/summary")

    assert response.status_code == 200
    assert response.json() == {
        "unmatched_debits_count": 2,
        "unpaid_invoices_count": 2,
    }


def test_unmatched_debits_endpoint_returns_list(client: TestClient) -> None:
    _seed(client)

    response = client.get("/api/bank/anomalies/unmatched-debits")

    assert response.status_code == 200
    debits = response.json()
    assert [debit["description"] for debit in debits] == [
        "CB METRO",
        "CB PROMOCASH",
    ]
    assert debits[0]["amount"] == "-42.00"
    assert debits[0]["category_code"] == "raw_materials_5_5"


def test_unpaid_invoices_endpoint_returns_list(client: TestClient) -> None:
    _seed(client)

    response = client.get("/api/bank/anomalies/unpaid-invoices")

    assert response.status_code == 200
    invoices = response.json()
    assert [invoice["supplier_name"] for invoice in invoices] == [
        "Metro",
        "Sysco",
    ]
    assert invoices[0]["invoice_number"] == "M-001"
    assert invoices[0]["total_ttc"] == "342.00"


def test_anomalies_lists_are_sorted_date_desc(client: TestClient) -> None:
    _seed(client)

    debits = client.get("/api/bank/anomalies/unmatched-debits").json()
    invoices = client.get("/api/bank/anomalies/unpaid-invoices").json()

    assert [debit["booking_date"] for debit in debits] == sorted(
        [debit["booking_date"] for debit in debits],
        reverse=True,
    )
    assert [invoice["invoice_date"] for invoice in invoices] == sorted(
        [invoice["invoice_date"] for invoice in invoices],
        reverse=True,
    )
