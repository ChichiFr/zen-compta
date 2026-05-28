# Zen Ledger V2

Private rebuild of Bouddha-Compta.

This repository is intentionally clean. It is not a fork of the old
`dada1802/Bouddha-Compta` repository, and it should not import the old Git
history, local database, uploaded files, or secrets.

## Goal

Build a reliable accounting and operations tool for a restaurant, with a clear
data model for invoices, sales, treasury, VAT, staffing, document imports, and
bank connections.

## Starting Principles

- PostgreSQL is the source of truth for business data.
- Amounts must clearly separate TTC, HT, and VAT.
- Documents are stored outside the database; the database stores metadata.
- Bank and API tokens must be stored securely, never in frontend-accessible data.
- Tests are required for accounting calculations and critical workflows.
- The old project is a reference prototype only.

## Proposed Stack

The final stack is still open, but the current preferred direction is:

- Backend: FastAPI or Django, to be decided before implementation.
- Database: PostgreSQL.
- Frontend: Next.js if using a separate API backend, or Django templates/HTMX if using Django.
- Background jobs: Redis-backed worker for document extraction and bank sync.
- File storage: S3-compatible bucket or equivalent managed object storage.

## Local Status

This repo currently contains planning and project guardrails only. No production
code has been migrated from the old repository.

