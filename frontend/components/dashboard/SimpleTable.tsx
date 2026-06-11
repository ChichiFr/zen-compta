export function SimpleTable({ rows, title }: { rows: string[][]; title: string }) {
  return (
    <article className="rounded-md border border-slate-200 bg-white">
      <div className="border-b border-slate-200 px-5 py-4">
        <h2 className="text-base font-semibold">{title}</h2>
      </div>
      <dl className="divide-y divide-slate-200">
        {rows.map(([label, value], index) => (
          <div
            className={`grid grid-cols-[minmax(0,1fr)_150px] gap-4 px-5 py-3 ${
              index === rows.length - 1 ? "bg-slate-50 font-semibold" : ""
            }`}
            key={label}
          >
            <dt className="text-sm text-slate-600">{label}</dt>
            <dd className="text-right text-sm font-semibold text-slate-950">
              {value}
            </dd>
          </div>
        ))}
      </dl>
    </article>
  );
}
