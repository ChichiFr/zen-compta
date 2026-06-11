import { formatMoney } from "@/lib/format";
import type {
  DashboardSummary,
  MonthlyForecastSummary,
  MonthlyPerformanceSummary,
} from "@/types/api";

function MetricCard({
  help,
  label,
  value,
}: {
  help: string;
  label: string;
  value: string;
}) {
  return (
    <article className="rounded-md border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-sm font-medium text-slate-500">{label}</p>
      <p className="mt-3 text-2xl font-semibold text-slate-950">{value}</p>
      <p className="mt-2 text-sm leading-5 text-slate-500">{help}</p>
    </article>
  );
}

export function DashboardMetrics({
  dashboard,
  forecast,
  performance,
}: {
  dashboard: DashboardSummary;
  forecast: MonthlyForecastSummary | null;
  performance: MonthlyPerformanceSummary | null;
}) {
  const normalForecast = forecast?.scenarios.find(
    (scenario) => scenario.key === "normal",
  );
  const metrics = [
    {
      label: "CA HT",
      value: formatMoney(dashboard.sales_ht),
      help: "Ventes mensuelles saisies.",
    },
    {
      label: "EBE Cash",
      value: performance
        ? formatMoney(performance.performance.ebe_cash)
        : "Non disponible",
      help: "Performance d exploitation hors flux exceptionnels.",
    },
    {
      label: "Cash estime",
      value: formatMoney(dashboard.estimated_cash),
      help: "Tresorerie depart + ventes TTC - factures TTC - TVA a payer.",
    },
    {
      label: "Fin de mois prevue",
      value: normalForecast
        ? formatMoney(normalForecast.ending_cash_estimate)
        : "Non disponible",
      help: "Simulation cash avec les hypotheses de prevision.",
    },
  ];

  return (
    <section className="grid gap-4 lg:grid-cols-4">
      {metrics.map((metric) => (
        <MetricCard key={metric.label} {...metric} />
      ))}
    </section>
  );
}
