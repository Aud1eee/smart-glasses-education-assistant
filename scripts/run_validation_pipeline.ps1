$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Resolve-Path (Join-Path $ScriptDir "..")).Path

. (Join-Path $ProjectRoot "windows_runtime_common.ps1")

$PythonExe = Get-FocusProjectPython -ProjectRoot $ProjectRoot
Write-FocusProjectRuntimeBanner -PythonExe $PythonExe

$Pipeline = @(
    "analytics/validate_learning_state.py",
    "analytics/build_labeling_sheet.py",
    "analytics/summarize_validation_readiness.py"
)

foreach ($RelativeScript in $Pipeline) {
    $ScriptPath = Join-Path $ProjectRoot $RelativeScript
    Write-Host ""
    Write-Host "Running $RelativeScript"
    & $PythonExe $ScriptPath
    if ($LASTEXITCODE -ne 0) {
        throw "Validation pipeline failed at $RelativeScript"
    }
}

Write-Host ""
Write-Host "Validation pipeline finished."
