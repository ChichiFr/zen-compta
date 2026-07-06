import Link from "next/link";

import {
  getBankAnomaliesSummary,
  getBankMatchSuggestions,
  listBankConnections,
  listBankTransactions,
  listUnmatchedInvoices,
  listUnpaidInvoices,
} from "@/lib/api";
import { requireAuth } from "@/lib/session";
import {
  SearchParams,
  currentMonth,
  firstParam,
  statusMessage,
} from "@/app/pageUtils";
import {
  BankConnectButton,
  BankSyncButton,
} from "@/components/bank/BankConnectButton";
import { AnomaliesCard } from "@/components/bank/AnomaliesCard";
import { AnomaliesDetail } from "@/components/bank/AnomaliesDetail";
import { MatchSuggestionsPanel } from "@/components/bank/MatchSuggestionsPanel";
import { PlaidConnectSection } from "@/components/bank/PlaidConnectSection";
import { TransactionList } from "@/components/bank/TransactionList";
import { ApiErrorNotice } from "@/components/layout/ApiErrorNotice";
import { AppShell } from "@/components/layout/AppShell";
import { StatusMessageBanner } from "@/components/layout/StatusMessageBanner";
import type {
  BankConnection,
  BankConnectionStatus,
  BankUnpaidInvoice,
} from "@/types/api";

export const dynamic = "force-dynamic";

const STATUS_LABELS: Record<BankConnectionStatus, string> = {
  created: "CREEE",
  expired: "EXPIREE",
  linked: "LIEE",
  revoked: "REVOQUEE",
};

export default async function BankPage({
  searchParams,
}: {
  searchParams: SearchParams;
}) {
  await requireAuth();

  const params = await searchParams;
  const period = firstParam(params, "period", currentMonth());
  const openingCash = firstParam(params, "openingCash", "0");
  const selectedConnectionId = firstParam(params, "connection", "");
  const anomaliesActive = firstParam(params, "anomalies", "") === "invoices";
  const message = statusMessage(firstParam(params, "message", ""));
  const isPlaidProvider = process.env.NEXT_PUBLIC_BANK_PROVIDER === "plaid";
  const [connectionsResult, anomaliesSummaryResult] = await Promise.all([
    listBankConnections(),
    getBankAnomaliesSummary(),
  ]);
  const connections = connectionsResult.data ?? [];
  const hasLinkedConnection = connections.some(
    (connection) => connection.status === "linked",
  );
  const activeConnection =
    connectionById(connections, selectedConnectionId) ??
    connections.find((connection) => connection.status === "linked") ??
    null;
  const transactionsResult = activeConnection?.status === "linked"
    ? await listBankTransactions(activeConnection.id)
    : { data: [], error: null };
  const matchTransactionId = firstParam(params, "match", "");
  const matchTransaction =
    (transactionsResult.data ?? []).find(
      (transaction) => transaction.id === matchTransactionId,
    ) ?? null;
  const showAll = firstParam(params, "matchAll", "") === "1";
  const [suggestionsResult, allInvoicesResult] = matchTransaction
    ? await Promise.all([
        getBankMatchSuggestions(matchTransaction.id),
        showAll ? listUnmatchedInvoices() : Promise.resolve(null),
      ])
    : [null, null];
  let anomaliesDetailError: string | null = null;
  let unpaidInvoices: BankUnpaidInvoice[] = [];
  if (anomaliesActive) {
    const result = await listUnpaidInvoices();
    anomaliesDetailError = result.error;
    unpaidInvoices = result.data ?? [];
  }

  return (
    <AppShell
      active="bank"
      openingCash={openingCash}
      period={period}
      title="Banque"
    >
      {message ? <StatusMessageBanner message={message} /> : null}
      <ApiErrorNotice error={connectionsResult.error} label="les connexions" />

      <section className="rounded-md border border-slate-200 bg-white">
        <div className="flex flex-col justify-between gap-4 border-b border-slate-200 px-5 py-4 sm:flex-row sm:items-center">
          <div>
            <h2 className="text-base font-semibold">Connexions</h2>
            <p className="mt-1 text-sm text-slate-500">
              {isPlaidProvider
                ? "Connexion sandbox Plaid pour le POC bancaire."
                : "Connexion sandbox GoCardless pour le POC bancaire."}
            </p>
          </div>
          {connections.length === 0 || !hasLinkedConnection ? (
            isPlaidProvider ? (
              <PlaidConnectSection />
            ) : (
              <BankConnectButton />
            )
          ) : null}
        </div>

        {connections.length === 0 ? (
          <div className="px-5 py-6 text-sm text-slate-500">
            Aucune banque connectee.
          </div>
        ) : (
          <div className="divide-y divide-slate-200">
            {connections.map((connection) => (
              <ConnectionRow
                connection={connection}
                isActive={connection.id === activeConnection?.id}
                key={connection.id}
                openingCash={openingCash}
                period={period}
              />
            ))}
          </div>
        )}
      </section>

      <ApiErrorNotice
        error={anomaliesSummaryResult.error}
        label="les alertes bancaires"
      />
      <AnomaliesCard
        active={anomaliesActive}
        openingCash={openingCash}
        period={period}
        summary={
          anomaliesSummaryResult.data ?? {
            unpaid_invoices_count: 0,
          }
        }
      />

      {activeConnection?.status === "linked" ? (
        <>
          <ApiErrorNotice
            error={transactionsResult.error}
            label="les transactions bancaires"
          />
          <ApiErrorNotice
            error={anomaliesDetailError}
            label="le detail des alertes bancaires"
          />
          {anomaliesActive ? (
            <AnomaliesDetail invoices={unpaidInvoices} />
          ) : null}
          {matchTransaction ? (
            <MatchSuggestionsPanel
              allInvoices={allInvoicesResult?.data ?? null}
              connectionId={activeConnection.id}
              openingCash={openingCash}
              period={period}
              showAll={showAll}
              suggestions={suggestionsResult?.data ?? []}
              transaction={matchTransaction}
            />
          ) : null}
          <TransactionList
            connectionId={activeConnection.id}
            openingCash={openingCash}
            period={period}
            transactions={transactionsResult.data ?? []}
          />
        </>
      ) : activeConnection ? (
        <section className="rounded-md border border-amber-200 bg-amber-50 p-5 text-sm text-amber-900">
          Cette connexion bancaire n est pas encore finalisee.
        </section>
      ) : null}
    </AppShell>
  );
}

function ConnectionRow({
  connection,
  isActive,
  openingCash,
  period,
}: {
  connection: BankConnection;
  isActive: boolean;
  openingCash: string;
  period: string;
}) {
  const params = new URLSearchParams({
    connection: connection.id,
    openingCash,
    period,
  });

  return (
    <div
      className={`flex flex-col gap-4 px-5 py-4 lg:flex-row lg:items-center lg:justify-between ${
        isActive ? "bg-slate-50" : ""
      }`}
    >
      <div>
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="font-semibold text-slate-950">
            {connection.institution_name}
          </h3>
          <span className="rounded-md border border-slate-300 px-2 py-1 text-xs font-semibold text-slate-600">
            {STATUS_LABELS[connection.status]}
          </span>
        </div>
        <p className="mt-1 text-sm text-slate-500">
          Provider {connection.provider} - creee le{" "}
          {new Date(connection.created_at).toLocaleDateString("fr-FR")}
        </p>
      </div>
      <div className="flex flex-wrap gap-2">
        <Link
          className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-900"
          href={`/bank?${params.toString()}`}
        >
          Voir
        </Link>
        {connection.status === "linked" ? (
          <BankSyncButton
            connectionId={connection.id}
            openingCash={openingCash}
            period={period}
          />
        ) : null}
      </div>
    </div>
  );
}

function connectionById(connections: BankConnection[], connectionId: string) {
  return connections.find((connection) => connection.id === connectionId);
}
