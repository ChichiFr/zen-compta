from datetime import date
from decimal import Decimal

import httpx
import pytest

from app.services.bank_aggregator import BankAggregatorError, RequisitionResult
from app.services.bank_aggregator.gocardless import (
    GoCardlessAggregator,
    _parse_transaction,
)


def test_get_access_token_uses_cache() -> None:
    token_requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal token_requests
        assert request.url.path == "/api/v2/token/new/"
        token_requests += 1
        return httpx.Response(
            200,
            json={"access": "access-token", "access_expires": 3600},
        )

    aggregator = GoCardlessAggregator(
        secret_id="id",
        secret_key="key",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert aggregator._get_access_token() == "access-token"
    assert aggregator._get_access_token() == "access-token"
    assert token_requests == 1


def test_get_access_token_refreshes_expired_token() -> None:
    tokens = ["first-token", "second-token"]

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v2/token/new/"
        return httpx.Response(
            200,
            json={"access": tokens.pop(0), "access_expires": 1},
        )

    aggregator = GoCardlessAggregator(
        secret_id="id",
        secret_key="key",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert aggregator._get_access_token() == "first-token"
    assert aggregator._get_access_token() == "second-token"


def test_create_requisition_returns_result() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v2/token/new/":
            return httpx.Response(
                200,
                json={"access": "access-token", "access_expires": 3600},
            )
        assert request.url.path == "/api/v2/requisitions/"
        assert request.headers["Authorization"] == "Bearer access-token"
        return httpx.Response(
            201,
            json={"id": "requisition-id", "link": "https://bank.example/auth"},
        )

    aggregator = GoCardlessAggregator(
        secret_id="id",
        secret_key="key",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = aggregator.create_requisition(
        institution_id="SANDBOXFINANCE_SFIN0000",
        reference="reference",
        redirect_uri="http://localhost:3000/bank/callback",
    )

    assert result == RequisitionResult(
        requisition_id="requisition-id",
        auth_link="https://bank.example/auth",
        expires_at=None,
    )


def test_fetch_transactions_parses_booked_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v2/token/new/":
            return httpx.Response(
                200,
                json={"access": "access-token", "access_expires": 3600},
            )
        assert request.url.path == "/api/v2/accounts/account-id/transactions/"
        assert request.url.params["date_from"] == "2026-03-01"
        return httpx.Response(
            200,
            json={
                "transactions": {
                    "booked": [
                        {
                            "transactionId": "tx-1",
                            "bookingDate": "2026-03-10",
                            "valueDate": "2026-03-11",
                            "transactionAmount": {
                                "amount": "-42.35",
                                "currency": "EUR",
                            },
                            "remittanceInformationUnstructured": "CB FOURNISSEUR",
                            "creditorName": "Fournisseur",
                        }
                    ],
                    "pending": [],
                }
            },
        )

    aggregator = GoCardlessAggregator(
        secret_id="id",
        secret_key="key",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    transactions = aggregator.fetch_transactions(
        external_account_id="account-id",
        date_from=date(2026, 3, 1),
    )

    assert len(transactions) == 1
    transaction = transactions[0]
    assert transaction.external_id == "tx-1"
    assert transaction.booking_date == date(2026, 3, 10)
    assert transaction.value_date == date(2026, 3, 11)
    assert transaction.amount == Decimal("-42.35")
    assert transaction.currency == "EUR"
    assert transaction.description == "CB FOURNISSEUR"
    assert transaction.creditor_name == "Fournisseur"


def test_raises_bank_aggregator_error_on_non_200() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="upstream error")

    aggregator = GoCardlessAggregator(
        secret_id="id",
        secret_key="key",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(BankAggregatorError):
        aggregator._get_access_token()


def test_parse_transaction_returns_none_when_required_data_missing() -> None:
    assert _parse_transaction({}) is None
    assert _parse_transaction({"transactionId": "tx-1"}) is None
    assert (
        _parse_transaction(
            {
                "transactionId": "tx-1",
                "bookingDate": "2026-03-10",
            }
        )
        is None
    )
