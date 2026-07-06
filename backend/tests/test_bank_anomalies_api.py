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


def _seed(client: TestClient) -> None:
    session_local = client.testing_session_local  # type: ignore[attr-defined]
    with session_local() as db:
        db.add_all(
            [
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
    assert response.json() == {"unpaid_invoices_count": 2}


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


def test_unpaid_invoices_are_sorted_date_desc(client: TestClient) -> None:
    _seed(client)

    invoices = client.get("/api/bank/anomalies/unpaid-invoices").json()

    assert [invoice["invoice_date"] for invoice in invoices] == sorted(
        [invoice["invoice_date"] for invoice in invoices],
        reverse=True,
    )
