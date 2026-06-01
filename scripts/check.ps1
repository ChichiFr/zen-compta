$ErrorActionPreference = "Stop"

Write-Host "Checking backend..."
Push-Location backend
if (Test-Path ".venv\Scripts\python.exe") {
    .\.venv\Scripts\python.exe -m pytest
    .\.venv\Scripts\python.exe -m ruff check .
} else {
    python -m pytest
    python -m ruff check .
}
Pop-Location

Write-Host "Checking frontend..."
Push-Location frontend
if (-not $env:INTERNAL_API_TOKEN) {
    $env:INTERNAL_API_TOKEN = "local-check-token"
}
if (-not $env:ZEN_COMPTA_APP_PASSWORD) {
    $env:ZEN_COMPTA_APP_PASSWORD = "local-check-password"
}
if (-not $env:ZEN_COMPTA_SESSION_SECRET) {
    $env:ZEN_COMPTA_SESSION_SECRET = "local-check-session-secret"
}
npm run lint
npm run build
npm audit --audit-level=high
Pop-Location

Write-Host "Running built-in security scan..."
.\scripts\security-scan.ps1

if (Get-Command gitleaks -ErrorAction SilentlyContinue) {
    Write-Host "Running gitleaks..."
    gitleaks detect --source . --no-git --redact
} else {
    Write-Host "Skipping gitleaks: not installed."
}
