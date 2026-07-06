import Link from "next/link";

import { invoiceCategoryLabel } from "@/lib/invoiceCategories";
import type { BankUnmatchedDebit, BankUnpaidInvoice } from "@/types/api";

type Props = {
  activeSection: "debits" | "invoices";
  connectionId: string;
  openingCash: string;
  period: string;
  unmatchedDebits: BankUnmatchedDebit[];
  unpaidInvoices: BankUnpaidInvoice[];
};

export function AnomaliesDetail({
  activeSection,
  connectionId,
  openingCash,
  period,
  unmatchedDebits,
  unpaidInvoices,
}: Props) {
  if (activeSection === "debits") {
    return (
      <UnmatchedDebitsTable
        connectionId={connectionId}
        openingCash={openingCash}
        period={period}
        transactions={unmatchedDebits}
      />
    );
  }

  return (
    <UnpaidInvoicesTable invoices={unpaidInvoices} />
  );
}

function UnmatchedDebitsTable({
  connectionId,
  openingCash,
  period,
  transactions,
}: {
  connectionId: string;
  openingCash: string;
  period: string;
  transactions: BankUnmatchedDebit[];
}) {
  return (
    <section className="rounded-md border border-rose-200 bg-white">
      <div className="border-b border-rose-100 px-5 py-4">
        <h2 className="text-base font-semibold text-slate-950">
          Transactions sans facture
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          Paiements sortants recents sans facture liee.
        </p>
      </div>
      {transactions.length === 0 ? (
        <EmptyState message="Aucune transaction debit sans facture." />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[860px] text-left text-sm">
            <thead className="bg-slate-50 text-xs font-semibold uppercase text-slate-500">
              <tr>
                <th className="px-5 py-3">Date</th>
                <th className="px-5 py-3">Description</th>
                <th className="px-5 py-3">Categorie</th>
                <th className="px-5 py-3 text-right">Montant</th>
                <th className="px-5 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {transactions.map((transaction) => (
                <UnmatchedDebitRow
                  connectionId={connectionId}
                  key={transaction.id}
                  openingCash={openingCash}
                  period={period}
                  transaction={transaction}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function UnmatchedDebitRow({
  connectionId,
  openingCash,
  period,
  transaction,
}: {
  connectionId: string;
  openingCash: string;
  period: string;
  transaction: BankUnmatchedDebit;
}) {
  const params = new URLSearchParams({
    connection: connectionId,
    match: transaction.id,
    openingCash,
    period,
  });

  return (
    <tr>
      <td className="whitespace-nowrap px-5 py-3 text-slate-600">
        {formatDate(transaction.booking_date)}
      </td>
      <td className="px-5 py-3 font-medium text-slate-950">
        {transaction.description || "Transaction bancaire"}
      </td>
      <td className="px-5 py-3 text-slate-600">
        {transaction.category_code
          ? invoiceCategoryLabel(transaction.category_code)
          : "-"}
      </td>
      <td className="whitespace-nowrap px-5 py-3 text-right font-semibold text-rose-700">
        {formatMoney(Number(transaction.amount), transaction.currency)}
      </td>
      <td className="px-5 py-3 text-right">
        <Link
          className="rounded-md border border-slate-300 bg-white px-2 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50"
          href={`/bank?${params.toString()}`}
        >
          Rapprocher
        </Link>
      </td>
    </tr>
  );
}

function UnpaidInvoicesTable({
  invoices,
}: {
  invoices: BankUnpaidInvoice[];
}) {
  return (
    <section className="rounded-md border border-amber-200 bg-white">
      <div className="border-b border-amber-100 px-5 py-4">
        <h2 className="text-base font-semibold text-slate-950">
          Factures sans paiement
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          Factures validees recentes sans transaction bancaire liee.
        </p>
      </div>
      {invoices.length === 0 ? (
        <EmptyState message="Aucune facture validee sans paiement." />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="bg-slate-50 text-xs font-semibold uppercase text-slate-500">
              <tr>
                <th className="px-5 py-3">Fournisseur</th>
                <th className="px-5 py-3">Date</th>
                <th className="px-5 py-3">Numero</th>
                <th className="px-5 py-3 text-right">TTC</th>
                <th className="px-5 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {invoices.map((invoice) => (
                <tr key={invoice.id}>
                  <td className="px-5 py-3 font-medium text-slate-950">
                    {invoice.supplier_name}
                  </td>
                  <td className="whitespace-nowrap px-5 py-3 text-slate-600">
                    {invoice.invoice_date
                      ? formatDate(invoice.invoice_date)
                      : "Date inconnue"}
                  </td>
                  <td className="px-5 py-3 text-slate-600">
                    {invoice.invoice_number || "-"}
                  </td>
                  <td className="whitespace-nowrap px-5 py-3 text-right font-semibold text-slate-950">
                    {formatMoney(Number(invoice.total_ttc), "EUR")}
                  </td>
                  <td className="px-5 py-3 text-right">
                    <Link
                      className="rounded-md border border-slate-300 bg-white px-2 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                      href="/invoices"
                    >
                      Voir
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function EmptyState({ message }: { message: string }) {
  return <p className="px-5 py-6 text-sm text-slate-500">{message}</p>;
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
