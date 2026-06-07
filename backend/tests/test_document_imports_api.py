from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models import DocumentImport, Invoice, InvoiceLine, MonthlySales  # noqa: F401
from app.services import document_import_service
from app.services.invoice_extraction_service import (
    ExtractedInvoice,
    ExtractedInvoiceLine,
    InvoiceExtractionError,
)


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
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

    original_token = settings.internal_api_token
    original_upload_dir = settings.upload_storage_dir
    original_max_upload_bytes = settings.max_upload_bytes
    original_openai_api_key = settings.openai_api_key
    settings.internal_api_token = "test-token"
    settings.upload_storage_dir = str(tmp_path / "private_uploads")
    settings.max_upload_bytes = 1024
    settings.openai_api_key = None

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    test_client.headers.update({"X-Internal-API-Token": "test-token"})
    try:
        yield test_client
    finally:
        settings.internal_api_token = original_token
        settings.upload_storage_dir = original_upload_dir
        settings.max_upload_bytes = original_max_upload_bytes
        settings.openai_api_key = original_openai_api_key
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)


def test_upload_document_import_creates_needs_review_invoice(client: TestClient):
    response = client.post(
        "/api/document-imports",
        files={"file": ("metro.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["document_import"]["original_filename"] == "metro.pdf"
    assert "storage_path" not in body["document_import"]
    assert body["document_import"]["content_type"] == "application/pdf"
    assert body["document_import"]["size_bytes"] == 13
    assert body["document_import"]["status"] == "uploaded"
    assert body["invoice"]["supplier_name"] == "A verifier"
    assert body["invoice"]["status"] == "needs_review"
    assert body["invoice"]["source"] == "ai_upload"
    assert body["invoice"]["invoice_date"] is None
    assert body["invoice"]["total_ht"] == "0.00"

    monthly_invoices_response = client.get(
        "/api/invoices",
        params={"period_start": "2026-06-01"},
    )

    assert monthly_invoices_response.status_code == 200
    assert monthly_invoices_response.json() == []

    review_invoices_response = client.get(
        "/api/invoices",
        params={"needs_review_without_date": "true"},
    )

    assert review_invoices_response.status_code == 200
    invoices = review_invoices_response.json()
    assert len(invoices) == 1
    assert invoices[0]["supplier_name"] == "A verifier"
    assert invoices[0]["invoice_date"] is None


def test_imported_invoice_with_date_is_listed_in_review_inbox(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    class FakeExtractor:
        def extract(self, **_: object) -> ExtractedInvoice:
            return ExtractedInvoice(
                supplier_name="GUIGEL",
                invoice_date="2025-08-05",
                lines=[
                    ExtractedInvoiceLine(
                        description="Marchandises",
                        category_code="raw_materials_5_5",
                        vat_rate=5.5,
                        amount_ht=100.00,
                    )
                ],
            )

    monkeypatch.setattr(
        document_import_service,
        "build_invoice_extractor",
        lambda: FakeExtractor(),
    )

    client.post(
        "/api/document-imports",
        files={"file": ("guigel.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )

    monthly_response = client.get(
        "/api/invoices",
        params={"period_start": "2026-06-01"},
    )
    review_response = client.get(
        "/api/invoices",
        params={"imported_to_review": "true"},
    )

    assert monthly_response.json() == []
    invoices = review_response.json()
    assert len(invoices) == 1
    assert invoices[0]["supplier_name"] == "GUIGEL"
    assert invoices[0]["invoice_date"] == "2025-08-05"


def test_upload_document_import_rejects_unsupported_file_type(client: TestClient):
    response = client.post(
        "/api/document-imports",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "unsupported_file_type"


def test_upload_document_import_prefills_invoice_from_extraction(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    class FakeExtractor:
        def extract(self, **_: object) -> ExtractedInvoice:
            return ExtractedInvoice(
                supplier_name="Metro",
                invoice_date="2026-06-03",
                invoice_number="M-123",
                lines=[
                    ExtractedInvoiceLine(
                        description="Tomates",
                        category_code="raw_materials_5_5",
                        vat_rate="5.5",
                        amount_ht="100.00",
                        amount_tva="5.50",
                        amount_ttc="105.50",
                    )
                ],
                total_ht="100.00",
                total_tva="5.50",
                total_ttc="105.50",
            )

    monkeypatch.setattr(
        document_import_service,
        "build_invoice_extractor",
        lambda: FakeExtractor(),
    )

    response = client.post(
        "/api/document-imports",
        files={"file": ("metro.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["document_import"]["status"] == "extraction_completed"
    assert body["invoice"]["supplier_name"] == "Metro"
    assert body["invoice"]["invoice_date"] == "2026-06-03"
    assert body["invoice"]["invoice_number"] == "M-123"
    assert body["invoice"]["status"] == "needs_review"
    assert body["invoice"]["total_ht"] == "100.00"
    assert body["invoice"]["total_tva"] == "5.50"
    assert body["invoice"]["total_ttc"] == "105.50"
    assert body["invoice"]["lines"][0]["category"] == "raw_materials_5_5"


def test_upload_document_import_falls_back_when_extraction_fails(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    class FailingExtractor:
        def extract(self, **_: object) -> ExtractedInvoice:
            raise InvoiceExtractionError("model_not_found")

    monkeypatch.setattr(
        document_import_service,
        "build_invoice_extractor",
        lambda: FailingExtractor(),
    )

    response = client.post(
        "/api/document-imports",
        files={"file": ("metro.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["document_import"]["status"] == "extraction_failed"
    assert body["invoice"]["supplier_name"] == "A verifier"
    assert body["invoice"]["status"] == "needs_review"
    assert body["invoice"]["lines"] == []


def test_upload_document_import_marks_unknown_category_for_review(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    class FakeExtractor:
        def extract(self, **_: object) -> ExtractedInvoice:
            return ExtractedInvoice(
                supplier_name="Metro",
                invoice_date="2026-06-03",
                lines=[
                    ExtractedInvoiceLine(
                        description="Categorie inconnue",
                        category_code="invented_category",
                        vat_rate="20",
                        amount_ht="50.00",
                    )
                ],
            )

    monkeypatch.setattr(
        document_import_service,
        "build_invoice_extractor",
        lambda: FakeExtractor(),
    )

    response = client.post(
        "/api/document-imports",
        files={"file": ("metro.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )

    assert response.status_code == 200
    line = response.json()["invoice"]["lines"][0]
    assert line["category"] == "other"
    assert line["needs_review_reason"] == "unknown_category"


def test_upload_document_import_keeps_invalid_extracted_date_in_review_inbox(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    class FakeExtractor:
        def extract(self, **_: object) -> ExtractedInvoice:
            return ExtractedInvoice(
                supplier_name="ALDI",
                invoice_date="0402-04-02",
                lines=[
                    ExtractedInvoiceLine(
                        description="Produits alimentaires",
                        category_code="raw_materials_5_5",
                        vat_rate=5.5,
                        amount_ht=37.00,
                    )
                ],
            )

    monkeypatch.setattr(
        document_import_service,
        "build_invoice_extractor",
        lambda: FakeExtractor(),
    )

    response = client.post(
        "/api/document-imports",
        files={"file": ("aldi.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["invoice"]["invoice_date"] is None
    assert body["invoice"]["lines"][0]["needs_review_reason"] == (
        "invalid_invoice_date"
    )

    review_invoices_response = client.get(
        "/api/invoices",
        params={"needs_review_without_date": "true"},
    )

    invoices = review_invoices_response.json()
    assert len(invoices) == 1
    assert invoices[0]["supplier_name"] == "ALDI"
    assert invoices[0]["invoice_date"] is None


def test_upload_document_import_rejects_mismatched_file_signature(
    client: TestClient,
):
    response = client.post(
        "/api/document-imports",
        files={"file": ("fake.pdf", b"not a pdf", "application/pdf")},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "file_signature_mismatch"


def test_upload_document_import_rejects_large_file(client: TestClient):
    response = client.post(
        "/api/document-imports",
        files={"file": ("large.pdf", b"x" * 1025, "application/pdf")},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "file_too_large"


def test_uploaded_invoice_is_excluded_from_official_exports(client: TestClient):
    client.post(
        "/api/document-imports",
        files={"file": ("metro.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )

    response = client.get(
        "/api/invoices/export.csv",
        params={"period_start": "2026-06-01"},
    )

    assert response.status_code == 200
    assert response.text.splitlines() == [
        (
            "invoice_date,supplier_name,invoice_number,status,line_position,"
            "line_description,category,vat_rate,line_ht,line_tva,line_ttc,"
            "invoice_total_ht,invoice_total_tva,invoice_total_ttc"
        )
    ]


def test_uploaded_invoice_without_date_is_excluded_from_monthly_dashboard(
    client: TestClient,
):
    client.post(
        "/api/document-imports",
        files={"file": ("metro.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )

    response = client.get(
        "/api/dashboard/summary",
        params={"period_start": "2026-06-01", "opening_cash": "500.00"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["invoices_to_review_count"] == 0
    assert body["validated_invoices_ttc"] == "0.00"
    assert body["estimated_cash"] == "500.00"


def test_document_import_upload_requires_internal_token(client: TestClient):
    response = client.post(
        "/api/document-imports",
        headers={"X-Internal-API-Token": "wrong-token"},
        files={"file": ("metro.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )

    assert response.status_code == 401
