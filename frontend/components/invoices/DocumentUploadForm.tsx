import { uploadDocumentAction } from "@/app/actions";
import { DocumentFileInput } from "@/components/invoices/DocumentFileInput";

export function DocumentUploadForm({
  openingCash,
  period,
}: {
  openingCash: string;
  period: string;
}) {
  return (
    <form
      action={uploadDocumentAction}
      className="rounded-md border border-slate-200 bg-white px-5 py-4"
    >
      <input name="return_to" type="hidden" value="/invoices" />
      <input name="period" type="hidden" value={period} />
      <input name="opening_cash" type="hidden" value={openingCash} />
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h2 className="text-base font-semibold">Importer une facture</h2>
          <p className="mt-1 text-sm text-slate-500">
            PDF ou image. Une facture a la fois.
          </p>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <DocumentFileInput />
          <button className="h-10 rounded-md bg-slate-950 px-4 text-sm font-semibold text-white">
          Importer
          </button>
        </div>
      </div>
    </form>
  );
}
