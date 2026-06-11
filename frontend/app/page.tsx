import {
  getDashboardSummary,
  getMonthlyForecastSummary,
  getMonthlyPerformanceSummary,
} from "@/lib/api";
import { requireAuth } from "@/lib/session";
import { DashboardActions } from "@/components/dashboard/DashboardActions";
import { DashboardHealth } from "@/components/dashboard/DashboardHealth";
import { DashboardMetrics } from "@/components/dashboard/DashboardMetrics";
import { PerformanceAndCashFlowTables } from "@/components/dashboard/PerformanceAndCashFlowTables";
import { AppShell } from "@/components/layout/AppShell";
import { StatusMessageBanner } from "@/components/layout/StatusMessageBanner";
import {
  SearchParams,
  currentMonth,
  firstParam,
  monthToDate,
  statusMessage,
} from "@/app/pageUtils";

export const dynamic = "force-dynamic";

export default async function Dashboard({
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

  const [dashboard, performance] = await Promise.all([
    getDashboardSummary(periodStart, openingCash),
    getMonthlyPerformanceSummary(periodStart),
  ]);
  const forecast = await getMonthlyForecastSummary(periodStart, {
    opening_cash: openingCash,
    forecast_sales_ht: dashboard.data?.sales_ht ?? "0",
    fixed_salaries: performance.data?.inputs.salaries ?? "0",
    variable_salary_rate: "0",
    social_charge_rate: "35",
    loan_repayments_cash:
      performance.data?.inputs.loan_repayments_cash ?? "0",
  });

  return (
    <AppShell
      active="dashboard"
      openingCash={openingCash}
      period={period}
      title="Tableau de bord"
    >
      {message ? <StatusMessageBanner message={message} /> : null}

      {dashboard.data ? (
        <>
          <DashboardMetrics
            dashboard={dashboard.data}
            forecast={forecast.data}
            performance={performance.data}
          />
          <DashboardHealth
            dashboard={dashboard.data}
            forecast={forecast.data}
            performance={performance.data}
          />
        </>
      ) : (
        <section className="rounded-md border border-amber-200 bg-amber-50 p-5 text-sm text-amber-900">
          Impossible de charger le dashboard: {dashboard.error}.
        </section>
      )}

      {performance.data ? (
        <PerformanceAndCashFlowTables compact summary={performance.data} />
      ) : (
        <section className="rounded-md border border-amber-200 bg-amber-50 p-5 text-sm text-amber-900">
          Impossible de charger la performance: {performance.error}.
        </section>
      )}

      <DashboardActions openingCash={openingCash} period={period} />
    </AppShell>
  );
}
