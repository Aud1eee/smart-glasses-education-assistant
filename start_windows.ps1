$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $projectRoot "windows_runtime_common.ps1")
$pythonExe = Get-FocusProjectPython -ProjectRoot $projectRoot -RequiredModule "cv2"

Set-Location $projectRoot

Write-FocusProjectRuntimeBanner -PythonExe $pythonExe

& $pythonExe run.py --serve-only
