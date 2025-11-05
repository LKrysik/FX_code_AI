#!/usr/bin/env python3
"""
One-Time Migration: Strategy JSON Files → QuestDB
=================================================

ARCHITECTURE CHANGE (2025-11-05):
File-based strategy storage (config/strategies/*.json) has been deprecated.
QuestDB is now the single source of truth for strategy persistence.

This script migrates existing JSON strategy files into QuestDB strategies table.

Usage:
    # Ensure QuestDB is running
    python database/questdb/install_questdb.py  # If not already running

    # Run migration
    python scripts/migrate_strategy_json_to_questdb.py

    # (Optional) Backup JSON files after verification
    tar -czf config/strategies_backup_$(date +%Y%m%d).tar.gz config/strategies/

WARNING: This script does NOT delete JSON files automatically. Manual cleanup required.
"""

import asyncio
import json
import traceback
from pathlib import Path
from datetime import datetime
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.domain.services.strategy_storage_questdb import (
    QuestDBStrategyStorage,
    StrategyStorageError,
    StrategyNotFoundError
)


class StrategyMigrator:
    """Migrates strategy JSON files to QuestDB"""

    def __init__(self, json_dir: Path, questdb_config: dict):
        self.json_dir = json_dir
        self.questdb_config = questdb_config
        self.storage = None

        # Migration statistics
        self.stats = {
            "total_files": 0,
            "migrated": 0,
            "skipped": 0,
            "errors": 0,
            "error_details": []
        }

    async def initialize(self):
        """Initialize QuestDB connection"""
        print("🔌 Connecting to QuestDB...")
        self.storage = QuestDBStrategyStorage(**self.questdb_config)

        try:
            await self.storage.initialize()
            print(f"✅ Connected to QuestDB at {self.questdb_config['host']}:{self.questdb_config['port']}")
        except Exception as e:
            print(f"❌ Failed to connect to QuestDB: {e}")
            print(f"   Ensure QuestDB is running on port {self.questdb_config['port']}")
            print(f"   Run: python database/questdb/install_questdb.py")
            raise

    async def close(self):
        """Close QuestDB connection"""
        if self.storage:
            await self.storage.close()

    async def migrate_strategy_file(self, json_file: Path) -> bool:
        """
        Migrate a single strategy JSON file to QuestDB.

        Returns:
            True if migrated, False if skipped
        """
        try:
            # Read JSON file
            with open(json_file, 'r', encoding='utf-8') as f:
                strategy_data = json.load(f)

            # Extract strategy ID and name
            strategy_id = strategy_data.get("id")
            strategy_name = strategy_data.get("strategy_name", "Unknown")

            if not strategy_id:
                print(f"⚠️  SKIP {json_file.name}: No 'id' field found")
                self.stats["skipped"] += 1
                return False

            # Check if already exists in QuestDB
            try:
                existing = await self.storage.read_strategy(strategy_id)
                print(f"⏭️  SKIP {json_file.name}: Already in QuestDB")
                print(f"      ID: {strategy_id}")
                print(f"      Name: {existing.get('strategy_name')}")
                self.stats["skipped"] += 1
                return False
            except StrategyNotFoundError:
                # Not found - proceed with migration
                pass

            # Migrate to QuestDB
            new_id = await self.storage.create_strategy(strategy_data)

            print(f"✅ MIGRATED {json_file.name}")
            print(f"      ID: {new_id}")
            print(f"      Name: {strategy_name}")

            self.stats["migrated"] += 1
            return True

        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON: {e}"
            print(f"❌ ERROR {json_file.name}: {error_msg}")
            self.stats["errors"] += 1
            self.stats["error_details"].append({
                "file": json_file.name,
                "error": error_msg
            })
            return False

        except Exception as e:
            error_msg = str(e)
            print(f"❌ ERROR {json_file.name}: {error_msg}")
            print(f"   Traceback: {traceback.format_exc()}")
            self.stats["errors"] += 1
            self.stats["error_details"].append({
                "file": json_file.name,
                "error": error_msg,
                "traceback": traceback.format_exc()
            })
            return False

    async def migrate_all(self):
        """Migrate all JSON files in directory"""
        print(f"\n📂 Scanning directory: {self.json_dir}")

        # Find all JSON files
        json_files = list(self.json_dir.glob("*.json"))
        self.stats["total_files"] = len(json_files)

        if self.stats["total_files"] == 0:
            print(f"⚠️  No JSON files found in {self.json_dir}")
            return

        print(f"   Found {self.stats['total_files']} strategy files\n")

        # Migrate each file
        for json_file in sorted(json_files):
            await self.migrate_strategy_file(json_file)
            print()  # Blank line between strategies

    def print_summary(self):
        """Print migration summary"""
        print("=" * 70)
        print("📊 MIGRATION SUMMARY")
        print("=" * 70)
        print(f"Total Files:  {self.stats['total_files']}")
        print(f"✅ Migrated:  {self.stats['migrated']}")
        print(f"⏭️  Skipped:   {self.stats['skipped']} (already in QuestDB)")
        print(f"❌ Errors:    {self.stats['errors']}")
        print()

        if self.stats["migrated"] > 0:
            print("✅ SUCCESS: Strategies have been migrated to QuestDB")
            print()
            print("📋 NEXT STEPS:")
            print("  1. Verify strategies accessible via API:")
            print("     curl http://localhost:8080/api/strategies")
            print()
            print("  2. Backup JSON files (recommended):")
            print(f"     tar -czf config/strategies_backup_$(date +%Y%m%d).tar.gz {self.json_dir}")
            print()
            print("  3. (Optional) Delete JSON files after verification:")
            print(f"     rm {self.json_dir}/*.json")
            print()

        if self.stats["errors"] > 0:
            print("⚠️  WARNING: Some files failed to migrate")
            print()
            print("Error Details:")
            for i, error in enumerate(self.stats["error_details"], 1):
                print(f"  {i}. {error['file']}: {error['error']}")
            print()

        if self.stats["skipped"] > 0 and self.stats["migrated"] == 0:
            print("ℹ️  All strategies already in QuestDB - nothing to migrate")
            print()


async def main():
    """Main migration entrypoint"""
    print("=" * 70)
    print("Strategy Migration: JSON → QuestDB")
    print("=" * 70)
    print()

    # Configuration
    json_dir = Path("config/strategies")
    questdb_config = {
        "host": "127.0.0.1",
        "port": 8812,
        "user": "admin",
        "password": "quest",
        "database": "qdb"
    }

    # Verify JSON directory exists
    if not json_dir.exists():
        print(f"❌ ERROR: Directory not found: {json_dir}")
        print(f"   Expected location: {json_dir.absolute()}")
        return 1

    # Create migrator
    migrator = StrategyMigrator(json_dir, questdb_config)

    try:
        # Initialize connection
        await migrator.initialize()

        # Run migration
        await migrator.migrate_all()

        # Print summary
        migrator.print_summary()

        # Return exit code
        if migrator.stats["errors"] > 0:
            return 1  # Partial failure
        else:
            return 0  # Success

    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        return 1

    finally:
        await migrator.close()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
