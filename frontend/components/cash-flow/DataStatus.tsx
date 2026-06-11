import type { DashboardSummary, MonthlySales } from "@/types/api";

export function DataStatus({
  dashboard,
  monthlySales,
  periodStart,
}: {
  dashboard: DashboardSummary | null;
  monthlySales: MonthlySales | null;
  periodStart: string;
}) {
  return (
    <aside className="rounded-md border border-slate-200 bg-white p-5">
      <h2 className="text-base font-semibold">Etat donnees</h2>
      <dl className="mt-4 space-y-4 text-sm">
        <div>
          <dt className="font-medium text-slate-500">Mois analyse</dt>
          <dd className="mt-1 font-semibold text-slate-950">{periodStart}</dd>
        </div>
        <div>
          <dt className="font-medium text-slate-500">Ventes en base</dt>
          <dd className="mt-1 font-semibold text-slate-950">
            {monthlySales ? "Oui" : "Non"}
          </dd>
        </div>
        <div>
          <dt className="font-medium text-slate-500">Banque connectee</dt>
          <dd className="mt-1 font-semibold text-slate-950">
            {dashboard?.cash_is_bank_connected ? "Oui" : "Non"}
          </dd>
        </div>
      </dl>
    </aside>
  );
}
