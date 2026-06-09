import {
  getImportedInvoicesToReview,
  getInvoices,
  invoiceCsvExportUrl,
  invoiceXlsxExportUrl,
} from "@/lib/api";
import { requireAuth } from "@/lib/session";
import {
  ApiErrorNotice,
  AppShell,
  DocumentUploadForm,
  InvoiceForm,
  InvoiceList,
  StatusMessageBanner,
} from "@/app/ui";
import {
  SearchParams,
  currentMonth,
  firstParam,
  monthToDate,
  statusMessage,
} from "@/app/pageUtils";

export const dynamic = "force-dynamic";

export default async function InvoicesPage({
  searchParams,
}: {
  searchParams: SearchParams;
}) {
  await requireAuth();

  const params = await searchParams;
  const period = firstParam(params, "period", currentMonth());
  const openingCash = firstParam(params, "openingCash", "0");
  const periodStart = monthToDate(period);
  const message = statusMessage(firstParam(params, "message", ""));
  const [invoices, reviewInboxInvoices] = await Promise.all([
    getInvoices(periodStart),
    getImportedInvoicesToReview(),
  ]);

  return (
    <AppShell
      active="invoices"
      openingCash={openingCash}
      period={period}
      title="Factures"
    >
      {message ? <StatusMessageBanner message={message} /> : null}

      <section className="grid gap-6 lg:grid-cols-2">
        <DocumentUploadForm openingCash={openingCash} period={period} />
        <InvoiceForm openingCash={openingCash} period={period} />
      </section>

      <ApiErrorNotice
        error={reviewInboxInvoices.error}
        label="les factures importees a traiter"
      />
      <ApiErrorNotice error={invoices.error} label="les factures du mois" />

      <InvoiceList
        emptyText="Aucune facture importee a traiter."
        invoices={reviewInboxInvoices.data ?? []}
        openingCash={openingCash}
        period={period}
        title="Factures importees a traiter"
      />
      <InvoiceList
        csvExportUrl={invoiceCsvExportUrl(periodStart)}
        emptyText="Aucune facture pour ce mois."
        invoices={invoices.data ?? []}
        openingCash={openingCash}
        period={period}
        title="Factures du mois"
        xlsxExportUrl={invoiceXlsxExportUrl(periodStart)}
      />
    </AppShell>
  );
}
