export type DashboardSummary = {
  period_start: string;
  invoices_to_review_count: number;
  validated_invoices_count: number;
  validated_invoices_ht: string;
  validated_invoices_tva: string;
  validated_invoices_ttc: string;
  vat_deductible: string;
  vat_collected: string;
  vat_payable_estimate: string;
  opening_cash: string;
  sales_ht: string;
  sales_ttc: string;
  estimated_cash: string;
  cash_is_bank_connected: boolean;
};

export type MonthlySales = {
  id: string;
  period_start: string;
  sales_ht: string;
  vat_collected: string;
  sales_ttc: string;
};

export type InvoiceStatus = "draft" | "needs_review" | "validated" | "archived";

export type InvoiceLineInput = {
  description: string;
  category?: string;
  vat_rate: string;
  amount_ht: string;
};

export type InvoiceLine = {
  id: string;
  description: string;
  category: string | null;
  vat_rate: string;
  amount_ht: string;
  amount_tva: string;
  amount_ttc: string;
  needs_review_reason: string | null;
};

export type Invoice = {
  id: string;
  supplier_name: string;
  invoice_date: string | null;
  invoice_number: string | null;
  status: InvoiceStatus;
  source: "manual" | "ai_upload";
  total_ht: string;
  total_tva: string;
  total_ttc: string;
  lines: InvoiceLine[];
};

export type ApiResult<T> =
  | { data: T; error: null }
  | { data: null; error: string };

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
  return `${apiBaseUrl()}/api/dashboard/${path}?${params.toString()}`;
}

function invoiceExportUrl(path: "export.csv" | "export.xlsx", periodStart: string) {
  const params = new URLSearchParams({ period_start: periodStart });
  return `${apiBaseUrl()}/api/invoices/${path}?${params.toString()}`;
}

async function fetchJson<T>(path: string, init?: RequestInit): Promise<ApiResult<T>> {
  try {
    const response = await fetch(`${apiBaseUrl()}/api${path}`, {
      ...init,
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
        ...init?.headers,
      },
    });

    if (!response.ok) {
      return { data: null, error: `api_error_${response.status}` };
    }

    return { data: (await response.json()) as T, error: null };
  } catch {
    return { data: null, error: "backend_unavailable" };
  }
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

export async function getMonthlySales(periodStart: string) {
  return fetchJson<MonthlySales>(`/monthly-sales/${periodStart}`);
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

export async function getInvoices(periodStart?: string) {
  if (!periodStart) {
    return fetchJson<Invoice[]>("/invoices");
  }
  const params = new URLSearchParams({ period_start: periodStart });
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

export async function validateInvoice(invoiceId: string) {
  return fetchJson<Invoice>(`/invoices/${invoiceId}/validate`, {
    method: "POST",
  });
}
