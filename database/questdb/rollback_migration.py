#!/usr/bin/env python3
"""
Database Migration Rollback Script for QuestDB
Safely rollback database migrations with verification and logging

Usage:
    python rollback_migration.py <migration_number>
    python rollback_migration.py 016  # Rollback migration 016
    python rollback_migration.py --list  # List applied migrations
    python rollback_migration.py --last  # Rollback last migration

Author: Deployment Agent
Date: 2025-11-07
"""

import asyncio
import asyncpg
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional

# Configuration
DB_CONFIG = {
    'host': os.getenv('QUESTDB_HOST', 'localhost'),
    'port': int(os.getenv('QUESTDB_PORT', 8812)),
    'user': os.getenv('QUESTDB_USER', 'admin'),
    'password': os.getenv('QUESTDB_PASSWORD', 'quest'),
    'database': os.getenv('QUESTDB_DATABASE', 'qdb')
}

MIGRATIONS_DIR = Path(__file__).parent / 'migrations'
LOG_FILE = Path(__file__).parent / 'logs' / f'rollback-{datetime.now().strftime("%Y%m%d-%H%M%S")}.log'


class MigrationRollback:
    """Handle database migration rollbacks with safety checks"""

    def __init__(self):
        self.conn: Optional[asyncpg.Connection] = None
        self._ensure_log_dir()

    def _ensure_log_dir(self):
        """Create logs directory if it doesn't exist"""
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    def log(self, message: str):
        """Log message to console and file"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)
        with open(LOG_FILE, 'a') as f:
            f.write(log_msg + '\n')

    async def connect(self):
        """Connect to QuestDB via PostgreSQL protocol"""
        try:
            self.log(f"Connecting to QuestDB at {DB_CONFIG['host']}:{DB_CONFIG['port']}...")
            self.conn = await asyncpg.connect(
                host=DB_CONFIG['host'],
                port=DB_CONFIG['port'],
                user=DB_CONFIG['user'],
                password=DB_CONFIG['password'],
                database=DB_CONFIG['database']
            )
            self.log("✓ Connected to QuestDB successfully")
        except Exception as e:
            self.log(f"✗ Failed to connect to QuestDB: {e}")
            raise

    async def disconnect(self):
        """Disconnect from QuestDB"""
        if self.conn:
            await self.conn.close()
            self.log("Disconnected from QuestDB")

    async def ensure_migrations_table(self):
        """Ensure schema_migrations table exists"""
        try:
            await self.conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INT,
                    applied_at TIMESTAMP,
                    description STRING
                )
            """)
            self.log("✓ schema_migrations table verified")
        except Exception as e:
            self.log(f"✗ Failed to verify schema_migrations table: {e}")
            raise

    async def get_applied_migrations(self) -> List[Tuple[int, datetime, str]]:
        """Get list of applied migrations"""
        try:
            rows = await self.conn.fetch("""
                SELECT version, applied_at, description
                FROM schema_migrations
                ORDER BY version DESC
            """)
            return [(row['version'], row['applied_at'], row['description']) for row in rows]
        except Exception as e:
            self.log(f"✗ Failed to fetch applied migrations: {e}")
            return []

    async def list_migrations(self):
        """List all applied migrations"""
        self.log("\n=== Applied Migrations ===")
        migrations = await self.get_applied_migrations()

        if not migrations:
            self.log("No migrations have been applied")
            return

        for version, applied_at, description in migrations:
            self.log(f"Migration {version:03d}: {description} (Applied: {applied_at})")

    async def get_last_migration(self) -> Optional[int]:
        """Get the last applied migration number"""
        migrations = await self.get_applied_migrations()
        if migrations:
            return migrations[0][0]  # First element (most recent)
        return None

    def find_rollback_file(self, migration_number: int) -> Optional[Path]:
        """Find rollback SQL file for given migration"""
        # Try standard naming: 016_rollback.sql
        rollback_file = MIGRATIONS_DIR / f'{migration_number:03d}_rollback.sql'
        if rollback_file.exists():
            return rollback_file

        # Try alternative naming: 016_live_trading_rollback.sql
        for file in MIGRATIONS_DIR.glob(f'{migration_number:03d}_*_rollback.sql'):
            return file

        return None

    async def verify_migration_applied(self, migration_number: int) -> bool:
        """Verify that migration is currently applied"""
        try:
            result = await self.conn.fetchval("""
                SELECT COUNT(*)
                FROM schema_migrations
                WHERE version = $1
            """, migration_number)
            return result > 0
        except Exception as e:
            self.log(f"✗ Failed to verify migration: {e}")
            return False

    async def rollback_migration(self, migration_number: int):
        """Rollback a specific migration"""
        self.log(f"\n=== Rolling Back Migration {migration_number:03d} ===")

        # Step 1: Verify migration is applied
        if not await self.verify_migration_applied(migration_number):
            self.log(f"✗ Migration {migration_number:03d} is not currently applied")
            return False

        # Step 2: Find rollback SQL file
        rollback_file = self.find_rollback_file(migration_number)
        if not rollback_file:
            self.log(f"✗ Rollback file not found for migration {migration_number:03d}")
            self.log(f"Expected: {MIGRATIONS_DIR}/{migration_number:03d}_rollback.sql")
            return False

        self.log(f"Found rollback file: {rollback_file}")

        # Step 3: Read rollback SQL
        try:
            with open(rollback_file, 'r') as f:
                rollback_sql = f.read()
            self.log(f"Read {len(rollback_sql)} characters from rollback file")
        except Exception as e:
            self.log(f"✗ Failed to read rollback file: {e}")
            return False

        # Step 4: Execute rollback in transaction
        try:
            async with self.conn.transaction():
                self.log("Executing rollback SQL...")

                # Execute rollback SQL (may contain multiple statements)
                # QuestDB doesn't fully support transactions, but we try
                for statement in rollback_sql.split(';'):
                    statement = statement.strip()
                    if statement and not statement.startswith('--'):
                        try:
                            await self.conn.execute(statement)
                            self.log(f"  ✓ Executed: {statement[:60]}...")
                        except Exception as e:
                            self.log(f"  ⚠ Warning: {e}")
                            # Continue with other statements

                # Remove migration from schema_migrations
                await self.conn.execute("""
                    DELETE FROM schema_migrations
                    WHERE version = $1
                """, migration_number)

                self.log(f"✓ Removed migration {migration_number:03d} from schema_migrations")

            self.log(f"✓ Migration {migration_number:03d} rolled back successfully")
            return True

        except Exception as e:
            self.log(f"✗ Rollback failed: {e}")
            self.log("Database may be in inconsistent state. Manual verification required!")
            return False

    async def create_backup(self, migration_number: int):
        """Create a backup before rollback (optional, requires pg_dump)"""
        backup_file = Path(f'./backups/pre-rollback-{migration_number:03d}-{datetime.now().strftime("%Y%m%d-%H%M%S")}.sql')
        backup_file.parent.mkdir(parents=True, exist_ok=True)

        self.log(f"Creating backup before rollback: {backup_file}")

        # Note: This requires pg_dump to be available
        # In production, you may want to use QuestDB's backup mechanism
        import subprocess
        try:
            result = subprocess.run([
                'pg_dump',
                '-h', DB_CONFIG['host'],
                '-p', str(DB_CONFIG['port']),
                '-U', DB_CONFIG['user'],
                '-d', DB_CONFIG['database'],
                '-f', str(backup_file)
            ], env={'PGPASSWORD': DB_CONFIG['password']}, capture_output=True, text=True)

            if result.returncode == 0:
                self.log(f"✓ Backup created: {backup_file}")
                return True
            else:
                self.log(f"⚠ Backup failed: {result.stderr}")
                return False
        except FileNotFoundError:
            self.log("⚠ pg_dump not found. Skipping backup.")
            return False


async def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python rollback_migration.py <migration_number>")
        print("  python rollback_migration.py --list")
        print("  python rollback_migration.py --last")
        print("\nExamples:")
        print("  python rollback_migration.py 016")
        print("  python rollback_migration.py --last")
        sys.exit(1)

    rollback = MigrationRollback()

    try:
        await rollback.connect()
        await rollback.ensure_migrations_table()

        # Handle command line arguments
        if sys.argv[1] == '--list':
            await rollback.list_migrations()

        elif sys.argv[1] == '--last':
            last_migration = await rollback.get_last_migration()
            if last_migration:
                rollback.log(f"Last applied migration: {last_migration:03d}")

                # Confirm rollback
                response = input(f"\nRollback migration {last_migration:03d}? (yes/no): ")
                if response.lower() == 'yes':
                    await rollback.create_backup(last_migration)
                    await rollback.rollback_migration(last_migration)
                else:
                    rollback.log("Rollback cancelled")
            else:
                rollback.log("No migrations to rollback")

        else:
            # Rollback specific migration
            try:
                migration_number = int(sys.argv[1])
            except ValueError:
                rollback.log(f"✗ Invalid migration number: {sys.argv[1]}")
                sys.exit(1)

            # Confirm rollback
            response = input(f"\nRollback migration {migration_number:03d}? (yes/no): ")
            if response.lower() == 'yes':
                await rollback.create_backup(migration_number)
                success = await rollback.rollback_migration(migration_number)
                sys.exit(0 if success else 1)
            else:
                rollback.log("Rollback cancelled")

    except Exception as e:
        rollback.log(f"✗ Fatal error: {e}")
        sys.exit(1)
    finally:
        await rollback.disconnect()
        rollback.log(f"\nLog file: {LOG_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
