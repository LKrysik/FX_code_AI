#!/usr/bin/env python3
"""
Tests for Streaming Indicator Engine Implementation
==================================================

Comprehensive test suite for the streaming indicator engine with real implementations
"""

import pytest
import asyncio
import time
from collections import deque
from unittest.mock import AsyncMock, MagicMock
from src.domain.services.streaming_indicator_engine import StreamingIndicatorEngine, StreamingIndicator, IndicatorType
from src.core.event_bus import EventBus


class TestStreamingIndicatorEngine:
    """Test suite for streaming indicator engine with real implementations."""

    @pytest.fixture
    def event_bus(self):
        """Create mock event bus for testing."""
        return AsyncMock(spec=EventBus)

    @pytest.fixture
    def indicator_engine(self, event_bus):
        """Create indicator engine instance for testing."""
        logger = MagicMock()
        engine = StreamingIndicatorEngine(event_bus, logger)
        return engine

    @pytest.fixture
    def sample_deal_data(self):
        """Generate sample deal data for testing."""
        base_time = int(time.time() * 1000)
        return [
            {"price": 100.0, "volume": 10.0, "timestamp": base_time - 3600000},  # 1 hour ago
            {"price": 101.0, "volume": 12.0, "timestamp": base_time - 1800000},  # 30 min ago
            {"price": 102.0, "volume": 15.0, "timestamp": base_time - 600000},   # 10 min ago
            {"price": 103.0, "volume": 20.0, "timestamp": base_time - 60000},    # 1 min ago
            {"price": 105.0, "volume": 50.0, "timestamp": base_time - 30000},    # 30 sec ago
            {"price": 107.0, "volume": 80.0, "timestamp": base_time - 10000},    # 10 sec ago
            {"price": 110.0, "volume": 100.0, "timestamp": base_time},           # now
        ]

    @pytest.fixture
    def sample_orderbook_data(self):
        """Generate sample orderbook data for testing."""
        base_time = int(time.time() * 1000)
        return [
            {
                "best_bid": 109.5, "best_ask": 110.5, "bid_qty": 100.0, "ask_qty": 120.0,
                "timestamp": base_time - 3600000
            },
            {
                "best_bid": 109.7, "best_ask": 110.7, "bid_qty": 110.0, "ask_qty": 130.0,
                "timestamp": base_time - 1800000
            },
            {
                "best_bid": 109.8, "best_ask": 110.8, "bid_qty": 105.0, "ask_qty": 125.0,
                "timestamp": base_time - 600000
            },
            {
                "best_bid": 109.9, "best_ask": 110.9, "bid_qty": 115.0, "ask_qty": 135.0,
                "timestamp": base_time - 60000
            },
            {
                "best_bid": 109.6, "best_ask": 110.6, "bid_qty": 90.0, "ask_qty": 110.0,
                "timestamp": base_time - 30000
            },
            {
                "best_bid": 109.4, "best_ask": 110.4, "bid_qty": 85.0, "ask_qty": 105.0,
                "timestamp": base_time - 10000
            },
            {
                "best_bid": 109.2, "best_ask": 110.2, "bid_qty": 80.0, "ask_qty": 100.0,
                "timestamp": base_time
            },
        ]

    def test_trade_size_momentum_calculation(self, indicator_engine, sample_deal_data):
        """Test Trade_Size_Momentum indicator calculation."""
        # Setup test data
        indicator_engine.deal_data = {"BTC/USD": sample_deal_data}

        async def run_test():
            indicator = StreamingIndicator(
                symbol="BTC/USD",
                indicator="TRADE_SIZE_MOMENTUM",
                timeframe="1m",
                current_value=0.0,
                timestamp=time.time(),
                series=deque(maxlen=1000),
                metadata={"type": "TRADE_SIZE_MOMENTUM", "current_window": {"t1": 300, "t2": 0}, "baseline_window": {"t1": 1800, "t2": 300}}
            )

            result = await indicator_engine.calculate_indicator(indicator)

            assert result is not None
            assert isinstance(result, float)
            assert result > 0  # Should be positive with increasing volumes

        asyncio.run(run_test())

    def test_mid_price_velocity_calculation(self, indicator_engine, sample_orderbook_data):
        """Test Mid_Price_Velocity indicator calculation."""
        # Setup test data
        indicator_engine.orderbook_data = {"BTC/USD": sample_orderbook_data}

        async def run_test():
            indicator = StreamingIndicator(
                symbol="BTC/USD",
                indicator="MID_PRICE_VELOCITY",
                timeframe="1m",
                current_value=0.0,
                timestamp=time.time(),
                series=deque(maxlen=1000),
                metadata={"type": "MID_PRICE_VELOCITY", "t": 300}
            )

            result = await indicator_engine.calculate_indicator(indicator)

            assert result is not None
            assert isinstance(result, float)

        asyncio.run(run_test())

    def test_twpa_registered_function_uses_windowed_prices(self, indicator_engine):
        """Ensure TWPA registry function delegates to real windowed calculation."""
        symbol = "BTCUSDT"
        timeframe = "1m"
        now = time.time()
        indicator_engine._price_data[f"{symbol}_{timeframe}"] = deque([
            {"timestamp": now - 60, "price": 100.0},
            {"timestamp": now - 30, "price": 110.0},
            {"timestamp": now, "price": 120.0},
        ], maxlen=indicator_engine._max_series_length)

        indicator = StreamingIndicator(
            symbol=symbol,
            indicator="TWPA",
            timeframe=timeframe,
            current_value=0.0,
            timestamp=now,
            series=deque(maxlen=100),
            metadata={"type": "TWPA", "t1": 60, "t2": 0}
        )

        twpa_definition = indicator_engine._indicator_registry.get_indicator("TWPA")
        result = twpa_definition.calculation_function(indicator, {})

        expected = ((100.0 * 30.0) + (110.0 * 30.0)) / 60.0
        assert result is not None
        assert result == pytest.approx(expected, rel=1e-6)

    def test_vwap_registered_function_uses_volume_weights(self, indicator_engine):
        """Ensure VWAP registry function delegates to real deal aggregates."""
        symbol = "BTCUSDT"
        timeframe = "1m"
        now = time.time()
        indicator_engine._deal_data[f"{symbol}_{timeframe}"] = deque([
            {"timestamp": now - 40, "price": 100.0, "volume": 2.0},
            {"timestamp": now - 20, "price": 110.0, "volume": 3.0},
            {"timestamp": now - 5, "price": 120.0, "volume": 5.0},
        ], maxlen=indicator_engine._max_series_length)

        indicator = StreamingIndicator(
            symbol=symbol,
            indicator="VWAP",
            timeframe=timeframe,
            current_value=0.0,
            timestamp=now,
            series=deque(maxlen=100),
            metadata={"type": "VWAP", "t1": 60, "t2": 0}
        )

        vwap_definition = indicator_engine._indicator_registry.get_indicator("VWAP")
        result = vwap_definition.calculation_function(indicator, {})

        expected = ((100.0 * 2.0) + (110.0 * 3.0) + (120.0 * 5.0)) / (2.0 + 3.0 + 5.0)
        assert result is not None
        assert result == pytest.approx(expected, rel=1e-6)

    def test_max_min_price_registered_functions_use_window(self, indicator_engine):
        """Ensure MAX/MIN price registry functions leverage window aggregates."""
        symbol = "BTCUSDT"
        timeframe = "1m"
        now = time.time()
        prices = [95.0, 102.0, 99.0, 111.0, 108.0]
        indicator_engine._price_data[f"{symbol}_{timeframe}"] = deque([
            {"timestamp": now - (len(prices) - idx) * 10, "price": price}
            for idx, price in enumerate(prices)
        ], maxlen=indicator_engine._max_series_length)

        max_indicator = StreamingIndicator(
            symbol=symbol,
            indicator="MAX_PRICE",
            timeframe=timeframe,
            current_value=0.0,
            timestamp=now,
            series=deque(maxlen=100),
            metadata={"type": "MAX_PRICE", "t1": 60, "t2": 0}
        )
        min_indicator = StreamingIndicator(
            symbol=symbol,
            indicator="MIN_PRICE",
            timeframe=timeframe,
            current_value=0.0,
            timestamp=now,
            series=deque(maxlen=100),
            metadata={"type": "MIN_PRICE", "t1": 60, "t2": 0}
        )

        max_definition = indicator_engine._indicator_registry.get_indicator("MAX_PRICE")
        min_definition = indicator_engine._indicator_registry.get_indicator("MIN_PRICE")

        max_value = max_definition.calculation_function(max_indicator, {})
        min_value = min_definition.calculation_function(min_indicator, {})

        assert max_value == pytest.approx(max(prices), rel=1e-6)
        assert min_value == pytest.approx(min(prices), rel=1e-6)

    def test_total_liquidity_calculation(self, indicator_engine, sample_orderbook_data):
        """Test Total_Liquidity indicator calculation."""
        # Setup test data
        indicator_engine.orderbook_data = {"BTC/USD": sample_orderbook_data}

        async def run_test():
            indicator = StreamingIndicator(
                symbol="BTC/USD",
                indicator="TOTAL_LIQUIDITY",
                timeframe="1m",
                current_value=0.0,
                timestamp=time.time(),
                series=deque(maxlen=1000),
                metadata={"t1": 300, "t2": 0}
            )

            result = await indicator_engine.calculate_indicator(indicator)

            assert result is not None
            assert isinstance(result, float)
            assert result > 0  # Should be positive

        asyncio.run(run_test())

    def test_liquidity_ratio_calculation(self, indicator_engine, sample_orderbook_data):
        """Test Liquidity_Ratio indicator calculation."""
        # Setup test data
        indicator_engine.orderbook_data = {"BTC/USD": sample_orderbook_data}

        async def run_test():
            indicator = StreamingIndicator(
                symbol="BTC/USD",
                indicator_type="LIQUIDITY_RATIO",
                metadata={
                    "current_window": {"t1": 300, "t2": 0},
                    "baseline_window": {"t1": 1800, "t2": 300}
                }
            )

            result = await indicator_engine.calculate_indicator(indicator)

            assert result is not None
            assert isinstance(result, float)
            assert result > 0

        asyncio.run(run_test())

    def test_liquidity_drain_index_calculation(self, indicator_engine, sample_orderbook_data):
        """Test Liquidity_Drain_Index indicator calculation."""
        # Setup test data
        indicator_engine.orderbook_data = {"BTC/USD": sample_orderbook_data}

        async def run_test():
            indicator = StreamingIndicator(
                symbol="BTC/USD",
                indicator_type="LIQUIDITY_DRAIN_INDEX",
                metadata={
                    "current_window": {"t1": 300, "t2": 0},
                    "baseline_window": {"t1": 600, "t2": 300}
                }
            )

            result = await indicator_engine.calculate_indicator(indicator)

            assert result is not None
            assert isinstance(result, float)
            assert 0 <= result <= 1  # Should be between 0 and 1

        asyncio.run(run_test())

    def test_deal_vs_mid_deviation_calculation(self, indicator_engine, sample_deal_data, sample_orderbook_data):
        """Test Deal_vs_Mid_Deviation indicator calculation."""
        # Setup test data
        indicator_engine.deal_data = {"BTC/USD": sample_deal_data}
        indicator_engine.orderbook_data = {"BTC/USD": sample_orderbook_data}

        async def run_test():
            indicator = StreamingIndicator(
                symbol="BTC/USD",
                indicator_type="DEAL_VS_MID_DEVIATION",
                metadata={"t1": 300, "t2": 0}
            )

            result = await indicator_engine.calculate_indicator(indicator)

            assert result is not None
            assert isinstance(result, float)
            assert result >= 0  # Should be non-negative

        asyncio.run(run_test())

    def test_inter_deal_intervals_calculation(self, indicator_engine, sample_deal_data):
        """Test Inter_Deal_Intervals indicator calculation."""
        # Setup test data
        indicator_engine.deal_data = {"BTC/USD": sample_deal_data}

        async def run_test():
            indicator = StreamingIndicator(
                symbol="BTC/USD",
                indicator_type="INTER_DEAL_INTERVALS",
                metadata={"t1": 300, "t2": 0}
            )

            result = await indicator_engine.calculate_indicator(indicator)

            assert result is not None
            assert isinstance(result, list)
            assert len(result) > 0  # Should have intervals

        asyncio.run(run_test())

    def test_decision_density_acceleration_calculation(self, indicator_engine, sample_deal_data):
        """Test Decision_Density_Acceleration indicator calculation."""
        # Setup test data
        indicator_engine.deal_data = {"BTC/USD": sample_deal_data}

        async def run_test():
            indicator = StreamingIndicator(
                symbol="BTC/USD",
                indicator_type="DECISION_DENSITY_ACCELERATION",
                metadata={
                    "current_window": {"t1": 300, "t2": 0},
                    "baseline_window": {"t1": 600, "t2": 300}
                }
            )

            result = await indicator_engine.calculate_indicator(indicator)

            assert result is not None
            assert isinstance(result, float)
            assert result > 0

        asyncio.run(run_test())

    def test_trade_clustering_coefficient_calculation(self, indicator_engine, sample_deal_data):
        """Test Trade_Clustering_Coefficient indicator calculation."""
        # Setup test data
        indicator_engine.deal_data = {"BTC/USD": sample_deal_data}

        async def run_test():
            indicator = StreamingIndicator(
                symbol="BTC/USD",
                indicator_type="TRADE_CLUSTERING_COEFFICIENT",
                metadata={"t1": 300, "t2": 0, "min_deals": 5}
            )

            result = await indicator_engine.calculate_indicator(indicator)

            assert result is not None
            assert isinstance(result, float)
            assert result >= 0

        asyncio.run(run_test())

    def test_price_volatility_calculation(self, indicator_engine, sample_deal_data):
        """Test Price_Volatility indicator calculation."""
        # Setup test data
        indicator_engine.deal_data = {"BTC/USD": sample_deal_data}

        async def run_test():
            indicator = StreamingIndicator(
                symbol="BTC/USD",
                indicator_type="PRICE_VOLATILITY",
                metadata={"t1": 300, "t2": 0, "min_deals": 3}
            )

            result = await indicator_engine.calculate_indicator(indicator)

            assert result is not None
            assert isinstance(result, float)
            assert result >= 0

        asyncio.run(run_test())

    def test_deal_size_volatility_calculation(self, indicator_engine, sample_deal_data):
        """Test Deal_Size_Volatility indicator calculation."""
        # Setup test data
        indicator_engine.deal_data = {"BTC/USD": sample_deal_data}

        async def run_test():
            indicator = StreamingIndicator(
                symbol="BTC/USD",
                indicator_type="DEAL_SIZE_VOLATILITY",
                metadata={"t1": 300, "t2": 0}
            )

            result = await indicator_engine.calculate_indicator(indicator)

            assert result is not None
            assert isinstance(result, float)
            assert result >= 0

        asyncio.run(run_test())

    def test_insufficient_data_handling(self, indicator_engine):
        """Test handling of insufficient data for all Phase 3 indicators."""
        # Empty data
        indicator_engine.deal_data = {}
        indicator_engine.orderbook_data = {}

        async def run_test():
            indicators_to_test = [
                ("TRADE_SIZE_MOMENTUM", {"current_window": {"t1": 300, "t2": 0}, "baseline_window": {"t1": 1800, "t2": 300}}),
                ("MID_PRICE_VELOCITY", {"t": 300}),
                ("TOTAL_LIQUIDITY", {"t1": 300, "t2": 0}),
                ("LIQUIDITY_RATIO", {"current_window": {"t1": 300, "t2": 0}, "baseline_window": {"t1": 1800, "t2": 300}}),
                ("LIQUIDITY_DRAIN_INDEX", {"current_window": {"t1": 300, "t2": 0}, "baseline_window": {"t1": 600, "t2": 300}}),
                ("DEAL_VS_MID_DEVIATION", {"t1": 300, "t2": 0}),
                ("INTER_DEAL_INTERVALS", {"t1": 300, "t2": 0}),
                ("DECISION_DENSITY_ACCELERATION", {"current_window": {"t1": 300, "t2": 0}, "baseline_window": {"t1": 600, "t2": 300}}),
                ("TRADE_CLUSTERING_COEFFICIENT", {"t1": 300, "t2": 0, "min_deals": 5}),
                ("PRICE_VOLATILITY", {"t1": 300, "t2": 0, "min_deals": 3}),
                ("DEAL_SIZE_VOLATILITY", {"t1": 300, "t2": 0})
            ]

            for indicator_type, metadata in indicators_to_test:
                indicator = StreamingIndicator(
                    symbol="BTC/USD",
                    indicator=indicator_type,
                    timeframe="1m",
                    current_value=0.0,
                    timestamp=time.time(),
                    series=deque(maxlen=1000),
                    metadata={"type": indicator_type, **metadata}
                )

                result = await indicator_engine.calculate_indicator(indicator)
                assert result is None, f"{indicator_type} should return None with insufficient data"

        asyncio.run(run_test())

    def test_indicator_type_enum_coverage(self, indicator_engine):
        """Test that all Phase 3 indicators are covered in the enum."""
        from src.domain.services.streaming_indicator_engine import IndicatorType

        phase_3_indicators = [
            "TRADE_SIZE_MOMENTUM",
            "MID_PRICE_VELOCITY",
            "TOTAL_LIQUIDITY",
            "LIQUIDITY_RATIO",
            "LIQUIDITY_DRAIN_INDEX",
            "DEAL_VS_MID_DEVIATION",
            "INTER_DEAL_INTERVALS",
            "DECISION_DENSITY_ACCELERATION",
            "TRADE_CLUSTERING_COEFFICIENT",
            "PRICE_VOLATILITY",
            "DEAL_SIZE_VOLATILITY"
        ]

        for indicator_name in phase_3_indicators:
            assert hasattr(IndicatorType, indicator_name), f"IndicatorType missing {indicator_name}"
            indicator_type = getattr(IndicatorType, indicator_name)
            assert indicator_type in IndicatorType, f"{indicator_name} not in IndicatorType enum"


if __name__ == "__main__":
    pytest.main([__file__])
