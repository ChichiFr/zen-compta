import Link from "next/link";

import {
  runBankMatchingAction,
  unmatchBankTransactionAction,
} from "@/app/actions";
import { invoiceCategoryLabel } from "@/lib/invoiceCategories";
import type { BankTransaction } from "@/types/api";

import { CategorizeTransactionButton } from "./CategorizeTransactionButton";

export function TransactionList({
  connectionId,
  openingCash,
  period,
  transactions,
}: {
  connectionId: string;
  openingCash: string;
  period: string;
  transactions: BankTransaction[];
}) {
  if (transactions.length === 0) {
    return (
      <section className="rounded-md border border-slate-200 bg-white p-5">
        <h2 className="text-base font-semibold">Transactions</h2>
        <p className="mt-2 text-sm text-slate-500">
          Aucune transaction bancaire importee pour cette connexion.
        </p>
      </section>
    );
  }

  return (
    <section className="rounded-md border border-slate-200 bg-white">
      <div className="flex flex-col justify-between gap-3 border-b border-slate-200 px-5 py-4 sm:flex-row sm:items-center">
        <h2 className="text-base font-semibold">Transactions</h2>
        <form action={runBankMatchingAction}>
          <input name="connection_id" type="hidden" value={connectionId} />
          <input name="period" type="hidden" value={period} />
          <input name="opening_cash" type="hidden" value={openingCash} />
          <button
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-900"
            type="submit"
          >
            Rapprochement auto
          </button>
        </form>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[980px] text-left text-sm">
          <thead className="bg-slate-50 text-xs font-semibold uppercase text-slate-500">
            <tr>
              <th className="px-5 py-3">Date</th>
              <th className="px-5 py-3">Description</th>
              <th className="px-5 py-3">Categorie</th>
              <th className="px-5 py-3">Facture</th>
              <th className="px-5 py-3 text-right">Montant</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {transactions.map((transaction) => {
              const amount = Number(transaction.amount);
              const counterparty =
                transaction.creditor_name ?? transaction.debtor_name ?? "";
              return (
                <tr key={transaction.id}>
                  <td className="whitespace-nowrap px-5 py-3 text-slate-600">
                    {formatDate(transaction.booking_date)}
                  </td>
                  <td className="px-5 py-3">
                    <p className="font-medium text-slate-950">
                      {transaction.description || "Transaction bancaire"}
                    </p>
                    {counterparty ? (
                      <p className="mt-1 text-xs text-slate-500">
                        {counterparty}
                      </p>
                    ) : null}
                  </td>
                  <td className="px-5 py-3">
                    {transaction.category_code ? (
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-xs font-medium text-slate-700">
                          {invoiceCategoryLabel(transaction.category_code)}
                        </span>
                        <span
                          className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${
                            transaction.category_source === "manual"
                              ? "bg-sky-100 text-sky-700"
                              : "bg-emerald-100 text-emerald-700"
                          }`}
                        >
                          {transaction.category_source === "manual"
                            ? "manuel"
                            : "auto"}
                        </span>
                      </div>
                    ) : (
                      <CategorizeTransactionButton
                        connectionId={connectionId}
                        openingCash={openingCash}
                        period={period}
                        transaction={transaction}
                      />
                    )}
                  </td>
                  <td className="px-5 py-3">
                    <MatchCell
                      connectionId={connectionId}
                      openingCash={openingCash}
                      period={period}
                      transaction={transaction}
                    />
                  </td>
                  <td
                    className={`whitespace-nowrap px-5 py-3 text-right font-semibold ${
                      amount >= 0 ? "text-emerald-700" : "text-rose-700"
                    }`}
                  >
                    {formatMoney(amount, transaction.currency)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function MatchCell({
  connectionId,
  openingCash,
  period,
  transaction,
}: {
  connectionId: string;
  openingCash: string;
  period: string;
  transaction: BankTransaction;
}) {
  if (transaction.matched_invoice_id) {
    return (
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${
            transaction.match_source === "manual"
              ? "bg-sky-100 text-sky-700"
              : "bg-emerald-100 text-emerald-700"
          }`}
        >
          Liee ({transaction.match_source === "manual" ? "manuel" : "auto"})
        </span>
        <form action={unmatchBankTransactionAction}>
          <input
            name="transaction_id"
            type="hidden"
            value={transaction.id}
          />
          <input name="connection_id" type="hidden" value={connectionId} />
          <input name="period" type="hidden" value={period} />
          <input name="opening_cash" type="hidden" value={openingCash} />
          <button
            className="text-xs font-semibold text-slate-500 underline-offset-2 hover:underline"
            type="submit"
          >
            Delier
          </button>
        </form>
      </div>
    );
  }

  if (Number(transaction.amount) >= 0) {
    return <span className="text-xs text-slate-400">-</span>;
  }

  const params = new URLSearchParams({
    connection: connectionId,
    match: transaction.id,
    openingCash,
    period,
  });
  return (
    <Link
      className="rounded-md border border-slate-300 bg-white px-2 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50"
      href={`/bank?${params.toString()}`}
    >
      Rapprocher
    </Link>
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
