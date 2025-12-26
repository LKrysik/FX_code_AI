"""
Unit Tests for MEXC Futures Order Executor
==========================================
Tests for MexcFuturesOrderExecutor - IOrderExecutor implementation wrapper.

Tests cover:
- Initialization with live and paper adapters
- Connection management (connect/disconnect)
- Order placement (market, limit, stop loss)
- Order cancellation (single and all)
- Order status and history
- Health checks and account info
- Response parsing and order conversion

Created: 2025-12-22
"""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from decimal import Decimal
from datetime import datetime

from src.infrastructure.adapters.mexc_futures_order_executor import MexcFuturesOrderExecutor
from src.domain.models.trading import Order, OrderSide, OrderType, OrderStatus
from src.core.logger import StructuredLogger

# Mark all tests in this module as unit tests (no database required)
pytestmark = [pytest.mark.unit, pytest.mark.fast]


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def logger():
    """Mock structured logger"""
    mock_logger = MagicMock(spec=StructuredLogger)
    mock_logger.info = MagicMock()
    mock_logger.error = MagicMock()
    mock_logger.warning = MagicMock()
    mock_logger.debug = MagicMock()
    return mock_logger


@pytest.fixture
def mock_live_adapter():
    """Mock MexcFuturesAdapter (live trading)"""
    adapter = MagicMock()
    adapter._ensure_session = AsyncMock()
    adapter._close_session = AsyncMock()
    adapter._make_request = AsyncMock()
    adapter.set_leverage = AsyncMock()
    adapter.place_futures_order = AsyncMock()
    adapter.get_balances = AsyncMock()
    adapter.get_positions = AsyncMock()
    adapter.is_circuit_breaker_healthy = MagicMock(return_value=True)
    adapter.get_circuit_breaker_status = MagicMock(return_value={
        "circuit_breaker": {"state": "closed"}
    })
    return adapter


@pytest.fixture
def mock_paper_adapter():
    """Mock MexcPaperAdapter (paper trading) - no session methods"""
    adapter = MagicMock(spec=[])  # Empty spec to avoid auto-creating attributes
    adapter.set_leverage = AsyncMock()
    adapter.place_futures_order = AsyncMock()
    adapter._assets = {"USDT": {"free": 10000.0, "locked": 0.0}}
    adapter.get_positions = AsyncMock(return_value=[])
    return adapter


@pytest.fixture
def executor(mock_live_adapter, logger):
    """Create executor with live adapter"""
    return MexcFuturesOrderExecutor(
        mexc_adapter=mock_live_adapter,
        logger=logger,
        default_leverage=3
    )


@pytest.fixture
def paper_executor(mock_paper_adapter, logger):
    """Create executor with paper adapter"""
    return MexcFuturesOrderExecutor(
        mexc_adapter=mock_paper_adapter,
        logger=logger,
        default_leverage=3
    )


# ============================================================================
# Test: Initialization
# ============================================================================

class TestMexcFuturesOrderExecutorInit:
    """Test executor initialization"""

    def test_initialization_with_defaults(self, mock_live_adapter, logger):
        """Test executor initializes with default leverage"""
        executor = MexcFuturesOrderExecutor(
            mexc_adapter=mock_live_adapter,
            logger=logger
        )

        assert executor.mexc_adapter == mock_live_adapter
        assert executor.logger == logger
        assert executor.default_leverage == 3  # default
        assert executor._connected is False
        assert executor._order_cache == {}

    def test_initialization_with_custom_leverage(self, mock_live_adapter, logger):
        """Test executor initializes with custom leverage"""
        executor = MexcFuturesOrderExecutor(
            mexc_adapter=mock_live_adapter,
            logger=logger,
            default_leverage=5
        )

        assert executor.default_leverage == 5


# ============================================================================
# Test: Connection Management
# ============================================================================

class TestMexcFuturesOrderExecutorConnection:
    """Test connection management"""

    @pytest.mark.asyncio
    async def test_connect_with_live_adapter(self, executor, mock_live_adapter):
        """Test connect establishes session for live adapter"""
        await executor.connect()

        mock_live_adapter._ensure_session.assert_called_once()
        assert executor._connected is True

    @pytest.mark.asyncio
    async def test_connect_with_paper_adapter(self, paper_executor):
        """Test connect works without session for paper adapter"""
        await paper_executor.connect()

        # Paper adapter doesn't have _ensure_session
        assert paper_executor._connected is True

    @pytest.mark.asyncio
    async def test_connect_failure(self, executor, mock_live_adapter, logger):
        """Test connect handles failure gracefully"""
        mock_live_adapter._ensure_session.side_effect = Exception("Connection failed")

        with pytest.raises(Exception) as exc_info:
            await executor.connect()

        assert "Connection failed" in str(exc_info.value)
        logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_disconnect_with_live_adapter(self, executor, mock_live_adapter):
        """Test disconnect closes session for live adapter"""
        executor._connected = True

        await executor.disconnect()

        mock_live_adapter._close_session.assert_called_once()
        assert executor._connected is False

    @pytest.mark.asyncio
    async def test_disconnect_with_paper_adapter(self, paper_executor):
        """Test disconnect works without session for paper adapter"""
        paper_executor._connected = True

        await paper_executor.disconnect()

        assert paper_executor._connected is False


# ============================================================================
# Test: Order Placement - Market Orders
# ============================================================================

class TestMexcFuturesOrderExecutorMarketOrders:
    """Test market order placement"""

    @pytest.mark.asyncio
    async def test_place_market_order_buy_long(self, executor, mock_live_adapter):
        """Test placing BUY market order creates LONG position"""
        mock_live_adapter.place_futures_order.return_value = {
            "order_id": "12345",
            "status": "FILLED",
            "executedQty": "0.001",
            "avgPrice": "50000.0"
        }

        order = await executor.place_market_order(
            symbol="BTC_USDT",
            side=OrderSide.BUY,
            quantity=Decimal("0.001")
        )

        # Verify leverage was set
        mock_live_adapter.set_leverage.assert_called_with("BTC_USDT", 3)

        # Verify order was placed with correct params
        mock_live_adapter.place_futures_order.assert_called_with(
            symbol="BTC_USDT",
            side="BUY",
            position_side="LONG",  # BUY -> LONG
            order_type="MARKET",
            quantity=0.001
        )

        # Verify returned order
        assert order.order_id == "12345"
        assert order.symbol == "BTC_USDT"
        assert order.side == OrderSide.BUY
        assert order.order_type == OrderType.MARKET
        assert order.status == OrderStatus.FILLED

    @pytest.mark.asyncio
    async def test_place_market_order_sell_short(self, executor, mock_live_adapter):
        """Test placing SELL market order creates SHORT position"""
        mock_live_adapter.place_futures_order.return_value = {
            "order_id": "67890",
            "status": "FILLED",
            "executedQty": "0.001",
            "avgPrice": "50000.0"
        }

        order = await executor.place_market_order(
            symbol="BTC_USDT",
            side=OrderSide.SELL,
            quantity=Decimal("0.001")
        )

        # Verify order was placed with SHORT position
        mock_live_adapter.place_futures_order.assert_called_with(
            symbol="BTC_USDT",
            side="SELL",
            position_side="SHORT",  # SELL -> SHORT
            order_type="MARKET",
            quantity=0.001
        )

        assert order.side == OrderSide.SELL

    @pytest.mark.asyncio
    async def test_place_market_order_failure(self, executor, mock_live_adapter, logger):
        """Test market order failure handling"""
        mock_live_adapter.place_futures_order.side_effect = Exception("Insufficient balance")

        with pytest.raises(Exception) as exc_info:
            await executor.place_market_order(
                symbol="BTC_USDT",
                side=OrderSide.BUY,
                quantity=Decimal("100.0")
            )

        assert "Insufficient balance" in str(exc_info.value)
        logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_place_market_order_caches_order(self, executor, mock_live_adapter):
        """Test that placed orders are cached"""
        mock_live_adapter.place_futures_order.return_value = {
            "order_id": "cache_test_123",
            "status": "FILLED"
        }

        order = await executor.place_market_order(
            symbol="ETH_USDT",
            side=OrderSide.BUY,
            quantity=Decimal("1.0")
        )

        assert "cache_test_123" in executor._order_cache
        assert executor._order_cache["cache_test_123"] == order


# ============================================================================
# Test: Order Placement - Limit Orders
# ============================================================================

class TestMexcFuturesOrderExecutorLimitOrders:
    """Test limit order placement"""

    @pytest.mark.asyncio
    async def test_place_limit_order_success(self, executor, mock_live_adapter):
        """Test placing limit order"""
        mock_live_adapter.place_futures_order.return_value = {
            "order_id": "limit_123",
            "status": "NEW",
            "price": "48000.0"
        }

        order = await executor.place_limit_order(
            symbol="BTC_USDT",
            side=OrderSide.BUY,
            quantity=Decimal("0.001"),
            price=Decimal("48000.0")
        )

        # Verify order was placed with LIMIT type
        mock_live_adapter.place_futures_order.assert_called_with(
            symbol="BTC_USDT",
            side="BUY",
            position_side="LONG",
            order_type="LIMIT",
            quantity=0.001,
            price=48000.0
        )

        assert order.order_type == OrderType.LIMIT
        assert order.price == Decimal("48000.0")

    @pytest.mark.asyncio
    async def test_place_limit_order_sell_short(self, executor, mock_live_adapter):
        """Test placing limit SELL order creates SHORT position"""
        mock_live_adapter.place_futures_order.return_value = {
            "order_id": "limit_456",
            "status": "NEW"
        }

        await executor.place_limit_order(
            symbol="ETH_USDT",
            side=OrderSide.SELL,
            quantity=Decimal("2.0"),
            price=Decimal("2100.0")
        )

        # Verify SELL -> SHORT mapping
        call_args = mock_live_adapter.place_futures_order.call_args
        assert call_args.kwargs["position_side"] == "SHORT"


# ============================================================================
# Test: Order Placement - Stop Loss
# ============================================================================

class TestMexcFuturesOrderExecutorStopLoss:
    """Test stop loss order placement"""

    @pytest.mark.asyncio
    async def test_place_stop_loss_order_as_limit(self, executor, mock_live_adapter, logger):
        """Test stop loss is placed as limit order (current implementation)"""
        mock_live_adapter.place_futures_order.return_value = {
            "order_id": "stop_123",
            "status": "NEW"
        }

        order = await executor.place_stop_loss_order(
            symbol="BTC_USDT",
            side=OrderSide.SELL,
            quantity=Decimal("0.001"),
            stop_price=Decimal("45000.0")
        )

        # Should log warning about stop loss as limit
        logger.warning.assert_called()

        # Should call place_limit_order under the hood
        mock_live_adapter.place_futures_order.assert_called()
        call_args = mock_live_adapter.place_futures_order.call_args
        assert call_args.kwargs["order_type"] == "LIMIT"
        assert call_args.kwargs["price"] == 45000.0


# ============================================================================
# Test: Order Cancellation
# ============================================================================

class TestMexcFuturesOrderExecutorCancellation:
    """Test order cancellation"""

    @pytest.mark.asyncio
    async def test_cancel_order_success(self, executor, mock_live_adapter):
        """Test successful order cancellation"""
        mock_live_adapter._make_request.return_value = {"orderId": "123"}

        result = await executor.cancel_order("123", "BTC_USDT")

        assert result is True
        mock_live_adapter._make_request.assert_called_with(
            "DELETE",
            "/fapi/v1/order",
            {"symbol": "BTC_USDT", "orderId": "123"},
            signed=True
        )

    @pytest.mark.asyncio
    async def test_cancel_order_updates_cache(self, executor, mock_live_adapter):
        """Test cancel order updates cache status"""
        # Pre-populate cache
        mock_order = MagicMock()
        mock_order.status = OrderStatus.PENDING
        executor._order_cache["456"] = mock_order

        mock_live_adapter._make_request.return_value = {}

        await executor.cancel_order("456", "ETH_USDT")

        assert executor._order_cache["456"].status == OrderStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_cancel_order_failure(self, executor, mock_live_adapter):
        """Test cancel order failure returns False"""
        mock_live_adapter._make_request.side_effect = Exception("Order not found")

        result = await executor.cancel_order("999", "BTC_USDT")

        assert result is False

    @pytest.mark.asyncio
    async def test_cancel_all_orders_with_symbol(self, executor, mock_live_adapter):
        """Test cancel all orders for specific symbol"""
        mock_live_adapter._make_request.return_value = {"count": 5}

        count = await executor.cancel_all_orders("BTC_USDT")

        assert count == 5
        mock_live_adapter._make_request.assert_called_with(
            "DELETE",
            "/fapi/v1/allOpenOrders",
            {"symbol": "BTC_USDT"},
            signed=True
        )

    @pytest.mark.asyncio
    async def test_cancel_all_orders_no_symbol(self, executor, mock_live_adapter):
        """Test cancel all orders without symbol"""
        mock_live_adapter._make_request.return_value = {"count": 10}

        count = await executor.cancel_all_orders()

        assert count == 10
        mock_live_adapter._make_request.assert_called_with(
            "DELETE",
            "/fapi/v1/allOpenOrders",
            {},
            signed=True
        )

    @pytest.mark.asyncio
    async def test_cancel_all_orders_failure(self, executor, mock_live_adapter):
        """Test cancel all orders failure returns 0"""
        mock_live_adapter._make_request.side_effect = Exception("API Error")

        count = await executor.cancel_all_orders("BTC_USDT")

        assert count == 0


# ============================================================================
# Test: Order Status and History
# ============================================================================

class TestMexcFuturesOrderExecutorOrderStatus:
    """Test order status and history retrieval"""

    @pytest.mark.asyncio
    async def test_get_order_status_success(self, executor, mock_live_adapter):
        """Test get order status from API"""
        mock_live_adapter._make_request.return_value = {
            "orderId": "status_123",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "type": "MARKET",
            "status": "FILLED",
            "origQty": "0.001",
            "executedQty": "0.001",
            "avgPrice": "50000.0"
        }

        order = await executor.get_order_status("status_123", "BTC_USDT")

        assert order is not None
        assert order.order_id == "status_123"
        assert order.status == OrderStatus.FILLED

    @pytest.mark.asyncio
    async def test_get_order_status_from_cache(self, executor, mock_live_adapter):
        """Test get order status falls back to cache on API error"""
        cached_order = MagicMock()
        cached_order.order_id = "cached_456"
        executor._order_cache["cached_456"] = cached_order

        mock_live_adapter._make_request.side_effect = Exception("API Error")

        order = await executor.get_order_status("cached_456", "ETH_USDT")

        assert order == cached_order

    @pytest.mark.asyncio
    async def test_get_open_orders(self, executor, mock_live_adapter):
        """Test get open orders"""
        mock_live_adapter._make_request.return_value = [
            {
                "orderId": "open_1",
                "symbol": "BTCUSDT",
                "side": "BUY",
                "type": "LIMIT",
                "status": "NEW",
                "origQty": "0.001"
            },
            {
                "orderId": "open_2",
                "symbol": "BTCUSDT",
                "side": "SELL",
                "type": "LIMIT",
                "status": "NEW",
                "origQty": "0.002"
            }
        ]

        orders = await executor.get_open_orders("BTC_USDT")

        assert len(orders) == 2
        assert orders[0].order_id == "open_1"
        assert orders[1].order_id == "open_2"

    @pytest.mark.asyncio
    async def test_get_open_orders_empty(self, executor, mock_live_adapter):
        """Test get open orders when none exist"""
        mock_live_adapter._make_request.return_value = []

        orders = await executor.get_open_orders("ETH_USDT")

        assert orders == []

    @pytest.mark.asyncio
    async def test_get_order_history(self, executor, mock_live_adapter):
        """Test get order history"""
        mock_live_adapter._make_request.return_value = [
            {
                "orderId": "hist_1",
                "symbol": "BTCUSDT",
                "side": "BUY",
                "type": "MARKET",
                "status": "FILLED",
                "origQty": "0.001",
                "time": 1699372800000
            }
        ]

        orders = await executor.get_order_history(
            symbol="BTC_USDT",
            start_time=datetime(2023, 11, 1),
            end_time=datetime(2023, 11, 30)
        )

        assert len(orders) == 1
        assert orders[0].order_id == "hist_1"

        # Verify time params were passed
        call_args = mock_live_adapter._make_request.call_args
        params = call_args[0][2]
        assert "startTime" in params
        assert "endTime" in params


# ============================================================================
# Test: Exchange Info and Health
# ============================================================================

class TestMexcFuturesOrderExecutorInfo:
    """Test exchange info and health checks"""

    def test_get_exchange_name(self, executor):
        """Test get exchange name returns correct value"""
        assert executor.get_exchange_name() == "MEXC_FUTURES"

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, executor, mock_live_adapter):
        """Test health check when circuit breaker is healthy"""
        mock_live_adapter.is_circuit_breaker_healthy.return_value = True
        mock_live_adapter.get_balances.return_value = {"assets": {}}

        result = await executor.health_check()

        assert result is True
        mock_live_adapter.get_balances.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_circuit_breaker_unhealthy(self, executor, mock_live_adapter, logger):
        """Test health check when circuit breaker is open"""
        mock_live_adapter.is_circuit_breaker_healthy.return_value = False

        result = await executor.health_check()

        assert result is False
        logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_health_check_paper_adapter(self, paper_executor, mock_paper_adapter):
        """Test health check with paper adapter (no circuit breaker)"""
        # Paper adapter has get_balances that returns successfully
        mock_paper_adapter.get_balances = AsyncMock(return_value={"assets": {}})

        result = await paper_executor.health_check()

        # Should pass without circuit breaker check
        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_api_failure(self, executor, mock_live_adapter):
        """Test health check when API fails"""
        mock_live_adapter.get_balances.side_effect = Exception("API Error")

        result = await executor.health_check()

        assert result is False

    @pytest.mark.asyncio
    async def test_get_account_info(self, executor, mock_live_adapter):
        """Test get account info"""
        mock_live_adapter.get_balances.return_value = {
            "assets": {"USDT": {"free": 10000.0}}
        }
        mock_live_adapter.get_positions.return_value = [
            {"symbol": "BTC_USDT", "quantity": 0.001}
        ]

        info = await executor.get_account_info()

        assert info["exchange"] == "MEXC_FUTURES"
        assert "balances" in info
        assert "positions" in info
        assert "circuit_breaker" in info

    @pytest.mark.asyncio
    async def test_get_account_info_paper_adapter(self, paper_executor, mock_paper_adapter):
        """Test get account info with paper adapter"""
        # Paper adapter doesn't have get_balances, uses _assets directly
        info = await paper_executor.get_account_info()

        assert info["exchange"] == "MEXC_FUTURES"
        # Paper adapter uses _assets directly via hasattr check
        assert "balances" in info
        assert info["balances"]["assets"] == mock_paper_adapter._assets

    @pytest.mark.asyncio
    async def test_get_account_info_failure(self, executor, mock_live_adapter):
        """Test get account info handles errors"""
        mock_live_adapter.get_balances.side_effect = Exception("API Error")

        info = await executor.get_account_info()

        assert info["exchange"] == "MEXC_FUTURES"
        assert "error" in info

    @pytest.mark.asyncio
    async def test_get_trading_fees(self, executor):
        """Test get trading fees returns standard MEXC fees"""
        fees = await executor.get_trading_fees("BTC_USDT")

        assert fees["maker"] == Decimal("0.0002")  # 0.02%
        assert fees["taker"] == Decimal("0.0004")  # 0.04%


# ============================================================================
# Test: Response Parsing
# ============================================================================

class TestMexcFuturesOrderExecutorParsing:
    """Test response parsing and order conversion"""

    def test_response_to_order_market(self, executor):
        """Test converting API response to Order for market order"""
        response = {
            "order_id": "parse_123",
            "status": "FILLED",
            "executedQty": "0.001",
            "avgPrice": "50000.0"
        }

        order = executor._response_to_order(
            response=response,
            symbol="BTC_USDT",
            side=OrderSide.BUY,
            quantity=Decimal("0.001"),
            price=None  # Market order
        )

        assert order.order_id == "parse_123"
        assert order.symbol == "BTC_USDT"
        assert order.side == OrderSide.BUY
        assert order.order_type == OrderType.MARKET
        assert order.quantity == Decimal("0.001")
        assert order.status == OrderStatus.FILLED
        assert order.exchange == "MEXC_FUTURES"

    def test_response_to_order_limit(self, executor):
        """Test converting API response to Order for limit order"""
        response = {
            "orderId": "limit_parse_456",
            "status": "NEW"
        }

        order = executor._response_to_order(
            response=response,
            symbol="ETH_USDT",
            side=OrderSide.SELL,
            quantity=Decimal("2.0"),
            price=Decimal("2100.0")
        )

        assert order.order_type == OrderType.LIMIT
        assert order.price == Decimal("2100.0")

    def test_response_to_order_status_mapping(self, executor):
        """Test status mapping from MEXC to domain"""
        # Note: EXPIRED maps to CANCELLED in domain model
        statuses = {
            "NEW": OrderStatus.PENDING,
            "PARTIALLY_FILLED": OrderStatus.PARTIALLY_FILLED,
            "FILLED": OrderStatus.FILLED,
            "CANCELED": OrderStatus.CANCELLED,
            "REJECTED": OrderStatus.REJECTED,
            "EXPIRED": OrderStatus.CANCELLED  # EXPIRED -> CANCELLED
        }

        for mexc_status, expected_status in statuses.items():
            response = {"order_id": "test", "status": mexc_status}
            order = executor._response_to_order(
                response, "BTC_USDT", OrderSide.BUY, Decimal("1"), None
            )
            assert order.status == expected_status, f"Failed for {mexc_status}"

    def test_parse_order_response(self, executor):
        """Test parsing complete order response from API"""
        response = {
            "orderId": "full_123",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "type": "LIMIT",
            "status": "PARTIALLY_FILLED",
            "origQty": "0.01",
            "price": "48000.0",
            "executedQty": "0.005",
            "avgPrice": "48100.0",
            "time": 1699372800000,
            "updateTime": 1699372900000
        }

        order = executor._parse_order_response(response)

        assert order.order_id == "full_123"
        assert order.symbol == "BTCUSDT"
        assert order.side == OrderSide.BUY
        assert order.order_type == OrderType.LIMIT
        assert order.status == OrderStatus.PARTIALLY_FILLED
        assert order.quantity == Decimal("0.01")
        assert order.price == Decimal("48000.0")
        assert order.filled_quantity == Decimal("0.005")

    def test_parse_order_response_sell(self, executor):
        """Test parsing SELL order response"""
        response = {
            "orderId": "sell_789",
            "symbol": "ETHUSDT",
            "side": "SELL",
            "type": "MARKET",
            "status": "FILLED",
            "origQty": "1.0"
        }

        order = executor._parse_order_response(response)

        assert order.side == OrderSide.SELL
        assert order.order_type == OrderType.MARKET


# ============================================================================
# Test: Edge Cases
# ============================================================================

class TestMexcFuturesOrderExecutorEdgeCases:
    """Test edge cases and error handling"""

    @pytest.mark.asyncio
    async def test_order_with_client_order_id(self, executor, mock_live_adapter):
        """Test order placement with client_order_id (currently ignored)"""
        mock_live_adapter.place_futures_order.return_value = {
            "order_id": "client_test_123",
            "status": "FILLED"
        }

        # client_order_id is accepted but not currently used
        order = await executor.place_market_order(
            symbol="BTC_USDT",
            side=OrderSide.BUY,
            quantity=Decimal("0.001"),
            client_order_id="my_custom_id"
        )

        assert order.order_id == "client_test_123"

    @pytest.mark.asyncio
    async def test_uppercase_symbol_handling(self, executor, mock_live_adapter):
        """Test symbol is properly uppercased for cancel operations"""
        mock_live_adapter._make_request.return_value = {}

        await executor.cancel_order("123", "btc_usdt")  # lowercase

        call_args = mock_live_adapter._make_request.call_args
        params = call_args[0][2]
        assert params["symbol"] == "BTC_USDT"  # Should be uppercase

    @pytest.mark.asyncio
    async def test_get_order_status_empty_response(self, executor, mock_live_adapter):
        """Test get order status with empty response uses cache"""
        mock_live_adapter._make_request.return_value = None

        order = await executor.get_order_status("no_exist", "BTC_USDT")

        # Should return None when not in cache
        assert order is None

    @pytest.mark.asyncio
    async def test_get_open_orders_non_list_response(self, executor, mock_live_adapter):
        """Test get open orders handles non-list response"""
        mock_live_adapter._make_request.return_value = {"error": "unexpected"}

        orders = await executor.get_open_orders("BTC_USDT")

        assert orders == []


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
