export function ApiErrorNotice({
  error,
  label,
}: {
  error: string | null;
  label: string;
}) {
  if (!error) {
    return null;
  }
  return (
    <section className="rounded-md border border-amber-200 bg-amber-50 p-5 text-sm text-amber-900">
      Impossible de charger {label}: {error}.
    </section>
  );
}
