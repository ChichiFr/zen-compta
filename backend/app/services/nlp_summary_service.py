from __future__ import annotations

from decimal import Decimal

from openai import OpenAI, OpenAIError

from app.core.config import settings

SYSTEM_PROMPT = """
Tu es Zen, l'assistant comptable de Zen Compta.
Tu parles en francais simple et clair. Ton interlocuteur est un restaurateur
qui ne connait pas l'informatique ni la comptabilite avancee.

Regles:
- Ne donne jamais de conseil fiscal, juridique ou d'investissement.
- Ne valide jamais une facture toi-meme. Seul l'humain valide.
- Separe toujours HT (hors taxe), TVA et TTC (toutes taxes comprises).
- Utilise des termes simples: "ce que tu dois payer", "ce que tu as vendu",
  "ce qu'il te reste en caisse".
- Sois bref: 3-5 phrases maximum sauf si on te demande un detail.
- Formate les montants en euros avec virgule decimale (1 234,56 EUR).
- Ne repete pas les donnees brutes, resume-les.
""".strip()


def _fmt(value: Decimal | str) -> str:
    d = Decimal(str(value))
    whole, frac = str(d.quantize(Decimal("0.01"))).split(".")
    parts = []
    whole_abs = whole.lstrip("-")
    for i, ch in enumerate(reversed(whole_abs)):
        if i > 0 and i % 3 == 0:
            parts.append(" ")
        parts.append(ch)
    formatted = "".join(reversed(parts))
    if whole.startswith("-"):
        formatted = "-" + formatted
    return f"{formatted},{frac} EUR"


class NLPSummaryService:
    def __init__(self, api_key: str, model: str) -> None:
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def _chat(self, user_prompt: str) -> str:
        try:
            response = self.client.responses.create(
                model=self.model,
                instructions=SYSTEM_PROMPT,
                input=[{"role": "user", "content": user_prompt}],
                max_output_tokens=1000,
            )
            return response.output_text or ""
        except OpenAIError:
            return ""

    def summarize_upload(self, invoice_data: dict) -> str:
        lines_desc = []
        for line in invoice_data.get("lines", []):
            desc = line.get("description", "?")
            ht = line.get("amount_ht", "?")
            lines_desc.append(f"- {desc}: {ht} EUR HT")
        lines_text = "\n".join(lines_desc) if lines_desc else "Aucune ligne"

        prompt = (
            "Voici les donnees extraites d'une facture fournisseur. "
            "Resume en 2-3 phrases ce que la facture contient et ce que le "
            "restaurateur doit verifier avant de valider.\n\n"
            f"Fournisseur: {invoice_data.get('supplier_name', 'Inconnu')}\n"
            f"Date: {invoice_data.get('invoice_date', 'Non renseignee')}\n"
            f"Numero: {invoice_data.get('invoice_number', 'Non renseigne')}\n"
            f"Total HT: {invoice_data.get('total_ht', '?')}\n"
            f"Total TVA: {invoice_data.get('total_tva', '?')}\n"
            f"Total TTC: {invoice_data.get('total_ttc', '?')}\n"
            f"Lignes:\n{lines_text}"
        )
        return self._chat(prompt)

    def summarize_dashboard(
        self,
        dashboard_data: dict,
        performance_data: dict | None,
    ) -> str:
        prompt = (
            "Voici les donnees financieres du mois pour un restaurant. "
            "Resume la situation en 3-5 phrases: les ventes, les achats, "
            "la TVA a payer, et la tresorerie estimee. "
            "Signale tout probleme (tresorerie basse, factures non validees).\n\n"
            f"Ventes HT: {dashboard_data.get('sales_ht', '0')}\n"
            f"Ventes TTC: {dashboard_data.get('sales_ttc', '0')}\n"
            f"Achats valides HT: {dashboard_data.get('validated_invoices_ht', '0')}\n"
            f"TVA collectee: {dashboard_data.get('vat_collected', '0')}\n"
            f"TVA deductible: {dashboard_data.get('vat_deductible', '0')}\n"
            f"TVA a payer: {dashboard_data.get('vat_payable_estimate', '0')}\n"
            f"Charges mensuelles: {dashboard_data.get('monthly_outflows', '0')}\n"
            f"Tresorerie estimee: {dashboard_data.get('estimated_cash', '0')}\n"
            f"Factures a traiter: {dashboard_data.get('invoices_to_review_count', 0)}\n"
            f"Factures validees: {dashboard_data.get('validated_invoices_count', 0)}"
        )
        if performance_data and performance_data.get("performance"):
            perf = performance_data["performance"]
            prompt += (
                f"\n\nPerformance:\n"
                f"Matieres premieres HT: {perf.get('raw_materials_ht', '0')}\n"
                f"Salaires: {perf.get('salaries', '0')}\n"
                f"Charges sociales: {perf.get('social_charges', '0')}\n"
                f"EBE Cash: {perf.get('ebe_cash', '0')}"
            )
        return self._chat(prompt)

    def summarize_review_queue(self, invoices: list[dict]) -> str:
        if not invoices:
            return "Aucune facture en attente de validation."

        suppliers = [inv.get("supplier_name", "?") for inv in invoices]
        total_ttc = sum(
            float(inv.get("total_ttc", 0)) for inv in invoices
        )
        issues = []
        for inv in invoices:
            for line in inv.get("lines", []):
                reason = line.get("needs_review_reason")
                if reason:
                    issues.extend(reason.split(","))
        unique_issues = list(set(issues))

        prompt = (
            "Voici la liste des factures a traiter pour un restaurant. "
            "Resume combien il y en a, les fournisseurs principaux, "
            "et les problemes detectes.\n\n"
            f"Nombre: {len(invoices)}\n"
            f"Fournisseurs: {', '.join(suppliers[:5])}"
            f"{'...' if len(suppliers) > 5 else ''}\n"
            f"Total TTC: {total_ttc:.2f} EUR\n"
            "Problemes detectes: "
            f"{', '.join(unique_issues) if unique_issues else 'Aucun'}"
        )
        return self._chat(prompt)


def _fallback_upload_summary(invoice_data: dict) -> str:
    supplier = invoice_data.get("supplier_name", "Inconnu")
    total_ttc = invoice_data.get("total_ttc", "0")
    n_lines = len(invoice_data.get("lines", []))
    issues = []
    for line in invoice_data.get("lines", []):
        if line.get("needs_review_reason"):
            issues.append(line["needs_review_reason"])
    issue_text = f" {len(issues)} point(s) a verifier." if issues else ""
    return (
        f"Facture de {supplier} pour {total_ttc} EUR TTC "
        f"({n_lines} ligne(s)).{issue_text}"
    )


def _fallback_dashboard_summary(dashboard_data: dict) -> str:
    return (
        f"Ventes HT: {dashboard_data.get('sales_ht', '0')} EUR. "
        f"Achats valides: {dashboard_data.get('validated_invoices_ht', '0')} EUR HT. "
        f"TVA a payer: {dashboard_data.get('vat_payable_estimate', '0')} EUR. "
        f"Tresorerie estimee: {dashboard_data.get('estimated_cash', '0')} EUR. "
        f"{dashboard_data.get('invoices_to_review_count', 0)} facture(s) a traiter."
    )


def _fallback_review_summary(invoices: list[dict]) -> str:
    if not invoices:
        return "Aucune facture en attente de validation."
    suppliers = [inv.get("supplier_name", "?") for inv in invoices[:3]]
    return (
        f"{len(invoices)} facture(s) a traiter: {', '.join(suppliers)}"
        f"{'...' if len(invoices) > 3 else ''}."
    )


def build_nlp_summary_service() -> NLPSummaryService | None:
    if not settings.openai_api_key:
        return None
    return NLPSummaryService(
        api_key=settings.openai_api_key,
        model=settings.openai_assistant_model,
    )
