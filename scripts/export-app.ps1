<#
.SYNOPSIS
  Refreshes the source-of-truth JSON under app/ from the live GECX / CX Agent Studio app.
  For each collection (agents, tools, toolsets, guardrails, examples) it GETs every resource
  and writes app/<collection>/<id>.json; it also writes the app resource to app/app.json.
  Each file gets a local "_syncedFrom" marker (source app path + UTC timestamp).

.DESCRIPTION
  This is the counterpart to push-app.ps1. It OVERWRITES local app/*.json with the live
  definitions, so commit or stash local edits first. Server-managed fields (name, etag,
  createTime, updateTime, ...) are kept so the files stay a faithful, diff-able mirror.

.PARAMETER Collection
  Limit to one collection (agents|tools|toolsets|guardrails|examples). Default: all + the app.

.PARAMETER Prune
  Delete local files under app/<collection>/ that no longer exist on the server.

.USAGE
  ./scripts/export-app.ps1                       # refresh everything from live
  ./scripts/export-app.ps1 -Collection agents    # just the agents
  ./scripts/export-app.ps1 -Prune                # also remove locally-orphaned files
  Reads config/config.json (projectId, location, endpoint, apiVersion, appId).
  Requires: gcloud CLI authenticated (see docs/authentication.md).
#>
[CmdletBinding()]
param(
    [ValidateSet("agents", "tools", "toolsets", "guardrails", "examples")]
    [string]$Collection,
    [switch]$Prune
)

$ErrorActionPreference = "Stop"

# --- config ------------------------------------------------------------------ #
$repoRoot   = Split-Path -Parent $PSScriptRoot
$appDir     = Join-Path $repoRoot "app"
$configPath = Join-Path $repoRoot "config/config.json"
if (-not (Test-Path $configPath)) {
    throw "config/config.json not found. Copy config/config.example.json and fill it in."
}
$config    = Get-Content $configPath -Raw | ConvertFrom-Json
$projectId = $config.projectId
$location  = $config.location
$endpoint  = $config.endpoint
$version   = $config.apiVersion
$appId     = $config.appId
foreach ($pair in @{ projectId = $projectId; location = $location; appId = $appId }.GetEnumerator()) {
    if ([string]::IsNullOrWhiteSpace($pair.Value)) { throw "$($pair.Key) is not set in config/config.json." }
}

$appPath = "projects/$projectId/locations/$location/apps/$appId"
$appBase = "$endpoint/$version/$appPath"

$token = (gcloud auth print-access-token).Trim()
if ([string]::IsNullOrWhiteSpace($token)) { throw "Could not obtain access token. Run 'gcloud auth login'." }
$headers = @{ Authorization = "Bearer $token"; "x-goog-user-project" = $projectId }

# UTF-8 without BOM (repo convention - avoids the documented BOM gotcha)
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
function Write-JsonFile($path, $obj) {
    $json = $obj | ConvertTo-Json -Depth 100
    [System.IO.File]::WriteAllText($path, $json, $utf8NoBom)
}

function Get-All($collectionName) {
    # GET .../apps/{app}/{collection}, following nextPageToken; returns the item array.
    $items = @()
    $pageToken = $null
    do {
        $uri = "$appBase/$collectionName"
        if ($pageToken) { $uri += "?pageToken=$([uri]::EscapeDataString($pageToken))" }
        $resp = Invoke-RestMethod -Method Get -Uri $uri -Headers $headers
        if ($resp.$collectionName) { $items += $resp.$collectionName }
        $pageToken = $resp.nextPageToken
    } while ($pageToken)
    return , $items
}

$collections = if ($Collection) { @($Collection) } else { @("agents", "tools", "toolsets", "guardrails", "examples") }
$stamp = (Get-Date).ToUniversalTime().ToString("o")

Write-Host "Exporting from $appPath" -ForegroundColor Cyan
Write-Host ""

function To-Slug($text) {
    $s = ($text -replace "[^A-Za-z0-9]+", "_").Trim("_").ToLower()
    if ([string]::IsNullOrWhiteSpace($s)) { "resource" } else { $s }
}
$uuidRe = "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"

$total = 0
foreach ($c in $collections) {
    $destDir = Join-Path $appDir $c
    if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir | Out-Null }

    # Map existing local files by their embedded server id so we overwrite in place and never
    # rename the readable slugs (a file name is a hand-authored slug != the server id).
    $byId = @{}
    Get-ChildItem $destDir -Filter "*.json" -ErrorAction SilentlyContinue | ForEach-Object {
        try {
            $existingId = ((Get-Content $_.FullName -Raw | ConvertFrom-Json).name -split "/")[-1]
            if ($existingId) { $byId[$existingId] = $_.FullName }
        } catch { }
    }

    $items = Get-All $c
    $seen = @{}
    foreach ($item in $items) {
        $id = ($item.name -split "/")[-1]
        $seen[$id] = $true
        $item | Add-Member -NotePropertyName "_syncedFrom" -NotePropertyValue "$appPath @ $stamp" -Force
        # keep the existing file name if we already track this id; otherwise pick a readable slug
        # (the id when it's already a slug, else the slugified displayName)
        if ($byId.ContainsKey($id)) {
            $path = $byId[$id]
        } else {
            $slug = if ($id -match $uuidRe) { To-Slug $item.displayName } else { $id }
            $path = Join-Path $destDir "$slug.json"
        }
        Write-JsonFile $path $item
        $total++
    }
    Write-Host ("  {0,-11} {1,3} file(s)" -f $c, $items.Count)

    if ($Prune) {
        Get-ChildItem $destDir -Filter "*.json" -ErrorAction SilentlyContinue | ForEach-Object {
            $localId = try { ((Get-Content $_.FullName -Raw | ConvertFrom-Json).name -split "/")[-1] } catch { $_.BaseName }
            if (-not $seen[$localId]) {
                Remove-Item $_.FullName
                Write-Host "  pruned  $c/$($_.Name)" -ForegroundColor DarkYellow
            }
        }
    }
}

# the app resource itself
if (-not $Collection) {
    $app = Invoke-RestMethod -Method Get -Uri $appBase -Headers $headers
    $app | Add-Member -NotePropertyName "_syncedFrom" -NotePropertyValue "$appPath @ $stamp" -Force
    Write-JsonFile (Join-Path $appDir "app.json") $app
    Write-Host ("  {0,-11}   1 file(s)" -f "app")
    $total++
}

Write-Host ""
Write-Host "[OK] Exported $total resource file(s) to app/." -ForegroundColor Green
Write-Host "     Review 'git diff app/' to see what changed on the platform."
