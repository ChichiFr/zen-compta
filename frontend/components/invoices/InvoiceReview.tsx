import {
  invoiceReviewMessages,
  invoiceReviewSummary,
} from "@/lib/invoiceReview";
import type {
  InvoiceReviewKind,
  InvoiceReviewMessage,
} from "@/lib/invoiceReview";
import type { Invoice } from "@/types/api";

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

export function InvoiceReviewPanel({ invoice }: { invoice: Invoice }) {
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

export function LineReviewMessages({ reason }: { reason: string | null }) {
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

export function hasVisibleValidationBlocker(invoice: Invoice) {
  return (
    !invoice.supplier_name.trim() ||
    !invoice.invoice_date ||
    invoice.lines.length === 0 ||
    invoice.lines.some(
      (line) => invoiceReviewMessages(line.needs_review_reason).length > 0,
    )
  );
}
