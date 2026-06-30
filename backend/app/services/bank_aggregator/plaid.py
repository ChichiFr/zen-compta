from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from app.services.bank_aggregator.base import (
    AccountInfo,
    BankAggregator,
    BankAggregatorError,
    RequisitionResult,
    TransactionInfo,
)


class PlaidAggregator(BankAggregator):
    """Implementation backed by the Plaid API (sandbox/production)."""

    def __init__(
        self,
        *,
        client_id: str,
        secret: str,
        env: str = "sandbox",
        http_client: httpx.Client | None = None,
    ) -> None:
        self._client_id = client_id
        self._secret = secret
        self._base_url = f"https://{env}.plaid.com"
        self._client = http_client or httpx.Client(timeout=httpx.Timeout(30.0))

    def _auth_body(self) -> dict[str, str]:
        """Body params Plaid requires on each request."""
        return {"client_id": self._client_id, "secret": self._secret}

    def create_requisition(
        self,
        *,
        institution_id: str,
        reference: str,
        redirect_uri: str,
    ) -> RequisitionResult:
        response = self._client.post(
            f"{self._base_url}/link/token/create",
            json={
                **self._auth_body(),
                "client_name": "Zen Compta",
                "user": {"client_user_id": reference},
                "products": ["transactions"],
                "country_codes": ["FR", "US"],
                "language": "fr",
            },
        )
        _check_status(response, "plaid_link_token_failed")
        payload = _response_json(response, "plaid_link_token_invalid_payload")
        try:
            link = str(payload["link_token"])
        except KeyError as exc:
            raise BankAggregatorError("plaid_link_token_invalid_payload") from exc
        return RequisitionResult(
            requisition_id=link,
            auth_link=f"plaid-link://{link}",
            expires_at=None,
            session_data={},
        )

    def exchange_public_token(self, public_token: str) -> dict:
        """Exchange Plaid public_token for access_token + item_id."""
        response = self._client.post(
            f"{self._base_url}/item/public_token/exchange",
            json={**self._auth_body(), "public_token": public_token},
        )
        _check_status(response, "plaid_exchange_failed")
        payload = _response_json(response, "plaid_exchange_invalid_payload")
        try:
            return {
                "access_token": str(payload["access_token"]),
                "item_id": str(payload["item_id"]),
            }
        except KeyError as exc:
            raise BankAggregatorError("plaid_exchange_invalid_payload") from exc

    def get_requisition_accounts(
        self,
        requisition_id: str,
        session_data: dict | None = None,
    ) -> list[str]:
        access = _require_access_token(session_data)
        response = self._client.post(
            f"{self._base_url}/accounts/get",
            json={**self._auth_body(), "access_token": access},
        )
        _check_status(response, "plaid_accounts_failed")
        payload = _response_json(response, "plaid_accounts_invalid_payload")
        accounts = payload.get("accounts")
        if not isinstance(accounts, list):
            raise BankAggregatorError("plaid_accounts_invalid_payload")
        return [
            str(account["account_id"])
            for account in accounts
            if "account_id" in account
        ]

    def get_account_metadata(
        self,
        external_account_id: str,
        session_data: dict | None = None,
    ) -> AccountInfo:
        access = _require_access_token(session_data)
        response = self._client.post(
            f"{self._base_url}/accounts/get",
            json={**self._auth_body(), "access_token": access},
        )
        _check_status(response, "plaid_account_meta_failed")
        payload = _response_json(response, "plaid_account_meta_invalid_payload")
        accounts = payload.get("accounts", [])
        if not isinstance(accounts, list):
            raise BankAggregatorError("plaid_account_meta_invalid_payload")
        account = next(
            (
                account
                for account in accounts
                if isinstance(account, dict)
                and str(account.get("account_id")) == external_account_id
            ),
            None,
        )
        if account is None:
            raise BankAggregatorError("plaid_account_meta_not_found")
        mask = account.get("mask")
        return AccountInfo(
            external_account_id=external_account_id,
            iban_last4=str(mask) if mask else None,
            name=str(account.get("official_name") or account.get("name") or "Compte"),
            currency=str(account.get("balances", {}).get("iso_currency_code") or "EUR"),
        )

    def fetch_transactions(
        self,
        *,
        external_account_id: str,
        date_from: date,
        session_data: dict | None = None,
    ) -> list[TransactionInfo]:
        access = _require_access_token(session_data)
        result: list[TransactionInfo] = []
        offset = 0
        count = 500
        while True:
            response = self._client.post(
                f"{self._base_url}/transactions/get",
                json={
                    **self._auth_body(),
                    "access_token": access,
                    "start_date": date_from.isoformat(),
                    "end_date": date.today().isoformat(),
                    "options": {
                        "account_ids": [external_account_id],
                        "count": count,
                        "offset": offset,
                    },
                },
            )
            _check_status(response, "plaid_transactions_failed")
            payload = _response_json(response, "plaid_transactions_invalid_payload")
            transactions_raw = payload.get("transactions")
            if not isinstance(transactions_raw, list):
                raise BankAggregatorError("plaid_transactions_invalid_payload")
            for raw in transactions_raw:
                if not isinstance(raw, dict):
                    continue
                if str(raw.get("account_id")) != external_account_id:
                    continue
                tx = _parse_transaction(raw)
                if tx is not None:
                    result.append(tx)
            total_transactions = payload.get("total_transactions")
            offset += len(transactions_raw)
            if (
                not isinstance(total_transactions, int)
                or offset >= total_transactions
                or not transactions_raw
            ):
                break
        return result


def _parse_transaction(raw: dict[str, Any]) -> TransactionInfo | None:
    external_id = raw.get("transaction_id")
    if not external_id:
        return None
    booking_date_str = raw.get("date")
    if not booking_date_str:
        return None
    try:
        booking_date = date.fromisoformat(str(booking_date_str))
    except ValueError:
        return None
    authorized_str = raw.get("authorized_date")
    try:
        value_date = date.fromisoformat(str(authorized_str)) if authorized_str else None
    except ValueError:
        return None
    amount_raw = raw.get("amount")
    if amount_raw is None:
        return None
    try:
        amount = -Decimal(str(amount_raw))
    except InvalidOperation:
        return None
    currency = str(
        raw.get("iso_currency_code") or raw.get("unofficial_currency_code") or "EUR"
    )
    description = str(raw.get("name") or raw.get("merchant_name") or "")
    merchant = raw.get("merchant_name")
    creditor = str(merchant) if merchant and amount < 0 else None
    debtor = str(merchant) if merchant and amount >= 0 else None
    return TransactionInfo(
        external_id=str(external_id),
        booking_date=booking_date,
        value_date=value_date,
        amount=amount,
        currency=currency,
        description=description.strip(),
        creditor_name=creditor,
        debtor_name=debtor,
        raw_payload=_sanitized_payload(raw),
    )


def _sanitized_payload(raw: dict[str, Any]) -> dict[str, Any]:
    allowed = (
        "transaction_id",
        "date",
        "authorized_date",
        "amount",
        "iso_currency_code",
        "name",
        "payment_channel",
    )
    return {key: raw[key] for key in allowed if key in raw}


def _require_access_token(session_data: dict | None) -> str:
    value = (session_data or {}).get("access_token")
    if not value:
        raise BankAggregatorError("plaid_session_missing")
    return str(value)


def _response_json(response: httpx.Response, error_code: str) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError as exc:
        raise BankAggregatorError(error_code) from exc
    if not isinstance(payload, dict):
        raise BankAggregatorError(error_code)
    return payload


def _check_status(response: httpx.Response, error_code: str) -> None:
    if response.status_code < 200 or response.status_code >= 300:
        raise BankAggregatorError(f"{error_code}: {response.status_code}")
