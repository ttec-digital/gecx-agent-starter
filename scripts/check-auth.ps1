<#
.SYNOPSIS
  Verifies BOTH gcloud credential stores this project uses are the expected account
  (config 'authAccount') with usable tokens:
    - gcloud ACTIVE account  -> used by the REST/curl scripts (gcloud auth print-access-token)
    - Application Default Credentials (ADC) -> used by the Python harness (google.auth.default)
  The ADC check matters: it is a SEPARATE store, and a mismatch there silently sends harness
  calls as the wrong identity (exactly the bug this guards against). Opt-in SessionStart hook;
  see docs/auth-hook.md.

.NOTES
  ASCII-only on purpose (Windows PowerShell 5.1 misreads UTF-8-without-BOM).
  Always exits 0 so it never blocks session start.
#>
$ErrorActionPreference = "SilentlyContinue"

$repoRoot   = Split-Path -Parent $PSScriptRoot
$configPath = Join-Path $repoRoot "config/config.json"
if (-not (Test-Path $configPath)) { $configPath = Join-Path $repoRoot "config/config.example.json" }
$expected = (Get-Content $configPath -Raw | ConvertFrom-Json).authAccount

function Get-TokenEmail($token) {
    if ([string]::IsNullOrWhiteSpace($token)) { return $null }
    try { return (Invoke-RestMethod -Uri "https://oauth2.googleapis.com/tokeninfo?access_token=$token").email }
    catch { return $null }
}

$active    = (gcloud config get-value account 2>$null | Out-String).Trim()
$activeTok = (gcloud auth print-access-token 2>$null | Out-String).Trim()
$adcTok    = (gcloud auth application-default print-access-token 2>$null | Out-String).Trim()
$adcEmail  = Get-TokenEmail $adcTok

$problems = @()
if ([string]::IsNullOrWhiteSpace($expected)) {
    if (-not $activeTok) { $problems += "no active gcloud token (run: gcloud auth login)" }
    if (-not $adcTok)    { $problems += "no ADC token (run: gcloud auth application-default login)" }
} else {
    if ($active -ne $expected)  { $problems += "ACTIVE account is '$active', expected '$expected' (gcloud config set account $expected)" }
    elseif (-not $activeTok)    { $problems += "ACTIVE token stale (gcloud auth login $expected)" }
    if ($adcEmail -and $adcEmail -ne $expected) { $problems += "ADC account is '$adcEmail', expected '$expected' (gcloud auth application-default login $expected)" }
    elseif (-not $adcTok)       { $problems += "ADC token stale/missing (gcloud auth application-default login $expected)" }
}

if ($problems.Count -gt 0) {
    Write-Output ("[AUTH REMINDER] " + ($problems -join "  |  "))
} else {
    if ([string]::IsNullOrWhiteSpace($expected)) { $who = "active '$active' / ADC '$adcEmail'" } else { $who = "'$expected'" }
    Write-Output "[AUTH OK] gcloud active + ADC both $who with valid tokens."
}
exit 0
