import type { Invoice } from "@/types/api";

import Link from "next/link";

import { validateInvoiceAction } from "@/app/actions";

export function AssistantReviewCard({
  invoices,
  summaryText,
  count,
  openingCash,
  period,
}: {
  invoices: Invoice[];
  summaryText: string;
  count: number;
  openingCash: string;
  period: string;
}) {
  if (count === 0) {
    return (
      <section className="rounded-md border border-emerald-200 bg-emerald-50 p-5 text-sm text-emerald-900">
        Aucune facture en attente. Tout est a jour.
      </section>
    );
  }

  return (
    <section className="space-y-4">
      <div className="rounded-md border border-amber-200 bg-amber-50 p-5">
        <h2 className="text-lg font-semibold text-amber-900">
          {count} facture{count > 1 ? "s" : ""} a traiter
        </h2>
        <p className="mt-2 text-sm text-amber-800">{summaryText}</p>
      </div>

      <div className="space-y-3">
        {invoices.slice(0, 5).map((invoice) => (
          <article
            className="rounded-md border border-slate-200 bg-white p-5"
            key={invoice.id}
          >
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-lg font-semibold">
                  {invoice.supplier_name}
                </p>
                <p className="text-sm text-slate-500">
                  {invoice.invoice_date ?? "Date non renseignee"}
                  {invoice.invoice_number
                    ? ` — N° ${invoice.invoice_number}`
                    : ""}
                </p>
              </div>
              <p className="text-xl font-semibold">
                {invoice.total_ttc} EUR
              </p>
            </div>
            <div className="mt-3 flex gap-3">
              <form action={validateInvoiceAction}>
                <input
                  name="invoice_id"
                  type="hidden"
                  value={invoice.id}
                />
                <input
                  name="period"
                  type="hidden"
                  value={period}
                />
                <input
                  name="opening_cash"
                  type="hidden"
                  value={openingCash}
                />
                <input
                  name="return_to"
                  type="hidden"
                  value="/assistant"
                />
                <button
                  className="rounded-md bg-emerald-700 px-4 py-2 text-sm font-semibold text-white"
                  type="submit"
                >
                  Valider
                </button>
              </form>
              <Link
                className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-800"
                href="/invoices"
              >
                Corriger
              </Link>
            </div>
          </article>
        ))}
      </div>

      {count > 5 && (
        <Link
          className="block text-center text-sm font-semibold text-slate-600 underline-offset-4 hover:underline"
          href="/invoices"
        >
          Voir les {count - 5} autres factures
        </Link>
      )}
    </section>
  );
}
