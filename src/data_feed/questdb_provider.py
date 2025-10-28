#!/usr/bin/env python3
"""
QuestDB Data Provider - Phase 2 Sprint 3
========================================

High-performance data provider for QuestDB time-series database.

Features:
- InfluxDB line protocol for ultra-fast inserts (1M+ rows/sec)
- PostgreSQL wire protocol for SQL queries
- Connection pooling
- Batch insertion optimization
- Error handling and retry logic

Usage:
    provider = QuestDBProvider(
        ilp_host='localhost',
        ilp_port=9009,
        pg_host='localhost',
        pg_port=8812
    )

    # Fast insert
    await provider.insert_price(symbol='BTC/USD', timestamp=now, close=50000, volume=1000)

    # Batch insert (fastest)
    await provider.insert_prices_batch(prices_list)

    # Query
    df = await provider.get_prices(symbol='BTC/USD', start_time=..., end_time=...)
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import asyncpg
from questdb.ingress import Sender, IngressError, TimestampNanos

logger = logging.getLogger(__name__)


class QuestDBProvider:
    """
    QuestDB data provider with dual-protocol support:
    - InfluxDB line protocol (ILP) for fast writes
    - PostgreSQL wire protocol for queries
    """

    def __init__(
        self,
        ilp_host: str = 'localhost',
        ilp_port: int = 9009,
        pg_host: str = 'localhost',
        pg_port: int = 8812,
        pg_user: str = 'admin',
        pg_password: str = 'quest',
        pg_database: str = 'qdb',
        pg_pool_size: int = 10,
    ):
        """
        Initialize QuestDB provider.

        Args:
            ilp_host: InfluxDB line protocol host
            ilp_port: InfluxDB line protocol port (default 9009)
            pg_host: PostgreSQL wire protocol host
            pg_port: PostgreSQL wire protocol port (default 8812)
            pg_user: PostgreSQL user
            pg_password: PostgreSQL password
            pg_database: PostgreSQL database name
            pg_pool_size: PostgreSQL connection pool size
        """
        # InfluxDB line protocol config
        self.ilp_host = ilp_host
        self.ilp_port = ilp_port

        # PostgreSQL config
        self.pg_host = pg_host
        self.pg_port = pg_port
        self.pg_user = pg_user
        self.pg_password = pg_password
        self.pg_database = pg_database
        self.pg_pool_size = pg_pool_size

        # Connection pool (initialized in async context)
        self.pg_pool: Optional[asyncpg.Pool] = None

        logger.info(f"QuestDBProvider initialized (ILP: {ilp_host}:{ilp_port}, PG: {pg_host}:{pg_port})")

    async def initialize(self):
        """Initialize PostgreSQL connection pool."""
        if self.pg_pool is None:
            self.pg_pool = await asyncpg.create_pool(
                host=self.pg_host,
                port=self.pg_port,
                user=self.pg_user,
                password=self.pg_password,
                database=self.pg_database,
                min_size=2,
                max_size=self.pg_pool_size,
            )
            logger.info(f"PostgreSQL pool created ({self.pg_pool_size} connections)")

    async def close(self):
        """Close PostgreSQL connection pool."""
        if self.pg_pool:
            await self.pg_pool.close()
            self.pg_pool = None
            logger.info("PostgreSQL pool closed")

    # ========================================================================
    # FAST WRITES (InfluxDB Line Protocol)
    # ========================================================================

    async def insert_price(
        self,
        symbol: str,
        timestamp: datetime,
        open_price: float,
        high: float,
        low: float,
        close: float,
        volume: float,
        bid: Optional[float] = None,
        ask: Optional[float] = None,
    ) -> bool:
        """
        Insert single price record (InfluxDB line protocol).

        Args:
            symbol: Trading pair (e.g., 'BTC/USD')
            timestamp: Price timestamp
            open_price: Open price
            high: High price
            low: Low price
            close: Close price
            volume: Volume
            bid: Bid price (optional)
            ask: Ask price (optional)

        Returns:
            True if successful
        """
        try:
            with Sender(self.ilp_host, self.ilp_port) as sender:
                columns = {
                    'open': open_price,
                    'high': high,
                    'low': low,
                    'close': close,
                    'volume': volume,
                }

                if bid is not None:
                    columns['bid'] = bid
                if ask is not None:
                    columns['ask'] = ask
                    if bid is not None:
                        columns['spread'] = ask - bid

                sender.row(
                    'prices',
                    symbols={'symbol': symbol},
                    columns=columns,
                    at=TimestampNanos(int(timestamp.timestamp() * 1_000_000_000))
                )
                sender.flush()

            return True

        except IngressError as e:
            logger.error(f"Failed to insert price for {symbol}: {e}")
            return False

    async def insert_prices_batch(self, prices: List[Dict[str, Any]]) -> int:
        """
        Insert batch of price records (fastest method).

        Args:
            prices: List of price dictionaries with keys:
                - symbol: str
                - timestamp: datetime
                - open, high, low, close, volume: float
                - bid, ask: float (optional)

        Returns:
            Number of successfully inserted rows
        """
        if not prices:
            return 0

        inserted = 0

        try:
            with Sender(self.ilp_host, self.ilp_port) as sender:
                for price in prices:
                    columns = {
                        'open': price['open'],
                        'high': price['high'],
                        'low': price['low'],
                        'close': price['close'],
                        'volume': price['volume'],
                    }

                    if 'bid' in price and price['bid'] is not None:
                        columns['bid'] = price['bid']
                    if 'ask' in price and price['ask'] is not None:
                        columns['ask'] = price['ask']
                        if 'bid' in price and price['bid'] is not None:
                            columns['spread'] = price['ask'] - price['bid']

                    sender.row(
                        'prices',
                        symbols={'symbol': price['symbol']},
                        columns=columns,
                        at=TimestampNanos(int(price['timestamp'].timestamp() * 1_000_000_000))
                    )
                    inserted += 1

                sender.flush()

            logger.info(f"Inserted {inserted} price records")
            return inserted

        except IngressError as e:
            logger.error(f"Failed to insert batch: {e}")
            return inserted

    async def insert_indicator(
        self,
        symbol: str,
        indicator_id: str,
        timestamp: datetime,
        value: float,
        confidence: Optional[float] = None,
        metadata: Optional[str] = None,
    ) -> bool:
        """
        Insert single indicator value (InfluxDB line protocol).

        Args:
            symbol: Trading pair
            indicator_id: Indicator identifier (e.g., 'RSI_14')
            timestamp: Calculation timestamp
            value: Indicator value
            confidence: Confidence score 0-1 (optional)
            metadata: JSON metadata string (optional)

        Returns:
            True if successful
        """
        try:
            with Sender(self.ilp_host, self.ilp_port) as sender:
                columns = {'value': value}

                if confidence is not None:
                    columns['confidence'] = confidence

                # Note: metadata must be sent via PostgreSQL INSERT
                # InfluxDB line protocol doesn't support STRING columns well

                sender.row(
                    'indicators',
                    symbols={
                        'symbol': symbol,
                        'indicator_id': indicator_id,
                    },
                    columns=columns,
                    at=TimestampNanos(int(timestamp.timestamp() * 1_000_000_000))
                )
                sender.flush()

            return True

        except IngressError as e:
            logger.error(f"Failed to insert indicator {indicator_id} for {symbol}: {e}")
            return False

    async def insert_indicators_batch(self, indicators: List[Dict[str, Any]]) -> int:
        """
        Insert batch of indicator values (fastest method).

        Args:
            indicators: List of indicator dictionaries with keys:
                - symbol: str
                - indicator_id: str
                - timestamp: datetime
                - value: float
                - confidence: float (optional)

        Returns:
            Number of successfully inserted rows
        """
        if not indicators:
            return 0

        inserted = 0

        try:
            with Sender(self.ilp_host, self.ilp_port) as sender:
                for indicator in indicators:
                    columns = {'value': indicator['value']}

                    if 'confidence' in indicator and indicator['confidence'] is not None:
                        columns['confidence'] = indicator['confidence']

                    sender.row(
                        'indicators',
                        symbols={
                            'symbol': indicator['symbol'],
                            'indicator_id': indicator['indicator_id'],
                        },
                        columns=columns,
                        at=TimestampNanos(int(indicator['timestamp'].timestamp() * 1_000_000_000))
                    )
                    inserted += 1

                sender.flush()

            logger.info(f"Inserted {inserted} indicator records")
            return inserted

        except IngressError as e:
            logger.error(f"Failed to insert indicator batch: {e}")
            return inserted

    # ========================================================================
    # QUERIES (PostgreSQL Wire Protocol)
    # ========================================================================

    async def get_prices(
        self,
        symbol: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
    ) -> pd.DataFrame:
        """
        Query price data.

        Args:
            symbol: Trading pair
            start_time: Start timestamp (optional)
            end_time: End timestamp (optional)
            limit: Maximum rows to return

        Returns:
            DataFrame with price data
        """
        await self.initialize()

        query = "SELECT * FROM prices WHERE symbol = $1"
        params = [symbol]

        if start_time:
            query += " AND timestamp >= $2"
            params.append(start_time)

        if end_time:
            idx = len(params) + 1
            query += f" AND timestamp <= ${idx}"
            params.append(end_time)

        query += f" ORDER BY timestamp DESC LIMIT ${len(params) + 1}"
        params.append(limit)

        async with self.pg_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame([dict(row) for row in rows])
        return df

    async def get_latest_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get latest price for symbol.

        Args:
            symbol: Trading pair

        Returns:
            Price dictionary or None
        """
        await self.initialize()

        query = """
            SELECT * FROM prices
            WHERE symbol = $1
            LATEST BY symbol
        """

        async with self.pg_pool.acquire() as conn:
            row = await conn.fetchrow(query, symbol)

        if row:
            return dict(row)
        return None

    async def get_indicators(
        self,
        symbol: str,
        indicator_ids: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
    ) -> pd.DataFrame:
        """
        Query indicator data.

        Args:
            symbol: Trading pair
            indicator_ids: List of indicator IDs to filter (optional)
            start_time: Start timestamp (optional)
            end_time: End timestamp (optional)
            limit: Maximum rows per indicator

        Returns:
            DataFrame with indicator data
        """
        await self.initialize()

        query = "SELECT * FROM indicators WHERE symbol = $1"
        params = [symbol]

        if indicator_ids:
            placeholders = ', '.join([f'${i+2}' for i in range(len(indicator_ids))])
            query += f" AND indicator_id IN ({placeholders})"
            params.extend(indicator_ids)

        if start_time:
            idx = len(params) + 1
            query += f" AND timestamp >= ${idx}"
            params.append(start_time)

        if end_time:
            idx = len(params) + 1
            query += f" AND timestamp <= ${idx}"
            params.append(end_time)

        query += f" ORDER BY timestamp DESC LIMIT ${len(params) + 1}"
        params.append(limit)

        async with self.pg_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame([dict(row) for row in rows])
        return df

    async def get_latest_indicators(
        self,
        symbol: str,
        indicator_ids: Optional[List[str]] = None,
    ) -> Dict[str, float]:
        """
        Get latest values for all indicators.

        Args:
            symbol: Trading pair
            indicator_ids: List of indicator IDs to filter (optional)

        Returns:
            Dictionary: {indicator_id: value}
        """
        await self.initialize()

        if indicator_ids:
            placeholders = ', '.join([f'${i+2}' for i in range(len(indicator_ids))])
            query = f"""
                SELECT indicator_id, value
                FROM indicators
                WHERE symbol = $1
                  AND indicator_id IN ({placeholders})
                LATEST BY indicator_id
            """
            params = [symbol] + indicator_ids
        else:
            query = """
                SELECT indicator_id, value
                FROM indicators
                WHERE symbol = $1
                LATEST BY indicator_id
            """
            params = [symbol]

        async with self.pg_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return {row['indicator_id']: row['value'] for row in rows}

    async def get_ohlcv_resample(
        self,
        symbol: str,
        interval: str = '1m',
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        Get resampled OHLCV data.

        Args:
            symbol: Trading pair
            interval: Resample interval ('1s', '1m', '5m', '1h', '1d')
            start_time: Start timestamp (optional)
            end_time: End timestamp (optional)

        Returns:
            DataFrame with resampled OHLCV
        """
        await self.initialize()

        query = f"""
            SELECT
                timestamp,
                first(open) as open,
                max(high) as high,
                min(low) as low,
                last(close) as close,
                sum(volume) as volume
            FROM prices
            WHERE symbol = $1
        """
        params = [symbol]

        if start_time:
            query += " AND timestamp >= $2"
            params.append(start_time)

        if end_time:
            idx = len(params) + 1
            query += f" AND timestamp <= ${idx}"
            params.append(end_time)

        query += f" SAMPLE BY {interval} ALIGN TO CALENDAR"

        async with self.pg_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame([dict(row) for row in rows])
        return df

    # ========================================================================
    # DATA COLLECTION SUPPORT
    # ========================================================================

    async def insert_tick_prices_batch(self, ticks: List[Dict[str, Any]]) -> int:
        """
        Insert batch of tick price data (high-frequency).

        Args:
            ticks: List of tick dictionaries with keys:
                - session_id: str
                - symbol: str
                - timestamp: float (seconds with decimal precision)
                - price: float
                - volume: float
                - quote_volume: float

        Returns:
            Number of successfully inserted rows
        """
        if not ticks:
            return 0

        inserted = 0

        try:
            with Sender(self.ilp_host, self.ilp_port) as sender:
                for tick in ticks:
                    timestamp_seconds = float(tick['timestamp'])
                    timestamp_ns = int(timestamp_seconds * 1_000_000_000)

                    sender.row(
                        'tick_prices',
                        symbols={
                            'session_id': tick['session_id'],
                            'symbol': tick['symbol'],
                        },
                        columns={
                            'price': float(tick['price']),
                            'volume': float(tick['volume']),
                            'quote_volume': float(tick['quote_volume']),
                        },
                        at=TimestampNanos(timestamp_ns)
                    )
                    inserted += 1

                sender.flush()

            logger.debug(f"Inserted {inserted} tick price records")
            return inserted

        except IngressError as e:
            logger.error(f"Failed to insert tick batch: {e}")
            return inserted

    async def insert_orderbook_snapshots_batch(self, snapshots: List[Dict[str, Any]]) -> int:
        """
        Insert batch of orderbook snapshots (3-level).

        Args:
            snapshots: List of orderbook dictionaries with keys:
                - session_id: str
                - symbol: str
                - timestamp: float (seconds with decimal precision)
                - bid_price_1, bid_qty_1, bid_price_2, bid_qty_2, bid_price_3, bid_qty_3: float
                - ask_price_1, ask_qty_1, ask_price_2, ask_qty_2, ask_price_3, ask_qty_3: float

        Returns:
            Number of successfully inserted rows
        """
        if not snapshots:
            return 0

        inserted = 0

        try:
            with Sender(self.ilp_host, self.ilp_port) as sender:
                for snapshot in snapshots:
                    timestamp_seconds = float(snapshot['timestamp'])
                    timestamp_ns = int(timestamp_seconds * 1_000_000_000)

                    sender.row(
                        'tick_orderbook',
                        symbols={
                            'session_id': snapshot['session_id'],
                            'symbol': snapshot['symbol'],
                        },
                        columns={
                            'bid_price_1': float(snapshot.get('bid_price_1', 0)),
                            'bid_qty_1': float(snapshot.get('bid_qty_1', 0)),
                            'bid_price_2': float(snapshot.get('bid_price_2', 0)),
                            'bid_qty_2': float(snapshot.get('bid_qty_2', 0)),
                            'bid_price_3': float(snapshot.get('bid_price_3', 0)),
                            'bid_qty_3': float(snapshot.get('bid_qty_3', 0)),
                            'ask_price_1': float(snapshot.get('ask_price_1', 0)),
                            'ask_qty_1': float(snapshot.get('ask_qty_1', 0)),
                            'ask_price_2': float(snapshot.get('ask_price_2', 0)),
                            'ask_qty_2': float(snapshot.get('ask_qty_2', 0)),
                            'ask_price_3': float(snapshot.get('ask_price_3', 0)),
                            'ask_qty_3': float(snapshot.get('ask_qty_3', 0)),
                        },
                        at=TimestampNanos(timestamp_ns)
                    )
                    inserted += 1

                sender.flush()

            logger.debug(f"Inserted {inserted} orderbook snapshot records")
            return inserted

        except IngressError as e:
            logger.error(f"Failed to insert orderbook batch: {e}")
            return inserted

    async def insert_ohlcv_candles_batch(self, candles: List[Dict[str, Any]]) -> int:
        """
        Insert batch of pre-aggregated OHLCV candles.

        Args:
            candles: List of candle dictionaries with keys:
                - session_id: str
                - symbol: str
                - interval: str ('1m', '5m', '15m', '1h', etc.)
                - timestamp: float (candle start time in seconds)
                - open, high, low, close, volume, quote_volume: float
                - trades_count: int
                - is_closed: bool

        Returns:
            Number of successfully inserted rows
        """
        if not candles:
            return 0

        inserted = 0

        try:
            with Sender(self.ilp_host, self.ilp_port) as sender:
                for candle in candles:
                    timestamp_seconds = float(candle['timestamp'])
                    timestamp_ns = int(timestamp_seconds * 1_000_000_000)

                    sender.row(
                        'aggregated_ohlcv',
                        symbols={
                            'session_id': candle['session_id'],
                            'symbol': candle['symbol'],
                            'interval': candle['interval'],
                        },
                        columns={
                            'open': float(candle['open']),
                            'high': float(candle['high']),
                            'low': float(candle['low']),
                            'close': float(candle['close']),
                            'volume': float(candle['volume']),
                            'quote_volume': float(candle['quote_volume']),
                            'trades_count': int(candle['trades_count']),
                            'is_closed': bool(candle.get('is_closed', False)),
                        },
                        at=TimestampNanos(timestamp_ns)
                    )
                    inserted += 1

                sender.flush()

            logger.debug(f"Inserted {inserted} OHLCV candle records")
            return inserted

        except IngressError as e:
            logger.error(f"Failed to insert OHLCV batch: {e}")
            return inserted

    async def execute_query(self, query: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute arbitrary SQL query via PostgreSQL wire protocol.

        Args:
            query: SQL query string
            params: Query parameters (optional)

        Returns:
            List of result dictionaries
        """
        await self.initialize()

        try:
            async with self.pg_pool.acquire() as conn:
                if params:
                    rows = await conn.fetch(query, *params)
                else:
                    rows = await conn.fetch(query)

            return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Query execution failed: {e}\nQuery: {query}")
            raise

    # ========================================================================
    # BACKTEST SUPPORT
    # ========================================================================

    async def get_backtest_data(
        self,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        indicator_ids: List[str],
    ) -> Tuple[pd.DataFrame, Dict[str, pd.Series]]:
        """
        Get data for backtesting (prices + indicators).

        Args:
            symbol: Trading pair
            start_time: Backtest start time
            end_time: Backtest end time
            indicator_ids: List of required indicators

        Returns:
            Tuple of (prices_df, indicators_dict)
        """
        # Get prices
        prices_df = await self.get_prices(
            symbol=symbol,
            start_time=start_time,
            end_time=end_time,
            limit=1000000  # No limit for backtest
        )

        # Get indicators
        indicators_df = await self.get_indicators(
            symbol=symbol,
            indicator_ids=indicator_ids,
            start_time=start_time,
            end_time=end_time,
            limit=1000000
        )

        # Pivot indicators to dict of series
        indicators_dict = {}
        if not indicators_df.empty:
            for indicator_id in indicator_ids:
                indicator_data = indicators_df[indicators_df['indicator_id'] == indicator_id]
                if not indicator_data.empty:
                    indicators_dict[indicator_id] = indicator_data.set_index('timestamp')['value']

        return prices_df, indicators_dict

    # ========================================================================
    # DELETE OPERATIONS (Application-Level Cascade)
    # ========================================================================

    async def delete_tick_prices(
        self,
        session_id: str,
        symbol: Optional[str] = None
    ) -> int:
        """
        Delete tick price data for session.

        Args:
            session_id: Session identifier
            symbol: Optional symbol filter (deletes all symbols if None)

        Returns:
            Number of rows deleted
        """
        await self.initialize()

        try:
            if symbol:
                query = "DELETE FROM tick_prices WHERE session_id = $1 AND symbol = $2"
                params = [session_id, symbol]
            else:
                query = "DELETE FROM tick_prices WHERE session_id = $1"
                params = [session_id]

            async with self.pg_pool.acquire() as conn:
                result = await conn.execute(query, *params)
                # Parse result: "DELETE N" -> N
                deleted_count = int(result.split()[-1]) if result else 0

            logger.info(f"Deleted {deleted_count} tick_prices rows for session {session_id}" +
                       (f", symbol {symbol}" if symbol else ""))
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to delete tick_prices for session {session_id}: {e}")
            raise

    async def delete_tick_orderbook(
        self,
        session_id: str,
        symbol: Optional[str] = None
    ) -> int:
        """
        Delete orderbook snapshots for session.

        Args:
            session_id: Session identifier
            symbol: Optional symbol filter (deletes all symbols if None)

        Returns:
            Number of rows deleted
        """
        await self.initialize()

        try:
            if symbol:
                query = "DELETE FROM tick_orderbook WHERE session_id = $1 AND symbol = $2"
                params = [session_id, symbol]
            else:
                query = "DELETE FROM tick_orderbook WHERE session_id = $1"
                params = [session_id]

            async with self.pg_pool.acquire() as conn:
                result = await conn.execute(query, *params)
                deleted_count = int(result.split()[-1]) if result else 0

            logger.info(f"Deleted {deleted_count} tick_orderbook rows for session {session_id}" +
                       (f", symbol {symbol}" if symbol else ""))
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to delete tick_orderbook for session {session_id}: {e}")
            raise

    async def delete_aggregated_ohlcv(
        self,
        session_id: str,
        symbol: Optional[str] = None
    ) -> int:
        """
        Delete aggregated OHLCV candles for session.

        Args:
            session_id: Session identifier
            symbol: Optional symbol filter (deletes all symbols if None)

        Returns:
            Number of rows deleted
        """
        await self.initialize()

        try:
            if symbol:
                query = "DELETE FROM aggregated_ohlcv WHERE session_id = $1 AND symbol = $2"
                params = [session_id, symbol]
            else:
                query = "DELETE FROM aggregated_ohlcv WHERE session_id = $1"
                params = [session_id]

            async with self.pg_pool.acquire() as conn:
                result = await conn.execute(query, *params)
                deleted_count = int(result.split()[-1]) if result else 0

            logger.info(f"Deleted {deleted_count} aggregated_ohlcv rows for session {session_id}" +
                       (f", symbol {symbol}" if symbol else ""))
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to delete aggregated_ohlcv for session {session_id}: {e}")
            raise

    async def delete_indicators(
        self,
        session_id: str,
        symbol: Optional[str] = None,
        indicator_id: Optional[str] = None
    ) -> int:
        """
        Delete indicator values for session.

        Args:
            session_id: Session identifier
            symbol: Optional symbol filter
            indicator_id: Optional indicator ID filter

        Returns:
            Number of rows deleted
        """
        await self.initialize()

        try:
            query = "DELETE FROM indicators WHERE session_id = $1"
            params = [session_id]

            if symbol:
                query += " AND symbol = $2"
                params.append(symbol)

            if indicator_id:
                param_idx = len(params) + 1
                query += f" AND indicator_id = ${param_idx}"
                params.append(indicator_id)

            async with self.pg_pool.acquire() as conn:
                result = await conn.execute(query, *params)
                deleted_count = int(result.split()[-1]) if result else 0

            logger.info(f"Deleted {deleted_count} indicators rows for session {session_id}" +
                       (f", symbol {symbol}" if symbol else "") +
                       (f", indicator {indicator_id}" if indicator_id else ""))
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to delete indicators for session {session_id}: {e}")
            raise

    async def delete_backtest_results(self, session_id: str) -> int:
        """
        Delete backtest results linked to session.

        Args:
            session_id: Session identifier

        Returns:
            Number of rows deleted
        """
        await self.initialize()

        try:
            query = "DELETE FROM backtest_results WHERE session_id = $1"

            async with self.pg_pool.acquire() as conn:
                result = await conn.execute(query, session_id)
                deleted_count = int(result.split()[-1]) if result else 0

            logger.info(f"Deleted {deleted_count} backtest_results rows for session {session_id}")
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to delete backtest_results for session {session_id}: {e}")
            raise

    async def delete_session_metadata(self, session_id: str) -> int:
        """
        Delete session metadata record.

        WARNING: This should be called LAST after all child data is deleted.

        Args:
            session_id: Session identifier

        Returns:
            Number of rows deleted (should be 1)
        """
        await self.initialize()

        try:
            query = "DELETE FROM data_collection_sessions WHERE session_id = $1"

            async with self.pg_pool.acquire() as conn:
                result = await conn.execute(query, session_id)
                deleted_count = int(result.split()[-1]) if result else 0

            logger.info(f"Deleted session metadata for {session_id}")
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to delete session metadata for {session_id}: {e}")
            raise

    async def delete_session_cascade(self, session_id: str) -> Dict[str, int]:
        """
        Delete all data for session (cascade delete).

        Deletes in correct order:
        1. Backtest results (most dispensable)
        2. Indicators (computed from prices)
        3. Aggregated OHLCV (derived data)
        4. Orderbook snapshots
        5. Tick prices
        6. Session metadata (parent record)

        Args:
            session_id: Session identifier

        Returns:
            Dictionary with deleted row counts per table:
            {
                'backtest_results': N,
                'indicators': N,
                'aggregated_ohlcv': N,
                'tick_orderbook': N,
                'tick_prices': N,
                'data_collection_sessions': N,
                'total': N
            }
        """
        logger.info(f"Starting cascade delete for session {session_id}")

        deleted_counts = {}

        try:
            # 1. Delete backtest results
            deleted_counts['backtest_results'] = await self.delete_backtest_results(session_id)

            # 2. Delete indicators
            deleted_counts['indicators'] = await self.delete_indicators(session_id)

            # 3. Delete aggregated OHLCV
            deleted_counts['aggregated_ohlcv'] = await self.delete_aggregated_ohlcv(session_id)

            # 4. Delete orderbook snapshots
            deleted_counts['tick_orderbook'] = await self.delete_tick_orderbook(session_id)

            # 5. Delete tick prices
            deleted_counts['tick_prices'] = await self.delete_tick_prices(session_id)

            # 6. Delete session metadata (parent record - LAST)
            deleted_counts['data_collection_sessions'] = await self.delete_session_metadata(session_id)

            # Calculate total
            deleted_counts['total'] = sum(deleted_counts.values())

            logger.info(f"Cascade delete completed for session {session_id}: " +
                       f"total {deleted_counts['total']} rows deleted")

            return deleted_counts

        except Exception as e:
            logger.error(f"Cascade delete failed for session {session_id}: {e}")
            # Return partial counts if any deletes succeeded
            deleted_counts['total'] = sum(deleted_counts.values())
            deleted_counts['error'] = str(e)
            raise

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    async def health_check(self) -> Dict[str, bool]:
        """
        Check QuestDB connection health.

        Returns:
            Dictionary with status of ILP and PostgreSQL
        """
        health = {
            'ilp': False,
            'postgresql': False,
        }

        # Test InfluxDB line protocol
        try:
            with Sender(self.ilp_host, self.ilp_port) as sender:
                sender.row(
                    'health_check',
                    symbols={'test': 'test'},
                    columns={'value': 1.0},
                    at=TimestampNanos.now()
                )
                sender.flush()
            health['ilp'] = True
        except Exception as e:
            logger.warning(f"ILP health check failed: {e}")

        # Test PostgreSQL
        try:
            await self.initialize()
            async with self.pg_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            health['postgresql'] = True
        except Exception as e:
            logger.warning(f"PostgreSQL health check failed: {e}")

        return health


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

async def example_usage():
    """Example usage of QuestDBProvider."""

    provider = QuestDBProvider()

    # Initialize
    await provider.initialize()

    # Insert single price
    await provider.insert_price(
        symbol='BTC/USD',
        timestamp=datetime.utcnow(),
        open_price=50000.0,
        high=50100.0,
        low=49900.0,
        close=50050.0,
        volume=1000000.0,
    )

    # Insert batch of prices
    prices = [
        {
            'symbol': 'BTC/USD',
            'timestamp': datetime.utcnow() - timedelta(seconds=i),
            'open': 50000 + i,
            'high': 50100 + i,
            'low': 49900 + i,
            'close': 50050 + i,
            'volume': 1000000,
        }
        for i in range(100)
    ]
    await provider.insert_prices_batch(prices)

    # Insert indicators
    await provider.insert_indicator(
        symbol='BTC/USD',
        indicator_id='RSI_14',
        timestamp=datetime.utcnow(),
        value=45.5,
        confidence=0.95,
    )

    # Query latest price
    latest = await provider.get_latest_price('BTC/USD')
    print(f"Latest price: {latest}")

    # Query latest indicators
    indicators = await provider.get_latest_indicators('BTC/USD')
    print(f"Latest indicators: {indicators}")

    # Health check
    health = await provider.health_check()
    print(f"Health: {health}")

    # Close
    await provider.close()


if __name__ == "__main__":
    asyncio.run(example_usage())
