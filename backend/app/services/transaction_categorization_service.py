from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.bank import BankTransaction
from app.models.bank_transaction_rule import BankTransactionRule
from app.services.invoice_categories import ALLOWED_CATEGORY_CODES


class UnknownCategoryError(ValueError):
    pass


class DuplicateRulePatternError(ValueError):
    pass


class EmptyRulePatternError(ValueError):
    pass


class TransactionCategorizationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def categorize_transaction(self, transaction: BankTransaction) -> None:
        """Assign a category from the first matching rule.

        Never overwrites a manual category. Rules match as case-insensitive
        substrings of the transaction description; the oldest rule wins so
        results stay stable as new rules are added.
        """
        if transaction.category_source == "manual":
            return

        haystack = _normalize(transaction.description)
        for rule in self._ordered_rules():
            if _normalize(rule.pattern) in haystack:
                transaction.category_code = rule.category_code
                transaction.category_source = "rule"
                transaction.category_rule_id = rule.id
                return

        transaction.category_code = None
        transaction.category_source = None
        transaction.category_rule_id = None

    def categorize_many(self, transactions: list[BankTransaction]) -> int:
        applied = 0
        for transaction in transactions:
            before = transaction.category_code
            self.categorize_transaction(transaction)
            if transaction.category_code and transaction.category_code != before:
                applied += 1
        return applied

    def set_manual_category(
        self,
        transaction: BankTransaction,
        category_code: str,
    ) -> None:
        if category_code not in ALLOWED_CATEGORY_CODES:
            raise UnknownCategoryError(category_code)
        transaction.category_code = category_code
        transaction.category_source = "manual"
        transaction.category_rule_id = None

    def create_rule(
        self,
        pattern: str,
        category_code: str,
    ) -> BankTransactionRule:
        normalized_pattern = pattern.strip()
        if not normalized_pattern:
            raise EmptyRulePatternError("empty_pattern")
        if category_code not in ALLOWED_CATEGORY_CODES:
            raise UnknownCategoryError(category_code)
        existing = self.db.scalar(
            select(BankTransactionRule).where(
                BankTransactionRule.pattern == normalized_pattern
            )
        )
        if existing is not None:
            raise DuplicateRulePatternError(normalized_pattern)

        rule = BankTransactionRule(
            pattern=normalized_pattern,
            category_code=category_code,
        )
        self.db.add(rule)
        self.db.flush()
        return rule

    def recategorize_all(self) -> int:
        """Re-run rules against every transaction not categorized manually.

        Called after a rule is created so historical transactions pick up
        the new rule too.
        """
        transactions = self.db.scalars(
            select(BankTransaction).where(
                BankTransaction.category_source.is_distinct_from("manual")
            )
        ).all()
        return self.categorize_many(list(transactions))

    def _ordered_rules(self) -> list[BankTransactionRule]:
        return list(
            self.db.scalars(
                select(BankTransactionRule).order_by(
                    BankTransactionRule.created_at.asc(),
                    BankTransactionRule.pattern.asc(),
                )
            ).all()
        )


def _normalize(value: str) -> str:
    return value.lower().strip()
