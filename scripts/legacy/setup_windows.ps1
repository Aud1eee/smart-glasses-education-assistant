$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $projectRoot "windows_runtime_common.ps1")
$pythonExe = Get-FocusProjectPython -ProjectRoot $projectRoot

Set-Location $projectRoot

Write-FocusProjectRuntimeBanner -PythonExe $pythonExe

New-Item -ItemType Directory -Force -Path (Join-Path $projectRoot "data") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $projectRoot "exports") | Out-Null

Write-Host ""
Write-Host "Windows runtime bridge is ready."
Write-Host "VSCode should use the bundled runtime interpreter configured in .vscode/settings.json."
Write-Host "If OCR fails later, install Tesseract OCR for Windows and add it to PATH."
