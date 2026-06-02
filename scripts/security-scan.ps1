param(
    [string]$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

$ErrorActionPreference = "Stop"

function Convert-ToRepositoryPath {
    param([string]$Path)
    return $Path.Replace("\", "/")
}

function Test-AllowlistedPath {
    param([string]$Path)
    return $Path -in @(
        ".env.example",
        "frontend/.env.example",
        "frontend/package-lock.json"
    )
}

function Test-TextFile {
    param([string]$Path)
    $binaryExtensions = @(
        ".ico", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".zip",
        ".xlsx", ".docx", ".pptx"
    )
    $extension = [System.IO.Path]::GetExtension($Path).ToLowerInvariant()
    return $extension -notin $binaryExtensions
}

function Test-AllowlistedSecretLine {
    param([string]$Line)
    return (
        $Line -match "local-check-" -or
        $Line -match "test-token" -or
        $Line -match "change-me" -or
        $Line -match "POSTGRES_PASSWORD" -or
        $Line -match "settings\." -or
        $Line -match "same-value-as-" -or
        $Line -match "your-shared-login-password" -or
        $Line -match "a-long-random-local-secret"
    )
}

Push-Location $Root
try {
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        throw "git is required for the security scan."
    }

    $paths = git ls-files --cached --others --exclude-standard |
        ForEach-Object { Convert-ToRepositoryPath $_ } |
        Where-Object { $_ -and -not (Test-AllowlistedPath $_) }

    $blockedPaths = @()
    foreach ($path in $paths) {
        if (
            $path -match '(^|/)\.env($|\.)' -or
            $path -match '\.(sqlite|sqlite3|db|dump|bak|backup|pem|key|crt|log|err)$' -or
            $path -match '(^|/)(uploads|media|documents|invoices|exports|secrets|tmp|temp)/'
        ) {
            $blockedPaths += $path
        }
    }

    if ($blockedPaths.Count -gt 0) {
        Write-Error (
            "Security scan failed: forbidden file paths found:`n" +
            ($blockedPaths | Sort-Object | ForEach-Object { " - $_" } | Out-String)
        )
    }

    $secretPatterns = @(
        @{ Name = "OpenAI API key"; Pattern = 'sk-[A-Za-z0-9_-]{20,}' },
        @{ Name = "GitHub token"; Pattern = 'gh[pousr]_[A-Za-z0-9_]{20,}' },
        @{ Name = "Stripe key"; Pattern = '(sk|pk)_(live|test)_[A-Za-z0-9]{20,}' },
        @{ Name = "AWS access key"; Pattern = 'AKIA[0-9A-Z]{16}' },
        @{
            Name = "Private key"
            Pattern = '-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'
        },
        @{
            Name = "Non-empty secret assignment"
            Pattern = '(?i)^\s*(\$env:)?[A-Z0-9_]*(API[_-]?KEY|SECRET|TOKEN|PASSWORD)[A-Z0-9_]*\s*[:=]\s*["'']?[^"''\s#]{8,}["'']?'
        }
    )

    $findings = @()
    foreach ($path in $paths) {
        if (-not (Test-TextFile $path)) {
            continue
        }
        if (-not (Test-Path -LiteralPath $path)) {
            continue
        }

        $lineNumber = 0
        foreach ($line in Get-Content -LiteralPath $path) {
            $lineNumber += 1
            if (Test-AllowlistedSecretLine $line) {
                continue
            }
            foreach ($secretPattern in $secretPatterns) {
                if ($line -match $secretPattern.Pattern) {
                    $findings += "${path}:$lineNumber $($secretPattern.Name)"
                }
            }
        }
    }

    if ($findings.Count -gt 0) {
        Write-Error (
            "Security scan failed: suspected secrets found:`n" +
            ($findings | Sort-Object | ForEach-Object { " - $_" } | Out-String)
        )
    }

    Write-Host "Security scan passed."
}
finally {
    Pop-Location
}
