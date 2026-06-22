from __future__ import annotations

import time
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


class GoCardlessAggregator(BankAggregator):
    """Implementation backed by the GoCardless Bank Account Data API."""

    BASE_URL = "https://bankaccountdata.gocardless.com/api/v2"
    TOKEN_REFRESH_BUFFER_SECONDS = 60

    def __init__(
        self,
        *,
        secret_id: str,
        secret_key: str,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._secret_id = secret_id
        self._secret_key = secret_key
        self._client = http_client or httpx.Client(timeout=httpx.Timeout(30.0))
        self._access_token: str | None = None
        self._access_token_expires_at: float = 0.0

    def _get_access_token(self) -> str:
        now = time.time()
        if (
            self._access_token is not None
            and now
            < self._access_token_expires_at - self.TOKEN_REFRESH_BUFFER_SECONDS
        ):
            return self._access_token

        response = self._client.post(
            f"{self.BASE_URL}/token/new/",
            json={"secret_id": self._secret_id, "secret_key": self._secret_key},
        )
        if response.status_code != 200:
            _raise_upstream_error("gocardless_token_failed", response.status_code)
        payload = _response_json(response, "gocardless_token_invalid_payload")
        try:
            self._access_token = str(payload["access"])
            self._access_token_expires_at = now + int(
                payload.get("access_expires", 86400)
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise BankAggregatorError("gocardless_token_invalid_payload") from exc
        return self._access_token

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._get_access_token()}"}

    def create_requisition(
        self,
        *,
        institution_id: str,
        reference: str,
        redirect_uri: str,
    ) -> RequisitionResult:
        response = self._client.post(
            f"{self.BASE_URL}/requisitions/",
            json={
                "redirect": redirect_uri,
                "institution_id": institution_id,
                "reference": reference,
                "user_language": "FR",
            },
            headers=self._auth_headers(),
        )
        if response.status_code not in (200, 201):
            _raise_upstream_error(
                "gocardless_requisition_failed", response.status_code
            )
        payload = _response_json(response, "gocardless_requisition_invalid_payload")
        try:
            return RequisitionResult(
                requisition_id=str(payload["id"]),
                auth_link=str(payload["link"]),
                expires_at=None,
            )
        except KeyError as exc:
            raise BankAggregatorError(
                "gocardless_requisition_invalid_payload"
            ) from exc

    def get_requisition_accounts(
        self,
        requisition_id: str,
        session_data: dict | None = None,
    ) -> list[str]:
        response = self._client.get(
            f"{self.BASE_URL}/requisitions/{requisition_id}/",
            headers=self._auth_headers(),
        )
        if response.status_code != 200:
            _raise_upstream_error(
                "gocardless_requisition_status_failed", response.status_code
            )
        payload = _response_json(
            response, "gocardless_requisition_status_invalid_payload"
        )
        return list(payload.get("accounts", []))

    def get_account_metadata(
        self,
        external_account_id: str,
        session_data: dict | None = None,
    ) -> AccountInfo:
        response = self._client.get(
            f"{self.BASE_URL}/accounts/{external_account_id}/details/",
            headers=self._auth_headers(),
        )
        if response.status_code != 200:
            _raise_upstream_error(
                "gocardless_account_details_failed", response.status_code
            )
        payload = _response_json(response, "gocardless_account_details_invalid_payload")
        account = payload.get("account", {})
        if not isinstance(account, dict):
            raise BankAggregatorError("gocardless_account_details_invalid_payload")
        iban = account.get("iban", "")
        return AccountInfo(
            external_account_id=external_account_id,
            iban_last4=iban[-4:] if iban else None,
            name=account.get("name") or account.get("ownerName") or "Compte bancaire",
            currency=account.get("currency", "EUR"),
        )

    def fetch_transactions(
        self,
        *,
        external_account_id: str,
        date_from: date,
        session_data: dict | None = None,
    ) -> list[TransactionInfo]:
        response = self._client.get(
            f"{self.BASE_URL}/accounts/{external_account_id}/transactions/",
            params={"date_from": date_from.isoformat()},
            headers=self._auth_headers(),
        )
        if response.status_code != 200:
            _raise_upstream_error(
                "gocardless_transactions_failed", response.status_code
            )
        payload = _response_json(response, "gocardless_transactions_invalid_payload")
        transactions: list[TransactionInfo] = []
        for raw in payload.get("transactions", {}).get("booked", []):
            try:
                tx = _parse_transaction(raw)
            except (InvalidOperation, TypeError, ValueError) as exc:
                raise BankAggregatorError(
                    "gocardless_transactions_invalid_payload"
                ) from exc
            if tx is not None:
                transactions.append(tx)
        return transactions


def _parse_transaction(raw: dict[str, Any]) -> TransactionInfo | None:
    external_id = (
        raw.get("transactionId")
        or raw.get("internalTransactionId")
        or raw.get("entryReference")
    )
    if not external_id:
        return None

    booking_date_str = raw.get("bookingDate") or raw.get("valueDate")
    if not booking_date_str:
        return None
    booking_date = date.fromisoformat(booking_date_str)
    value_date_str = raw.get("valueDate")
    value_date = date.fromisoformat(value_date_str) if value_date_str else None

    amount_data = raw.get("transactionAmount", {})
    amount_raw = amount_data.get("amount")
    if amount_raw is None:
        return None
    amount = Decimal(str(amount_raw))
    currency = amount_data.get("currency", "EUR")

    description = (
        raw.get("remittanceInformationUnstructured")
        or " ".join(raw.get("remittanceInformationUnstructuredArray", []) or [])
        or raw.get("additionalInformation", "")
    )

    return TransactionInfo(
        external_id=str(external_id),
        booking_date=booking_date,
        value_date=value_date,
        amount=amount,
        currency=currency,
        description=description.strip(),
        creditor_name=raw.get("creditorName"),
        debtor_name=raw.get("debtorName"),
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


def _sanitized_transaction_payload(raw: dict[str, Any]) -> dict[str, Any]:
    allowed_keys = (
        "transactionId",
        "internalTransactionId",
        "entryReference",
        "bookingDate",
        "valueDate",
        "transactionAmount",
    )
    return {key: raw[key] for key in allowed_keys if key in raw}
