param([int]$Port = 8102)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if ($Port -lt 1 -or $Port -gt 65535) { throw 'Port must be between 1 and 65535.' }
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe') -or -not (Test-Path -LiteralPath 'frontend\dist\index.html')) {
    throw 'Run .\Setup.ps1 first.'
}
if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
    throw "Port $Port is in use. Open the existing app or choose another -Port."
}
New-Item -ItemType Directory -Force logs | Out-Null
$serverProcess = Start-Process -FilePath "$PSScriptRoot\.venv\Scripts\python.exe" -ArgumentList @('-m','uvicorn','backend.api:app','--host','127.0.0.1','--port',"$Port") -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -RedirectStandardOutput "$PSScriptRoot\logs\api-$Port.out.log" -RedirectStandardError "$PSScriptRoot\logs\api-$Port.err.log" -PassThru
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/health" -TimeoutSec 1
        if ($health.status -eq 'ok') {
            Write-Host "Warehouse Robot Fleet is running at http://127.0.0.1:$Port" -ForegroundColor Green
            Write-Host "Stop with .\Stop.ps1 -Port $Port. Logs are in the logs folder."
            exit 0
        }
    } catch { }
    if ($serverProcess.HasExited) { throw "Server exited. Read logs\api-$Port.err.log." }
    Start-Sleep -Milliseconds 200
}
throw "Server did not become ready. Read logs\api-$Port.err.log."
