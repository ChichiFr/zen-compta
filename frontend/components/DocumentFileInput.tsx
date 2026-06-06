"use client";

import { useId, useState } from "react";

export function DocumentFileInput() {
  const inputId = useId();
  const [filename, setFilename] = useState("Aucun fichier selectionne");

  return (
    <div className="mt-1 flex flex-col gap-2 sm:flex-row sm:items-center">
      <label
        className="inline-flex h-10 cursor-pointer items-center justify-center rounded-md bg-slate-100 px-4 text-sm font-semibold text-slate-900 hover:bg-slate-200"
        htmlFor={inputId}
      >
        Choisir une facture
      </label>
      <span className="min-w-0 text-sm text-slate-500">{filename}</span>
      <input
        accept="application/pdf,image/jpeg,image/png,image/webp"
        className="sr-only"
        id={inputId}
        name="invoice_file"
        onChange={(event) => {
          setFilename(event.target.files?.[0]?.name ?? "Aucun fichier selectionne");
        }}
        required
        type="file"
      />
    </div>
  );
}
