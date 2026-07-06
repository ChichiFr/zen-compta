import Link from "next/link";

import type { BankAnomaliesSummary } from "@/types/api";

type Props = {
  active: boolean;
  openingCash: string;
  period: string;
  summary: BankAnomaliesSummary;
};

export function AnomaliesCard({ active, openingCash, period, summary }: Props) {
  const params = new URLSearchParams({ openingCash, period });
  if (!active) {
    params.set("anomalies", "invoices");
  }
  const href = `/bank?${params.toString()}`;

  return (
    <Link
      className={`block rounded-md border p-5 transition ${
        active
          ? "border-amber-400 bg-amber-50"
          : "border-slate-200 bg-white hover:border-amber-200"
      }`}
      href={href}
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
  );
}
