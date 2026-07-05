import Link from "next/link";

import { matchBankTransactionAction } from "@/app/actions";
import type { BankMatchSuggestion, BankTransaction } from "@/types/api";

export function MatchSuggestionsPanel({
  connectionId,
  openingCash,
  period,
  suggestions,
  transaction,
}: {
  connectionId: string;
  openingCash: string;
  period: string;
  suggestions: BankMatchSuggestion[];
  transaction: BankTransaction;
}) {
  const cancelParams = new URLSearchParams({
    connection: connectionId,
    openingCash,
    period,
  });
  const cancelHref = `/bank?${cancelParams.toString()}`;

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

      {suggestions.length === 0 ? (
        <p className="mt-4 text-sm text-slate-600">
          Aucune facture validee ne correspond a ce montant. Verifie que la
          facture a bien ete importee et validee dans l onglet Factures.
        </p>
      ) : (
        <ul className="mt-4 divide-y divide-sky-200 rounded-md border border-sky-200 bg-white">
          {suggestions.map((suggestion) => (
            <li
              className="flex flex-col justify-between gap-3 px-4 py-3 sm:flex-row sm:items-center"
              key={suggestion.id}
            >
              <div>
                <p className="font-medium text-slate-950">
                  {suggestion.supplier_name}
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  {suggestion.invoice_date
                    ? formatDate(suggestion.invoice_date)
                    : "Date inconnue"}
                  {suggestion.invoice_number
                    ? ` — n° ${suggestion.invoice_number}`
                    : ""}
                  {" — "}
                  {formatMoney(Number(suggestion.total_ttc), "EUR")} TTC
                </p>
              </div>
              <form action={matchBankTransactionAction}>
                <input
                  name="transaction_id"
                  type="hidden"
                  value={transaction.id}
                />
                <input name="invoice_id" type="hidden" value={suggestion.id} />
                <input
                  name="connection_id"
                  type="hidden"
                  value={connectionId}
                />
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
          ))}
        </ul>
      )}
    </section>
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
