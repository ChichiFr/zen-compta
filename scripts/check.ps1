$ErrorActionPreference = "Stop"

function Assert-LastExit {
    param([string]$StepName)
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Check failed: $StepName (exit code $LASTEXITCODE)" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

Write-Host "Checking backend..."
Push-Location backend
if (Test-Path ".venv\Scripts\python.exe") {
    .\.venv\Scripts\python.exe -m pytest
    Assert-LastExit "backend tests"
    .\.venv\Scripts\python.exe -m ruff check .
    Assert-LastExit "backend lint"
} else {
    python -m pytest
    Assert-LastExit "backend tests"
    python -m ruff check .
    Assert-LastExit "backend lint"
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
Assert-LastExit "frontend lint"
npm run build
Assert-LastExit "frontend build"
npm audit --audit-level=high
Assert-LastExit "frontend audit"
Pop-Location

Write-Host "Running built-in security scan..."
.\scripts\security-scan.ps1

if (Get-Command gitleaks -ErrorAction SilentlyContinue) {
    Write-Host "Running gitleaks..."
    gitleaks detect --source . --no-git --redact
    Assert-LastExit "gitleaks"
} else {
    Write-Host "Skipping gitleaks: not installed."
}

Write-Host "All checks passed."
