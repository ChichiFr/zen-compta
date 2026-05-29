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

export type ApiResult<T> =
  | { data: T; error: null }
  | { data: null; error: string };

function apiBaseUrl() {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  return baseUrl.replace(/\/$/, "");
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
