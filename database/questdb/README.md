# QuestDB Installation & Migration System

Professional database migration system for FX trading system using QuestDB.

## 📋 Overview

This directory contains:
- **Installation scripts** (PowerShell + Python)
- **Migration system** (version-controlled schema changes)
- **SQL migrations** (incremental database updates)

## 🚀 Quick Start

### Option 1: PowerShell (Windows)

```powershell
cd database/questdb
.\Install-QuestDB.ps1
```

### Option 2: Python (Cross-platform)

```bash
cd database/questdb
pip install psycopg2-binary requests
python install_questdb.py
```

## 📁 Directory Structure

```
database/questdb/
├── Install-QuestDB.ps1          # PowerShell installation script
├── install_questdb.py           # Python installation script
├── README.md                    # This file
└── migrations/                  # Migration files (versioned)
    ├── 001_create_initial_schema.sql
    ├── 002_add_performance_indexes.sql
    └── ...
```

## 🔧 Prerequisites

### QuestDB Running

Ensure QuestDB is running and accessible:
- **Web UI:** http://127.0.0.1:9000
- **PostgreSQL wire:** Port 8812
- **InfluxDB line protocol:** Port 9009

### For PowerShell Script
- Windows PowerShell 5.1+ or PowerShell Core 7+
- QuestDB running locally or remotely

### For Python Script
- Python 3.7+
- Dependencies:
  ```bash
  pip install psycopg2-binary requests
  ```

## 📚 Usage

### Basic Installation

Install all pending migrations:

**PowerShell:**
```powershell
.\Install-QuestDB.ps1
```

**Python:**
```bash
python install_questdb.py
```

### Dry Run (Preview Changes)

See what would be executed without making changes:

**PowerShell:**
```powershell
.\Install-QuestDB.ps1 -DryRun
```

**Python:**
```bash
python install_questdb.py --dry-run
```

### Remote QuestDB

Connect to remote QuestDB instance:

**PowerShell:**
```powershell
.\Install-QuestDB.ps1 -QuestDBHost "192.168.1.40"
```

**Python:**
```bash
python install_questdb.py --host 192.168.1.40
```

### Force Re-run (Dangerous!)

Re-run all migrations (useful for testing):

**PowerShell:**
```powershell
.\Install-QuestDB.ps1 -Force
```

**Python:**
```bash
python install_questdb.py --force
```

### Verbose Output

See detailed execution information:

**PowerShell:**
```powershell
.\Install-QuestDB.ps1 -Verbose
```

**Python:**
```bash
python install_questdb.py  # Verbose by default
```

## 📝 Migration System

### How It Works

1. **Version Control:** Each migration has a numeric prefix (001, 002, etc.)
2. **Tracking:** `schema_migrations` table tracks applied migrations
3. **Idempotent:** Safe to run multiple times - only executes pending migrations
4. **Incremental:** Apply changes incrementally without recreating entire schema

### Migration File Format

**Filename:** `NNN_description.sql`
- `NNN` = 3-digit version number (001, 002, 003, ...)
- `description` = Short description with underscores

**Examples:**
- `001_create_initial_schema.sql`
- `002_add_performance_indexes.sql`
- `003_add_user_authentication.sql`

### Creating New Migrations

1. **Create file** in `migrations/` directory:
   ```bash
   touch migrations/003_add_new_feature.sql
   ```

2. **Write SQL:**
   ```sql
   -- Migration 003: Add New Feature
   -- Date: 2025-10-27
   -- Description: Brief description of changes

   CREATE TABLE new_table (
       id INT,
       name STRING,
       created_at TIMESTAMP
   );

   -- More SQL statements...
   ```

3. **Run migration:**
   ```bash
   python install_questdb.py
   ```

### Migration Best Practices

✅ **DO:**
- Use sequential version numbers (001, 002, 003, ...)
- Include descriptive comments
- Test migrations on dev environment first
- Keep migrations small and focused
- Make migrations idempotent when possible

❌ **DON'T:**
- Skip version numbers
- Modify existing migrations (create new ones instead)
- Delete migrations that have been applied
- Make destructive changes without backups

## 🗄️ Database Tables

After running migrations, the following tables are created:

### Time-Series Tables
- **prices** - OHLCV price data for all symbols
- **indicators** - Calculated indicator values (RSI, EMA, etc.)
- **strategy_signals** - Strategy signal events
- **orders** - Order lifecycle tracking
- **positions** - Position snapshots
- **backtest_results** - Backtest run results
- **system_metrics** - System health metrics
- **error_logs** - Error and exception logs

### Relational Tables
- **strategy_templates** - Strategy template library
- **schema_migrations** - Migration tracking (auto-created)

## 🔍 Verifying Installation

### Check Migration Status

**PowerShell:**
```powershell
# View migration history
Invoke-RestMethod -Uri "http://localhost:9000/exec?query=SELECT%20*%20FROM%20schema_migrations%20ORDER%20BY%20version"
```

**Python:**
```python
import requests
response = requests.get('http://localhost:9000/exec?query=SELECT * FROM schema_migrations ORDER BY version')
print(response.json())
```

### Check Tables

1. **Web UI:** http://127.0.0.1:9000
2. Navigate to **SQL Console**
3. Run:
   ```sql
   SELECT table_name FROM tables() ORDER BY table_name;
   ```

### Query Sample Data

```sql
-- Check prices
SELECT * FROM prices LIMIT 10;

-- Check indicators
SELECT * FROM indicators LIMIT 10;

-- Check templates
SELECT * FROM strategy_templates;
```

## 🐛 Troubleshooting

### Connection Failed

**Error:** Cannot connect to QuestDB

**Solutions:**
1. Verify QuestDB is running:
   ```bash
   # Windows
   netstat -an | findstr "9000 8812"

   # Linux/Mac
   netstat -an | grep -E "9000|8812"
   ```

2. Check Web UI: http://127.0.0.1:9000
3. Check firewall settings
4. Verify QuestDB process is running

### Migration Failed

**Error:** Migration execution failed

**Solutions:**
1. Check SQL syntax in migration file
2. Review error message in console
3. Check `schema_migrations` table for failed entries:
   ```sql
   SELECT * FROM schema_migrations WHERE status = 'failed';
   ```

4. Fix issue and re-run (failed migrations won't execute again)

### Table Already Exists

**Error:** Table already exists

**Solution:**
- This is normal if migration uses `CREATE TABLE IF NOT EXISTS`
- Migration system should handle this gracefully
- If persistent, check migration file for syntax errors

### Python Script: ModuleNotFoundError

**Error:** `ModuleNotFoundError: No module named 'psycopg2'`

**Solution:**
```bash
pip install psycopg2-binary requests
```

## 📊 Migration Table Schema

```sql
CREATE TABLE schema_migrations (
    id INT,                    -- Migration ID (same as version number)
    version STRING,            -- Migration version (001, 002, etc.)
    name STRING,               -- Migration name
    executed_at TIMESTAMP,     -- When migration was executed
    execution_time_ms INT,     -- How long it took (milliseconds)
    status STRING              -- 'success' or 'failed'
);
```

## 🔄 Rollback Strategy

QuestDB migrations are **forward-only** by design. To rollback:

### Option 1: Create Reverse Migration

Create new migration that undoes previous changes:

```sql
-- 004_rollback_feature.sql
DROP TABLE IF EXISTS unwanted_table;
-- Restore previous state
```

### Option 2: Manual Cleanup

1. Drop affected tables manually
2. Remove migration entry:
   ```sql
   DELETE FROM schema_migrations WHERE version = '003';
   ```
3. Re-run migrations

### Option 3: Full Reset (Development Only)

```sql
-- WARNING: This deletes ALL data!
DROP TABLE IF EXISTS prices;
DROP TABLE IF EXISTS indicators;
-- ... drop all tables
DROP TABLE IF EXISTS schema_migrations;
```

Then re-run installation script.

## 🎯 Next Steps

After successful installation:

1. **Verify Data Structure**
   ```sql
   -- Check table count
   SELECT COUNT(*) FROM tables();

   -- Check table sizes
   SELECT table_name, count(*) as rows FROM prices GROUP BY table_name;
   ```

2. **Insert Test Data**
   ```bash
   python scripts/insert_test_data.py
   ```

3. **Start Indicator Scheduler**
   ```bash
   python src/domain/services/indicator_scheduler_questdb.py
   ```

4. **Run Backtest**
   ```bash
   python src/trading/run_backtest.py
   ```

## 📖 Additional Resources

- [QuestDB Documentation](https://questdb.io/docs/)
- [QuestDB SQL Reference](https://questdb.io/docs/reference/sql/)
- [Migration Pattern Best Practices](https://www.liquibase.org/get-started/best-practices)

## 🤝 Contributing

When adding new migrations:

1. Create branch: `git checkout -b feature/new-migration`
2. Add migration file: `migrations/NNN_description.sql`
3. Test locally: `python install_questdb.py --dry-run`
4. Commit: `git add migrations/NNN_description.sql`
5. Push and create PR

## 📜 License

This migration system is part of the FX trading system.

## 🆘 Support

For issues or questions:
1. Check this README
2. Review QuestDB docs
3. Check migration logs
4. Open GitHub issue

---

**Last Updated:** 2025-10-27
**QuestDB Version:** 9.1.0
**Script Version:** 1.0
