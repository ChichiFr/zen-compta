import { createInvoiceAction } from "@/app/actions";
import { FormFooter } from "@/components/forms/FormFooter";
import {
  InvoiceHeaderFields,
  InvoiceLineFields,
} from "@/components/invoices/InvoiceFields";

export function InvoiceForm({
  openingCash,
  period,
}: {
  openingCash: string;
  period: string;
}) {
  return (
    <details className="rounded-md border border-slate-200 bg-white">
      <summary className="cursor-pointer px-5 py-4 text-base font-semibold">
        Creer une facture manuellement
      </summary>
      <form action={createInvoiceAction} className="border-t border-slate-200 p-5">
        <input name="return_to" type="hidden" value="/invoices" />
        <input name="period" type="hidden" value={period} />
        <input name="opening_cash" type="hidden" value={openingCash} />
        <InvoiceHeaderFields />
        <InvoiceLineFields collapseOptional />
        <FormFooter label="Creer la facture" />
      </form>
    </details>
  );
}
