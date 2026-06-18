<#
.SYNOPSIS
  Runs the GECX agent RPC regression harness. Non-zero exit on any failure - use this as the
  gate after major changes.

.USAGE
  ./scripts/run-tests.ps1                       # all cases, default transport
  ./scripts/run-tests.ps1 -Transport mock       # force the mock transport
  ./scripts/run-tests.ps1 -Case smoke-greeting  # one case

.NOTES
  Requires Python 3.10+ and `pip install -r tests/requirements.txt`.
  See docs/testing.md.
#>
param(
    [string]$Transport,
    [string]$Case,
    [string]$Cases
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$testsDir = Join-Path $repoRoot "tests"

$argsList = @("-m", "runner")
if ($Cases)     { $argsList += @("--cases", $Cases) }
if ($Transport) { $argsList += @("--transport", $Transport) }
if ($Case)      { $argsList += @("--case", $Case) }

Push-Location $testsDir
try {
    Write-Host "python $($argsList -join ' ')  (cwd: $testsDir)"
    & python @argsList
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
