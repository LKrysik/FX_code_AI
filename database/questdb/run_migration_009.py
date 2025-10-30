#!/usr/bin/env python3
"""
Run Migration 009: Recreate Indicators Table

This script:
1. Connects to QuestDB via PostgreSQL protocol
2. Drops existing indicators table
3. Creates new indicators table with correct schema
4. Verifies the schema

Usage:
    python database/questdb/run_migration_009.py

Requirements:
    - QuestDB must be running (port 8812)
    - psycopg2 or asyncpg installed
"""

import asyncio
import sys
from pathlib import Path

try:
    import asyncpg
except ImportError:
    print("ERROR: asyncpg not installed. Run: pip install asyncpg")
    sys.exit(1)


async def run_migration():
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

    try:
        # Connect to QuestDB
        conn = await asyncpg.connect(
            host='127.0.0.1',
            port=8812,
            user='admin',
            password='quest',
            database='qdb'
        )

        print("✓ Connected to QuestDB\n")

        # Execute each command
        for idx, command in enumerate(sql_commands, 1):
            # Show preview of command
            preview = command[:100] + "..." if len(command) > 100 else command
            print(f"[{idx}/{len(sql_commands)}] Executing: {preview}")

            try:
                result = await conn.execute(command)
                print(f"    ✓ Success: {result}")
            except Exception as e:
                # Some commands may fail if table doesn't exist, etc. - that's OK
                if "does not exist" in str(e).lower() or "already exists" in str(e).lower():
                    print(f"    ⚠ Skipped: {e}")
                else:
                    print(f"    ✗ Error: {e}")
                    raise

        # Verify schema
        print("\n" + "=" * 80)
        print("Verifying indicators table schema...")
        print("=" * 80 + "\n")

        # Get table info
        rows = await conn.fetch("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'indicators'
            ORDER BY ordinal_position
        """)

        if not rows:
            print("✗ ERROR: indicators table not found!")
            sys.exit(1)

        print("✓ indicators table exists\n")
        print("Schema:")
        print("-" * 40)
        for row in rows:
            print(f"  {row['column_name']:20s} {row['data_type']}")
        print("-" * 40)

        # Count rows
        count_row = await conn.fetchrow("SELECT COUNT(*) as count FROM indicators")
        row_count = count_row['count'] if count_row else 0

        print(f"\nRows in table: {row_count}")

        if row_count == 0:
            print("✓ Table is empty (fresh start)")
        else:
            print(f"⚠ Table has {row_count} existing rows (from previous migration)")

        await conn.close()

        print("\n" + "=" * 80)
        print("✓ Migration 009 completed successfully!")
        print("=" * 80)
        print("\nNext steps:")
        print("1. Restart backend server")
        print("2. Add indicators via frontend UI")
        print("3. Verify data appears in QuestDB: SELECT * FROM indicators LIMIT 10;")

    except asyncpg.PostgresConnectionError as e:
        print(f"\n✗ ERROR: Cannot connect to QuestDB")
        print(f"   {e}")
        print("\nIs QuestDB running? Start it with:")
        print("   python database/questdb/install_questdb.py")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: Migration failed")
        print(f"   {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(run_migration())
