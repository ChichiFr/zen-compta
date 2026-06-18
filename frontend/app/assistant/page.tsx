import {
  getAssistantHealthBrief,
  getAssistantReviewSummary,
} from "@/lib/api";
import { requireAuth } from "@/lib/session";
import { AssistantDashboardCard } from "@/components/assistant/AssistantDashboardCard";
import { AssistantReviewCard } from "@/components/assistant/AssistantReviewCard";
import { AssistantUploadZone } from "@/components/assistant/AssistantUploadZone";
import { AppShell } from "@/components/layout/AppShell";
import {
  type SearchParams,
  currentMonth,
  firstParam,
  monthToDate,
} from "@/app/pageUtils";

export const dynamic = "force-dynamic";

export default async function AssistantPage({
  searchParams,
}: {
  searchParams: SearchParams;
}) {
  await requireAuth();

  const params = await searchParams;
  const period = firstParam(params, "period", currentMonth());
  const openingCash = firstParam(params, "openingCash", "0");
  const periodStart = monthToDate(period);

  const [reviewResult, healthResult] = await Promise.all([
    getAssistantReviewSummary(),
    getAssistantHealthBrief(periodStart, openingCash),
  ]);

  return (
    <AppShell
      active="assistant"
      openingCash={openingCash}
      period={period}
      title="Assistant"
    >
      <div className="space-y-8">
        <AssistantUploadZone openingCash={openingCash} period={period} />

        {reviewResult.data ? (
          <AssistantReviewCard
            count={reviewResult.data.count}
            invoices={reviewResult.data.invoices}
            openingCash={openingCash}
            period={period}
            summaryText={reviewResult.data.summary_text}
          />
        ) : null}

        {healthResult.data ? (
          <AssistantDashboardCard
            alerts={[]}
            riskLevel={healthResult.data.risk_level}
            summaryText={healthResult.data.text}
          />
        ) : null}
      </div>
    </AppShell>
  );
}
