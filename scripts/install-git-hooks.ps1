$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

Push-Location $repoRoot
try {
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        throw "git is required to install hooks."
    }

    git config core.hooksPath .githooks
    Write-Host "Git hooks installed. Pre-push will run scripts/check.ps1."
}
finally {
    Pop-Location
}
