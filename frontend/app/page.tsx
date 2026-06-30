import { requireAuth } from "@/lib/session";
import { RestaurantDashboard } from "@/components/dashboard/RestaurantDashboard";
import { AppShell } from "@/components/layout/AppShell";
import {
  SearchParams,
  currentMonth,
  firstParam,
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

  return (
    <AppShell
      active="dashboard"
      openingCash={openingCash}
      period={period}
      title="Tableau de bord"
    >
      <RestaurantDashboard />
    </AppShell>
  );
}
