import {
  startBankConnectionAction,
  syncBankTransactionsAction,
} from "@/app/actions";

export function BankConnectButton() {
  return (
    <form action={startBankConnectionAction}>
      <button
        className="rounded-md bg-slate-950 px-4 py-2 text-sm font-semibold text-white"
        type="submit"
      >
        Connecter une banque
      </button>
    </form>
  );
}

export function BankSyncButton({
  connectionId,
  openingCash,
  period,
}: {
  connectionId: string;
  openingCash: string;
  period: string;
}) {
  return (
    <form action={syncBankTransactionsAction}>
      <input name="connection_id" type="hidden" value={connectionId} />
      <input name="opening_cash" type="hidden" value={openingCash} />
      <input name="period" type="hidden" value={period} />
      <button
        className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-900"
        type="submit"
      >
        Synchroniser
      </button>
    </form>
  );
}
