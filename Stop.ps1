param([int]$Port = 8102)
$ErrorActionPreference = 'Stop'
if ($Port -lt 1 -or $Port -gt 65535) { throw 'Port must be between 1 and 65535.' }
$listeners = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
if ($listeners.Count -eq 0) { Write-Host "No server is listening on port $Port."; exit 0 }
foreach ($listener in $listeners) {
    $serverProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $($listener.OwningProcess)"
    $expectedPython = "$PSScriptRoot\.venv\Scripts\python.exe"
    if (-not $serverProcess -or -not $serverProcess.CommandLine -or $serverProcess.CommandLine.IndexOf($expectedPython, [StringComparison]::OrdinalIgnoreCase) -lt 0 -or -not $serverProcess.CommandLine.Contains('uvicorn backend.api:app')) {
        throw "Port $Port belongs to a different process. It was not stopped."
    }
    Stop-Process -Id $serverProcess.ProcessId
}
Write-Host "Warehouse Robot Fleet stopped on port $Port."
