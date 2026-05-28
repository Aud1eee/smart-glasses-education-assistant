$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $projectRoot "windows_runtime_common.ps1")

$pythonExe = Get-FocusProjectPython -ProjectRoot $projectRoot
Write-FocusProjectRuntimeBanner -PythonExe $pythonExe

& $pythonExe (Join-Path $projectRoot "analytics\generate_scene_calibration_sheet.py")
