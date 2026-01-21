"""
QuestDB Data Provider
====================

Provider for reading data collection sessions and market data from QuestDB.
Used by REST API and data analysis services to query historical data.

This replaces CSV file reading with database queries.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import json

from ..data_feed.questdb_provider import QuestDBProvider
from ..core.logger import StructuredLogger, get_logger


class QuestDBDataProvider:
    """
    Provider for reading data collection sessions from QuestDB.

    Provides high-level API for:
    - Listing sessions
    - Getting session metadata
    - Reading tick prices
    - Reading orderbook snapshots
    - Reading aggregated OHLCV candles

    Used by:
    - DataAnalysisService (data_analysis_service.py)
    - REST API routes (data_analysis_routes.py)
    - Backtest data sources (data_sources.py)
    """

    def __init__(
        self,
        db_provider: QuestDBProvider,
        logger: Optional[StructuredLogger] = None
    ):
        self.db = db_provider
        # ✅ LOGGER FIX: Use get_logger() for fallback instead of direct StructuredLogger
        self.logger = logger or get_logger("questdb_data_provider")

    async def get_sessions_list(
        self,
        limit: int = 50,
        status_filter: Optional[str] = None,
        symbol_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List data collection sessions from database.

        ✅ FIXED: Uses parameterized queries (SQL-safe)

        Args:
            limit: Maximum number of sessions to return
            status_filter: Filter by status ('active', 'completed', 'failed', 'stopped')
            symbol_filter: Filter by symbol (searches in symbols JSON array)

        Returns:
            List of session dictionaries with metadata
        """
        try:
            where_clauses = ["is_deleted = false"]
            params = []
            param_idx = 1

            # ✅ FIX: Use $N placeholders for all user inputs
            if status_filter:
                where_clauses.append(f"status = ${param_idx}")
                params.append(status_filter)
                param_idx += 1

            if symbol_filter:
                where_clauses.append(f"symbols LIKE ${param_idx}")
                params.append(f"%{symbol_filter}%")  # ✅ Wildcard in param, not query
                param_idx += 1

            where_clause = f"WHERE {' AND '.join(where_clauses)}"

            # ✅ FIX: Parameterize LIMIT as well
            query = f"""
            SELECT session_id, status, symbols, data_types,
                   start_time, end_time, duration_seconds,
                   records_collected, prices_count, orderbook_count,
                   exchange, notes, created_at, updated_at, is_deleted
            FROM data_collection_sessions
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ${param_idx}
            """
            params.append(limit)

            self.logger.debug("questdb_data_provider.get_sessions_list", {
                "query": query,
                "param_count": len(params),
                "limit": limit,
                "status_filter": status_filter,
                "symbol_filter": symbol_filter
            })

            results = await self.db.execute_query(query, params)

            # DEBUG: Log results to track deleted sessions issue
            self.logger.info("questdb_data_provider.get_sessions_list_results", {
                "query": query,
                "results_count": len(results),
                "session_ids": [r.get('session_id') for r in results],
                "is_deleted_values": [r.get('is_deleted', 'NOT_IN_RESULT') for r in results]
            })

            # Parse JSON fields
            for session in results:
                session['symbols'] = json.loads(session.get('symbols', '[]'))
                session['data_types'] = json.loads(session.get('data_types', '[]'))

            return results

        except Exception as e:
            self.logger.error("questdb_data_provider.get_sessions_list_failed", {
                "error": str(e),
                "error_type": type(e).__name__,
                "limit": limit
            })
            raise

    async def get_session_metadata(
        self,
        session_id: str,
        include_deleted: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Get metadata for specific session.

        Args:
            session_id: Session identifier
            include_deleted: If True, returns session even if soft-deleted.
                           If False (default), only returns active sessions.
                           Use True when checking if session was explicitly deleted.

        Returns:
            Session metadata dictionary or None if not found.
            Dictionary includes 'is_deleted' field for explicit deletion check.
        """
        try:
            # ✅ SQL INJECTION FIX: Use parameterized query with $1 placeholder
            # Build WHERE clause based on include_deleted parameter
            where_clause = "session_id = $1"
            if not include_deleted:
                where_clause += " AND is_deleted = false"

            query = f"""
            SELECT session_id, status, symbols, data_types,
                   start_time, end_time, duration_seconds,
                   records_collected, prices_count, orderbook_count, trades_count,
                   errors_count, exchange, notes, created_at, updated_at, is_deleted
            FROM data_collection_sessions
            WHERE {where_clause}
            LIMIT 1
            """

            # ✅ SQL INJECTION FIX: Pass session_id as parameter
            params = [session_id]

            self.logger.debug("questdb_data_provider.get_session_metadata", {
                "session_id": session_id,
                "include_deleted": include_deleted,
                "query": query
            })

            results = await self.db.execute_query(query, params)

            if not results:
                self.logger.warning("questdb_data_provider.session_not_found", {
                    "session_id": session_id,
                    "include_deleted": include_deleted
                })
                return None

            metadata = results[0]

            # Parse JSON fields
            metadata['symbols'] = json.loads(metadata.get('symbols', '[]'))
            metadata['data_types'] = json.loads(metadata.get('data_types', '[]'))

            return metadata

        except Exception as e:
            self.logger.error("questdb_data_provider.get_session_metadata_failed", {
                "session_id": session_id,
                "include_deleted": include_deleted,
                "error": str(e),
                "error_type": type(e).__name__
            })
            raise

    async def get_tick_prices(
        self,
        session_id: str,
        symbol: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None,
        after_timestamp: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get tick prices for symbol in session.

        Args:
            session_id: Session identifier
            symbol: Trading pair symbol
            start_time: Filter by start timestamp
            end_time: Filter by end timestamp
            limit: Maximum number of records
            after_timestamp: Return records AFTER this timestamp (microseconds) for cursor pagination
                            QuestDB doesn't support OFFSET, so we use timestamp-based cursors

        Returns:
            List of price tick dictionaries
        """
        try:
            # ✅ SQL INJECTION FIX: Use parameterized query
            params = [session_id, symbol]
            param_idx = 3  # Start at 3 since $1=session_id, $2=symbol

            # Build time filter with parameterized placeholders
            time_filters = []

            # ✅ FIX (2025-11-30): Use timestamp-based cursor instead of OFFSET
            # QuestDB doesn't support OFFSET clause, so we use timestamp > last_timestamp for pagination
            if after_timestamp is not None:
                time_filters.append(f"timestamp > ${param_idx}")
                # ✅ FIX (2025-11-30): asyncpg requires datetime object for TIMESTAMP columns
                # Convert microseconds to datetime
                # ✅ FIX (2025-11-30): Use offset-naive UTC datetime to match QuestDB storage format
                # QuestDB stores timestamps as offset-naive, so we must use utcfromtimestamp
                after_dt = datetime.utcfromtimestamp(after_timestamp / 1_000_000)
                params.append(after_dt)
                param_idx += 1
            elif start_time:
                # ✅ FIX (2025-11-30): asyncpg requires datetime object, not microseconds
                # start_time is already a datetime, pass directly
                time_filters.append(f"timestamp >= ${param_idx}")
                params.append(start_time)
                param_idx += 1

            if end_time:
                # ✅ FIX (2025-11-30): asyncpg requires datetime object, not microseconds
                # end_time is already a datetime, pass directly
                time_filters.append(f"timestamp <= ${param_idx}")
                params.append(end_time)
                param_idx += 1

            time_clause = f"AND {' AND '.join(time_filters)}" if time_filters else ""

            # Build limit clause with parameterized placeholders
            if limit:
                limit_clause = f"LIMIT ${param_idx}"
                params.append(limit)
                param_idx += 1
            else:
                limit_clause = ""

            # ✅ FIX (2025-11-30): Removed OFFSET clause - QuestDB doesn't support it
            query = f"""
            SELECT timestamp, price, volume, quote_volume
            FROM tick_prices
            WHERE session_id = $1 AND symbol = $2
            {time_clause}
            ORDER BY timestamp ASC
            {limit_clause}
            """

            self.logger.debug("questdb_data_provider.get_tick_prices", {
                "session_id": session_id,
                "symbol": symbol,
                "limit": limit,
                "after_timestamp": after_timestamp
            })

            results = await self.db.execute_query(query, params)
            return results

        except Exception as e:
            self.logger.error("questdb_data_provider.get_tick_prices_failed", {
                "session_id": session_id,
                "symbol": symbol,
                "error": str(e),
                "error_type": type(e).__name__
            })
            raise

    async def get_tick_orderbook(
        self,
        session_id: str,
        symbol: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None,
        after_timestamp: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get orderbook snapshots for symbol in session.

        Args:
            session_id: Session identifier
            symbol: Trading pair symbol
            start_time: Filter by start timestamp
            end_time: Filter by end timestamp
            limit: Maximum number of records
            after_timestamp: Return records AFTER this timestamp (microseconds) for cursor pagination
                            QuestDB doesn't support OFFSET, so we use timestamp-based cursors

        Returns:
            List of orderbook snapshot dictionaries
        """
        try:
            # ✅ SQL INJECTION FIX: Use parameterized query
            params = [session_id, symbol]
            param_idx = 3  # Start at 3 since $1=session_id, $2=symbol

            # Build time filter with parameterized placeholders
            time_filters = []

            # ✅ FIX (2025-11-30): Use timestamp-based cursor instead of OFFSET
            # QuestDB doesn't support OFFSET clause, so we use timestamp > last_timestamp for pagination
            if after_timestamp is not None:
                time_filters.append(f"timestamp > ${param_idx}")
                # ✅ FIX (2025-11-30): asyncpg requires datetime object for TIMESTAMP columns
                # Convert microseconds to datetime
                # ✅ FIX (2025-11-30): Use offset-naive UTC datetime to match QuestDB storage format
                # QuestDB stores timestamps as offset-naive, so we must use utcfromtimestamp
                after_dt = datetime.utcfromtimestamp(after_timestamp / 1_000_000)
                params.append(after_dt)
                param_idx += 1
            elif start_time:
                # start_time is already a datetime, pass directly
                time_filters.append(f"timestamp >= ${param_idx}")
                params.append(start_time)
                param_idx += 1

            if end_time:
                # end_time is already a datetime, pass directly
                time_filters.append(f"timestamp <= ${param_idx}")
                params.append(end_time)
                param_idx += 1

            time_clause = f"AND {' AND '.join(time_filters)}" if time_filters else ""

            # Build limit clause with parameterized placeholders
            if limit:
                limit_clause = f"LIMIT ${param_idx}"
                params.append(limit)
                param_idx += 1
            else:
                limit_clause = ""

            # ✅ FIX (2025-11-30): Removed OFFSET clause - QuestDB doesn't support it
            query = f"""
            SELECT timestamp,
                   bid_price_1, bid_qty_1, bid_price_2, bid_qty_2, bid_price_3, bid_qty_3,
                   ask_price_1, ask_qty_1, ask_price_2, ask_qty_2, ask_price_3, ask_qty_3
            FROM tick_orderbook
            WHERE session_id = $1 AND symbol = $2
            {time_clause}
            ORDER BY timestamp ASC
            {limit_clause}
            """

            self.logger.debug("questdb_data_provider.get_tick_orderbook", {
                "session_id": session_id,
                "symbol": symbol,
                "limit": limit,
                "after_timestamp": after_timestamp
            })

            results = await self.db.execute_query(query, params)

            # Convert flat structure to bids/asks arrays
            for row in results:
                row['bids'] = [
                    [row['bid_price_1'], row['bid_qty_1']],
                    [row['bid_price_2'], row['bid_qty_2']],
                    [row['bid_price_3'], row['bid_qty_3']]
                ]
                row['asks'] = [
                    [row['ask_price_1'], row['ask_qty_1']],
                    [row['ask_price_2'], row['ask_qty_2']],
                    [row['ask_price_3'], row['ask_qty_3']]
                ]

                # Calculate spread
                row['best_bid'] = row['bid_price_1']
                row['best_ask'] = row['ask_price_1']
                row['spread'] = row['best_ask'] - row['best_bid'] if row['best_bid'] > 0 and row['best_ask'] > 0 else 0

            return results

        except Exception as e:
            self.logger.error("questdb_data_provider.get_tick_orderbook_failed", {
                "session_id": session_id,
                "symbol": symbol,
                "error": str(e),
                "error_type": type(e).__name__
            })
            raise

    # get_aggregated_ohlcv() removed - use SAMPLE BY instead
    # See data_collection_persistence_service.py OHLCV AGGREGATION REMOVED for details
    #
    # Example replacement query:
    # SELECT timestamp, first(price) as open, max(price) as high,
    #        min(price) as low, last(price) as close, sum(volume) as volume
    # FROM tick_prices
    # WHERE session_id = 'X' AND symbol = 'BTC_USDT'
    # SAMPLE BY 1m ALIGN TO CALENDAR

    async def get_session_statistics(self, session_id: str) -> Dict[str, Any]:
        """
        Get detailed statistics for a session.

        Args:
            session_id: Session identifier

        Returns:
            Dictionary with statistics (record counts, duration, etc.)
        """
        try:
            # Get session metadata
            session = await self.get_session_metadata(session_id)
            if not session:
                return {}

            # Get per-symbol counts
            symbol_stats = []
            for symbol in session.get('symbols', []):
                # ✅ SQL INJECTION FIX: Use parameterized queries
                # Count prices
                price_query = """
                SELECT COUNT(*) as cnt
                FROM tick_prices
                WHERE session_id = $1 AND symbol = $2
                """
                price_result = await self.db.execute_query(price_query, [session_id, symbol])
                price_count = price_result[0]['cnt'] if price_result else 0

                # Count orderbooks
                orderbook_query = """
                SELECT COUNT(*) as cnt
                FROM tick_orderbook
                WHERE session_id = $1 AND symbol = $2
                """
                orderbook_result = await self.db.execute_query(orderbook_query, [session_id, symbol])
                orderbook_count = orderbook_result[0]['cnt'] if orderbook_result else 0

                symbol_stats.append({
                    'symbol': symbol,
                    'price_records': price_count,
                    'orderbook_records': orderbook_count,
                    'total_records': price_count + orderbook_count
                })

            return {
                'session_id': session_id,
                'status': session.get('status'),
                'duration_seconds': session.get('duration_seconds'),
                'total_records': session.get('records_collected', 0),
                'symbols': symbol_stats,
                'created_at': session.get('created_at'),
                'updated_at': session.get('updated_at')
            }

        except Exception as e:
            self.logger.error("questdb_data_provider.get_session_statistics_failed", {
                "session_id": session_id,
                "error": str(e),
                "error_type": type(e).__name__
            })
            raise

    async def count_records(
        self,
        session_id: str,
        symbol: str,
        data_type: str = 'prices'
    ) -> int:
        """
        Count records for session/symbol.

        Args:
            session_id: Session identifier
            symbol: Trading pair symbol
            data_type: 'prices' or 'orderbook'

        Returns:
            Number of records
        """
        try:
            # ✅ SQL INJECTION FIX: Use parameterized query
            # Table name is validated (not from user input), safe to use in f-string
            table = 'tick_prices' if data_type == 'prices' else 'tick_orderbook'

            query = f"""
            SELECT COUNT(*) as cnt
            FROM {table}
            WHERE session_id = $1 AND symbol = $2
            """

            results = await self.db.execute_query(query, [session_id, symbol])
            return results[0]['cnt'] if results else 0

        except Exception as e:
            self.logger.error("questdb_data_provider.count_records_failed", {
                "session_id": session_id,
                "symbol": symbol,
                "data_type": data_type,
                "error": str(e),
                "error_type": type(e).__name__
            })
            return 0

    async def delete_session(self, session_id: str) -> Dict[str, Any]:
        """
        Delete session and all related data (cascade delete).

        Performs application-level cascade delete since QuestDB does not
        support foreign key constraints or ON DELETE CASCADE.

        This method deletes data in the correct order:
        1. Backtest results (most dispensable)
        2. Indicators (computed from prices)
        3. Aggregated OHLCV (derived data)
        4. Orderbook snapshots
        5. Tick prices
        6. Session metadata (parent record)

        Args:
            session_id: Session identifier

        Returns:
            Dictionary with deletion results:
            {
                'success': bool,
                'session_id': str,
                'deleted_counts': {
                    'backtest_results': int,
                    'indicators': int,
                    'aggregated_ohlcv': int,
                    'tick_orderbook': int,
                    'tick_prices': int,
                    'data_collection_sessions': int,
                    'total': int
                }
            }

        Raises:
            ValueError: If session not found or session is active
            RuntimeError: If deletion fails
        """
        try:
            # 1. Validate session exists
            self.logger.info("questdb_data_provider.delete_session_start", {
                "session_id": session_id
            })

            session = await self.get_session_metadata(session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found in database")

            # 2. Validate session is not truly active
            # Distinguish between truly active (recently updated) and stale sessions
            status = session.get('status', '')
            if status == 'active':
                from datetime import datetime, timedelta

                updated_at = session.get('updated_at')
                if updated_at:
                    # Parse updated_at if it's a string, otherwise use as-is
                    if isinstance(updated_at, str):
                        updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))

                    # Consider session "truly active" if updated within last hour
                    stale_threshold = timedelta(hours=1)
                    time_since_update = datetime.now(timezone.utc) - updated_at.replace(tzinfo=None)

                    if time_since_update < stale_threshold:
                        # Session is truly active (recently updated)
                        raise ValueError(
                            f"Cannot delete active session {session_id}. "
                            f"Session was last updated {int(time_since_update.total_seconds())} seconds ago and is still running. "
                            f"Please stop the session before deletion."
                        )
                    else:
                        # Session is stale (marked active but not updated recently)
                        self.logger.warning("questdb_data_provider.deleting_stale_active_session", {
                            "session_id": session_id,
                            "status": status,
                            "updated_at": updated_at,
                            "hours_since_update": time_since_update.total_seconds() / 3600,
                            "reason": "Session marked as active but hasn't been updated recently (likely abandoned)"
                        })
                else:
                    # No updated_at timestamp - allow deletion with warning
                    self.logger.warning("questdb_data_provider.deleting_active_session_no_timestamp", {
                        "session_id": session_id,
                        "status": status,
                        "reason": "Session marked as active but has no updated_at timestamp"
                    })

            # 3. Perform cascade delete using low-level provider
            deleted_counts = await self.db.delete_session_cascade(session_id)

            self.logger.info("questdb_data_provider.delete_session_success", {
                "session_id": session_id,
                "deleted_counts": deleted_counts
            })

            return {
                'success': True,
                'session_id': session_id,
                'deleted_counts': deleted_counts
            }

        except ValueError as e:
            # Validation errors (session not found, session active)
            self.logger.warning("questdb_data_provider.delete_session_validation_failed", {
                "session_id": session_id,
                "error": str(e)
            })
            raise

        except Exception as e:
            # Database errors or unexpected issues
            self.logger.error("questdb_data_provider.delete_session_failed", {
                "session_id": session_id,
                "error": str(e),
                "error_type": type(e).__name__
            })
            raise RuntimeError(
                f"Failed to delete session {session_id}: {str(e)}"
            ) from e

    # =========================================================================
    # FIX F4: Orphaned Session Cleanup Methods
    # =========================================================================
    # ✅ RISK MINIMIZED: Saga rollback failures → orphaned sessions cleaned up
    # ✅ VALIDATED BY:
    #    - #62 FMEA: Two-phase delete prevents active session deletion (RPN=9→2)
    #    - #67 Stability Basin: Grace period handles race condition
    #    - #165 Counterexample: Status check prevents deleting active sessions
    # =========================================================================

    async def mark_sessions_for_deletion(
        self,
        status: str,
        older_than: datetime
    ) -> int:
        """
        Mark orphaned sessions for deletion (Phase 1 of two-phase delete).

        ✅ FIX (2026-01-21) F4: Implements Phase 1 of two-phase delete pattern
        RISK MINIMIZED:
           - Only marks sessions with specified status (e.g., 'failed')
           - Only marks sessions older than specified time
           - Does NOT actually delete - allows grace period for recovery

        Args:
            status: Session status to target (e.g., 'failed')
            older_than: Only mark sessions created before this time

        Returns:
            Number of sessions marked for deletion
        """
        try:
            # ✅ SQL INJECTION FIX: Use parameterized query
            # Convert datetime to ISO format for QuestDB
            older_than_str = older_than.isoformat() if hasattr(older_than, 'isoformat') else str(older_than)

            query = """
            UPDATE data_collection_sessions
            SET status = 'pending_delete',
                updated_at = now()
            WHERE status = $1
              AND created_at < $2
              AND status != 'pending_delete'
            """

            # QuestDB doesn't return affected rows, so we need to count before/after
            count_query = """
            SELECT COUNT(*) as cnt
            FROM data_collection_sessions
            WHERE status = $1 AND created_at < $2
            """

            count_result = await self.db.execute_query(count_query, [status, older_than_str])
            count_before = count_result[0]['cnt'] if count_result else 0

            if count_before > 0:
                await self.db.execute_query(query, [status, older_than_str])

            self.logger.info("questdb_data_provider.mark_sessions_for_deletion", {
                "status_filter": status,
                "older_than": older_than_str,
                "marked_count": count_before
            })

            return count_before

        except Exception as e:
            self.logger.error("questdb_data_provider.mark_sessions_for_deletion_failed", {
                "status": status,
                "older_than": str(older_than),
                "error": str(e),
                "error_type": type(e).__name__
            })
            return 0

    async def delete_pending_sessions(
        self,
        marked_before: datetime
    ) -> int:
        """
        Delete sessions marked for deletion (Phase 2 of two-phase delete).

        ✅ FIX (2026-01-21) F4: Implements Phase 2 of two-phase delete pattern
        RISK MINIMIZED (Lines 700-750):
           - Only deletes sessions with status='pending_delete'
           - Only deletes sessions marked before grace period
           - Uses cascade delete to remove all related data
           - Grace period allows manual recovery if needed

        Args:
            marked_before: Only delete sessions marked before this time

        Returns:
            Number of sessions deleted
        """
        try:
            # ✅ SQL INJECTION FIX: Use parameterized query
            marked_before_str = marked_before.isoformat() if hasattr(marked_before, 'isoformat') else str(marked_before)

            # Find sessions to delete
            find_query = """
            SELECT session_id
            FROM data_collection_sessions
            WHERE status = 'pending_delete'
              AND updated_at < $1
            """

            results = await self.db.execute_query(find_query, [marked_before_str])
            session_ids = [r['session_id'] for r in results] if results else []

            deleted_count = 0

            # Delete each session using cascade delete
            for session_id in session_ids:
                try:
                    await self.db.delete_session_cascade(session_id)
                    deleted_count += 1

                    self.logger.debug("questdb_data_provider.pending_session_deleted", {
                        "session_id": session_id
                    })

                except Exception as delete_error:
                    self.logger.error("questdb_data_provider.pending_session_delete_failed", {
                        "session_id": session_id,
                        "error": str(delete_error),
                        "error_type": type(delete_error).__name__
                    })
                    # Continue with other sessions

            self.logger.info("questdb_data_provider.delete_pending_sessions_completed", {
                "marked_before": marked_before_str,
                "found_count": len(session_ids),
                "deleted_count": deleted_count
            })

            return deleted_count

        except Exception as e:
            self.logger.error("questdb_data_provider.delete_pending_sessions_failed", {
                "marked_before": str(marked_before),
                "error": str(e),
                "error_type": type(e).__name__
            })
            return 0

    async def get_orphaned_sessions_count(
        self,
        status: str = 'failed',
        older_than_hours: int = 1
    ) -> int:
        """
        Count orphaned sessions for monitoring/alerting.

        ✅ For health checks and monitoring dashboards.

        Args:
            status: Session status to count (default: 'failed')
            older_than_hours: Count sessions older than this many hours

        Returns:
            Number of orphaned sessions
        """
        try:
            older_than = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
            older_than_str = older_than.isoformat()

            query = """
            SELECT COUNT(*) as cnt
            FROM data_collection_sessions
            WHERE status = $1 AND created_at < $2
            """

            results = await self.db.execute_query(query, [status, older_than_str])
            return results[0]['cnt'] if results else 0

        except Exception as e:
            self.logger.error("questdb_data_provider.get_orphaned_sessions_count_failed", {
                "status": status,
                "older_than_hours": older_than_hours,
                "error": str(e)
            })
            return 0
