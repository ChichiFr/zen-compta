from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

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
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)


def test_create_invoice_returns_draft_with_calculated_totals(client: TestClient):
    response = client.post(
        "/api/invoices",
        json={
            "supplier_name": "Metro",
            "invoice_date": "2026-05-01",
            "invoice_number": "M-001",
            "lines": [
                {
                    "description": "Matieres premieres",
                    "category": "601",
                    "vat_rate": "10",
                    "amount_ht": "100.00",
                },
                {
                    "description": "Materiel",
                    "category": "606",
                    "vat_rate": "20",
                    "amount_ht": "50.00",
                },
            ],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "draft"
    assert body["source"] == "manual"
    assert body["total_ht"] == "150.00"
    assert body["total_tva"] == "20.00"
    assert body["total_ttc"] == "170.00"
    assert len(body["lines"]) == 2


def test_create_invoice_marks_mismatch_as_needs_review(client: TestClient):
    response = client.post(
        "/api/invoices",
        json={
            "supplier_name": "EDF",
            "invoice_date": "2026-05-02",
            "lines": [
                {
                    "description": "Electricite",
                    "vat_rate": "20",
                    "amount_ht": "100.00",
                    "amount_tva": "21.00",
                }
            ],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "needs_review"
    assert body["lines"][0]["needs_review_reason"] == "vat_amount_mismatch"


def test_validate_invoice_changes_status_when_complete(client: TestClient):
    created = client.post(
        "/api/invoices",
        json={
            "supplier_name": "Metro",
            "invoice_date": "2026-05-01",
            "lines": [
                {
                    "description": "Achats",
                    "vat_rate": "10",
                    "amount_ht": "100.00",
                }
            ],
        },
    ).json()

    response = client.post(f"/api/invoices/{created['id']}/validate")

    assert response.status_code == 200
    assert response.json()["status"] == "validated"


def test_validate_invoice_returns_errors_when_incomplete(client: TestClient):
    created = client.post(
        "/api/invoices",
        json={
            "supplier_name": "Metro",
            "lines": [
                {
                    "description": "Achats",
                    "vat_rate": "10",
                    "amount_ht": "100.00",
                }
            ],
        },
    ).json()

    response = client.post(f"/api/invoices/{created['id']}/validate")

    assert response.status_code == 422
    assert response.json()["detail"] == {"errors": ["invoice_date_required"]}


def test_list_invoices_returns_created_invoices(client: TestClient):
    client.post(
        "/api/invoices",
        json={
            "supplier_name": "Metro",
            "invoice_date": "2026-05-01",
            "lines": [
                {
                    "description": "Achats",
                    "vat_rate": "10",
                    "amount_ht": "100.00",
                }
            ],
        },
    )

    response = client.get("/api/invoices")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["supplier_name"] == "Metro"


def test_list_invoices_can_filter_by_month(client: TestClient):
    client.post(
        "/api/invoices",
        json={
            "supplier_name": "May Supplier",
            "invoice_date": "2026-05-20",
            "lines": [
                {
                    "description": "Achats mai",
                    "vat_rate": "20",
                    "amount_ht": "100.00",
                }
            ],
        },
    )
    client.post(
        "/api/invoices",
        json={
            "supplier_name": "June Supplier",
            "invoice_date": "2026-06-01",
            "lines": [
                {
                    "description": "Achats juin",
                    "vat_rate": "20",
                    "amount_ht": "100.00",
                }
            ],
        },
    )

    response = client.get("/api/invoices", params={"period_start": "2026-05-01"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["supplier_name"] == "May Supplier"
