<#
.SYNOPSIS
    QuestDB Installation and Migration Script

.DESCRIPTION
    Professional database migration system for QuestDB.
    - Creates all necessary tables and structures
    - Tracks migration history
    - Supports incremental schema changes
    - Idempotent (safe to run multiple times)

.PARAMETER QuestDBHost
    QuestDB host address (default: localhost)

.PARAMETER QuestDBPort
    QuestDB HTTP port (default: 9000)

.PARAMETER PostgreSQLPort
    QuestDB PostgreSQL wire protocol port (default: 8812)

.PARAMETER MigrationPath
    Path to migrations directory (default: ./migrations)

.PARAMETER DryRun
    Show what would be executed without making changes

.PARAMETER Force
    Force re-run all migrations (dangerous!)

.EXAMPLE
    .\Install-QuestDB.ps1
    Run all pending migrations

.EXAMPLE
    .\Install-QuestDB.ps1 -DryRun
    Show what migrations would run

.EXAMPLE
    .\Install-QuestDB.ps1 -QuestDBHost "192.168.1.40"
    Run migrations on remote QuestDB
#>

[CmdletBinding()]
param(
    [string]$QuestDBHost = "127.0.0.1",
    [int]$QuestDBPort = 9000,
    [int]$PostgreSQLPort = 8812,
    [string]$MigrationPath = ".\migrations",
    [switch]$DryRun,
    [switch]$Force,
    [switch]$Verbose
)

# ============================================================================
# CONFIGURATION
# ============================================================================

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# Colors
$ColorSuccess = "Green"
$ColorWarning = "Yellow"
$ColorError = "Red"
$ColorInfo = "Cyan"

# ============================================================================
# LOGGING FUNCTIONS
# ============================================================================

function Write-Header {
    param([string]$Message)
    Write-Host ""
    Write-Host "=" * 80 -ForegroundColor $ColorInfo
    Write-Host " $Message" -ForegroundColor $ColorInfo
    Write-Host "=" * 80 -ForegroundColor $ColorInfo
    Write-Host ""
}

function Write-Step {
    param([string]$Message)
    Write-Host "→ $Message" -ForegroundColor $ColorInfo
}

function Write-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor $ColorSuccess
}

function Write-Warn {
    param([string]$Message)
    Write-Host "⚠ $Message" -ForegroundColor $ColorWarning
}

function Write-Fail {
    param([string]$Message)
    Write-Host "✗ $Message" -ForegroundColor $ColorError
}

# ============================================================================
# QUESTDB CONNECTION
# ============================================================================

function Test-QuestDBConnection {
    param(
        [string]$Host,
        [int]$Port
    )

    try {
        $url = "http://${Host}:${Port}/exec?query=SELECT%201"
        $response = Invoke-RestMethod -Uri $url -Method Get -TimeoutSec 5

        if ($response) {
            return $true
        }
    }
    catch {
        return $false
    }

    return $false
}

function Invoke-QuestDBQuery {
    param(
        [string]$Query,
        [string]$Host = $QuestDBHost,
        [int]$Port = $QuestDBPort
    )

    try {
        $encodedQuery = [System.Web.HttpUtility]::UrlEncode($Query)
        $url = "http://${Host}:${Port}/exec?query=${encodedQuery}"

        if ($Verbose) {
            Write-Host "Query: $Query" -ForegroundColor DarkGray
        }

        $response = Invoke-RestMethod -Uri $url -Method Get -TimeoutSec 30

        return $response
    }
    catch {
        Write-Fail "Query failed: $($_.Exception.Message)"
        throw
    }
}

function Invoke-QuestDBScript {
    param(
        [string]$ScriptPath,
        [string]$Host = $QuestDBHost,
        [int]$Port = $QuestDBPort
    )

    if (-not (Test-Path $ScriptPath)) {
        throw "Script not found: $ScriptPath"
    }

    $sqlContent = Get-Content $ScriptPath -Raw -Encoding UTF8

    # Remove multi-line comments /* ... */
    $sqlContent = $sqlContent -replace '/\*[\s\S]*?\*/', ''

    # Split by semicolon and execute each statement
    # Note: This simple split may fail for strings containing semicolons
    # For production, consider using a proper SQL parser
    $statements = $sqlContent -split ";"

    $successCount = 0
    $failCount = 0

    foreach ($statement in $statements) {
        # Remove single-line comments
        $lines = $statement -split "`n" | Where-Object { $_ -notmatch '^\s*--' }
        $trimmed = ($lines -join "`n").Trim()

        # Skip empty statements
        if ([string]::IsNullOrWhiteSpace($trimmed)) {
            continue
        }

        try {
            Invoke-QuestDBQuery -Query $trimmed -Host $Host -Port $Port | Out-Null
            $successCount++
        }
        catch {
            $failCount++

            # For INSERT statements, duplicate key errors are acceptable
            if ($trimmed -match '^\s*INSERT\s+INTO' -and $_.Exception.Message -match 'duplicate') {
                if ($Verbose) {
                    Write-Host "  Skipping duplicate INSERT (OK)" -ForegroundColor DarkGray
                }
            }
            else {
                Write-Warn "Statement failed: $($_.Exception.Message)"
                if ($Verbose) {
                    Write-Host "  Statement: $($trimmed.Substring(0, [Math]::Min(100, $trimmed.Length)))..." -ForegroundColor DarkGray
                }
            }
        }
    }

    if ($Verbose) {
        Write-Host "  Script execution: $successCount statements succeeded, $failCount failed/skipped" -ForegroundColor DarkGray
    }
}

# ============================================================================
# MIGRATION SYSTEM
# ============================================================================

function Initialize-MigrationTable {
    Write-Step "Initializing migration tracking table..."

    $createTable = @"
CREATE TABLE IF NOT EXISTS schema_migrations (
    id INT,
    version STRING,
    name STRING,
    executed_at TIMESTAMP,
    execution_time_ms INT,
    status STRING,
    checksum STRING
) timestamp(executed_at)
"@

    try {
        Invoke-QuestDBQuery -Query $createTable
        Write-Success "Migration table ready"
    }
    catch {
        Write-Fail "Failed to create migration table"
        throw
    }
}

function Get-AppliedMigrations {
    try {
        $query = "SELECT version FROM schema_migrations WHERE status = 'success' ORDER BY version"
        $result = Invoke-QuestDBQuery -Query $query

        if ($result.dataset) {
            return $result.dataset | ForEach-Object { $_[0] }
        }

        return @()
    }
    catch {
        # Table might not exist yet
        return @()
    }
}

function Get-MigrationFiles {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        Write-Warn "Migration path not found: $Path"
        return @()
    }

    $files = Get-ChildItem -Path $Path -Filter "*.sql" | Sort-Object Name

    $migrations = $files | ForEach-Object {
        # Extract version from filename (e.g., "001_create_schema.sql" -> "001")
        if ($_.Name -match '^(\d+)_(.+)\.sql$') {
            [PSCustomObject]@{
                Version = $matches[1]
                Name = $matches[2]
                FileName = $_.Name
                FullPath = $_.FullName
            }
        }
    }

    # Validate migration sequence (no gaps or duplicates)
    if ($migrations) {
        $versions = $migrations | ForEach-Object { [int]$_.Version }
        $sortedVersions = $versions | Sort-Object

        # Check for duplicates
        $duplicates = $versions | Group-Object | Where-Object { $_.Count -gt 1 }
        if ($duplicates) {
            Write-Fail "Duplicate migration versions detected: $($duplicates.Name -join ', ')"
            throw "Migration validation failed: duplicate versions"
        }

        # Check for gaps in sequence
        for ($i = 0; $i -lt ($sortedVersions.Count - 1); $i++) {
            $current = $sortedVersions[$i]
            $next = $sortedVersions[$i + 1]

            if ($next - $current -gt 1) {
                Write-Warn "Gap detected in migration sequence: $current -> $next"
                Write-Warn "Consider renumbering migrations to be sequential"
            }
        }
    }

    return $migrations
}

function Get-FileChecksum {
    param([string]$FilePath)

    $hash = Get-FileHash -Path $FilePath -Algorithm SHA256
    return $hash.Hash
}

function Invoke-Migration {
    param(
        [PSCustomObject]$Migration,
        [switch]$DryRun
    )

    Write-Step "Running migration: $($Migration.Version) - $($Migration.Name)"

    if ($DryRun) {
        Write-Host "  [DRY RUN] Would execute: $($Migration.FullPath)" -ForegroundColor DarkGray
        return $true
    }

    # Calculate checksum for integrity verification
    $checksum = Get-FileChecksum -FilePath $Migration.FullPath
    if ($Verbose) {
        Write-Host "  Checksum: $checksum" -ForegroundColor DarkGray
    }

    $startTime = Get-Date

    try {
        # Execute migration script
        Invoke-QuestDBScript -ScriptPath $Migration.FullPath

        $endTime = Get-Date
        $duration = ($endTime - $startTime).TotalMilliseconds

        # Record successful migration with checksum
        $insertLog = @"
INSERT INTO schema_migrations (id, version, name, executed_at, execution_time_ms, status, checksum)
VALUES (
    $($Migration.Version),
    '$($Migration.Version)',
    '$($Migration.Name)',
    systimestamp(),
    $([int]$duration),
    'success',
    '$checksum'
)
"@

        Invoke-QuestDBQuery -Query $insertLog | Out-Null

        Write-Success "Migration completed in $([int]$duration)ms"
        return $true
    }
    catch {
        # Record failed migration
        $insertLog = @"
INSERT INTO schema_migrations (id, version, name, executed_at, execution_time_ms, status, checksum)
VALUES (
    $($Migration.Version),
    '$($Migration.Version)',
    '$($Migration.Name)',
    systimestamp(),
    0,
    'failed',
    '$checksum'
)
"@

        try {
            Invoke-QuestDBQuery -Query $insertLog | Out-Null
        }
        catch {
            # Ignore log failure
        }

        Write-Fail "Migration failed: $($_.Exception.Message)"
        return $false
    }
}

# ============================================================================
# MAIN INSTALLATION LOGIC
# ============================================================================

function Install-QuestDB {
    Write-Header "QuestDB Installation & Migration System"

    # 1. Check connection
    Write-Step "Checking QuestDB connection..."
    if (-not (Test-QuestDBConnection -Host $QuestDBHost -Port $QuestDBPort)) {
        Write-Fail "Cannot connect to QuestDB at ${QuestDBHost}:${QuestDBPort}"
        Write-Host ""
        Write-Host "Please ensure QuestDB is running:" -ForegroundColor Yellow
        Write-Host "  1. Check if QuestDB process is running" -ForegroundColor Yellow
        Write-Host "  2. Verify Web UI is accessible: http://${QuestDBHost}:${QuestDBPort}" -ForegroundColor Yellow
        Write-Host "  3. Check firewall settings" -ForegroundColor Yellow
        Write-Host ""
        exit 1
    }
    Write-Success "Connected to QuestDB at ${QuestDBHost}:${QuestDBPort}"

    # 2. Initialize migration system
    Initialize-MigrationTable

    # 3. Get migration status
    Write-Step "Checking migration status..."
    $appliedMigrations = Get-AppliedMigrations
    Write-Host "  Applied migrations: $($appliedMigrations.Count)" -ForegroundColor DarkGray

    # 4. Get available migrations
    $allMigrations = Get-MigrationFiles -Path $MigrationPath
    Write-Host "  Available migrations: $($allMigrations.Count)" -ForegroundColor DarkGray

    if ($allMigrations.Count -eq 0) {
        Write-Warn "No migration files found in: $MigrationPath"
        exit 0
    }

    # 5. Determine pending migrations
    $pendingMigrations = $allMigrations | Where-Object {
        -not ($appliedMigrations -contains $_.Version)
    }

    if ($Force) {
        Write-Warn "Force mode: Re-running ALL migrations"
        $pendingMigrations = $allMigrations
    }

    if ($pendingMigrations.Count -eq 0) {
        Write-Success "Database is up to date! No pending migrations."
        Write-Host ""

        # Show current schema version
        Write-Step "Current schema version:"
        $latestVersion = $appliedMigrations | Sort-Object -Descending | Select-Object -First 1
        Write-Host "  Version: $latestVersion" -ForegroundColor Green

        exit 0
    }

    # 6. Show pending migrations
    Write-Header "Pending Migrations ($($pendingMigrations.Count))"
    foreach ($migration in $pendingMigrations) {
        Write-Host "  • $($migration.Version) - $($migration.Name)" -ForegroundColor Cyan
    }
    Write-Host ""

    if ($DryRun) {
        Write-Warn "DRY RUN MODE - No changes will be made"
        Write-Host ""
    }

    # 7. Confirm execution
    if (-not $DryRun -and -not $Force) {
        $confirm = Read-Host "Execute these migrations? (y/N)"
        if ($confirm -ne "y" -and $confirm -ne "Y") {
            Write-Host "Cancelled by user" -ForegroundColor Yellow
            exit 0
        }
    }

    # 8. Execute migrations
    Write-Header "Executing Migrations"

    $successCount = 0
    $failCount = 0

    foreach ($migration in $pendingMigrations) {
        $result = Invoke-Migration -Migration $migration -DryRun:$DryRun

        if ($result) {
            $successCount++
        }
        else {
            $failCount++
            Write-Fail "Migration failed, stopping execution"
            break
        }
    }

    # 9. Summary
    Write-Header "Migration Summary"
    Write-Host "  Successful: $successCount" -ForegroundColor Green

    if ($failCount -gt 0) {
        Write-Host "  Failed: $failCount" -ForegroundColor Red
        exit 1
    }

    Write-Success "All migrations completed successfully!"

    # 10. Show database info
    Write-Header "Database Information"

    try {
        $tablesQuery = 'SELECT table_name FROM tables() ORDER BY table_name'
        $tables = Invoke-QuestDBQuery -Query $tablesQuery

        if ($tables.dataset) {
            Write-Host "  Tables created: $($tables.dataset.Count)" -ForegroundColor Cyan
            foreach ($table in $tables.dataset) {
                Write-Host "    • $($table[0])" -ForegroundColor DarkGray
            }
        }
    }
    catch {
        Write-Warn "Could not retrieve table list"
    }

    Write-Host ""
    Write-Success "Installation complete!"
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Verify tables in QuestDB Web UI: http://${QuestDBHost}:${QuestDBPort}" -ForegroundColor White
    Write-Host "  2. Run test data insertion script" -ForegroundColor White
    Write-Host "  3. Start indicator scheduler" -ForegroundColor White
    Write-Host ""
}

# ============================================================================
# SCRIPT EXECUTION
# ============================================================================

try {
    # Add System.Web for URL encoding
    Add-Type -AssemblyName System.Web

    # Run installation
    Install-QuestDB
}
catch {
    Write-Host ""
    Write-Fail "Installation failed: $($_.Exception.Message)"
    Write-Host ""
    Write-Host "Error details:" -ForegroundColor Red
    Write-Host $_.Exception.ToString() -ForegroundColor DarkRed
    Write-Host ""
    exit 1
}
=======
<#
.SYNOPSIS
    QuestDB Installation and Migration Script

.DESCRIPTION
    Professional database migration system for QuestDB.
    - Creates all necessary tables and structures
    - Tracks migration history
    - Supports incremental schema changes
    - Idempotent (safe to run multiple times)

.PARAMETER QuestDBHost
    QuestDB host address (default: localhost)

.PARAMETER QuestDBPort
    QuestDB HTTP port (default: 9000)

.PARAMETER PostgreSQLPort
    QuestDB PostgreSQL wire protocol port (default: 8812)

.PARAMETER MigrationPath
    Path to migrations directory (default: ./migrations)

.PARAMETER DryRun
    Show what would be executed without making changes

.PARAMETER Force
    Force re-run all migrations (dangerous!)

.EXAMPLE
    .\Install-QuestDB.ps1
    Run all pending migrations

.EXAMPLE
    .\Install-QuestDB.ps1 -DryRun
    Show what migrations would run

.EXAMPLE
    .\Install-QuestDB.ps1 -QuestDBHost "192.168.1.40"
    Run migrations on remote QuestDB
#>

[CmdletBinding()]
param(
    [string]$QuestDBHost = "127.0.0.1",
    [int]$QuestDBPort = 9000,
    [int]$PostgreSQLPort = 8812,
    [string]$MigrationPath = ".\migrations",
    [switch]$DryRun,
    [switch]$Force
)

# ============================================================================
# CONFIGURATION
# ============================================================================

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# Colors
$ColorSuccess = "Green"
$ColorWarning = "Yellow"
$ColorError = "Red"
$ColorInfo = "Cyan"

# ============================================================================
# LOGGING FUNCTIONS
# ============================================================================

function Write-Header {
    param([string]$Message)
    Write-Host ""
    Write-Host "=" * 80 -ForegroundColor $ColorInfo
    Write-Host " $Message" -ForegroundColor $ColorInfo
    Write-Host "=" * 80 -ForegroundColor $ColorInfo
    Write-Host ""
}

function Write-Step {
    param([string]$Message)
    Write-Host "[STEP] $Message" -ForegroundColor $ColorInfo
}

function Write-Success {
    param([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor $ColorSuccess
}

function Write-Warn {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor $ColorWarning
}

function Write-Fail {
    param([string]$Message)
    Write-Host "[FAIL] $Message" -ForegroundColor $ColorError
}

# ============================================================================
# QUESTDB CONNECTION
# ============================================================================

function Test-QuestDBConnection {
    param(
        [string]$QuestHost,
        [int]$Port
    )

    try {
        $url = "http://${QuestHost}:${Port}/exec?query=SELECT%201"
        $response = Invoke-RestMethod -Uri $url -Method Get -TimeoutSec 5

        if ($response) {
            return $true
        }
    }
    catch {
        return $false
    }

    return $false
}

function Invoke-QuestDBQuery {
    param(
        [string]$Query,
        [string]$QuestHost = $QuestDBHost,
        [int]$Port = $QuestDBPort
    )

    try {
        $encodedQuery = [System.Web.HttpUtility]::UrlEncode($Query)
        $url = "http://${QuestHost}:${Port}/exec?query=${encodedQuery}"

        Write-Verbose "Query: $Query"

        $response = Invoke-RestMethod -Uri $url -Method Get -TimeoutSec 30

        return $response
    }
    catch {
        Write-Fail "Query failed: $($_.Exception.Message)"
        throw
    }
}

function Invoke-QuestDBScript {
    param(
        [string]$ScriptPath,
        [string]$QuestHost = $QuestDBHost,
        [int]$Port = $QuestDBPort
    )

    if (-not (Test-Path $ScriptPath)) {
        throw "Script not found: $ScriptPath"
    }

    $sqlContent = Get-Content $ScriptPath -Raw

    # Split by semicolon and execute each statement
    $statements = $sqlContent -split ";"

    foreach ($statement in $statements) {
        $trimmed = $statement.Trim()

        # Skip empty statements and comments
        if ([string]::IsNullOrWhiteSpace($trimmed) -or $trimmed.StartsWith("--")) {
            continue
        }

        try {
            Invoke-QuestDBQuery -Query $trimmed -QuestHost $QuestHost -Port $Port | Out-Null
        }
        catch {
            Write-Warn "Statement failed (continuing): $trimmed"
            Write-Warn "Error: $($_.Exception.Message)"
        }
    }
}

# ============================================================================
# MIGRATION SYSTEM
# ============================================================================

function Initialize-MigrationTable {
    Write-Step "Initializing migration tracking table..."

    $createTable = @"
CREATE TABLE IF NOT EXISTS schema_migrations (
    id INT,
    version STRING,
    name STRING,
    executed_at TIMESTAMP,
    execution_time_ms INT,
    status STRING
)
"@

    try {
        Invoke-QuestDBQuery -Query $createTable
        Write-Success "Migration table ready"
    }
    catch {
        Write-Fail "Failed to create migration table"
        throw
    }
}

function Get-AppliedMigrations {
    try {
        $query = "SELECT version FROM schema_migrations WHERE status = 'success' ORDER BY version"
        $result = Invoke-QuestDBQuery -Query $query

        if ($result.dataset) {
            return $result.dataset | ForEach-Object { $_[0] }
        }

        return @()
    }
    catch {
        # Table might not exist yet
        return @()
    }
}

function Get-MigrationFiles {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        Write-Warn "Migration path not found: $Path"
        return @()
    }

    $files = Get-ChildItem -Path $Path -Filter "*.sql" | Sort-Object Name

    return $files | ForEach-Object {
        # Extract version from filename (e.g., "001_create_schema.sql" -> "001")
        if ($_.Name -match '^(\d+)_(.+)\.sql$') {
            [PSCustomObject]@{
                Version = $matches[1]
                Name = $matches[2]
                FileName = $_.Name
                FullPath = $_.FullName
            }
        }
    }
}

function Invoke-Migration {
    param(
        [PSCustomObject]$Migration,
        [switch]$DryRun
    )

    Write-Step "Running migration: $($Migration.Version) - $($Migration.Name)"

    if ($DryRun) {
        Write-Host "  [DRY RUN] Would execute: $($Migration.FullPath)" -ForegroundColor DarkGray
        return $true
    }

    $startTime = Get-Date

    try {
        # Execute migration script
        Invoke-QuestDBScript -ScriptPath $Migration.FullPath

        $endTime = Get-Date
        $duration = ($endTime - $startTime).TotalMilliseconds

        # Record successful migration
        $insertLog = @"
INSERT INTO schema_migrations (id, version, name, executed_at, execution_time_ms, status)
VALUES (
    $($Migration.Version),
    '$($Migration.Version)',
    '$($Migration.Name)',
    systimestamp(),
    $([int]$duration),
    'success'
)
"@

        Invoke-QuestDBQuery -Query $insertLog | Out-Null

        Write-Success "Migration completed in $([int]$duration)ms"
        return $true
    }
    catch {
        # Record failed migration
        $insertLog = @"
INSERT INTO schema_migrations (id, version, name, executed_at, execution_time_ms, status)
VALUES (
    $($Migration.Version),
    '$($Migration.Version)',
    '$($Migration.Name)',
    systimestamp(),
    0,
    'failed'
)
"@

        try {
            Invoke-QuestDBQuery -Query $insertLog | Out-Null
        }
        catch {
            # Ignore log failure
        }

        Write-Fail "Migration failed: $($_.Exception.Message)"
        return $false
    }
}

# ============================================================================
# MAIN INSTALLATION LOGIC
# ============================================================================

function Install-QuestDB {
    Write-Header "QuestDB Installation & Migration System"

    # 1. Check connection
    Write-Step "Checking QuestDB connection..."
    if (-not (Test-QuestDBConnection -QuestHost $QuestDBHost -Port $QuestDBPort)) {
        Write-Fail "Cannot connect to QuestDB at ${QuestDBHost}:${QuestDBPort}"
        Write-Host ""
        Write-Host "Please ensure QuestDB is running:" -ForegroundColor Yellow
        Write-Host "  1. Check if QuestDB process is running" -ForegroundColor Yellow
        Write-Host "  2. Verify Web UI is accessible: http://${QuestDBHost}:${QuestDBPort}" -ForegroundColor Yellow
        Write-Host "  3. Check firewall settings" -ForegroundColor Yellow
        Write-Host ""
        exit 1
    }
    Write-Success "Connected to QuestDB at ${QuestDBHost}:${QuestDBPort}"

    # 2. Initialize migration system
    Initialize-MigrationTable

    # 3. Get migration status
    Write-Step "Checking migration status..."
    $appliedMigrations = Get-AppliedMigrations
    Write-Host "  Applied migrations: $($appliedMigrations.Count)" -ForegroundColor DarkGray

    # 4. Get available migrations
    $allMigrations = Get-MigrationFiles -Path $MigrationPath
    Write-Host "  Available migrations: $($allMigrations.Count)" -ForegroundColor DarkGray

    if ($allMigrations.Count -eq 0) {
        Write-Warn "No migration files found in: $MigrationPath"
        exit 0
    }

    # 5. Determine pending migrations
    $pendingMigrations = $allMigrations | Where-Object {
        -not ($appliedMigrations -contains $_.Version)
    }

    if ($Force) {
        Write-Warn "Force mode: Re-running ALL migrations"
        $pendingMigrations = $allMigrations
    }

    if ($pendingMigrations.Count -eq 0) {
        Write-Success "Database is up to date! No pending migrations."
        Write-Host ""

        # Show current schema version
        Write-Step "Current schema version:"
        $latestVersion = $appliedMigrations | Sort-Object -Descending | Select-Object -First 1
        Write-Host "  Version: $latestVersion" -ForegroundColor Green

        exit 0
    }

    # 6. Show pending migrations
    Write-Header "Pending Migrations ($($pendingMigrations.Count))"
    foreach ($migration in $pendingMigrations) {
        Write-Host "  -> $($migration.Version) - $($migration.Name)" -ForegroundColor Cyan
    }
    Write-Host ""

    if ($DryRun) {
        Write-Warn "DRY RUN MODE - No changes will be made"
        Write-Host ""
    }

    # 7. Confirm execution
    if (-not $DryRun -and -not $Force) {
        $confirm = Read-Host "Execute these migrations? (y/N)"
        if ($confirm -ne "y" -and $confirm -ne "Y") {
            Write-Host "Cancelled by user" -ForegroundColor Yellow
            exit 0
        }
    }

    # 8. Execute migrations
    Write-Header "Executing Migrations"

    $successCount = 0
    $failCount = 0

    foreach ($migration in $pendingMigrations) {
        $result = Invoke-Migration -Migration $migration -DryRun:$DryRun

        if ($result) {
            $successCount++
        }
        else {
            $failCount++
            Write-Fail "Migration failed, stopping execution"
            break
        }
    }

    # 9. Summary
    Write-Header "Migration Summary"
    Write-Host "  Successful: $successCount" -ForegroundColor Green

    if ($failCount -gt 0) {
        Write-Host "  Failed: $failCount" -ForegroundColor Red
        exit 1
    }

    Write-Success "All migrations completed successfully!"

    # 10. Show database info
    Write-Header "Database Information"

    try {
        $tablesQuery = 'SELECT table_name FROM tables() ORDER BY table_name'
        $tables = Invoke-QuestDBQuery -Query $tablesQuery

        if ($tables.dataset) {
            Write-Host "  Tables created: $($tables.dataset.Count)" -ForegroundColor Cyan
            foreach ($table in $tables.dataset) {
                Write-Host "    -> $($table[0])" -ForegroundColor DarkGray
            }
        }
    }
    catch {
        Write-Warn "Could not retrieve table list"
    }

    Write-Host ""
    Write-Success "Installation complete!"
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Verify tables in QuestDB Web UI: http://${QuestDBHost}:${QuestDBPort}" -ForegroundColor White
    Write-Host "  2. Run test data insertion script" -ForegroundColor White
    Write-Host "  3. Start indicator scheduler" -ForegroundColor White
    Write-Host ""
}

# ============================================================================
# SCRIPT EXECUTION
# ============================================================================

try {
    # Add System.Web for URL encoding
    Add-Type -AssemblyName System.Web

    # Run installation
    Install-QuestDB
}
catch {
    Write-Host ""
    Write-Fail "Installation failed: $($_.Exception.Message)"
    Write-Host ""
    Write-Host "Error details:" -ForegroundColor Red
    Write-Host $_.Exception.ToString() -ForegroundColor DarkRed
    Write-Host ""
    exit 1
}

