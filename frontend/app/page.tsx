import { redirect } from "next/navigation";

import {
  DashboardSummary,
  Invoice,
  InvoiceLineInput,
  archiveInvoice,
  createInvoice,
  dashboardCsvExportUrl,
  dashboardXlsxExportUrl,
  getDashboardSummary,
  getInvoices,
  getInvoicesToReviewWithoutDate,
  getMonthlySales,
  invoiceCsvExportUrl,
  invoiceXlsxExportUrl,
  saveMonthlySales,
  updateInvoice,
  uploadDocumentImport,
  validateInvoice,
} from "@/lib/api";
import { clearSession, requireAuth } from "@/lib/session";
import { DocumentFileInput } from "@/components/DocumentFileInput";

export const dynamic = "force-dynamic";

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

type Metric = {
  label: string;
  value: string;
  help: string;
};

type InvoiceLineFormResult = InvoiceLineInput | "incomplete" | null;

const INVOICE_FORM_LINE_NUMBERS = [1, 2, 3, 4, 5] as const;

function firstParam(
  params: Record<string, string | string[] | undefined>,
  key: string,
  fallback: string,
) {
  const value = params[key];
  if (Array.isArray(value)) {
    return value[0] ?? fallback;
  }
  return value ?? fallback;
}

function currentMonth() {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  return `${now.getFullYear()}-${month}`;
}

function monthToDate(value: string) {
  if (!/^\d{4}-\d{2}$/.test(value)) {
    return `${currentMonth()}-01`;
  }
  return `${value}-01`;
}

function formatMoney(value: string) {
  const amount = Number(value);
  if (!Number.isFinite(amount)) {
    return `${value} EUR`;
  }
  return new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "EUR",
  }).format(amount);
}

function messageText(value: string | null) {
  if (value === "saved") {
    return "Ventes mensuelles enregistrees.";
  }
  if (value === "invoice_created") {
    return "Facture creee. Elle doit encore etre validee humainement.";
  }
  if (value === "document_uploaded") {
    return "Document importe. Une facture a verifier a ete creee.";
  }
  if (value === "document_uploaded_to_inbox") {
    return "Document importe. La facture est dans Factures importees a traiter.";
  }
  if (value === "document_upload_missing") {
    return "Choisis un PDF ou une image de facture a importer.";
  }
  if (value === "document_upload_failed") {
    return "Import impossible. Verifie le fichier, puis reessaie.";
  }
  if (value === "invoice_validated") {
    return "Facture validee.";
  }
  if (value === "invoice_updated") {
    return "Facture modifiee.";
  }
  if (value === "invoice_archived") {
    return "Facture archivee.";
  }
  if (value === "invoice_validation_failed") {
    return "La facture ne peut pas encore etre validee.";
  }
  if (value === "invoice_missing_line") {
    return "Ajoute au moins une ligne de facture.";
  }
  if (value === "invoice_incomplete_line") {
    return "Complete chaque ligne commencee: description, TVA et montant HT.";
  }
  if (value === "invalid_sales") {
    return "Les ventes sont incoherentes: HT + TVA doit egaler TTC.";
  }
  if (value === "backend_unavailable") {
    return "Backend indisponible. Lance FastAPI puis recharge la page.";
  }
  if (value?.startsWith("api_error_")) {
    return "L API a refuse la demande. Verifie les montants saisis.";
  }
  return null;
}

function redirectToDashboard(
  period: string,
  openingCash: string,
  message: string,
): never {
  redirect(
    `/?period=${encodeURIComponent(period)}&openingCash=${encodeURIComponent(
      openingCash,
    )}&message=${encodeURIComponent(message)}`,
  );
}

function invoiceLineFromForm(
  formData: FormData,
  index: number,
): InvoiceLineFormResult {
  const description = String(formData.get(`line_${index}_description`) ?? "").trim();
  const amountHt = String(formData.get(`line_${index}_amount_ht`) ?? "").trim();
  const category = String(formData.get(`line_${index}_category`) ?? "").trim();
  const vatRate = String(formData.get(`line_${index}_vat_rate`) ?? "").trim();
  if (!description && !amountHt && !category && !vatRate) {
    return null;
  }

  if (!description || !amountHt || !vatRate) {
    return "incomplete";
  }

  return {
    description,
    category: category || undefined,
    vat_rate: vatRate,
    amount_ht: amountHt,
  };
}

async function saveSalesAction(formData: FormData) {
  "use server";

  const period = String(formData.get("period") ?? currentMonth());
  const openingCash = String(formData.get("opening_cash") ?? "0");
  const periodStart = monthToDate(period);
  const result = await saveMonthlySales(periodStart, {
    sales_ht: String(formData.get("sales_ht") ?? "0"),
    vat_collected: String(formData.get("vat_collected") ?? "0"),
    sales_ttc: String(formData.get("sales_ttc") ?? "0"),
  });

  const message = result.error ? result.error : "saved";
  redirectToDashboard(period, openingCash, message);
}

async function createInvoiceAction(formData: FormData) {
  "use server";

  const period = String(formData.get("period") ?? currentMonth());
  const openingCash = String(formData.get("opening_cash") ?? "0");
  const lineResults = INVOICE_FORM_LINE_NUMBERS.map((lineNumber) =>
    invoiceLineFromForm(formData, lineNumber),
  );
  if (lineResults.includes("incomplete")) {
    redirectToDashboard(period, openingCash, "invoice_incomplete_line");
  }
  const lines = lineResults.filter(
    (line): line is InvoiceLineInput => line !== null && line !== "incomplete",
  );

  if (lines.length === 0) {
    redirectToDashboard(period, openingCash, "invoice_missing_line");
  }

  const result = await createInvoice({
    supplier_name: String(formData.get("supplier_name") ?? "").trim(),
    invoice_date: String(formData.get("invoice_date") ?? "") || undefined,
    invoice_number: String(formData.get("invoice_number") ?? "").trim() || undefined,
    lines,
  });

  redirectToDashboard(
    period,
    openingCash,
    result.error ? result.error : "invoice_created",
  );
}

async function uploadDocumentAction(formData: FormData) {
  "use server";

  await requireAuth();

  const period = String(formData.get("period") ?? currentMonth());
  const openingCash = String(formData.get("opening_cash") ?? "0");
  const file = formData.get("invoice_file");
  if (!(file instanceof File) || file.size === 0) {
    redirectToDashboard(period, openingCash, "document_upload_missing");
  }

  const result = await uploadDocumentImport(file);
  redirectToDashboard(
    period,
    openingCash,
    result.error ? "document_upload_failed" : "document_uploaded_to_inbox",
  );
}

async function validateInvoiceAction(formData: FormData) {
  "use server";

  const period = String(formData.get("period") ?? currentMonth());
  const openingCash = String(formData.get("opening_cash") ?? "0");
  const invoiceId = String(formData.get("invoice_id") ?? "");
  const result = await validateInvoice(invoiceId);

  redirectToDashboard(
    period,
    openingCash,
    result.error ? "invoice_validation_failed" : "invoice_validated",
  );
}

async function updateInvoiceAction(formData: FormData) {
  "use server";

  const period = String(formData.get("period") ?? currentMonth());
  const openingCash = String(formData.get("opening_cash") ?? "0");
  const invoiceId = String(formData.get("invoice_id") ?? "");
  const lineResults = INVOICE_FORM_LINE_NUMBERS.map((lineNumber) =>
    invoiceLineFromForm(formData, lineNumber),
  );
  if (lineResults.includes("incomplete")) {
    redirectToDashboard(period, openingCash, "invoice_incomplete_line");
  }
  const lines = lineResults.filter(
    (line): line is InvoiceLineInput => line !== null && line !== "incomplete",
  );

  if (lines.length === 0) {
    redirectToDashboard(period, openingCash, "invoice_missing_line");
  }

  const result = await updateInvoice(invoiceId, {
    supplier_name: String(formData.get("supplier_name") ?? "").trim(),
    invoice_date: String(formData.get("invoice_date") ?? "") || undefined,
    invoice_number: String(formData.get("invoice_number") ?? "").trim() || undefined,
    lines,
  });

  redirectToDashboard(
    period,
    openingCash,
    result.error ? result.error : "invoice_updated",
  );
}

async function archiveInvoiceAction(formData: FormData) {
  "use server";

  const period = String(formData.get("period") ?? currentMonth());
  const openingCash = String(formData.get("opening_cash") ?? "0");
  const invoiceId = String(formData.get("invoice_id") ?? "");
  const result = await archiveInvoice(invoiceId);

  redirectToDashboard(
    period,
    openingCash,
    result.error ? result.error : "invoice_archived",
  );
}

async function logoutAction() {
  "use server";

  await clearSession();
  redirect("/login");
}

function MetricCard({ label, value, help }: Metric) {
  return (
    <article className="rounded-md border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-sm font-medium text-slate-500">{label}</p>
      <p className="mt-3 text-2xl font-semibold text-slate-950">{value}</p>
      <p className="mt-2 text-sm leading-5 text-slate-500">{help}</p>
    </article>
  );
}

function DashboardMetrics({ summary }: { summary: DashboardSummary }) {
  const metrics: Metric[] = [
    {
      label: "Factures a verifier",
      value: String(summary.invoices_to_review_count),
      help: "Brouillons et factures bloquees par une revue humaine.",
    },
    {
      label: "TVA a payer estimee",
      value: formatMoney(summary.vat_payable_estimate),
      help: "TVA collectee moins TVA deductible sur factures validees.",
    },
    {
      label: "Tresorerie estimee",
      value: formatMoney(summary.estimated_cash),
      help: "Tresorerie initiale + ventes TTC - depenses TTC - TVA estimee.",
    },
  ];

  return (
    <section className="grid gap-4 lg:grid-cols-3">
      {metrics.map((metric) => (
        <MetricCard key={metric.label} {...metric} />
      ))}
    </section>
  );
}

function DetailTable({ summary }: { summary: DashboardSummary }) {
  const rows = [
    ["Ventes HT", formatMoney(summary.sales_ht)],
    ["TVA collectee", formatMoney(summary.vat_collected)],
    ["Ventes TTC", formatMoney(summary.sales_ttc)],
    ["Factures validees HT", formatMoney(summary.validated_invoices_ht)],
    ["TVA deductible", formatMoney(summary.vat_deductible)],
    ["Factures validees TTC", formatMoney(summary.validated_invoices_ttc)],
  ];

  return (
    <section className="rounded-md border border-slate-200 bg-white">
      <div className="border-b border-slate-200 px-5 py-4">
        <h2 className="text-base font-semibold">Lecture comptable du mois</h2>
      </div>
      <dl className="grid gap-px bg-slate-200 sm:grid-cols-2 lg:grid-cols-3">
        {rows.map(([label, value]) => (
          <div className="bg-white p-5" key={label}>
            <dt className="text-sm font-medium text-slate-500">{label}</dt>
            <dd className="mt-2 text-lg font-semibold text-slate-950">{value}</dd>
          </div>
        ))}
      </dl>
    </section>
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

function InvoiceForm({
  period,
  openingCash,
}: {
  period: string;
  openingCash: string;
}) {
  return (
    <form
      action={createInvoiceAction}
      className="rounded-md border border-slate-200 bg-white p-5"
    >
      <div className="border-b border-slate-200 pb-4">
        <h2 className="text-base font-semibold">Nouvelle facture</h2>
        <p className="mt-1 text-sm text-slate-500">
          Saisie manuelle avec TVA calculee par ligne, jusqu a 5 lignes.
        </p>
      </div>
      <input name="period" type="hidden" value={period} />
      <input name="opening_cash" type="hidden" value={openingCash} />
      <div className="mt-5 grid gap-4 md:grid-cols-3">
        <label className="text-sm font-medium text-slate-600">
          Fournisseur
          <input
            className="mt-1 block h-10 w-full rounded-md border border-slate-300 px-3 text-slate-950"
            name="supplier_name"
            required
            type="text"
          />
        </label>
        <label className="text-sm font-medium text-slate-600">
          Date facture
          <input
            className="mt-1 block h-10 w-full rounded-md border border-slate-300 px-3 text-slate-950"
            name="invoice_date"
            required
            type="date"
          />
        </label>
        <label className="text-sm font-medium text-slate-600">
          Numero
          <input
            className="mt-1 block h-10 w-full rounded-md border border-slate-300 px-3 text-slate-950"
            name="invoice_number"
            type="text"
          />
        </label>
      </div>
      {INVOICE_FORM_LINE_NUMBERS.map((lineNumber) => (
        <div
          className="mt-5 grid gap-4 border-t border-slate-100 pt-5 md:grid-cols-[minmax(0,1fr)_120px_140px_140px]"
          key={lineNumber}
        >
          <label className="text-sm font-medium text-slate-600">
            Ligne {lineNumber}
            <input
              className="mt-1 block h-10 w-full rounded-md border border-slate-300 px-3 text-slate-950"
              name={`line_${lineNumber}_description`}
              placeholder="Achats marchandises"
              required={lineNumber === 1}
              type="text"
            />
          </label>
          <label className="text-sm font-medium text-slate-600">
            Categorie
            <input
              className="mt-1 block h-10 w-full rounded-md border border-slate-300 px-3 text-slate-950"
              name={`line_${lineNumber}_category`}
              placeholder="601"
              type="text"
            />
          </label>
          <label className="text-sm font-medium text-slate-600">
            TVA %
            <input
              className="mt-1 block h-10 w-full rounded-md border border-slate-300 px-3 text-slate-950"
              defaultValue={lineNumber === 1 ? "20" : ""}
              max="100"
              min="0"
              name={`line_${lineNumber}_vat_rate`}
              required={lineNumber === 1}
              step="0.01"
              type="number"
            />
          </label>
          <label className="text-sm font-medium text-slate-600">
            Montant HT
            <input
              className="mt-1 block h-10 w-full rounded-md border border-slate-300 px-3 text-slate-950"
              min="0"
              name={`line_${lineNumber}_amount_ht`}
              required={lineNumber === 1}
              step="0.01"
              type="number"
            />
          </label>
        </div>
      ))}
      <div className="mt-5 flex justify-end">
        <button className="rounded-md bg-slate-950 px-4 py-2 text-sm font-semibold text-white">
          Creer la facture
        </button>
      </div>
    </form>
  );
}

function DocumentUploadForm({
  period,
  openingCash,
}: {
  period: string;
  openingCash: string;
}) {
  return (
    <form
      action={uploadDocumentAction}
      className="rounded-md border border-slate-200 bg-white p-5"
    >
      <div className="border-b border-slate-200 pb-4">
        <h2 className="text-base font-semibold">Uploader une facture</h2>
        <p className="mt-1 text-sm text-slate-500">
          PDF ou image stocke localement. La facture reste a verifier.
        </p>
      </div>
      <input name="period" type="hidden" value={period} />
      <input name="opening_cash" type="hidden" value={openingCash} />
      <div className="mt-5 flex flex-col gap-4 sm:flex-row sm:items-end">
        <div className="text-sm font-medium text-slate-600 sm:flex-1">
          <p>Fichier facture</p>
          <DocumentFileInput />
        </div>
        <button className="h-10 rounded-md bg-slate-950 px-4 text-sm font-semibold text-white">
          Importer
        </button>
      </div>
    </form>
  );
}

function InvoiceEditForm({
  invoice,
  period,
  openingCash,
}: {
  invoice: Invoice;
  period: string;
  openingCash: string;
}) {
  return (
    <details className="mt-4 rounded-md border border-slate-200 bg-slate-50">
      <summary className="cursor-pointer px-4 py-3 text-sm font-semibold text-slate-900">
        Modifier cette facture
      </summary>
      <form action={updateInvoiceAction} className="border-t border-slate-200 p-4">
        <input name="period" type="hidden" value={period} />
        <input name="opening_cash" type="hidden" value={openingCash} />
        <input name="invoice_id" type="hidden" value={invoice.id} />
        <div className="grid gap-4 md:grid-cols-3">
          <label className="text-sm font-medium text-slate-600">
            Fournisseur
            <input
              className="mt-1 block h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-slate-950"
              defaultValue={invoice.supplier_name}
              name="supplier_name"
              required
              type="text"
            />
          </label>
          <label className="text-sm font-medium text-slate-600">
            Date facture
            <input
              className="mt-1 block h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-slate-950"
              defaultValue={invoice.invoice_date ?? ""}
              name="invoice_date"
              required
              type="date"
            />
          </label>
          <label className="text-sm font-medium text-slate-600">
            Numero
            <input
              className="mt-1 block h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-slate-950"
              defaultValue={invoice.invoice_number ?? ""}
              name="invoice_number"
              type="text"
            />
          </label>
        </div>
        {INVOICE_FORM_LINE_NUMBERS.map((lineNumber) => {
          const line = invoice.lines[lineNumber - 1];
          return (
            <div
              className="mt-4 grid gap-4 border-t border-slate-200 pt-4 md:grid-cols-[minmax(0,1fr)_120px_140px_140px]"
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
                <input
                  className="mt-1 block h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-slate-950"
                  defaultValue={line?.category ?? ""}
                  name={`line_${lineNumber}_category`}
                  type="text"
                />
              </label>
              <label className="text-sm font-medium text-slate-600">
                TVA %
                <input
                  className="mt-1 block h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-slate-950"
                  defaultValue={line?.vat_rate ?? (lineNumber === 1 ? "20" : "")}
                  max="100"
                  min="0"
                  name={`line_${lineNumber}_vat_rate`}
                  required={lineNumber === 1}
                  step="0.01"
                  type="number"
                />
              </label>
              <label className="text-sm font-medium text-slate-600">
                Montant HT
                <input
                  className="mt-1 block h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-slate-950"
                  defaultValue={line?.amount_ht ?? ""}
                  min="0"
                  name={`line_${lineNumber}_amount_ht`}
                  required={lineNumber === 1}
                  step="0.01"
                  type="number"
                />
              </label>
            </div>
          );
        })}
        <div className="mt-4 flex justify-end">
          <button className="rounded-md bg-slate-950 px-4 py-2 text-sm font-semibold text-white">
            Enregistrer les corrections
          </button>
        </div>
      </form>
    </details>
  );
}

function InvoiceList({
  title,
  emptyText,
  invoices,
  csvExportUrl,
  xlsxExportUrl,
  period,
  openingCash,
}: {
  title: string;
  emptyText: string;
  invoices: Invoice[];
  csvExportUrl?: string;
  xlsxExportUrl?: string;
  period: string;
  openingCash: string;
}) {
  return (
    <section className="rounded-md border border-slate-200 bg-white">
      <div className="flex flex-col justify-between gap-3 border-b border-slate-200 px-5 py-4 sm:flex-row sm:items-center">
        <h2 className="text-base font-semibold">{title}</h2>
        {csvExportUrl && xlsxExportUrl ? (
          <div className="flex flex-wrap gap-2">
            <a
              className="rounded-md border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-900"
              href={csvExportUrl}
            >
              Export factures CSV
            </a>
            <a
              className="rounded-md border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-900"
              href={xlsxExportUrl}
            >
              Export factures Excel
            </a>
          </div>
        ) : null}
      </div>
      <div className="divide-y divide-slate-200">
        {invoices.length === 0 ? (
          <p className="px-5 py-4 text-sm text-slate-500">
            {emptyText}
          </p>
        ) : (
          invoices.slice(0, 8).map((invoice) => (
            <article
              className="px-5 py-4"
              key={invoice.id}
            >
              <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_120px_120px_120px_120px_auto]">
                <div>
                  <p className="font-semibold text-slate-950">
                    {invoice.supplier_name}
                  </p>
                  <p className="mt-1 text-sm text-slate-500">
                    {invoice.invoice_date ?? "Date manquante"}
                    {invoice.invoice_number ? ` - ${invoice.invoice_number}` : ""}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-slate-500">Statut</p>
                  <p className="mt-1 font-semibold">
                    {statusLabel(invoice.status)}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-slate-500">HT</p>
                  <p className="mt-1 font-semibold">
                    {formatMoney(invoice.total_ht)}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-slate-500">TVA</p>
                  <p className="mt-1 font-semibold">
                    {formatMoney(invoice.total_tva)}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-slate-500">TTC</p>
                  <p className="mt-1 font-semibold">
                    {formatMoney(invoice.total_ttc)}
                  </p>
                </div>
                <div className="flex flex-wrap items-start gap-2 lg:justify-end">
                  {invoice.status === "validated" ? (
                    <span className="rounded-md bg-emerald-50 px-3 py-2 text-sm font-semibold text-emerald-800">
                      Validee
                    </span>
                  ) : (
                    <form action={validateInvoiceAction}>
                      <input name="period" type="hidden" value={period} />
                      <input
                        name="opening_cash"
                        type="hidden"
                        value={openingCash}
                      />
                      <input name="invoice_id" type="hidden" value={invoice.id} />
                      <button className="rounded-md bg-emerald-700 px-3 py-2 text-sm font-semibold text-white">
                        Valider
                      </button>
                    </form>
                  )}
                  {invoice.status !== "validated" ? (
                    <form action={archiveInvoiceAction}>
                      <input name="period" type="hidden" value={period} />
                      <input
                        name="opening_cash"
                        type="hidden"
                        value={openingCash}
                      />
                      <input name="invoice_id" type="hidden" value={invoice.id} />
                      <button className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-900">
                        Archiver
                      </button>
                    </form>
                  ) : null}
                </div>
              </div>
              <div className="mt-4 overflow-x-auto rounded-md border border-slate-200">
                <div className="min-w-[720px]">
                  <div className="grid grid-cols-[minmax(0,1fr)_90px_90px_110px_110px_110px] bg-slate-50 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
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
                        className="grid grid-cols-[minmax(0,1fr)_90px_90px_110px_110px_110px] gap-0 px-3 py-3 text-sm"
                        key={line.id}
                      >
                        <div>
                          <p className="font-medium text-slate-900">
                            {line.description}
                          </p>
                          {line.needs_review_reason ? (
                            <p className="mt-1 text-xs font-medium text-amber-700">
                              Revue: {line.needs_review_reason}
                            </p>
                          ) : null}
                        </div>
                        <span className="text-slate-600">
                          {line.category ?? "-"}
                        </span>
                        <span className="text-slate-600">{line.vat_rate}%</span>
                        <span className="font-medium">
                          {formatMoney(line.amount_ht)}
                        </span>
                        <span className="font-medium">
                          {formatMoney(line.amount_tva)}
                        </span>
                        <span className="font-medium">
                          {formatMoney(line.amount_ttc)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
              {invoice.status !== "validated" ? (
                <InvoiceEditForm
                  invoice={invoice}
                  period={period}
                  openingCash={openingCash}
                />
              ) : null}
            </article>
          ))
        )}
      </div>
    </section>
  );
}

export default async function Home({
  searchParams,
}: {
  searchParams: SearchParams;
}) {
  await requireAuth();

  const params = await searchParams;
  const period = firstParam(params, "period", currentMonth());
  const openingCash = firstParam(params, "openingCash", "0");
  const periodStart = monthToDate(period);
  const message = messageText(firstParam(params, "message", ""));
  const csvExportUrl = dashboardCsvExportUrl(periodStart, openingCash);
  const xlsxExportUrl = dashboardXlsxExportUrl(periodStart, openingCash);
  const invoiceCsvUrl = invoiceCsvExportUrl(periodStart);
  const invoiceXlsxUrl = invoiceXlsxExportUrl(periodStart);
  const [dashboard, monthlySales, invoices, reviewInboxInvoices] = await Promise.all([
    getDashboardSummary(periodStart, openingCash),
    getMonthlySales(periodStart),
    getInvoices(periodStart),
    getInvoicesToReviewWithoutDate(),
  ]);

  return (
    <main className="min-h-screen bg-[#f6f7f4] text-slate-950">
      <section className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-5 py-6 sm:px-6 lg:px-8">
        <header className="flex flex-col justify-between gap-4 border-b border-slate-200 pb-5 lg:flex-row lg:items-end">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">
              Zen Compta
            </p>
            <h1 className="mt-2 text-3xl font-semibold">
              Dashboard TVA et tresorerie
            </h1>
          </div>
          <div className="flex flex-col gap-3">
            <form className="flex flex-col gap-3 sm:flex-row" method="get">
              <label className="text-sm font-medium text-slate-600">
                Mois
                <input
                  className="mt-1 block h-10 rounded-md border border-slate-300 bg-white px-3 text-slate-950"
                  defaultValue={period}
                  name="period"
                  type="month"
                />
              </label>
              <label className="text-sm font-medium text-slate-600">
                Tresorerie depart
                <input
                  className="mt-1 block h-10 rounded-md border border-slate-300 bg-white px-3 text-slate-950"
                  defaultValue={openingCash}
                  min="0"
                  name="openingCash"
                  step="0.01"
                  type="number"
                />
              </label>
              <button className="h-10 self-end rounded-md bg-slate-950 px-4 text-sm font-semibold text-white">
                Actualiser
              </button>
            </form>
            <form action={logoutAction} className="flex justify-end">
              <button className="text-sm font-semibold text-slate-600 underline-offset-4 hover:underline">
                Deconnexion
              </button>
            </form>
          </div>
        </header>

        {message ? (
          <p className="rounded-md border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700">
            {message}
          </p>
        ) : null}

        {dashboard.data ? (
          <>
            <div className="flex flex-wrap justify-end gap-2">
              <a
                className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-900 shadow-sm"
                href={csvExportUrl}
              >
                Exporter CSV
              </a>
              <a
                className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-900 shadow-sm"
                href={xlsxExportUrl}
              >
                Exporter Excel
              </a>
            </div>
            <DashboardMetrics summary={dashboard.data} />
            <DetailTable summary={dashboard.data} />
          </>
        ) : (
          <section className="rounded-md border border-amber-200 bg-amber-50 p-5 text-sm text-amber-900">
            Impossible de charger le dashboard: {dashboard.error}.
          </section>
        )}

        <section className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_380px]">
          <form
            action={saveSalesAction}
            className="rounded-md border border-slate-200 bg-white p-5"
          >
            <div className="flex flex-col justify-between gap-2 border-b border-slate-200 pb-4 sm:flex-row">
              <div>
                <h2 className="text-base font-semibold">Ventes mensuelles</h2>
                <p className="mt-1 text-sm text-slate-500">
                  Saisie manuelle du chiffre d affaires du mois.
                </p>
              </div>
              <span className="text-sm font-medium text-slate-500">{period}</span>
            </div>
            <input name="period" type="hidden" value={period} />
            <input name="opening_cash" type="hidden" value={openingCash} />
            <div className="mt-5 grid gap-4 sm:grid-cols-3">
              <label className="text-sm font-medium text-slate-600">
                Ventes HT
                <input
                  className="mt-1 block h-10 w-full rounded-md border border-slate-300 px-3 text-slate-950"
                  defaultValue={monthlySales.data?.sales_ht ?? "0.00"}
                  min="0"
                  name="sales_ht"
                  required
                  step="0.01"
                  type="number"
                />
              </label>
              <label className="text-sm font-medium text-slate-600">
                TVA collectee
                <input
                  className="mt-1 block h-10 w-full rounded-md border border-slate-300 px-3 text-slate-950"
                  defaultValue={monthlySales.data?.vat_collected ?? "0.00"}
                  min="0"
                  name="vat_collected"
                  required
                  step="0.01"
                  type="number"
                />
              </label>
              <label className="text-sm font-medium text-slate-600">
                Ventes TTC
                <input
                  className="mt-1 block h-10 w-full rounded-md border border-slate-300 px-3 text-slate-950"
                  defaultValue={monthlySales.data?.sales_ttc ?? "0.00"}
                  min="0"
                  name="sales_ttc"
                  required
                  step="0.01"
                  type="number"
                />
              </label>
            </div>
            <div className="mt-5 flex justify-end">
              <button className="rounded-md bg-emerald-700 px-4 py-2 text-sm font-semibold text-white">
                Enregistrer les ventes
              </button>
            </div>
          </form>

          <aside className="rounded-md border border-slate-200 bg-white p-5">
            <h2 className="text-base font-semibold">Etat donnees</h2>
            <dl className="mt-4 space-y-4 text-sm">
              <div>
                <dt className="font-medium text-slate-500">Mois analyse</dt>
                <dd className="mt-1 font-semibold text-slate-950">{periodStart}</dd>
              </div>
              <div>
                <dt className="font-medium text-slate-500">Ventes en base</dt>
                <dd className="mt-1 font-semibold text-slate-950">
                  {monthlySales.data ? "Oui" : "Non"}
                </dd>
              </div>
              <div>
                <dt className="font-medium text-slate-500">Banque connectee</dt>
                <dd className="mt-1 font-semibold text-slate-950">
                  {dashboard.data?.cash_is_bank_connected ? "Oui" : "Non"}
                </dd>
              </div>
            </dl>
          </aside>
        </section>

        <section className="grid gap-6 lg:grid-cols-2">
          <DocumentUploadForm period={period} openingCash={openingCash} />
          <InvoiceForm period={period} openingCash={openingCash} />
        </section>
        <InvoiceList
          title="Factures importees a traiter"
          emptyText="Aucune facture importee en attente de date."
          invoices={reviewInboxInvoices.data ?? []}
          period={period}
          openingCash={openingCash}
        />
        <InvoiceList
          title="Factures du mois"
          emptyText="Aucune facture pour ce mois."
          invoices={invoices.data ?? []}
          csvExportUrl={invoiceCsvUrl}
          xlsxExportUrl={invoiceXlsxUrl}
          period={period}
          openingCash={openingCash}
        />
      </section>
    </main>
  );
}
