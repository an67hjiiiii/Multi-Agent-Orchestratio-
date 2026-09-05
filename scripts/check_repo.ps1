[CmdletBinding()]
param(
    [switch]$SkipBackend,
    [switch]$SkipFrontend,
    [switch]$PolicyOnly
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root

$python = Join-Path $root ".venv\Scripts\python.exe"
$pythonArguments = @()
if (-not (Test-Path -LiteralPath $python)) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($null -eq $pythonCommand) {
        $pythonCommand = Get-Command py -ErrorAction SilentlyContinue
        if ($null -eq $pythonCommand) {
            throw "Python was not found. Create the repository's documented .venv first."
        }
        $python = $pythonCommand.Source
        $pythonArguments = @("-3")
    }
    else {
        $python = $pythonCommand.Source
    }
}

$arguments = @("scripts\check_foundation.py")
if ($SkipBackend) { $arguments += "--skip-backend" }
if ($SkipFrontend) { $arguments += "--skip-frontend" }
if ($PolicyOnly) { $arguments += "--policy-only" }

& $python @pythonArguments @arguments
exit $LASTEXITCODE
