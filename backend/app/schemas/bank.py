from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.bank import BankConnectionStatus


class BankConnectionRead(BaseModel):
    id: UUID
    provider: str
    institution_id: str
    institution_name: str
    reference: str
    status: BankConnectionStatus
    expires_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BankConnectionStartResult(BaseModel):
    connection: BankConnectionRead
    auth_link: str


class BankConnectionCompleteRequest(BaseModel):
    ref: str
    connection_id: str | None = None
    public_token: str | None = None


class BankAccountRead(BaseModel):
    id: UUID
    external_account_id: str
    iban_last4: str | None
    name: str
    currency: str

    model_config = ConfigDict(from_attributes=True)


class BankTransactionRead(BaseModel):
    id: UUID
    booking_date: date
    value_date: date | None
    amount: Decimal
    currency: str
    description: str
    creditor_name: str | None
    debtor_name: str | None

    model_config = ConfigDict(from_attributes=True)


class BankSyncResult(BaseModel):
    connection_id: UUID
    new_transactions_count: int
    total_transactions_count: int
