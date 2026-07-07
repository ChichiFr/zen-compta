import { internalApiToken } from "@/lib/session";
import type {
  ApiResult,
  BankAnomaliesSummary,
  BankConnection,
  BankConnectionStartResult,
  BankMatchingRunResult,
  BankMatchSuggestion,
  BankSyncResult,
  BankTransaction,
  BankTransactionRule,
  BankUnpaidInvoice,
  DashboardSummary,
  DocumentImportUpload,
  HomeDashboardSummary,
  Invoice,
  InvoiceLineInput,
  MonthlyCashFlowInputs,
  MonthlyForecastSummary,
  MonthlyPerformanceSummary,
  MonthlySales,
  RunwayForecastSummary,
} from "@/types/api";

function apiBaseUrl() {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  return baseUrl.replace(/\/$/, "");
}

export function dashboardCsvExportUrl(periodStart: string, openingCash: string) {
  return dashboardExportUrl("summary.csv", periodStart, openingCash);
}

export function dashboardXlsxExportUrl(periodStart: string, openingCash: string) {
  return dashboardExportUrl("summary.xlsx", periodStart, openingCash);
}

export function invoiceCsvExportUrl(periodStart: string) {
  return invoiceExportUrl("export.csv", periodStart);
}

export function invoiceXlsxExportUrl(periodStart: string) {
  return invoiceExportUrl("export.xlsx", periodStart);
}

function dashboardExportUrl(
  path: "summary.csv" | "summary.xlsx",
  periodStart: string,
  openingCash: string,
) {
  const params = new URLSearchParams({
    period_start: periodStart,
    opening_cash: openingCash,
  });
  return `/downloads/dashboard/${path}?${params.toString()}`;
}

function invoiceExportUrl(path: "export.csv" | "export.xlsx", periodStart: string) {
  const params = new URLSearchParams({ period_start: periodStart });
  return `/downloads/invoice-files/${path}?${params.toString()}`;
}

async function fetchJson<T>(path: string, init?: RequestInit): Promise<ApiResult<T>> {
  try {
    const isFormData = init?.body instanceof FormData;
    const response = await fetch(`${apiBaseUrl()}/api${path}`, {
      ...init,
      cache: "no-store",
      headers: {
        ...(isFormData ? {} : { "Content-Type": "application/json" }),
        "X-Internal-API-Token": internalApiToken(),
        ...init?.headers,
      },
    });

    if (!response.ok) {
      let detail: unknown = null;
      try {
        detail = ((await response.json()) as { detail?: unknown })?.detail;
      } catch {
        detail = null;
      }
      if (typeof detail === "string" && /^[a-z0-9_]+$/.test(detail)) {
        return { data: null, error: detail };
      }
      return { data: null, error: `api_error_${response.status}` };
    }

    if (response.status === 204) {
      return { data: null as T, error: null };
    }
    return { data: (await response.json()) as T, error: null };
  } catch {
    return { data: null, error: "backend_unavailable" };
  }
}

export async function getHomeDashboard(periodStart: string) {
  const params = new URLSearchParams({ period_start: periodStart });
  return fetchJson<HomeDashboardSummary>(
    `/dashboard/home?${params.toString()}`,
  );
}

export async function getDashboardSummary(
  periodStart: string,
  openingCash: string,
) {
  const params = new URLSearchParams({
    period_start: periodStart,
    opening_cash: openingCash,
  });
  return fetchJson<DashboardSummary>(`/dashboard/summary?${params.toString()}`);
}

export async function getMonthlyPerformanceSummary(periodStart: string) {
  const params = new URLSearchParams({ period_start: periodStart });
  return fetchJson<MonthlyPerformanceSummary>(
    `/performance/monthly?${params.toString()}`,
  );
}

export async function getMonthlyForecastSummary(
  periodStart: string,
  payload: {
    opening_cash: string;
    forecast_sales_ht: string;
    fixed_salaries: string;
    variable_salary_rate: string;
    social_charge_rate: string;
    loan_repayments_cash: string;
  },
) {
  const params = new URLSearchParams({
    period_start: periodStart,
    ...payload,
  });
  return fetchJson<MonthlyForecastSummary>(
    `/forecast/monthly?${params.toString()}`,
  );
}

export async function getRunwayForecastSummary(
  periodStart: string,
  payload: {
    opening_cash: string;
    months: string;
    reference_sales_ht: string;
    custom_sales_drop_rate: string;
    fixed_salaries: string;
    variable_salary_rate: string;
    social_charge_rate: string;
    loan_repayments_cash: string;
    monthly_vat_payable_estimate: string;
    minimum_cash_threshold: string;
  },
) {
  const params = new URLSearchParams({
    period_start: periodStart,
    ...payload,
  });
  return fetchJson<RunwayForecastSummary>(
    `/forecast/runway?${params.toString()}`,
  );
}

export async function getMonthlySales(periodStart: string) {
  const result = await fetchJson<MonthlySales>(`/monthly-sales/${periodStart}`);
  if (result.error === "api_error_404") {
    // Aucune vente saisie pour ce mois: etat normal, pas une erreur.
    return { data: null, error: null };
  }
  return result;
}

export async function saveMonthlySales(
  periodStart: string,
  payload: {
    sales_ht: string;
    vat_collected: string;
    sales_ttc: string;
  },
) {
  return fetchJson<MonthlySales>(`/monthly-sales/${periodStart}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function saveMonthlyCashFlowInputs(
  periodStart: string,
  payload: {
    salaries: string;
    social_charges: string;
    investments_cash: string;
    loan_repayments_cash: string;
  },
) {
  return fetchJson<MonthlyCashFlowInputs>(
    `/performance/monthly-inputs/${periodStart}`,
    {
      method: "PUT",
      body: JSON.stringify(payload),
    },
  );
}

export async function getInvoices(periodStart?: string) {
  if (!periodStart) {
    return fetchJson<Invoice[]>("/invoices");
  }
  const params = new URLSearchParams({ period_start: periodStart });
  return fetchJson<Invoice[]>(`/invoices?${params.toString()}`);
}

export async function getImportedInvoicesToReview() {
  const params = new URLSearchParams({ imported_to_review: "true" });
  return fetchJson<Invoice[]>(`/invoices?${params.toString()}`);
}

export async function createInvoice(payload: {
  supplier_name: string;
  invoice_date?: string;
  invoice_number?: string;
  lines: InvoiceLineInput[];
}) {
  return fetchJson<Invoice>("/invoices", {
    method: "POST",
    body: JSON.stringify({
      ...payload,
      source: "manual",
    }),
  });
}

export async function uploadDocumentImport(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  return fetchJson<DocumentImportUpload>("/document-imports", {
    method: "POST",
    body: formData,
  });
}

export async function updateInvoice(
  invoiceId: string,
  payload: {
    supplier_name: string;
    invoice_date?: string;
    invoice_number?: string;
    lines: InvoiceLineInput[];
  },
) {
  return fetchJson<Invoice>(`/invoices/${invoiceId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function validateInvoice(invoiceId: string) {
  return fetchJson<Invoice>(`/invoices/${invoiceId}/validate`, {
    method: "POST",
  });
}

export async function archiveInvoice(invoiceId: string) {
  return fetchJson<Invoice>(`/invoices/${invoiceId}/archive`, {
    method: "POST",
  });
}

export async function startBankConnection() {
  return fetchJson<BankConnectionStartResult>("/bank/connect", {
    method: "POST",
  });
}

export async function completeBankCallback(
  ref: string,
  connectionId?: string,
  publicToken?: string,
) {
  if (publicToken) {
    return fetchJson<BankConnection>("/bank/callback", {
      method: "POST",
      body: JSON.stringify({
        ref,
        connection_id: connectionId,
        "public_token": publicToken,
      }),
    });
  }
  const params = new URLSearchParams({ ref });
  if (connectionId) {
    params.set("connection_id", connectionId);
  }
  return fetchJson<BankConnection>(`/bank/callback?${params.toString()}`);
}

export async function listBankConnections() {
  return fetchJson<BankConnection[]>("/bank/connections");
}

export async function syncBankTransactions(connectionId: string) {
  return fetchJson<BankSyncResult>(`/bank/connections/${connectionId}/sync`, {
    method: "POST",
  });
}

export async function listBankTransactions(connectionId: string) {
  return fetchJson<BankTransaction[]>(
    `/bank/connections/${connectionId}/transactions`,
  );
}

export async function updateBankTransactionCategory(
  transactionId: string,
  categoryCode: string,
  options?: { createRule?: boolean; rulePattern?: string },
) {
  return fetchJson<BankTransaction>(
    `/bank/transactions/${transactionId}/category`,
    {
      method: "PATCH",
      body: JSON.stringify({
        category_code: categoryCode,
        create_rule: options?.createRule ?? false,
        rule_pattern: options?.rulePattern ?? null,
      }),
    },
  );
}

export async function runBankMatching() {
  return fetchJson<BankMatchingRunResult>("/bank/matching/run", {
    method: "POST",
  });
}

export async function getBankMatchSuggestions(transactionId: string) {
  return fetchJson<BankMatchSuggestion[]>(
    `/bank/transactions/${transactionId}/match-suggestions`,
  );
}

export async function listUnmatchedInvoices() {
  return fetchJson<BankMatchSuggestion[]>("/bank/matching/unmatched-invoices");
}

export async function getBankAnomaliesSummary() {
  return fetchJson<BankAnomaliesSummary>("/bank/anomalies/summary");
}

export async function listUnpaidInvoices() {
  return fetchJson<BankUnpaidInvoice[]>("/bank/anomalies/unpaid-invoices");
}

export async function matchBankTransaction(
  transactionId: string,
  invoiceId: string,
) {
  return fetchJson<BankTransaction>(
    `/bank/transactions/${transactionId}/match`,
    {
      method: "PATCH",
      body: JSON.stringify({ invoice_id: invoiceId }),
    },
  );
}

export async function unmatchBankTransaction(transactionId: string) {
  return fetchJson<BankTransaction>(
    `/bank/transactions/${transactionId}/match`,
    { method: "DELETE" },
  );
}

export async function listBankTransactionRules() {
  return fetchJson<BankTransactionRule[]>("/bank/transaction-rules");
}

export async function deleteBankTransactionRule(ruleId: string) {
  return fetchJson<null>(`/bank/transaction-rules/${ruleId}`, {
    method: "DELETE",
  });
}
