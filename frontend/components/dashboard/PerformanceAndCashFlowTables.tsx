import { SimpleTable } from "@/components/dashboard/SimpleTable";
import { formatMoney } from "@/lib/format";
import { noteLabel } from "@/lib/labels";
import type { MonthlyPerformanceSummary } from "@/types/api";

export function PerformanceAndCashFlowTables({
  compact = false,
  summary,
}: {
  compact?: boolean;
  summary: MonthlyPerformanceSummary;
}) {
  const performanceRows = [
    ["CA HT", formatMoney(summary.performance.sales_ht)],
    ["Matieres premieres HT", formatMoney(summary.performance.raw_materials_ht)],
    ["Emballages HT", formatMoney(summary.performance.packaging_ht)],
    ["Salaires", formatMoney(summary.performance.salaries)],
    ["Charges sociales", formatMoney(summary.performance.social_charges)],
    [
      "Achats externes, charges et impots HT",
      formatMoney(summary.performance.external_purchases_taxes_ht),
    ],
    ["EBE Cash", formatMoney(summary.performance.ebe_cash)],
  ];
  const cashFlowRows = [
    [
      "Investissements cash",
      formatMoney(summary.non_operating_cash_flow.investments_cash),
    ],
    [
      "Remboursements emprunts cash",
      formatMoney(summary.non_operating_cash_flow.loan_repayments_cash),
    ],
    [
      "TVA a payer estimee",
      formatMoney(summary.non_operating_cash_flow.vat_payable_estimate),
    ],
    [
      "Credit TVA estime",
      formatMoney(summary.non_operating_cash_flow.vat_credit_estimate),
    ],
    [
      "Total hors exploitation",
      formatMoney(summary.non_operating_cash_flow.total_cash_outflow),
    ],
  ];

  return (
    <section className="grid gap-6 lg:grid-cols-2">
      <SimpleTable
        rows={compact ? performanceRows.slice(0, 4).concat([performanceRows[6]]) : performanceRows}
        title="Performance"
      />
      <SimpleTable
        rows={compact ? cashFlowRows.slice(1) : cashFlowRows}
        title="Flux exceptionnels / hors exploitation"
      />
      {summary.data_quality_notes.length > 0 ? (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 lg:col-span-2">
          {summary.data_quality_notes.map((note) => (
            <p key={note}>{noteLabel(note)}</p>
          ))}
        </div>
      ) : null}
    </section>
  );
}
