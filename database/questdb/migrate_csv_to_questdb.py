#!/usr/bin/env python3
"""
CSV to QuestDB Migration Script
================================

Migrates historical data collection sessions from CSV files to QuestDB.

Usage:
    python migrate_csv_to_questdb.py [--data-dir PATH] [--dry-run] [--session SESSION_ID]

Options:
    --data-dir PATH       Path to data directory (default: ./data)
    --dry-run             Show what would be migrated without actually migrating
    --session SESSION_ID  Migrate only specific session (default: all sessions)
    --batch-size SIZE     Batch size for DB writes (default: 1000)
    --skip-errors         Continue migration even if errors occur
    --verbose             Show detailed progress

Example:
    # Migrate all sessions
    python migrate_csv_to_questdb.py

    # Dry run to see what would be migrated
    python migrate_csv_to_questdb.py --dry-run

    # Migrate specific session
    python migrate_csv_to_questdb.py --session exec_20251027_123456

    # Migrate with custom data directory
    python migrate_csv_to_questdb.py --data-dir /path/to/data
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
from data.data_collection_persistence_service import DataCollectionPersistenceService
from core.logger import StructuredLogger, get_logger


class CSVMigrator:
    """Migrates CSV data to QuestDB"""

    def __init__(
        self,
        data_dir: Path,
        db_provider: QuestDBProvider,
        persistence_service: DataCollectionPersistenceService,
        logger: StructuredLogger,
        batch_size: int = 1000,
        skip_errors: bool = False
    ):
        self.data_dir = data_dir
        self.db_provider = db_provider
        self.persistence_service = persistence_service
        self.logger = logger
        self.batch_size = batch_size
        self.skip_errors = skip_errors

        # Migration statistics
        self.stats = {
            'sessions_found': 0,
            'sessions_migrated': 0,
            'sessions_skipped': 0,
            'sessions_failed': 0,
            'total_price_records': 0,
            'total_orderbook_records': 0,
            'errors': []
        }

    def find_sessions(self, session_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Find all data collection sessions in CSV format.

        Returns:
            List of session metadata dictionaries
        """
        sessions = []

        if not self.data_dir.exists():
            self.logger.warning("migration.data_dir_not_found", {
                "data_dir": str(self.data_dir)
            })
            return sessions

        # Scan for session directories
        for session_path in self.data_dir.glob("session_*"):
            if not session_path.is_dir():
                continue

            session_id = session_path.name.replace("session_", "")

            # Apply session filter if specified
            if session_filter and session_id != session_filter:
                continue

            # Find symbols in this session
            symbols = []
            for symbol_dir in session_path.iterdir():
                if symbol_dir.is_dir():
                    # Check if it has data files
                    prices_file = symbol_dir / "prices.csv"
                    orderbook_file = symbol_dir / "orderbook.csv"

                    if prices_file.exists() or orderbook_file.exists():
                        symbols.append(symbol_dir.name)

            if symbols:
                sessions.append({
                    'session_id': session_id,
                    'session_path': session_path,
                    'symbols': symbols,
                    'created_at': datetime.fromtimestamp(session_path.stat().st_mtime)
                })

        self.stats['sessions_found'] = len(sessions)
        return sorted(sessions, key=lambda x: x['created_at'])

    async def check_session_exists(self, session_id: str) -> bool:
        """Check if session already exists in QuestDB"""
        try:
            query = f"SELECT COUNT(*) as cnt FROM data_collection_sessions WHERE session_id = '{session_id}'"
            result = await self.db_provider.execute_query(query)
            return result[0]['cnt'] > 0 if result else False
        except Exception as e:
            self.logger.warning("migration.session_check_failed", {
                "session_id": session_id,
                "error": str(e)
            })
            return False

    def parse_prices_csv(self, csv_file: Path) -> List[Dict[str, Any]]:
        """Parse prices.csv file"""
        records = []

        try:
            with open(csv_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        records.append({
                            'timestamp': float(row['timestamp']),
                            'price': float(row['price']),
                            'volume': float(row['volume']),
                            'quote_volume': float(row.get('quote_volume', 0))
                        })
                    except (ValueError, KeyError) as e:
                        if not self.skip_errors:
                            raise
                        self.logger.warning("migration.price_record_parse_error", {
                            "file": str(csv_file),
                            "row": row,
                            "error": str(e)
                        })
        except Exception as e:
            self.logger.error("migration.price_file_parse_failed", {
                "file": str(csv_file),
                "error": str(e)
            })
            if not self.skip_errors:
                raise

        return records

    def parse_orderbook_csv(self, csv_file: Path) -> List[Dict[str, Any]]:
        """Parse orderbook.csv file"""
        records = []

        try:
            with open(csv_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        # Extract bids and asks (3 levels)
                        bids = []
                        asks = []

                        for i in range(1, 4):  # 3 levels
                            bid_price = float(row.get(f'bid_price_{i}', 0))
                            bid_qty = float(row.get(f'bid_qty_{i}', 0))
                            if bid_price > 0:
                                bids.append([bid_price, bid_qty])

                            ask_price = float(row.get(f'ask_price_{i}', 0))
                            ask_qty = float(row.get(f'ask_qty_{i}', 0))
                            if ask_price > 0:
                                asks.append([ask_price, ask_qty])

                        records.append({
                            'timestamp': float(row['timestamp']),
                            'bids': bids,
                            'asks': asks
                        })
                    except (ValueError, KeyError) as e:
                        if not self.skip_errors:
                            raise
                        self.logger.warning("migration.orderbook_record_parse_error", {
                            "file": str(csv_file),
                            "row": row,
                            "error": str(e)
                        })
        except Exception as e:
            self.logger.error("migration.orderbook_file_parse_failed", {
                "file": str(csv_file),
                "error": str(e)
            })
            if not self.skip_errors:
                raise

        return records

    async def migrate_session(self, session: Dict[str, Any]) -> bool:
        """
        Migrate single session from CSV to QuestDB.

        Returns:
            True if migration succeeded, False otherwise
        """
        session_id = session['session_id']
        session_path = session['session_path']
        symbols = session['symbols']

        try:
            self.logger.info("migration.session_started", {
                "session_id": session_id,
                "symbols": symbols
            })

            # Check if already migrated
            if await self.check_session_exists(session_id):
                self.logger.info("migration.session_already_exists", {
                    "session_id": session_id
                })
                self.stats['sessions_skipped'] += 1
                return True

            # Create session in QuestDB
            await self.persistence_service.create_session(
                session_id=session_id,
                symbols=symbols,
                data_types=['prices', 'orderbook'],
                exchange='mexc',  # Default, may need to be detected from data
                notes=f"Migrated from CSV on {datetime.now().isoformat()}"
            )

            # Migrate each symbol
            total_prices = 0
            total_orderbooks = 0

            for symbol in symbols:
                symbol_dir = session_path / symbol

                # Migrate prices
                prices_file = symbol_dir / "prices.csv"
                if prices_file.exists():
                    price_records = self.parse_prices_csv(prices_file)

                    if price_records:
                        # Write in batches
                        for i in range(0, len(price_records), self.batch_size):
                            batch = price_records[i:i + self.batch_size]
                            await self.persistence_service.persist_tick_prices(
                                session_id=session_id,
                                symbol=symbol,
                                price_data=batch
                            )

                        total_prices += len(price_records)
                        self.logger.info("migration.prices_migrated", {
                            "session_id": session_id,
                            "symbol": symbol,
                            "records": len(price_records)
                        })

                # Migrate orderbook
                orderbook_file = symbol_dir / "orderbook.csv"
                if orderbook_file.exists():
                    orderbook_records = self.parse_orderbook_csv(orderbook_file)

                    if orderbook_records:
                        # Write in batches
                        for i in range(0, len(orderbook_records), self.batch_size):
                            batch = orderbook_records[i:i + self.batch_size]
                            await self.persistence_service.persist_orderbook_snapshots(
                                session_id=session_id,
                                symbol=symbol,
                                orderbook_data=batch
                            )

                        total_orderbooks += len(orderbook_records)
                        self.logger.info("migration.orderbooks_migrated", {
                            "session_id": session_id,
                            "symbol": symbol,
                            "records": len(orderbook_records)
                        })

            # Update session with final counts
            await self.persistence_service.update_session_status(
                session_id=session_id,
                status='completed',
                records_collected=total_prices + total_orderbooks
            )

            self.stats['sessions_migrated'] += 1
            self.stats['total_price_records'] += total_prices
            self.stats['total_orderbook_records'] += total_orderbooks

            self.logger.info("migration.session_completed", {
                "session_id": session_id,
                "prices": total_prices,
                "orderbooks": total_orderbooks
            })

            return True

        except Exception as e:
            self.stats['sessions_failed'] += 1
            self.stats['errors'].append({
                'session_id': session_id,
                'error': str(e),
                'error_type': type(e).__name__
            })

            self.logger.error("migration.session_failed", {
                "session_id": session_id,
                "error": str(e),
                "error_type": type(e).__name__
            })

            if not self.skip_errors:
                raise

            return False

    async def migrate_all(self, session_filter: Optional[str] = None) -> Dict[str, Any]:
        """
        Migrate all sessions (or filtered session) from CSV to QuestDB.

        Returns:
            Migration statistics
        """
        sessions = self.find_sessions(session_filter)

        if not sessions:
            self.logger.warning("migration.no_sessions_found", {
                "data_dir": str(self.data_dir),
                "filter": session_filter
            })
            return self.stats

        self.logger.info("migration.started", {
            "sessions_found": len(sessions),
            "data_dir": str(self.data_dir)
        })

        for session in sessions:
            await self.migrate_session(session)

        self.logger.info("migration.completed", self.stats)
        return self.stats


async def main():
    """Main migration entry point"""
    parser = argparse.ArgumentParser(
        description="Migrate CSV data collection sessions to QuestDB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--data-dir',
        type=Path,
        default=Path('./data'),
        help='Path to data directory (default: ./data)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be migrated without actually migrating'
    )

    parser.add_argument(
        '--session',
        type=str,
        help='Migrate only specific session ID'
    )

    parser.add_argument(
        '--batch-size',
        type=int,
        default=1000,
        help='Batch size for DB writes (default: 1000)'
    )

    parser.add_argument(
        '--skip-errors',
        action='store_true',
        help='Continue migration even if errors occur'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show detailed progress'
    )

    args = parser.parse_args()

    # Setup logger
    # ✅ LOGGER FIX: Use get_logger() instead of direct StructuredLogger
    # Note: Log level controlled by config.json, not by --verbose flag
    logger = get_logger("migration")

    logger.info("migration.init", {
        "data_dir": str(args.data_dir),
        "dry_run": args.dry_run,
        "session_filter": args.session,
        "batch_size": args.batch_size,
        "skip_errors": args.skip_errors
    })

    # Create QuestDB provider
    db_provider = QuestDBProvider(
        ilp_host='127.0.0.1',
        ilp_port=9009,
        pg_host='127.0.0.1',
        pg_port=8812
    )

    # Initialize QuestDB connection
    try:
        await db_provider.initialize()
        logger.info("migration.db_connected")
    except Exception as e:
        logger.error("migration.db_connection_failed", {
            "error": str(e),
            "error_type": type(e).__name__
        })
        print(f"❌ Failed to connect to QuestDB: {str(e)}")
        print(f"   Ensure QuestDB is running at 127.0.0.1:9009 (ILP) and 127.0.0.1:8812 (PG)")
        return 1

    # Create persistence service
    persistence_service = DataCollectionPersistenceService(
        db_provider=db_provider,
        logger=logger
    )

    # Create migrator
    migrator = CSVMigrator(
        data_dir=args.data_dir,
        db_provider=db_provider,
        persistence_service=persistence_service,
        logger=logger,
        batch_size=args.batch_size,
        skip_errors=args.skip_errors
    )

    # Dry run - just list sessions
    if args.dry_run:
        sessions = migrator.find_sessions(args.session)

        print(f"\n📊 Dry Run: Found {len(sessions)} session(s) to migrate:\n")

        for session in sessions:
            print(f"  Session: {session['session_id']}")
            print(f"    Symbols: {', '.join(session['symbols'])}")
            print(f"    Created: {session['created_at'].strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"    Path: {session['session_path']}")
            print()

        print(f"Total sessions: {len(sessions)}")
        print(f"\n✅ Dry run completed. Run without --dry-run to migrate.\n")
        return 0

    # Run migration
    try:
        stats = await migrator.migrate_all(args.session)

        # Print summary
        print(f"\n" + "=" * 60)
        print(f"  CSV → QuestDB Migration Summary")
        print(f"=" * 60)
        print(f"  Sessions found:     {stats['sessions_found']}")
        print(f"  Sessions migrated:  {stats['sessions_migrated']}")
        print(f"  Sessions skipped:   {stats['sessions_skipped']}")
        print(f"  Sessions failed:    {stats['sessions_failed']}")
        print(f"  Price records:      {stats['total_price_records']:,}")
        print(f"  Orderbook records:  {stats['total_orderbook_records']:,}")
        print(f"=" * 60)

        if stats['errors']:
            print(f"\n⚠️  Errors occurred during migration:")
            for error in stats['errors']:
                print(f"  - {error['session_id']}: {error['error']}")

        if stats['sessions_failed'] > 0:
            print(f"\n❌ Migration completed with errors\n")
            return 1
        else:
            print(f"\n✅ Migration completed successfully\n")
            return 0

    except KeyboardInterrupt:
        logger.warning("migration.interrupted")
        print(f"\n⚠️  Migration interrupted by user\n")
        return 130

    except Exception as e:
        logger.error("migration.failed", {
            "error": str(e),
            "error_type": type(e).__name__
        })
        print(f"\n❌ Migration failed: {str(e)}\n")
        return 1

    finally:
        # Cleanup
        try:
            await db_provider.close()
        except:
            pass


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
