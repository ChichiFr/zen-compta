from collections.abc import Iterator
from datetime import date
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
from app.models import MonthlySales


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


def test_home_endpoint_returns_series(client: TestClient) -> None:
    session_local = client.testing_session_local  # type: ignore[attr-defined]
    with session_local() as db:
        db.add(
            MonthlySales(
                period_start=date(2026, 7, 1),
                sales_ht=Decimal("12450.00"),
                vat_collected=Decimal("1245.00"),
                sales_ttc=Decimal("13695.00"),
            )
        )
        db.commit()

    response = client.get(
        "/api/dashboard/home", params={"period_start": "2026-07-01"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["period_start"] == "2026-07-01"
    assert len(body["monthly_series"]) == 12
    assert body["monthly_series"][-1]["sales_ht"] == "12450.00"
    assert body["bank_connected"] is False
    assert body["unpaid_invoices_count"] == 0


def test_home_endpoint_requires_auth(client: TestClient) -> None:
    response = client.get(
        "/api/dashboard/home",
        params={"period_start": "2026-07-01"},
        headers={"X-Internal-API-Token": "wrong"},
    )

    assert response.status_code in (401, 403)
