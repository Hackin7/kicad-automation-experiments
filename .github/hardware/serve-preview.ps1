$ErrorActionPreference = "Stop"
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$site = Join-Path $env:TEMP "kicad-hardware-preview"
$board = Join-Path $site "projects\simple-led-board"

Remove-Item -Recurse -Force $site -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path (Join-Path $board "kicad") | Out-Null

$templates = Join-Path $PSScriptRoot "site"
Copy-Item (Join-Path $templates "style.css"), (Join-Path $templates "theme.js"), (Join-Path $templates "index.html") $board

$hw = Join-Path $root "hardware\simple_led_board"
Copy-Item (Join-Path $hw "simple_led_board.kicad_pro"), (Join-Path $hw "simple_led_board.kicad_sch"), (Join-Path $hw "simple_led_board.kicad_pcb") (Join-Path $board "kicad")

@'
window.HARDWARE_CI = {
  runUrl: "https://github.com/example/actions/runs/1",
  sha: "deadbeefcafe",
  checksResult: "success",
  outputsResult: "success",
  modelsResult: "skipped",
  projectName: "Simple LED Board",
  projectSlug: "simple-led-board",
  projectFile: "simple_led_board.kicad_pro",
  schematicFile: "simple_led_board.kicad_sch",
  boardFile: "simple_led_board.kicad_pcb",
  baseName: "simple_led_board"
};
'@ | Set-Content (Join-Path $board "run-info.js") -Encoding utf8

$html = Get-Content (Join-Path $board "index.html") -Raw
$html = $html -replace '__PROJECT_NAME__', 'Simple LED Board'
$html = $html -replace '__PROJECT_FILE__', 'simple_led_board.kicad_pro'
$html = $html -replace '__SCHEMATIC_FILE__', 'simple_led_board.kicad_sch'
$html = $html -replace '__BOARD_FILE__', 'simple_led_board.kicad_pcb'
$html = $html -replace '__BASE_NAME__', 'simple_led_board'
Set-Content (Join-Path $board "index.html") $html -Encoding utf8

$url = "http://127.0.0.1:8766/projects/simple-led-board/"
Write-Host "Preview: $url"
Write-Host "Press Ctrl+C to stop."
Set-Location $site
Start-Process $url
python -m http.server 8766
