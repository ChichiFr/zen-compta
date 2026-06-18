import {
  SimpleTable,
  type SimpleTableRow,
} from "@/components/dashboard/SimpleTable";
import { formatMoney } from "@/lib/format";
import { noteLabel } from "@/lib/labels";
import type { MonthlyPerformanceSummary } from "@/types/api";

const FIXED_CHARGES_LABELS: { code: string; label: string }[] = [
  { code: "rent", label: "Loyer" },
  { code: "electricity", label: "Electricite" },
  { code: "water", label: "Eau" },
  { code: "gas", label: "Gaz" },
  { code: "phone_internet", label: "Telephone & Internet" },
  { code: "maintenance", label: "Entretiens" },
];

const EXTERNAL_PURCHASES_LABELS: { code: string; label: string }[] = [
  { code: "purchase_transport", label: "Transports sur achats" },
  { code: "cleaning_products", label: "Produits entretien" },
  { code: "hygiene_products", label: "Produits hygiene" },
  { code: "administrative_supplies", label: "Fournitures administratives" },
  { code: "fuel_purchases", label: "Carburant" },
  { code: "business_meals", label: "Repas professionnel" },
  { code: "tips_donations", label: "Pourboires / dons" },
  { code: "point_of_sale_advertising", label: "Pub. sur point de vente" },
  { code: "discount", label: "Remise" },
  { code: "other", label: "Autre" },
];

function percentageOf(value: string, total: string): string {
  const valueNum = Number(value);
  const totalNum = Number(total);
  if (!Number.isFinite(valueNum) || !Number.isFinite(totalNum) || totalNum === 0) {
    return "";
  }
  const ratio = (valueNum / totalNum) * 100;
  return `${ratio.toFixed(1)}%`;
}

function breakdownSubRows(
  breakdown: Record<string, string>,
  labels: { code: string; label: string }[],
  salesHt: string,
): SimpleTableRow[] {
  const rows: SimpleTableRow[] = [];
  for (const item of labels) {
    const raw = breakdown[item.code] ?? "0";
    if (Number(raw) <= 0) {
      continue;
    }
    rows.push({
      label: item.label,
      value: formatMoney(raw),
      percentage: percentageOf(raw, salesHt),
      indent: true,
    });
  }
  return rows;
}

export function PerformanceAndCashFlowTables({
  compact = false,
  summary,
}: {
  compact?: boolean;
  summary: MonthlyPerformanceSummary;
}) {
  const salesHt = summary.performance.sales_ht;
  const perf = summary.performance;

  const performanceRows: SimpleTableRow[] = [
    {
      label: "CA HT",
      value: formatMoney(perf.sales_ht),
      percentage: "100,0%",
      emphasis: true,
    },
    {
      label: "Matieres premieres HT",
      value: formatMoney(perf.raw_materials_ht),
      percentage: percentageOf(perf.raw_materials_ht, salesHt),
    },
    {
      label: "Emballages HT",
      value: formatMoney(perf.packaging_ht),
      percentage: percentageOf(perf.packaging_ht, salesHt),
    },
    {
      label: "Salaires & charges sociales",
      value: formatMoney(perf.salaries_total_ht),
      percentage: percentageOf(perf.salaries_total_ht, salesHt),
    },
    {
      label: "Charges fixes HT",
      value: formatMoney(perf.fixed_charges_ht),
      percentage: percentageOf(perf.fixed_charges_ht, salesHt),
    },
    ...breakdownSubRows(perf.fixed_charges_breakdown, FIXED_CHARGES_LABELS, salesHt),
    {
      label: "Achats externes HT",
      value: formatMoney(perf.external_purchases_ht),
      percentage: percentageOf(perf.external_purchases_ht, salesHt),
    },
    ...breakdownSubRows(
      perf.external_purchases_breakdown,
      EXTERNAL_PURCHASES_LABELS,
      salesHt,
    ),
    {
      label: "EBE Cash",
      value: formatMoney(perf.ebe_cash),
      percentage: percentageOf(perf.ebe_cash, salesHt),
      emphasis: true,
    },
  ];

  const cashFlowRows: SimpleTableRow[] = [
    {
      label: "Investissements cash",
      value: formatMoney(summary.non_operating_cash_flow.investments_cash),
    },
    {
      label: "Remboursements emprunts cash",
      value: formatMoney(summary.non_operating_cash_flow.loan_repayments_cash),
    },
    {
      label: "TVA a payer estimee",
      value: formatMoney(summary.non_operating_cash_flow.vat_payable_estimate),
    },
    {
      label: "Credit TVA estime",
      value: formatMoney(summary.non_operating_cash_flow.vat_credit_estimate),
    },
    {
      label: "Total hors exploitation",
      value: formatMoney(summary.non_operating_cash_flow.total_cash_outflow),
      emphasis: true,
    },
  ];

  const performanceCompactRows: SimpleTableRow[] = [
    performanceRows[0],
    ...performanceRows.slice(1, 4),
    performanceRows[performanceRows.length - 1],
  ];

  return (
    <section className="grid gap-6 lg:grid-cols-2">
      <SimpleTable
        rows={compact ? performanceCompactRows : performanceRows}
        showPercentColumn
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
