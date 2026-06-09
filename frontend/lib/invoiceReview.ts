export type InvoiceReviewKind = "important" | "ai" | "technical" | "review";

export type InvoiceReviewMessage = {
  code: string;
  kind: InvoiceReviewKind;
  text: string;
};

type ReviewReasonCopy = {
  kind: InvoiceReviewKind;
  text: string;
};

const REVIEW_REASON_COPY: Record<string, ReviewReasonCopy> = {
  invalid_invoice_date: {
    kind: "important",
    text: "La date extraite est invalide ou hors plage.",
  },
  invoice_total_ht_mismatch: {
    kind: "important",
    text: "Le total HT extrait ne correspond pas a la somme des lignes.",
  },
  invoice_total_tva_mismatch: {
    kind: "important",
    text: "Le total TVA extrait ne correspond pas a la somme des lignes.",
  },
  invoice_total_ttc_mismatch: {
    kind: "important",
    text: "Le total TTC extrait ne correspond pas a la somme des lignes.",
  },
  ttc_amount_mismatch: {
    kind: "important",
    text: "Le TTC de la ligne ne correspond pas a HT + TVA.",
  },
  unknown_category: {
    kind: "important",
    text: "La categorie proposee par l IA n est pas reconnue.",
  },
  vat_amount_mismatch: {
    kind: "important",
    text: "La TVA extraite ne correspond pas au montant HT et au taux.",
  },
  ai_low_confidence: {
    kind: "ai",
    text: "Confiance IA faible sur cette ligne.",
  },
};

export function invoiceReviewMessages(
  value: string | null,
): InvoiceReviewMessage[] {
  if (!value) {
    return [];
  }

  return value
    .split(",")
    .map((reason) => reason.trim())
    .filter(Boolean)
    .map((reason) => {
      const copy = REVIEW_REASON_COPY[reason];
      if (copy) {
        return {
          code: reason,
          kind: copy.kind,
          text: copy.text,
        };
      }

      return {
        code: reason,
        kind: "review",
        text: humanizeReviewReason(reason),
      };
    });
}

export function invoiceReviewSummary(
  lines: { needs_review_reason: string | null }[],
) {
  const messages = lines.flatMap((line) =>
    invoiceReviewMessages(line.needs_review_reason),
  );

  return {
    messages,
    important: messages.filter((message) => message.kind === "important").length,
    ai: messages.filter((message) => message.kind === "ai").length,
    technical: messages.filter((message) => message.kind === "technical").length,
    review: messages.filter((message) => message.kind === "review").length,
  };
}

function humanizeReviewReason(reason: string) {
  return reason.replace(/_/g, " ");
}
