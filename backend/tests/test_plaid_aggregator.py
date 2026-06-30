from datetime import date
from decimal import Decimal

import httpx
import pytest

from app.services.bank_aggregator import BankAggregatorError
from app.services.bank_aggregator.plaid import PlaidAggregator


def test_create_requisition_returns_plaid_link_url() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/link/token/create"
        return httpx.Response(200, json={"link_token": "link-sandbox-abc123"})

    aggregator = _aggregator(handler)

    result = aggregator.create_requisition(
        institution_id="ins_1",
        reference="reference",
        redirect_uri="http://localhost:3000/bank/callback",
    )

    assert result.requisition_id == "link-sandbox-abc123"
    assert result.auth_link == "plaid-link://link-sandbox-abc123"
    assert result.session_data == {}


def test_exchange_public_token_returns_session_data() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/item/public_token/exchange"
        return httpx.Response(
            200,
            json={"access_token": "access-sandbox-xxx", "item_id": "item-123"},
        )

    aggregator = _aggregator(handler)

    assert aggregator.exchange_public_token("public-sandbox-xxx") == {
        "access_token": "access-sandbox-xxx",
        "item_id": "item-123",
    }


def test_get_requisition_accounts_uses_access_token() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/accounts/get"
        assert '"access_token":"access-sandbox-xxx"' in request.read().decode()
        return httpx.Response(
            200,
            json={"accounts": [{"account_id": "acc-1"}, {"account_id": "acc-2"}]},
        )

    aggregator = _aggregator(handler)

    assert aggregator.get_requisition_accounts(
        "item-123",
        session_data={"access_token": "access-sandbox-xxx"},
    ) == ["acc-1", "acc-2"]


def test_get_requisition_accounts_requires_session_data() -> None:
    aggregator = _aggregator(_no_request)

    with pytest.raises(BankAggregatorError, match="plaid_session_missing"):
        aggregator.get_requisition_accounts("item-123")


def test_get_account_metadata_returns_account_info() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/accounts/get"
        return httpx.Response(
            200,
            json={
                "accounts": [
                    {
                        "account_id": "acc-1",
                        "official_name": "Compte courant",
                        "mask": "6789",
                        "balances": {"iso_currency_code": "EUR"},
                    }
                ]
            },
        )

    aggregator = _aggregator(handler)

    account = aggregator.get_account_metadata(
        "acc-1",
        session_data={"access_token": "access-sandbox-xxx"},
    )

    assert account.external_account_id == "acc-1"
    assert account.iban_last4 == "6789"
    assert account.name == "Compte courant"
    assert account.currency == "EUR"


def test_fetch_transactions_inverts_plaid_amount_sign() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/transactions/get"
        return httpx.Response(
            200,
            json={
                "transactions": [
                    {
                        "transaction_id": "tx-1",
                        "account_id": "acc-1",
                        "date": "2026-06-01",
                        "amount": 45.50,
                        "iso_currency_code": "EUR",
                        "name": "METRO",
                    }
                ]
            },
        )

    aggregator = _aggregator(handler)

    transactions = aggregator.fetch_transactions(
        external_account_id="acc-1",
        date_from=date(2026, 6, 1),
        session_data={"access_token": "access-sandbox-xxx"},
    )

    assert transactions[0].amount == Decimal("-45.50")


def test_fetch_transactions_filters_by_account() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "transactions": [
                    {
                        "transaction_id": "tx-1",
                        "account_id": "acc-1",
                        "date": "2026-06-01",
                        "amount": 45.50,
                    },
                    {
                        "transaction_id": "tx-2",
                        "account_id": "acc-2",
                        "date": "2026-06-02",
                        "amount": 12.30,
                    },
                ]
            },
        )

    aggregator = _aggregator(handler)

    transactions = aggregator.fetch_transactions(
        external_account_id="acc-1",
        date_from=date(2026, 6, 1),
        session_data={"access_token": "access-sandbox-xxx"},
    )

    assert len(transactions) == 1
    assert transactions[0].external_id == "tx-1"


def test_fetch_transactions_paginates_until_total_transactions() -> None:
    seen_offsets: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = request.read().decode()
        offset = 0 if '"offset":0' in body else 1
        seen_offsets.append(offset)
        transaction_id = f"tx-{offset + 1}"
        return httpx.Response(
            200,
            json={
                "total_transactions": 2,
                "transactions": [
                    {
                        "transaction_id": transaction_id,
                        "account_id": "acc-1",
                        "date": "2026-06-01",
                        "amount": "1.00",
                    }
                ],
            },
        )

    aggregator = _aggregator(handler)

    transactions = aggregator.fetch_transactions(
        external_account_id="acc-1",
        date_from=date(2026, 6, 1),
        session_data={"access_token": "access-sandbox-xxx"},
    )

    assert seen_offsets == [0, 1]
    assert [transaction.external_id for transaction in transactions] == ["tx-1", "tx-2"]


def test_fetch_transactions_skips_invalid_authorized_date() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "transactions": [
                    {
                        "transaction_id": "tx-1",
                        "account_id": "acc-1",
                        "date": "2026-06-01",
                        "authorized_date": "not-a-date",
                        "amount": 45.50,
                    }
                ]
            },
        )

    aggregator = _aggregator(handler)

    assert (
        aggregator.fetch_transactions(
            external_account_id="acc-1",
            date_from=date(2026, 6, 1),
            session_data={"access_token": "access-sandbox-xxx"},
        )
        == []
    )


def test_create_requisition_raises_on_api_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error_code": "INVALID_REQUEST"})

    aggregator = _aggregator(handler)

    with pytest.raises(BankAggregatorError, match="plaid_link_token_failed"):
        aggregator.create_requisition(
            institution_id="ins_1",
            reference="reference",
            redirect_uri="http://localhost:3000/bank/callback",
        )


def _aggregator(handler: httpx.MockTransport) -> PlaidAggregator:
    return PlaidAggregator(
        client_id="id",
        secret="secret",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )


def _no_request(request: httpx.Request) -> httpx.Response:
    raise AssertionError(f"unexpected request: {request.url}")
