$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPath = Join-Path $projectRoot ".venv"
$pythonExe = Join-Path $venvPath "Scripts\python.exe"

Set-Location $projectRoot

if (-not (Test-Path -LiteralPath $venvPath)) {
    Write-Host "Creating Windows virtual environment..."
    py -3 -m venv .venv
}

Write-Host "Upgrading pip..."
& $pythonExe -m pip install --upgrade pip

Write-Host "Installing project requirements..."
& $pythonExe -m pip install -r requirements.txt

Write-Host ""
Write-Host "Windows environment is ready."
Write-Host "If OCR fails later, install Tesseract OCR for Windows and add it to PATH."
