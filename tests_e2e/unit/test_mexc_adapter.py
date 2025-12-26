"""
Unit Tests for MEXC Futures Adapter
===================================
Tests for MexcFuturesAdapter - the actual MEXC Futures API integration.

Tests cover:
- Initialization and configuration
- Leverage management (1-10x safety limits)
- Order placement (LONG/SHORT positions)
- Position retrieval
- Funding rate queries
- Circuit breaker integration
- Compatibility methods (for backward compatibility with Spot interface)

Updated: 2025-12-22 - Fixed orphaned tests that were testing non-existent MexcRealAdapter
"""

import pytest

# Mark all tests in this module as unit tests (no database required)
pytestmark = [pytest.mark.unit, pytest.mark.fast]
import asyncio
import time
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from decimal import Decimal

from src.infrastructure.adapters.mexc_futures_adapter import MexcFuturesAdapter
from src.core.logger import StructuredLogger


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
def adapter(logger):
    """Create MEXC Futures adapter instance with mocked dependencies"""
    adapter = MexcFuturesAdapter(
        api_key="test_api_key",
        api_secret="test_api_secret",
        logger=logger
    )
    return adapter


@pytest.fixture
def mock_resilient_service():
    """Mock resilient service for circuit breaker"""
    mock_service = MagicMock()
    mock_service.call_async = AsyncMock()
    mock_service.get_status = MagicMock(return_value={
        "circuit_breaker": {
            "state": "closed",
            "metrics": {
                "success_rate_percent": 100,
                "total_requests": 10,
                "failed_requests": 0
            }
        }
    })
    return mock_service


# ============================================================================
# Test: Initialization
# ============================================================================

class TestMexcFuturesAdapterInit:
    """Test adapter initialization"""

    def test_initialization_with_defaults(self, logger):
        """Test adapter initializes with correct defaults"""
        adapter = MexcFuturesAdapter(
            api_key="test_key",
            api_secret="test_secret",
            logger=logger
        )

        assert adapter.api_key == "test_key"
        assert adapter.api_secret == "test_secret"
        assert adapter.base_url == "https://contract.mexc.com"
        assert adapter.rate_limiter["requests_per_second"] == 100
        assert adapter._leverage_cache == {}

    def test_initialization_with_custom_base_url(self, logger):
        """Test adapter accepts custom base URL"""
        adapter = MexcFuturesAdapter(
            api_key="test_key",
            api_secret="test_secret",
            logger=logger,
            base_url="https://custom.mexc.com"
        )

        assert adapter.base_url == "https://custom.mexc.com"


# ============================================================================
# Test: Leverage Management
# ============================================================================

class TestMexcFuturesAdapterLeverage:
    """Test leverage configuration with safety limits"""

    @pytest.mark.asyncio
    async def test_set_leverage_success(self, adapter):
        """Test successful leverage setting within safe range"""
        mock_response = {"success": True, "leverage": 3}

        with patch.object(adapter, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await adapter.set_leverage("BTC_USDT", 3)

            assert result["success"] is True
            assert result["leverage"] == 3
            assert result["symbol"] == "BTC_USDT"
            assert adapter._leverage_cache["BTC_USDT"] == 3

            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args[0][0] == "POST"
            assert call_args[0][1] == "/fapi/v1/leverage"

    @pytest.mark.asyncio
    async def test_set_leverage_rejects_above_10x(self, adapter):
        """Test that leverage above 10x is rejected for safety"""
        with pytest.raises(ValueError) as exc_info:
            await adapter.set_leverage("BTC_USDT", 15)

        assert "Leverage must be between 1 and 10" in str(exc_info.value)
        assert "extreme liquidation risk" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_set_leverage_rejects_below_1x(self, adapter):
        """Test that leverage below 1x is rejected"""
        with pytest.raises(ValueError) as exc_info:
            await adapter.set_leverage("BTC_USDT", 0)

        assert "Leverage must be between 1 and 10" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_leverage_from_cache(self, adapter):
        """Test leverage retrieval from cache"""
        adapter._leverage_cache["ETH_USDT"] = 5

        leverage = await adapter.get_leverage("ETH_USDT")

        assert leverage == 5

    @pytest.mark.asyncio
    async def test_get_leverage_with_fallback(self, adapter):
        """Test leverage fallback when circuit breaker is open"""
        with patch.object(adapter, 'is_circuit_breaker_healthy', return_value=False):
            leverage = await adapter.get_leverage_with_fallback("BTC_USDT", default_leverage=3)

            assert leverage == 3


# ============================================================================
# Test: Order Placement
# ============================================================================

class TestMexcFuturesAdapterOrders:
    """Test order placement methods"""

    @pytest.mark.asyncio
    async def test_place_futures_order_long_market(self, adapter):
        """Test placing a LONG market order"""
        mock_response = {
            "orderId": "12345678",
            "status": "FILLED",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "positionSide": "LONG",
            "type": "MARKET",
            "origQty": "0.001",
            "avgPrice": "50000.00"
        }

        with patch.object(adapter, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await adapter.place_futures_order(
                symbol="BTC_USDT",
                side="BUY",
                position_side="LONG",
                order_type="MARKET",
                quantity=0.001
            )

            assert result["order_id"] == "12345678"
            assert result["status"] == "FILLED"
            assert result["side"] == "BUY"
            assert result["position_side"] == "LONG"
            assert result["source"] == "mexc_futures_api"

    @pytest.mark.asyncio
    async def test_place_futures_order_short_market(self, adapter):
        """Test placing a SHORT market order (open short position)"""
        mock_response = {
            "orderId": "87654321",
            "status": "FILLED",
            "symbol": "BTCUSDT",
            "side": "SELL",
            "positionSide": "SHORT",
            "type": "MARKET",
            "origQty": "0.001",
            "avgPrice": "50000.00"
        }

        with patch.object(adapter, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await adapter.place_futures_order(
                symbol="BTC_USDT",
                side="SELL",
                position_side="SHORT",
                order_type="MARKET",
                quantity=0.001
            )

            assert result["order_id"] == "87654321"
            assert result["side"] == "SELL"
            assert result["position_side"] == "SHORT"

    @pytest.mark.asyncio
    async def test_place_futures_order_limit_requires_price(self, adapter):
        """Test that LIMIT orders require price parameter"""
        with pytest.raises(ValueError) as exc_info:
            await adapter.place_futures_order(
                symbol="BTC_USDT",
                side="BUY",
                position_side="LONG",
                order_type="LIMIT",
                quantity=0.001
                # Missing price parameter
            )

        assert "Price required for LIMIT orders" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_place_futures_order_limit_with_price(self, adapter):
        """Test placing a LIMIT order with price"""
        mock_response = {
            "orderId": "11111111",
            "status": "NEW",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "positionSide": "LONG",
            "type": "LIMIT",
            "origQty": "0.001",
            "price": "48000.00"
        }

        with patch.object(adapter, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await adapter.place_futures_order(
                symbol="BTC_USDT",
                side="BUY",
                position_side="LONG",
                order_type="LIMIT",
                quantity=0.001,
                price=48000.0
            )

            assert result["order_id"] == "11111111"
            assert result["type"] == "LIMIT"

            # Verify params include price and timeInForce
            call_args = mock_request.call_args
            params = call_args[0][2]
            assert params["price"] == "48000.0"
            assert params["timeInForce"] == "GTC"

    @pytest.mark.asyncio
    async def test_place_futures_order_api_error(self, adapter):
        """Test order placement with API error"""
        with patch.object(adapter, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = Exception("MEXC API Error: Insufficient balance")

            with pytest.raises(Exception) as exc_info:
                await adapter.place_futures_order(
                    symbol="BTC_USDT",
                    side="BUY",
                    position_side="LONG",
                    order_type="MARKET",
                    quantity=100.0
                )

            assert "Insufficient balance" in str(exc_info.value)


# ============================================================================
# Test: Position Management
# ============================================================================

class TestMexcFuturesAdapterPositions:
    """Test position retrieval methods"""

    @pytest.mark.asyncio
    async def test_get_position_long(self, adapter):
        """Test retrieving LONG position"""
        mock_response = [
            {
                "symbol": "BTCUSDT",
                "positionSide": "LONG",
                "positionAmt": "0.001",
                "entryPrice": "50000.00",
                "leverage": "3",
                "liquidationPrice": "40000.00",
                "unRealizedProfit": "10.00",
                "marginType": "ISOLATED"
            }
        ]

        with patch.object(adapter, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            position = await adapter.get_position("BTC_USDT")

            assert position is not None
            assert position["symbol"] == "BTCUSDT"
            assert position["position_side"] == "LONG"
            assert position["position_amount"] == 0.001
            assert position["entry_price"] == 50000.0
            assert position["leverage"] == 3
            assert position["liquidation_price"] == 40000.0
            assert position["unrealized_pnl"] == 10.0

    @pytest.mark.asyncio
    async def test_get_position_no_position(self, adapter):
        """Test get_position when no active position"""
        mock_response = [
            {
                "symbol": "BTCUSDT",
                "positionSide": "LONG",
                "positionAmt": "0",  # Zero position
                "entryPrice": "0",
                "leverage": "1"
            }
        ]

        with patch.object(adapter, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            position = await adapter.get_position("BTC_USDT")

            assert position is None

    @pytest.mark.asyncio
    async def test_get_positions_multiple(self, adapter):
        """Test retrieving multiple positions via compatibility method"""
        mock_response = {
            "data": [
                {
                    "symbol": "BTC_USDT",
                    "positionType": 1,  # LONG
                    "holdVol": "0.5",
                    "openAvgPrice": "50000.00",
                    "fairPrice": "51000.00",
                    "unrealizedPnl": "500.00",
                    "equity": "5000.00",
                    "maintenanceMargin": "250.00",
                    "liquidatePrice": "45000.00",
                    "leverage": "10",
                    "positionMargin": "500.00"
                },
                {
                    "symbol": "ETH_USDT",
                    "positionType": 2,  # SHORT
                    "holdVol": "2.0",
                    "openAvgPrice": "2000.00",
                    "fairPrice": "1950.00",
                    "unrealizedPnl": "100.00",
                    "equity": "2000.00",
                    "maintenanceMargin": "100.00",
                    "liquidatePrice": "2200.00",
                    "leverage": "5",
                    "positionMargin": "400.00"
                }
            ]
        }

        with patch.object(adapter, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            positions = await adapter.get_positions()

            assert len(positions) == 2

            # Verify BTC position
            btc_pos = positions[0]
            assert btc_pos["symbol"] == "BTC_USDT"
            assert btc_pos["side"] == "LONG"
            assert btc_pos["quantity"] == 0.5
            assert btc_pos["entry_price"] == 50000.0
            assert btc_pos["leverage"] == 10.0

            # Verify ETH position
            eth_pos = positions[1]
            assert eth_pos["symbol"] == "ETH_USDT"
            assert eth_pos["side"] == "SHORT"
            assert eth_pos["quantity"] == 2.0

    @pytest.mark.asyncio
    async def test_get_positions_filters_zero_quantity(self, adapter):
        """Test that positions with zero quantity are filtered out"""
        mock_response = {
            "data": [
                {
                    "symbol": "BTC_USDT",
                    "positionType": 1,
                    "holdVol": "0.5",  # Non-zero
                    "openAvgPrice": "50000.00",
                    "fairPrice": "51000.00",
                    "unrealizedPnl": "500.00",
                    "equity": "5000.00",
                    "maintenanceMargin": "250.00",
                    "liquidatePrice": "45000.00",
                    "leverage": "10",
                    "positionMargin": "500.00"
                },
                {
                    "symbol": "ETH_USDT",
                    "positionType": 1,
                    "holdVol": "0",  # Zero - should be filtered
                    "openAvgPrice": "2000.00",
                    "fairPrice": "2000.00",
                    "unrealizedPnl": "0.00",
                    "equity": "0.00",
                    "maintenanceMargin": "0.00",
                    "liquidatePrice": "0.00",
                    "leverage": "1",
                    "positionMargin": "0.00"
                }
            ]
        }

        with patch.object(adapter, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            positions = await adapter.get_positions()

            # Only BTC position should be returned
            assert len(positions) == 1
            assert positions[0]["symbol"] == "BTC_USDT"


# ============================================================================
# Test: Funding Rate
# ============================================================================

class TestMexcFuturesAdapterFundingRate:
    """Test funding rate methods"""

    @pytest.mark.asyncio
    async def test_get_funding_rate_success(self, adapter):
        """Test successful funding rate retrieval"""
        mock_response = [
            {
                "symbol": "BTCUSDT",
                "fundingRate": "0.0001",
                "fundingTime": 1699372800000,
                "markPrice": "50000.00"
            }
        ]

        with patch.object(adapter, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await adapter.get_funding_rate("BTC_USDT")

            assert result["symbol"] == "BTCUSDT"
            assert result["funding_rate"] == 0.0001
            assert result["mark_price"] == 50000.0
            assert result["source"] == "mexc_futures_api"

    @pytest.mark.asyncio
    async def test_get_funding_rate_with_fallback_circuit_breaker_open(self, adapter):
        """Test funding rate fallback when circuit breaker is open"""
        with patch.object(adapter, 'is_circuit_breaker_healthy', return_value=False):
            result = await adapter.get_funding_rate_with_fallback("BTC_USDT")

            assert result["funding_rate"] == 0.0
            assert result["source"] == "fallback_circuit_breaker_open"

    @pytest.mark.asyncio
    async def test_calculate_funding_cost(self, adapter):
        """Test funding cost calculation"""
        mock_funding = {
            "symbol": "BTCUSDT",
            "funding_rate": 0.0001,
            "mark_price": 50000.0
        }

        with patch.object(adapter, 'get_funding_rate', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_funding

            # Calculate for 24 hours (3 funding intervals)
            cost = await adapter.calculate_funding_cost("BTC_USDT", -0.001, 24)

            # Expected: position_amount * mark_price * funding_rate * intervals
            # -(-0.001 * 50000 * 0.0001 * 3) = -(-0.015) = 0.015
            # Note: negative cost means you earn, positive means you pay
            assert abs(cost - 0.015) < 0.001


# ============================================================================
# Test: Circuit Breaker
# ============================================================================

class TestMexcFuturesAdapterCircuitBreaker:
    """Test circuit breaker integration"""

    def test_is_circuit_breaker_healthy_closed(self, adapter, mock_resilient_service):
        """Test circuit breaker health check when CLOSED"""
        adapter.resilient_service = mock_resilient_service

        result = adapter.is_circuit_breaker_healthy()

        assert result is True

    def test_is_circuit_breaker_healthy_open(self, adapter):
        """Test circuit breaker health check when OPEN"""
        mock_service = MagicMock()
        mock_service.get_status = MagicMock(return_value={
            "circuit_breaker": {"state": "open"}
        })
        adapter.resilient_service = mock_service

        result = adapter.is_circuit_breaker_healthy()

        assert result is False

    def test_get_circuit_breaker_state(self, adapter, mock_resilient_service):
        """Test getting circuit breaker state"""
        adapter.resilient_service = mock_resilient_service

        state = adapter.get_circuit_breaker_state()

        assert state == "closed"


# ============================================================================
# Test: Compatibility Methods
# ============================================================================

class TestMexcFuturesAdapterCompatibility:
    """Test backward compatibility methods matching Spot adapter interface"""

    @pytest.mark.asyncio
    async def test_create_market_order_wrapper(self, adapter):
        """Test create_market_order compatibility wrapper"""
        mock_response = {
            "orderId": "12345",
            "status": "FILLED"
        }

        with patch.object(adapter, 'place_futures_order', new_callable=AsyncMock) as mock_place:
            mock_place.return_value = mock_response

            order_id = await adapter.create_market_order(
                symbol="BTC_USDT",
                side="BUY",
                quantity=0.001
            )

            assert order_id == "12345"

            # Verify it called place_futures_order with correct params
            mock_place.assert_called_once_with(
                symbol="BTC_USDT",
                side="BUY",
                position_side="LONG",  # BUY -> LONG
                order_type="MARKET",
                quantity=0.001
            )

    @pytest.mark.asyncio
    async def test_create_market_order_short(self, adapter):
        """Test create_market_order for SHORT position"""
        mock_response = {
            "orderId": "67890",
            "status": "FILLED"
        }

        with patch.object(adapter, 'place_futures_order', new_callable=AsyncMock) as mock_place:
            mock_place.return_value = mock_response

            order_id = await adapter.create_market_order(
                symbol="BTC_USDT",
                side="SELL",
                quantity=0.001
            )

            # Verify SELL -> SHORT
            mock_place.assert_called_once_with(
                symbol="BTC_USDT",
                side="SELL",
                position_side="SHORT",
                order_type="MARKET",
                quantity=0.001
            )

    @pytest.mark.asyncio
    async def test_create_limit_order_wrapper(self, adapter):
        """Test create_limit_order compatibility wrapper"""
        mock_response = {
            "orderId": "99999",
            "status": "NEW"
        }

        with patch.object(adapter, 'place_futures_order', new_callable=AsyncMock) as mock_place:
            mock_place.return_value = mock_response

            order_id = await adapter.create_limit_order(
                symbol="ETH_USDT",
                side="BUY",
                quantity=1.0,
                price=2000.0
            )

            assert order_id == "99999"

            mock_place.assert_called_once_with(
                symbol="ETH_USDT",
                side="BUY",
                position_side="LONG",
                order_type="LIMIT",
                quantity=1.0,
                price=2000.0
            )

    @pytest.mark.asyncio
    async def test_get_balances(self, adapter):
        """Test get_balances compatibility method"""
        mock_response = {
            "data": {
                "assets": [
                    {"asset": "USDT", "availableBalance": "10000.00", "frozenBalance": "500.00"},
                    {"asset": "BTC", "availableBalance": "0.5", "frozenBalance": "0.1"}
                ]
            }
        }

        with patch.object(adapter, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await adapter.get_balances()

            assert "assets" in result
            assert result["assets"]["USDT"]["free"] == 10000.0
            assert result["assets"]["USDT"]["locked"] == 500.0
            assert result["assets"]["BTC"]["free"] == 0.5
            assert result["source"] == "mexc_futures_api"

    @pytest.mark.asyncio
    async def test_deprecated_place_order_raises(self, adapter):
        """Test that deprecated place_order raises NotImplementedError"""
        with pytest.raises(NotImplementedError) as exc_info:
            await adapter.place_order(symbol="BTC_USDT", side="BUY", quantity=0.001)

        assert "place_futures_order" in str(exc_info.value)


# ============================================================================
# Test: Error Handling
# ============================================================================

class TestMexcFuturesAdapterErrorHandling:
    """Test error handling and resilience"""

    @pytest.mark.asyncio
    async def test_api_error_propagates(self, adapter):
        """Test that API errors propagate correctly"""
        with patch.object(adapter, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = Exception("MEXC API Error: HTTP 500: Internal Server Error")

            with pytest.raises(Exception) as exc_info:
                await adapter.place_futures_order(
                    symbol="BTC_USDT",
                    side="BUY",
                    position_side="LONG",
                    order_type="MARKET",
                    quantity=0.1
                )

            assert "500" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_network_timeout(self, adapter):
        """Test network timeout handling"""
        with patch.object(adapter, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = asyncio.TimeoutError("Request timeout")

            with pytest.raises(asyncio.TimeoutError):
                await adapter.place_futures_order(
                    symbol="BTC_USDT",
                    side="BUY",
                    position_side="LONG",
                    order_type="MARKET",
                    quantity=0.1
                )


# ============================================================================
# Test: Signature Generation
# ============================================================================

class TestMexcFuturesAdapterSignature:
    """Test HMAC signature generation"""

    def test_generate_signature(self, adapter):
        """Test signature generation for authenticated requests"""
        params = {"symbol": "BTCUSDT", "leverage": 3}
        timestamp = 1699372800000

        signature = adapter._generate_signature(params, timestamp)

        # Signature should be a hex string
        assert isinstance(signature, str)
        assert len(signature) == 64  # SHA256 hex digest length


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
