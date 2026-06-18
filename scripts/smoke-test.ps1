<#
.SYNOPSIS
  Verifies authentication and connectivity to the GECX / CX Agent Studio REST API
  by listing the apps in the configured project/location.

.USAGE
  ./scripts/smoke-test.ps1
  Reads config/config.json (falls back to config/config.example.json).
  Requires: gcloud CLI authenticated (see docs/authentication.md).
#>

$ErrorActionPreference = "Stop"

$repoRoot   = Split-Path -Parent $PSScriptRoot
$configPath = Join-Path $repoRoot "config/config.json"
if (-not (Test-Path $configPath)) {
    $configPath = Join-Path $repoRoot "config/config.example.json"
    Write-Warning "config/config.json not found - using config.example.json. Copy and edit it for real use."
}

$config = Get-Content $configPath -Raw | ConvertFrom-Json
$projectId = $config.projectId
$location  = $config.location
$endpoint  = $config.endpoint
$version   = $config.apiVersion

if ([string]::IsNullOrWhiteSpace($projectId) -or $projectId -eq "YOUR_GCP_PROJECT_ID") {
    throw "projectId is not set. Edit config/config.json before running."
}

Write-Host "Project : $projectId"
Write-Host "Location: $location"
Write-Host "Endpoint: $endpoint/$version"
Write-Host ""

Write-Host "Fetching access token via gcloud..."
$token = (gcloud auth print-access-token).Trim()
if ([string]::IsNullOrWhiteSpace($token)) {
    throw "Could not obtain access token. Run 'gcloud auth login' first."
}

$uri = "$endpoint/$version/projects/$projectId/locations/$location/apps"
Write-Host "GET $uri"
Write-Host ""

$headers = @{
    Authorization        = "Bearer $token"
    "x-goog-user-project" = $projectId
}

try {
    $response = Invoke-RestMethod -Method Get -Uri $uri -Headers $headers
    Write-Host "[OK] Success - API reachable and authorized." -ForegroundColor Green
    $response | ConvertTo-Json -Depth 10
} catch {
    Write-Host "[FAIL] Request failed." -ForegroundColor Red
    Write-Host $_.Exception.Message
    if ($_.ErrorDetails.Message) { Write-Host $_.ErrorDetails.Message }
    throw
}
