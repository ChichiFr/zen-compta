import {
  getMonthlyForecastSummary,
  getMonthlyPerformanceSummary,
} from "@/lib/api";
import { requireAuth } from "@/lib/session";
import {
  AppShell,
  ForecastForm,
  ForecastResults,
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

export default async function ForecastPage({
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
  const performance = await getMonthlyPerformanceSummary(periodStart);
  const forecast = await getMonthlyForecastSummary(periodStart, {
    opening_cash: openingCash,
    forecast_sales_ht: firstParam(
      params,
      "forecastSalesHt",
      performance.data?.performance.sales_ht ?? "0",
    ),
    fixed_salaries: firstParam(
      params,
      "fixedSalaries",
      performance.data?.inputs.salaries ?? "0",
    ),
    variable_salary_rate: firstParam(params, "variableSalaryRate", "0"),
    social_charge_rate: firstParam(params, "socialChargeRate", "35"),
    loan_repayments_cash: firstParam(
      params,
      "loanRepaymentsCash",
      performance.data?.inputs.loan_repayments_cash ?? "0",
    ),
  });

  return (
    <AppShell
      active="forecast"
      openingCash={openingCash}
      period={period}
      title="Prevision cash"
    >
      {message ? <StatusMessageBanner message={message} /> : null}

      {forecast.data ? (
        <>
          <ForecastForm
            assumptions={forecast.data.assumptions}
            period={period}
          />
          <ForecastResults summary={forecast.data} />
        </>
      ) : (
        <section className="rounded-md border border-amber-200 bg-amber-50 p-5 text-sm text-amber-900">
          Impossible de charger la prevision: {forecast.error}.
        </section>
      )}
    </AppShell>
  );
}
