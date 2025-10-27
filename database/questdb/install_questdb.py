#!/usr/bin/env python3
"""
QuestDB Installation and Migration Script (Python Version)
==========================================================

Professional database migration system for QuestDB.
- Creates all necessary tables and structures
- Tracks migration history
- Supports incremental schema changes
- Idempotent (safe to run multiple times)

Usage:
    python install_questdb.py
    python install_questdb.py --dry-run
    python install_questdb.py --host 192.168.1.40
    python install_questdb.py --force

Requirements:
    pip install psycopg2-binary requests
"""

import argparse
import sys
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import requests
import psycopg2
from psycopg2.extras import RealDictCursor

# ============================================================================
# CONFIGURATION
# ============================================================================

DEFAULT_HOST = "127.0.0.1"
DEFAULT_HTTP_PORT = 9000
DEFAULT_PG_PORT = 8812
MIGRATIONS_DIR = "migrations"

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

# ============================================================================
# LOGGING
# ============================================================================

def print_header(message: str):
    """Print section header"""
    print()
    print(Colors.OKCYAN + "=" * 80)
    print(f" {message}")
    print("=" * 80 + Colors.ENDC)
    print()

def print_step(message: str):
    """Print step message"""
    print(Colors.OKBLUE + f"→ {message}" + Colors.ENDC)

def print_success(message: str):
    """Print success message"""
    print(Colors.OKGREEN + f"✓ {message}" + Colors.ENDC)

def print_warn(message: str):
    """Print warning message"""
    print(Colors.WARNING + f"⚠ {message}" + Colors.ENDC)

def print_fail(message: str):
    """Print error message"""
    print(Colors.FAIL + f"✗ {message}" + Colors.ENDC)

# ============================================================================
# QUESTDB CONNECTION
# ============================================================================

def test_questdb_connection(host: str, port: int) -> bool:
    """Test QuestDB HTTP connection"""
    try:
        url = f"http://{host}:{port}/exec?query=SELECT%201"
        response = requests.get(url, timeout=5)
        return response.status_code == 200
    except Exception:
        return False

def execute_query_http(query: str, host: str, port: int) -> Dict:
    """Execute query via HTTP REST API"""
    try:
        import urllib.parse
        encoded_query = urllib.parse.quote(query)
        url = f"http://{host}:{port}/exec?query={encoded_query}"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise Exception(f"Query failed: {e}")

def execute_query_pg(query: str, host: str, port: int) -> List[Dict]:
    """Execute query via PostgreSQL wire protocol"""
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            user='admin',
            password='quest',
            database='qdb'
        )

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query)
            try:
                results = cur.fetchall()
                conn.commit()
                return [dict(row) for row in results]
            except psycopg2.ProgrammingError:
                # No results (DDL statement)
                conn.commit()
                return []
    finally:
        conn.close()

def execute_script_http(script_path: Path, host: str, port: int):
    """Execute SQL script file via HTTP"""
    with open(script_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    # Split by semicolon and execute each statement
    statements = sql_content.split(';')

    for statement in statements:
        trimmed = statement.strip()

        # Skip empty statements and comments
        if not trimmed or trimmed.startswith('--'):
            continue

        try:
            execute_query_http(trimmed, host, port)
        except Exception as e:
            print_warn(f"Statement failed (continuing): {e}")

# ============================================================================
# MIGRATION SYSTEM
# ============================================================================

def initialize_migration_table(host: str, port: int):
    """Create schema_migrations tracking table"""
    print_step("Initializing migration tracking table...")

    create_table = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    id INT,
    version STRING,
    name STRING,
    executed_at TIMESTAMP,
    execution_time_ms INT,
    status STRING
)
"""

    try:
        execute_query_http(create_table, host, port)
        print_success("Migration table ready")
    except Exception as e:
        print_fail(f"Failed to create migration table: {e}")
        raise

def get_applied_migrations(host: str, port: int) -> List[str]:
    """Get list of applied migration versions"""
    try:
        query = "SELECT version FROM schema_migrations WHERE status = 'success' ORDER BY version"
        result = execute_query_http(query, host, port)

        if 'dataset' in result:
            return [row[0] for row in result['dataset']]

        return []
    except Exception:
        # Table might not exist yet
        return []

def get_migration_files(migrations_dir: Path) -> List[Tuple[str, str, Path]]:
    """Get list of migration files"""
    if not migrations_dir.exists():
        print_warn(f"Migration directory not found: {migrations_dir}")
        return []

    migrations = []
    pattern = re.compile(r'^(\d+)_(.+)\.sql$')

    for file in sorted(migrations_dir.glob('*.sql')):
        match = pattern.match(file.name)
        if match:
            version = match.group(1)
            name = match.group(2)
            migrations.append((version, name, file))

    return migrations

def execute_migration(
    version: str,
    name: str,
    script_path: Path,
    host: str,
    port: int,
    dry_run: bool = False
) -> bool:
    """Execute a single migration"""
    print_step(f"Running migration: {version} - {name}")

    if dry_run:
        print(f"  [DRY RUN] Would execute: {script_path}")
        return True

    start_time = time.time()

    try:
        # Execute migration script
        execute_script_http(script_path, host, port)

        end_time = time.time()
        duration_ms = int((end_time - start_time) * 1000)

        # Record successful migration
        insert_log = f"""
INSERT INTO schema_migrations (id, version, name, executed_at, execution_time_ms, status)
VALUES (
    {version},
    '{version}',
    '{name}',
    systimestamp(),
    {duration_ms},
    'success'
)
"""

        execute_query_http(insert_log, host, port)

        print_success(f"Migration completed in {duration_ms}ms")
        return True

    except Exception as e:
        # Record failed migration
        insert_log = f"""
INSERT INTO schema_migrations (id, version, name, executed_at, execution_time_ms, status)
VALUES (
    {version},
    '{version}',
    '{name}',
    systimestamp(),
    0,
    'failed'
)
"""

        try:
            execute_query_http(insert_log, host, port)
        except Exception:
            pass  # Ignore log failure

        print_fail(f"Migration failed: {e}")
        return False

# ============================================================================
# MAIN INSTALLATION
# ============================================================================

def install_questdb(args):
    """Main installation logic"""
    print_header("QuestDB Installation & Migration System")

    # 1. Check connection
    print_step("Checking QuestDB connection...")
    if not test_questdb_connection(args.host, args.http_port):
        print_fail(f"Cannot connect to QuestDB at {args.host}:{args.http_port}")
        print()
        print("Please ensure QuestDB is running:")
        print(f"  1. Check if QuestDB process is running")
        print(f"  2. Verify Web UI is accessible: http://{args.host}:{args.http_port}")
        print(f"  3. Check firewall settings")
        print()
        sys.exit(1)

    print_success(f"Connected to QuestDB at {args.host}:{args.http_port}")

    # 2. Initialize migration system
    initialize_migration_table(args.host, args.http_port)

    # 3. Get migration status
    print_step("Checking migration status...")
    applied_migrations = get_applied_migrations(args.host, args.http_port)
    print(f"  Applied migrations: {len(applied_migrations)}")

    # 4. Get available migrations
    migrations_path = Path(args.migrations_dir)
    all_migrations = get_migration_files(migrations_path)
    print(f"  Available migrations: {len(all_migrations)}")

    if not all_migrations:
        print_warn(f"No migration files found in: {migrations_path}")
        sys.exit(0)

    # 5. Determine pending migrations
    pending_migrations = [
        m for m in all_migrations
        if m[0] not in applied_migrations
    ]

    if args.force:
        print_warn("Force mode: Re-running ALL migrations")
        pending_migrations = all_migrations

    if not pending_migrations:
        print_success("Database is up to date! No pending migrations.")
        print()

        # Show current schema version
        print_step("Current schema version:")
        latest_version = sorted(applied_migrations)[-1] if applied_migrations else "None"
        print(f"  Version: {latest_version}")

        sys.exit(0)

    # 6. Show pending migrations
    print_header(f"Pending Migrations ({len(pending_migrations)})")
    for version, name, _ in pending_migrations:
        print(f"  • {version} - {name}")
    print()

    if args.dry_run:
        print_warn("DRY RUN MODE - No changes will be made")
        print()

    # 7. Confirm execution
    if not args.dry_run and not args.force and not args.yes:
        response = input("Execute these migrations? (y/N): ")
        if response.lower() != 'y':
            print("Cancelled by user")
            sys.exit(0)

    # 8. Execute migrations
    print_header("Executing Migrations")

    success_count = 0
    fail_count = 0

    for version, name, script_path in pending_migrations:
        result = execute_migration(
            version, name, script_path,
            args.host, args.http_port,
            args.dry_run
        )

        if result:
            success_count += 1
        else:
            fail_count += 1
            print_fail("Migration failed, stopping execution")
            break

    # 9. Summary
    print_header("Migration Summary")
    print(f"  Successful: {success_count}")

    if fail_count > 0:
        print(f"  Failed: {fail_count}")
        sys.exit(1)

    print_success("All migrations completed successfully!")

    # 10. Show database info
    print_header("Database Information")

    try:
        result = execute_query_http("SELECT table_name FROM tables() ORDER BY table_name", args.host, args.http_port)

        if 'dataset' in result:
            print(f"  Tables created: {len(result['dataset'])}")
            for table in result['dataset']:
                print(f"    • {table[0]}")
    except Exception:
        print_warn("Could not retrieve table list")

    print()
    print_success("Installation complete!")
    print()
    print("Next steps:")
    print(f"  1. Verify tables in QuestDB Web UI: http://{args.host}:{args.http_port}")
    print(f"  2. Run test data insertion script")
    print(f"  3. Start indicator scheduler")
    print()

# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="QuestDB Installation and Migration System",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--host',
        default=DEFAULT_HOST,
        help=f'QuestDB host address (default: {DEFAULT_HOST})'
    )

    parser.add_argument(
        '--http-port',
        type=int,
        default=DEFAULT_HTTP_PORT,
        help=f'QuestDB HTTP port (default: {DEFAULT_HTTP_PORT})'
    )

    parser.add_argument(
        '--pg-port',
        type=int,
        default=DEFAULT_PG_PORT,
        help=f'QuestDB PostgreSQL port (default: {DEFAULT_PG_PORT})'
    )

    parser.add_argument(
        '--migrations-dir',
        default=MIGRATIONS_DIR,
        help=f'Path to migrations directory (default: {MIGRATIONS_DIR})'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be executed without making changes'
    )

    parser.add_argument(
        '--force',
        action='store_true',
        help='Force re-run all migrations (dangerous!)'
    )

    parser.add_argument(
        '--yes', '-y',
        action='store_true',
        help='Automatic yes to prompts'
    )

    args = parser.parse_args()

    try:
        install_questdb(args)
    except Exception as e:
        print()
        print_fail(f"Installation failed: {e}")
        print()
        import traceback
        traceback.print_exc()
        print()
        sys.exit(1)

if __name__ == '__main__':
    main()
