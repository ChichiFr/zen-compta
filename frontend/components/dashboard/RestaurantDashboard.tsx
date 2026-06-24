"use client";

import { AreaChart, BarChart } from "@tremor/react";
import {
  ArrowUpRight,
  CheckCircle2,
  Minus,
  MoreHorizontal,
} from "lucide-react";

import { Avatar } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

const monthlySales = [
  { month: "Jul", "Annee N-1": 5800, "Annee en cours": 7200 },
  { month: "Aou", "Annee N-1": 6400, "Annee en cours": 8300 },
  { month: "Sep", "Annee N-1": 7100, "Annee en cours": 9100 },
  { month: "Oct", "Annee N-1": 7050, "Annee en cours": 8600 },
  { month: "Nov", "Annee N-1": 7800, "Annee en cours": 9400 },
  { month: "Dec", "Annee N-1": 9300, "Annee en cours": 11200 },
  { month: "Jan", "Annee N-1": 8200, "Annee en cours": 9800 },
  { month: "Fev", "Annee N-1": 8400, "Annee en cours": 10100 },
  { month: "Mar", "Annee N-1": 9100, "Annee en cours": 10900 },
  { month: "Avr", "Annee N-1": 9600, "Annee en cours": 11600 },
  { month: "Mai", "Annee N-1": 10000, "Annee en cours": 12100 },
  { month: "Jun", "Annee N-1": 10400, "Annee en cours": 12450 },
];

const monthlyPurchases = [
  { month: "Jul", "Annee N-1": 2800, "Annee en cours": 3100 },
  { month: "Aou", "Annee N-1": 3050, "Annee en cours": 3380 },
  { month: "Sep", "Annee N-1": 3210, "Annee en cours": 3520 },
  { month: "Oct", "Annee N-1": 3180, "Annee en cours": 3440 },
  { month: "Nov", "Annee N-1": 3360, "Annee en cours": 3710 },
  { month: "Dec", "Annee N-1": 3900, "Annee en cours": 4260 },
  { month: "Jan", "Annee N-1": 3550, "Annee en cours": 3890 },
  { month: "Fev", "Annee N-1": 3700, "Annee en cours": 4020 },
  { month: "Mar", "Annee N-1": 3820, "Annee en cours": 4150 },
  { month: "Avr", "Annee N-1": 3760, "Annee en cours": 4070 },
  { month: "Mai", "Annee N-1": 3870, "Annee en cours": 4210 },
  { month: "Jun", "Annee N-1": 3950, "Annee en cours": 4280 },
];

const balanceEvolution = Array.from({ length: 30 }, (_, index) => {
  const day = String(index + 1).padStart(2, "0");
  const drift = index * 52;
  const wave = Math.round(Math.sin(index / 3) * 420);
  return {
    day,
    Solde: 6900 + drift + wave,
  };
});

const periodOptions = ["Mois courant", "Mois precedent", "Annee"];

const kpis = [
  {
    indicator: "up",
    label: "Marge brute",
    tone: "text-emerald-600",
    value: "66%",
  },
  {
    indicator: "up",
    label: "EBE Cash",
    tone: "text-emerald-600",
    value: "5 870 EUR",
  },
  {
    indicator: "neutral",
    label: "Tresorerie fin de mois",
    tone: "text-slate-500",
    value: "9 240 EUR",
  },
  {
    indicator: "ok",
    label: "Premier mois critique",
    tone: "text-emerald-600",
    value: "Aucun",
  },
] as const;

export function RestaurantDashboard() {
  return (
    <main className="min-h-screen bg-[#f8f9fa] text-slate-950">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-8 px-4 py-6 sm:px-6 lg:px-8">
        <header className="flex flex-col gap-5 border-b border-slate-200 pb-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="min-w-0">
            <p className="text-sm font-semibold text-slate-500">Zen Compta</p>
            <h1 className="mt-1 text-3xl font-semibold tracking-normal text-slate-950">
              Tableau de bord
            </h1>
          </div>

          <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
            <div className="flex rounded-lg border border-slate-200 bg-white p-1 shadow-sm">
              {periodOptions.map((option, index) => (
                <button
                  className={cn(
                    "h-9 rounded-md px-3 text-sm font-medium text-slate-600 transition-colors",
                    index === 0
                      ? "bg-slate-950 text-white shadow-sm"
                      : "hover:bg-slate-50 hover:text-slate-950",
                  )}
                  key={option}
                  type="button"
                >
                  {option}
                </button>
              ))}
            </div>
            <Avatar>MR</Avatar>
          </div>
        </header>

        <section className="grid auto-rows-fr gap-6 lg:grid-cols-2">
          <MetricCard
            action="Saisir mes ventes"
            chart={
              <BarChart
                categories={["Annee N-1", "Annee en cours"]}
                className="h-44"
                colors={["slate", "emerald"]}
                data={monthlySales}
                index="month"
                showAnimation
                showGridLines={false}
                showLegend={true}
                showXAxis={true}
                showYAxis={false}
                yAxisWidth={0}
              />
            }
            pill="+12% vs juin 2025"
            pillTone="bg-emerald-50 text-emerald-700 ring-emerald-200"
            subtitle="Total ventes HT du mois"
            title="Ventes"
            titleTone="text-emerald-600"
            value="12 450 EUR"
          />

          <MetricCard
            action="Importer une facture"
            chart={
              <BarChart
                categories={["Annee N-1", "Annee en cours"]}
                className="h-44"
                colors={["slate", "rose"]}
                data={monthlyPurchases}
                index="month"
                showAnimation
                showGridLines={false}
                showLegend={true}
                showXAxis={true}
                showYAxis={false}
                yAxisWidth={0}
              />
            }
            pill="+8% vs juin 2025"
            pillTone="bg-rose-50 text-rose-700 ring-rose-200"
            sideStats={[
              { label: "3 a valider" },
              { label: "1 en retard" },
            ]}
            subtitle="Total achats HT valides"
            title="Achats"
            titleTone="text-rose-600"
            value="4 280 EUR"
          />

          <MetricCard
            action="Voir les transactions"
            chart={
              <AreaChart
                categories={["Solde"]}
                className="h-36"
                colors={["sky"]}
                data={balanceEvolution}
                index="day"
                showAnimation
                showGridLines={false}
                showLegend={false}
                showXAxis={false}
                showYAxis={false}
                yAxisWidth={0}
              />
            }
            pill="+1 240 EUR depuis le 1er juin"
            pillTone="bg-sky-50 text-sky-700 ring-sky-200"
            sideStats={[{ label: "12 transactions a categoriser" }]}
            subtitle="Solde estime"
            title="Banque"
            titleTone="text-sky-600"
            value="8 320 EUR"
          />

          <KpiCard />
        </section>
      </div>
    </main>
  );
}

function MetricCard({
  action,
  chart,
  pill,
  pillTone,
  sideStats = [],
  subtitle,
  title,
  titleTone,
  value,
}: {
  action: string;
  chart: React.ReactNode;
  pill: string;
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
        <button
          aria-label={`Menu ${title}`}
          className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-slate-50 hover:text-slate-700"
          type="button"
        >
          <MoreHorizontal className="size-5" />
        </button>
      </div>

      <div className="mt-7 grid gap-4 sm:grid-cols-[minmax(0,1fr)_150px]">
        <div>
          <p className="font-sans text-4xl font-bold tabular-nums tracking-normal text-slate-950">
            {value}
          </p>
          <span
            className={cn(
              "mt-3 inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ring-1",
              pillTone,
            )}
          >
            {pill}
          </span>
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
        <Button>{action}</Button>
      </div>
    </Card>
  );
}

function KpiCard() {
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
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700 ring-1 ring-emerald-200">
            Sante: OK
          </span>
          <button
            aria-label="Menu Chiffres cles"
            className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-slate-50 hover:text-slate-700"
            type="button"
          >
            <MoreHorizontal className="size-5" />
          </button>
        </div>
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
            <TrendIcon indicator={kpi.indicator} tone={kpi.tone} />
          </div>
        ))}
      </div>

      <div className="mt-6">
        <Button>Voir la prevision complete</Button>
      </div>
    </Card>
  );
}

function TrendIcon({
  indicator,
  tone,
}: {
  indicator: "neutral" | "ok" | "up";
  tone: string;
}) {
  if (indicator === "ok") {
    return <CheckCircle2 className={cn("size-5", tone)} />;
  }
  if (indicator === "neutral") {
    return <Minus className={cn("size-5", tone)} />;
  }
  return <ArrowUpRight className={cn("size-5", tone)} />;
}
