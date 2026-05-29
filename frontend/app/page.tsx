export default function Home() {
  return (
    <main className="min-h-screen bg-[#f6f7f4] text-slate-950">
      <section className="mx-auto flex w-full max-w-6xl flex-col gap-8 px-6 py-8">
        <header className="flex flex-col justify-between gap-4 border-b border-slate-200 pb-6 md:flex-row md:items-center">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">
              Zen Compta
            </p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight">
              Pilotage factures, TVA et tresorerie
            </h1>
          </div>
          <button className="w-fit rounded-md bg-slate-950 px-4 py-2 text-sm font-semibold text-white">
            Importer une facture
          </button>
        </header>

        <section className="grid gap-4 md:grid-cols-3">
          {[
            ["Factures a verifier", "12", "3 avec TVA incertaine"],
            ["TVA a payer estimee", "2 670 EUR", "Collectee - deductible"],
            ["Tresorerie estimee", "50 880 EUR", "Non connectee a la banque"],
          ].map(([label, value, help]) => (
            <article
              className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm"
              key={label}
            >
              <p className="text-sm font-medium text-slate-500">{label}</p>
              <p className="mt-3 text-3xl font-semibold tracking-tight">{value}</p>
              <p className="mt-2 text-sm text-slate-500">{help}</p>
            </article>
          ))}
        </section>

        <section className="rounded-lg border border-dashed border-slate-300 bg-white p-6">
          <h2 className="text-lg font-semibold">Scaffold technique pret</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
            Cette page confirme que le frontend Next.js est initialise. Les
            prochains changements remplaceront ces donnees d&apos;exemple par
            les API FastAPI et PostgreSQL.
          </p>
        </section>
      </section>
    </main>
  );
}

