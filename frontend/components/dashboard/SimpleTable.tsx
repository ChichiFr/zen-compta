export type SimpleTableRow = {
  label: string;
  value: string;
  percentage?: string;
  indent?: boolean;
  emphasis?: boolean;
};

export type SimpleTableInput = SimpleTableRow | string[];

function normalize(row: SimpleTableInput): SimpleTableRow {
  if (Array.isArray(row)) {
    return { label: row[0], value: row[1] ?? "" };
  }
  return row;
}

export function SimpleTable({
  rows,
  title,
  showPercentColumn = false,
}: {
  rows: SimpleTableInput[];
  title: string;
  showPercentColumn?: boolean;
}) {
  const normalized = rows.map(normalize);
  const gridCols = showPercentColumn
    ? "grid-cols-[minmax(0,1fr)_120px_60px]"
    : "grid-cols-[minmax(0,1fr)_150px]";

  return (
    <article className="rounded-md border border-slate-200 bg-white">
      <div className="border-b border-slate-200 px-5 py-4">
        <h2 className="text-base font-semibold">{title}</h2>
      </div>
      <dl className="divide-y divide-slate-200">
        {normalized.map((row, index) => {
          const isLast = index === normalized.length - 1;
          const isEmphasis = row.emphasis ?? isLast;
          const rowClass = [
            "grid",
            gridCols,
            "gap-4 px-5 py-3",
            isEmphasis ? "bg-slate-50 font-semibold" : "",
            row.indent ? "text-slate-500" : "",
          ]
            .filter(Boolean)
            .join(" ");
          const labelClass = [
            "text-sm",
            row.indent ? "pl-5 text-slate-500" : "text-slate-600",
          ].join(" ");
          return (
            <div className={rowClass} key={`${row.label}-${index}`}>
              <dt className={labelClass}>{row.label}</dt>
              <dd className="text-right text-sm font-semibold text-slate-950">
                {row.value}
              </dd>
              {showPercentColumn ? (
                <dd className="text-right text-sm text-slate-500">
                  {row.percentage ?? ""}
                </dd>
              ) : null}
            </div>
          );
        })}
      </dl>
    </article>
  );
}
