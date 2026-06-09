import {
  dashboardCsvExportUrl,
  dashboardXlsxExportUrl,
  getDashboardSummary,
  getMonthlyPerformanceSummary,
  getMonthlySales,
} from "@/lib/api";
import { requireAuth } from "@/lib/session";
import {
  ApiErrorNotice,
  AppShell,
  CashFlowInputsForm,
  DataStatus,
  DetailTable,
  PerformanceAndCashFlowTables,
  SalesForm,
  StatusMessageBanner,
} from "@/app/ui";
import {
  SearchParams,
  currentMonth,
  firstParam,
  monthToDate,
  statusMessage,
} from "@/app/pageUtils";

export const dynamic = "force-dynamic";

export default async function CashFlowPage({
  searchParams,
}: {
  searchParams: SearchParams;
}) {
  await requireAuth();

  const params = await searchParams;
  const period = firstParam(params, "period", currentMonth());
  const openingCash = firstParam(params, "openingCash", "0");
  const periodStart = monthToDate(period);
  const message = statusMessage(firstParam(params, "message", ""));
  const [dashboard, performance, monthlySales] = await Promise.all([
    getDashboardSummary(periodStart, openingCash),
    getMonthlyPerformanceSummary(periodStart),
    getMonthlySales(periodStart),
  ]);

  return (
    <AppShell
      active="cash-flow"
      openingCash={openingCash}
      period={period}
      title="Cash-flow reel"
    >
      {message ? <StatusMessageBanner message={message} /> : null}

      {dashboard.data ? (
        <>
          <div className="flex flex-wrap justify-end gap-2">
            <a
              className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-900 shadow-sm"
              href={dashboardCsvExportUrl(periodStart, openingCash)}
            >
              Exporter CSV
            </a>
            <a
              className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-900 shadow-sm"
              href={dashboardXlsxExportUrl(periodStart, openingCash)}
            >
              Exporter Excel
            </a>
          </div>
          <DetailTable summary={dashboard.data} />
        </>
      ) : (
        <section className="rounded-md border border-amber-200 bg-amber-50 p-5 text-sm text-amber-900">
          Impossible de charger le dashboard: {dashboard.error}.
        </section>
      )}

      {performance.data ? (
        <>
          <PerformanceAndCashFlowTables summary={performance.data} />
          <CashFlowInputsForm
            inputs={performance.data.inputs}
            openingCash={openingCash}
            period={period}
          />
        </>
      ) : (
        <section className="rounded-md border border-amber-200 bg-amber-50 p-5 text-sm text-amber-900">
          Impossible de charger la performance: {performance.error}.
        </section>
      )}

      <section className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_380px]">
        <ApiErrorNotice error={monthlySales.error} label="les ventes mensuelles" />
        <SalesForm
          monthlySales={monthlySales.data}
          openingCash={openingCash}
          period={period}
        />
        <DataStatus
          dashboard={dashboard.data}
          monthlySales={monthlySales.data}
          periodStart={periodStart}
        />
      </section>
    </AppShell>
  );
}
