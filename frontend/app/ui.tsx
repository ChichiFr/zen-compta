import Link from "next/link";
import type { ReactNode } from "react";

import { DocumentFileInput } from "@/components/DocumentFileInput";
import {
  DashboardSummary,
  Invoice,
  MonthlyCashFlowInputs,
  MonthlyForecastSummary,
  MonthlyPerformanceSummary,
  MonthlySales,
  RunwayForecastSummary,
} from "@/lib/api";
import {
  INVOICE_CATEGORIES,
  invoiceCategoryLabel,
} from "@/lib/invoiceCategories";
import {
  invoiceReviewMessages,
  invoiceReviewSummary,
} from "@/lib/invoiceReview";
import type {
  InvoiceReviewKind,
  InvoiceReviewMessage,
} from "@/lib/invoiceReview";
import {
  archiveInvoiceAction,
  createInvoiceAction,
  logoutAction,
  saveCashFlowInputsAction,
  saveSalesAction,
  updateInvoiceAction,
  uploadDocumentAction,
  validateInvoiceAction,
} from "@/app/actions";
import { StatusMessage, formatMoney } from "@/app/pageUtils";

const INVOICE_FORM_LINE_NUMBERS = [1, 2, 3, 4, 5] as const;

type AppShellProps = {
  active: "dashboard" | "invoices" | "cash-flow" | "forecast";
  children: ReactNode;
  openingCash: string;
  period: string;
  preservedQueryParams?: Record<string, string>;
  title: string;
};

const NAV_ITEMS = [
  { key: "dashboard", label: "Tableau de bord", href: "/" },
  { key: "invoices", label: "Factures", href: "/invoices" },
  { key: "cash-flow", label: "Cash-flow", href: "/cash-flow" },
  { key: "forecast", label: "Prevision", href: "/forecast" },
] as const;

export function AppShell({
  active,
  children,
  openingCash,
  period,
  preservedQueryParams = {},
  title,
}: AppShellProps) {
  const preservedQuery = new URLSearchParams(preservedQueryParams).toString();
  const preservedSuffix = preservedQuery ? `&${preservedQuery}` : "";

  return (
    <main className="min-h-screen bg-[#f6f7f4] text-slate-950">
      <section className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-5 py-6 sm:px-6 lg:px-8">
        <header className="flex flex-col gap-5 border-b border-slate-200 pb-5">
          <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
            <div>
              <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">
                Zen Compta
              </p>
              <h1 className="mt-2 text-3xl font-semibold">{title}</h1>
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
                {Object.entries(preservedQueryParams).map(([key, value]) => (
                  <input key={key} name={key} type="hidden" value={value} />
                ))}
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
          </div>
          <nav className="flex flex-wrap gap-2">
            {NAV_ITEMS.map((item) => {
              const href =
                item.href === "/"
                  ? `/?period=${period}&openingCash=${openingCash}${preservedSuffix}`
                  : `${item.href}?period=${period}&openingCash=${openingCash}${preservedSuffix}`;
              return (
                <Link
                  className={`rounded-md border px-3 py-2 text-sm font-semibold ${
                    item.key === active
                      ? "border-slate-950 bg-slate-950 text-white"
                      : "border-slate-300 bg-white text-slate-800"
                  }`}
                  href={href}
                  key={item.key}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </header>
        {children}
      </section>
    </main>
  );
}

const STATUS_MESSAGE_STYLES = {
  success: "border-emerald-200 bg-emerald-50 text-emerald-900",
  review: "border-amber-200 bg-amber-50 text-amber-950",
  technical: "border-rose-200 bg-rose-50 text-rose-900",
};

export function StatusMessageBanner({ message }: { message: StatusMessage }) {
  return (
    <p
      className={`rounded-md border px-4 py-3 text-sm font-medium ${STATUS_MESSAGE_STYLES[message.kind]}`}
    >
      {message.text}
    </p>
  );
}

export function ApiErrorNotice({
  error,
  label,
}: {
  error: string | null;
  label: string;
}) {
  if (!error) {
    return null;
  }
  return (
    <section className="rounded-md border border-amber-200 bg-amber-50 p-5 text-sm text-amber-900">
      Impossible de charger {label}: {error}.
    </section>
  );
}

function MetricCard({
  help,
  label,
  value,
}: {
  help: string;
  label: string;
  value: string;
}) {
  return (
    <article className="rounded-md border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-sm font-medium text-slate-500">{label}</p>
      <p className="mt-3 text-2xl font-semibold text-slate-950">{value}</p>
      <p className="mt-2 text-sm leading-5 text-slate-500">{help}</p>
    </article>
  );
}

export function DashboardMetrics({
  dashboard,
  forecast,
  performance,
}: {
  dashboard: DashboardSummary;
  forecast: MonthlyForecastSummary | null;
  performance: MonthlyPerformanceSummary | null;
}) {
  const normalForecast = forecast?.scenarios.find(
    (scenario) => scenario.key === "normal",
  );
  const metrics = [
    {
      label: "CA HT",
      value: formatMoney(dashboard.sales_ht),
      help: "Ventes mensuelles saisies.",
    },
    {
      label: "EBE Cash",
      value: performance
        ? formatMoney(performance.performance.ebe_cash)
        : "Non disponible",
      help: "Performance d exploitation hors flux exceptionnels.",
    },
    {
      label: "Cash estime",
      value: formatMoney(dashboard.estimated_cash),
      help: "Tresorerie depart + ventes TTC - factures TTC - TVA a payer.",
    },
    {
      label: "Fin de mois prevue",
      value: normalForecast
        ? formatMoney(normalForecast.ending_cash_estimate)
        : "Non disponible",
      help: "Simulation cash avec les hypotheses de prevision.",
    },
  ];

  return (
    <section className="grid gap-4 lg:grid-cols-4">
      {metrics.map((metric) => (
        <MetricCard key={metric.label} {...metric} />
      ))}
    </section>
  );
}

export function DashboardHealth({
  dashboard,
  forecast,
  performance,
}: {
  dashboard: DashboardSummary;
  forecast: MonthlyForecastSummary | null;
  performance: MonthlyPerformanceSummary | null;
}) {
  const worstRisk = forecast?.scenarios.some(
    (scenario) => scenario.risk_level === "critical",
  )
    ? "critical"
    : forecast?.scenarios.some((scenario) => scenario.risk_level === "warning")
      ? "warning"
      : "ok";
  const profitable =
    performance && Number(performance.performance.ebe_cash) > 0;

  return (
    <section className="rounded-md border border-slate-200 bg-white p-5">
      <h2 className="text-base font-semibold">Sante du mois</h2>
      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <p className="rounded-md bg-slate-50 p-3 text-sm">
          <span className="block font-semibold">
            {profitable ? "Mois rentable" : "Performance a surveiller"}
          </span>
          <span className="text-slate-500">
            {profitable
              ? "L exploitation gagne de l argent."
              : "L EBE Cash est nul ou negatif."}
          </span>
        </p>
        <p className="rounded-md bg-slate-50 p-3 text-sm">
          <span className="block font-semibold">
            {dashboard.invoices_to_review_count} factures a traiter
          </span>
          <span className="text-slate-500">
            Les factures non validees restent hors exports.
          </span>
        </p>
        <p className="rounded-md bg-slate-50 p-3 text-sm">
          <span className="block font-semibold">
            Risque prevision: {riskLabel(worstRisk)}
          </span>
          <span className="text-slate-500">
            Voir les scenarios detailles dans Prevision.
          </span>
        </p>
      </div>
    </section>
  );
}

export function DetailTable({ summary }: { summary: DashboardSummary }) {
  const rows = [
    ["Ventes HT", formatMoney(summary.sales_ht)],
    ["TVA collectee", formatMoney(summary.vat_collected)],
    ["Ventes TTC", formatMoney(summary.sales_ttc)],
    ["Factures validees HT", formatMoney(summary.validated_invoices_ht)],
    ["TVA deductible", formatMoney(summary.vat_deductible)],
    ["Factures validees TTC", formatMoney(summary.validated_invoices_ttc)],
  ];

  return <SimpleTable rows={rows} title="Lecture comptable du mois" />;
}

export function PerformanceAndCashFlowTables({
  compact = false,
  summary,
}: {
  compact?: boolean;
  summary: MonthlyPerformanceSummary;
}) {
  const performanceRows = [
    ["CA HT", formatMoney(summary.performance.sales_ht)],
    ["Matieres premieres HT", formatMoney(summary.performance.raw_materials_ht)],
    ["Emballages HT", formatMoney(summary.performance.packaging_ht)],
    ["Salaires", formatMoney(summary.performance.salaries)],
    ["Charges sociales", formatMoney(summary.performance.social_charges)],
    [
      "Achats externes, charges et impots HT",
      formatMoney(summary.performance.external_purchases_taxes_ht),
    ],
    ["EBE Cash", formatMoney(summary.performance.ebe_cash)],
  ];
  const cashFlowRows = [
    [
      "Investissements cash",
      formatMoney(summary.non_operating_cash_flow.investments_cash),
    ],
    [
      "Remboursements emprunts cash",
      formatMoney(summary.non_operating_cash_flow.loan_repayments_cash),
    ],
    [
      "TVA a payer estimee",
      formatMoney(summary.non_operating_cash_flow.vat_payable_estimate),
    ],
    [
      "Credit TVA estime",
      formatMoney(summary.non_operating_cash_flow.vat_credit_estimate),
    ],
    [
      "Total hors exploitation",
      formatMoney(summary.non_operating_cash_flow.total_cash_outflow),
    ],
  ];

  return (
    <section className="grid gap-6 lg:grid-cols-2">
      <SimpleTable
        rows={compact ? performanceRows.slice(0, 4).concat([performanceRows[6]]) : performanceRows}
        title="Performance"
      />
      <SimpleTable
        rows={compact ? cashFlowRows.slice(1) : cashFlowRows}
        title="Flux exceptionnels / hors exploitation"
      />
      {summary.data_quality_notes.length > 0 ? (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 lg:col-span-2">
          {summary.data_quality_notes.map((note) => (
            <p key={note}>{noteLabel(note)}</p>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function SimpleTable({ rows, title }: { rows: string[][]; title: string }) {
  return (
    <article className="rounded-md border border-slate-200 bg-white">
      <div className="border-b border-slate-200 px-5 py-4">
        <h2 className="text-base font-semibold">{title}</h2>
      </div>
      <dl className="divide-y divide-slate-200">
        {rows.map(([label, value], index) => (
          <div
            className={`grid grid-cols-[minmax(0,1fr)_150px] gap-4 px-5 py-3 ${
              index === rows.length - 1 ? "bg-slate-50 font-semibold" : ""
            }`}
            key={label}
          >
            <dt className="text-sm text-slate-600">{label}</dt>
            <dd className="text-right text-sm font-semibold text-slate-950">
              {value}
            </dd>
          </div>
        ))}
      </dl>
    </article>
  );
}

function noteLabel(note: string) {
  if (note === "monthly_sales_missing") {
    return "CA mensuel non saisi: la performance utilise 0 EUR de ventes.";
  }
  if (note === "cash_flow_inputs_missing") {
    return "Flux salaires, charges, investissements et emprunts non saisis: ils valent 0 EUR.";
  }
  if (note === "forecast_operating_costs_ratio_missing") {
    return "Charges fournisseurs insuffisantes: la prevision ne peut pas encore estimer les couts d exploitation variables.";
  }
  return note;
}

export function DashboardActions({
  openingCash,
  period,
}: {
  openingCash: string;
  period: string;
}) {
  const query = `period=${period}&openingCash=${openingCash}`;
  return (
    <section className="grid gap-3 md:grid-cols-4">
      <ActionLink href={`/invoices?${query}`} label="Importer une facture" />
      <ActionLink href={`/invoices?${query}`} label="Factures a traiter" />
      <ActionLink href={`/cash-flow?${query}`} label="Ouvrir cash-flow" />
      <ActionLink href={`/forecast?${query}`} label="Ouvrir prevision" />
    </section>
  );
}

function ActionLink({ href, label }: { href: string; label: string }) {
  return (
    <Link
      className="rounded-md border border-slate-300 bg-white px-4 py-3 text-center text-sm font-semibold text-slate-900 shadow-sm"
      href={href}
    >
      {label}
    </Link>
  );
}

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

export function DataStatus({
  dashboard,
  monthlySales,
  periodStart,
}: {
  dashboard: DashboardSummary | null;
  monthlySales: MonthlySales | null;
  periodStart: string;
}) {
  return (
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
            {monthlySales ? "Oui" : "Non"}
          </dd>
        </div>
        <div>
          <dt className="font-medium text-slate-500">Banque connectee</dt>
          <dd className="mt-1 font-semibold text-slate-950">
            {dashboard?.cash_is_bank_connected ? "Oui" : "Non"}
          </dd>
        </div>
      </dl>
    </aside>
  );
}

function MoneyInput({
  defaultValue,
  label,
  max,
  name,
  required = true,
}: {
  defaultValue: string;
  label: string;
  max?: string;
  name: string;
  required?: boolean;
}) {
  return (
    <label className="text-sm font-medium text-slate-600">
      {label}
      <input
        className="mt-1 block h-10 w-full rounded-md border border-slate-300 px-3 text-slate-950"
        defaultValue={defaultValue}
        max={max}
        min="0"
        name={name}
        required={required}
        step="0.01"
        type="number"
      />
    </label>
  );
}

function FormFooter({ label }: { label: string }) {
  return (
    <div className="mt-5 flex justify-end">
      <button className="rounded-md bg-emerald-700 px-4 py-2 text-sm font-semibold text-white">
        {label}
      </button>
    </div>
  );
}

export function DocumentUploadForm({
  openingCash,
  period,
}: {
  openingCash: string;
  period: string;
}) {
  return (
    <form
      action={uploadDocumentAction}
      className="rounded-md border border-slate-200 bg-white px-5 py-4"
    >
      <input name="return_to" type="hidden" value="/invoices" />
      <input name="period" type="hidden" value={period} />
      <input name="opening_cash" type="hidden" value={openingCash} />
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h2 className="text-base font-semibold">Importer une facture</h2>
          <p className="mt-1 text-sm text-slate-500">
            PDF ou image. Une facture a la fois.
          </p>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <DocumentFileInput />
          <button className="h-10 rounded-md bg-slate-950 px-4 text-sm font-semibold text-white">
          Importer
          </button>
        </div>
      </div>
    </form>
  );
}

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

function InvoiceHeaderFields({ invoice }: { invoice?: Invoice }) {
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

function InvoiceLineFields({
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

const REVIEW_LABELS: Record<InvoiceReviewKind, string> = {
  important: "Alerte importante",
  ai: "Commentaire IA",
  technical: "Erreur technique",
  review: "A verifier",
};

const REVIEW_STYLES: Record<InvoiceReviewKind, string> = {
  important: "border-amber-200 bg-amber-50 text-amber-950",
  ai: "border-sky-200 bg-sky-50 text-sky-950",
  technical: "border-rose-200 bg-rose-50 text-rose-900",
  review: "border-slate-200 bg-slate-50 text-slate-800",
};

function groupedReviewMessages(messages: InvoiceReviewMessage[]) {
  return (["important", "review", "ai", "technical"] as const).map((kind) => ({
    kind,
    messages: messages.filter((message) => message.kind === kind),
  }));
}

function InvoiceReviewPanel({ invoice }: { invoice: Invoice }) {
  const summary = invoiceReviewSummary(invoice.lines);
  if (
    invoice.source !== "ai_upload" ||
    invoice.status === "validated" ||
    summary.messages.length === 0
  ) {
    return null;
  }

  const items = [
    { kind: "important" as const, count: summary.important },
    { kind: "review" as const, count: summary.review },
    { kind: "ai" as const, count: summary.ai },
    { kind: "technical" as const, count: summary.technical },
  ].filter((item) => item.count > 0);

  return (
    <div className="mt-4 grid gap-2 md:grid-cols-3">
      {items.map((item) => (
        <div
          className={`rounded-md border px-3 py-2 ${REVIEW_STYLES[item.kind]}`}
          key={item.kind}
        >
          <p className="text-xs font-semibold uppercase tracking-wide">
            {REVIEW_LABELS[item.kind]}
          </p>
          <p className="mt-1 text-lg font-semibold">{item.count}</p>
        </div>
      ))}
    </div>
  );
}

function LineReviewMessages({ reason }: { reason: string | null }) {
  const messages = invoiceReviewMessages(reason);
  if (messages.length === 0) {
    return null;
  }

  return (
    <div className="mt-2 space-y-2">
      {groupedReviewMessages(messages).map((group) =>
        group.messages.length > 0 ? (
          <div
            className={`rounded-md border px-2.5 py-2 ${REVIEW_STYLES[group.kind]}`}
            key={group.kind}
          >
            <p className="text-[11px] font-semibold uppercase tracking-wide">
              {REVIEW_LABELS[group.kind]}
            </p>
            <ul className="mt-1 space-y-1 text-xs leading-5">
              {group.messages.map((message, index) => (
                <li key={`${message.kind}-${message.code}-${index}`}>
                  {message.text}
                </li>
              ))}
            </ul>
          </div>
        ) : null,
      )}
    </div>
  );
}

function hasVisibleValidationBlocker(invoice: Invoice) {
  return (
    !invoice.supplier_name.trim() ||
    !invoice.invoice_date ||
    invoice.lines.length === 0 ||
    invoice.lines.some(
      (line) => invoiceReviewMessages(line.needs_review_reason).length > 0,
    )
  );
}

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

export function RunwayForecastResults({
  summary,
}: {
  summary: RunwayForecastSummary;
}) {
  const selectedScenario =
    summary.scenarios.find((scenario) => scenario.key === "custom_drop") ??
    summary.scenarios[0];
  const firstCritical = selectedScenario.first_critical_month
    ? formatMonth(selectedScenario.first_critical_month)
    : "Aucun mois critique";
  const selectedRunway = runwayLabel(
    selectedScenario.runway_months,
    Boolean(selectedScenario.first_critical_month),
  );

  return (
    <section className="grid gap-6">
      {summary.data_quality_notes.length > 0 ? (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          {summary.data_quality_notes.map((note) => (
            <p key={note}>{noteLabel(note)}</p>
          ))}
        </div>
      ) : null}

      <article className="rounded-md border border-slate-200 bg-white p-5">
        <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          Reponse principale
        </p>
        <h2 className="mt-2 text-2xl font-semibold text-slate-950">
          Avec une baisse de CA de {selectedScenario.sales_drop_rate}%, vous
          tenez {selectedRunway}.
        </h2>
        <div className="mt-5 grid gap-4 md:grid-cols-3">
          <ForecastMetric label="Premier mois critique" value={firstCritical} plain />
          <ForecastMetric label="Cash fin periode" value={selectedScenario.ending_cash_estimate} />
          <ForecastMetric label="Risque" value={riskLabel(selectedScenario.risk_level)} plain />
        </div>
      </article>

      <article className="rounded-md border border-slate-200 bg-white">
        <div className="border-b border-slate-200 px-5 py-4">
          <h2 className="text-base font-semibold">Scenarios compares</h2>
        </div>
        <div className="grid gap-0 md:grid-cols-2 xl:grid-cols-5">
          {summary.scenarios.map((scenario) => (
            <div
              className="border-b border-slate-200 px-5 py-4 md:border-r xl:border-b-0"
              key={scenario.key}
            >
              <p className="font-semibold">{scenario.label}</p>
              <p className={`mt-1 text-sm font-semibold ${riskClass(scenario.risk_level)}`}>
                {riskLabel(scenario.risk_level)}
              </p>
              <dl className="mt-4 space-y-3 text-sm">
                <ForecastAssumption
                  label="Mois tenables"
                  plain
                  value={runwayLabel(
                    scenario.runway_months,
                    Boolean(scenario.first_critical_month),
                  )}
                />
                <ForecastAssumption label="Mois critique" value={scenario.first_critical_month ? formatMonth(scenario.first_critical_month) : "Aucun"} plain />
                <ForecastAssumption label="Cash final" value={scenario.ending_cash_estimate} />
              </dl>
            </div>
          ))}
        </div>
      </article>

      <article className="rounded-md border border-slate-200 bg-white p-5">
        <h2 className="text-base font-semibold">Detail mois par mois</h2>
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-3 py-3">Mois</th>
                <th className="px-3 py-3">CA</th>
                <th className="px-3 py-3">EBE</th>
                <th className="px-3 py-3">TVA</th>
                <th className="px-3 py-3">Emprunts</th>
                <th className="px-3 py-3">Cash final</th>
                <th className="px-3 py-3">Risque</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {selectedScenario.months.map((month) => (
                <tr key={month.month}>
                  <td className="px-3 py-3 font-semibold">{formatMonth(month.month)}</td>
                  <td className="px-3 py-3">{formatMoney(month.forecast_sales_ht)}</td>
                  <td className="px-3 py-3">{formatMoney(month.ebe_forecast)}</td>
                  <td className="px-3 py-3">{formatMoney(month.vat_payable_estimate)}</td>
                  <td className="px-3 py-3">{formatMoney(month.loan_repayments_cash)}</td>
                  <td className="px-3 py-3 font-semibold">{formatMoney(month.ending_cash_estimate)}</td>
                  <td className={`px-3 py-3 font-semibold ${riskClass(month.risk_level)}`}>
                    {riskLabel(month.risk_level)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </article>
    </section>
  );
}

function ForecastMetric({
  label,
  plain = false,
  value,
}: {
  label: string;
  plain?: boolean;
  value: string;
}) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        {label}
      </p>
      <p className="mt-1 font-semibold">{plain ? value : formatMoney(value)}</p>
    </div>
  );
}

function ForecastAssumption({
  label,
  plain = false,
  value,
}: {
  label: string;
  plain?: boolean;
  value: string;
}) {
  return (
    <div className="flex justify-between gap-4">
      <dt className="text-slate-500">{label}</dt>
      <dd className="font-semibold text-slate-950">
        {plain || value.includes("%") ? value : formatMoney(value)}
      </dd>
    </div>
  );
}

function formatMonth(value: string) {
  return new Intl.DateTimeFormat("fr-FR", {
    month: "long",
    year: "numeric",
  }).format(new Date(`${value}T00:00:00`));
}

function runwayLabel(months: number, hasCriticalMonth: boolean) {
  if (!hasCriticalMonth) {
    return `au moins ${months} mois`;
  }
  return `${months} mois`;
}

function riskLabel(risk: "ok" | "warning" | "critical") {
  if (risk === "critical") {
    return "Critique";
  }
  if (risk === "warning") {
    return "Attention";
  }
  return "OK";
}

function riskClass(risk: "ok" | "warning" | "critical") {
  if (risk === "critical") {
    return "text-rose-700";
  }
  if (risk === "warning") {
    return "text-amber-700";
  }
  return "text-emerald-700";
}
