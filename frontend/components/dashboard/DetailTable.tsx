import { SimpleTable } from "@/components/dashboard/SimpleTable";
import { formatMoney } from "@/lib/format";
import type { DashboardSummary } from "@/types/api";

export function DetailTable({ summary }: { summary: DashboardSummary }) {
  const rows = [
    ["Ventes HT", formatMoney(summary.sales_ht)],
    ["TVA collectee", formatMoney(summary.vat_collected)],
    ["Ventes TTC", formatMoney(summary.sales_ttc)],
    ["Factures validees HT", formatMoney(summary.validated_invoices_ht)],
    ["TVA deductible", formatMoney(summary.vat_deductible)],
    ["Factures validees TTC", formatMoney(summary.validated_invoices_ttc)],
    ["Flux mensuels sortants", formatMoney(summary.monthly_outflows)],
  ];

  return <SimpleTable rows={rows} title="Lecture comptable du mois" />;
}
