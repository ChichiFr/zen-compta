export function noteLabel(note: string) {
  if (note === "monthly_sales_missing") {
    return "CA mensuel non saisi: la performance utilise 0 EUR de ventes.";
  }
  if (note === "cash_flow_inputs_missing") {
    return "Flux salaires, charges, investissements et emprunts non saisis: ils valent 0 EUR.";
  }
  if (note === "forecast_operating_costs_ratio_missing") {
    return "Charges fournisseurs insuffisantes: la prevision ne peut pas encore estimer les couts d exploitation variables.";
  }
  return note;
}

export function riskLabel(risk: "ok" | "warning" | "critical") {
  if (risk === "critical") {
    return "Critique";
  }
  if (risk === "warning") {
    return "Attention";
  }
  return "OK";
}

export function riskClass(risk: "ok" | "warning" | "critical") {
  if (risk === "critical") {
    return "text-rose-700";
  }
  if (risk === "warning") {
    return "text-amber-700";
  }
  return "text-emerald-700";
}

export function runwayLabel(months: number, hasCriticalMonth: boolean) {
  if (!hasCriticalMonth) {
    return `au moins ${months} mois`;
  }
  return `${months} mois`;
}
