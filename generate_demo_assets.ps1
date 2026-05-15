$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $projectRoot "windows_runtime_common.ps1")
$pythonExe = Get-FocusProjectPython -ProjectRoot $projectRoot

Set-Location $projectRoot

Write-FocusProjectRuntimeBanner -PythonExe $pythonExe

& $pythonExe analytics\generate_demo_assets.py
