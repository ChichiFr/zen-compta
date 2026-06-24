import { requireAuth } from "@/lib/session";
import { RestaurantDashboard } from "@/components/dashboard/RestaurantDashboard";

export const dynamic = "force-dynamic";

export default async function Dashboard() {
  await requireAuth();

  return <RestaurantDashboard />;
}
