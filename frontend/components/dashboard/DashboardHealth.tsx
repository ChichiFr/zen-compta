import { riskLabel } from "@/lib/labels";
import type {
  DashboardSummary,
  MonthlyForecastSummary,
  MonthlyPerformanceSummary,
} from "@/types/api";

export function DashboardHealth({
  dashboard,
  forecast,
  performance,
}: {
  dashboard: DashboardSummary;
  forecast: MonthlyForecastSummary | null;
  performance: MonthlyPerformanceSummary | null;
}) {
  const worstRisk = forecast?.scenarios.some(
    (scenario) => scenario.risk_level === "critical",
  )
    ? "critical"
    : forecast?.scenarios.some((scenario) => scenario.risk_level === "warning")
      ? "warning"
      : "ok";
  const profitable =
    performance && Number(performance.performance.ebe_cash) > 0;

  return (
    <section className="rounded-md border border-slate-200 bg-white p-5">
      <h2 className="text-base font-semibold">Sante du mois</h2>
      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <p className="rounded-md bg-slate-50 p-3 text-sm">
          <span className="block font-semibold">
            {profitable ? "Mois rentable" : "Performance a surveiller"}
          </span>
          <span className="text-slate-500">
            {profitable
              ? "L exploitation gagne de l argent."
              : "L EBE Cash est nul ou negatif."}
          </span>
        </p>
        <p className="rounded-md bg-slate-50 p-3 text-sm">
          <span className="block font-semibold">
            {dashboard.invoices_to_review_count} factures a traiter
          </span>
          <span className="text-slate-500">
            Les factures non validees restent hors exports.
          </span>
        </p>
        <p className="rounded-md bg-slate-50 p-3 text-sm">
          <span className="block font-semibold">
            Risque prevision: {riskLabel(worstRisk)}
          </span>
          <span className="text-slate-500">
            Voir les scenarios detailles dans Prevision.
          </span>
        </p>
      </div>
    </section>
  );
}
