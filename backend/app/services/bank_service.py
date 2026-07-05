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
    BankTransactionRule,
)
from app.models.invoice import Invoice
from app.services.bank_aggregator import (
    BankAggregator,
    build_bank_aggregator,
)
from app.services.invoice_transaction_matching_service import (
    InvoiceTransactionMatchingService,
)
from app.services.transaction_categorization_service import (
    TransactionCategorizationService,
)


class BankAggregatorUnavailableError(Exception):
    pass


class BankConnectionNotFoundError(Exception):
    pass


class BankTransactionNotFoundError(Exception):
    pass


class BankTransactionRuleNotFoundError(Exception):
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
        institution_name = {
            "gocardless": "GoCardless Sandbox Finance",
            "powens": "Powens Sandbox",
            "plaid": "Plaid Sandbox",
        }.get(settings.bank_aggregator_provider.lower(), "Banque sandbox")
        connection = BankConnection(
            provider=settings.bank_aggregator_provider.lower(),
            external_requisition_id=result.requisition_id,
            institution_id=institution_id,
            institution_name=institution_name,
            reference=reference,
            status=BankConnectionStatus.CREATED,
            expires_at=result.expires_at,
            provider_session_data=result.session_data,
        )
        connection.auth_link = result.auth_link
        self.db.add(connection)
        self.db.commit()
        self.db.refresh(connection)
        connection.auth_link = result.auth_link
        return connection

    def complete_connection(
        self,
        reference: str,
        *,
        upstream_connection_id: str | None = None,
        public_token: str | None = None,
    ) -> BankConnection:
        aggregator = self._require_aggregator()
        connection = self._get_connection_by_reference(reference)
        if connection.status == BankConnectionStatus.LINKED:
            # Idempotent: already linked, don't refetch accounts.
            return connection
        if public_token and hasattr(aggregator, "exchange_public_token"):
            new_session = aggregator.exchange_public_token(public_token)
            connection.provider_session_data = new_session
            connection.external_requisition_id = new_session["item_id"]
            self.db.flush()
        elif (
            upstream_connection_id
            and upstream_connection_id != connection.external_requisition_id
        ):
            connection.external_requisition_id = upstream_connection_id
            self.db.flush()
        session_data = dict(connection.provider_session_data or {})
        account_ids = aggregator.get_requisition_accounts(
            connection.external_requisition_id,
            session_data=session_data,
        )
        if not account_ids:
            raise BankAggregatorUnavailableError("bank_connection_has_no_accounts")
        existing_account_ids = {
            account.external_account_id for account in connection.accounts
        }
        for external_account_id in account_ids:
            if external_account_id in existing_account_ids:
                continue
            account_info = aggregator.get_account_metadata(
                external_account_id,
                session_data=session_data,
            )
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
        session_data = dict(connection.provider_session_data or {})
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
                session_data=session_data,
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

        TransactionCategorizationService(self.db).categorize_many(new_rows)

        self.db.add_all(new_rows)
        try:
            self.db.commit()
        except IntegrityError:
            # Race against a concurrent sync: fall back to per-row inserts so
            # we still persist what we can and skip true duplicates.
            self.db.rollback()
            inserted = self._insert_transactions_one_by_one(new_rows)
            self._auto_match_transactions()
            return inserted
        self._auto_match_transactions()
        return len(new_rows)

    def _auto_match_transactions(self) -> None:
        matched = InvoiceTransactionMatchingService(self.db).auto_match_all()
        if matched:
            self.db.commit()

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

    def get_transaction(self, transaction_id: uuid.UUID) -> BankTransaction:
        transaction = self.db.get(BankTransaction, transaction_id)
        if transaction is None:
            raise BankTransactionNotFoundError(str(transaction_id))
        return transaction

    def update_transaction_category(
        self,
        transaction_id: uuid.UUID,
        *,
        category_code: str,
        create_rule: bool = False,
        rule_pattern: str | None = None,
    ) -> BankTransaction:
        transaction = self.get_transaction(transaction_id)
        categorization = TransactionCategorizationService(self.db)
        categorization.set_manual_category(transaction, category_code)
        if create_rule and rule_pattern:
            categorization.create_rule(rule_pattern, category_code)
            categorization.recategorize_all()
        self.db.commit()
        self.db.refresh(transaction)
        return transaction

    def run_transaction_matching(self) -> int:
        matched = InvoiceTransactionMatchingService(self.db).auto_match_all()
        self.db.commit()
        return matched

    def get_match_suggestions(
        self, transaction_id: uuid.UUID
    ) -> list[Invoice]:
        transaction = self.get_transaction(transaction_id)
        return InvoiceTransactionMatchingService(self.db).suggestions(transaction)

    def match_transaction(
        self, transaction_id: uuid.UUID, invoice_id: uuid.UUID
    ) -> BankTransaction:
        transaction = self.get_transaction(transaction_id)
        InvoiceTransactionMatchingService(self.db).match_manually(
            transaction, invoice_id
        )
        self.db.commit()
        self.db.refresh(transaction)
        return transaction

    def unmatch_transaction(self, transaction_id: uuid.UUID) -> BankTransaction:
        transaction = self.get_transaction(transaction_id)
        InvoiceTransactionMatchingService(self.db).unmatch(transaction)
        self.db.commit()
        self.db.refresh(transaction)
        return transaction

    def list_transaction_rules(self) -> list[BankTransactionRule]:
        statement = select(BankTransactionRule).order_by(
            BankTransactionRule.created_at.asc(),
            BankTransactionRule.pattern.asc(),
        )
        return list(self.db.scalars(statement).all())

    def delete_transaction_rule(self, rule_id: uuid.UUID) -> None:
        rule = self.db.get(BankTransactionRule, rule_id)
        if rule is None:
            raise BankTransactionRuleNotFoundError(str(rule_id))
        # Detach explicitly instead of relying on ON DELETE SET NULL so the
        # behaviour is identical on SQLite (tests) and PostgreSQL.
        linked = self.db.scalars(
            select(BankTransaction).where(
                BankTransaction.category_rule_id == rule.id
            )
        ).all()
        for transaction in linked:
            transaction.category_rule_id = None
        self.db.delete(rule)
        self.db.commit()

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
