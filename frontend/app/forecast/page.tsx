import {
  getMonthlyPerformanceSummary,
  getRunwayForecastSummary,
} from "@/lib/api";
import { requireAuth } from "@/lib/session";
import {
  AppShell,
  RunwayForecastForm,
  RunwayForecastResults,
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

function hasDataGap(notes: string[] | undefined, note: string) {
  return notes?.includes(note) ?? true;
}

function defaultFromData(
  value: string | undefined,
  fallback: string,
  useFallback: boolean,
) {
  if (useFallback || value === undefined) {
    return fallback;
  }
  return value;
}

export default async function ForecastPage({
  searchParams,
}: {
  searchParams: SearchParams;
}) {
  await requireAuth();

  const params = await searchParams;
  const period = firstParam(params, "period", currentMonth());
  const openingCash = firstParam(params, "openingCash", "15000");
  const periodStart = monthToDate(period);
  const message = statusMessage(firstParam(params, "message", ""));
  const performance = await getMonthlyPerformanceSummary(periodStart);
  const notes = performance.data?.data_quality_notes;
  const salesMissing = hasDataGap(notes, "monthly_sales_missing");
  const cashFlowInputsMissing = hasDataGap(notes, "cash_flow_inputs_missing");
  const forecastParams = {
    months: firstParam(params, "months", "3"),
    referenceSalesHt: firstParam(
      params,
      "referenceSalesHt",
      defaultFromData(
        performance.data?.performance.sales_ht,
        "45000",
        salesMissing,
      ),
    ),
    customSalesDropRate: firstParam(params, "customSalesDropRate", "20"),
    fixedSalaries: firstParam(
      params,
      "fixedSalaries",
      defaultFromData(
        performance.data?.inputs.salaries,
        "12000",
        cashFlowInputsMissing,
      ),
    ),
    variableSalaryRate: firstParam(params, "variableSalaryRate", "0"),
    socialChargeRate: firstParam(params, "socialChargeRate", "35"),
    loanRepaymentsCash: firstParam(
      params,
      "loanRepaymentsCash",
      defaultFromData(
        performance.data?.inputs.loan_repayments_cash,
        "2500",
        cashFlowInputsMissing,
      ),
    ),
    monthlyVatPayableEstimate: firstParam(
      params,
      "monthlyVatPayableEstimate",
      defaultFromData(
        performance.data?.non_operating_cash_flow.vat_payable_estimate,
        "3000",
        salesMissing,
      ),
    ),
    minimumCashThreshold: firstParam(params, "minimumCashThreshold", "0"),
  };
  const forecast = await getRunwayForecastSummary(periodStart, {
    opening_cash: openingCash,
    months: forecastParams.months,
    reference_sales_ht: forecastParams.referenceSalesHt,
    custom_sales_drop_rate: forecastParams.customSalesDropRate,
    fixed_salaries: forecastParams.fixedSalaries,
    variable_salary_rate: forecastParams.variableSalaryRate,
    social_charge_rate: forecastParams.socialChargeRate,
    loan_repayments_cash: forecastParams.loanRepaymentsCash,
    monthly_vat_payable_estimate: forecastParams.monthlyVatPayableEstimate,
    minimum_cash_threshold: forecastParams.minimumCashThreshold,
  });

  return (
    <AppShell
      active="forecast"
      openingCash={openingCash}
      period={period}
      preservedQueryParams={forecastParams}
      title="Prevision cash"
    >
      {message ? <StatusMessageBanner message={message} /> : null}

      {forecast.data ? (
        <>
          <RunwayForecastForm
            assumptions={forecast.data.assumptions}
            period={period}
          />
          <RunwayForecastResults summary={forecast.data} />
        </>
      ) : (
        <section className="rounded-md border border-amber-200 bg-amber-50 p-5 text-sm text-amber-900">
          Impossible de charger la prevision: {forecast.error}.
        </section>
      )}
    </AppShell>
  );
}
