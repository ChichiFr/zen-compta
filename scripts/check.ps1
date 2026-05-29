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
npm run lint
npm run build
npm audit --audit-level=high
Pop-Location

if (Get-Command gitleaks -ErrorAction SilentlyContinue) {
    Write-Host "Running gitleaks..."
    gitleaks detect --source . --no-git --redact
} else {
    Write-Host "Skipping gitleaks: not installed."
}

