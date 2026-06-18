"use server";

import type {
  ApiResult,
  AssistantUploadResult,
  AssistantValidationResult,
} from "@/types/api";
import {
  assistantUpload,
  assistantValidateInvoice,
} from "@/lib/api";
import { requireAuth } from "@/lib/session";

export async function assistantUploadAction(
  formData: FormData,
): Promise<ApiResult<AssistantUploadResult>> {
  await requireAuth();

  const file = formData.get("file");
  if (!(file instanceof File) || file.size === 0) {
    return { data: null, error: "Choisissez un fichier a importer." };
  }

  return assistantUpload(file);
}

export async function assistantValidateAction(
  formData: FormData,
): Promise<ApiResult<AssistantValidationResult>> {
  await requireAuth();

  const invoiceId = String(formData.get("invoice_id") ?? "");
  if (!invoiceId) {
    return { data: null, error: "Facture introuvable." };
  }

  return assistantValidateInvoice(invoiceId);
}
