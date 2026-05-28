$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $projectRoot "windows_runtime_common.ps1")
$pythonExe = Get-FocusProjectPython -ProjectRoot $projectRoot -RequiredModule "cv2"

Set-Location $projectRoot

Write-FocusProjectRuntimeBanner -PythonExe $pythonExe

$serverBootstrap = "import bootstrap_windows_runtime; import serve_app; serve_app.main()"
& $pythonExe -B -c $serverBootstrap
