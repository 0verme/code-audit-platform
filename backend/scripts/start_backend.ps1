[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$backendDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$pythonPath = Join-Path $backendDir ".venv\Scripts\python.exe"
$logDir = Join-Path $backendDir "logs"
$stdoutLog = Join-Path $logDir "backend.log"
$stderrLog = Join-Path $logDir "backend.err.log"

if (-not (Test-Path -LiteralPath $pythonPath)) {
    Write-Error "Virtual environment interpreter not found: $pythonPath"
}

if (-not (Test-Path -LiteralPath $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

Set-Location -LiteralPath $backendDir
& $pythonPath "app.py" 1>> $stdoutLog 2>> $stderrLog
