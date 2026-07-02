import type { BankTransaction } from "@/types/api";

export function TransactionList({
  transactions,
}: {
  transactions: BankTransaction[];
}) {
  if (transactions.length === 0) {
    return (
      <section className="rounded-md border border-slate-200 bg-white p-5">
        <h2 className="text-base font-semibold">Transactions</h2>
        <p className="mt-2 text-sm text-slate-500">
          Aucune transaction bancaire importee pour cette connexion.
        </p>
      </section>
    );
  }

  return (
    <section className="rounded-md border border-slate-200 bg-white">
      <div className="border-b border-slate-200 px-5 py-4">
        <h2 className="text-base font-semibold">Transactions</h2>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[680px] text-left text-sm">
          <thead className="bg-slate-50 text-xs font-semibold uppercase text-slate-500">
            <tr>
              <th className="px-5 py-3">Date</th>
              <th className="px-5 py-3">Description</th>
              <th className="px-5 py-3 text-right">Montant</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {transactions.map((transaction) => {
              const amount = Number(transaction.amount);
              const counterparty =
                transaction.creditor_name ?? transaction.debtor_name ?? "";
              return (
                <tr key={transaction.id}>
                  <td className="whitespace-nowrap px-5 py-3 text-slate-600">
                    {formatDate(transaction.booking_date)}
                  </td>
                  <td className="px-5 py-3">
                    <p className="font-medium text-slate-950">
                      {transaction.description || "Transaction bancaire"}
                    </p>
                    {counterparty ? (
                      <p className="mt-1 text-xs text-slate-500">
                        {counterparty}
                      </p>
                    ) : null}
                  </td>
                  <td
                    className={`whitespace-nowrap px-5 py-3 text-right font-semibold ${
                      amount >= 0 ? "text-emerald-700" : "text-rose-700"
                    }`}
                  >
                    {formatMoney(amount, transaction.currency)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function formatDate(dateText: string) {
  const [year, month, day] = dateText.split("-");
  if (!year || !month || !day) {
    return dateText;
  }
  return `${day}/${month}/${year}`;
}

function formatMoney(amount: number, currency: string) {
  return new Intl.NumberFormat("fr-FR", {
    currency,
    style: "currency",
  }).format(amount);
}
