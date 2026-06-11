export function MoneyInput({
  defaultValue,
  label,
  max,
  name,
  required = true,
}: {
  defaultValue: string;
  label: string;
  max?: string;
  name: string;
  required?: boolean;
}) {
  return (
    <label className="text-sm font-medium text-slate-600">
      {label}
      <input
        className="mt-1 block h-10 w-full rounded-md border border-slate-300 px-3 text-slate-950"
        defaultValue={defaultValue}
        max={max}
        min="0"
        name={name}
        required={required}
        step="0.01"
        type="number"
      />
    </label>
  );
}
