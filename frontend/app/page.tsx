import { redirect } from "next/navigation";

import {
  DashboardSummary,
  getDashboardSummary,
  getMonthlySales,
  saveMonthlySales,
} from "@/lib/api";

export const dynamic = "force-dynamic";

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

type Metric = {
  label: string;
  value: string;
  help: string;
};

function firstParam(
  params: Record<string, string | string[] | undefined>,
  key: string,
  fallback: string,
) {
  const value = params[key];
  if (Array.isArray(value)) {
    return value[0] ?? fallback;
  }
  return value ?? fallback;
}

function currentMonth() {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  return `${now.getFullYear()}-${month}`;
}

function monthToDate(value: string) {
  if (!/^\d{4}-\d{2}$/.test(value)) {
    return `${currentMonth()}-01`;
  }
  return `${value}-01`;
}

function formatMoney(value: string) {
  const amount = Number(value);
  if (!Number.isFinite(amount)) {
    return `${value} EUR`;
  }
  return new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "EUR",
  }).format(amount);
}

function messageText(value: string | null) {
  if (value === "saved") {
    return "Ventes mensuelles enregistrees.";
  }
  if (value === "invalid_sales") {
    return "Les ventes sont incoherentes: HT + TVA doit egaler TTC.";
  }
  if (value === "backend_unavailable") {
    return "Backend indisponible. Lance FastAPI puis recharge la page.";
  }
  if (value?.startsWith("api_error_")) {
    return "L API a refuse la demande. Verifie les montants saisis.";
  }
  return null;
}

async function saveSalesAction(formData: FormData) {
  "use server";

  const period = String(formData.get("period") ?? currentMonth());
  const openingCash = String(formData.get("opening_cash") ?? "0");
  const periodStart = monthToDate(period);
  const result = await saveMonthlySales(periodStart, {
    sales_ht: String(formData.get("sales_ht") ?? "0"),
    vat_collected: String(formData.get("vat_collected") ?? "0"),
    sales_ttc: String(formData.get("sales_ttc") ?? "0"),
  });

  const message = result.error ? result.error : "saved";
  redirect(
    `/?period=${encodeURIComponent(period)}&openingCash=${encodeURIComponent(
      openingCash,
    )}&message=${encodeURIComponent(message)}`,
  );
}

function MetricCard({ label, value, help }: Metric) {
  return (
    <article className="rounded-md border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-sm font-medium text-slate-500">{label}</p>
      <p className="mt-3 text-2xl font-semibold text-slate-950">{value}</p>
      <p className="mt-2 text-sm leading-5 text-slate-500">{help}</p>
    </article>
  );
}

function DashboardMetrics({ summary }: { summary: DashboardSummary }) {
  const metrics: Metric[] = [
    {
      label: "Factures a verifier",
      value: String(summary.invoices_to_review_count),
      help: "Brouillons et factures bloquees par une revue humaine.",
    },
    {
      label: "TVA a payer estimee",
      value: formatMoney(summary.vat_payable_estimate),
      help: "TVA collectee moins TVA deductible sur factures validees.",
    },
    {
      label: "Tresorerie estimee",
      value: formatMoney(summary.estimated_cash),
      help: "Tresorerie initiale + ventes TTC - depenses TTC - TVA estimee.",
    },
  ];

  return (
    <section className="grid gap-4 lg:grid-cols-3">
      {metrics.map((metric) => (
        <MetricCard key={metric.label} {...metric} />
      ))}
    </section>
  );
}

function DetailTable({ summary }: { summary: DashboardSummary }) {
  const rows = [
    ["Ventes HT", formatMoney(summary.sales_ht)],
    ["TVA collectee", formatMoney(summary.vat_collected)],
    ["Ventes TTC", formatMoney(summary.sales_ttc)],
    ["Factures validees HT", formatMoney(summary.validated_invoices_ht)],
    ["TVA deductible", formatMoney(summary.vat_deductible)],
    ["Factures validees TTC", formatMoney(summary.validated_invoices_ttc)],
  ];

  return (
    <section className="rounded-md border border-slate-200 bg-white">
      <div className="border-b border-slate-200 px-5 py-4">
        <h2 className="text-base font-semibold">Lecture comptable du mois</h2>
      </div>
      <dl className="grid gap-px bg-slate-200 sm:grid-cols-2 lg:grid-cols-3">
        {rows.map(([label, value]) => (
          <div className="bg-white p-5" key={label}>
            <dt className="text-sm font-medium text-slate-500">{label}</dt>
            <dd className="mt-2 text-lg font-semibold text-slate-950">{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

export default async function Home({
  searchParams,
}: {
  searchParams: SearchParams;
}) {
  const params = await searchParams;
  const period = firstParam(params, "period", currentMonth());
  const openingCash = firstParam(params, "openingCash", "0");
  const periodStart = monthToDate(period);
  const message = messageText(firstParam(params, "message", ""));
  const [dashboard, monthlySales] = await Promise.all([
    getDashboardSummary(periodStart, openingCash),
    getMonthlySales(periodStart),
  ]);

  return (
    <main className="min-h-screen bg-[#f6f7f4] text-slate-950">
      <section className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-5 py-6 sm:px-6 lg:px-8">
        <header className="flex flex-col justify-between gap-4 border-b border-slate-200 pb-5 lg:flex-row lg:items-end">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">
              Zen Compta
            </p>
            <h1 className="mt-2 text-3xl font-semibold">
              Dashboard TVA et tresorerie
            </h1>
          </div>
          <form className="flex flex-col gap-3 sm:flex-row" method="get">
            <label className="text-sm font-medium text-slate-600">
              Mois
              <input
                className="mt-1 block h-10 rounded-md border border-slate-300 bg-white px-3 text-slate-950"
                defaultValue={period}
                name="period"
                type="month"
              />
            </label>
            <label className="text-sm font-medium text-slate-600">
              Tresorerie depart
              <input
                className="mt-1 block h-10 rounded-md border border-slate-300 bg-white px-3 text-slate-950"
                defaultValue={openingCash}
                min="0"
                name="openingCash"
                step="0.01"
                type="number"
              />
            </label>
            <button className="h-10 self-end rounded-md bg-slate-950 px-4 text-sm font-semibold text-white">
              Actualiser
            </button>
          </form>
        </header>

        {message ? (
          <p className="rounded-md border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700">
            {message}
          </p>
        ) : null}

        {dashboard.data ? (
          <>
            <DashboardMetrics summary={dashboard.data} />
            <DetailTable summary={dashboard.data} />
          </>
        ) : (
          <section className="rounded-md border border-amber-200 bg-amber-50 p-5 text-sm text-amber-900">
            Impossible de charger le dashboard: {dashboard.error}.
          </section>
        )}

        <section className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_380px]">
          <form
            action={saveSalesAction}
            className="rounded-md border border-slate-200 bg-white p-5"
          >
            <div className="flex flex-col justify-between gap-2 border-b border-slate-200 pb-4 sm:flex-row">
              <div>
                <h2 className="text-base font-semibold">Ventes mensuelles</h2>
                <p className="mt-1 text-sm text-slate-500">
                  Saisie manuelle du chiffre d affaires du mois.
                </p>
              </div>
              <span className="text-sm font-medium text-slate-500">{period}</span>
            </div>
            <input name="period" type="hidden" value={period} />
            <input name="opening_cash" type="hidden" value={openingCash} />
            <div className="mt-5 grid gap-4 sm:grid-cols-3">
              <label className="text-sm font-medium text-slate-600">
                Ventes HT
                <input
                  className="mt-1 block h-10 w-full rounded-md border border-slate-300 px-3 text-slate-950"
                  defaultValue={monthlySales.data?.sales_ht ?? "0.00"}
                  min="0"
                  name="sales_ht"
                  required
                  step="0.01"
                  type="number"
                />
              </label>
              <label className="text-sm font-medium text-slate-600">
                TVA collectee
                <input
                  className="mt-1 block h-10 w-full rounded-md border border-slate-300 px-3 text-slate-950"
                  defaultValue={monthlySales.data?.vat_collected ?? "0.00"}
                  min="0"
                  name="vat_collected"
                  required
                  step="0.01"
                  type="number"
                />
              </label>
              <label className="text-sm font-medium text-slate-600">
                Ventes TTC
                <input
                  className="mt-1 block h-10 w-full rounded-md border border-slate-300 px-3 text-slate-950"
                  defaultValue={monthlySales.data?.sales_ttc ?? "0.00"}
                  min="0"
                  name="sales_ttc"
                  required
                  step="0.01"
                  type="number"
                />
              </label>
            </div>
            <div className="mt-5 flex justify-end">
              <button className="rounded-md bg-emerald-700 px-4 py-2 text-sm font-semibold text-white">
                Enregistrer les ventes
              </button>
            </div>
          </form>

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
                  {monthlySales.data ? "Oui" : "Non"}
                </dd>
              </div>
              <div>
                <dt className="font-medium text-slate-500">Banque connectee</dt>
                <dd className="mt-1 font-semibold text-slate-950">
                  {dashboard.data?.cash_is_bank_connected ? "Oui" : "Non"}
                </dd>
              </div>
            </dl>
          </aside>
        </section>
      </section>
    </main>
  );
}
