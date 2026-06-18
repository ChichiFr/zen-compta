import Link from "next/link";

const RISK_STYLES = {
  ok: "border-emerald-200 bg-emerald-50 text-emerald-900",
  warning: "border-amber-200 bg-amber-50 text-amber-900",
  critical: "border-rose-200 bg-rose-50 text-rose-900",
} as const;

const RISK_LABELS = {
  ok: "Bonne sante",
  warning: "A surveiller",
  critical: "Attention",
} as const;

export function AssistantDashboardCard({
  summaryText,
  riskLevel,
  alerts,
}: {
  summaryText: string;
  riskLevel: "ok" | "warning" | "critical";
  alerts: string[];
}) {
  const style = RISK_STYLES[riskLevel];
  const label = RISK_LABELS[riskLevel];

  return (
    <section className={`rounded-md border p-5 ${style}`}>
      <div className="flex items-center gap-3">
        <span className="rounded-full bg-white/60 px-3 py-1 text-xs font-bold uppercase tracking-wider">
          {label}
        </span>
        <h2 className="text-lg font-semibold">Resume du mois</h2>
      </div>
      <p className="mt-3 text-sm leading-relaxed">{summaryText}</p>
      {alerts.length > 0 && (
        <ul className="mt-3 space-y-1">
          {alerts.map((alert) => (
            <li className="text-sm font-medium" key={alert}>
              &bull; {alert}
            </li>
          ))}
        </ul>
      )}
      <Link
        className="mt-4 inline-block text-sm font-semibold underline-offset-4 hover:underline"
        href="/"
      >
        Voir le tableau de bord complet
      </Link>
    </section>
  );
}
