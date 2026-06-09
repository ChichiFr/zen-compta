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
from app.models import (  # noqa: F401
    Invoice,
    InvoiceLine,
    MonthlyCashFlowInputs,
    MonthlySales,
)
from app.services.invoice_categories import ALLOWED_CATEGORY_CODES
from app.services.performance_service import PERFORMANCE_CATEGORY_BUCKETS


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


def test_dashboard_summary_does_not_show_negative_vat_payable(client: TestClient):
    validated_invoice = client.post(
        "/api/invoices",
        json={
            "supplier_name": "Metro",
            "invoice_date": "2026-05-05",
            "lines": [
                {
                    "description": "Achats avec TVA deductible superieure",
                    "vat_rate": "20",
                    "amount_ht": "1000.00",
                }
            ],
        },
    ).json()
    client.post(f"/api/invoices/{validated_invoice['id']}/validate")
    client.put(
        "/api/monthly-sales/2026-05-01",
        json={
            "sales_ht": "100.00",
            "vat_collected": "20.00",
            "sales_ttc": "120.00",
        },
    )

    response = client.get(
        "/api/dashboard/summary",
        params={"period_start": "2026-05-20", "opening_cash": "500.00"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["vat_deductible"] == "200.00"
    assert body["vat_collected"] == "20.00"
    assert body["vat_payable_estimate"] == "0.00"
    assert body["estimated_cash"] == "-580.00"


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


def test_monthly_cash_flow_inputs_upsert_normalizes_period(client: TestClient):
    response = client.put(
        "/api/performance/monthly-inputs/2026-05-20",
        json={
            "salaries": "1200.00",
            "social_charges": "400.00",
            "investments_cash": "700.00",
            "loan_repayments_cash": "300.00",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["period_start"] == "2026-05-01"
    assert body["salaries"] == "1200.00"
    assert body["social_charges"] == "400.00"
    assert body["investments_cash"] == "700.00"
    assert body["loan_repayments_cash"] == "300.00"

    updated = client.put(
        "/api/performance/monthly-inputs/2026-05-01",
        json={
            "salaries": "1300.00",
            "social_charges": "450.00",
            "investments_cash": "0.00",
            "loan_repayments_cash": "250.00",
        },
    )

    assert updated.status_code == 200
    assert updated.json()["id"] == body["id"]
    assert updated.json()["salaries"] == "1300.00"


def test_monthly_performance_summary_splits_operating_and_non_operating_cash(
    client: TestClient,
):
    validated_invoice = client.post(
        "/api/invoices",
        json={
            "supplier_name": "Metro",
            "invoice_date": "2026-05-05",
            "lines": [
                {
                    "description": "Matieres premieres",
                    "category": "raw_materials_5_5",
                    "vat_rate": "5.5",
                    "amount_ht": "1000.00",
                },
                {
                    "description": "Emballages",
                    "category": "lost_packaging_20",
                    "vat_rate": "20",
                    "amount_ht": "200.00",
                },
                {
                    "description": "Maintenance",
                    "category": "maintenance",
                    "vat_rate": "20",
                    "amount_ht": "300.00",
                },
            ],
        },
    ).json()
    client.post(f"/api/invoices/{validated_invoice['id']}/validate")
    client.post(
        "/api/invoices",
        json={
            "supplier_name": "Draft supplier",
            "invoice_date": "2026-05-06",
            "lines": [
                {
                    "description": "Brouillon ignore",
                    "category": "raw_materials_20",
                    "vat_rate": "20",
                    "amount_ht": "999.00",
                }
            ],
        },
    )
    client.put(
        "/api/monthly-sales/2026-05-01",
        json={
            "sales_ht": "5000.00",
            "vat_collected": "500.00",
            "sales_ttc": "5500.00",
        },
    )
    client.put(
        "/api/performance/monthly-inputs/2026-05-01",
        json={
            "salaries": "1200.00",
            "social_charges": "400.00",
            "investments_cash": "700.00",
            "loan_repayments_cash": "300.00",
        },
    )

    response = client.get(
        "/api/performance/monthly",
        params={"period_start": "2026-05-20"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["period_start"] == "2026-05-01"
    assert body["data_quality_notes"] == []
    assert body["vat_collected"] == "500.00"
    assert body["vat_deductible"] == "155.00"
    assert body["performance"] == {
        "sales_ht": "5000.00",
        "raw_materials_ht": "1000.00",
        "packaging_ht": "200.00",
        "salaries": "1200.00",
        "social_charges": "400.00",
        "external_purchases_taxes_ht": "300.00",
        "ebe_cash": "1900.00",
    }
    assert body["non_operating_cash_flow"] == {
        "investments_cash": "700.00",
        "loan_repayments_cash": "300.00",
        "vat_payable_estimate": "345.00",
        "vat_credit_estimate": "0.00",
        "total_cash_outflow": "1345.00",
        "forecast_relevant_cash_outflow": "645.00",
    }


def test_monthly_performance_summary_reports_missing_source_data(
    client: TestClient,
):
    response = client.get(
        "/api/performance/monthly",
        params={"period_start": "2026-05-20"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["performance"]["sales_ht"] == "0.00"
    assert body["performance"]["ebe_cash"] == "0.00"
    assert body["non_operating_cash_flow"]["total_cash_outflow"] == "0.00"
    assert body["data_quality_notes"] == [
        "monthly_sales_missing",
        "cash_flow_inputs_missing",
    ]


def test_monthly_performance_summary_separates_vat_credit_from_cash_outflow(
    client: TestClient,
):
    validated_invoice = client.post(
        "/api/invoices",
        json={
            "supplier_name": "Equipment supplier",
            "invoice_date": "2026-05-05",
            "lines": [
                {
                    "description": "Large maintenance invoice",
                    "category": "maintenance",
                    "vat_rate": "20",
                    "amount_ht": "1000.00",
                }
            ],
        },
    ).json()
    client.post(f"/api/invoices/{validated_invoice['id']}/validate")
    client.put(
        "/api/monthly-sales/2026-05-01",
        json={
            "sales_ht": "100.00",
            "vat_collected": "20.00",
            "sales_ttc": "120.00",
        },
    )
    client.put(
        "/api/performance/monthly-inputs/2026-05-01",
        json={
            "salaries": "0.00",
            "social_charges": "0.00",
            "investments_cash": "50.00",
            "loan_repayments_cash": "25.00",
        },
    )

    response = client.get(
        "/api/performance/monthly",
        params={"period_start": "2026-05-20"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["vat_collected"] == "20.00"
    assert body["vat_deductible"] == "200.00"
    assert body["non_operating_cash_flow"]["vat_payable_estimate"] == "0.00"
    assert body["non_operating_cash_flow"]["vat_credit_estimate"] == "180.00"
    assert body["non_operating_cash_flow"]["total_cash_outflow"] == "75.00"
    assert (
        body["non_operating_cash_flow"]["forecast_relevant_cash_outflow"]
        == "25.00"
    )


def test_performance_category_mapping_documents_all_known_categories():
    assert set(PERFORMANCE_CATEGORY_BUCKETS) == ALLOWED_CATEGORY_CODES


def test_monthly_forecast_returns_normal_and_downside_scenarios(
    client: TestClient,
):
    validated_invoice = client.post(
        "/api/invoices",
        json={
            "supplier_name": "Metro",
            "invoice_date": "2026-05-05",
            "lines": [
                {
                    "description": "Matieres premieres",
                    "category": "raw_materials_5_5",
                    "vat_rate": "20",
                    "amount_ht": "2000.00",
                }
            ],
        },
    ).json()
    client.post(f"/api/invoices/{validated_invoice['id']}/validate")
    client.post(
        "/api/invoices",
        json={
            "supplier_name": "Draft supplier",
            "invoice_date": "2026-05-06",
            "lines": [
                {
                    "description": "Brouillon ignore",
                    "category": "maintenance",
                    "vat_rate": "20",
                    "amount_ht": "9999.00",
                }
            ],
        },
    )
    client.put(
        "/api/monthly-sales/2026-05-01",
        json={
            "sales_ht": "10000.00",
            "vat_collected": "1000.00",
            "sales_ttc": "11000.00",
        },
    )
    client.put(
        "/api/performance/monthly-inputs/2026-05-01",
        json={
            "salaries": "0.00",
            "social_charges": "0.00",
            "investments_cash": "0.00",
            "loan_repayments_cash": "0.00",
        },
    )

    response = client.get(
        "/api/forecast/monthly",
        params={
            "period_start": "2026-05-20",
            "opening_cash": "1000.00",
            "forecast_sales_ht": "12000.00",
            "fixed_salaries": "3000.00",
            "variable_salary_rate": "10.00",
            "social_charge_rate": "40.00",
            "loan_repayments_cash": "500.00",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["period_start"] == "2026-05-01"
    assert body["assumptions"] == {
        "opening_cash": "1000.00",
        "forecast_sales_ht": "12000.00",
        "fixed_salaries": "3000.00",
        "variable_salary_rate": "10.00",
        "social_charge_rate": "40.00",
        "loan_repayments_cash": "500.00",
        "vat_collection_rate": "10.00",
        "vat_deductible_estimate": "400.00",
    }
    scenarios = {scenario["key"]: scenario for scenario in body["scenarios"]}
    assert set(scenarios) == {"normal", "sales_minus_10", "sales_minus_20"}
    assert scenarios["normal"]["forecast_sales_ht"] == "12000.00"
    assert scenarios["normal"]["operating_costs_ht"] == "2400.00"
    assert scenarios["normal"]["salaries"] == "4200.00"
    assert scenarios["normal"]["social_charges"] == "1680.00"
    assert scenarios["normal"]["ebe_forecast"] == "3720.00"
    assert scenarios["normal"]["vat_collected_estimate"] == "1200.00"
    assert scenarios["normal"]["vat_payable_estimate"] == "800.00"
    assert scenarios["normal"]["vat_credit_estimate"] == "0.00"
    assert scenarios["normal"]["ending_cash_estimate"] == "3420.00"
    assert scenarios["normal"]["risk_level"] == "ok"
    assert scenarios["sales_minus_10"]["forecast_sales_ht"] == "10800.00"
    assert scenarios["sales_minus_10"]["vat_payable_estimate"] == "680.00"
    assert scenarios["sales_minus_20"]["forecast_sales_ht"] == "9600.00"
    assert scenarios["sales_minus_20"]["loan_repayments_cash"] == "500.00"
    assert scenarios["sales_minus_20"]["vat_payable_estimate"] == "560.00"
    assert body["data_quality_notes"] == []


def test_monthly_forecast_keeps_vat_credit_out_of_cash_outflow(
    client: TestClient,
):
    validated_invoice = client.post(
        "/api/invoices",
        json={
            "supplier_name": "Maintenance supplier",
            "invoice_date": "2026-05-05",
            "lines": [
                {
                    "description": "Grosse facture",
                    "category": "maintenance",
                    "vat_rate": "20",
                    "amount_ht": "1000.00",
                }
            ],
        },
    ).json()
    client.post(f"/api/invoices/{validated_invoice['id']}/validate")
    client.put(
        "/api/monthly-sales/2026-05-01",
        json={
            "sales_ht": "100.00",
            "vat_collected": "20.00",
            "sales_ttc": "120.00",
        },
    )

    response = client.get(
        "/api/forecast/monthly",
        params={
            "period_start": "2026-05-20",
            "opening_cash": "1000.00",
            "forecast_sales_ht": "0.00",
            "fixed_salaries": "0.00",
            "variable_salary_rate": "0.00",
            "social_charge_rate": "35.00",
            "loan_repayments_cash": "250.00",
        },
    )

    assert response.status_code == 200
    normal = response.json()["scenarios"][0]
    assert response.json()["assumptions"]["vat_collection_rate"] == "20.00"
    assert response.json()["assumptions"]["vat_deductible_estimate"] == "200.00"
    assert normal["vat_credit_estimate"] == "200.00"
    assert normal["ending_cash_estimate"] == "750.00"
