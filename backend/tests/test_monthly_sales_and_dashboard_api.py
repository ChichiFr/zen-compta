import csv
from collections.abc import Iterator
from io import BytesIO, StringIO
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models import Invoice, InvoiceLine, MonthlySales  # noqa: F401


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


def test_upsert_monthly_sales_normalizes_to_month_start(client: TestClient):
    created = client.put(
        "/api/monthly-sales/2026-05-18",
        json={
            "sales_ht": "1000.00",
            "vat_collected": "200.00",
            "sales_ttc": "1200.00",
        },
    )

    assert created.status_code == 200
    body = created.json()
    assert body["period_start"] == "2026-05-01"
    assert body["sales_ht"] == "1000.00"
    assert body["vat_collected"] == "200.00"
    assert body["sales_ttc"] == "1200.00"

    updated = client.put(
        "/api/monthly-sales/2026-05-01",
        json={
            "sales_ht": "1500.00",
            "vat_collected": "300.00",
            "sales_ttc": "1800.00",
        },
    )

    assert updated.status_code == 200
    assert updated.json()["id"] == body["id"]
    assert updated.json()["sales_ttc"] == "1800.00"

    fetched = client.get("/api/monthly-sales/2026-05-20")

    assert fetched.status_code == 200
    assert fetched.json()["id"] == body["id"]
    assert fetched.json()["period_start"] == "2026-05-01"


def test_monthly_sales_rejects_inconsistent_totals(client: TestClient):
    response = client.put(
        "/api/monthly-sales/2026-05-01",
        json={
            "sales_ht": "1000.00",
            "vat_collected": "200.00",
            "sales_ttc": "1199.00",
        },
    )

    assert response.status_code == 422
    assert "sales_ttc_must_equal_sales_ht_plus_vat_collected" in response.text


def test_dashboard_summary_uses_validated_invoices_for_vat_and_cash(
    client: TestClient,
):
    validated_invoice = client.post(
        "/api/invoices",
        json={
            "supplier_name": "Metro",
            "invoice_date": "2026-05-05",
            "lines": [
                {
                    "description": "Achats marchandises",
                    "vat_rate": "20",
                    "amount_ht": "100.00",
                }
            ],
        },
    ).json()
    client.post(f"/api/invoices/{validated_invoice['id']}/validate")

    client.post(
        "/api/invoices",
        json={
            "supplier_name": "EDF",
            "invoice_date": "2026-05-06",
            "lines": [
                {
                    "description": "Electricite non validee",
                    "vat_rate": "20",
                    "amount_ht": "1000.00",
                }
            ],
        },
    )

    client.put(
        "/api/monthly-sales/2026-05-01",
        json={
            "sales_ht": "1000.00",
            "vat_collected": "200.00",
            "sales_ttc": "1200.00",
        },
    )

    response = client.get(
        "/api/dashboard/summary",
        params={"period_start": "2026-05-20", "opening_cash": "500.00"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["period_start"] == "2026-05-01"
    assert body["invoices_to_review_count"] == 1
    assert body["validated_invoices_count"] == 1
    assert body["validated_invoices_ht"] == "100.00"
    assert body["validated_invoices_tva"] == "20.00"
    assert body["validated_invoices_ttc"] == "120.00"
    assert body["vat_deductible"] == "20.00"
    assert body["vat_collected"] == "200.00"
    assert body["vat_payable_estimate"] == "180.00"
    assert body["opening_cash"] == "500.00"
    assert body["sales_ht"] == "1000.00"
    assert body["sales_ttc"] == "1200.00"
    assert body["estimated_cash"] == "1400.00"
    assert body["cash_is_bank_connected"] is False


def test_dashboard_summary_csv_export_matches_monthly_summary(client: TestClient):
    validated_invoice = client.post(
        "/api/invoices",
        json={
            "supplier_name": "Metro",
            "invoice_date": "2026-05-05",
            "lines": [
                {
                    "description": "Achats marchandises",
                    "vat_rate": "20",
                    "amount_ht": "100.00",
                }
            ],
        },
    ).json()
    client.post(f"/api/invoices/{validated_invoice['id']}/validate")
    client.put(
        "/api/monthly-sales/2026-05-01",
        json={
            "sales_ht": "1000.00",
            "vat_collected": "200.00",
            "sales_ttc": "1200.00",
        },
    )

    response = client.get(
        "/api/dashboard/summary.csv",
        params={"period_start": "2026-05-20", "opening_cash": "500.00"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert response.headers["content-disposition"] == (
        'attachment; filename="zen-compta-dashboard-2026-05-01.csv"'
    )
    rows = list(csv.DictReader(StringIO(response.text)))
    body = {row["metric"]: row["value"] for row in rows}
    assert body["period_start"] == "2026-05-01"
    assert body["sales_ht"] == "1000.00"
    assert body["vat_collected"] == "200.00"
    assert body["sales_ttc"] == "1200.00"
    assert body["vat_deductible"] == "20.00"
    assert body["vat_payable_estimate"] == "180.00"
    assert body["estimated_cash"] == "1400.00"


def test_dashboard_summary_xlsx_export_is_a_valid_workbook(client: TestClient):
    client.put(
        "/api/monthly-sales/2026-05-01",
        json={
            "sales_ht": "1000.00",
            "vat_collected": "200.00",
            "sales_ttc": "1200.00",
        },
    )

    response = client.get(
        "/api/dashboard/summary.xlsx",
        params={"period_start": "2026-05-20", "opening_cash": "500.00"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert response.headers["content-disposition"] == (
        'attachment; filename="zen-compta-dashboard-2026-05-01.xlsx"'
    )
    workbook = ZipFile(BytesIO(response.content))
    assert "[Content_Types].xml" in workbook.namelist()
    worksheet = workbook.read("xl/worksheets/sheet1.xml").decode()
    assert "<t>period_start</t>" in worksheet
    assert "<t>2026-05-01</t>" in worksheet
    assert "<t>vat_collected</t>" in worksheet
    assert "<t>200.00</t>" in worksheet
