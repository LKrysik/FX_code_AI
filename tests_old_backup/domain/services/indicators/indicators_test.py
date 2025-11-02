#!/usr/bin/env python3
"""
Tests for Simple Indicators Implementation
=========================================

Comprehensive test suite for the simple indicators from INDICATORS.md
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock
from src.domain.services.streaming_indicator_engine import StreamingIndicatorEngine, IndicatorConfig
from src.core.event_bus import EventBus


class TestSimpleIndicators:
    """Test suite for simple pump & dump detection indicators."""

    @pytest.fixture
    def event_bus(self):
        """Create mock event bus for testing."""
        return AsyncMock(spec=EventBus)

    @pytest.fixture
    def indicator_engine(self, event_bus):
        """Create indicator engine instance for testing."""
        engine = StreamingIndicatorEngine(event_bus)
        return engine

    @pytest.fixture
    def sample_market_data(self):
        """Generate sample market data for testing."""
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

    def test_volume_spike_ratio_calculation(self, indicator_engine, sample_market_data):
        """Test Volume Spike Ratio indicator calculation."""
        # Setup test data
        indicator_engine.price_data = sample_market_data

        async def run_test():
            # Test with 30s current window vs 30min baseline
            result = await indicator_engine.calculate_volume_spike_ratio(
                current_window_seconds=30,
                baseline_window_seconds=1800
            )

            assert result is not None
            assert isinstance(result, float)
            assert result > 0

            # With spike in recent data, ratio should be > 1
            assert result > 1.0

        asyncio.run(run_test())

    def test_trade_frequency_spike_calculation(self, indicator_engine, sample_market_data):
        """Test Trade Frequency Spike indicator calculation."""
        indicator_engine.price_data = sample_market_data

        async def run_test():
            result = await indicator_engine.calculate_trade_frequency_spike(
                current_window_seconds=30,
                baseline_window_seconds=1800
            )

            assert result is not None
            assert isinstance(result, float)
            assert result > 0

        asyncio.run(run_test())

    def test_price_acceleration_velocity(self, indicator_engine, sample_market_data):
        """Test Price Acceleration indicator (velocity mode)."""
        indicator_engine.price_data = sample_market_data

        async def run_test():
            # Test velocity (1st derivative)
            result = await indicator_engine.calculate_price_acceleration(
                window_seconds=60,
                derivative_order=1
            )

            assert result is not None
            assert isinstance(result, float)

            # With rising prices, velocity should be positive
            assert result > 0

        asyncio.run(run_test())

    def test_price_acceleration_acceleration(self, indicator_engine, sample_market_data):
        """Test Price Acceleration indicator (acceleration mode)."""
        indicator_engine.price_data = sample_market_data

        async def run_test():
            # Test acceleration (2nd derivative)
            result = await indicator_engine.calculate_price_acceleration(
                window_seconds=120,
                derivative_order=2
            )

            assert result is not None
            assert isinstance(result, float)

        asyncio.run(run_test())

    def test_momentum_decay_calculation(self, indicator_engine, sample_market_data):
        """Test Momentum Decay indicator calculation."""
        indicator_engine.price_data = sample_market_data

        async def run_test():
            result = await indicator_engine.calculate_momentum_decay(
                peak_lookback_seconds=300
            )

            assert result is not None
            assert isinstance(result, float)
            assert 0 <= result <= 1  # Should be between 0 and 1

            # With rising prices, decay should be low
            assert result < 0.5

        asyncio.run(run_test())

    def test_spread_widening_ratio_calculation(self, indicator_engine, sample_market_data):
        """Test Spread Widening Ratio indicator calculation."""
        indicator_engine.price_data = sample_market_data

        async def run_test():
            result = await indicator_engine.calculate_spread_widening_ratio(
                current_window_seconds=30,
                baseline_window_seconds=1800
            )

            assert result is not None
            assert isinstance(result, float)
            assert result > 0

        asyncio.run(run_test())

    def test_liquidity_drain_calculation(self, indicator_engine, sample_market_data):
        """Test Liquidity Drain indicator calculation."""
        # Add more data points within the window to ensure calculation
        current_time = int(time.time() * 1000)
        additional_data = [
            {"price": 108.0, "volume": 90.0, "timestamp": current_time - 5000},   # 5 sec ago
            {"price": 109.0, "volume": 95.0, "timestamp": current_time - 2000},   # 2 sec ago
        ]
        indicator_engine.price_data = sample_market_data + additional_data

        async def run_test():
            result = await indicator_engine.calculate_liquidity_drain(
                window_seconds=60
            )

            assert result is not None
            assert isinstance(result, float)
            assert 0 <= result <= 1  # Should be between 0 and 1

        asyncio.run(run_test())

    def test_indicator_caching(self, indicator_engine, sample_market_data):
        """Test that indicators use caching properly."""
        indicator_engine.price_data = sample_market_data

        async def run_test():
            # First calculation
            result1 = await indicator_engine.calculate_volume_spike_ratio(30, 1800)

            # Second calculation with same parameters should use cache
            result2 = await indicator_engine.calculate_volume_spike_ratio(30, 1800)

            assert result1 == result2

            # Check cache exists
            cache_key = indicator_engine._get_cache_key("volume_spike_ratio", 30)
            cached = indicator_engine._get_cached_indicator(cache_key)
            assert cached == result1

        asyncio.run(run_test())

    def test_insufficient_data_handling(self, indicator_engine):
        """Test handling of insufficient data."""
        # Empty data
        indicator_engine.price_data = []

        async def run_test():
            result = await indicator_engine.calculate_volume_spike_ratio()
            assert result is None

            result = await indicator_engine.calculate_price_acceleration()
            assert result is None

        asyncio.run(run_test())

    def test_indicator_registration(self, indicator_engine):
        """Test indicator registration functionality."""
        # Register a volume spike ratio indicator
        indicator_engine.register_volume_spike_ratio_indicator(
            current_window_seconds=30,
            baseline_window_seconds=1800
        )

        registered = indicator_engine.get_registered_indicators()
        assert "volume_spike_ratio_30s_1800s" in registered

        # Register price acceleration indicator
        indicator_engine.register_price_acceleration_indicator(
            window_seconds=60,
            derivative_order=1
        )

        registered = indicator_engine.get_registered_indicators()
        assert "price_acceleration_60s_order1" in registered

    def test_edge_cases(self, indicator_engine):
        """Test edge cases and boundary conditions."""
        # Minimal data
        minimal_data = [
            {"price": 100.0, "volume": 10.0, "timestamp": int(time.time() * 1000)}
        ]
        indicator_engine.price_data = minimal_data

        async def run_test():
            # These should return None with insufficient data
            assert await indicator_engine.calculate_price_acceleration() is None
            assert await indicator_engine.calculate_liquidity_drain() is None

            # But volume spike should work with minimal data
            result = await indicator_engine.calculate_volume_spike_ratio()
            assert result is not None

        asyncio.run(run_test())

    @pytest.mark.parametrize("indicator_method,expected_range", [
        ("calculate_volume_spike_ratio", (0, float('inf'))),
        ("calculate_trade_frequency_spike", (0, float('inf'))),
        ("calculate_momentum_decay", (0, 1)),
    ])
    def test_indicator_value_ranges(self, indicator_engine, sample_market_data, indicator_method, expected_range):
        """Test that indicators return values in expected ranges."""
        indicator_engine.price_data = sample_market_data

        async def run_test():
            method = getattr(indicator_engine, indicator_method)
            result = await method()

            assert result is not None
            assert expected_range[0] <= result <= expected_range[1]

        asyncio.run(run_test())

    def test_liquidity_drain_value_range(self, indicator_engine, sample_market_data):
        """Test that liquidity drain indicator returns value in expected range."""
        # Add more data points within the window for liquidity drain calculation
        current_time = int(time.time() * 1000)
        additional_data = [
            {"price": 108.0, "volume": 90.0, "timestamp": current_time - 5000},   # 5 sec ago
            {"price": 109.0, "volume": 95.0, "timestamp": current_time - 2000},   # 2 sec ago
        ]
        indicator_engine.price_data = sample_market_data + additional_data

        async def run_test():
            result = await indicator_engine.calculate_liquidity_drain()

            assert result is not None
            assert 0 <= result <= 1  # Should be between 0 and 1

        asyncio.run(run_test())


if __name__ == "__main__":
    pytest.main([__file__])