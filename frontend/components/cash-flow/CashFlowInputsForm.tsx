import { saveCashFlowInputsAction } from "@/app/actions";
import { FormFooter } from "@/components/forms/FormFooter";
import { MoneyInput } from "@/components/forms/MoneyInput";
import type { MonthlyCashFlowInputs } from "@/types/api";

export function CashFlowInputsForm({
  inputs,
  openingCash,
  period,
}: {
  inputs: MonthlyCashFlowInputs;
  openingCash: string;
  period: string;
}) {
  return (
    <form action={saveCashFlowInputsAction} className="rounded-md border border-slate-200 bg-white p-5">
      <h2 className="text-base font-semibold">Flux mensuels</h2>
      <p className="mt-1 text-sm text-slate-500">
        Montants non presents dans les factures validees.
      </p>
      <input name="return_to" type="hidden" value="/cash-flow" />
      <input name="period" type="hidden" value={period} />
      <input name="opening_cash" type="hidden" value={openingCash} />
      <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MoneyInput defaultValue={inputs.salaries} label="Salaires" name="salaries" />
        <MoneyInput defaultValue={inputs.social_charges} label="Charges sociales" name="social_charges" />
        <MoneyInput defaultValue={inputs.investments_cash} label="Investissements cash" name="investments_cash" />
        <MoneyInput defaultValue={inputs.loan_repayments_cash} label="Remboursements emprunts" name="loan_repayments_cash" />
      </div>
      <FormFooter label="Enregistrer les flux" />
    </form>
  );
}
