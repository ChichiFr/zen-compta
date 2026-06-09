export type SearchParams = Promise<Record<string, string | string[] | undefined>>;

export type StatusMessageKind = "success" | "review" | "technical";
export type StatusMessage = {
  kind: StatusMessageKind;
  text: string;
};

export function firstParam(
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

export function currentMonth() {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  return `${now.getFullYear()}-${month}`;
}

export function monthToDate(value: string) {
  if (!/^\d{4}-\d{2}$/.test(value)) {
    return `${currentMonth()}-01`;
  }
  return `${value}-01`;
}

export function formatMoney(value: string) {
  const amount = Number(value);
  if (!Number.isFinite(amount)) {
    return `${value} EUR`;
  }
  return new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "EUR",
  }).format(amount);
}

export function statusMessage(value: string | null): StatusMessage | null {
  if (value === "saved") {
    return { kind: "success", text: "Ventes mensuelles enregistrees." };
  }
  if (value === "cash_flow_inputs_saved") {
    return { kind: "success", text: "Flux mensuels enregistres." };
  }
  if (value === "invoice_created") {
    return {
      kind: "review",
      text: "Facture creee. Elle doit encore etre validee humainement.",
    };
  }
  if (value === "document_uploaded_to_inbox") {
    return {
      kind: "review",
      text: "Document importe. La facture est dans Factures importees a traiter.",
    };
  }
  if (value === "document_extracted") {
    return {
      kind: "review",
      text: "Document importe et pre-rempli par IA. Verifie la facture avant validation.",
    };
  }
  if (value === "document_extraction_failed") {
    return {
      kind: "technical",
      text: "Document importe, mais l extraction IA a echoue. Complete la facture manuellement.",
    };
  }
  if (value === "document_upload_missing") {
    return {
      kind: "review",
      text: "Choisis un PDF ou une image de facture a importer.",
    };
  }
  if (value === "document_upload_failed") {
    return {
      kind: "technical",
      text: "Import impossible. Verifie le fichier, puis reessaie.",
    };
  }
  if (value === "invoice_validated") {
    return { kind: "success", text: "Facture validee." };
  }
  if (value === "invoice_updated") {
    return { kind: "success", text: "Facture modifiee." };
  }
  if (value === "invoice_archived") {
    return { kind: "success", text: "Facture archivee." };
  }
  if (value === "invoice_validation_failed") {
    return { kind: "review", text: "La facture ne peut pas encore etre validee." };
  }
  if (value === "invoice_missing_line") {
    return { kind: "review", text: "Ajoute au moins une ligne de facture." };
  }
  if (value === "invoice_incomplete_line") {
    return {
      kind: "review",
      text: "Complete chaque ligne commencee: description, TVA et montant HT.",
    };
  }
  if (value === "invalid_sales") {
    return {
      kind: "review",
      text: "Les ventes sont incoherentes: HT + TVA doit egaler TTC.",
    };
  }
  if (value === "backend_unavailable") {
    return {
      kind: "technical",
      text: "Backend indisponible. Lance FastAPI puis recharge la page.",
    };
  }
  if (value?.startsWith("api_error_")) {
    return {
      kind: "technical",
      text: "L API a refuse la demande. Verifie les montants saisis.",
    };
  }
  return null;
}
