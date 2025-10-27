<#
.SYNOPSIS
    Test QuestDB connection

.DESCRIPTION
    Quick script to test QuestDB connectivity on all ports

.PARAMETER Host
    QuestDB host (default: localhost)
#>

param(
    [string]$Host = "127.0.0.1"
)

Write-Host ""
Write-Host "Testing QuestDB Connection" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

# Test HTTP (Web UI)
Write-Host "Testing HTTP (Web UI) on port 9000..." -NoNewline
try {
    $response = Invoke-RestMethod -Uri "http://${Host}:9000/exec?query=SELECT%201" -TimeoutSec 5
    Write-Host " OK" -ForegroundColor Green
    Write-Host "  Web UI: http://${Host}:9000" -ForegroundColor DarkGray
}
catch {
    Write-Host " FAILED" -ForegroundColor Red
    Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor DarkRed
}

# Test PostgreSQL wire protocol
Write-Host "Testing PostgreSQL wire protocol on port 8812..." -NoNewline
try {
    $null = Test-NetConnection -ComputerName $Host -Port 8812 -InformationLevel Quiet -WarningAction SilentlyContinue
    if ($?) {
        Write-Host " OK" -ForegroundColor Green
        Write-Host "  PostgreSQL: ${Host}:8812" -ForegroundColor DarkGray
    }
    else {
        Write-Host " FAILED" -ForegroundColor Red
    }
}
catch {
    Write-Host " FAILED" -ForegroundColor Red
}

# Test InfluxDB line protocol
Write-Host "Testing InfluxDB line protocol on port 9009..." -NoNewline
try {
    $null = Test-NetConnection -ComputerName $Host -Port 9009 -InformationLevel Quiet -WarningAction SilentlyContinue
    if ($?) {
        Write-Host " OK" -ForegroundColor Green
        Write-Host "  InfluxDB: ${Host}:9009" -ForegroundColor DarkGray
    }
    else {
        Write-Host " FAILED" -ForegroundColor Red
    }
}
catch {
    Write-Host " FAILED" -ForegroundColor Red
}

Write-Host ""
Write-Host "Connection test complete!" -ForegroundColor Cyan
Write-Host ""
