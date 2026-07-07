import { requireAuth } from "@/lib/session";
import {
  getDashboardSummary,
  getHomeDashboard,
  getMonthlyPerformanceSummary,
} from "@/lib/api";
import { RestaurantDashboard } from "@/components/dashboard/RestaurantDashboard";
import { ApiErrorNotice } from "@/components/layout/ApiErrorNotice";
import { AppShell } from "@/components/layout/AppShell";
import {
  SearchParams,
  currentMonth,
  firstParam,
  monthToDate,
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

  const [homeResult, dashboardResult, performanceResult] = await Promise.all([
    getHomeDashboard(periodStart),
    getDashboardSummary(periodStart, openingCash),
    getMonthlyPerformanceSummary(periodStart),
  ]);

  return (
    <AppShell
      active="dashboard"
      openingCash={openingCash}
      period={period}
      title="Tableau de bord"
    >
      <ApiErrorNotice error={homeResult.error} label="le tableau de bord" />
      <RestaurantDashboard
        dashboard={dashboardResult.data}
        home={homeResult.data}
        openingCash={openingCash}
        performance={performanceResult.data}
        period={period}
      />
    </AppShell>
  );
}
