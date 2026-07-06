<#
.SYNOPSIS
  Pull the server-side CES conversation trace for one call and render a per-call report
  (transcript, tool calls/responses, guardrail decisions, outcome). Reads config/config.json
  for the target project/location/app; auth is your active gcloud account.

.USAGE
  ./scripts/call-report.ps1 -List [-Limit 20]        # recent calls, newest first
  ./scripts/call-report.ps1 -Id test-1a2b3c4d5e6f    # rendered report to console
  ./scripts/call-report.ps1 -Id <id> -Out report.md  # ...or to a file
  ./scripts/call-report.ps1 -Id <id> -Raw            # raw conversation JSON

.NOTES
  <id> is the conversation id = last path segment of the resource name (e.g. a `test-…` session
  id the harness mints, a `bidi-…`/`simulator-…` id, or a bare UUID). Requires Python 3.10+.
#>
param(
    [string]$Id,
    [switch]$List,
    [int]$Limit,
    [switch]$Raw,
    [string]$Out
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$testsDir = Join-Path $repoRoot "tests"

Push-Location $testsDir
try {
    if ($List) {
        $a = @("-m", "runner.conversations", "list")
        if ($Limit) { $a += @("--limit", "$Limit") }
        & python @a
    }
    elseif ($Raw -and $Id) {
        & python -m runner.conversations get $Id
    }
    elseif ($Id) {
        $a = @("-m", "runner.conversations", "report", $Id)
        if ($Out) { $a += @("--out", $Out) }
        & python @a
    }
    else {
        Write-Host "Specify -Id <conversation-id> (report), add -Raw for JSON, or -List for recent calls."
        Write-Host "See the script header for usage."
        exit 2
    }
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
