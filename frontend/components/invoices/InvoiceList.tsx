import {
  archiveInvoiceAction,
  updateInvoiceAction,
  validateInvoiceAction,
} from "@/app/actions";
import { FormFooter } from "@/components/forms/FormFooter";
import {
  InvoiceHeaderFields,
  InvoiceLineFields,
} from "@/components/invoices/InvoiceFields";
import {
  InvoiceReviewPanel,
  LineReviewMessages,
  hasVisibleValidationBlocker,
} from "@/components/invoices/InvoiceReview";
import { formatMoney } from "@/lib/format";
import { invoiceCategoryLabel } from "@/lib/invoiceCategories";
import type { Invoice } from "@/types/api";

export function InvoiceList({
  csvExportUrl,
  emptyText,
  invoices,
  openingCash,
  period,
  title,
  xlsxExportUrl,
}: {
  csvExportUrl?: string;
  emptyText: string;
  invoices: Invoice[];
  openingCash: string;
  period: string;
  title: string;
  xlsxExportUrl?: string;
}) {
  return (
    <section className="rounded-md border border-slate-200 bg-white">
      <div className="flex flex-col justify-between gap-3 border-b border-slate-200 px-5 py-4 sm:flex-row sm:items-center">
        <h2 className="text-base font-semibold">{title}</h2>
        {csvExportUrl && xlsxExportUrl ? (
          <div className="flex flex-wrap gap-2">
            <a className="rounded-md border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-900" href={csvExportUrl}>
              Export CSV
            </a>
            <a className="rounded-md border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-900" href={xlsxExportUrl}>
              Export Excel
            </a>
          </div>
        ) : null}
      </div>
      <div className="divide-y divide-slate-200">
        {invoices.length === 0 ? (
          <p className="px-5 py-4 text-sm text-slate-500">{emptyText}</p>
        ) : (
          invoices.map((invoice) => (
            <InvoiceCard
              invoice={invoice}
              key={invoice.id}
              openingCash={openingCash}
              period={period}
            />
          ))
        )}
      </div>
    </section>
  );
}

function InvoiceCard({
  invoice,
  openingCash,
  period,
}: {
  invoice: Invoice;
  openingCash: string;
  period: string;
}) {
  return (
    <article className="px-5 py-4">
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_120px_120px_120px_120px_auto]">
        <div>
          <p className="font-semibold text-slate-950">{invoice.supplier_name}</p>
          <p className="mt-1 text-sm text-slate-500">
            {invoice.invoice_date ?? "Date manquante"}
            {invoice.invoice_number ? ` - ${invoice.invoice_number}` : ""}
          </p>
        </div>
        <InvoiceAmount label="Statut" value={statusLabel(invoice.status)} />
        <InvoiceAmount label="HT" value={formatMoney(invoice.total_ht)} />
        <InvoiceAmount label="TVA" value={formatMoney(invoice.total_tva)} />
        <InvoiceAmount label="TTC" value={formatMoney(invoice.total_ttc)} />
        <InvoiceActions
          invoice={invoice}
          openingCash={openingCash}
          period={period}
        />
      </div>
      {invoice.source === "ai_upload" && invoice.status !== "validated" ? (
        <p className="mt-2 text-xs font-semibold text-amber-700">Hors exports</p>
      ) : null}
      <InvoiceReviewPanel invoice={invoice} />
      <InvoiceLinesTable invoice={invoice} />
      {invoice.status !== "validated" ? (
        <InvoiceEditForm
          invoice={invoice}
          openingCash={openingCash}
          period={period}
        />
      ) : null}
    </article>
  );
}

function InvoiceAmount({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-sm text-slate-500">{label}</p>
      <p className="mt-1 font-semibold">{value}</p>
    </div>
  );
}

function InvoiceActions({
  invoice,
  openingCash,
  period,
}: {
  invoice: Invoice;
  openingCash: string;
  period: string;
}) {
  return (
    <div className="flex flex-wrap items-start gap-2 lg:justify-end">
      {invoice.status === "validated" ? (
        <span className="rounded-md bg-emerald-50 px-3 py-2 text-sm font-semibold text-emerald-800">
          Validee
        </span>
      ) : hasVisibleValidationBlocker(invoice) ? (
        <span className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-900">
          A corriger
        </span>
      ) : (
        <form action={validateInvoiceAction}>
          <InvoiceHiddenFields openingCash={openingCash} period={period} />
          <input name="invoice_id" type="hidden" value={invoice.id} />
          <button className="rounded-md bg-emerald-700 px-3 py-2 text-sm font-semibold text-white">
            Valider
          </button>
        </form>
      )}
      {invoice.status !== "validated" ? (
        <form action={archiveInvoiceAction}>
          <InvoiceHiddenFields openingCash={openingCash} period={period} />
          <input name="invoice_id" type="hidden" value={invoice.id} />
          <button className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-900">
            Archiver
          </button>
        </form>
      ) : null}
    </div>
  );
}

function InvoiceHiddenFields({
  openingCash,
  period,
}: {
  openingCash: string;
  period: string;
}) {
  return (
    <>
      <input name="return_to" type="hidden" value="/invoices" />
      <input name="period" type="hidden" value={period} />
      <input name="opening_cash" type="hidden" value={openingCash} />
    </>
  );
}

function InvoiceLinesTable({ invoice }: { invoice: Invoice }) {
  return (
    <div className="mt-4 overflow-x-auto rounded-md border border-slate-200">
      <div className="min-w-[720px]">
        <div className="grid grid-cols-[minmax(0,1fr)_180px_90px_110px_110px_110px] bg-slate-50 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
          <span>Ligne</span>
          <span>Categorie</span>
          <span>TVA</span>
          <span>HT</span>
          <span>TVA EUR</span>
          <span>TTC</span>
        </div>
        <div className="divide-y divide-slate-200">
          {invoice.lines.map((line) => (
            <div
              className="grid grid-cols-[minmax(0,1fr)_180px_90px_110px_110px_110px] gap-0 px-3 py-3 text-sm"
              key={line.id}
            >
              <div>
                <p className="font-medium text-slate-900">{line.description}</p>
                <LineReviewMessages reason={line.needs_review_reason} />
              </div>
              <span className="text-slate-600">
                {invoiceCategoryLabel(line.category)}
              </span>
              <span className="text-slate-600">{line.vat_rate}%</span>
              <span className="font-medium">{formatMoney(line.amount_ht)}</span>
              <span className="font-medium">{formatMoney(line.amount_tva)}</span>
              <span className="font-medium">{formatMoney(line.amount_ttc)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function InvoiceEditForm({
  invoice,
  openingCash,
  period,
}: {
  invoice: Invoice;
  openingCash: string;
  period: string;
}) {
  return (
    <details className="mt-4 rounded-md border border-slate-200 bg-slate-50" open={invoice.source === "ai_upload"}>
      <summary className="cursor-pointer px-4 py-3 text-sm font-semibold">
        Modifier cette facture
      </summary>
      <form action={updateInvoiceAction} className="border-t border-slate-200 p-4">
        <InvoiceHiddenFields openingCash={openingCash} period={period} />
        <input name="invoice_id" type="hidden" value={invoice.id} />
        <InvoiceHeaderFields invoice={invoice} />
        <InvoiceLineFields invoice={invoice} />
        <FormFooter label="Enregistrer les corrections" />
      </form>
    </details>
  );
}

function statusLabel(status: Invoice["status"]) {
  if (status === "validated") {
    return "Validee";
  }
  if (status === "needs_review") {
    return "A revoir";
  }
  if (status === "archived") {
    return "Archivee";
  }
  return "Brouillon";
}
