from __future__ import annotations

from typing import Literal

InvoiceCategoryCode = Literal[
    "raw_materials_5_5",
    "lost_packaging_20",
    "alcohol_purchases",
    "maintenance",
    "purchase_transport",
    "raw_materials_20",
    "cleaning_products",
    "discount",
    "hygiene_products",
    "administrative_supplies",
    "phone_internet",
    "fuel_purchases",
    "business_meals",
    "tips_donations",
    "point_of_sale_advertising",
    "other",
]

CATEGORY_LABELS: dict[str, str] = {
    "raw_materials_5_5": "ACHATS MP A 5.5%",
    "lost_packaging_20": "EMB. PERDUS 20%",
    "alcohol_purchases": "ACHATS ALCOOL",
    "maintenance": "ENTRETIENS",
    "purchase_transport": "TRANSPORTS SUR ACHATS",
    "raw_materials_20": "ACHATS MP A 20%",
    "cleaning_products": "PRODUITS ENTRETIENS",
    "discount": "REMISE",
    "hygiene_products": "PRODUITS HYGIENES",
    "administrative_supplies": "FOURNITURES ADMINISTRATIVES",
    "phone_internet": "TELEPHONE & INTERNET",
    "fuel_purchases": "ACHATS CARBURANT",
    "business_meals": "REPAS PROFESSIONNEL",
    "tips_donations": "POURBOIRE DONS COURANTS",
    "point_of_sale_advertising": "PUB. SUR POINT DE VENTE",
    "other": "AUTRE",
}

ALLOWED_CATEGORY_CODES = set(CATEGORY_LABELS)


def normalize_category_code(value: str | None) -> tuple[str | None, str | None]:
    if value is None:
        return None, None

    normalized = value.strip()
    if not normalized:
        return None, None
    if normalized in ALLOWED_CATEGORY_CODES:
        return normalized, None
    return "other", "unknown_category"


def category_label(code: str | None) -> str:
    if not code:
        return ""
    return CATEGORY_LABELS.get(code, CATEGORY_LABELS["other"])


def append_review_reason(existing: str | None, reason: str | None) -> str | None:
    if not reason:
        return existing
    if not existing:
        return reason
    reasons = [item.strip() for item in existing.split(",") if item.strip()]
    if reason not in reasons:
        reasons.append(reason)
    return ", ".join(reasons)
