$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Resolve-Path (Join-Path $ScriptDir "..")).Path

. (Join-Path $ProjectRoot "windows_runtime_common.ps1")

$PythonExe = Get-FocusProjectPython -ProjectRoot $ProjectRoot
Write-FocusProjectRuntimeBanner -PythonExe $PythonExe

$Pipeline = @(
    "analytics/generate_demo_assets.py",
    "analytics/generate_reflection_report.py",
    "analytics/generate_demo_storyboard.py",
    "analytics/generate_presentation_script.py"
)

foreach ($RelativeScript in $Pipeline) {
    $ScriptPath = Join-Path $ProjectRoot $RelativeScript
    Write-Host ""
    Write-Host "Running $RelativeScript"
    & $PythonExe $ScriptPath
    if ($LASTEXITCODE -ne 0) {
        throw "Demo pipeline failed at $RelativeScript"
    }
}

Write-Host ""
Write-Host "Demo pipeline finished."
