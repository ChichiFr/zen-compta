import { FormFooter } from "@/components/forms/FormFooter";
import { MoneyInput } from "@/components/forms/MoneyInput";
import type { RunwayForecastSummary } from "@/types/api";

export function RunwayForecastForm({
  assumptions,
  period,
}: {
  assumptions: RunwayForecastSummary["assumptions"];
  period: string;
}) {
  return (
    <form className="rounded-md border border-slate-200 bg-white p-5" method="get">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-base font-semibold">Hypotheses de prevision</h2>
          <p className="mt-1 text-sm text-slate-500">
            Simulation basee sur vos hypotheses. L historique reel pourra etre
            utilise automatiquement quand il y aura assez de donnees.
          </p>
        </div>
      </div>
      <input name="period" type="hidden" value={period} />
      <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <MoneyInput defaultValue={assumptions.opening_cash} label="Cash de depart" name="openingCash" />
        <label className="text-sm font-medium text-slate-600">
          Duree
          <select
            className="mt-1 block h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-slate-950"
            defaultValue={assumptions.months}
            name="months"
          >
            <option value="3">3 mois</option>
            <option value="6">6 mois</option>
            <option value="12">12 mois</option>
          </select>
        </label>
        <MoneyInput defaultValue={assumptions.reference_sales_ht} label="CA mensuel de reference HT" name="referenceSalesHt" />
        <MoneyInput
          defaultValue={assumptions.custom_sales_drop_rate}
          label="Baisse CA personnalisee %"
          max="100"
          name="customSalesDropRate"
        />
        <MoneyInput defaultValue={assumptions.fixed_salaries} label="Salaires fixes" name="fixedSalaries" />
        <MoneyInput defaultValue={assumptions.variable_salary_rate} label="% salaires variables" name="variableSalaryRate" />
        <MoneyInput defaultValue={assumptions.social_charge_rate} label="% charges sociales" name="socialChargeRate" />
        <MoneyInput defaultValue={assumptions.loan_repayments_cash} label="Emprunts mensuels" name="loanRepaymentsCash" />
        <MoneyInput
          defaultValue={assumptions.monthly_vat_payable_estimate}
          label="TVA estimee au CA de reference"
          name="monthlyVatPayableEstimate"
        />
        <MoneyInput defaultValue={assumptions.minimum_cash_threshold} label="Seuil cash critique" name="minimumCashThreshold" />
      </div>
      <FormFooter label="Simuler" />
    </form>
  );
}
