$ErrorActionPreference = "Stop"

function Get-FocusProjectPython {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ProjectRoot,
        [string]$RequiredModule = ""
    )

    $bundledPython = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
    $legacyPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    if ([string]::IsNullOrWhiteSpace($RequiredModule)) {
        if (Test-Path -LiteralPath $bundledPython) {
            return $bundledPython
        }
        if (Test-Path -LiteralPath $legacyPython) {
            return $legacyPython
        }
    }
    else {
        if ((Test-Path -LiteralPath $bundledPython) -and (Test-FocusProjectPythonModule -PythonExe $bundledPython -ModuleName $RequiredModule)) {
            return $bundledPython
        }
        if ((Test-Path -LiteralPath $legacyPython) -and (Test-FocusProjectPythonModule -PythonExe $legacyPython -ModuleName $RequiredModule)) {
            return $legacyPython
        }
        if (Test-Path -LiteralPath $bundledPython) {
            return $bundledPython
        }
        if (Test-Path -LiteralPath $legacyPython) {
            return $legacyPython
        }
    }

    throw "No usable Windows Python runtime was found. Install the Codex desktop runtime or repair the local .venv."
}

function Test-FocusProjectPythonModule {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PythonExe,
        [Parameter(Mandatory = $true)]
        [string]$ModuleName
    )

    $probe = "import importlib; importlib.import_module('$ModuleName')"
    try {
        $null = & $PythonExe -c $probe *> $null
        return $LASTEXITCODE -eq 0
    }
    catch {
        return $false
    }
}

function Write-FocusProjectRuntimeBanner {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PythonExe
    )

    if ($PythonExe -like "*codex-primary-runtime*") {
        Write-Host "Using bundled Codex Python runtime bridge for Windows."
        Write-Host "Pure-Python dependencies are bridged from the legacy .venv when needed."
    }
    else {
        Write-Host "Using local .venv interpreter."
    }
}
