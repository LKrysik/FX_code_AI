# PowerShell script to run migration 023 - Add session_id to trading tables
# Usage: .\run_migration_023.ps1

param(
    [string]$QuestDBHost = "127.0.0.1",
    [int]$QuestDBPort = 9000
)

$ErrorActionPreference = "Stop"

Write-Host "================================================================================================"  -ForegroundColor Cyan
Write-Host " Migration 023: Add session_id to Trading Persistence Tables" -ForegroundColor Cyan
Write-Host "================================================================================================"  -ForegroundColor Cyan
Write-Host ""
Write-Host "Purpose: Enable session separation for backtests, live, and paper trading" -ForegroundColor White
Write-Host "Impact:  Backtest sessions will become visible in frontend Session History" -ForegroundColor White
Write-Host ""

# Test connection
Write-Host "Checking QuestDB connection at http://${QuestDBHost}:${QuestDBPort}..." -ForegroundColor Yellow

try {
    $testUrl = "http://${QuestDBHost}:${QuestDBPort}/exec?query=SELECT%201"
    $testResponse = Invoke-RestMethod -Uri $testUrl -Method Get -TimeoutSec 5
    Write-Host "Connected to QuestDB" -ForegroundColor Green
}
catch {
    Write-Host "ERROR: Cannot connect to QuestDB" -ForegroundColor Red
    Write-Host "  Make sure QuestDB is running on port $QuestDBPort" -ForegroundColor Red
    Write-Host "  You can start it with: .\database\questdb\Install-QuestDB.ps1" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Read migration file
$migrationFile = Join-Path $PSScriptRoot "migrations\023_add_session_id_to_trading_tables.sql"

if (-not (Test-Path $migrationFile)) {
    Write-Host "ERROR: Migration file not found: $migrationFile" -ForegroundColor Red
    exit 1
}

Write-Host "Reading migration file: $migrationFile" -ForegroundColor Yellow

$sqlContent = Get-Content $migrationFile -Raw -Encoding UTF8

# Remove comments and split into statements
$sqlContent = $sqlContent -replace '--[^\r\n]*', ''
$sqlContent = $sqlContent -replace '/\*[\s\S]*?\*/', ''

$statements = $sqlContent -split ';' | Where-Object { $_.Trim() -ne '' }

Write-Host "Statements to execute: $($statements.Count)" -ForegroundColor Yellow
Write-Host ""

# Execute each statement
$successCount = 0
$errorCount = 0

foreach ($statement in $statements) {
    $trimmed = $statement.Trim()
    if ($trimmed -eq '') { continue }

    # Show preview
    $preview = $trimmed.Substring(0, [Math]::Min(80, $trimmed.Length))
    if ($trimmed.Length -gt 80) { $preview += "..." }

    Write-Host "Executing: $preview" -ForegroundColor Gray

    try {
        Add-Type -AssemblyName System.Web
        $encodedQuery = [System.Web.HttpUtility]::UrlEncode($trimmed)
        $url = "http://${QuestDBHost}:${QuestDBPort}/exec?query=${encodedQuery}"

        $response = Invoke-RestMethod -Uri $url -Method Get -TimeoutSec 30

        Write-Host "  Success" -ForegroundColor Green
        $successCount++
    }
    catch {
        $errorMsg = $_.Exception.Message

        # Some errors are OK (column already exists, index already exists)
        if ($errorMsg -match "already exists" -or $errorMsg -match "duplicate") {
            Write-Host "  Skipped: $errorMsg" -ForegroundColor Yellow
            $successCount++
        }
        else {
            Write-Host "  Error: $errorMsg" -ForegroundColor Red
            $errorCount++
        }
    }
}

Write-Host ""
Write-Host "================================================================================================"  -ForegroundColor Cyan

if ($errorCount -eq 0) {
    Write-Host "Migration completed successfully!" -ForegroundColor Green
    Write-Host "  Executed: $successCount statements" -ForegroundColor Green
}
else {
    Write-Host "Migration completed with errors" -ForegroundColor Red
    Write-Host "  Success: $successCount, Errors: $errorCount" -ForegroundColor Red
    exit 1
}

Write-Host "================================================================================================"  -ForegroundColor Cyan
Write-Host ""

# Verify schema changes
Write-Host "Verifying schema changes..." -ForegroundColor Yellow
Write-Host ""

$tables = @("strategy_signals", "orders", "positions")

foreach ($table in $tables) {
    try {
        Add-Type -AssemblyName System.Web
        $query = [System.Web.HttpUtility]::UrlEncode("SHOW COLUMNS FROM $table")
        $url = "http://${QuestDBHost}:${QuestDBPort}/exec?query=${query}"

        $response = Invoke-RestMethod -Uri $url -Method Get -TimeoutSec 10

        if ($response.dataset) {
            $hasSessionId = $false
            foreach ($row in $response.dataset) {
                if ($row[0] -eq "session_id") {
                    $hasSessionId = $true
                    Write-Host "Table '$table' has session_id column (type: $($row[1]))" -ForegroundColor Green
                    break
                }
            }
            
            if (-not $hasSessionId) {
                Write-Host "Table '$table' is missing session_id column!" -ForegroundColor Red
                $errorCount++
            }
        }
    }
    catch {
        Write-Host "Could not verify table '$table': $($_.Exception.Message)" -ForegroundColor Red
        $errorCount++
    }
}

Write-Host ""
Write-Host "================================================================================================"  -ForegroundColor Cyan
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Restart backend server to load updated TradingPersistenceService code" -ForegroundColor White
Write-Host "  2. Run a backtest via /api/backtesting/start" -ForegroundColor White
Write-Host "  3. Check Session History page - backtest should now be visible!" -ForegroundColor White
Write-Host "  4. Verify data: SELECT session_id, COUNT(*) FROM strategy_signals GROUP BY session_id;" -ForegroundColor White
Write-Host ""
Write-Host "Related Documentation:" -ForegroundColor Cyan
Write-Host "  - docs/SESSION_SEPARATION_FIX.md" -ForegroundColor Gray
Write-Host "  - docs/AUDIT_FINAL_REPORT.md" -ForegroundColor Gray
Write-Host ""
