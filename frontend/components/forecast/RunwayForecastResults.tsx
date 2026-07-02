import {
  SimpleTable,
  type SimpleTableRow,
} from "@/components/dashboard/SimpleTable";
import { formatMoney, formatMonth } from "@/lib/format";
import { noteLabel, riskClass, riskLabel, runwayLabel } from "@/lib/labels";
import type { RunwayForecastSummary } from "@/types/api";

export function RunwayForecastResults({
  summary,
}: {
  summary: RunwayForecastSummary;
}) {
  const selectedScenario =
    summary.scenarios.find((scenario) => scenario.key === "custom_drop") ??
    summary.scenarios[0];
  const firstCritical = selectedScenario.first_critical_month
    ? formatMonth(selectedScenario.first_critical_month)
    : "Aucun mois critique";
  const selectedRunway = runwayLabel(
    selectedScenario.runway_months,
    Boolean(selectedScenario.first_critical_month),
  );

  return (
    <section className="grid gap-6">
      {summary.data_quality_notes.length > 0 ? (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          {summary.data_quality_notes.map((note) => (
            <p key={note}>{noteLabel(note)}</p>
          ))}
        </div>
      ) : null}

      <article className="rounded-md border border-slate-200 bg-white p-5">
        <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          Reponse principale
        </p>
        <h2 className="mt-2 text-2xl font-semibold text-slate-950">
          Avec une baisse de CA de {selectedScenario.sales_drop_rate}%, vous
          tenez {selectedRunway}.
        </h2>
        <div className="mt-5 grid gap-4 md:grid-cols-3">
          <ForecastMetric label="Premier mois critique" value={firstCritical} plain />
          <ForecastMetric label="Cash fin periode" value={selectedScenario.ending_cash_estimate} />
          <ForecastMetric label="Risque" value={riskLabel(selectedScenario.risk_level)} plain />
        </div>
      </article>

      <article className="rounded-md border border-slate-200 bg-white">
        <div className="border-b border-slate-200 px-5 py-4">
          <h2 className="text-base font-semibold">Scenarios compares</h2>
        </div>
        <div className="grid gap-0 md:grid-cols-2 xl:grid-cols-5">
          {summary.scenarios.map((scenario) => (
            <div
              className="border-b border-slate-200 px-5 py-4 md:border-r xl:border-b-0"
              key={scenario.key}
            >
              <p className="font-semibold">{scenario.label}</p>
              <p className={`mt-1 text-sm font-semibold ${riskClass(scenario.risk_level)}`}>
                {riskLabel(scenario.risk_level)}
              </p>
              <dl className="mt-4 space-y-3 text-sm">
                <ForecastAssumption
                  label="Mois tenables"
                  plain
                  value={runwayLabel(
                    scenario.runway_months,
                    Boolean(scenario.first_critical_month),
                  )}
                />
                <ForecastAssumption label="Mois critique" value={scenario.first_critical_month ? formatMonth(scenario.first_critical_month) : "Aucun"} plain />
                <ForecastAssumption label="Cash final" value={scenario.ending_cash_estimate} />
              </dl>
            </div>
          ))}
        </div>
      </article>

      <div className="grid gap-6 lg:grid-cols-2">
        {selectedScenario.months.map((month) => {
          const rows: SimpleTableRow[] = [
            {
              label: "Cash de depart",
              value: formatMoney(month.opening_cash),
            },
            {
              label: "CA HT",
              value: formatMoney(month.forecast_sales_ht),
              emphasis: true,
            },
            {
              label: "Couts d exploitation HT",
              value: formatMoney(month.operating_costs_ht),
            },
            {
              label: "Salaires",
              value: formatMoney(month.salaries),
            },
            {
              label: "Charges sociales",
              value: formatMoney(month.social_charges),
            },
            {
              label: "EBE prevu",
              value: formatMoney(month.ebe_forecast),
              emphasis: true,
            },
            {
              label: "TVA a payer estimee",
              value: formatMoney(month.vat_payable_estimate),
            },
            {
              label: "Remboursements emprunts",
              value: formatMoney(month.loan_repayments_cash),
            },
            {
              label: "Cash fin de mois",
              value: formatMoney(month.ending_cash_estimate),
              emphasis: true,
            },
          ];
          return (
            <div key={month.month}>
              <SimpleTable
                rows={rows}
                title={`${formatMonth(month.month)} — ${selectedScenario.label}`}
              />
              <p
                className={`mt-2 text-right text-sm font-semibold ${riskClass(month.risk_level)}`}
              >
                Risque : {riskLabel(month.risk_level)}
              </p>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function ForecastMetric({
  label,
  plain = false,
  value,
}: {
  label: string;
  plain?: boolean;
  value: string;
}) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        {label}
      </p>
      <p className="mt-1 font-semibold">{plain ? value : formatMoney(value)}</p>
    </div>
  );
}

function ForecastAssumption({
  label,
  plain = false,
  value,
}: {
  label: string;
  plain?: boolean;
  value: string;
}) {
  return (
    <div className="flex justify-between gap-4">
      <dt className="text-slate-500">{label}</dt>
      <dd className="font-semibold text-slate-950">
        {plain || value.includes("%") ? value : formatMoney(value)}
      </dd>
    </div>
  );
}
