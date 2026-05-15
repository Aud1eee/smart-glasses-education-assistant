$ErrorActionPreference = "Stop"

function Get-FocusProjectPython {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ProjectRoot
    )

    $bundledPython = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
    if (Test-Path -LiteralPath $bundledPython) {
        return $bundledPython
    }

    $legacyPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $legacyPython) {
        return $legacyPython
    }

    throw "No usable Windows Python runtime was found. Install the Codex desktop runtime or repair the local .venv."
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
