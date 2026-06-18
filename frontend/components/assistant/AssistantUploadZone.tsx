"use client";

import { useRef, useState } from "react";

import { assistantUploadAction } from "@/app/assistant/actions";

type UploadState =
  | { step: "idle" }
  | { step: "selected"; fileName: string }
  | { step: "uploading" }
  | { step: "done"; summary: string; needsAction: boolean }
  | { step: "error"; message: string };

export function AssistantUploadZone({
  openingCash,
  period,
}: {
  openingCash: string;
  period: string;
}) {
  const [state, setState] = useState<UploadState>({ step: "idle" });
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function handleFile(file: File) {
    const allowed = [
      "application/pdf",
      "image/jpeg",
      "image/png",
      "image/webp",
    ];
    if (!allowed.includes(file.type)) {
      setState({
        step: "error",
        message: "Format non supporte. Utilisez un PDF ou une image.",
      });
      return;
    }
    setState({ step: "selected", fileName: file.name });
  }

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const file = formData.get("file");
    if (!(file instanceof File) || file.size === 0) {
      setState({
        step: "error",
        message: "Choisissez un fichier.",
      });
      return;
    }
    setState({ step: "uploading" });
    const result = await assistantUploadAction(formData);
    if (result.error) {
      setState({ step: "error", message: result.error });
    } else if (result.data) {
      setState({
        step: "done",
        summary: result.data.summary_text,
        needsAction: result.data.needs_action,
      });
    }
  }

  return (
    <section className="rounded-xl border-2 border-dashed border-slate-300 bg-white p-8 text-center">
      <form onSubmit={handleSubmit}>
        <input name="period" type="hidden" value={period} />
        <input name="opening_cash" type="hidden" value={openingCash} />

        <div
          className={`rounded-lg p-10 transition-colors ${
            dragOver ? "border-emerald-500 bg-emerald-50" : "bg-slate-50"
          }`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            const file = e.dataTransfer.files[0];
            if (file) {
              handleFile(file);
              const dt = new DataTransfer();
              dt.items.add(file);
              if (inputRef.current) {
                inputRef.current.files = dt.files;
              }
            }
          }}
        >
          <p className="text-2xl font-semibold text-slate-700">
            Glissez votre facture ici
          </p>
          <p className="mt-2 text-base text-slate-500">
            ou cliquez pour choisir un fichier (PDF, JPEG, PNG)
          </p>
          <input
            ref={inputRef}
            accept=".pdf,.jpg,.jpeg,.png,.webp"
            className="hidden"
            id="assistant-file"
            name="file"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleFile(file);
            }}
            type="file"
          />
          <label
            className="mt-4 inline-block cursor-pointer rounded-md bg-slate-950 px-6 py-3 text-base font-semibold text-white"
            htmlFor="assistant-file"
          >
            Choisir un fichier
          </label>
        </div>

        {state.step === "selected" && (
          <div className="mt-4 flex flex-col items-center gap-3">
            <p className="text-base text-slate-700">
              Fichier : <span className="font-semibold">{state.fileName}</span>
            </p>
            <button
              className="rounded-md bg-emerald-700 px-6 py-3 text-base font-semibold text-white"
              type="submit"
            >
              Envoyer la facture
            </button>
          </div>
        )}

        {state.step === "uploading" && (
          <p className="mt-4 text-base text-slate-500">
            Analyse en cours...
          </p>
        )}

        {state.step === "done" && (
          <div className="mx-auto mt-4 max-w-xl rounded-md border border-emerald-200 bg-emerald-50 p-5 text-left text-sm text-emerald-900">
            <p className="font-semibold">
              Facture importee
            </p>
            <p className="mt-2">{state.summary}</p>
            {state.needsAction && (
              <p className="mt-2 text-amber-700">
                Des points sont a verifier avant de valider cette facture.
              </p>
            )}
            <button
              className="mt-3 text-sm font-semibold text-emerald-700 underline-offset-4 hover:underline"
              onClick={() => {
                setState({ step: "idle" });
                if (inputRef.current) inputRef.current.value = "";
              }}
              type="button"
            >
              Importer une autre facture
            </button>
          </div>
        )}

        {state.step === "error" && (
          <div className="mx-auto mt-4 max-w-xl rounded-md border border-rose-200 bg-rose-50 p-5 text-left text-sm text-rose-900">
            <p>{state.message}</p>
            <button
              className="mt-2 text-sm font-semibold text-rose-700 underline-offset-4 hover:underline"
              onClick={() => setState({ step: "idle" })}
              type="button"
            >
              Reessayer
            </button>
          </div>
        )}
      </form>
    </section>
  );
}
