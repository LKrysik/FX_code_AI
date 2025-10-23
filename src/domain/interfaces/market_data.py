"""
Market Data Interfaces - Ports for market data providers
========================================================
Abstract interfaces for market data access without coupling to specific exchanges.
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, List, Optional, Dict, Any
from datetime import datetime

from ..models.market_data import MarketData, OrderBook, PriceHistory


class IMarketDataProvider(ABC):
    """
    Interface for market data providers.
    Abstracts away specific exchange implementations.
    """
    
    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to market data source"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to market data source"""
        pass
    
    @abstractmethod
    async def subscribe_to_symbol(self, symbol: str) -> None:
        """Subscribe to market data for a specific symbol"""
        pass
    
    @abstractmethod
    async def unsubscribe_from_symbol(self, symbol: str) -> None:
        """Unsubscribe from market data for a specific symbol"""
        pass
    
    @abstractmethod
    async def get_market_data_stream(self, symbol: str) -> AsyncIterator[MarketData]:
        """
        Get real-time market data stream for a symbol.
        Yields MarketData objects as they arrive.
        """
        pass
    
    @abstractmethod
    async def get_latest_price(self, symbol: str) -> Optional[MarketData]:
        """Get the latest price for a symbol"""
        pass
    
    @abstractmethod
    async def get_24h_volume(self, symbol: str) -> Optional[float]:
        """Get 24h volume for a symbol in USDT"""
        pass
    
    @abstractmethod
    async def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get symbol information (precision, limits, etc.)"""
        pass
    
    @abstractmethod
    async def is_symbol_active(self, symbol: str) -> bool:
        """Check if symbol is actively trading"""
        pass
    
    @abstractmethod
    def get_exchange_name(self) -> str:
        """Get the name of the exchange"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if connection is healthy"""
        pass


class IOrderBookProvider(ABC):
    """
    Interface for order book data providers.
    Separate from market data for performance reasons.
    """
    
    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to order book source"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to order book source"""
        pass
    
    @abstractmethod
    async def subscribe_to_orderbook(self, symbol: str, depth: int = 20) -> None:
        """Subscribe to order book updates for a symbol"""
        pass
    
    @abstractmethod
    async def unsubscribe_from_orderbook(self, symbol: str) -> None:
        """Unsubscribe from order book updates"""
        pass
    
    @abstractmethod
    async def get_orderbook_stream(self, symbol: str) -> AsyncIterator[OrderBook]:
        """
        Get real-time order book stream for a symbol.
        Yields OrderBook objects as they update.
        """
        pass
    
    @abstractmethod
    async def get_latest_orderbook(self, symbol: str) -> Optional[OrderBook]:
        """Get the latest order book snapshot"""
        pass
    
    @abstractmethod
    async def get_best_bid_ask(self, symbol: str) -> Optional[tuple[float, float]]:
        """Get best bid and ask prices"""
        pass
    
    @abstractmethod
    async def get_spread_percentage(self, symbol: str) -> Optional[float]:
        """Get current spread percentage"""
        pass
    
    @abstractmethod
    async def get_liquidity_usdt(self, symbol: str, levels: int = 5) -> Optional[float]:
        """Get total liquidity in USDT for top N levels"""
        pass


class IHistoricalDataProvider(ABC):
    """
    Interface for historical market data.
    Used for backtesting and technical analysis.
    """
    
    @abstractmethod
    async def get_historical_prices(
        self,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        interval: str = "1m"
    ) -> List[MarketData]:
        """Get historical price data for a time range"""
        pass
    
    @abstractmethod
    async def get_price_history(
        self,
        symbol: str,
        minutes: int = 60
    ) -> PriceHistory:
        """Get recent price history for technical analysis"""
        pass
    
    @abstractmethod
    async def get_volume_profile(
        self,
        symbol: str,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[float, float]:
        """Get volume profile (price -> volume mapping)"""
        pass
    
    @abstractmethod
    async def get_ohlcv_data(
        self,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        interval: str = "1m"
    ) -> List[Dict[str, Any]]:
        """Get OHLCV (Open, High, Low, Close, Volume) data"""
        pass


class IMarketDataCache(ABC):
    """
    Interface for market data caching.
    Improves performance and reduces API calls.
    """
    
    @abstractmethod
    async def cache_market_data(self, symbol: str, data: MarketData) -> None:
        """Cache market data for a symbol"""
        pass
    
    @abstractmethod
    async def get_cached_market_data(self, symbol: str, max_age_seconds: int = 60) -> Optional[MarketData]:
        """Get cached market data if not too old"""
        pass
    
    @abstractmethod
    async def cache_orderbook(self, symbol: str, orderbook: OrderBook) -> None:
        """Cache order book data"""
        pass
    
    @abstractmethod
    async def get_cached_orderbook(self, symbol: str, max_age_seconds: int = 10) -> Optional[OrderBook]:
        """Get cached order book if not too old"""
        pass
    
    @abstractmethod
    async def invalidate_cache(self, symbol: str) -> None:
        """Invalidate all cached data for a symbol"""
        pass
    
    @abstractmethod
    async def clear_cache(self) -> None:
        """Clear all cached data"""
        pass
    
    @abstractmethod
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        pass


class IMarketDataValidator(ABC):
    """
    Interface for market data validation.
    Ensures data quality and consistency.
    """
    
    @abstractmethod
    async def validate_market_data(self, data: MarketData) -> tuple[bool, Optional[str]]:
        """
        Validate market data.
        Returns (is_valid, error_message)
        """
        pass
    
    @abstractmethod
    async def validate_orderbook(self, orderbook: OrderBook) -> tuple[bool, Optional[str]]:
        """
        Validate order book data.
        Returns (is_valid, error_message)
        """
        pass
    
    @abstractmethod
    async def check_data_freshness(self, data: MarketData, max_age_seconds: int = 60) -> bool:
        """Check if data is fresh enough"""
        pass
    
    @abstractmethod
    async def detect_anomalies(self, data: MarketData, history: List[MarketData]) -> List[str]:
        """
        Detect anomalies in market data.
        Returns list of anomaly descriptions.
        """
        pass
    
    @abstractmethod
    async def sanitize_market_data(self, data: MarketData) -> MarketData:
        """Sanitize and normalize market data"""
        pass


class IMarketDataAggregator(ABC):
    """
    Interface for aggregating market data from multiple sources.
    Useful for cross-exchange arbitrage or data redundancy.
    """
    
    @abstractmethod
    async def add_provider(self, provider: IMarketDataProvider) -> None:
        """Add a market data provider to the aggregator"""
        pass
    
    @abstractmethod
    async def remove_provider(self, exchange_name: str) -> None:
        """Remove a provider by exchange name"""
        pass
    
    @abstractmethod
    async def get_aggregated_market_data(self, symbol: str) -> Optional[MarketData]:
        """Get aggregated market data from all providers"""
        pass
    
    @abstractmethod
    async def get_best_price(self, symbol: str, side: str) -> Optional[tuple[str, float]]:
        """
        Get best price across all exchanges.
        Returns (exchange_name, price)
        """
        pass
    
    @abstractmethod
    async def get_arbitrage_opportunities(self, symbol: str, min_profit_pct: float = 0.5) -> List[Dict[str, Any]]:
        """Find arbitrage opportunities across exchanges"""
        pass
    
    @abstractmethod
    async def get_provider_health(self) -> Dict[str, bool]:
        """Get health status of all providers"""
        pass