"use client";

import Link from "next/link";
import { AreaChart, BarChart } from "@tremor/react";
import {
  ArrowDownRight,
  ArrowUpRight,
  CheckCircle2,
  Minus,
} from "lucide-react";

import { buttonVariants } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type {
  DashboardSummary,
  HomeDashboardSummary,
  MonthlyPerformanceSummary,
} from "@/types/api";

const MONTH_LABELS = [
  "Jan",
  "Fev",
  "Mar",
  "Avr",
  "Mai",
  "Jun",
  "Jul",
  "Aou",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
] as const;

const FULL_MONTH_LABELS = [
  "janvier",
  "fevrier",
  "mars",
  "avril",
  "mai",
  "juin",
  "juillet",
  "aout",
  "septembre",
  "octobre",
  "novembre",
  "decembre",
] as const;

type Props = {
  dashboard: DashboardSummary | null;
  home: HomeDashboardSummary | null;
  openingCash: string;
  performance: MonthlyPerformanceSummary | null;
  period: string;
};

export function RestaurantDashboard({
  dashboard,
  home,
  openingCash,
  performance,
  period,
}: Props) {
  const navSuffix = `period=${period}&openingCash=${openingCash}`;

  if (!home) {
    return (
      <div className="rounded-md border border-rose-300 bg-rose-50 px-4 py-3 text-sm text-rose-900">
        <p className="font-semibold">Donnees indisponibles</p>
        <p className="mt-1">
          Impossible de charger le tableau de bord. Verifie que le backend
          est lance, puis recharge la page.
        </p>
      </div>
    );
  }

  const series = home.monthly_series;
  const latest = series[series.length - 1] ?? null;
  const hasSalesHistory = series.some((point) => Number(point.sales_ht) > 0);
  const hasPurchasesHistory = series.some(
    (point) => Number(point.purchases_ht) > 0,
  );
  const hasAnyData =
    hasSalesHistory || hasPurchasesHistory || home.bank_connected;

  const salesChart = buildChartData(series, "sales_ht", "sales_prior_ht");
  const purchasesChart = buildChartData(
    series,
    "purchases_ht",
    "purchases_prior_ht",
  );
  const bankChart = home.bank_flow.map((point) => ({
    day: formatShortDate(point.day),
    "Flux net": Number(point.cumulative_flow),
  }));

  return (
    <div className="flex flex-col gap-8">
      {!hasAnyData ? <OnboardingNotice navSuffix={navSuffix} /> : null}

      <section className="grid auto-rows-fr gap-6 lg:grid-cols-2">
        <MetricCard
          actionHref={`/cash-flow?${navSuffix}`}
          actionLabel="Saisir mes ventes"
          chart={
            hasSalesHistory ? (
              <BarChart
                categories={salesChart.categories}
                className="h-44"
                colors={salesChart.categories.length === 2
                  ? ["slate", "emerald"]
                  : ["emerald"]}
                data={salesChart.rows}
                index="month"
                showAnimation
                showGridLines={false}
                showLegend={salesChart.categories.length === 2}
                showXAxis={true}
                showYAxis={false}
                yAxisWidth={0}
              />
            ) : (
              <EmptyChart message="Aucune vente saisie pour l'instant." />
            )
          }
          pill={yoyPill(latest?.sales_ht, latest?.sales_prior_ht, period)}
          pillTone="bg-emerald-50 text-emerald-700 ring-emerald-200"
          subtitle="Total ventes HT du mois"
          title="Ventes"
          titleTone="text-emerald-600"
          value={formatEur(latest?.sales_ht)}
        />

        <MetricCard
          actionHref={`/invoices?${navSuffix}`}
          actionLabel="Importer une facture"
          chart={
            hasPurchasesHistory ? (
              <BarChart
                categories={purchasesChart.categories}
                className="h-44"
                colors={purchasesChart.categories.length === 2
                  ? ["slate", "rose"]
                  : ["rose"]}
                data={purchasesChart.rows}
                index="month"
                showAnimation
                showGridLines={false}
                showLegend={purchasesChart.categories.length === 2}
                showXAxis={true}
                showYAxis={false}
                yAxisWidth={0}
              />
            ) : (
              <EmptyChart message="Aucune facture validee pour l'instant." />
            )
          }
          pill={yoyPill(latest?.purchases_ht, latest?.purchases_prior_ht, period)}
          pillTone="bg-rose-50 text-rose-700 ring-rose-200"
          sideStats={
            dashboard && dashboard.invoices_to_review_count > 0
              ? [
                  {
                    label: `${dashboard.invoices_to_review_count} a valider`,
                  },
                ]
              : []
          }
          subtitle="Total achats HT valides"
          title="Achats"
          titleTone="text-rose-600"
          value={formatEur(latest?.purchases_ht)}
        />

        <MetricCard
          actionHref={`/bank?${navSuffix}`}
          actionLabel={
            home.bank_connected ? "Voir les transactions" : "Connecter ma banque"
          }
          chart={
            home.bank_connected && bankChart.length > 0 ? (
              <AreaChart
                categories={["Flux net"]}
                className="h-36"
                colors={["sky"]}
                data={bankChart}
                index="day"
                showAnimation
                showGridLines={false}
                showLegend={false}
                showXAxis={false}
                showYAxis={false}
                yAxisWidth={0}
              />
            ) : (
              <EmptyChart
                message={
                  home.bank_connected
                    ? "Aucune transaction sur les 30 derniers jours."
                    : "Connectez votre banque pour suivre vos mouvements."
                }
              />
            )
          }
          pill={home.bank_connected ? "Flux net sur 30 jours" : "Non connectee"}
          pillTone="bg-sky-50 text-sky-700 ring-sky-200"
          sideStats={
            home.unpaid_invoices_count > 0
              ? [
                  {
                    label: `${home.unpaid_invoices_count} facture${
                      home.unpaid_invoices_count > 1 ? "s" : ""
                    } sans paiement`,
                  },
                ]
              : []
          }
          subtitle="Mouvements bancaires"
          title="Banque"
          titleTone="text-sky-600"
          value={home.bank_connected ? formatEur(home.bank_net_flow) : "-"}
        />

        <KpiCard
          dashboard={dashboard}
          navSuffix={navSuffix}
          performance={performance}
        />
      </section>
    </div>
  );
}

function OnboardingNotice({ navSuffix }: { navSuffix: string }) {
  return (
    <div className="rounded-md border border-sky-300 bg-sky-50 px-4 py-3 text-sm text-sky-900">
      <p className="font-semibold">Bienvenue sur Zen Compta</p>
      <p className="mt-1">
        Commencez par{" "}
        <Link className="font-semibold underline" href={`/cash-flow?${navSuffix}`}>
          saisir vos ventes du mois
        </Link>{" "}
        ou{" "}
        <Link className="font-semibold underline" href={`/invoices?${navSuffix}`}>
          importer une premiere facture
        </Link>
        . Vos chiffres apparaitront ici automatiquement.
      </p>
    </div>
  );
}

function EmptyChart({ message }: { message: string }) {
  return (
    <div className="flex h-36 items-center justify-center rounded-lg border border-dashed border-slate-200 bg-slate-50 px-4 text-center text-sm text-slate-500">
      {message}
    </div>
  );
}

function buildChartData(
  series: HomeDashboardSummary["monthly_series"],
  currentKey: "purchases_ht" | "sales_ht",
  priorKey: "purchases_prior_ht" | "sales_prior_ht",
) {
  const hasPrior = series.some((point) => point[priorKey] !== null);
  const rows = series.map((point) => {
    const row: Record<string, number | string> = {
      month: monthLabel(point.month),
      "Annee en cours": Number(point[currentKey]),
    };
    if (hasPrior) {
      row["Annee N-1"] = Number(point[priorKey] ?? 0);
    }
    return row;
  });
  const categories = hasPrior
    ? ["Annee N-1", "Annee en cours"]
    : ["Annee en cours"];
  return { categories, rows };
}

function formatShortDate(dateText: string) {
  const [, month, day] = dateText.split("-");
  if (!month || !day) {
    return dateText;
  }
  return `${day}/${month}`;
}

function monthLabel(monthDate: string) {
  const month = Number(monthDate.split("-")[1] ?? "0");
  return MONTH_LABELS[month - 1] ?? monthDate;
}

function formatEur(value: string | null | undefined) {
  if (value === null || value === undefined) {
    return "-";
  }
  return new Intl.NumberFormat("fr-FR", {
    currency: "EUR",
    maximumFractionDigits: 0,
    style: "currency",
  }).format(Number(value));
}

function yoyPill(
  current: string | null | undefined,
  prior: string | null | undefined,
  period: string,
) {
  if (!current || !prior || Number(prior) === 0) {
    return null;
  }
  const rate = (Number(current) / Number(prior) - 1) * 100;
  const rounded = Math.round(rate);
  const month = Number(period.split("-")[1] ?? "0");
  const year = Number(period.split("-")[0] ?? "0") - 1;
  const label = FULL_MONTH_LABELS[month - 1] ?? "";
  return `${rounded >= 0 ? "+" : ""}${rounded}% vs ${label} ${year}`;
}

function MetricCard({
  actionHref,
  actionLabel,
  chart,
  pill,
  pillTone,
  sideStats = [],
  subtitle,
  title,
  titleTone,
  value,
}: {
  actionHref: string;
  actionLabel: string;
  chart: React.ReactNode;
  pill: string | null;
  pillTone: string;
  sideStats?: Array<{ label: string }>;
  subtitle: string;
  title: string;
  titleTone: string;
  value: string;
}) {
  return (
    <Card className="flex h-full min-h-[420px] flex-col p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className={cn("text-lg font-semibold", titleTone)}>{title}</h2>
          <p className="mt-1 text-sm text-slate-500">{subtitle}</p>
        </div>
      </div>

      <div className="mt-7 grid gap-4 sm:grid-cols-[minmax(0,1fr)_150px]">
        <div>
          <p className="font-sans text-4xl font-bold tabular-nums tracking-normal text-slate-950">
            {value}
          </p>
          {pill ? (
            <span
              className={cn(
                "mt-3 inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ring-1",
                pillTone,
              )}
            >
              {pill}
            </span>
          ) : null}
        </div>
        {sideStats.length > 0 ? (
          <div className="flex flex-col gap-3 sm:items-end">
            {sideStats.map((stat) => (
              <div
                className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-700"
                key={stat.label}
              >
                {stat.label}
              </div>
            ))}
          </div>
        ) : null}
      </div>

      <div className="mt-6 flex-1">{chart}</div>

      <div className="mt-6">
        <Link className={buttonVariants()} href={actionHref}>
          {actionLabel}
        </Link>
      </div>
    </Card>
  );
}

function KpiCard({
  dashboard,
  navSuffix,
  performance,
}: {
  dashboard: DashboardSummary | null;
  navSuffix: string;
  performance: MonthlyPerformanceSummary | null;
}) {
  const salesHt = performance ? Number(performance.performance.sales_ht) : 0;
  const grossMargin =
    performance && salesHt > 0
      ? Math.round(
          ((salesHt -
            Number(performance.performance.raw_materials_ht) -
            Number(performance.performance.packaging_ht)) /
            salesHt) *
            100,
        )
      : null;
  const ebeCash = performance
    ? Number(performance.performance.ebe_cash)
    : null;
  const estimatedCash = dashboard ? Number(dashboard.estimated_cash) : null;
  const toReview = dashboard ? dashboard.invoices_to_review_count : null;
  const healthy = estimatedCash === null || estimatedCash >= 0;

  const kpis = [
    {
      indicator: trendIndicator(grossMargin),
      label: "Marge brute",
      value: grossMargin === null ? "-" : `${grossMargin}%`,
    },
    {
      indicator: trendIndicator(ebeCash),
      label: "EBE Cash",
      value: ebeCash === null ? "-" : formatEur(String(ebeCash)),
    },
    {
      indicator: trendIndicator(estimatedCash),
      label: "Tresorerie fin de mois",
      value:
        estimatedCash === null ? "-" : formatEur(String(estimatedCash)),
    },
    {
      indicator: toReview === 0 ? ("ok" as const) : ("neutral" as const),
      label: "Factures a valider",
      value: toReview === null ? "-" : String(toReview),
    },
  ];

  return (
    <Card className="flex h-full min-h-[420px] flex-col p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-amber-600">
            Chiffres cles
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Indicateurs du mois courant
          </p>
        </div>
        <span
          className={cn(
            "rounded-full px-3 py-1 text-xs font-semibold ring-1",
            healthy
              ? "bg-emerald-50 text-emerald-700 ring-emerald-200"
              : "bg-rose-50 text-rose-700 ring-rose-200",
          )}
        >
          {healthy ? "Sante: OK" : "Sante: attention"}
        </span>
      </div>

      <div className="mt-8 flex flex-1 flex-col divide-y divide-slate-100">
        {kpis.map((kpi) => (
          <div
            className="grid grid-cols-[minmax(0,1fr)_auto_auto] items-center gap-4 py-4"
            key={kpi.label}
          >
            <p className="text-sm font-medium text-slate-600">{kpi.label}</p>
            <p className="font-sans text-lg font-semibold tabular-nums text-slate-950">
              {kpi.value}
            </p>
            <TrendIcon indicator={kpi.indicator} />
          </div>
        ))}
      </div>

      <div className="mt-6">
        <Link className={buttonVariants()} href={`/forecast?${navSuffix}`}>
          Voir la prevision complete
        </Link>
      </div>
    </Card>
  );
}

function trendIndicator(value: number | null): "down" | "neutral" | "up" {
  if (value === null || value === 0) {
    return "neutral";
  }
  return value > 0 ? "up" : "down";
}

function TrendIcon({
  indicator,
}: {
  indicator: "down" | "neutral" | "ok" | "up";
}) {
  if (indicator === "ok") {
    return <CheckCircle2 className="size-5 text-emerald-600" />;
  }
  if (indicator === "neutral") {
    return <Minus className="size-5 text-slate-500" />;
  }
  if (indicator === "down") {
    return <ArrowDownRight className="size-5 text-rose-600" />;
  }
  return <ArrowUpRight className="size-5 text-emerald-600" />;
}
