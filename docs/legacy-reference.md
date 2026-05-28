# Legacy Repository Reference

Old prototype repository:

- GitHub: https://github.com/dada1802/Bouddha-Compta
- Local copy: `C:\dev\Bouddha-Compta#`

## Rules

- Do not fork the legacy repository for V2.
- Do not copy the legacy `.git` history.
- Do not copy `db.sqlite3`, `.env`, uploads, caches, or generated files.
- Treat old secrets as potentially exposed and rotate them before production use.
- Copy code only after manual review, and prefer rewriting core accounting logic.

## Useful Legacy Concepts

- Invoice upload and extraction workflow.
- Sales tracking workflow.
- Treasury dashboard concept.
- Staffing and payroll concept.
- Bank connection concept.

## Known Legacy Risks To Avoid

- Mixed TTC/HT/VAT semantics.
- Fake dashboard fallback values.
- No tests for accounting calculations.
- Firebase Realtime Database as accounting source of truth.
- Plaid access token stored in user-readable data.
- Fragile template and JavaScript coupling.

