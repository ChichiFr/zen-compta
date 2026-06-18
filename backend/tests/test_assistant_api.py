from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models import Invoice, InvoiceLine  # noqa: F401


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
    test_client.headers.update({"X-Internal-API-Token": "test-token"})
    try:
        yield test_client
    finally:
        settings.internal_api_token = original_token
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)


def test_assistant_review_empty(client: TestClient) -> None:
    response = client.get("/api/assistant/review")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0
    assert data["invoices"] == []
    assert isinstance(data["summary_text"], str)


def test_assistant_dashboard(client: TestClient) -> None:
    response = client.get(
        "/api/assistant/dashboard",
        params={"period_start": "2026-06-01", "opening_cash": "5000"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "dashboard" in data
    assert "summary_text" in data
    assert isinstance(data["alerts"], list)


def test_assistant_health_brief(client: TestClient) -> None:
    response = client.get(
        "/api/assistant/health-brief",
        params={"period_start": "2026-06-01", "opening_cash": "5000"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "text" in data
    assert data["risk_level"] in ("ok", "warning", "critical")


def test_assistant_validate_not_found(client: TestClient) -> None:
    response = client.post(
        "/api/assistant/validate/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404


def test_assistant_review_with_invoice(client: TestClient) -> None:
    client.post(
        "/api/invoices",
        json={
            "supplier_name": "Metro",
            "invoice_date": "2026-06-10",
            "source": "ai_upload",
            "lines": [
                {
                    "description": "Legumes",
                    "category": "raw_materials_5_5",
                    "vat_rate": "5.5",
                    "amount_ht": "100.00",
                }
            ],
        },
    )
    response = client.get("/api/assistant/review")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] >= 1
    assert any(
        inv["supplier_name"] == "Metro" for inv in data["invoices"]
    )


def test_assistant_validate_success(client: TestClient) -> None:
    create_response = client.post(
        "/api/invoices",
        json={
            "supplier_name": "Metro",
            "invoice_date": "2026-06-10",
            "source": "manual",
            "lines": [
                {
                    "description": "Legumes",
                    "category": "raw_materials_5_5",
                    "vat_rate": "5.5",
                    "amount_ht": "100.00",
                }
            ],
        },
    )
    invoice_id = create_response.json()["id"]

    response = client.post(f"/api/assistant/validate/{invoice_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["invoice"]["status"] == "validated"
    assert "validee" in data["summary_text"].lower()
