"use client";

import { useState } from "react";

import { categorizeBankTransactionAction } from "@/app/actions";
import { INVOICE_CATEGORIES } from "@/lib/invoiceCategories";
import type { BankTransaction } from "@/types/api";

export function CategorizeTransactionButton({
  connectionId,
  openingCash,
  period,
  transaction,
}: {
  connectionId: string;
  openingCash: string;
  period: string;
  transaction: BankTransaction;
}) {
  const [open, setOpen] = useState(false);
  const defaultPattern = transaction.description.slice(0, 30).trim();

  if (!open) {
    return (
      <button
        className="rounded-md border border-slate-300 bg-white px-2 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50"
        onClick={() => setOpen(true)}
        type="button"
      >
        Categoriser
      </button>
    );
  }

  return (
    <form
      action={categorizeBankTransactionAction}
      className="flex flex-col gap-2 rounded-md border border-slate-200 bg-slate-50 p-3"
    >
      <input name="transaction_id" type="hidden" value={transaction.id} />
      <input name="connection_id" type="hidden" value={connectionId} />
      <input name="period" type="hidden" value={period} />
      <input name="opening_cash" type="hidden" value={openingCash} />

      <label className="text-xs font-medium text-slate-600">
        Categorie
        <select
          className="mt-1 block w-full rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-950"
          defaultValue=""
          name="category_code"
          required
        >
          <option disabled value="">
            Choisir une categorie
          </option>
          {INVOICE_CATEGORIES.map(([code, label]) => (
            <option key={code} value={code}>
              {label}
            </option>
          ))}
        </select>
      </label>

      <label className="flex items-center gap-2 text-xs text-slate-600">
        <input name="create_rule" type="checkbox" />
        Appliquer aux transactions similaires (cree une regle)
      </label>

      <label className="text-xs font-medium text-slate-600">
        Motif de la regle
        <input
          className="mt-1 block w-full rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-950"
          defaultValue={defaultPattern}
          name="rule_pattern"
          type="text"
        />
      </label>

      <div className="flex gap-2">
        <button
          className="rounded-md bg-slate-950 px-3 py-1.5 text-xs font-semibold text-white"
          type="submit"
        >
          Enregistrer
        </button>
        <button
          className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700"
          onClick={() => setOpen(false)}
          type="button"
        >
          Annuler
        </button>
      </div>
    </form>
  );
}
