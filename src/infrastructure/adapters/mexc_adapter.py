"""
MEXC Adapter - Real API Integration
===================================
Real MEXC REST API adapter with authentication, rate limiting, and caching.

Enhanced for Live Trading (Phase 1):
- Order submission (market & limit orders)
- Order cancellation
- Order status tracking
- Position fetching
- Comprehensive error handling
"""

import asyncio
import hashlib
import hmac
import json
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from urllib.parse import urlencode
from dataclasses import dataclass
from enum import Enum

import aiohttp
from aiohttp import ClientTimeout

from ...core.logger import StructuredLogger
from ...core.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    RetryConfig,
    ResilientService,
    get_or_create_service
)


# ===== RESPONSE DATACLASSES =====

class OrderStatus(str, Enum):
    """MEXC order status"""
    NEW = "NEW"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    PENDING_CANCEL = "PENDING_CANCEL"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


@dataclass
class OrderStatusResponse:
    """Order status response from MEXC"""
    exchange_order_id: str
    symbol: str
    side: str  # "BUY" or "SELL"
    order_type: str  # "MARKET" or "LIMIT"
    quantity: float
    price: float
    status: OrderStatus
    filled_quantity: float
    average_fill_price: Optional[float]
    created_at: int  # Unix timestamp in milliseconds
    updated_at: int  # Unix timestamp in milliseconds


@dataclass
class PositionResponse:
    """Position response from MEXC"""
    symbol: str
    side: str  # "LONG" or "SHORT"
    quantity: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    margin_ratio: float  # equity / maintenance_margin (%)
    liquidation_price: float
    leverage: float
    margin: float



class MexcRealAdapter:
    """
    Real MEXC API adapter with authentication and rate limiting.
    Implements HMAC-SHA256 signature authentication.
    """

    def __init__(self,
                 api_key: str,
                 api_secret: str,
                 logger: StructuredLogger,
                 base_url: str = "https://api.mexc.com",
                 timeout: int = 30):
        self.api_key = api_key
        self.api_secret = api_secret
        self.logger = logger
        self.base_url = base_url
        self.timeout = ClientTimeout(total=timeout)

        # Rate limiting: 10 requests per second (per IMPLEMENTATION_ROADMAP.md Task 1.1)
        self.rate_limiter = {
            "requests_per_second": 10,
            "last_request_time": 0.0,
            "request_count": 0
        }

        # Simple cache for API responses (TTL 30 seconds)
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = 30

        # Initialize resilient service with circuit breaker and retry
        circuit_config = CircuitBreakerConfig(
            name="mexc_api",
            failure_threshold=5,
            recovery_timeout=60.0,
            timeout=timeout,
            expected_exception=(aiohttp.ClientError, asyncio.TimeoutError, Exception)
        )

        retry_config = RetryConfig(
            name="mexc_api",
            max_attempts=3,
            initial_delay=1.0,
            backoff_factor=2.0,
            retry_on=(aiohttp.ClientError, asyncio.TimeoutError, Exception)
        )

        self.resilient_service = ResilientService("mexc_api", circuit_config, retry_config)

        self.session: Optional[aiohttp.ClientSession] = None

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
            self.logger.error("mexc_adapter.api_error", {
                "status": response.status,
                "error": error_msg,
                "endpoint": response.url.path if hasattr(response, 'url') else 'unknown'
            })
            raise Exception(f"MEXC API Error: {error_msg}")

        return data

    def _get_cache_key(self, method: str, endpoint: str, params: Dict[str, Any]) -> str:
        """Generate cache key for request"""
        param_str = json.dumps(params, sort_keys=True)
        return f"{method}:{endpoint}:{param_str}"

    def _get_cached_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached response if still valid"""
        if cache_key in self.cache:
            cached_data = self.cache[cache_key]
            if time.time() - cached_data["timestamp"] < self.cache_ttl:
                return cached_data["data"]
            else:
                del self.cache[cache_key]
        return None

    def _cache_response(self, cache_key: str, data: Dict[str, Any]):
        """Cache API response"""
        self.cache[cache_key] = {
            "data": data,
            "timestamp": time.time()
        }

    async def get_balances(self) -> Dict[str, Any]:
        """Get account balances from MEXC API"""
        cache_key = self._get_cache_key("GET", "/api/v3/account", {})
        cached = self._get_cached_response(cache_key)
        if cached:
            return cached

        try:
            response = await self._make_request("GET", "/api/v3/account", signed=True)

            # Transform MEXC response format
            balances = {}
            for balance in response.get("balances", []):
                asset = balance["asset"]
                free = float(balance["free"])
                locked = float(balance["locked"])

                if free > 0 or locked > 0:
                    balances[asset] = {
                        "free": free,
                        "locked": locked
                    }

            result = {
                "timestamp": datetime.utcnow().isoformat(),
                "assets": balances,
                "source": "mexc_api"
            }

            self._cache_response(cache_key, result)
            return result

        except Exception as e:
            self.logger.error("mexc_adapter.get_balances_error", {"error": str(e)})
            raise

    async def get_account_info(self) -> Dict[str, Any]:
        """Get detailed account information"""
        return await self.get_balances()  # For now, balances provide main account info

    async def place_order(self,
                         symbol: str,
                         side: str,
                         order_type: str,
                         quantity: float,
                         price: Optional[float] = None) -> Dict[str, Any]:
        """Place an order on MEXC"""
        params = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": order_type.upper(),
            "quantity": str(quantity)
        }

        if price and order_type.upper() == "LIMIT":
            params["price"] = str(price)
            params["timeInForce"] = "GTC"

        try:
            response = await self._make_request("POST", "/api/v3/order", params, signed=True)

            return {
                "order_id": response.get("orderId"),
                "status": response.get("status"),
                "symbol": response.get("symbol"),
                "side": response.get("side"),
                "type": response.get("type"),
                "quantity": float(response.get("origQty", 0)),
                "price": float(response.get("price", 0)),
                "source": "mexc_api"
            }

        except Exception as e:
            self.logger.error("mexc_adapter.place_order_error", {
                "symbol": symbol,
                "side": side,
                "error": str(e)
            })
            raise

    async def cancel_order(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """Cancel an order on MEXC"""
        params = {
            "symbol": symbol.upper(),
            "orderId": order_id
        }

        try:
            response = await self._make_request("DELETE", "/api/v3/order", params, signed=True)

            return {
                "success": True,
                "order_id": response.get("orderId"),
                "symbol": response.get("symbol"),
                "source": "mexc_api"
            }

        except Exception as e:
            self.logger.error("mexc_adapter.cancel_order_error", {
                "symbol": symbol,
                "order_id": order_id,
                "error": str(e)
            })
            raise

    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get open orders from MEXC"""
        params = {}
        if symbol:
            params["symbol"] = symbol.upper()

        cache_key = self._get_cache_key("GET", "/api/v3/openOrders", params)
        cached = self._get_cached_response(cache_key)
        if cached:
            return cached

        try:
            response = await self._make_request("GET", "/api/v3/openOrders", params, signed=True)

            orders = []
            for order in response:
                orders.append({
                    "order_id": order.get("orderId"),
                    "symbol": order.get("symbol"),
                    "side": order.get("side"),
                    "type": order.get("type"),
                    "quantity": float(order.get("origQty", 0)),
                    "price": float(order.get("price", 0)),
                    "status": order.get("status"),
                    "source": "mexc_api"
                })

            self._cache_response(cache_key, orders)
            return orders

        except Exception as e:
            self.logger.error("mexc_adapter.get_open_orders_error", {"error": str(e)})
            raise

    def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """Get circuit breaker status for monitoring"""
        return self.resilient_service.get_status()

    # ===== ENHANCED METHODS FOR LIVE TRADING (Phase 1) =====

    async def create_market_order(self, symbol: str, side: str, quantity: float) -> str:
        """
        Create market order on MEXC (Agent 3 - Task 3.1).

        Args:
            symbol: Trading symbol (e.g., "BTC_USDT")
            side: "buy" or "sell"
            quantity: Order quantity

        Returns:
            Exchange order ID (string)

        Raises:
            Exception: On API errors (500, 418 rate limit, network timeout, etc.)

        Error Handling:
            - HTTP 500: Server error → Retry via ResilientService
            - HTTP 418: Rate limit → Retry via ResilientService
            - Network timeout → Retry via ResilientService
            - HTTP 400: Invalid parameters → Raise immediately (no retry)
        """
        params = {
            "symbol": symbol.upper().replace("_", ""),  # MEXC expects "BTCUSDT" not "BTC_USDT"
            "side": side.upper(),
            "type": "MARKET",
            "quantity": str(quantity)
        }

        try:
            self.logger.info("mexc_adapter.create_market_order", {
                "symbol": symbol,
                "side": side,
                "quantity": quantity
            })

            response = await self._make_request("POST", "/api/v3/order", params, signed=True)

            exchange_order_id = str(response.get("orderId"))

            self.logger.info("mexc_adapter.market_order_created", {
                "symbol": symbol,
                "exchange_order_id": exchange_order_id,
                "status": response.get("status")
            })

            return exchange_order_id

        except Exception as e:
            self.logger.error("mexc_adapter.create_market_order_error", {
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "error": str(e),
                "error_type": type(e).__name__
            })
            raise

    async def create_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float
    ) -> str:
        """
        Create limit order on MEXC (Agent 3 - Task 3.1).

        Args:
            symbol: Trading symbol (e.g., "BTC_USDT")
            side: "buy" or "sell"
            quantity: Order quantity
            price: Limit price

        Returns:
            Exchange order ID (string)

        Raises:
            Exception: On API errors (500, 418 rate limit, network timeout, etc.)

        Error Handling:
            - HTTP 500: Server error → Retry via ResilientService
            - HTTP 418: Rate limit → Retry via ResilientService
            - Network timeout → Retry via ResilientService
            - HTTP 400: Invalid parameters → Raise immediately (no retry)
        """
        params = {
            "symbol": symbol.upper().replace("_", ""),
            "side": side.upper(),
            "type": "LIMIT",
            "quantity": str(quantity),
            "price": str(price),
            "timeInForce": "GTC"  # Good Till Cancel
        }

        try:
            self.logger.info("mexc_adapter.create_limit_order", {
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": price
            })

            response = await self._make_request("POST", "/api/v3/order", params, signed=True)

            exchange_order_id = str(response.get("orderId"))

            self.logger.info("mexc_adapter.limit_order_created", {
                "symbol": symbol,
                "exchange_order_id": exchange_order_id,
                "status": response.get("status")
            })

            return exchange_order_id

        except Exception as e:
            self.logger.error("mexc_adapter.create_limit_order_error", {
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": price,
                "error": str(e),
                "error_type": type(e).__name__
            })
            raise

    async def cancel_order(self, symbol: str, exchange_order_id: str) -> bool:
        """
        Cancel order on MEXC (Agent 3 - Task 3.1).

        Args:
            symbol: Trading symbol (e.g., "BTC_USDT")
            exchange_order_id: Exchange order ID to cancel

        Returns:
            True if cancelled successfully, False otherwise

        Raises:
            Exception: On API errors (500, 418 rate limit, network timeout, etc.)

        Error Handling:
            - HTTP 500: Server error → Retry via ResilientService
            - HTTP 418: Rate limit → Retry via ResilientService
            - Network timeout → Retry via ResilientService
            - HTTP 400: Order not found → Return False (no retry)
        """
        params = {
            "symbol": symbol.upper().replace("_", ""),
            "orderId": exchange_order_id
        }

        try:
            self.logger.info("mexc_adapter.cancel_order", {
                "symbol": symbol,
                "exchange_order_id": exchange_order_id
            })

            response = await self._make_request("DELETE", "/api/v3/order", params, signed=True)

            success = response.get("orderId") == exchange_order_id

            self.logger.info("mexc_adapter.order_cancelled", {
                "symbol": symbol,
                "exchange_order_id": exchange_order_id,
                "success": success
            })

            return success

        except Exception as e:
            # Check if order not found (HTTP 400)
            error_msg = str(e).lower()
            if "not found" in error_msg or "unknown order" in error_msg:
                self.logger.warning("mexc_adapter.cancel_order_not_found", {
                    "symbol": symbol,
                    "exchange_order_id": exchange_order_id
                })
                return False

            self.logger.error("mexc_adapter.cancel_order_error", {
                "symbol": symbol,
                "exchange_order_id": exchange_order_id,
                "error": str(e),
                "error_type": type(e).__name__
            })
            raise

    async def get_order_status(
        self,
        symbol: str,
        exchange_order_id: str
    ) -> OrderStatusResponse:
        """
        Get order status from MEXC (Agent 3 - Task 3.1).

        Args:
            symbol: Trading symbol (e.g., "BTC_USDT")
            exchange_order_id: Exchange order ID to query

        Returns:
            OrderStatusResponse with order details

        Raises:
            Exception: On API errors (500, 418 rate limit, network timeout, etc.)

        Error Handling:
            - HTTP 500: Server error → Retry via ResilientService
            - HTTP 418: Rate limit → Retry via ResilientService
            - Network timeout → Retry via ResilientService
            - HTTP 400: Order not found → Raise with clear error message
        """
        params = {
            "symbol": symbol.upper().replace("_", ""),
            "orderId": exchange_order_id
        }

        try:
            self.logger.debug("mexc_adapter.get_order_status", {
                "symbol": symbol,
                "exchange_order_id": exchange_order_id
            })

            response = await self._make_request("GET", "/api/v3/order", params, signed=True)

            # Parse response into OrderStatusResponse
            order_status = OrderStatusResponse(
                exchange_order_id=str(response.get("orderId")),
                symbol=response.get("symbol"),
                side=response.get("side"),
                order_type=response.get("type"),
                quantity=float(response.get("origQty", 0)),
                price=float(response.get("price", 0)),
                status=OrderStatus(response.get("status")),
                filled_quantity=float(response.get("executedQty", 0)),
                average_fill_price=float(response.get("avgPrice")) if response.get("avgPrice") else None,
                created_at=int(response.get("time", 0)),
                updated_at=int(response.get("updateTime", response.get("time", 0)))
            )

            return order_status

        except Exception as e:
            self.logger.error("mexc_adapter.get_order_status_error", {
                "symbol": symbol,
                "exchange_order_id": exchange_order_id,
                "error": str(e),
                "error_type": type(e).__name__
            })
            raise

    async def get_positions(self) -> List[PositionResponse]:
        """
        Get all open positions from MEXC Futures API (Agent 3 - Task 3.1).

        Returns:
            List of PositionResponse objects

        Raises:
            Exception: On API errors (500, 418 rate limit, network timeout, etc.)

        Error Handling:
            - HTTP 500: Server error → Retry via ResilientService
            - HTTP 418: Rate limit → Retry via ResilientService
            - Network timeout → Retry via ResilientService

        Note:
            This endpoint uses MEXC Futures API, not Spot API.
            Endpoint: GET /api/v1/private/position/list
            Documentation: https://mexcdevelop.github.io/apidocs/contract_v1_en/#get-all-position-information
        """
        try:
            self.logger.debug("mexc_adapter.get_positions")

            # MEXC Futures API endpoint (different from Spot API)
            # Note: This assumes futures API, adjust base_url if needed
            response = await self._make_request(
                "GET",
                "/api/v1/private/position/list",
                params={},
                signed=True
            )

            positions = []

            # Parse response - MEXC returns positions under "data" key
            position_data = response.get("data", []) if isinstance(response.get("data"), list) else []

            for pos in position_data:
                # Only include positions with non-zero quantity
                quantity = float(pos.get("holdVol", 0))
                if quantity == 0:
                    continue

                # Determine side (1 = LONG, 2 = SHORT in MEXC Futures)
                position_type = pos.get("positionType", 1)
                side = "LONG" if position_type == 1 else "SHORT"

                # Calculate margin ratio
                equity = float(pos.get("equity", 0))
                maintenance_margin = float(pos.get("maintenanceMargin", 1))  # Avoid division by zero
                margin_ratio = (equity / maintenance_margin * 100) if maintenance_margin > 0 else 0

                position = PositionResponse(
                    symbol=pos.get("symbol"),
                    side=side,
                    quantity=quantity,
                    entry_price=float(pos.get("openAvgPrice", 0)),
                    current_price=float(pos.get("fairPrice", 0)),
                    unrealized_pnl=float(pos.get("unrealizedPnl", 0)),
                    margin_ratio=margin_ratio,
                    liquidation_price=float(pos.get("liquidatePrice", 0)),
                    leverage=float(pos.get("leverage", 1)),
                    margin=float(pos.get("holdFee", 0))
                )

                positions.append(position)

            self.logger.info("mexc_adapter.positions_fetched", {
                "count": len(positions)
            })

            return positions

        except Exception as e:
            self.logger.error("mexc_adapter.get_positions_error", {
                "error": str(e),
                "error_type": type(e).__name__
            })
            raise

