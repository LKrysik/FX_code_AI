# Simple PowerShell script to run migration 009
# Usage: .\run_migration_009.ps1

param(
    [string]$QuestDBHost = "127.0.0.1",
    [int]$QuestDBPort = 9000
)

$ErrorActionPreference = "Stop"

Write-Host "================================================================================================"  -ForegroundColor Cyan
Write-Host " Migration 009: Recreate Indicators Table" -ForegroundColor Cyan
Write-Host "================================================================================================"  -ForegroundColor Cyan
Write-Host ""

# Test connection
Write-Host "Checking QuestDB connection at http://${QuestDBHost}:${QuestDBPort}..." -ForegroundColor Yellow

try {
    $testUrl = "http://${QuestDBHost}:${QuestDBPort}/exec?query=SELECT%201"
    $testResponse = Invoke-RestMethod -Uri $testUrl -Method Get -TimeoutSec 5
    Write-Host "✓ Connected to QuestDB" -ForegroundColor Green
}
catch {
    Write-Host "✗ ERROR: Cannot connect to QuestDB" -ForegroundColor Red
    Write-Host "  Make sure QuestDB is running on port $QuestDBPort" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Read migration file
$migrationFile = Join-Path $PSScriptRoot "migrations\009_recreate_indicators_table.sql"

if (-not (Test-Path $migrationFile)) {
    Write-Host "✗ ERROR: Migration file not found: $migrationFile" -ForegroundColor Red
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

        Write-Host "  ✓ Success" -ForegroundColor Green
        $successCount++
    }
    catch {
        $errorMsg = $_.Exception.Message

        # Some errors are OK (table doesn't exist, etc.)
        if ($errorMsg -match "does not exist" -or $errorMsg -match "already exists") {
            Write-Host "  ⚠ Skipped: $errorMsg" -ForegroundColor Yellow
        }
        else {
            Write-Host "  ✗ Error: $errorMsg" -ForegroundColor Red
            $errorCount++
        }
    }
}

Write-Host ""
Write-Host "================================================================================================"  -ForegroundColor Cyan

if ($errorCount -eq 0) {
    Write-Host "✓ Migration completed successfully!" -ForegroundColor Green
    Write-Host "  Executed: $successCount statements" -ForegroundColor Green
}
else {
    Write-Host "✗ Migration completed with errors" -ForegroundColor Red
    Write-Host "  Success: $successCount, Errors: $errorCount" -ForegroundColor Red
    exit 1
}

Write-Host "================================================================================================"  -ForegroundColor Cyan
Write-Host ""

# Verify table
Write-Host "Verifying indicators table schema..." -ForegroundColor Yellow

try {
    Add-Type -AssemblyName System.Web
    $query = [System.Web.HttpUtility]::UrlEncode("SHOW COLUMNS FROM indicators")
    $url = "http://${QuestDBHost}:${QuestDBPort}/exec?query=${query}"

    $response = Invoke-RestMethod -Uri $url -Method Get -TimeoutSec 10

    if ($response.dataset) {
        Write-Host "✓ Table exists with $($response.dataset.Count) columns:" -ForegroundColor Green
        foreach ($row in $response.dataset) {
            $colName = $row[0]
            $colType = $row[1]
            Write-Host "  - ${colName}: $colType" -ForegroundColor Gray
        }
    }
}
catch {
    Write-Host "✗ Could not verify table: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Restart backend server" -ForegroundColor White
Write-Host "  2. Add indicators via frontend UI" -ForegroundColor White
Write-Host "  3. Verify data in QuestDB: SELECT * FROM indicators LIMIT 10;" -ForegroundColor White
Write-Host ""
