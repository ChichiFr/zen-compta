import Link from "next/link";
import type { ReactNode } from "react";

import { logoutAction } from "@/app/actions";

type AppShellProps = {
  active: "dashboard" | "invoices" | "cash-flow" | "forecast" | "assistant";
  children: ReactNode;
  openingCash: string;
  period: string;
  preservedQueryParams?: Record<string, string>;
  title: string;
};

const NAV_ITEMS = [
  { key: "dashboard", label: "Tableau de bord", href: "/" },
  { key: "invoices", label: "Factures", href: "/invoices" },
  { key: "cash-flow", label: "Cash-flow", href: "/cash-flow" },
  { key: "forecast", label: "Prevision", href: "/forecast" },
  { key: "assistant", label: "Assistant", href: "/assistant" },
] as const;

export function AppShell({
  active,
  children,
  openingCash,
  period,
  preservedQueryParams = {},
  title,
}: AppShellProps) {
  const preservedQuery = new URLSearchParams(preservedQueryParams).toString();
  const preservedSuffix = preservedQuery ? `&${preservedQuery}` : "";

  return (
    <main className="min-h-screen bg-[#f6f7f4] text-slate-950">
      <section className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-5 py-6 sm:px-6 lg:px-8">
        <header className="flex flex-col gap-5 border-b border-slate-200 pb-5">
          <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
            <div>
              <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">
                Zen Compta
              </p>
              <h1 className="mt-2 text-3xl font-semibold">{title}</h1>
            </div>
            <div className="flex flex-col gap-3">
              <form className="flex flex-col gap-3 sm:flex-row" method="get">
                <label className="text-sm font-medium text-slate-600">
                  Mois
                  <input
                    className="mt-1 block h-10 rounded-md border border-slate-300 bg-white px-3 text-slate-950"
                    defaultValue={period}
                    name="period"
                    type="month"
                  />
                </label>
                <label className="text-sm font-medium text-slate-600">
                  Tresorerie depart
                  <input
                    className="mt-1 block h-10 rounded-md border border-slate-300 bg-white px-3 text-slate-950"
                    defaultValue={openingCash}
                    min="0"
                    name="openingCash"
                    step="0.01"
                    type="number"
                  />
                </label>
                {Object.entries(preservedQueryParams).map(([key, value]) => (
                  <input key={key} name={key} type="hidden" value={value} />
                ))}
                <button className="h-10 self-end rounded-md bg-slate-950 px-4 text-sm font-semibold text-white">
                  Actualiser
                </button>
              </form>
              <form action={logoutAction} className="flex justify-end">
                <button className="text-sm font-semibold text-slate-600 underline-offset-4 hover:underline">
                  Deconnexion
                </button>
              </form>
            </div>
          </div>
          <nav className="flex flex-wrap gap-2">
            {NAV_ITEMS.map((item) => {
              const href =
                item.href === "/"
                  ? `/?period=${period}&openingCash=${openingCash}${preservedSuffix}`
                  : `${item.href}?period=${period}&openingCash=${openingCash}${preservedSuffix}`;
              return (
                <Link
                  className={`rounded-md border px-3 py-2 text-sm font-semibold ${
                    item.key === active
                      ? "border-slate-950 bg-slate-950 text-white"
                      : "border-slate-300 bg-white text-slate-800"
                  }`}
                  href={href}
                  key={item.key}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </header>
        {children}
      </section>
    </main>
  );
}
