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
  monthly_outflows: string;
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
    salaries_total_ht: string;
    fixed_charges_ht: string;
    external_purchases_ht: string;
    fixed_charges_breakdown: Record<string, string>;
    external_purchases_breakdown: Record<string, string>;
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
  ai_confidence: string | null;
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

export type BankConnectionStatus = "created" | "linked" | "expired" | "revoked";

export type BankConnection = {
  id: string;
  provider: string;
  institution_id: string;
  institution_name: string;
  reference: string;
  status: BankConnectionStatus;
  expires_at: string | null;
  created_at: string;
};

export type BankConnectionStartResult = {
  connection: BankConnection;
  auth_link: string;
};

export type BankTransaction = {
  id: string;
  booking_date: string;
  value_date: string | null;
  amount: string;
  currency: string;
  description: string;
  creditor_name: string | null;
  debtor_name: string | null;
  category_code: string | null;
  category_source: "rule" | "manual" | null;
  matched_invoice_id: string | null;
  match_source: "auto" | "manual" | null;
};

export type BankMatchSuggestion = {
  id: string;
  supplier_name: string;
  invoice_date: string | null;
  invoice_number: string | null;
  total_ttc: string;
};

export type BankMatchingRunResult = {
  matched_count: number;
};

export type BankAnomaliesSummary = {
  unpaid_invoices_count: number;
};

export type HomeMonthlyPoint = {
  month: string;
  sales_ht: string;
  sales_prior_ht: string | null;
  purchases_ht: string;
  purchases_prior_ht: string | null;
};

export type HomeBankFlowPoint = {
  day: string;
  cumulative_flow: string;
};

export type HomeDashboardSummary = {
  period_start: string;
  monthly_series: HomeMonthlyPoint[];
  bank_connected: boolean;
  bank_flow: HomeBankFlowPoint[];
  bank_net_flow: string;
  unpaid_invoices_count: number;
};

export type BankUnpaidInvoice = {
  id: string;
  supplier_name: string;
  invoice_date: string | null;
  invoice_number: string | null;
  total_ttc: string;
};

export type BankTransactionRule = {
  id: string;
  pattern: string;
  category_code: string;
  created_at: string;
};

export type BankSyncResult = {
  connection_id: string;
  new_transactions_count: number;
  total_transactions_count: number;
};
