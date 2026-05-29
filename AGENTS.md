# AGENTS.md

Instructions for AI coding agents working on Zen Compta.

## Core Rule

Code like a conventional, experienced human engineer. Prefer boring, standard,
maintainable patterns over clever abstractions. Keep changes small, readable,
and easy to review.

## Project Context

Zen Compta is a clean V2 rebuild of a restaurant accounting and financial
management tool. The legacy Bouddha-Compta project is reference-only.

Do not copy the legacy project directly. Do not import its Git history, local
database, uploaded documents, generated exports, caches, `.env` files, or
secrets. Product ideas may be reused, but core accounting and security-sensitive
logic should be rewritten deliberately.

## Standard Stack Direction

The planned stack is:

- Frontend: Next.js, React, TypeScript, Tailwind CSS.
- Backend: FastAPI, Python, Pydantic.
- Database: PostgreSQL.
- Migrations: Alembic.
- Background jobs: Redis-backed worker later, when needed.

Follow common conventions for these tools. Do not invent a custom framework,
folder layout, state system, validation layer, or migration strategy unless
there is a clear documented reason.

## Frontend Standards

Use a conventional Next.js structure:

- `app/` for routes and pages.
- `components/` for reusable UI components.
- `lib/` for client helpers and shared utilities.
- `types/` for TypeScript types.

Rules:

- Use TypeScript.
- Keep React components simple and readable.
- Use Tailwind utilities consistently.
- Avoid hardcoded magic styling spread across unrelated files.
- Keep business-critical calculations out of the frontend unless they are only
  display previews. The backend is authoritative.
- Do not expose secrets or private backend credentials to the browser.

## Backend Standards

Use a conventional FastAPI structure:

- `app/api/` for API routers.
- `app/core/` for configuration, security, and app setup.
- `app/models/` for database models.
- `app/schemas/` for Pydantic request and response schemas.
- `app/services/` for business logic.
- `app/tests/` or `tests/` for tests.

Rules:

- Keep route handlers thin.
- Put accounting and VAT logic in services, not directly in API routes.
- Validate inputs with Pydantic.
- Use PostgreSQL as the source of truth.
- Use Alembic migrations for schema changes.
- Never store uploaded documents as base64 blobs in PostgreSQL.
- Do not log secrets, access tokens, uploaded document contents, or full
  sensitive payloads.

## Accounting Rules

Accounting correctness matters more than UI speed.

- Never mix HT, TVA, and TTC.
- Store and display HT, TVA, and TTC as separate concepts.
- Invoice totals must be derived from invoice lines.
- Multi-rate VAT must be handled at the invoice-line level.
- AI may prefill invoice data, but it must never validate an invoice.
- A human validation step is required before a draft invoice counts in official
  totals, exports, or VAT summaries.
- Important VAT and invoice-total rules must have tests.
- If rounding policy is unclear, stop and ask before implementing financial
  behavior.

## Security And Data Rules

Never commit:

- `.env` files with real values.
- API keys, access tokens, passwords, private keys, or secrets.
- local databases such as `.sqlite`, `.sqlite3`, `.db`, dumps, or backups.
- uploaded invoices, receipts, bank exports, generated reports, or customer data.
- caches, build outputs, or temporary files.

If a suspected secret or sensitive file has already been committed, stop and
report it. Treat it as a rotation/remediation issue. Do not hide it in a later
commit.

## Required Pre-Push Checklist

Before pushing any branch, run the full local validation checklist that exists
for the current stage of the project.

Minimum expectations once the relevant tools exist:

- Frontend TypeScript/build check.
- Frontend lint.
- Backend tests.
- Backend lint/format check.
- Secret scan, such as `gitleaks`, if installed.
- Python dependency audit, if installed.
- Node dependency audit, if installed.

If a check is not available yet, document that it was skipped and why. Do not
fake successful checks.

If tests, build, lint, or critical security checks fail:

- Fix the problem when the fix is safe and clearly within scope.
- Otherwise stop and explain the risk.
- Do not push code with known secrets, failing critical tests, or failing
  critical security checks.

## Branching And Commits

- Do not work directly on `main` for new features.
- Use branch names such as `feature/invoices-mvp`, `feature/dashboard`,
  `fix/security-gitignore`, or `docs/agents-guidelines`.
- Keep commits focused.
- Do not mix unrelated refactors with feature work.
- Do not rewrite or remove user changes unless explicitly asked.

## Communication

When reporting work:

- Say what changed.
- Say what checks were run.
- Say what checks were skipped and why.
- Call out security or accounting risks clearly.

