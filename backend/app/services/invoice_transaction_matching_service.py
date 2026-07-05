from __future__ import annotations

import unicodedata
import uuid
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BankTransaction, Invoice, InvoiceStatus

# A supplier payment usually happens on or shortly after the invoice date.
# Card payments can be booked a couple of days before the invoice is issued
# (e.g. cash-and-carry), hence the small negative margin.
AUTO_MATCH_DAYS_BEFORE_INVOICE = 3
AUTO_MATCH_DAYS_AFTER_INVOICE = 45

SUGGESTION_WINDOW_DAYS = 90
SUGGESTION_AMOUNT_TOLERANCE = Decimal("0.01")  # 1%


class TransactionNotMatchableError(Exception):
    """Raised when trying to match a credit (incoming) transaction."""


class InvoiceNotMatchableError(Exception):
    """Raised when the invoice does not exist or is not validated."""


class InvoiceTransactionMatchingService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def auto_match_all(self) -> int:
        """Link unmatched debit transactions to validated invoices.

        Conservative on purpose: a link is only created when the amounts
        match exactly and a single invoice remains after filtering by date
        window (and supplier name when several invoices share the amount).
        Ambiguous cases are left for manual matching.
        """
        transactions = self.db.scalars(
            select(BankTransaction).where(
                BankTransaction.matched_invoice_id.is_(None),
                BankTransaction.amount < 0,
            )
        ).all()
        invoices = self.db.scalars(
            select(Invoice).where(
                Invoice.status == InvoiceStatus.VALIDATED,
                Invoice.invoice_date.is_not(None),
            )
        ).all()
        already_matched_invoice_ids = set(
            self.db.scalars(
                select(BankTransaction.matched_invoice_id).where(
                    BankTransaction.matched_invoice_id.is_not(None)
                )
            ).all()
        )
        available = [
            invoice
            for invoice in invoices
            if invoice.id not in already_matched_invoice_ids
        ]

        matched = 0
        for transaction in transactions:
            candidates = [
                invoice
                for invoice in available
                if invoice.total_ttc == -transaction.amount
                and _within_auto_window(transaction, invoice)
            ]
            if len(candidates) > 1:
                candidates = [
                    invoice
                    for invoice in candidates
                    if _supplier_in_description(invoice, transaction)
                ]
            if len(candidates) != 1:
                continue
            invoice = candidates[0]
            transaction.matched_invoice_id = invoice.id
            transaction.match_source = "auto"
            available.remove(invoice)
            matched += 1
        return matched

    def suggestions(self, transaction: BankTransaction) -> list[Invoice]:
        """Candidate invoices for manual matching, best first."""
        amount = -transaction.amount
        if amount <= 0:
            return []
        matched_ids = set(
            self.db.scalars(
                select(BankTransaction.matched_invoice_id).where(
                    BankTransaction.matched_invoice_id.is_not(None)
                )
            ).all()
        )
        invoices = self.db.scalars(
            select(Invoice).where(
                Invoice.status == InvoiceStatus.VALIDATED,
                Invoice.invoice_date.is_not(None),
            )
        ).all()

        candidates: list[tuple[tuple[int, int, int], Invoice]] = []
        for invoice in invoices:
            if invoice.id in matched_ids:
                continue
            assert invoice.invoice_date is not None
            date_gap = abs((transaction.booking_date - invoice.invoice_date).days)
            if date_gap > SUGGESTION_WINDOW_DAYS:
                continue
            amount_gap = abs(invoice.total_ttc - amount)
            if amount_gap > invoice.total_ttc * SUGGESTION_AMOUNT_TOLERANCE:
                continue
            name_bonus = 0 if _supplier_in_description(invoice, transaction) else 1
            exact_bonus = 0 if amount_gap == 0 else 1
            candidates.append(((exact_bonus, name_bonus, date_gap), invoice))

        candidates.sort(key=lambda item: item[0])
        return [invoice for _, invoice in candidates]

    def match_manually(
        self,
        transaction: BankTransaction,
        invoice_id: uuid.UUID,
    ) -> None:
        if transaction.amount >= 0:
            raise TransactionNotMatchableError(str(transaction.id))
        invoice = self.db.get(Invoice, invoice_id)
        if invoice is None or invoice.status != InvoiceStatus.VALIDATED:
            raise InvoiceNotMatchableError(str(invoice_id))
        transaction.matched_invoice_id = invoice.id
        transaction.match_source = "manual"

    def unmatch(self, transaction: BankTransaction) -> None:
        transaction.matched_invoice_id = None
        transaction.match_source = None


def _within_auto_window(
    transaction: BankTransaction, invoice: Invoice
) -> bool:
    assert invoice.invoice_date is not None
    earliest = invoice.invoice_date - timedelta(
        days=AUTO_MATCH_DAYS_BEFORE_INVOICE
    )
    latest = invoice.invoice_date + timedelta(days=AUTO_MATCH_DAYS_AFTER_INVOICE)
    return earliest <= transaction.booking_date <= latest


def _supplier_in_description(
    invoice: Invoice, transaction: BankTransaction
) -> bool:
    supplier = _normalize(invoice.supplier_name)
    if not supplier:
        return False
    return supplier in _normalize(transaction.description)


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    without_accents = "".join(
        char for char in decomposed if not unicodedata.combining(char)
    )
    return " ".join(without_accents.lower().split())
