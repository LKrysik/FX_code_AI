"""
Data Collection Persistence Service
====================================
Handles persisting data collection sessions and data to QuestDB.

Replaces file-based CSV storage with database-backed storage for:
- Session metadata tracking
- Tick price data (high-frequency)
- Order book snapshots (3-level)
- Pre-aggregated OHLCV candles

This service integrates with the existing data collection system in
execution_controller.py, providing a database-backed alternative to CSV files.
"""

import asyncio
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from ..core.logger import StructuredLogger, get_logger
from ..data_feed.questdb_provider import QuestDBProvider


class DataCollectionPersistenceService:
    """
    Service for persisting data collection sessions and data to QuestDB.

    Responsibilities:
    - Create and update session metadata
    - Persist tick price data
    - Persist orderbook snapshots
    - Aggregate OHLCV candles
    - Provide session lifecycle management
    """

    def __init__(
        self,
        db_provider: Optional[QuestDBProvider] = None,
        logger: Optional[StructuredLogger] = None
    ):
        """
        Initialize persistence service.

        Args:
            db_provider: QuestDB provider instance (creates default if None)
            logger: Structured logger instance
        """
        self.db_provider = db_provider or QuestDBProvider()
        self.logger = logger or get_logger(__name__)

        # In-memory cache for session state
        self._active_sessions: Dict[str, Dict[str, Any]] = {}

        # OHLCV aggregation state
        self._ohlcv_aggregators: Dict[str, 'OHLCVAggregator'] = {}  # session_id -> aggregator

    async def create_session(
        self,
        session_id: str,
        symbols: List[str],
        data_types: List[str],
        exchange: str = "mexc",
        notes: str = ""
    ) -> Dict[str, Any]:
        """
        Create a new data collection session.

        Args:
            session_id: Unique session identifier
            symbols: List of trading symbols
            data_types: List of data types to collect ('prices', 'orderbook', 'trades')
            exchange: Source exchange
            notes: Optional user notes

        Returns:
            Session metadata dictionary
        """
        try:
            now = datetime.utcnow()

            session_metadata = {
                'session_id': session_id,
                'status': 'active',
                'symbols': symbols,
                'data_types': data_types,
                'exchange': exchange,
                'notes': notes,
                'start_time': now,
                'end_time': None,
                'duration_seconds': 0,
                'records_collected': 0,
                'prices_count': 0,
                'orderbook_count': 0,
                'trades_count': 0,
                'errors_count': 0,
                'created_at': now,
                'updated_at': now
            }

            # Store in cache
            self._active_sessions[session_id] = session_metadata

            # Insert into database
            await self._insert_session_metadata(session_metadata)

            # Initialize OHLCV aggregator for this session
            self._ohlcv_aggregators[session_id] = OHLCVAggregator(
                session_id=session_id,
                db_provider=self.db_provider,
                logger=self.logger
            )

            self.logger.info("data_collection.session_created", {
                'session_id': session_id,
                'symbols': symbols,
                'data_types': data_types
            })

            return session_metadata

        except Exception as e:
            self.logger.error("data_collection.session_creation_failed", {
                'session_id': session_id,
                'error': str(e)
            })
            raise

    async def update_session_status(
        self,
        session_id: str,
        status: str,
        records_collected: Optional[int] = None,
        errors_count: Optional[int] = None
    ) -> None:
        """
        Update session status and metrics.

        Args:
            session_id: Session identifier
            status: New status ('active', 'completed', 'failed', 'stopped')
            records_collected: Total records collected (optional)
            errors_count: Number of errors (optional)
        """
        try:
            # Update cache
            if session_id in self._active_sessions:
                session = self._active_sessions[session_id]
                session['status'] = status
                session['updated_at'] = datetime.utcnow()

                if records_collected is not None:
                    session['records_collected'] = records_collected

                if errors_count is not None:
                    session['errors_count'] = errors_count

                # Calculate duration if completing
                if status in ('completed', 'failed', 'stopped'):
                    session['end_time'] = datetime.utcnow()
                    duration = (session['end_time'] - session['start_time']).total_seconds()
                    session['duration_seconds'] = int(duration)

                # Update database
                await self._update_session_metadata(session)

                # Cleanup aggregator if session ended
                if status in ('completed', 'failed', 'stopped'):
                    if session_id in self._ohlcv_aggregators:
                        await self._ohlcv_aggregators[session_id].flush()
                        del self._ohlcv_aggregators[session_id]

                    # Remove from active sessions
                    del self._active_sessions[session_id]

            self.logger.info("data_collection.session_updated", {
                'session_id': session_id,
                'status': status
            })

        except Exception as e:
            self.logger.error("data_collection.session_update_failed", {
                'session_id': session_id,
                'error': str(e)
            })
            raise

    async def persist_tick_prices(
        self,
        session_id: str,
        symbol: str,
        price_data: List[Dict[str, Any]]
    ) -> int:
        """
        Persist tick price data to database.

        Args:
            session_id: Session identifier
            symbol: Trading symbol
            price_data: List of price ticks with keys: timestamp, price, volume, quote_volume

        Returns:
            Number of records inserted
        """
        try:
            if not price_data:
                return 0

            # Prepare batch for insertion
            batch = []
            for tick in price_data:
                batch.append({
                    'session_id': session_id,
                    'symbol': symbol,
                    'timestamp': tick['timestamp'],
                    'price': tick['price'],
                    'volume': tick['volume'],
                    'quote_volume': tick.get('quote_volume', tick['price'] * tick['volume'])
                })

            # Insert via InfluxDB line protocol (ultra-fast)
            count = await self.db_provider.insert_tick_prices_batch(batch)

            # Update session metrics
            if session_id in self._active_sessions:
                self._active_sessions[session_id]['prices_count'] += count
                self._active_sessions[session_id]['records_collected'] += count

            # Feed data to OHLCV aggregator
            if session_id in self._ohlcv_aggregators:
                await self._ohlcv_aggregators[session_id].add_ticks(symbol, price_data)

            self.logger.debug("data_collection.ticks_persisted", {
                'session_id': session_id,
                'symbol': symbol,
                'count': count
            })

            return count

        except Exception as e:
            self.logger.error("data_collection.tick_persistence_failed", {
                'session_id': session_id,
                'symbol': symbol,
                'error': str(e)
            })
            raise

    async def persist_orderbook_snapshots(
        self,
        session_id: str,
        symbol: str,
        orderbook_data: List[Dict[str, Any]]
    ) -> int:
        """
        Persist orderbook snapshots to database.

        Args:
            session_id: Session identifier
            symbol: Trading symbol
            orderbook_data: List of orderbook snapshots with keys: timestamp, bids, asks

        Returns:
            Number of records inserted
        """
        try:
            if not orderbook_data:
                return 0

            # Prepare batch for insertion
            batch = []
            for snapshot in orderbook_data:
                timestamp = snapshot['timestamp']
                bids = snapshot.get('bids', [])
                asks = snapshot.get('asks', [])

                # Extract top 3 levels (bids and asks are [[price, qty], ...])
                record = {
                    'session_id': session_id,
                    'symbol': symbol,
                    'timestamp': timestamp,
                }

                # Add bid levels (top 3)
                for i in range(3):
                    if i < len(bids):
                        record[f'bid_price_{i+1}'] = float(bids[i][0])
                        record[f'bid_qty_{i+1}'] = float(bids[i][1])
                    else:
                        record[f'bid_price_{i+1}'] = 0.0
                        record[f'bid_qty_{i+1}'] = 0.0

                # Add ask levels (top 3)
                for i in range(3):
                    if i < len(asks):
                        record[f'ask_price_{i+1}'] = float(asks[i][0])
                        record[f'ask_qty_{i+1}'] = float(asks[i][1])
                    else:
                        record[f'ask_price_{i+1}'] = 0.0
                        record[f'ask_qty_{i+1}'] = 0.0

                batch.append(record)

            # Insert via InfluxDB line protocol
            count = await self.db_provider.insert_orderbook_snapshots_batch(batch)

            # Update session metrics
            if session_id in self._active_sessions:
                self._active_sessions[session_id]['orderbook_count'] += count
                self._active_sessions[session_id]['records_collected'] += count

            self.logger.debug("data_collection.orderbook_persisted", {
                'session_id': session_id,
                'symbol': symbol,
                'count': count
            })

            return count

        except Exception as e:
            self.logger.error("data_collection.orderbook_persistence_failed", {
                'session_id': session_id,
                'symbol': symbol,
                'error': str(e)
            })
            raise

    async def get_session_metadata(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session metadata.

        Args:
            session_id: Session identifier

        Returns:
            Session metadata dictionary or None if not found
        """
        # Check cache first
        if session_id in self._active_sessions:
            return self._active_sessions[session_id].copy()

        # Query database
        try:
            query = f"""
            SELECT * FROM data_collection_sessions
            WHERE session_id = '{session_id}'
            LIMIT 1
            """

            results = await self.db_provider.execute_query(query)
            if results:
                return results[0]

            return None

        except Exception as e:
            self.logger.error("data_collection.get_session_failed", {
                'session_id': session_id,
                'error': str(e)
            })
            return None

    async def _insert_session_metadata(self, session: Dict[str, Any]) -> None:
        """
        Insert session metadata into database using parameterized query.

        CRITICAL FIX: Explicitly sets is_deleted = false to prevent NULL values.
        Without explicit value, QuestDB may not apply DEFAULT, causing sessions
        to be filtered out by 'WHERE is_deleted = false' queries.
        """
        import json

        # Parameterized query prevents SQL injection
        query = """
        INSERT INTO data_collection_sessions (
            session_id, status, symbols, data_types, collection_interval_ms,
            start_time, end_time, duration_seconds,
            records_collected, prices_count, orderbook_count, trades_count, errors_count,
            exchange, notes, created_at, updated_at, is_deleted
        ) VALUES (
            $1, $2, $3, $4, $5,
            cast($6 as timestamp), NULL, 0,
            0, 0, 0, 0, 0,
            $7, $8, cast($9 as timestamp), cast($10 as timestamp), $11
        )
        """

        # Convert datetime to microseconds (LONG) for QuestDB
        start_time_us = int(session['start_time'].timestamp() * 1_000_000)
        created_at_us = int(session['created_at'].timestamp() * 1_000_000)
        updated_at_us = int(session['updated_at'].timestamp() * 1_000_000)

        params = [
            session['session_id'],
            session['status'],
            json.dumps(session['symbols']),
            json.dumps(session['data_types']),
            1000,  # collection_interval_ms
            start_time_us,
            session.get('exchange', 'mexc'),
            session.get('notes', ''),
            created_at_us,
            updated_at_us,
            False  # is_deleted - explicit false to ensure proper filtering
        ]

        await self.db_provider.execute_query(query, params)

    async def _update_session_metadata(self, session: Dict[str, Any]) -> None:
        """Update session metadata in database using parameterized query."""

        # Parameterized query prevents SQL injection
        query = """
        UPDATE data_collection_sessions SET
            status = $1,
            end_time = cast($2 as timestamp),
            duration_seconds = $3,
            records_collected = $4,
            prices_count = $5,
            orderbook_count = $6,
            trades_count = $7,
            errors_count = $8,
            updated_at = cast($9 as timestamp)
        WHERE session_id = $10
        """

        # Convert datetime to microseconds (LONG) for QuestDB, handle NULL for end_time
        end_time_us = None
        if session.get('end_time'):
            end_time_us = int(session['end_time'].timestamp() * 1_000_000)

        updated_at_us = int(session['updated_at'].timestamp() * 1_000_000)

        params = [
            session['status'],
            end_time_us,
            session['duration_seconds'],
            session['records_collected'],
            session.get('prices_count', 0),
            session.get('orderbook_count', 0),
            session.get('trades_count', 0),
            session.get('errors_count', 0),
            updated_at_us,
            session['session_id']
        ]

        await self.db_provider.execute_query(query, params)


class OHLCVAggregator:
    """
    Aggregates tick data into OHLCV candles.

    Runs continuously during data collection, pre-aggregating candles
    for common timeframes (1m, 5m, 15m, 1h) to enable fast backtest queries.
    """

    def __init__(
        self,
        session_id: str,
        db_provider: QuestDBProvider,
        logger: StructuredLogger,
        intervals: List[str] = None
    ):
        """
        Initialize OHLCV aggregator.

        Args:
            session_id: Session identifier
            db_provider: QuestDB provider
            logger: Logger instance
            intervals: List of timeframes to aggregate ('1m', '5m', '15m', '1h', '4h', '1d')
        """
        self.session_id = session_id
        self.db_provider = db_provider
        self.logger = logger
        self.intervals = intervals or ['1m', '5m', '15m', '1h']

        # Current candle state per symbol and interval
        self._current_candles: Dict[str, Dict[str, Dict[str, Any]]] = {}  # symbol -> interval -> candle

        # Buffer for batch inserts
        self._candle_buffer: List[Dict[str, Any]] = []
        self._buffer_size = 100

    async def add_ticks(self, symbol: str, ticks: List[Dict[str, Any]]) -> None:
        """
        Add ticks and update OHLCV candles.

        Args:
            symbol: Trading symbol
            ticks: List of tick data
        """
        if symbol not in self._current_candles:
            self._current_candles[symbol] = {}

        for tick in ticks:
            timestamp = float(tick['timestamp'])
            price = float(tick['price'])
            volume = float(tick['volume'])
            quote_volume = float(tick.get('quote_volume', price * volume))

            # Update candles for each interval
            for interval in self.intervals:
                candle_start = self._get_candle_start(timestamp, interval)
                interval_key = f"{symbol}_{interval}"

                if interval not in self._current_candles[symbol]:
                    # New candle
                    self._current_candles[symbol][interval] = {
                        'session_id': self.session_id,
                        'symbol': symbol,
                        'interval': interval,
                        'timestamp': candle_start,
                        'open': price,
                        'high': price,
                        'low': price,
                        'close': price,
                        'volume': volume,
                        'quote_volume': quote_volume,
                        'trades_count': 1,
                        'is_closed': False
                    }
                else:
                    candle = self._current_candles[symbol][interval]

                    # Check if we need to close current candle and start new one
                    if candle_start > candle['timestamp']:
                        # Close and persist current candle
                        candle['is_closed'] = True
                        self._candle_buffer.append(candle)

                        # Start new candle
                        self._current_candles[symbol][interval] = {
                            'session_id': self.session_id,
                            'symbol': symbol,
                            'interval': interval,
                            'timestamp': candle_start,
                            'open': price,
                            'high': price,
                            'low': price,
                            'close': price,
                            'volume': volume,
                            'quote_volume': quote_volume,
                            'trades_count': 1,
                            'is_closed': False
                        }
                    else:
                        # Update existing candle
                        candle['high'] = max(candle['high'], price)
                        candle['low'] = min(candle['low'], price)
                        candle['close'] = price
                        candle['volume'] += volume
                        candle['quote_volume'] += quote_volume
                        candle['trades_count'] += 1

        # Flush buffer if full
        if len(self._candle_buffer) >= self._buffer_size:
            await self.flush()

    async def flush(self) -> None:
        """Flush pending candles to database."""
        if not self._candle_buffer:
            return

        try:
            await self.db_provider.insert_ohlcv_candles_batch(self._candle_buffer)
            self.logger.debug("ohlcv_aggregation.candles_flushed", {
                'session_id': self.session_id,
                'count': len(self._candle_buffer)
            })
            self._candle_buffer.clear()

        except Exception as e:
            self.logger.error("ohlcv_aggregation.flush_failed", {
                'session_id': self.session_id,
                'error': str(e)
            })

    def _get_candle_start(self, timestamp: float, interval: str) -> float:
        """Calculate candle start timestamp for given interval."""
        # Parse interval (e.g., '1m' -> 60 seconds)
        unit = interval[-1]
        value = int(interval[:-1])

        seconds_per_unit = {
            's': 1,
            'm': 60,
            'h': 3600,
            'd': 86400
        }

        interval_seconds = value * seconds_per_unit.get(unit, 60)

        # Round down to interval start
        return (int(timestamp) // interval_seconds) * interval_seconds
