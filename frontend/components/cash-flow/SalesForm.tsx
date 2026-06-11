import { saveSalesAction } from "@/app/actions";
import { FormFooter } from "@/components/forms/FormFooter";
import { MoneyInput } from "@/components/forms/MoneyInput";
import type { MonthlySales } from "@/types/api";

export function SalesForm({
  monthlySales,
  openingCash,
  period,
}: {
  monthlySales: MonthlySales | null;
  openingCash: string;
  period: string;
}) {
  return (
    <form action={saveSalesAction} className="rounded-md border border-slate-200 bg-white p-5">
      <h2 className="text-base font-semibold">Ventes mensuelles</h2>
      <input name="return_to" type="hidden" value="/cash-flow" />
      <input name="period" type="hidden" value={period} />
      <input name="opening_cash" type="hidden" value={openingCash} />
      <div className="mt-5 grid gap-4 sm:grid-cols-3">
        <MoneyInput defaultValue={monthlySales?.sales_ht ?? "0.00"} label="Ventes HT" name="sales_ht" />
        <MoneyInput defaultValue={monthlySales?.vat_collected ?? "0.00"} label="TVA collectee" name="vat_collected" />
        <MoneyInput defaultValue={monthlySales?.sales_ttc ?? "0.00"} label="Ventes TTC" name="sales_ttc" />
      </div>
      <FormFooter label="Enregistrer les ventes" />
    </form>
  );
}
