import { internalApiToken } from "@/lib/session";

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

export type MonthlyCashFlowInputs = {
  id: string | null;
  period_start: string;
  salaries: string;
  social_charges: string;
  investments_cash: string;
  loan_repayments_cash: string;
};

export type MonthlyPerformanceSummary = {
  period_start: string;
  inputs: MonthlyCashFlowInputs;
  performance: {
    sales_ht: string;
    raw_materials_ht: string;
    packaging_ht: string;
    salaries: string;
    social_charges: string;
    external_purchases_taxes_ht: string;
    ebe_cash: string;
  };
  non_operating_cash_flow: {
    investments_cash: string;
    loan_repayments_cash: string;
    vat_payable_estimate: string;
    vat_credit_estimate: string;
    total_cash_outflow: string;
    forecast_relevant_cash_outflow: string;
  };
  vat_collected: string;
  vat_deductible: string;
  data_quality_notes: string[];
};

export type MonthlyForecastSummary = {
  period_start: string;
  assumptions: {
    opening_cash: string;
    forecast_sales_ht: string;
    fixed_salaries: string;
    variable_salary_rate: string;
    social_charge_rate: string;
    loan_repayments_cash: string;
    vat_collection_rate: string;
    vat_deductible_estimate: string;
  };
  scenarios: Array<{
    key: "normal" | "sales_minus_10" | "sales_minus_20";
    label: string;
    forecast_sales_ht: string;
    salaries: string;
    social_charges: string;
    operating_costs_ht: string;
    ebe_forecast: string;
    vat_collected_estimate: string;
    vat_payable_estimate: string;
    vat_credit_estimate: string;
    loan_repayments_cash: string;
    ending_cash_estimate: string;
    risk_level: "ok" | "warning" | "critical";
  }>;
  data_quality_notes: string[];
};

export type RunwayForecastSummary = {
  period_start: string;
  assumptions: {
    opening_cash: string;
    months: 3 | 6 | 12;
    reference_sales_ht: string;
    custom_sales_drop_rate: string;
    fixed_salaries: string;
    variable_salary_rate: string;
    social_charge_rate: string;
    loan_repayments_cash: string;
    monthly_vat_payable_estimate: string;
    minimum_cash_threshold: string;
  };
  scenarios: Array<{
    key:
      | "normal"
      | "custom_drop"
      | "sales_minus_10"
      | "sales_minus_20"
      | "sales_minus_30";
    label: string;
    sales_drop_rate: string;
    runway_months: number;
    first_critical_month: string | null;
    ending_cash_estimate: string;
    risk_level: "ok" | "warning" | "critical";
    months: Array<{
      month: string;
      opening_cash: string;
      forecast_sales_ht: string;
      salaries: string;
      social_charges: string;
      operating_costs_ht: string;
      ebe_forecast: string;
      vat_payable_estimate: string;
      loan_repayments_cash: string;
      ending_cash_estimate: string;
      risk_level: "ok" | "warning" | "critical";
    }>;
  }>;
  data_quality_notes: string[];
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

export type DocumentImport = {
  id: string;
  original_filename: string;
  stored_filename: string;
  storage_path: string;
  content_type: string;
  size_bytes: number;
  status:
    | "uploaded"
    | "extraction_pending"
    | "extraction_failed"
    | "extraction_completed";
  created_at: string;
};

export type DocumentImportUpload = {
  document_import: DocumentImport;
  invoice: Invoice;
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
