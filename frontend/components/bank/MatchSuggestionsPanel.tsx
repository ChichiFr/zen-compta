import Link from "next/link";

import { matchBankTransactionAction } from "@/app/actions";
import type { BankMatchSuggestion, BankTransaction } from "@/types/api";

export function MatchSuggestionsPanel({
  allInvoices,
  connectionId,
  openingCash,
  period,
  showAll,
  suggestions,
  transaction,
}: {
  allInvoices: BankMatchSuggestion[] | null;
  connectionId: string;
  openingCash: string;
  period: string;
  showAll: boolean;
  suggestions: BankMatchSuggestion[];
  transaction: BankTransaction;
}) {
  const baseParams = new URLSearchParams({
    connection: connectionId,
    openingCash,
    period,
  });
  const cancelHref = `/bank?${baseParams.toString()}`;
  const toggleAllHref = (() => {
    const params = new URLSearchParams({
      connection: connectionId,
      match: transaction.id,
      openingCash,
      period,
    });
    if (!showAll) {
      params.set("matchAll", "1");
    }
    return `/bank?${params.toString()}`;
  })();

  const suggestionIds = new Set(suggestions.map((invoice) => invoice.id));
  const extraInvoices =
    showAll && allInvoices
      ? allInvoices.filter((invoice) => !suggestionIds.has(invoice.id))
      : [];

  return (
    <section className="rounded-md border border-sky-200 bg-sky-50 p-5">
      <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-center">
        <div>
          <h2 className="text-base font-semibold text-slate-950">
            Rapprocher la transaction
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            {formatDate(transaction.booking_date)} —{" "}
            {transaction.description || "Transaction bancaire"} —{" "}
            {formatMoney(Number(transaction.amount), transaction.currency)}
          </p>
        </div>
        <Link
          className="text-sm font-semibold text-slate-600 underline-offset-4 hover:underline"
          href={cancelHref}
        >
          Annuler
        </Link>
      </div>

      <p className="mt-4 text-xs font-semibold uppercase tracking-wide text-slate-500">
        Suggestions ({suggestions.length})
      </p>
      {suggestions.length === 0 ? (
        <p className="mt-2 text-sm text-slate-600">
          Aucune facture validee ne correspond exactement a ce montant dans les
          90 derniers jours.
        </p>
      ) : (
        <ul className="mt-2 divide-y divide-sky-200 rounded-md border border-sky-200 bg-white">
          {suggestions.map((suggestion) => (
            <InvoiceRow
              connectionId={connectionId}
              invoice={suggestion}
              key={suggestion.id}
              openingCash={openingCash}
              period={period}
              transaction={transaction}
            />
          ))}
        </ul>
      )}

      <div className="mt-4 flex flex-col gap-2">
        <Link
          className="text-sm font-semibold text-slate-700 underline-offset-4 hover:underline"
          href={toggleAllHref}
        >
          {showAll
            ? "Masquer les autres factures non liees"
            : "Voir toutes les factures non liees"}
        </Link>
        {showAll ? (
          extraInvoices.length === 0 ? (
            <p className="text-sm text-slate-600">
              Toutes les factures validees non liees sont deja proposees
              ci-dessus.
            </p>
          ) : (
            <ul className="divide-y divide-slate-200 rounded-md border border-slate-200 bg-white">
              {extraInvoices.map((invoice) => (
                <InvoiceRow
                  connectionId={connectionId}
                  invoice={invoice}
                  key={invoice.id}
                  openingCash={openingCash}
                  period={period}
                  transaction={transaction}
                />
              ))}
            </ul>
          )
        ) : null}
      </div>
    </section>
  );
}

function InvoiceRow({
  connectionId,
  invoice,
  openingCash,
  period,
  transaction,
}: {
  connectionId: string;
  invoice: BankMatchSuggestion;
  openingCash: string;
  period: string;
  transaction: BankTransaction;
}) {
  return (
    <li className="flex flex-col justify-between gap-3 px-4 py-3 sm:flex-row sm:items-center">
      <div>
        <p className="font-medium text-slate-950">{invoice.supplier_name}</p>
        <p className="mt-1 text-xs text-slate-500">
          {invoice.invoice_date
            ? formatDate(invoice.invoice_date)
            : "Date inconnue"}
          {invoice.invoice_number ? ` — n° ${invoice.invoice_number}` : ""}
          {" — "}
          {formatMoney(Number(invoice.total_ttc), "EUR")} TTC
        </p>
      </div>
      <form action={matchBankTransactionAction}>
        <input name="transaction_id" type="hidden" value={transaction.id} />
        <input name="invoice_id" type="hidden" value={invoice.id} />
        <input name="connection_id" type="hidden" value={connectionId} />
        <input name="period" type="hidden" value={period} />
        <input name="opening_cash" type="hidden" value={openingCash} />
        <button
          className="rounded-md bg-slate-950 px-3 py-1.5 text-sm font-semibold text-white"
          type="submit"
        >
          Lier cette facture
        </button>
      </form>
    </li>
  );
}

function formatDate(dateText: string) {
  const [year, month, day] = dateText.split("-");
  if (!year || !month || !day) {
    return dateText;
  }
  return `${day}/${month}/${year}`;
}

function formatMoney(amount: number, currency: string) {
  return new Intl.NumberFormat("fr-FR", {
    currency,
    style: "currency",
  }).format(amount);
}
