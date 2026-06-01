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

    original_environment = settings.environment
    original_token = settings.internal_api_token
    settings.environment = "production"
    settings.internal_api_token = "test-token"

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        settings.environment = original_environment
        settings.internal_api_token = original_token
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)


def test_health_route_does_not_require_internal_token(client: TestClient):
    response = client.get("/api/health")

    assert response.status_code == 200


def test_invoice_routes_require_internal_token(client: TestClient):
    response = client.get("/api/invoices")

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid_internal_api_token"


def test_invoice_routes_accept_valid_internal_token(client: TestClient):
    response = client.get(
        "/api/invoices",
        headers={"X-Internal-API-Token": "test-token"},
    )

    assert response.status_code == 200
    assert response.json() == []
