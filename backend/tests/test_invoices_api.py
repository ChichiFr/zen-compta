import csv
from collections.abc import Iterator
from io import BytesIO, StringIO
from zipfile import ZipFile

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


def test_update_invoice_before_validation_recalculates_totals(client: TestClient):
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

    response = client.put(
        f"/api/invoices/{created['id']}",
        json={
            "supplier_name": "Metro corrige",
            "invoice_date": "2026-05-02",
            "invoice_number": "M-002",
            "lines": [
                {
                    "description": "Achats corriges",
                    "category": "601",
                    "vat_rate": "20",
                    "amount_ht": "50.00",
                },
                {
                    "description": "Frais",
                    "category": "625",
                    "vat_rate": "10",
                    "amount_ht": "30.00",
                },
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["supplier_name"] == "Metro corrige"
    assert body["invoice_date"] == "2026-05-02"
    assert body["invoice_number"] == "M-002"
    assert body["total_ht"] == "80.00"
    assert body["total_tva"] == "13.00"
    assert body["total_ttc"] == "93.00"
    assert len(body["lines"]) == 2


def test_update_invoice_after_validation_is_rejected(client: TestClient):
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
    client.post(f"/api/invoices/{created['id']}/validate")

    response = client.put(
        f"/api/invoices/{created['id']}",
        json={
            "supplier_name": "Metro corrige",
            "invoice_date": "2026-05-02",
            "lines": [
                {
                    "description": "Achats",
                    "vat_rate": "10",
                    "amount_ht": "100.00",
                }
            ],
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "validated_invoice_cannot_be_edited"


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


def test_archive_invoice_hides_it_from_list(client: TestClient):
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

    archive_response = client.post(f"/api/invoices/{created['id']}/archive")
    list_response = client.get("/api/invoices")
    get_response = client.get(f"/api/invoices/{created['id']}")

    assert archive_response.status_code == 200
    assert archive_response.json()["status"] == "archived"
    assert list_response.status_code == 200
    assert list_response.json() == []
    assert get_response.status_code == 200
    assert get_response.json()["status"] == "archived"


def test_archive_validated_invoice_is_rejected(client: TestClient):
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
    client.post(f"/api/invoices/{created['id']}/validate")

    response = client.post(f"/api/invoices/{created['id']}/archive")

    assert response.status_code == 409
    assert response.json()["detail"] == "validated_invoice_cannot_be_archived"


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


def test_invoice_csv_export_contains_monthly_invoice_lines(client: TestClient):
    may_invoice = client.post(
        "/api/invoices",
        json={
            "supplier_name": "May Supplier",
            "invoice_date": "2026-05-20",
            "invoice_number": "MAY-1",
            "lines": [
                {
                    "description": "Achats 20",
                    "category": "601",
                    "vat_rate": "20",
                    "amount_ht": "100.00",
                },
                {
                    "description": "Achats 5.5",
                    "category": "601",
                    "vat_rate": "5.5",
                    "amount_ht": "50.00",
                },
            ],
        },
    ).json()
    client.post(f"/api/invoices/{may_invoice['id']}/validate")
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

    response = client.get(
        "/api/invoices/export.csv",
        params={"period_start": "2026-05-01"},
    )

    assert response.status_code == 200
    assert response.headers["content-disposition"] == (
        'attachment; filename="zen-compta-invoices-2026-05-01.csv"'
    )
    rows = list(csv.DictReader(StringIO(response.text)))
    assert len(rows) == 2
    assert {row["line_description"] for row in rows} == {
        "Achats 20",
        "Achats 5.5",
    }
    assert {row["supplier_name"] for row in rows} == {"May Supplier"}
    assert rows[0]["invoice_total_tva"] == "22.75"


def test_invoice_xlsx_export_is_a_valid_workbook(client: TestClient):
    invoice = client.post(
        "/api/invoices",
        json={
            "supplier_name": "May Supplier",
            "invoice_date": "2026-05-20",
            "invoice_number": "MAY-1",
            "lines": [
                {
                    "description": "Achats 20",
                    "category": "601",
                    "vat_rate": "20",
                    "amount_ht": "100.00",
                }
            ],
        },
    ).json()
    client.post(f"/api/invoices/{invoice['id']}/validate")

    response = client.get(
        "/api/invoices/export.xlsx",
        params={"period_start": "2026-05-01"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    workbook = ZipFile(BytesIO(response.content))
    assert "[Content_Types].xml" in workbook.namelist()
    worksheet = workbook.read("xl/worksheets/sheet1.xml").decode()
    assert "<t>supplier_name</t>" in worksheet
    assert "<t>May Supplier</t>" in worksheet
    assert "<t>invoice_total_tva</t>" in worksheet
    assert "<t>20.00</t>" in worksheet


def test_invoice_export_excludes_draft_invoices(client: TestClient):
    validated = client.post(
        "/api/invoices",
        json={
            "supplier_name": "Validated Supplier",
            "invoice_date": "2026-05-20",
            "lines": [
                {
                    "description": "Validated line",
                    "vat_rate": "20",
                    "amount_ht": "100.00",
                }
            ],
        },
    ).json()
    client.post(f"/api/invoices/{validated['id']}/validate")
    client.post(
        "/api/invoices",
        json={
            "supplier_name": "Draft Supplier",
            "invoice_date": "2026-05-21",
            "lines": [
                {
                    "description": "Draft line",
                    "vat_rate": "20",
                    "amount_ht": "100.00",
                }
            ],
        },
    )

    response = client.get(
        "/api/invoices/export.csv",
        params={"period_start": "2026-05-01"},
    )

    assert response.status_code == 200
    rows = list(csv.DictReader(StringIO(response.text)))
    assert [row["supplier_name"] for row in rows] == ["Validated Supplier"]


def test_invoice_csv_export_neutralizes_spreadsheet_formulas(client: TestClient):
    invoice = client.post(
        "/api/invoices",
        json={
            "supplier_name": "=cmd",
            "invoice_date": "2026-05-20",
            "invoice_number": "@danger",
            "lines": [
                {
                    "description": "+formula",
                    "category": "-category",
                    "vat_rate": "20",
                    "amount_ht": "100.00",
                }
            ],
        },
    ).json()
    client.post(f"/api/invoices/{invoice['id']}/validate")

    response = client.get(
        "/api/invoices/export.csv",
        params={"period_start": "2026-05-01"},
    )

    assert response.status_code == 200
    rows = list(csv.DictReader(StringIO(response.text)))
    assert rows[0]["supplier_name"] == "'=cmd"
    assert rows[0]["invoice_number"] == "'@danger"
    assert rows[0]["line_description"] == "'+formula"
    assert rows[0]["category"] == "'-category"
