# Zen Compta

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

## Stack

The current V2 direction is:

- Frontend: Next.js, React, TypeScript, Tailwind CSS.
- Backend: FastAPI, Python, Pydantic.
- Database: PostgreSQL.
- Migrations: Alembic.
- Background jobs: Redis-backed worker later, when needed.
- File storage: S3-compatible bucket or equivalent managed object storage.

## Local Development

### Requirements

- Node.js 24+
- npm 11+
- Python 3.11+
- Docker

### Start PostgreSQL

```powershell
docker compose up -d postgres
```

### Backend

```powershell
Copy-Item .env.example .env
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Health check:

```text
http://localhost:8000/api/health
```

### Frontend

```powershell
cd frontend
Copy-Item .env.example .env.local
npm install
npm run dev
```

Frontend:

```text
http://localhost:3000
```

### Checks

```powershell
.\scripts\check.ps1
```

This runs backend tests, Python linting, frontend linting, frontend build,
`npm audit --audit-level=high`, the built-in security scan, and `gitleaks` when
it is installed.

### Pre-Push Hook

Install the local Git pre-push hook once per machine:

```powershell
.\scripts\install-git-hooks.ps1
```

After installation, `git push` runs:

```powershell
.\scripts\check.ps1
```

If tests, build, linting, audit, or security checks fail, the push is blocked.

## Local Status

The repo contains the MVP foundation: monthly sales, manual invoices with
multi-rate VAT, human validation, edit/archive actions before validation,
dashboard VAT/treasury estimates, CSV/XLSX exports, and local validation
scripts. No production code has been migrated from the old repository.
