"""
TimescaleDB Client with COPY Bulk Insert
========================================
High-performance async client for TimescaleDB operations.

Features:
- Connection pooling (asyncpg)
- COPY bulk insert (100x faster than INSERT)
- Batch operations
- Query helpers for time-series data
"""

import asyncpg
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class TimescaleConfig:
    """TimescaleDB connection configuration"""
    host: str = "localhost"
    port: int = 5432
    database: str = "trading"
    user: str = "trading_user"
    password: str = "trading_pass_2024"
    min_pool_size: int = 5
    max_pool_size: int = 20
    command_timeout: float = 60.0


class TimescaleClient:
    """
    Async TimescaleDB client with COPY bulk insert support.

    Per user requirement: Use COPY for bulk indicator inserts (100x faster).
    """

    def __init__(self, config: Optional[TimescaleConfig] = None):
        self.config = config or TimescaleConfig()
        self.pool: Optional[asyncpg.Pool] = None
        self._connection_string = self._build_connection_string()

    def _build_connection_string(self) -> str:
        """Build PostgreSQL connection string"""
        return (
            f"postgresql://{self.config.user}:{self.config.password}@"
            f"{self.config.host}:{self.config.port}/{self.config.database}"
        )

    async def connect(self):
        """Initialize connection pool"""
        if self.pool is not None:
            logger.warning("Connection pool already exists")
            return

        try:
            self.pool = await asyncpg.create_pool(
                self._connection_string,
                min_size=self.config.min_pool_size,
                max_size=self.config.max_pool_size,
                command_timeout=self.config.command_timeout,
                server_settings={
                    'jit': 'off',  # Disable JIT for faster startup
                    'timezone': 'UTC'
                }
            )
            logger.info(f"Connected to TimescaleDB at {self.config.host}:{self.config.port}")

            # Test connection
            async with self.pool.acquire() as conn:
                version = await conn.fetchval("SELECT version()")
                logger.info(f"PostgreSQL version: {version}")

                # Check TimescaleDB extension
                ts_version = await conn.fetchval(
                    "SELECT extversion FROM pg_extension WHERE extname = 'timescaledb'"
                )
                logger.info(f"TimescaleDB version: {ts_version}")

        except Exception as e:
            logger.error(f"Failed to connect to TimescaleDB: {e}")
            raise

    async def disconnect(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("Disconnected from TimescaleDB")

    # ========================================================================
    # MARKET DATA OPERATIONS
    # ========================================================================

    async def insert_market_data(self, data: Dict[str, Any]):
        """
        Insert single OHLCV bar.
        For bulk inserts, use bulk_insert_market_data() with COPY.
        """
        query = """
            INSERT INTO market_data (ts, symbol, open, high, low, close, volume, trades_count, vwap)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ON CONFLICT (ts, symbol) DO UPDATE
            SET close = EXCLUDED.close,
                high = GREATEST(market_data.high, EXCLUDED.high),
                low = LEAST(market_data.low, EXCLUDED.low),
                volume = market_data.volume + EXCLUDED.volume,
                trades_count = market_data.trades_count + EXCLUDED.trades_count
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                query,
                data['ts'], data['symbol'], data['open'], data['high'],
                data['low'], data['close'], data['volume'],
                data.get('trades_count', 0), data.get('vwap')
            )

    async def bulk_insert_market_data(self, data_list: List[Dict[str, Any]]):
        """
        Bulk insert OHLCV data using COPY (100x faster than INSERT).
        User requirement: Use COPY for bulk operations.
        """
        if not data_list:
            return

        async with self.pool.acquire() as conn:
            # Prepare data for COPY
            records = [
                (
                    d['ts'], d['symbol'], d['open'], d['high'], d['low'],
                    d['close'], d['volume'], d.get('trades_count', 0), d.get('vwap')
                )
                for d in data_list
            ]

            # Use COPY for bulk insert
            await conn.copy_records_to_table(
                'market_data',
                records=records,
                columns=['ts', 'symbol', 'open', 'high', 'low', 'close', 'volume', 'trades_count', 'vwap']
            )

            logger.debug(f"Bulk inserted {len(records)} market data records using COPY")

    async def get_market_data_range(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        interval: str = '1m'
    ) -> List[Dict]:
        """
        Get OHLCV data for time range.
        Uses continuous aggregates (1m/5m) if available for better performance.
        """
        query = """
            SELECT * FROM get_ohlcv_range($1, $2, $3, $4)
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, symbol, start, end, interval)
            return [dict(row) for row in rows]

    async def get_latest_price(self, symbol: str) -> Optional[float]:
        """Get latest close price for symbol"""
        query = "SELECT get_latest_price($1)"
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, symbol)

    # ========================================================================
    # INDICATOR OPERATIONS (with COPY bulk insert)
    # ========================================================================

    async def insert_indicator_value(
        self,
        ts: datetime,
        symbol: str,
        indicator_type: str,
        indicator_id: str,
        value: float,
        metadata: Optional[Dict] = None
    ):
        """
        Insert single indicator value.
        For bulk inserts, use bulk_insert_indicators() with COPY.
        """
        query = """
            INSERT INTO indicators (ts, symbol, indicator_type, indicator_id, value, metadata)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (ts, symbol, indicator_id) DO UPDATE
            SET value = EXCLUDED.value,
                metadata = EXCLUDED.metadata
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                query, ts, symbol, indicator_type, indicator_id, value,
                metadata if metadata else None
            )

    async def bulk_insert_indicators(self, indicators: List[Tuple]):
        """
        Bulk insert indicator values using COPY (user requirement).

        Args:
            indicators: List of tuples (ts, symbol, indicator_type, indicator_id, value, metadata)

        Performance: 100x faster than individual INSERTs.
        Example: 10,000 indicators in 100ms instead of 10 seconds.
        """
        if not indicators:
            return

        async with self.pool.acquire() as conn:
            # Use PostgreSQL COPY for bulk insert
            await conn.copy_records_to_table(
                'indicators',
                records=indicators,
                columns=['ts', 'symbol', 'indicator_type', 'indicator_id', 'value', 'metadata']
            )

            logger.debug(f"Bulk inserted {len(indicators)} indicators using COPY")

    async def get_indicator_values(
        self,
        symbol: str,
        indicator_id: str,
        start: datetime,
        end: datetime
    ) -> List[Dict]:
        """Get indicator values for time range"""
        query = """
            SELECT ts, value, metadata
            FROM indicators
            WHERE symbol = $1 AND indicator_id = $2
              AND ts BETWEEN $3 AND $4
            ORDER BY ts ASC
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, symbol, indicator_id, start, end)
            return [dict(row) for row in rows]

    async def get_latest_indicator_value(
        self,
        symbol: str,
        indicator_id: str
    ) -> Optional[float]:
        """Get latest value for indicator"""
        query = """
            SELECT value
            FROM indicators
            WHERE symbol = $1 AND indicator_id = $2
            ORDER BY ts DESC
            LIMIT 1
        """
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, symbol, indicator_id)

    # ========================================================================
    # TRADE OPERATIONS
    # ========================================================================

    async def bulk_insert_trades(self, trades: List[Dict]):
        """Bulk insert trade records using COPY"""
        if not trades:
            return

        records = [
            (
                t['ts'], t['symbol'], t.get('trade_id'), t['price'],
                t['quantity'], t.get('side'), t.get('is_buyer_maker')
            )
            for t in trades
        ]

        async with self.pool.acquire() as conn:
            await conn.copy_records_to_table(
                'trades',
                records=records,
                columns=['ts', 'symbol', 'trade_id', 'price', 'quantity', 'side', 'is_buyer_maker']
            )

            logger.debug(f"Bulk inserted {len(records)} trades using COPY")

    async def get_trades_range(
        self,
        symbol: str,
        start: datetime,
        end: datetime
    ) -> List[Dict]:
        """Get trades for time range"""
        query = """
            SELECT ts, trade_id, price, quantity, side, is_buyer_maker
            FROM trades
            WHERE symbol = $1 AND ts BETWEEN $2 AND $3
            ORDER BY ts ASC
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, symbol, start, end)
            return [dict(row) for row in rows]

    # ========================================================================
    # ORDERBOOK OPERATIONS
    # ========================================================================

    async def insert_orderbook_snapshot(self, data: Dict):
        """Insert orderbook snapshot"""
        query = """
            INSERT INTO orderbook_snapshots (ts, symbol, bids, asks, best_bid, best_ask, bid_qty, ask_qty)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                query,
                data['ts'], data['symbol'], data['bids'], data['asks'],
                data['best_bid'], data['best_ask'], data['bid_qty'], data['ask_qty']
            )

    async def get_orderbook_snapshots(
        self,
        symbol: str,
        start: datetime,
        end: datetime
    ) -> List[Dict]:
        """Get orderbook snapshots for time range"""
        query = """
            SELECT ts, bids, asks, best_bid, best_ask, bid_qty, ask_qty
            FROM orderbook_snapshots
            WHERE symbol = $1 AND ts BETWEEN $2 AND $3
            ORDER BY ts ASC
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, symbol, start, end)
            return [dict(row) for row in rows]

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    async def get_database_stats(self) -> List[Dict]:
        """Get database statistics (row counts, sizes, etc.)"""
        query = "SELECT * FROM database_stats"
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query)
            return [dict(row) for row in rows]

    async def get_symbol_list(self) -> List[str]:
        """Get list of all symbols in database"""
        query = "SELECT DISTINCT symbol FROM market_data ORDER BY symbol"
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query)
            return [row['symbol'] for row in rows]

    async def get_data_range(self, symbol: str) -> Optional[Tuple[datetime, datetime]]:
        """Get oldest and newest data timestamps for symbol"""
        query = """
            SELECT MIN(ts) AS oldest, MAX(ts) AS newest
            FROM market_data
            WHERE symbol = $1
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, symbol)
            if row and row['oldest'] and row['newest']:
                return (row['oldest'], row['newest'])
            return None

    async def execute_query(self, query: str, *args) -> List[Dict]:
        """Execute custom query and return results"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]

    async def health_check(self) -> bool:
        """Check if database connection is healthy"""
        try:
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
