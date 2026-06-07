export const INVOICE_CATEGORIES = [
  ["raw_materials_5_5", "ACHATS MP A 5.5%"],
  ["lost_packaging_20", "EMB. PERDUS 20%"],
  ["alcohol_purchases", "ACHATS ALCOOL"],
  ["maintenance", "ENTRETIENS"],
  ["purchase_transport", "TRANSPORTS SUR ACHATS"],
  ["raw_materials_20", "ACHATS MP A 20%"],
  ["cleaning_products", "PRODUITS ENTRETIENS"],
  ["discount", "REMISE"],
  ["hygiene_products", "PRODUITS HYGIENES"],
  ["administrative_supplies", "FOURNITURES ADMINISTRATIVES"],
  ["phone_internet", "TELEPHONE & INTERNET"],
  ["fuel_purchases", "ACHATS CARBURANT"],
  ["business_meals", "REPAS PROFESSIONNEL"],
  ["tips_donations", "POURBOIRE DONS COURANTS"],
  ["point_of_sale_advertising", "PUB. SUR POINT DE VENTE"],
  ["other", "AUTRE"],
] as const;

const CATEGORY_LABELS = Object.fromEntries(INVOICE_CATEGORIES);

export function invoiceCategoryLabel(code: string | null) {
  if (!code) {
    return "-";
  }
  return CATEGORY_LABELS[code] ?? CATEGORY_LABELS.other;
}
