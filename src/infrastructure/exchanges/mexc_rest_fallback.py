"""
MEXC REST API Fallback Handler
==============================
Provides REST API fallback when WebSocket connections fail.
"""

import asyncio
import aiohttp
import time
from typing import Optional, Dict, List
from datetime import datetime
from decimal import Decimal

from ...core.logger import StructuredLogger
from ...domain.models.market_data import MarketData


class MexcRestFallback:
    """
    REST API fallback for MEXC when WebSocket connections fail.
    Provides essential market data through HTTP endpoints.
    """
    
    def __init__(self, logger: StructuredLogger):
        """
        Initialize REST API fallback handler.
        
        Args:
            logger: Structured logger instance
        """
        self.logger = logger
        self.base_url = "https://contract.mexc.com"
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Rate limiting for REST API
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms between requests
        
        # Circuit breaker for REST API
        self.consecutive_failures = 0
        self.max_failures = 5
        self.failure_timeout = 30.0
        self.last_failure_time = 0
        
        # Statistics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.start_time = time.time()
    
    async def start(self) -> None:
        """Initialize HTTP session"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=10, connect=5)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={"User-Agent": "MEXC-RestFallback/1.0"}
            )
            self.logger.info("mexc_rest_fallback.started")
    
    async def stop(self) -> None:
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None
            self.logger.info("mexc_rest_fallback.stopped")
    
    def _is_circuit_open(self) -> bool:
        """Check if circuit breaker is open"""
        if self.consecutive_failures >= self.max_failures:
            if time.time() - self.last_failure_time < self.failure_timeout:
                return True
            else:
                # Reset circuit breaker
                self.consecutive_failures = 0
        return False
    
    async def _rate_limit(self) -> None:
        """Apply rate limiting"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()
    
    async def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Make HTTP request with error handling and rate limiting.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            
        Returns:
            Response data or None if failed
        """
        if self._is_circuit_open():
            self.logger.warning("mexc_rest_fallback.circuit_open", {
                "consecutive_failures": self.consecutive_failures,
                "last_failure_time": self.last_failure_time
            })
            return None
        
        if not self.session:
            await self.start()
        
        await self._rate_limit()
        self.total_requests += 1
        
        try:
            url = f"{self.base_url}{endpoint}"
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    self.successful_requests += 1
                    self.consecutive_failures = 0
                    return data
                else:
                    self.logger.warning("mexc_rest_fallback.http_error", {
                        "status": response.status,
                        "endpoint": endpoint
                    })
                    self._record_failure()
                    return None
        
        except Exception as e:
            self.logger.error("mexc_rest_fallback.request_error", {
                "endpoint": endpoint,
                "error": str(e)
            })
            self._record_failure()
            return None
    
    def _record_failure(self) -> None:
        """Record request failure for circuit breaker"""
        self.failed_requests += 1
        self.consecutive_failures += 1
        self.last_failure_time = time.time()
    
    async def get_ticker(self, symbol: str) -> Optional[MarketData]:
        """
        Get ticker data for a symbol via REST API.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            MarketData object or None
        """
        data = await self._make_request("/api/v1/contract/ticker", {"symbol": symbol})
        
        if not data or "data" not in data:
            return None
        
        try:
            ticker = data["data"]
            price = float(ticker.get("lastPrice", 0))
            volume = float(ticker.get("volume24", 0))
            
            if price > 0:
                return MarketData(
                    symbol=symbol,
                    price=Decimal(str(price)),
                    volume=Decimal(str(volume)),
                    timestamp=datetime.now(),
                    exchange="mexc",
                    side="unknown"  # REST API doesn't provide trade side
                )
        
        except (ValueError, KeyError) as e:
            self.logger.error("mexc_rest_fallback.ticker_parse_error", {
                "symbol": symbol,
                "error": str(e)
            })
        
        return None
    
    async def get_multiple_tickers(self, symbols: List[str]) -> Dict[str, Optional[MarketData]]:
        """
        Get ticker data for multiple symbols.

        ✅ PERF FIX (2025-12-04): Use parallel fetching instead of sequential.
        This reduces 39 symbols from 69s to ~2-3s.

        Args:
            symbols: List of trading pair symbols

        Returns:
            Dictionary mapping symbol to MarketData
        """
        import asyncio

        async def safe_get_ticker(symbol: str) -> tuple:
            """Wrapper that returns (symbol, result) tuple"""
            try:
                result = await self.get_ticker(symbol)
                return (symbol, result)
            except Exception as e:
                self.logger.warning("mexc_rest.ticker_fetch_failed", {
                    "symbol": symbol,
                    "error": str(e)
                })
                return (symbol, None)

        # Fetch all tickers in parallel with concurrency limit
        # Using semaphore to prevent overwhelming the API (max 20 concurrent)
        semaphore = asyncio.Semaphore(20)

        async def rate_limited_fetch(symbol: str) -> tuple:
            async with semaphore:
                return await safe_get_ticker(symbol)

        # Execute all fetches in parallel
        tasks = [rate_limited_fetch(s) for s in symbols]
        results_list = await asyncio.gather(*tasks)

        # Convert to dictionary
        return {symbol: data for symbol, data in results_list}
    
    async def get_orderbook(self, symbol: str, limit: int = 10) -> Optional[Dict]:
        """
        Get orderbook data via REST API.
        
        Args:
            symbol: Trading pair symbol
            limit: Number of price levels
            
        Returns:
            Orderbook data or None
        """
        data = await self._make_request("/api/v1/contract/depth", {
            "symbol": symbol,
            "limit": limit
        })
        
        if not data or "data" not in data:
            return None
        
        try:
            orderbook = data["data"]
            bids = [[float(p), float(v)] for p, v in orderbook.get("bids", [])]
            asks = [[float(p), float(v)] for p, v in orderbook.get("asks", [])]
            
            return {
                "symbol": symbol,
                "bids": bids,
                "asks": asks,
                "best_bid": bids[0][0] if bids else 0,
                "best_ask": asks[0][0] if asks else 0,
                "timestamp": time.time(),
                "source": "rest_fallback"
            }
        
        except (ValueError, KeyError) as e:
            self.logger.error("mexc_rest_fallback.orderbook_parse_error", {
                "symbol": symbol,
                "error": str(e)
            })
        
        return None
    
    def get_stats(self) -> Dict:
        """Get REST fallback statistics"""
        uptime = time.time() - self.start_time
        success_rate = (self.successful_requests / max(self.total_requests, 1)) * 100
        
        return {
            "name": "mexc_rest_fallback",
            "type": "http_fallback",
            "state": {
                "session_active": self.session is not None,
                "circuit_open": self._is_circuit_open(),
                "consecutive_failures": self.consecutive_failures
            },
            "statistics": {
                "total_requests": self.total_requests,
                "successful_requests": self.successful_requests,
                "failed_requests": self.failed_requests,
                "success_rate_pct": success_rate,
                "uptime_seconds": uptime,
                "requests_per_second": self.total_requests / max(uptime, 1)
            },
            "rate_limiting": {
                "min_request_interval": self.min_request_interval,
                "last_request_time": self.last_request_time
            }
        }
