# Security Baseline

## Secrets

- No real secrets in Git.
- Rotate any secret that was used in or near the legacy project before V2 production.
- Use environment variables or a managed secret store.

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

