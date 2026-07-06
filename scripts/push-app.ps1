<#
.SYNOPSIS
  Pushes the source-of-truth JSON under app/ to the live GECX / CX Agent Studio app via REST.
  Existing resources are PATCHed; missing ones are POST-created. DRY-RUN by default - it prints
  the plan and changes nothing until you pass -Apply.

.DESCRIPTION
  Counterpart to export-app.ps1. For each app/<collection>/<id>.json it strips server-managed
  fields (name, etag, createTime, updateTime, generatedSummary, validationErrors, _syncedFrom),
  then targets the app in config/config.json:
    - resource id  = the file name (== last segment of the resource 'name')
    - resource path= projects/{p}/locations/{l}/apps/{appId}/{collection}/{id}
  UPDATE uses PATCH with ?updateMask=<top-level keys in the body>. CREATE uses POST with the
  collection's id query param. Resources are processed tools -> toolsets -> guardrails ->
  examples -> agents -> app, so dependencies exist before the things that reference them.

  Cross-app note: reference fields inside the JSON (e.g. an agent's tools[], the app's rootAgent)
  embed the SOURCE app path. Pushing back to the app the files came from is safe; pushing to a
  DIFFERENT app would leave those references pointing at the source. This script does not rewrite
  them - use exportApp/importApp for whole-app moves.

.PARAMETER Apply
  Actually send the writes. Without it, the script only prints the plan (dry run).

.PARAMETER Collection
  Limit to one collection (agents|tools|toolsets|guardrails|examples).

.PARAMETER Id
  Limit to a single resource id (file base name), e.g. my_agent. Implies its collection.

.PARAMETER IncludeApp
  Also push app/app.json (the app resource). Off by default - the app carries broad settings you
  rarely want to overwrite in bulk.

.USAGE
  ./scripts/push-app.ps1                                   # dry run: plan for everything
  ./scripts/push-app.ps1 -Collection agents               # dry run: agents only
  ./scripts/push-app.ps1 -Id my_agent -Apply         # push one agent for real
  ./scripts/push-app.ps1 -Apply                            # push all resources for real
  Reads config/config.json. Requires: gcloud CLI authenticated (see docs/authentication.md).
#>
[CmdletBinding()]
param(
    [switch]$Apply,
    [ValidateSet("agents", "tools", "toolsets", "guardrails", "examples")]
    [string]$Collection,
    [string]$Id,
    [switch]$IncludeApp
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

# fields the server owns / we add locally - never sent on a write
$readOnly = @("name", "etag", "createTime", "updateTime", "generatedSummary", "validationErrors", "_syncedFrom")
# collection -> the create-time id query param
$idParam = @{ agents = "agentId"; tools = "toolId"; toolsets = "toolsetId"; guardrails = "guardrailId"; examples = "exampleId" }
# dependency-safe order (referenced things first)
$order = @("tools", "toolsets", "guardrails", "examples", "agents")

function Strip-ReadOnly($obj) {
    $out = [ordered]@{}
    foreach ($p in $obj.PSObject.Properties) {
        if ($readOnly -notcontains $p.Name) { $out[$p.Name] = $p.Value }
    }
    return $out
}

function Test-Exists($url) {
    try { Invoke-RestMethod -Method Get -Uri $url -Headers $headers | Out-Null; return $true }
    catch { if ($_.Exception.Response.StatusCode.value__ -eq 404) { return $false } else { throw } }
}

# --- collect targets --------------------------------------------------------- #
$collections = if ($Collection) { @($Collection) } elseif ($Id) { @() } else { $order }
if ($Id -and -not $Collection) {
    # find which collection holds this id
    foreach ($c in $order) {
        if (Test-Path (Join-Path $appDir "$c/$Id.json")) { $collections = @($c); break }
    }
    if (-not $collections) { throw "No app/*/$Id.json found for -Id '$Id'." }
}

$mode = if ($Apply) { "APPLY" } else { "DRY RUN" }
Write-Host "Push to $appPath  [$mode]" -ForegroundColor Cyan
if (-not $Apply) { Write-Host "No changes will be sent. Re-run with -Apply to write." -ForegroundColor Yellow }
Write-Host ""

$created = 0; $updated = 0; $failed = 0
foreach ($c in $collections) {
    $dir = Join-Path $appDir $c
    if (-not (Test-Path $dir)) { continue }
    $files = Get-ChildItem $dir -Filter "*.json" -ErrorAction SilentlyContinue
    if ($Id) { $files = $files | Where-Object { $_.BaseName -eq $Id } }

    foreach ($f in $files) {
        $rid  = $f.BaseName                                   # readable local handle
        $obj  = Get-Content $f.FullName -Raw | ConvertFrom-Json
        $body = Strip-ReadOnly $obj
        # Address by the server resource id embedded in 'name' (last segment) - the file name is a
        # hand-authored slug that does NOT reliably equal the id (some ids are UUIDs). Fall back to
        # the file name only for a brand-new local resource that has no 'name' yet.
        $srvId = ($obj.name -split "/")[-1]
        if ([string]::IsNullOrWhiteSpace($srvId)) { $srvId = $rid }
        $label = if ($srvId -eq $rid) { $rid } else { "$rid ($srvId)" }
        $url  = "$appBase/$c/$srvId"
        $exists = Test-Exists $url

        if ($exists) {
            $mask   = ($body.Keys -join ",")
            $target = "$url`?updateMask=$([uri]::EscapeDataString($mask))"
            Write-Host ("  UPDATE  {0}/{1}  (mask: {2})" -f $c, $label, $mask)
            if ($Apply) {
                try {
                    Invoke-RestMethod -Method Patch -Uri $target -Headers $headers `
                        -ContentType "application/json" -Body ($body | ConvertTo-Json -Depth 100) | Out-Null
                    $updated++
                } catch { $failed++; Write-Host "  [FAIL] $($_.Exception.Message)" -ForegroundColor Red; if ($_.ErrorDetails.Message) { Write-Host "         $($_.ErrorDetails.Message)" } }
            } else { $updated++ }
        } else {
            $createUrl = "$appBase/$c`?$($idParam[$c])=$([uri]::EscapeDataString($srvId))"
            Write-Host ("  CREATE  {0}/{1}" -f $c, $label) -ForegroundColor Green
            if ($Apply) {
                try {
                    Invoke-RestMethod -Method Post -Uri $createUrl -Headers $headers `
                        -ContentType "application/json" -Body ($body | ConvertTo-Json -Depth 100) | Out-Null
                    $created++
                } catch { $failed++; Write-Host "  [FAIL] $($_.Exception.Message)" -ForegroundColor Red; if ($_.ErrorDetails.Message) { Write-Host "         $($_.ErrorDetails.Message)" } }
            } else { $created++ }
        }
    }
}

# the app resource itself (opt-in)
if ($IncludeApp -and -not $Collection -and -not $Id) {
    $appFile = Join-Path $appDir "app.json"
    if (Test-Path $appFile) {
        $obj  = Get-Content $appFile -Raw | ConvertFrom-Json
        $body = Strip-ReadOnly $obj
        $mask = ($body.Keys -join ",")
        Write-Host ("  UPDATE  app  (mask: {0})" -f $mask)
        if ($Apply) {
            try {
                Invoke-RestMethod -Method Patch -Uri "$appBase`?updateMask=$([uri]::EscapeDataString($mask))" `
                    -Headers $headers -ContentType "application/json" -Body ($body | ConvertTo-Json -Depth 100) | Out-Null
                $updated++
            } catch { $failed++; Write-Host "  [FAIL] $($_.Exception.Message)" -ForegroundColor Red; if ($_.ErrorDetails.Message) { Write-Host "         $($_.ErrorDetails.Message)" } }
        } else { $updated++ }
    }
}

Write-Host ""
$verb = if ($Apply) { "applied" } else { "planned" }
Write-Host ("[OK] {0}: {1} update(s), {2} create(s), {3} failure(s)." -f $verb, $updated, $created, $failed) `
    -ForegroundColor $(if ($failed) { "Red" } else { "Green" })
if (-not $Apply) { Write-Host "     Dry run only - re-run with -Apply to write these changes." -ForegroundColor Yellow }
if ($failed) { exit 1 }
