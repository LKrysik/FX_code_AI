#!/usr/bin/env python3
"""
Run Migration 009: Recreate Indicators Table

This script:
1. Connects to QuestDB via HTTP REST API
2. Drops existing indicators table
3. Creates new indicators table with correct schema
4. Verifies the schema

Usage:
    python database/questdb/run_migration_009.py

Requirements:
    - QuestDB must be running (port 9000)
    - requests library installed
"""

import sys
from pathlib import Path
import urllib.parse

try:
    import requests
except ImportError:
    print("ERROR: requests not installed. Run: pip install requests")
    sys.exit(1)


def execute_query(query: str, host: str = "127.0.0.1", port: int = 9000):
    """Execute SQL query via HTTP REST API"""
    try:
        encoded_query = urllib.parse.quote(query)
        url = f"http://{host}:{port}/exec?query={encoded_query}"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise Exception(f"Query failed: {e}")


def run_migration():
    """Run migration 009 to recreate indicators table."""

    migration_file = Path(__file__).parent / "migrations" / "009_recreate_indicators_table.sql"

    if not migration_file.exists():
        print(f"ERROR: Migration file not found: {migration_file}")
        sys.exit(1)

    # Read migration SQL
    with open(migration_file, 'r', encoding='utf-8') as f:
        migration_sql = f.read()

    # Extract SQL statements (skip comments)
    statements = []
    for line in migration_sql.split('\n'):
        line = line.strip()
        if line and not line.startswith('--'):
            statements.append(line)

    sql = ' '.join(statements)

    # Split into individual statements
    sql_commands = [cmd.strip() for cmd in sql.split(';') if cmd.strip()]

    print("=" * 80)
    print("Migration 009: Recreate Indicators Table")
    print("=" * 80)
    print(f"\nMigration file: {migration_file}")
    print(f"SQL commands to execute: {len(sql_commands)}")
    print("\nConnecting to QuestDB...")

    # Test connection
    try:
        test_response = requests.get("http://127.0.0.1:9000/exec?query=SELECT%201", timeout=5)
        test_response.raise_for_status()
        print("✓ Connected to QuestDB at http://127.0.0.1:9000\n")
    except Exception as e:
        print(f"\n✗ ERROR: Cannot connect to QuestDB")
        print(f"   {e}")
        print("\nIs QuestDB running? Start it with:")
        print("   python database/questdb/install_questdb.py")
        sys.exit(1)

    try:
        # Execute each command
        for idx, command in enumerate(sql_commands, 1):
            # Show preview of command
            preview = command[:100] + "..." if len(command) > 100 else command
            print(f"[{idx}/{len(sql_commands)}] Executing: {preview}")

            try:
                result = execute_query(command)
                print(f"    ✓ Success")
            except Exception as e:
                # Some commands may fail if table doesn't exist, etc. - that's OK
                error_str = str(e).lower()
                if "does not exist" in error_str or "already exists" in error_str:
                    print(f"    ⚠ Skipped: {e}")
                else:
                    print(f"    ✗ Error: {e}")
                    raise

        # Verify schema
        print("\n" + "=" * 80)
        print("Verifying indicators table schema...")
        print("=" * 80 + "\n")

        # Get table columns
        result = execute_query("SHOW COLUMNS FROM indicators")

        if not result.get('dataset'):
            print("✗ ERROR: indicators table not found!")
            sys.exit(1)

        print("✓ indicators table exists\n")
        print("Schema:")
        print("-" * 40)
        for row in result['dataset']:
            column_name = row[0]
            column_type = row[1]
            print(f"  {column_name:20s} {column_type}")
        print("-" * 40)

        # Count rows
        count_result = execute_query("SELECT COUNT(*) FROM indicators")
        row_count = count_result['dataset'][0][0] if count_result.get('dataset') else 0

        print(f"\nRows in table: {row_count}")

        if row_count == 0:
            print("✓ Table is empty (fresh start)")
        else:
            print(f"⚠ Table has {row_count} existing rows (from previous migration)")

        print("\n" + "=" * 80)
        print("✓ Migration 009 completed successfully!")
        print("=" * 80)
        print("\nNext steps:")
        print("1. Restart backend server")
        print("2. Add indicators via frontend UI")
        print("3. Verify data appears in QuestDB: SELECT * FROM indicators LIMIT 10;")

    except Exception as e:
        print(f"\n✗ ERROR: Migration failed")
        print(f"   {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    run_migration()
