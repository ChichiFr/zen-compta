export function formatMoney(value: string) {
  const amount = Number(value);
  if (!Number.isFinite(amount)) {
    return `${value} EUR`;
  }
  return new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "EUR",
  }).format(amount);
}

export function formatMonth(value: string) {
  return new Intl.DateTimeFormat("fr-FR", {
    month: "long",
    year: "numeric",
  }).format(new Date(`${value}T00:00:00`));
}
