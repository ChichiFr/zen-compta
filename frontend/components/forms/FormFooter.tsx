export function FormFooter({ label }: { label: string }) {
  return (
    <div className="mt-5 flex justify-end">
      <button className="rounded-md bg-emerald-700 px-4 py-2 text-sm font-semibold text-white">
        {label}
      </button>
    </div>
  );
}
