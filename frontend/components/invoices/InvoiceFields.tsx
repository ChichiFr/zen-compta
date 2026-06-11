import { MoneyInput } from "@/components/forms/MoneyInput";
import { INVOICE_CATEGORIES } from "@/lib/invoiceCategories";
import type { Invoice } from "@/types/api";

export const INVOICE_FORM_LINE_NUMBERS = [1, 2, 3, 4, 5] as const;

export function InvoiceHeaderFields({ invoice }: { invoice?: Invoice }) {
  return (
    <div className="mt-5 grid gap-4 md:grid-cols-3">
      <label className="text-sm font-medium text-slate-600">
        Fournisseur
        <input
          className="mt-1 block h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-slate-950"
          defaultValue={invoice?.supplier_name ?? ""}
          name="supplier_name"
          required
          type="text"
        />
      </label>
      <label className="text-sm font-medium text-slate-600">
        Date
        <input
          className="mt-1 block h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-slate-950"
          defaultValue={invoice?.invoice_date ?? ""}
          name="invoice_date"
          required
          type="date"
        />
      </label>
      <label className="text-sm font-medium text-slate-600">
        Numero
        <input
          className="mt-1 block h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-slate-950"
          defaultValue={invoice?.invoice_number ?? ""}
          name="invoice_number"
          type="text"
        />
      </label>
    </div>
  );
}

export function InvoiceLineFields({
  collapseOptional = false,
  invoice,
}: {
  collapseOptional?: boolean;
  invoice?: Invoice;
}) {
  const renderLine = (lineNumber: (typeof INVOICE_FORM_LINE_NUMBERS)[number]) => {
    const line = invoice?.lines[lineNumber - 1];
    return (
      <div
        className="mt-4 grid gap-4 border-t border-slate-200 pt-4 md:grid-cols-[minmax(0,1fr)_220px_140px_140px]"
        key={lineNumber}
      >
        <label className="text-sm font-medium text-slate-600">
          Ligne {lineNumber}
          <input
            className="mt-1 block h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-slate-950"
            defaultValue={line?.description ?? ""}
            name={`line_${lineNumber}_description`}
            required={lineNumber === 1}
            type="text"
          />
        </label>
        <label className="text-sm font-medium text-slate-600">
          Categorie
          <CategorySelect
            defaultValue={line?.category}
            name={`line_${lineNumber}_category`}
          />
        </label>
        <MoneyInput
          defaultValue={line?.vat_rate ?? (lineNumber === 1 ? "20" : "")}
          label="TVA %"
          name={`line_${lineNumber}_vat_rate`}
          required={lineNumber === 1}
        />
        <MoneyInput
          defaultValue={line?.amount_ht ?? ""}
          label="Montant HT"
          name={`line_${lineNumber}_amount_ht`}
          required={lineNumber === 1}
        />
      </div>
    );
  };

  if (!collapseOptional) {
    return <>{INVOICE_FORM_LINE_NUMBERS.map(renderLine)}</>;
  }

  return (
    <>
      {renderLine(1)}
      <details className="mt-4 rounded-md border border-slate-200 bg-slate-50">
        <summary className="cursor-pointer px-4 py-3 text-sm font-semibold text-slate-800">
          Ajouter des lignes supplementaires
        </summary>
        <div className="border-t border-slate-200 px-4 pb-4">
          {INVOICE_FORM_LINE_NUMBERS.slice(1).map(renderLine)}
        </div>
      </details>
    </>
  );
}

function CategorySelect({
  defaultValue,
  name,
}: {
  defaultValue?: string | null;
  name: string;
}) {
  return (
    <select
      className="mt-1 block h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-slate-950"
      defaultValue={defaultValue ?? ""}
      name={name}
    >
      <option value="">A categoriser</option>
      {INVOICE_CATEGORIES.map(([code, label]) => (
        <option key={code} value={code}>
          {label}
        </option>
      ))}
    </select>
  );
}
