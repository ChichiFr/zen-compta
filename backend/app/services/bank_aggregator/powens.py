from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urlencode

import httpx

from app.services.bank_aggregator.base import (
    AccountInfo,
    BankAggregator,
    BankAggregatorError,
    RequisitionResult,
    TransactionInfo,
)


class PowensAggregator(BankAggregator):
    """Implementation backed by the Powens Bank API."""

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        domain: str,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._domain = domain
        self._base_url = f"https://{domain}-sandbox.biapi.pro/2.0"
        self._client = http_client or httpx.Client(timeout=httpx.Timeout(30.0))

    def _create_session_data(self) -> dict:
        response = self._client.post(
            f"{self._base_url}/auth/init",
            json={
                "client_id": self._client_id,
                "client_secret": self._client_secret,
            },
        )
        if response.status_code < 200 or response.status_code >= 300:
            _raise_upstream_error("powens_token_failed", response.status_code)
        payload = _response_json(response, "powens_token_invalid_payload")
        try:
            return {
                "auth_token": str(payload["auth_token"]),
                "id_user": payload["id_user"],
            }
        except KeyError as exc:
            raise BankAggregatorError("powens_token_invalid_payload") from exc

    def _auth_headers(self, session_data: dict | None) -> dict[str, str]:
        bearer_value = (session_data or {}).get("auth_token")
        if not bearer_value:
            raise BankAggregatorError("powens_session_missing")
        return {"Authorization": f"Bearer {bearer_value}"}

    def create_requisition(
        self,
        *,
        institution_id: str,
        reference: str,
        redirect_uri: str,
    ) -> RequisitionResult:
        session_data = self._create_session_data()
        response = self._client.get(
            f"{self._base_url}/auth/token/code",
            headers=self._auth_headers(session_data),
        )
        if response.status_code < 200 or response.status_code >= 300:
            _raise_upstream_error("powens_token_code_failed", response.status_code)
        payload = _response_json(response, "powens_token_code_invalid_payload")
        try:
            code = str(payload["code"])
        except KeyError as exc:
            raise BankAggregatorError("powens_token_code_invalid_payload") from exc

        webview_params = urlencode(
            {
                "domain": f"{self._domain}-sandbox",
                "client_id": self._client_id,
                "redirect_uri": _redirect_uri_with_reference(redirect_uri, reference),
                "code": code,
            }
        )
        return RequisitionResult(
            requisition_id=code,
            auth_link=f"https://webview.powens.com/connect?{webview_params}",
            expires_at=None,
            session_data=session_data,
        )

    def get_requisition_accounts(
        self,
        requisition_id: str,
        session_data: dict | None = None,
    ) -> list[str]:
        response = self._client.get(
            f"{self._base_url}/users/me/connections/{requisition_id}/accounts",
            headers=self._auth_headers(session_data),
        )
        if response.status_code < 200 or response.status_code >= 300:
            _raise_upstream_error(
                "powens_connection_accounts_failed", response.status_code
            )
        payload = _response_json(
            response, "powens_connection_accounts_invalid_payload"
        )
        accounts = payload.get("accounts")
        if not isinstance(accounts, list):
            raise BankAggregatorError("powens_connection_accounts_invalid_payload")
        return [str(account["id"]) for account in accounts if "id" in account]

    def get_account_metadata(
        self,
        external_account_id: str,
        session_data: dict | None = None,
    ) -> AccountInfo:
        response = self._client.get(
            f"{self._base_url}/users/me/accounts/{external_account_id}",
            headers=self._auth_headers(session_data),
        )
        if response.status_code < 200 or response.status_code >= 300:
            _raise_upstream_error("powens_account_details_failed", response.status_code)
        payload = _response_json(response, "powens_account_details_invalid_payload")
        account = payload.get("account", payload)
        if not isinstance(account, dict):
            raise BankAggregatorError("powens_account_details_invalid_payload")
        iban = account.get("iban", "")
        return AccountInfo(
            external_account_id=external_account_id,
            iban_last4=iban[-4:] if iban else None,
            name=str(account.get("name") or "Compte bancaire"),
            currency=_currency_code(account.get("currency")),
        )

    def fetch_transactions(
        self,
        *,
        external_account_id: str,
        date_from: date,
        session_data: dict | None = None,
    ) -> list[TransactionInfo]:
        response = self._client.get(
            f"{self._base_url}/users/me/accounts/{external_account_id}/transactions",
            params={"min_date": date_from.isoformat(), "limit": "500"},
            headers=self._auth_headers(session_data),
        )
        if response.status_code < 200 or response.status_code >= 300:
            _raise_upstream_error("powens_transactions_failed", response.status_code)
        payload = _response_json(response, "powens_transactions_invalid_payload")
        transactions_payload = payload.get("transactions")
        if not isinstance(transactions_payload, list):
            raise BankAggregatorError("powens_transactions_invalid_payload")

        transactions: list[TransactionInfo] = []
        for raw in transactions_payload:
            if not isinstance(raw, dict):
                raise BankAggregatorError("powens_transactions_invalid_payload")
            try:
                tx = _parse_transaction(raw)
            except (InvalidOperation, TypeError, ValueError) as exc:
                raise BankAggregatorError(
                    "powens_transactions_invalid_payload"
                ) from exc
            if tx is not None:
                transactions.append(tx)
        return transactions


def _parse_transaction(raw: dict[str, Any]) -> TransactionInfo | None:
    external_id = raw.get("id")
    if external_id is None:
        return None

    booking_date_str = raw.get("date")
    if not booking_date_str:
        return None
    booking_date = date.fromisoformat(str(booking_date_str))
    value_date_str = raw.get("vdate")
    value_date = date.fromisoformat(str(value_date_str)) if value_date_str else None

    amount_raw = raw.get("value")
    if amount_raw is None:
        return None
    amount = Decimal(str(amount_raw))
    currency = _currency_code(raw.get("currency"))
    description = (
        raw.get("wording")
        or raw.get("simplified_wording")
        or raw.get("original_wording")
        or ""
    )
    counterparty_name = _counterparty_name(raw.get("counterparty"))

    return TransactionInfo(
        external_id=str(external_id),
        booking_date=booking_date,
        value_date=value_date,
        amount=amount,
        currency=currency,
        description=str(description).strip(),
        creditor_name=counterparty_name if amount < 0 else None,
        debtor_name=counterparty_name if amount >= 0 else None,
        raw_payload=_sanitized_transaction_payload(raw),
    )


def _response_json(response: httpx.Response, error_code: str) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError as exc:
        raise BankAggregatorError(error_code) from exc
    if not isinstance(payload, dict):
        raise BankAggregatorError(error_code)
    return payload


def _raise_upstream_error(error_code: str, status_code: int) -> None:
    raise BankAggregatorError(f"{error_code}: {status_code}")


def _currency_code(payload: Any) -> str:
    if isinstance(payload, dict):
        return str(payload.get("id") or "EUR")
    if isinstance(payload, str):
        return payload
    return "EUR"


def _counterparty_name(payload: Any) -> str | None:
    if isinstance(payload, dict) and payload.get("name"):
        return str(payload["name"])
    if isinstance(payload, str):
        return payload
    return None


def _redirect_uri_with_reference(redirect_uri: str, reference: str) -> str:
    separator = "&" if "?" in redirect_uri else "?"
    return f"{redirect_uri}{separator}ref={reference}"


def _sanitized_transaction_payload(raw: dict[str, Any]) -> dict[str, Any]:
    allowed_keys = (
        "id",
        "date",
        "vdate",
        "value",
        "currency",
        "wording",
    )
    return {key: raw[key] for key in allowed_keys if key in raw}
