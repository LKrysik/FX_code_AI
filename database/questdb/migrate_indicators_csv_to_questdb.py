#!/usr/bin/env python3
"""
CSV Indicators to QuestDB Migration Script
===========================================

Migrates historical indicator data from CSV files to QuestDB.

This script finds indicator CSV files in the data directory structure:
    data/{session_id}/{symbol}/indicators/{variant_type}_{variant_id}.csv

And migrates them to the QuestDB indicators table with proper session_id linking.

Usage:
    python migrate_indicators_csv_to_questdb.py [OPTIONS]

Options:
    --data-dir PATH       Path to data directory (default: ./data)
    --dry-run             Show what would be migrated without actually migrating
    --session SESSION_ID  Migrate only specific session (default: all sessions)
    --symbol SYMBOL       Migrate only specific symbol (default: all symbols)
    --batch-size SIZE     Batch size for DB writes (default: 1000)
    --skip-errors         Continue migration even if errors occur
    --verbose             Show detailed progress

Example:
    # Migrate all indicators
    python migrate_indicators_csv_to_questdb.py

    # Dry run to see what would be migrated
    python migrate_indicators_csv_to_questdb.py --dry-run

    # Migrate specific session
    python migrate_indicators_csv_to_questdb.py --session exec_20251027_123456

    # Migrate specific symbol across all sessions
    python migrate_indicators_csv_to_questdb.py --symbol BTC/USDT
"""

import sys
import os
import argparse
import asyncio
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from data_feed.questdb_provider import QuestDBProvider
from core.logger import StructuredLogger, get_logger


class IndicatorCSVMigrator:
    """Migrates indicator CSV data to QuestDB"""

    def __init__(
        self,
        data_dir: Path,
        db_provider: QuestDBProvider,
        logger: StructuredLogger,
        batch_size: int = 1000,
        skip_errors: bool = False
    ):
        self.data_dir = data_dir
        self.db_provider = db_provider
        self.logger = logger
        self.batch_size = batch_size
        self.skip_errors = skip_errors

        # Migration statistics
        self.stats = {
            'indicators_found': 0,
            'indicators_migrated': 0,
            'indicators_skipped': 0,
            'indicators_failed': 0,
            'total_records': 0,
            'sessions_processed': set(),
            'errors': []
        }

    def find_indicator_files(
        self,
        session_filter: Optional[str] = None,
        symbol_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Find all indicator CSV files in data directory.

        Args:
            session_filter: Only find indicators for specific session
            symbol_filter: Only find indicators for specific symbol

        Returns:
            List of indicator file metadata dictionaries
        """
        indicator_files = []

        if not self.data_dir.exists():
            self.logger.warning("migration.data_dir_not_found", {
                "data_dir": str(self.data_dir)
            })
            return indicator_files

        # Scan for session directories
        session_pattern = session_filter if session_filter else "*"
        for session_path in self.data_dir.glob(session_pattern):
            if not session_path.is_dir():
                continue

            session_id = session_path.name

            # Scan for symbol directories
            symbol_pattern = symbol_filter if symbol_filter else "*"
            for symbol_path in session_path.glob(symbol_pattern):
                if not symbol_path.is_dir():
                    continue

                symbol = symbol_path.name

                # Look for indicators subdirectory
                indicators_dir = symbol_path / "indicators"
                if not indicators_dir.exists() or not indicators_dir.is_dir():
                    continue

                # Find all CSV files in indicators directory
                # Format: {variant_type}_{variant_id}.csv
                for csv_file in indicators_dir.glob("*.csv"):
                    # Parse filename to extract variant_type and variant_id
                    filename = csv_file.stem  # Remove .csv extension
                    parts = filename.split('_', 1)
                    if len(parts) != 2:
                        self.logger.warning("migration.invalid_filename", {
                            "file": str(csv_file),
                            "expected_format": "variant_type_variant_id.csv"
                        })
                        continue

                    variant_type, variant_id = parts

                    indicator_files.append({
                        'session_id': session_id,
                        'symbol': symbol,
                        'variant_type': variant_type,
                        'variant_id': variant_id,
                        'file_path': csv_file,
                        'indicator_id': f"{variant_type}_{variant_id}"
                    })

        self.stats['indicators_found'] = len(indicator_files)
        return indicator_files

    async def migrate_indicator_file(
        self,
        file_info: Dict[str, Any],
        dry_run: bool = False
    ) -> bool:
        """
        Migrate single indicator CSV file to QuestDB.

        Args:
            file_info: Indicator file metadata
            dry_run: If True, don't actually insert to database

        Returns:
            True if migration successful, False otherwise
        """
        session_id = file_info['session_id']
        symbol = file_info['symbol']
        indicator_id = file_info['indicator_id']
        file_path = file_info['file_path']

        self.logger.info("migration.indicator_start", {
            "session_id": session_id,
            "symbol": symbol,
            "indicator_id": indicator_id,
            "file": str(file_path)
        })

        try:
            # Check if already migrated by querying database
            if not dry_run:
                existing_query = f"""
                    SELECT COUNT(*) as cnt
                    FROM indicators
                    WHERE session_id = '{session_id}'
                      AND symbol = '{symbol}'
                      AND indicator_id = '{indicator_id}'
                """
                existing_result = await self.db_provider.execute_query(existing_query)
                existing_count = existing_result[0]['cnt'] if existing_result else 0

                if existing_count > 0:
                    self.logger.info("migration.indicator_already_exists", {
                        "session_id": session_id,
                        "symbol": symbol,
                        "indicator_id": indicator_id,
                        "existing_rows": existing_count
                    })
                    self.stats['indicators_skipped'] += 1
                    return True

            # Read CSV file
            indicators_batch = []
            row_count = 0

            with file_path.open('r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)

                for row in reader:
                    try:
                        # Parse CSV row
                        # Expected columns: timestamp, value, confidence (optional)
                        timestamp = float(row.get('timestamp', 0))
                        value = float(row.get('value', 0))
                        confidence = float(row['confidence']) if 'confidence' in row and row['confidence'] else None

                        # Convert timestamp to datetime
                        timestamp_dt = datetime.fromtimestamp(timestamp)

                        indicators_batch.append({
                            'session_id': session_id,
                            'symbol': symbol,
                            'indicator_id': indicator_id,
                            'timestamp': timestamp_dt,
                            'value': value,
                            'confidence': confidence
                        })

                        row_count += 1

                        # Write batch if full
                        if len(indicators_batch) >= self.batch_size:
                            if not dry_run:
                                inserted = await self.db_provider.insert_indicators_batch(indicators_batch)
                                self.stats['total_records'] += inserted
                            else:
                                self.stats['total_records'] += len(indicators_batch)

                            indicators_batch = []

                    except (KeyError, ValueError, TypeError) as e:
                        error_msg = f"Invalid row in {file_path}: {row} - {str(e)}"
                        self.logger.warning("migration.invalid_row", {
                            "file": str(file_path),
                            "row": row,
                            "error": str(e)
                        })
                        self.stats['errors'].append(error_msg)

                        if not self.skip_errors:
                            raise

            # Write remaining batch
            if indicators_batch:
                if not dry_run:
                    inserted = await self.db_provider.insert_indicators_batch(indicators_batch)
                    self.stats['total_records'] += inserted
                else:
                    self.stats['total_records'] += len(indicators_batch)

            self.logger.info("migration.indicator_complete", {
                "session_id": session_id,
                "symbol": symbol,
                "indicator_id": indicator_id,
                "rows_migrated": row_count
            })

            self.stats['indicators_migrated'] += 1
            self.stats['sessions_processed'].add(session_id)
            return True

        except Exception as e:
            error_msg = f"Failed to migrate {file_path}: {str(e)}"
            self.logger.error("migration.indicator_failed", {
                "session_id": session_id,
                "symbol": symbol,
                "indicator_id": indicator_id,
                "file": str(file_path),
                "error": str(e)
            })
            self.stats['errors'].append(error_msg)
            self.stats['indicators_failed'] += 1

            if not self.skip_errors:
                raise

            return False

    async def migrate_all(
        self,
        session_filter: Optional[str] = None,
        symbol_filter: Optional[str] = None,
        dry_run: bool = False,
        verbose: bool = False
    ) -> Dict[str, Any]:
        """
        Migrate all indicator CSV files to QuestDB.

        Args:
            session_filter: Only migrate specific session
            symbol_filter: Only migrate specific symbol
            dry_run: If True, don't actually insert to database
            verbose: Show detailed progress

        Returns:
            Migration statistics dictionary
        """
        self.logger.info("migration.start", {
            "data_dir": str(self.data_dir),
            "session_filter": session_filter,
            "symbol_filter": symbol_filter,
            "dry_run": dry_run
        })

        # Find all indicator files
        indicator_files = self.find_indicator_files(session_filter, symbol_filter)

        if not indicator_files:
            self.logger.warning("migration.no_indicators_found", {
                "data_dir": str(self.data_dir),
                "session_filter": session_filter,
                "symbol_filter": symbol_filter
            })
            return self.stats

        self.logger.info("migration.indicators_found", {
            "count": len(indicator_files)
        })

        # Migrate each indicator file
        for idx, file_info in enumerate(indicator_files, 1):
            if verbose:
                print(f"[{idx}/{len(indicator_files)}] Migrating {file_info['indicator_id']} "
                      f"for {file_info['session_id']}/{file_info['symbol']}...")

            await self.migrate_indicator_file(file_info, dry_run)

        # Print summary
        self.stats['sessions_processed'] = len(self.stats['sessions_processed'])

        self.logger.info("migration.complete", {
            "stats": self.stats
        })

        return self.stats


async def main():
    """Main migration function"""
    parser = argparse.ArgumentParser(
        description="Migrate indicator CSV files to QuestDB"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="./data",
        help="Path to data directory (default: ./data)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without actually migrating"
    )
    parser.add_argument(
        "--session",
        type=str,
        default=None,
        help="Migrate only specific session"
    )
    parser.add_argument(
        "--symbol",
        type=str,
        default=None,
        help="Migrate only specific symbol"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Batch size for DB writes (default: 1000)"
    )
    parser.add_argument(
        "--skip-errors",
        action="store_true",
        help="Continue migration even if errors occur"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed progress"
    )

    args = parser.parse_args()

    # Initialize logger
    # ✅ LOGGER FIX: Use get_logger() instead of direct StructuredLogger
    logger = get_logger("indicator_migration")

    # Initialize QuestDB provider
    logger.info("migration.init_questdb", {})
    questdb_provider = QuestDBProvider(
        ilp_host='127.0.0.1',
        ilp_port=9009,
        pg_host='127.0.0.1',
        pg_port=8812
    )

    # Test connection
    try:
        await questdb_provider.initialize()
        health = await questdb_provider.health_check()
        if not all(health.values()):
            logger.error("migration.questdb_not_healthy", {"health": health})
            print("ERROR: QuestDB is not healthy. Please check connection.")
            return 1
    except Exception as e:
        logger.error("migration.questdb_connection_failed", {"error": str(e)})
        print(f"ERROR: Failed to connect to QuestDB: {str(e)}")
        return 1

    # Initialize migrator
    data_dir = Path(args.data_dir).resolve()
    migrator = IndicatorCSVMigrator(
        data_dir=data_dir,
        db_provider=questdb_provider,
        logger=logger,
        batch_size=args.batch_size,
        skip_errors=args.skip_errors
    )

    # Run migration
    try:
        stats = await migrator.migrate_all(
            session_filter=args.session,
            symbol_filter=args.symbol,
            dry_run=args.dry_run,
            verbose=args.verbose
        )

        # Print summary
        print("\n" + "=" * 60)
        print("MIGRATION SUMMARY")
        print("=" * 60)
        print(f"Indicators found:     {stats['indicators_found']}")
        print(f"Indicators migrated:  {stats['indicators_migrated']}")
        print(f"Indicators skipped:   {stats['indicators_skipped']}")
        print(f"Indicators failed:    {stats['indicators_failed']}")
        print(f"Total records:        {stats['total_records']}")
        print(f"Sessions processed:   {stats['sessions_processed']}")
        print(f"Errors:               {len(stats['errors'])}")

        if stats['errors']:
            print("\nErrors:")
            for error in stats['errors'][:10]:  # Show first 10 errors
                print(f"  - {error}")
            if len(stats['errors']) > 10:
                print(f"  ... and {len(stats['errors']) - 10} more errors")

        if args.dry_run:
            print("\n(DRY RUN - no data was actually migrated)")

        print("=" * 60)

        return 0 if stats['indicators_failed'] == 0 else 1

    except Exception as e:
        logger.error("migration.fatal_error", {"error": str(e)})
        print(f"\nFATAL ERROR: {str(e)}")
        return 1

    finally:
        await questdb_provider.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
