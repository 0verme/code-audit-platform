[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$backendDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonPath = Join-Path $backendDir ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $pythonPath)) {
    Write-Error "Virtual environment interpreter not found: $pythonPath"
}

Set-Location -LiteralPath $backendDir
& $pythonPath "app.py"
