param([int]$Port = 8102, [switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe') -or -not (Test-Path -LiteralPath 'frontend\dist\index.html')) {
    throw 'Run .\Setup.ps1 first to install dependencies and build the frontend.'
}
Write-Host "Warehouse Robot Fleet: http://127.0.0.1:$Port" -ForegroundColor Green
Write-Host 'Press Ctrl+C to stop. No LLM API key is required.'
if (-not $NoBrowser) { Start-Process "http://127.0.0.1:$Port" }
& .\.venv\Scripts\python.exe -m uvicorn backend.api:app --host 127.0.0.1 --port $Port
if ($LASTEXITCODE -ne 0) { throw 'Server stopped with an error. Check whether the port is already in use.' }
