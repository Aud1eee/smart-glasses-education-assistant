$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $projectRoot "windows_runtime_common.ps1")
$pythonExe = Get-FocusProjectPython -ProjectRoot $projectRoot -RequiredModule "flask"

Set-Location $projectRoot

Write-FocusProjectRuntimeBanner -PythonExe $pythonExe

& $pythonExe mock_reflection_provider.py
