# Security Baseline

## Secrets

- No real secrets in Git.
- Rotate any secret that was used in or near the legacy project before V2 production.
- Use environment variables or a managed secret store.
- `scripts/check.ps1` runs `scripts/security-scan.ps1`, which blocks common
  API keys, private keys, non-empty secret assignments, local databases, and
  uploaded/generated business files that are visible to Git.
- `scripts/install-git-hooks.ps1` configures Git to run `scripts/check.ps1`
  before every push through `.githooks/pre-push`.
- `gitleaks` is still recommended when installed, but the built-in scan gives
  a baseline even on machines without extra security tools.

## Data

- Do not commit local databases.
- Do not commit customer documents, invoices, bank exports, or generated reports.
- Store documents in object storage, not as base64 blobs in the database.

## Production Defaults

- Private repository.
- HTTPS-only deployment.
- Secure cookies for web sessions.
- Explicit allowed hosts/origins.
- Least-privilege database user.
- Audit trail for accounting-sensitive mutations.
