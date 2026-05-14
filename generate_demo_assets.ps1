$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"

Set-Location $projectRoot

if (-not (Test-Path -LiteralPath $pythonExe)) {
    throw "Missing .venv. Run setup_windows.ps1 first."
}

& $pythonExe analytics\generate_demo_assets.py
