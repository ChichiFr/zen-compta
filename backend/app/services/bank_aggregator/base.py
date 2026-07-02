from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal


class BankAggregatorError(Exception):
    """Raised when the upstream bank API call fails or returns unexpected data."""


@dataclass
class RequisitionResult:
    requisition_id: str
    auth_link: str
    expires_at: datetime | None
    session_data: dict = field(default_factory=dict)


@dataclass
class AccountInfo:
    external_account_id: str
    iban_last4: str | None
    name: str
    currency: str


@dataclass
class TransactionInfo:
    external_id: str
    booking_date: date
    value_date: date | None
    amount: Decimal
    currency: str
    description: str
    creditor_name: str | None
    debtor_name: str | None
    raw_payload: dict = field(default_factory=dict)


class BankAggregator(ABC):
    """Agnostic interface to a bank account aggregation provider."""

    @abstractmethod
    def create_requisition(
        self,
        *,
        institution_id: str,
        reference: str,
        redirect_uri: str,
    ) -> RequisitionResult:
        """Create a requisition and return the auth link to redirect the user to."""

    @abstractmethod
    def get_requisition_accounts(
        self,
        requisition_id: str,
        session_data: dict | None = None,
    ) -> list[str]:
        """Return account ids using optional provider-specific persisted data."""

    @abstractmethod
    def get_account_metadata(
        self,
        external_account_id: str,
        session_data: dict | None = None,
    ) -> AccountInfo:
        """Return account metadata using optional provider-specific persisted data."""

    @abstractmethod
    def fetch_transactions(
        self,
        *,
        external_account_id: str,
        date_from: date,
        session_data: dict | None = None,
    ) -> list[TransactionInfo]:
        """Fetch transactions using optional provider-specific persisted data."""
