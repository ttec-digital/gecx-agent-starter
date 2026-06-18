<#
.SYNOPSIS
  Verifies the active gcloud account and token before working against the CES API.
  If config 'authAccount' is set, enforces that exact account; otherwise just checks a token
  is available. Designed as an OPT-IN SessionStart hook - see docs/auth-hook.md.

.NOTES
  ASCII-only on purpose (Windows PowerShell 5.1 misreads UTF-8-without-BOM).
  Always exits 0 so it never blocks session start.
#>
$ErrorActionPreference = "SilentlyContinue"

$repoRoot   = Split-Path -Parent $PSScriptRoot
$configPath = Join-Path $repoRoot "config/config.json"
if (-not (Test-Path $configPath)) { $configPath = Join-Path $repoRoot "config/config.example.json" }
$expected = (Get-Content $configPath -Raw | ConvertFrom-Json).authAccount

$active = (gcloud config get-value account 2>$null | Out-String).Trim()

if ([string]::IsNullOrWhiteSpace($expected)) {
    # No specific account configured - just confirm a usable token exists.
    $null = (gcloud auth print-access-token 2>$null)
    if ($LASTEXITCODE -ne 0) {
        Write-Output "[AUTH REMINDER] No active gcloud token. Run: gcloud auth login   (set 'authAccount' in config/config.json to enforce a specific account)."
    } else {
        Write-Output "[AUTH OK] gcloud token valid for '$active'. (Set 'authAccount' in config/config.json to enforce a specific account.)"
    }
    exit 0
}

if ($active -ne $expected) {
    Write-Output "[AUTH REMINDER] Active gcloud account is '$active' (expected '$expected'). Switch with: gcloud config set account $expected   (then 'gcloud auth login $expected' if the token is stale)."
    exit 0
}

$null = (gcloud auth print-access-token 2>$null)
if ($LASTEXITCODE -ne 0) {
    Write-Output "[AUTH REMINDER] Signed in as $expected but the access token needs a refresh. Run: gcloud auth login $expected"
} else {
    Write-Output "[AUTH OK] gcloud active account is $expected and the access token is valid."
}
exit 0
