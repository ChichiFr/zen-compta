import Link from "next/link";

import type { BankAnomaliesSummary } from "@/types/api";

type Props = {
  activeSection: "debits" | "invoices" | null;
  openingCash: string;
  period: string;
  summary: BankAnomaliesSummary;
};

export function AnomaliesCard({
  activeSection,
  openingCash,
  period,
  summary,
}: Props) {
  const baseParams = new URLSearchParams({ openingCash, period });
  const debitsHref = withAnomalies(
    baseParams,
    activeSection === "debits" ? null : "debits",
  );
  const invoicesHref = withAnomalies(
    baseParams,
    activeSection === "invoices" ? null : "invoices",
  );

  return (
    <section className="grid gap-4 sm:grid-cols-2">
      <Link
        className={`rounded-md border p-5 transition ${
          activeSection === "debits"
            ? "border-rose-400 bg-rose-50"
            : "border-slate-200 bg-white hover:border-rose-200"
        }`}
        href={debitsHref}
      >
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Transactions sans facture
        </p>
        <p className="mt-2 text-3xl font-semibold text-rose-700">
          {summary.unmatched_debits_count}
        </p>
        <p className="mt-1 text-sm text-slate-500">
          Paiements bancaires des 6 derniers mois non relies a une facture.
        </p>
      </Link>
      <Link
        className={`rounded-md border p-5 transition ${
          activeSection === "invoices"
            ? "border-amber-400 bg-amber-50"
            : "border-slate-200 bg-white hover:border-amber-200"
        }`}
        href={invoicesHref}
      >
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Factures sans paiement
        </p>
        <p className="mt-2 text-3xl font-semibold text-amber-700">
          {summary.unpaid_invoices_count}
        </p>
        <p className="mt-1 text-sm text-slate-500">
          Factures validees des 6 derniers mois sans transaction bancaire liee.
        </p>
      </Link>
    </section>
  );
}

function withAnomalies(base: URLSearchParams, value: string | null) {
  const params = new URLSearchParams(base);
  if (value) {
    params.set("anomalies", value);
  } else {
    params.delete("anomalies");
  }
  return `/bank?${params.toString()}`;
}
