import Link from "next/link";

export function DashboardActions({
  openingCash,
  period,
}: {
  openingCash: string;
  period: string;
}) {
  const query = `period=${period}&openingCash=${openingCash}`;
  return (
    <section className="grid gap-3 md:grid-cols-4">
      <ActionLink href={`/invoices?${query}`} label="Importer une facture" />
      <ActionLink href={`/invoices?${query}`} label="Factures a traiter" />
      <ActionLink href={`/cash-flow?${query}`} label="Ouvrir cash-flow" />
      <ActionLink href={`/forecast?${query}`} label="Ouvrir prevision" />
    </section>
  );
}

function ActionLink({ href, label }: { href: string; label: string }) {
  return (
    <Link
      className="rounded-md border border-slate-300 bg-white px-4 py-3 text-center text-sm font-semibold text-slate-900 shadow-sm"
      href={href}
    >
      {label}
    </Link>
  );
}
