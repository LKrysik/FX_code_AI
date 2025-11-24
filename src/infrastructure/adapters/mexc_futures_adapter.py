"""
✅ FUTURES ONLY - Standalone implementation (Phase 2)
=====================================================
MEXC Futures Adapter - Futures API Integration for SHORT Selling (TIER 2.2 Enhanced)

Standalone implementation - NO inheritance from MexcSpotAdapter.
All infrastructure methods are self-contained.

Key differences from SPOT API:
- Base URL: https://contract.mexc.com (not api.mexc.com)
- Endpoints: /fapi/v1/* (not /api/v3/*)
- Position management: LONG/SHORT positions with leverage
- Funding rates: Applied every 8 hours
- Margin types: ISOLATED or CROSS

Circuit Breaker Integration (TIER 2.2):
- Automatic retry with exponential backoff (3 attempts, 1s → 2s → 4s)
- Circuit breaker protection (opens after 5 consecutive failures, 60s recovery)
- Fallback strategies for non-critical operations
- Graceful degradation when API is temporarily unavailable

Usage:
    async with MexcFuturesAdapter(api_key, api_secret, logger) as adapter:
        # Set leverage before opening position
        await adapter.set_leverage("BTC_USDT", 3)

        # Open SHORT position (protected by circuit breaker)
        order = await adapter.place_futures_order(
            symbol="BTC_USDT",
            side="SELL",
            position_side="SHORT",
            order_type="MARKET",
            quantity=0.001
        )

        # Get funding rate (with fallback on failure)
        funding = await adapter.get_funding_rate("BTC_USDT")

        # Monitor circuit breaker status
        status = adapter.get_circuit_breaker_metrics()
"""

import asyncio
import time
import hmac
import hashlib
import json
import aiohttp
from typing import Dict, Any, Optional, List, Literal
from datetime import datetime
from urllib.parse import urlencode

from ...core.logger import StructuredLogger
from ...core.circuit_breaker import ResilientService


class MexcFuturesAdapter:
    """
    MEXC Futures API adapter for margin trading and SHORT selling.

    ✅ FUTURES ONLY - Standalone implementation (Phase 2)

    Adds futures-specific functionality:
    - Position management (LONG/SHORT)
    - Leverage configuration
    - Funding rate queries
    - Margin type management (ISOLATED/CROSS)
    """

    def __init__(self,
                 api_key: str,
                 api_secret: str,
                 logger: StructuredLogger,
                 base_url: str = "https://contract.mexc.com",
                 timeout: int = 30):
        """
        Initialize MEXC Futures adapter.

        Args:
            api_key: MEXC API key
            api_secret: MEXC API secret
            logger: Structured logger
            base_url: Futures API base URL (default: https://contract.mexc.com)
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.logger = logger
        self.base_url = base_url
        self.timeout = aiohttp.ClientTimeout(total=timeout)

        # HTTP session (initialized on first use)
        self.session: Optional[aiohttp.ClientSession] = None

        # Rate limiter (MEXC futures: 100 requests per second per IP)
        self.rate_limiter = {
            "requests_per_second": 100,
            "request_count": 0,
            "last_request_time": time.time()
        }

        # Circuit breaker for resilience
        self.resilient_service = ResilientService(
            failure_threshold=5,
            recovery_timeout=60,
            logger=logger
        )

        # Track leverage settings per symbol
        self._leverage_cache: Dict[str, int] = {}

        self.logger.info("mexc_futures_adapter.initialized", {
            "base_url": self.base_url,
            "rate_limit": self.rate_limiter["requests_per_second"]
        })

    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self._close_session()

    async def _ensure_session(self):
        """Ensure HTTP session is available"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=self.timeout)

    async def _close_session(self):
        """Close HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()

    def _generate_signature(self, params: Dict[str, Any], timestamp: int) -> str:
        """Generate HMAC-SHA256 signature for MEXC API authentication"""
        # Add timestamp to params
        params_with_timestamp = params.copy()
        params_with_timestamp['timestamp'] = timestamp

        # Create query string
        query_string = urlencode(params_with_timestamp)

        # Generate signature
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        return signature

    async def _make_request(self,
                            method: str,
                            endpoint: str,
                            params: Optional[Dict[str, Any]] = None,
                            signed: bool = False) -> Dict[str, Any]:
        """Make HTTP request to MEXC API with resilience patterns"""
        await self._ensure_session()

        # Rate limiting (still handled here as it's specific to MEXC API limits)
        current_time = time.time()
        if current_time - self.rate_limiter["last_request_time"] >= 1.0:
            self.rate_limiter["request_count"] = 0
            self.rate_limiter["last_request_time"] = current_time

        if self.rate_limiter["request_count"] >= self.rate_limiter["requests_per_second"]:
            wait_time = 1.0 - (current_time - self.rate_limiter["last_request_time"])
            if wait_time > 0:
                await asyncio.sleep(wait_time)

        self.rate_limiter["request_count"] += 1

        # Prepare request
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "MEXC-TradingBot/1.0"
        }

        request_params = params or {}

        if signed:
            timestamp = int(time.time() * 1000)
            signature = self._generate_signature(request_params, timestamp)
            request_params['signature'] = signature
            headers['X-MEXC-APIKEY'] = self.api_key

        # Create the actual HTTP request function
        async def make_http_request():
            if method.upper() == "GET":
                async with self.session.get(url, params=request_params, headers=headers) as response:
                    return await self._handle_response(response)
            elif method.upper() == "POST":
                async with self.session.post(url, json=request_params, headers=headers) as response:
                    return await self._handle_response(response)
            elif method.upper() == "DELETE":
                async with self.session.delete(url, params=request_params, headers=headers) as response:
                    return await self._handle_response(response)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

        # Use resilient service for the actual request
        return await self.resilient_service.call_async(make_http_request)

    async def _handle_response(self, response: aiohttp.ClientResponse) -> Dict[str, Any]:
        """Handle API response with error checking"""
        response_text = await response.text()

        try:
            data = json.loads(response_text) if response_text else {}
        except json.JSONDecodeError:
            data = {"error": "Invalid JSON response", "raw_response": response_text}

        if response.status >= 400:
            error_msg = data.get("msg", f"HTTP {response.status}: {response_text}")
            # Log the error (circuit breaker handling is now in resilient service)
            self.logger.error("mexc_futures_adapter.api_error", {
                "status": response.status,
                "error": error_msg,
                "endpoint": response.url.path if hasattr(response, 'url') else 'unknown'
            })
            raise Exception(f"MEXC API Error: {error_msg}")

        return data

    def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """Get circuit breaker status for monitoring"""
        return self.resilient_service.get_status()

    # ============================================================================
    # FUTURES-SPECIFIC METHODS
    # ============================================================================

    async def set_leverage(self,
                          symbol: str,
                          leverage: int,
                          margin_type: Literal["ISOLATED", "CROSS"] = "ISOLATED") -> Dict[str, Any]:
        """
        Set leverage for a symbol.

        IMPORTANT: Must be called BEFORE opening a position!

        Args:
            symbol: Trading symbol (e.g., 'BTC_USDT')
            leverage: Leverage multiplier (1-10, enforced for safety)
            margin_type: Margin type (ISOLATED or CROSS)

        Returns:
            Response with leverage confirmation

        Raises:
            ValueError: If leverage is outside safe range (1-10)

        Example:
            await adapter.set_leverage("BTC_USDT", 3, "ISOLATED")

        Note (TIER 3.1):
            While MEXC API allows up to 200x leverage, this adapter enforces
            a maximum of 10x for safety. Leverage >10x has extreme liquidation
            risk and is not recommended for algorithmic trading.
        """
        # TIER 3.1: Enforce safe leverage limits (1-10) instead of MEXC API max (1-200)
        if leverage < 1 or leverage > 10:
            raise ValueError(f"Leverage must be between 1 and 10 for safety, got {leverage}. "
                           f"Leverage >10x has extreme liquidation risk (<10% price movement).")

        params = {
            "symbol": symbol.upper(),
            "leverage": int(leverage)
        }

        try:
            self.logger.info("mexc_futures_adapter.set_leverage", {
                "symbol": symbol,
                "leverage": leverage,
                "margin_type": margin_type
            })

            # Set leverage via futures API
            response = await self._make_request("POST", "/fapi/v1/leverage", params, signed=True)

            # Cache leverage setting
            self._leverage_cache[symbol.upper()] = leverage

            return {
                "success": True,
                "symbol": symbol,
                "leverage": leverage,
                "margin_type": margin_type,
                "response": response
            }

        except Exception as e:
            self.logger.error("mexc_futures_adapter.set_leverage_error", {
                "symbol": symbol,
                "leverage": leverage,
                "error": str(e)
            })
            raise

    async def get_leverage(self, symbol: str) -> int:
        """
        Get current leverage for symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Current leverage (from cache or API)
        """
        symbol_upper = symbol.upper()

        # Check cache first
        if symbol_upper in self._leverage_cache:
            return self._leverage_cache[symbol_upper]

        # Query from API
        try:
            position = await self.get_position(symbol)
            if position and "leverage" in position:
                leverage = int(position["leverage"])
                self._leverage_cache[symbol_upper] = leverage
                return leverage
        except Exception as e:
            self.logger.warning("mexc_futures_adapter.get_leverage_fallback", {
                "symbol": symbol,
                "error": str(e)
            })

        # Default to 1x if unknown
        return 1

    async def get_leverage_with_fallback(self, symbol: str, default_leverage: int = 1) -> int:
        """
        Get leverage with fallback to default if circuit breaker is open or API fails.

        This is a graceful degradation pattern - returns cached or default value
        when API is unavailable instead of raising exception.

        Args:
            symbol: Trading symbol
            default_leverage: Default leverage to return on failure (default: 1)

        Returns:
            Leverage value (from API, cache, or default)

        Example:
            >>> leverage = await adapter.get_leverage_with_fallback("BTC_USDT", default_leverage=3)
            >>> # Always returns a value, never throws exception
        """
        symbol_upper = symbol.upper()

        # First try cache
        if symbol_upper in self._leverage_cache:
            self.logger.debug("mexc_futures_adapter.leverage_from_cache", {
                "symbol": symbol,
                "leverage": self._leverage_cache[symbol_upper]
            })
            return self._leverage_cache[symbol_upper]

        # Try API if circuit breaker is healthy
        if self.is_circuit_breaker_healthy():
            try:
                return await self.get_leverage(symbol)
            except Exception as e:
                self.logger.warning("mexc_futures_adapter.leverage_fallback_to_default", {
                    "symbol": symbol,
                    "error": str(e),
                    "default_leverage": default_leverage
                })
        else:
            self.logger.warning("mexc_futures_adapter.leverage_circuit_breaker_open", {
                "symbol": symbol,
                "default_leverage": default_leverage,
                "circuit_breaker_state": self.get_circuit_breaker_state()
            })

        # Fallback to default
        return default_leverage

    async def place_futures_order(self,
                                  symbol: str,
                                  side: Literal["BUY", "SELL"],
                                  position_side: Literal["LONG", "SHORT"],
                                  order_type: Literal["MARKET", "LIMIT"],
                                  quantity: float,
                                  price: Optional[float] = None,
                                  time_in_force: str = "GTC",
                                  reduce_only: bool = False) -> Dict[str, Any]:
        """
        Place a futures order (supports SHORT selling).

        Args:
            symbol: Trading symbol (e.g., 'BTC_USDT')
            side: Order side (BUY or SELL)
            position_side: Position side (LONG or SHORT)
                - LONG + BUY = Open long position
                - SHORT + SELL = Open short position
                - LONG + SELL = Close long position
                - SHORT + BUY = Close short position (cover)
            order_type: MARKET or LIMIT
            quantity: Order quantity (in base currency)
            price: Limit price (required for LIMIT orders)
            time_in_force: Time in force (GTC, IOC, FOK)
            reduce_only: Only reduce position (don't increase)

        Returns:
            Order response with order_id, status, etc.

        Raises:
            Exception: If order placement fails

        Example (Open SHORT):
            order = await adapter.place_futures_order(
                symbol="BTC_USDT",
                side="SELL",
                position_side="SHORT",
                order_type="MARKET",
                quantity=0.001
            )

        Example (Close SHORT - Cover):
            order = await adapter.place_futures_order(
                symbol="BTC_USDT",
                side="BUY",
                position_side="SHORT",
                order_type="MARKET",
                quantity=0.001,
                reduce_only=True
            )
        """
        params = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "positionSide": position_side.upper(),
            "type": order_type.upper(),
            "quantity": str(quantity)
        }

        if order_type.upper() == "LIMIT":
            if price is None:
                raise ValueError("Price required for LIMIT orders")
            params["price"] = str(price)
            params["timeInForce"] = time_in_force

        if reduce_only:
            params["reduceOnly"] = "true"

        try:
            self.logger.info("mexc_futures_adapter.place_order", {
                "symbol": symbol,
                "side": side,
                "position_side": position_side,
                "order_type": order_type,
                "quantity": quantity,
                "price": price
            })

            # Use futures order endpoint
            response = await self._make_request("POST", "/fapi/v1/order", params, signed=True)

            result = {
                "order_id": response.get("orderId"),
                "status": response.get("status"),
                "symbol": response.get("symbol"),
                "side": response.get("side"),
                "position_side": response.get("positionSide"),
                "type": response.get("type"),
                "quantity": float(response.get("origQty", 0)),
                "price": float(response.get("price", 0)),
                "avg_price": float(response.get("avgPrice", 0)),
                "source": "mexc_futures_api",
                "timestamp": datetime.utcnow().isoformat()
            }

            self.logger.info("mexc_futures_adapter.order_placed", result)
            return result

        except Exception as e:
            self.logger.error("mexc_futures_adapter.place_order_error", {
                "symbol": symbol,
                "side": side,
                "position_side": position_side,
                "error": str(e)
            })
            raise

    async def close_position(self,
                            symbol: str,
                            position_side: Literal["LONG", "SHORT"],
                            order_type: Literal["MARKET", "LIMIT"] = "MARKET",
                            price: Optional[float] = None) -> Dict[str, Any]:
        """
        Close an entire position.

        Args:
            symbol: Trading symbol
            position_side: Position to close (LONG or SHORT)
            order_type: MARKET or LIMIT
            price: Limit price (for LIMIT orders)

        Returns:
            Order response

        Example (Close SHORT position):
            order = await adapter.close_position("BTC_USDT", "SHORT", "MARKET")
        """
        # Get current position to determine quantity
        position = await self.get_position(symbol)

        if not position or position["position_side"] != position_side:
            raise ValueError(f"No {position_side} position found for {symbol}")

        quantity = abs(position["position_amount"])

        # Determine order side (opposite of position)
        # To close SHORT: BUY
        # To close LONG: SELL
        side = "BUY" if position_side == "SHORT" else "SELL"

        return await self.place_futures_order(
            symbol=symbol,
            side=side,
            position_side=position_side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            reduce_only=True
        )

    async def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get current position for symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Position info or None if no position

        Example response:
            {
                "symbol": "BTC_USDT",
                "position_side": "SHORT",
                "position_amount": -0.001,  # Negative = SHORT
                "entry_price": 50000.0,
                "leverage": 3,
                "liquidation_price": 66666.67,
                "unrealized_pnl": 50.0,
                "margin_type": "ISOLATED"
            }
        """
        params = {"symbol": symbol.upper()}

        try:
            response = await self._make_request("GET", "/fapi/v1/positionRisk", params, signed=True)

            # MEXC returns array of positions (for both LONG and SHORT)
            for position in response:
                pos_amt = float(position.get("positionAmt", 0))
                if pos_amt != 0:  # Active position
                    return {
                        "symbol": position.get("symbol"),
                        "position_side": position.get("positionSide"),
                        "position_amount": pos_amt,
                        "entry_price": float(position.get("entryPrice", 0)),
                        "leverage": int(position.get("leverage", 1)),
                        "liquidation_price": float(position.get("liquidationPrice", 0)),
                        "unrealized_pnl": float(position.get("unRealizedProfit", 0)),
                        "margin_type": position.get("marginType", "ISOLATED"),
                        "source": "mexc_futures_api"
                    }

            return None  # No active position

        except Exception as e:
            self.logger.error("mexc_futures_adapter.get_position_error", {
                "symbol": symbol,
                "error": str(e)
            })
            raise

    async def get_funding_rate(self, symbol: str) -> Dict[str, Any]:
        """
        Get current and next funding rate for symbol.

        Funding rates are applied every 8 hours in futures markets.
        - Positive rate: LONG pays SHORT
        - Negative rate: SHORT pays LONG

        Args:
            symbol: Trading symbol

        Returns:
            Funding rate info

        Example response:
            {
                "symbol": "BTC_USDT",
                "funding_rate": 0.0001,  # 0.01%
                "funding_time": "2025-11-04T16:00:00",
                "next_funding_time": "2025-11-05T00:00:00"
            }
        """
        params = {"symbol": symbol.upper()}

        try:
            response = await self._make_request("GET", "/fapi/v1/fundingRate", params, signed=False)

            if isinstance(response, list) and len(response) > 0:
                latest = response[0]
                return {
                    "symbol": latest.get("symbol"),
                    "funding_rate": float(latest.get("fundingRate", 0)),
                    "funding_time": datetime.fromtimestamp(
                        int(latest.get("fundingTime", 0)) / 1000
                    ).isoformat(),
                    "mark_price": float(latest.get("markPrice", 0)),
                    "source": "mexc_futures_api"
                }
            else:
                # Fallback if no data
                return {
                    "symbol": symbol,
                    "funding_rate": 0.0,
                    "funding_time": None,
                    "mark_price": 0.0,
                    "source": "mexc_futures_api"
                }

        except Exception as e:
            self.logger.error("mexc_futures_adapter.get_funding_rate_error", {
                "symbol": symbol,
                "error": str(e)
            })
            raise

    async def get_funding_rate_with_fallback(self, symbol: str) -> Dict[str, Any]:
        """
        Get funding rate with fallback to zero if circuit breaker is open or API fails.

        Non-critical operation - funding rate is informational and can be approximated.

        Args:
            symbol: Trading symbol

        Returns:
            Funding rate info (real or fallback)

        Example:
            >>> funding = await adapter.get_funding_rate_with_fallback("BTC_USDT")
            >>> # Always returns data, even if API is down
        """
        if not self.is_circuit_breaker_healthy():
            self.logger.warning("mexc_futures_adapter.funding_rate_circuit_breaker_open", {
                "symbol": symbol,
                "circuit_breaker_state": self.get_circuit_breaker_state()
            })
            return {
                "symbol": symbol,
                "funding_rate": 0.0,
                "funding_time": None,
                "mark_price": 0.0,
                "source": "fallback_circuit_breaker_open"
            }

        try:
            return await self.get_funding_rate(symbol)
        except Exception as e:
            self.logger.warning("mexc_futures_adapter.funding_rate_fallback", {
                "symbol": symbol,
                "error": str(e)
            })
            return {
                "symbol": symbol,
                "funding_rate": 0.0,
                "funding_time": None,
                "mark_price": 0.0,
                "source": "fallback_exception"
            }

    async def calculate_funding_cost(self,
                                     symbol: str,
                                     position_amount: float,
                                     holding_hours: float) -> float:
        """
        Calculate expected funding cost for a position.

        Args:
            symbol: Trading symbol
            position_amount: Position size (positive = LONG, negative = SHORT)
            holding_hours: Expected holding period in hours

        Returns:
            Expected funding cost (negative = you pay, positive = you earn)

        Example:
            # SHORT 0.001 BTC @ $50,000 for 24 hours
            cost = await adapter.calculate_funding_cost("BTC_USDT", -0.001, 24)
            # Returns: -0.15 USDT (you pay $0.15)
        """
        try:
            funding_info = await self.get_funding_rate(symbol)
            funding_rate = funding_info["funding_rate"]
            mark_price = funding_info.get("mark_price", 0)

            # Funding is applied every 8 hours
            funding_intervals = holding_hours / 8

            # Notional value
            notional_value = abs(position_amount) * mark_price

            # For SHORT positions (negative amount), we PAY if funding is positive
            # For LONG positions (positive amount), we PAY if funding is negative
            total_funding = position_amount * mark_price * funding_rate * funding_intervals

            return -total_funding  # Negative = cost, positive = earning

        except Exception as e:
            self.logger.warning("mexc_futures_adapter.calculate_funding_cost_error", {
                "symbol": symbol,
                "error": str(e)
            })
            return 0.0  # Return 0 if calculation fails

    # ============================================================================
    # Circuit Breaker Management Methods (TIER 2.2)
    # ============================================================================

    def get_circuit_breaker_metrics(self) -> Dict[str, Any]:
        """
        Get detailed circuit breaker metrics for monitoring and observability.

        Returns comprehensive status including:
        - Current state (CLOSED, OPEN, HALF_OPEN)
        - Success/failure rates
        - Request counts
        - Last failure/success timestamps
        - Configuration settings

        Returns:
            Dict with circuit breaker metrics and status

        Example:
            >>> metrics = adapter.get_circuit_breaker_metrics()
            >>> print(f"State: {metrics['circuit_breaker']['state']}")
            >>> print(f"Success rate: {metrics['circuit_breaker']['metrics']['success_rate_percent']}%")
            >>> print(f"Total requests: {metrics['circuit_breaker']['metrics']['total_requests']}")
        """
        return self.get_circuit_breaker_status()

    def is_circuit_breaker_healthy(self) -> bool:
        """
        Check if circuit breaker is in healthy state (CLOSED or recovering).

        Returns:
            True if CLOSED or HALF_OPEN, False if OPEN

        Example:
            >>> if not adapter.is_circuit_breaker_healthy():
            >>>     logger.warning("Circuit breaker is OPEN - degraded service")
            >>>     # Use fallback strategies or skip non-critical operations
        """
        try:
            status = self.get_circuit_breaker_metrics()
            state = status.get('circuit_breaker', {}).get('state', 'unknown')
            return state in ['closed', 'half_open']
        except Exception:
            return False

    def get_circuit_breaker_state(self) -> str:
        """
        Get current circuit breaker state (CLOSED, OPEN, or HALF_OPEN).

        Returns:
            State string: 'closed', 'open', 'half_open', or 'unknown'
        """
        try:
            status = self.get_circuit_breaker_metrics()
            return status.get('circuit_breaker', {}).get('state', 'unknown')
        except Exception:
            return 'unknown'

    def log_circuit_breaker_status(self):
        """
        Log current circuit breaker status for debugging/monitoring.

        Useful for periodic health checks or troubleshooting.

        Example:
            >>> adapter.log_circuit_breaker_status()
            >>> # Logs detailed circuit breaker metrics
        """
        try:
            metrics = self.get_circuit_breaker_metrics()
            cb_metrics = metrics.get('circuit_breaker', {}).get('metrics', {})

            self.logger.info("mexc_futures_adapter.circuit_breaker_status", {
                "state": metrics.get('circuit_breaker', {}).get('state', 'unknown'),
                "success_rate_percent": cb_metrics.get('success_rate_percent', 0),
                "total_requests": cb_metrics.get('total_requests', 0),
                "failed_requests": cb_metrics.get('failed_requests', 0),
                "rejected_requests": cb_metrics.get('rejected_requests', 0),
                "consecutive_failures": cb_metrics.get('consecutive_failures', 0),
                "state_changes": cb_metrics.get('state_changes', 0)
            })
        except Exception as e:
            self.logger.error("mexc_futures_adapter.circuit_breaker_status_error", {
                "error": str(e)
            })

    # ============================================================================
    # DEPRECATED METHOD - PREVENT SPOT API USAGE
    # ============================================================================

    async def place_order(self, *args, **kwargs):
        """
        DEPRECATED: Use place_futures_order() instead.

        This method is for SPOT trading only and won't work for SHORT positions.
        """
        self.logger.warning("mexc_futures_adapter.deprecated_method", {
            "message": "place_order() is for SPOT trading. Use place_futures_order() for futures/SHORT."
        })
        raise NotImplementedError(
            "For futures trading, use place_futures_order() instead of place_order(). "
            "Futures API requires positionSide parameter which SPOT API doesn't support."
        )
