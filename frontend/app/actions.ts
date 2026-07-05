"use server";

import { redirect } from "next/navigation";

import type { InvoiceLineInput } from "@/types/api";
import {
  archiveInvoice,
  completeBankCallback,
  createInvoice,
  saveMonthlyCashFlowInputs,
  saveMonthlySales,
  startBankConnection,
  syncBankTransactions,
  updateBankTransactionCategory,
  updateInvoice,
  uploadDocumentImport,
  validateInvoice,
} from "@/lib/api";
import { clearSession, requireAuth } from "@/lib/session";
import { currentMonth, monthToDate } from "@/app/pageUtils";

type InvoiceLineFormResult = InvoiceLineInput | "incomplete" | null;

const INVOICE_FORM_LINE_NUMBERS = [1, 2, 3, 4, 5] as const;
const ALLOWED_RETURN_PATHS = new Set([
  "/",
  "/invoices",
  "/cash-flow",
  "/forecast",
  "/bank",
]);

function redirectBack(formData: FormData, message: string, fallbackPath: string): never {
  const requestedReturnTo = String(formData.get("return_to") ?? fallbackPath);
  const returnTo = ALLOWED_RETURN_PATHS.has(requestedReturnTo)
    ? requestedReturnTo
    : fallbackPath;
  const period = String(formData.get("period") ?? currentMonth());
  const openingCash = String(formData.get("opening_cash") ?? "0");
  const params = new URLSearchParams({
    period,
    openingCash,
    message,
  });
  redirect(`${returnTo}?${params.toString()}`);
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

export async function saveSalesAction(formData: FormData) {
  await requireAuth();

  const period = String(formData.get("period") ?? currentMonth());
  const periodStart = monthToDate(period);
  const salesHt = String(formData.get("sales_ht") ?? "0");
  const vatCollected = String(formData.get("vat_collected") ?? "0");
  const salesTtc = String(formData.get("sales_ttc") ?? "0");
  if (
    Math.abs(Number(salesHt) + Number(vatCollected) - Number(salesTtc)) >= 0.005
  ) {
    redirectBack(formData, "invalid_sales", "/cash-flow");
  }
  const result = await saveMonthlySales(periodStart, {
    sales_ht: salesHt,
    vat_collected: vatCollected,
    sales_ttc: salesTtc,
  });

  redirectBack(formData, result.error ? result.error : "saved", "/cash-flow");
}

export async function saveCashFlowInputsAction(formData: FormData) {
  await requireAuth();

  const period = String(formData.get("period") ?? currentMonth());
  const periodStart = monthToDate(period);
  const result = await saveMonthlyCashFlowInputs(periodStart, {
    salaries: String(formData.get("salaries") ?? "0"),
    social_charges: String(formData.get("social_charges") ?? "0"),
    investments_cash: String(formData.get("investments_cash") ?? "0"),
    loan_repayments_cash: String(formData.get("loan_repayments_cash") ?? "0"),
  });

  redirectBack(
    formData,
    result.error ? result.error : "cash_flow_inputs_saved",
    "/cash-flow",
  );
}

export async function createInvoiceAction(formData: FormData) {
  await requireAuth();

  const lineResults = INVOICE_FORM_LINE_NUMBERS.map((lineNumber) =>
    invoiceLineFromForm(formData, lineNumber),
  );
  if (lineResults.includes("incomplete")) {
    redirectBack(formData, "invoice_incomplete_line", "/invoices");
  }
  const lines = lineResults.filter(
    (line): line is InvoiceLineInput => line !== null && line !== "incomplete",
  );

  if (lines.length === 0) {
    redirectBack(formData, "invoice_missing_line", "/invoices");
  }

  const result = await createInvoice({
    supplier_name: String(formData.get("supplier_name") ?? "").trim(),
    invoice_date: String(formData.get("invoice_date") ?? "") || undefined,
    invoice_number: String(formData.get("invoice_number") ?? "").trim() || undefined,
    lines,
  });

  redirectBack(
    formData,
    result.error ? result.error : "invoice_created",
    "/invoices",
  );
}

export async function uploadDocumentAction(formData: FormData) {
  await requireAuth();

  const file = formData.get("invoice_file");
  if (!(file instanceof File) || file.size === 0) {
    redirectBack(formData, "document_upload_missing", "/invoices");
  }

  const result = await uploadDocumentImport(file);
  let message = "document_uploaded_to_inbox";
  if (result.data?.document_import.status === "extraction_completed") {
    message = "document_extracted";
  }
  if (result.data?.document_import.status === "extraction_failed") {
    message = "document_extraction_failed";
  }
  const rejectionMessages = new Set([
    "document_not_an_invoice",
    "document_contains_multiple_invoices",
  ]);
  const errorMessage =
    result.error && rejectionMessages.has(result.error)
      ? result.error
      : "document_upload_failed";
  redirectBack(formData, result.error ? errorMessage : message, "/invoices");
}

export async function validateInvoiceAction(formData: FormData) {
  await requireAuth();

  const invoiceId = String(formData.get("invoice_id") ?? "");
  const result = await validateInvoice(invoiceId);
  redirectBack(
    formData,
    result.error ? "invoice_validation_failed" : "invoice_validated",
    "/invoices",
  );
}

export async function updateInvoiceAction(formData: FormData) {
  await requireAuth();

  const invoiceId = String(formData.get("invoice_id") ?? "");
  const lineResults = INVOICE_FORM_LINE_NUMBERS.map((lineNumber) =>
    invoiceLineFromForm(formData, lineNumber),
  );
  if (lineResults.includes("incomplete")) {
    redirectBack(formData, "invoice_incomplete_line", "/invoices");
  }
  const lines = lineResults.filter(
    (line): line is InvoiceLineInput => line !== null && line !== "incomplete",
  );

  if (lines.length === 0) {
    redirectBack(formData, "invoice_missing_line", "/invoices");
  }

  const result = await updateInvoice(invoiceId, {
    supplier_name: String(formData.get("supplier_name") ?? "").trim(),
    invoice_date: String(formData.get("invoice_date") ?? "") || undefined,
    invoice_number: String(formData.get("invoice_number") ?? "").trim() || undefined,
    lines,
  });

  redirectBack(formData, result.error ? result.error : "invoice_updated", "/invoices");
}

export async function archiveInvoiceAction(formData: FormData) {
  await requireAuth();

  const invoiceId = String(formData.get("invoice_id") ?? "");
  const result = await archiveInvoice(invoiceId);
  redirectBack(
    formData,
    result.error ? result.error : "invoice_archived",
    "/invoices",
  );
}

export async function startBankConnectionAction() {
  await requireAuth();

  const result = await startBankConnection();
  if (result.error || !result.data) {
    redirect("/bank?message=bank_connect_failed");
  }
  redirect(result.data.auth_link);
}

export async function getPlaidLinkTokenAction(): Promise<{
  link_token: string;
  reference: string;
} | null> {
  await requireAuth();

  const result = await startBankConnection();
  if (result.error || !result.data) {
    return null;
  }
  const authLink = result.data.auth_link;
  if (!authLink.startsWith("plaid-link://")) {
    return null;
  }
  const link_token = authLink.replace("plaid-link://", "");
  return { link_token, reference: result.data.connection.reference };
}

export async function completePlaidConnectionAction(
  reference: string,
  publicToken: string,
): Promise<string | null> {
  await requireAuth();

  const result = await completeBankCallback(reference, undefined, publicToken);
  if (result.error || !result.data) {
    return null;
  }
  return result.data.id;
}

export async function syncBankTransactionsAction(formData: FormData) {
  await requireAuth();

  const connectionId = String(formData.get("connection_id") ?? "");
  const period = String(formData.get("period") ?? currentMonth());
  const openingCash = String(formData.get("opening_cash") ?? "0");
  const result = await syncBankTransactions(connectionId);
  const params = new URLSearchParams({
    connection: connectionId,
    message: result.error ? "bank_sync_failed" : "bank_synced",
    openingCash,
    period,
  });
  redirect(`/bank?${params.toString()}`);
}

export async function categorizeBankTransactionAction(formData: FormData) {
  await requireAuth();

  const transactionId = String(formData.get("transaction_id") ?? "");
  const connectionId = String(formData.get("connection_id") ?? "");
  const categoryCode = String(formData.get("category_code") ?? "");
  const createRule = formData.get("create_rule") === "on";
  const rulePattern = String(formData.get("rule_pattern") ?? "").trim();
  const period = String(formData.get("period") ?? currentMonth());
  const openingCash = String(formData.get("opening_cash") ?? "0");

  const result = await updateBankTransactionCategory(
    transactionId,
    categoryCode,
    createRule && rulePattern
      ? { createRule: true, rulePattern }
      : undefined,
  );

  const params = new URLSearchParams({
    connection: connectionId,
    message: result.error
      ? result.error === "duplicate_rule_pattern"
        ? "bank_rule_duplicate"
        : "bank_categorize_failed"
      : "transaction_categorized",
    openingCash,
    period,
  });
  redirect(`/bank?${params.toString()}`);
}

export async function logoutAction() {
  await clearSession();
  redirect("/login");
}
