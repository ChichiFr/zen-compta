from datetime import date
from decimal import Decimal

import httpx
import pytest

from app.services.bank_aggregator import BankAggregatorError
from app.services.bank_aggregator.powens import PowensAggregator


def test_create_requisition_returns_webview_result_and_session_data() -> None:
    seen_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_paths.append(request.url.path)
        if request.url.path == "/2.0/auth/init":
            assert request.read() == b'{"client_id":"id","client_secret":"key"}'
            return httpx.Response(
                200,
                json={"auth_token": "auth-token", "id_user": 123},
            )
        assert request.url.path == "/2.0/auth/token/code"
        assert request.headers["Authorization"] == "Bearer auth-token"
        return httpx.Response(200, json={"code": "temp-code", "type": "temporary"})

    aggregator = PowensAggregator(
        client_id="id",
        client_secret="key",
        domain="demo",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = aggregator.create_requisition(
        institution_id="SANDBOXFINANCE_SFIN0000",
        reference="reference",
        redirect_uri="http://localhost:3000/bank/callback",
    )

    assert seen_paths == ["/2.0/auth/init", "/2.0/auth/token/code"]
    assert result.requisition_id == "temp-code"
    assert result.expires_at is None
    assert result.session_data == {"auth_token": "auth-token", "id_user": 123}
    assert result.auth_link.startswith("https://webview.powens.com/connect?")
    assert "code=temp-code" in result.auth_link
    assert "domain=demo-sandbox" in result.auth_link
    assert "redirect_uri=http%3A%2F%2Flocalhost%3A3000%2Fbank%2Fcallback" in (
        result.auth_link
    )


def test_get_requisition_accounts_requires_session_data() -> None:
    aggregator = PowensAggregator(
        client_id="id",
        client_secret="key",
        domain="demo",
        http_client=httpx.Client(transport=httpx.MockTransport(_no_request)),
    )

    with pytest.raises(BankAggregatorError, match="powens_session_missing"):
        aggregator.get_requisition_accounts("conn-1")


def test_get_requisition_accounts_parses_accounts() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/2.0/users/me/connections/conn-1/accounts"
        assert request.headers["Authorization"] == "Bearer auth-token"
        return httpx.Response(
            200,
            json={"accounts": [{"id": 123}, {"id": "account-456"}]},
        )

    aggregator = PowensAggregator(
        client_id="id",
        client_secret="key",
        domain="demo",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert aggregator.get_requisition_accounts(
        "conn-1",
        session_data={"auth_token": "auth-token"},
    ) == ["123", "account-456"]


def test_get_account_metadata_parses_account_details() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/2.0/users/me/accounts/account-1"
        assert request.headers["Authorization"] == "Bearer auth-token"
        return httpx.Response(
            200,
            json={
                "account": {
                    "id": "account-1",
                    "name": "Compte courant",
                    "iban": "FR7612345678901234567890123",
                    "currency": {"id": "EUR"},
                }
            },
        )

    aggregator = PowensAggregator(
        client_id="id",
        client_secret="key",
        domain="demo",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    account = aggregator.get_account_metadata(
        "account-1",
        session_data={"auth_token": "auth-token"},
    )

    assert account.external_account_id == "account-1"
    assert account.iban_last4 == "0123"
    assert account.name == "Compte courant"
    assert account.currency == "EUR"


def test_fetch_transactions_parses_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/2.0/users/me/accounts/account-1/transactions"
        assert request.headers["Authorization"] == "Bearer auth-token"
        assert request.url.params["min_date"] == "2026-03-01"
        assert request.url.params["limit"] == "500"
        return httpx.Response(
            200,
            json={
                "transactions": [
                    {
                        "id": 987,
                        "date": "2026-03-10",
                        "vdate": "2026-03-11",
                        "value": "-42.35",
                        "currency": {"id": "EUR"},
                        "wording": "CB FOURNISSEUR",
                        "counterparty": {"name": "Fournisseur"},
                    }
                ]
            },
        )

    aggregator = PowensAggregator(
        client_id="id",
        client_secret="key",
        domain="demo",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    transactions = aggregator.fetch_transactions(
        external_account_id="account-1",
        date_from=date(2026, 3, 1),
        session_data={"auth_token": "auth-token"},
    )

    assert len(transactions) == 1
    transaction = transactions[0]
    assert transaction.external_id == "987"
    assert transaction.booking_date == date(2026, 3, 10)
    assert transaction.value_date == date(2026, 3, 11)
    assert transaction.amount == Decimal("-42.35")
    assert transaction.currency == "EUR"
    assert transaction.description == "CB FOURNISSEUR"
    assert transaction.creditor_name == "Fournisseur"
    assert "counterparty" not in transaction.raw_payload


def test_fetch_transactions_does_not_use_rdate_as_value_date() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "transactions": [
                    {
                        "id": "tx-1",
                        "date": "2026-03-10",
                        "rdate": "2026-03-11",
                        "value": "10.00",
                        "wording": "VIREMENT CLIENT",
                    }
                ]
            },
        )

    aggregator = PowensAggregator(
        client_id="id",
        client_secret="key",
        domain="demo",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    transactions = aggregator.fetch_transactions(
        external_account_id="account-1",
        date_from=date(2026, 3, 1),
        session_data={"auth_token": "auth-token"},
    )

    assert transactions[0].value_date is None


def test_raises_bank_aggregator_error_on_non_2xx() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="upstream error")

    aggregator = PowensAggregator(
        client_id="id",
        client_secret="key",
        domain="demo",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(BankAggregatorError):
        aggregator.create_requisition(
            institution_id="SANDBOXFINANCE_SFIN0000",
            reference="reference",
            redirect_uri="http://localhost:3000/bank/callback",
        )


def test_raises_bank_aggregator_error_on_invalid_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id_user": 123})

    aggregator = PowensAggregator(
        client_id="id",
        client_secret="key",
        domain="demo",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(BankAggregatorError):
        aggregator.create_requisition(
            institution_id="SANDBOXFINANCE_SFIN0000",
            reference="reference",
            redirect_uri="http://localhost:3000/bank/callback",
        )


def _no_request(request: httpx.Request) -> httpx.Response:
    raise AssertionError(f"unexpected request: {request.url}")
