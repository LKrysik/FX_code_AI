"""
QuestDB Data Provider
====================

Provider for reading data collection sessions and market data from QuestDB.
Used by REST API and data analysis services to query historical data.

This replaces CSV file reading with database queries.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
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
            # Build WHERE clause based on include_deleted parameter
            where_clause = f"session_id = '{session_id}'"
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

            self.logger.debug("questdb_data_provider.get_session_metadata", {
                "session_id": session_id,
                "include_deleted": include_deleted,
                "query": query
            })

            results = await self.db.execute_query(query)

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
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get tick prices for symbol in session.

        Args:
            session_id: Session identifier
            symbol: Trading pair symbol
            start_time: Filter by start timestamp
            end_time: Filter by end timestamp
            limit: Maximum number of records
            offset: Skip first N records (for pagination)

        Returns:
            List of price tick dictionaries
        """
        try:
            # Build time filter
            time_filters = []
            if start_time:
                # Convert to epoch microseconds (QuestDB timestamp format)
                start_us = int(start_time.timestamp() * 1_000_000)
                time_filters.append(f"timestamp >= {start_us}")

            if end_time:
                end_us = int(end_time.timestamp() * 1_000_000)
                time_filters.append(f"timestamp <= {end_us}")

            time_clause = f"AND {' AND '.join(time_filters)}" if time_filters else ""
            limit_clause = f"LIMIT {limit}" if limit else ""
            offset_clause = f"OFFSET {offset}" if offset > 0 else ""

            query = f"""
            SELECT timestamp, price, volume, quote_volume
            FROM tick_prices
            WHERE session_id = '{session_id}' AND symbol = '{symbol}'
            {time_clause}
            ORDER BY timestamp ASC
            {limit_clause}
            {offset_clause}
            """

            self.logger.debug("questdb_data_provider.get_tick_prices", {
                "session_id": session_id,
                "symbol": symbol,
                "limit": limit,
                "offset": offset
            })

            results = await self.db.execute_query(query)
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
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get orderbook snapshots for symbol in session.

        Args:
            session_id: Session identifier
            symbol: Trading pair symbol
            start_time: Filter by start timestamp
            end_time: Filter by end timestamp
            limit: Maximum number of records
            offset: Skip first N records (for pagination)

        Returns:
            List of orderbook snapshot dictionaries
        """
        try:
            # Build time filter
            time_filters = []
            if start_time:
                start_us = int(start_time.timestamp() * 1_000_000)
                time_filters.append(f"timestamp >= {start_us}")

            if end_time:
                end_us = int(end_time.timestamp() * 1_000_000)
                time_filters.append(f"timestamp <= {end_us}")

            time_clause = f"AND {' AND '.join(time_filters)}" if time_filters else ""
            limit_clause = f"LIMIT {limit}" if limit else ""
            offset_clause = f"OFFSET {offset}" if offset > 0 else ""

            query = f"""
            SELECT timestamp,
                   bid_price_1, bid_qty_1, bid_price_2, bid_qty_2, bid_price_3, bid_qty_3,
                   ask_price_1, ask_qty_1, ask_price_2, ask_qty_2, ask_price_3, ask_qty_3
            FROM tick_orderbook
            WHERE session_id = '{session_id}' AND symbol = '{symbol}'
            {time_clause}
            ORDER BY timestamp ASC
            {limit_clause}
            {offset_clause}
            """

            self.logger.debug("questdb_data_provider.get_tick_orderbook", {
                "session_id": session_id,
                "symbol": symbol,
                "limit": limit,
                "offset": offset
            })

            results = await self.db.execute_query(query)

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
                # Count prices
                price_query = f"""
                SELECT COUNT(*) as cnt
                FROM tick_prices
                WHERE session_id = '{session_id}' AND symbol = '{symbol}'
                """
                price_result = await self.db.execute_query(price_query)
                price_count = price_result[0]['cnt'] if price_result else 0

                # Count orderbooks
                orderbook_query = f"""
                SELECT COUNT(*) as cnt
                FROM tick_orderbook
                WHERE session_id = '{session_id}' AND symbol = '{symbol}'
                """
                orderbook_result = await self.db.execute_query(orderbook_query)
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
            table = 'tick_prices' if data_type == 'prices' else 'tick_orderbook'

            query = f"""
            SELECT COUNT(*) as cnt
            FROM {table}
            WHERE session_id = '{session_id}' AND symbol = '{symbol}'
            """

            results = await self.db.execute_query(query)
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
                    time_since_update = datetime.utcnow() - updated_at.replace(tzinfo=None)

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
