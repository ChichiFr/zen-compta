import uuid
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models import (
    BankAccount,
    BankConnection,
    BankConnectionStatus,
    BankTransaction,
)
from app.services.bank_aggregator import (
    BankAggregator,
    build_bank_aggregator,
)


class BankAggregatorUnavailableError(Exception):
    pass


class BankConnectionNotFoundError(Exception):
    pass


class BankService:
    def __init__(self, db: Session) -> None:
        self.db = db
        try:
            self.aggregator: BankAggregator | None = build_bank_aggregator()
        except ValueError:
            self.aggregator = None

    def start_connection(
        self, institution_id: str = "SANDBOXFINANCE_SFIN0000"
    ) -> BankConnection:
        aggregator = self._require_aggregator()
        reference = uuid.uuid4().hex
        result = aggregator.create_requisition(
            institution_id=institution_id,
            reference=reference,
            redirect_uri=settings.gocardless_redirect_uri,
        )
        connection = BankConnection(
            provider=settings.bank_aggregator_provider.lower(),
            external_requisition_id=result.requisition_id,
            institution_id=institution_id,
            institution_name="GoCardless Sandbox Finance",
            reference=reference,
            status=BankConnectionStatus.CREATED,
            expires_at=result.expires_at,
        )
        connection.auth_link = result.auth_link
        self.db.add(connection)
        self.db.commit()
        self.db.refresh(connection)
        connection.auth_link = result.auth_link
        return connection

    def complete_connection(self, reference: str) -> BankConnection:
        aggregator = self._require_aggregator()
        connection = self._get_connection_by_reference(reference)
        if connection.status == BankConnectionStatus.LINKED:
            # Idempotent: already linked, don't refetch accounts.
            return connection
        account_ids = aggregator.get_requisition_accounts(
            connection.external_requisition_id
        )
        if not account_ids:
            raise BankAggregatorUnavailableError("bank_connection_has_no_accounts")
        existing_account_ids = {
            account.external_account_id for account in connection.accounts
        }
        for external_account_id in account_ids:
            if external_account_id in existing_account_ids:
                continue
            account_info = aggregator.get_account_metadata(external_account_id)
            connection.accounts.append(
                BankAccount(
                    external_account_id=account_info.external_account_id,
                    iban_last4=account_info.iban_last4,
                    name=account_info.name,
                    currency=account_info.currency,
                )
            )
        connection.status = BankConnectionStatus.LINKED
        self.db.commit()
        return self.get_connection(connection.id)

    def list_connections(self) -> list[BankConnection]:
        statement = (
            select(BankConnection)
            .options(selectinload(BankConnection.accounts))
            .order_by(BankConnection.created_at.desc())
        )
        return list(self.db.scalars(statement).all())

    def sync_transactions(self, connection_id: uuid.UUID) -> int:
        aggregator = self._require_aggregator()
        connection = self.get_connection(connection_id)
        date_from = date.today() - timedelta(days=90)
        new_rows: list[BankTransaction] = []
        for account in connection.accounts:
            existing_external_ids = {
                external_id
                for external_id in self.db.scalars(
                    select(BankTransaction.external_id).where(
                        BankTransaction.account_id == account.id
                    )
                ).all()
            }
            transactions = aggregator.fetch_transactions(
                external_account_id=account.external_account_id,
                date_from=date_from,
            )
            for transaction in transactions:
                if transaction.external_id in existing_external_ids:
                    continue
                existing_external_ids.add(transaction.external_id)
                new_rows.append(
                    BankTransaction(
                        account_id=account.id,
                        external_id=transaction.external_id,
                        booking_date=transaction.booking_date,
                        value_date=transaction.value_date,
                        amount=transaction.amount,
                        currency=transaction.currency,
                        description=transaction.description,
                        creditor_name=transaction.creditor_name,
                        debtor_name=transaction.debtor_name,
                        raw_payload=transaction.raw_payload,
                    )
                )

        if not new_rows:
            return 0

        self.db.add_all(new_rows)
        try:
            self.db.commit()
        except IntegrityError:
            # Race against a concurrent sync: fall back to per-row inserts so
            # we still persist what we can and skip true duplicates.
            self.db.rollback()
            return self._insert_transactions_one_by_one(new_rows)
        return len(new_rows)

    def _insert_transactions_one_by_one(
        self, rows: list[BankTransaction]
    ) -> int:
        inserted = 0
        for row in rows:
            self.db.add(row)
            try:
                self.db.commit()
            except IntegrityError:
                self.db.rollback()
                continue
            inserted += 1
        return inserted

    def list_transactions(
        self, connection_id: uuid.UUID, limit: int = 100
    ) -> list[BankTransaction]:
        self.get_connection(connection_id)
        statement = (
            select(BankTransaction)
            .join(BankAccount)
            .where(BankAccount.connection_id == connection_id)
            .order_by(
                BankTransaction.booking_date.desc(),
                BankTransaction.created_at.desc(),
            )
            .limit(limit)
        )
        return list(self.db.scalars(statement).all())

    def count_transactions(self, connection_id: uuid.UUID) -> int:
        self.get_connection(connection_id)
        statement = (
            select(func.count())
            .select_from(BankTransaction)
            .join(BankAccount)
            .where(BankAccount.connection_id == connection_id)
        )
        return int(self.db.scalar(statement) or 0)

    def get_connection(self, connection_id: uuid.UUID) -> BankConnection:
        statement = (
            select(BankConnection)
            .options(selectinload(BankConnection.accounts))
            .where(BankConnection.id == connection_id)
        )
        connection = self.db.scalar(statement)
        if connection is None:
            raise BankConnectionNotFoundError(str(connection_id))
        return connection

    def _get_connection_by_reference(self, reference: str) -> BankConnection:
        statement = (
            select(BankConnection)
            .options(selectinload(BankConnection.accounts))
            .where(BankConnection.reference == reference)
        )
        connection = self.db.scalar(statement)
        if connection is None:
            raise BankConnectionNotFoundError(reference)
        return connection

    def _require_aggregator(self) -> BankAggregator:
        if self.aggregator is None:
            raise BankAggregatorUnavailableError("bank_aggregator_unavailable")
        return self.aggregator
