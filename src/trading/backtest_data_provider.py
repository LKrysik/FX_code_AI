"""
Backtesting Market Data Provider
=================================
Provides historical market data and indicator values from TimescaleDB
for accurate backtesting.

Replaces hardcoded prices with real historical data.
Uses continuous aggregates for performance.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

from ..database.timescale_client import TimescaleClient


@dataclass
class MarketDataSnapshot:
    """Snapshot of market data at a specific time"""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class IndicatorSnapshot:
    """Snapshot of indicator values at a specific time"""
    symbol: str
    timestamp: datetime
    indicators: Dict[str, float]  # {indicator_id: value}


class BacktestMarketDataProvider:
    """
    Provides historical market data and indicators from TimescaleDB.

    Features:
    - Query historical OHLCV data (with continuous aggregates)
    - Query indicator values calculated by scheduler
    - Cache recent data for performance
    - Support multiple timeframes (1s, 1m, 5m via continuous aggregates)
    """

    def __init__(self, db_client: TimescaleClient, cache_size: int = 1000):
        self.db_client = db_client
        self.cache_size = cache_size

        # Cache: {(symbol, timestamp): MarketDataSnapshot}
        self.price_cache: Dict[Tuple[str, datetime], MarketDataSnapshot] = {}

        # Indicator cache: {(symbol, timestamp): IndicatorSnapshot}
        self.indicator_cache: Dict[Tuple[str, datetime], IndicatorSnapshot] = {}

        # Current prices (for real-time mode)
        self.current_prices: Dict[str, float] = {}

    def update_current_price(self, symbol: str, price: float):
        """Update current price for a symbol (used in real-time data replay)"""
        self.current_prices[symbol] = price

    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for symbol"""
        return self.current_prices.get(symbol)

    async def get_price_at_time(
        self,
        symbol: str,
        timestamp: datetime,
        timeframe: str = "1s"
    ) -> Optional[float]:
        """
        Get close price for symbol at specific timestamp.

        Args:
            symbol: Trading symbol
            timestamp: Time to query
            timeframe: "1s" (raw), "1m", "5m" (continuous aggregates)

        Returns:
            Close price or None if not found
        """
        # Check cache first
        cache_key = (symbol, timestamp)
        if cache_key in self.price_cache:
            return self.price_cache[cache_key].close

        # Query database
        snapshot = await self.get_market_data_at_time(symbol, timestamp, timeframe)

        if snapshot:
            # Update cache
            self.price_cache[cache_key] = snapshot
            self._trim_cache()
            return snapshot.close

        return None

    async def get_market_data_at_time(
        self,
        symbol: str,
        timestamp: datetime,
        timeframe: str = "1s"
    ) -> Optional[MarketDataSnapshot]:
        """
        Get complete OHLCV data at specific timestamp.

        Uses continuous aggregates for 1m/5m timeframes (faster queries).
        """
        try:
            async with self.db_client.pool.acquire() as conn:
                if timeframe == "1m":
                    # Use continuous aggregate (pre-computed 1m candles)
                    query = """
                        SELECT bucket AS ts, symbol, open, high, low, close, volume
                        FROM market_data_1m
                        WHERE symbol = $1
                          AND bucket <= $2
                        ORDER BY bucket DESC
                        LIMIT 1
                    """
                elif timeframe == "5m":
                    # Use continuous aggregate (pre-computed 5m candles)
                    query = """
                        SELECT bucket AS ts, symbol, open, high, low, close, volume
                        FROM market_data_5m
                        WHERE symbol = $1
                          AND bucket <= $2
                        ORDER BY bucket DESC
                        LIMIT 1
                    """
                else:
                    # Use raw 1s data
                    query = """
                        SELECT ts, symbol, open, high, low, close, volume
                        FROM market_data
                        WHERE symbol = $1
                          AND ts <= $2
                        ORDER BY ts DESC
                        LIMIT 1
                    """

                row = await conn.fetchrow(query, symbol, timestamp)

                if row:
                    return MarketDataSnapshot(
                        symbol=row['symbol'],
                        timestamp=row['ts'],
                        open=float(row['open']),
                        high=float(row['high']),
                        low=float(row['low']),
                        close=float(row['close']),
                        volume=float(row['volume'])
                    )

                return None

        except Exception as e:
            # Log error but don't crash
            print(f"Error querying market data: {e}")
            return None

    async def get_price_range(
        self,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        timeframe: str = "1m"
    ) -> List[MarketDataSnapshot]:
        """
        Get range of market data (for backtesting initialization).

        Uses continuous aggregates for better performance.
        """
        try:
            async with self.db_client.pool.acquire() as conn:
                if timeframe == "1m":
                    table = "market_data_1m"
                    time_col = "bucket"
                elif timeframe == "5m":
                    table = "market_data_5m"
                    time_col = "bucket"
                else:
                    table = "market_data"
                    time_col = "ts"

                query = f"""
                    SELECT {time_col} AS ts, symbol, open, high, low, close, volume
                    FROM {table}
                    WHERE symbol = $1
                      AND {time_col} >= $2
                      AND {time_col} <= $3
                    ORDER BY {time_col} ASC
                """

                rows = await conn.fetch(query, symbol, start_time, end_time)

                return [
                    MarketDataSnapshot(
                        symbol=row['symbol'],
                        timestamp=row['ts'],
                        open=float(row['open']),
                        high=float(row['high']),
                        low=float(row['low']),
                        close=float(row['close']),
                        volume=float(row['volume'])
                    )
                    for row in rows
                ]

        except Exception as e:
            print(f"Error querying price range: {e}")
            return []

    async def get_indicators_at_time(
        self,
        symbol: str,
        timestamp: datetime,
        indicator_ids: Optional[List[str]] = None
    ) -> Optional[IndicatorSnapshot]:
        """
        Get indicator values at specific timestamp.

        Args:
            symbol: Trading symbol
            timestamp: Time to query
            indicator_ids: List of indicator IDs to fetch (None = all)

        Returns:
            IndicatorSnapshot with all indicator values
        """
        # Check cache
        cache_key = (symbol, timestamp)
        if cache_key in self.indicator_cache:
            cached = self.indicator_cache[cache_key]
            if not indicator_ids or all(ind_id in cached.indicators for ind_id in indicator_ids):
                return cached

        try:
            async with self.db_client.pool.acquire() as conn:
                if indicator_ids:
                    # Query specific indicators
                    query = """
                        SELECT indicator_id, value
                        FROM indicators
                        WHERE symbol = $1
                          AND ts <= $2
                          AND indicator_id = ANY($3)
                          AND ts = (
                              SELECT MAX(ts)
                              FROM indicators AS i2
                              WHERE i2.symbol = indicators.symbol
                                AND i2.indicator_id = indicators.indicator_id
                                AND i2.ts <= $2
                          )
                    """
                    rows = await conn.fetch(query, symbol, timestamp, indicator_ids)
                else:
                    # Query all indicators for symbol
                    query = """
                        SELECT DISTINCT ON (indicator_id) indicator_id, value, ts
                        FROM indicators
                        WHERE symbol = $1
                          AND ts <= $2
                        ORDER BY indicator_id, ts DESC
                    """
                    rows = await conn.fetch(query, symbol, timestamp)

                if rows:
                    indicators = {row['indicator_id']: float(row['value']) for row in rows}

                    snapshot = IndicatorSnapshot(
                        symbol=symbol,
                        timestamp=timestamp,
                        indicators=indicators
                    )

                    # Update cache
                    self.indicator_cache[cache_key] = snapshot
                    self._trim_cache()

                    return snapshot

                return None

        except Exception as e:
            print(f"Error querying indicators: {e}")
            return None

    async def get_indicator_range(
        self,
        symbol: str,
        indicator_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[Tuple[datetime, float]]:
        """
        Get time series of indicator values.

        Useful for analyzing indicator behavior over time.
        """
        try:
            async with self.db_client.pool.acquire() as conn:
                query = """
                    SELECT ts, value
                    FROM indicators
                    WHERE symbol = $1
                      AND indicator_id = $2
                      AND ts >= $3
                      AND ts <= $4
                    ORDER BY ts ASC
                """

                rows = await conn.fetch(query, symbol, indicator_id, start_time, end_time)

                return [(row['ts'], float(row['value'])) for row in rows]

        except Exception as e:
            print(f"Error querying indicator range: {e}")
            return []

    def _trim_cache(self):
        """Trim caches to max size (LRU-style)"""
        if len(self.price_cache) > self.cache_size:
            # Remove oldest 20% of entries
            to_remove = len(self.price_cache) - self.cache_size + (self.cache_size // 5)
            for key in list(self.price_cache.keys())[:to_remove]:
                del self.price_cache[key]

        if len(self.indicator_cache) > self.cache_size:
            to_remove = len(self.indicator_cache) - self.cache_size + (self.cache_size // 5)
            for key in list(self.indicator_cache.keys())[:to_remove]:
                del self.indicator_cache[key]

    def clear_cache(self):
        """Clear all caches"""
        self.price_cache.clear()
        self.indicator_cache.clear()

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        return {
            "price_cache_size": len(self.price_cache),
            "indicator_cache_size": len(self.indicator_cache),
            "cache_size_limit": self.cache_size
        }
