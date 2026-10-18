$ErrorActionPreference = "Stop"
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$site = Join-Path $env:TEMP "kicad-hardware-preview"

function Invoke-Python {
  param([Parameter(ValueFromRemainingArguments = $true)][string[]]$PyArgs)
  if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3.11 @PyArgs
  } else {
    & python @PyArgs
  }
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Set-Location $root
$projects = Invoke-Python "actions/discover/discover.py"
$env:PROJECTS_JSON = $projects
Invoke-Python "actions/viewer/assemble.py" --root $root --artifacts (Join-Path $site "missing-artifacts") --out $site --title "Hardware Boards"

$url = "http://127.0.0.1:8766/projects/simple-led-board/"
Write-Host "Preview: $url"
Write-Host "Press Ctrl+C to stop."
Set-Location $site
Start-Process $url
python -m http.server 8766
