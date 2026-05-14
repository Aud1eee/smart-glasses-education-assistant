$ErrorActionPreference = "Stop"

param(
    [ValidateSet("presentation", "stable", "rising", "overload", "recovery")]
    [string]$Mode = "presentation"
)

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"

Set-Location $projectRoot

if (-not (Test-Path -LiteralPath $pythonExe)) {
    throw "Missing .venv. Run setup_windows.ps1 first."
}

& $pythonExe simulate_motion.py --mode $Mode
