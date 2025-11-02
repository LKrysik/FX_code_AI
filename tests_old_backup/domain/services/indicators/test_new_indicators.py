"""
Test Suite for New Pump Detection Indicators
===========================================
Tests for PUMP_MAGNITUDE_PCT, VOLUME_SURGE_RATIO, PRICE_VELOCITY, and VELOCITY_CASCADE
"""

import pytest
from src.domain.services.indicators.pump_magnitude_pct import pump_magnitude_pct_algorithm
from src.domain.services.indicators.volume_surge_ratio import volume_surge_ratio_algorithm
from src.domain.services.indicators.price_velocity import price_velocity_algorithm
from src.domain.services.indicators.velocity_cascade import velocity_cascade_algorithm
from src.domain.services.indicators.base_algorithm import IndicatorParameters, DataWindow


class TestPumpMagnitudePct:
    """Test PUMP_MAGNITUDE_PCT indicator."""

    def test_basic_calculation(self):
        """Test basic pump magnitude calculation."""
        # Create test data: price increasing from 100 to 110 (10% pump)
        current_data = [
            (100.0, 105.0),  # 10s ago
            (105.0, 110.0),  # 5s ago (current level)
        ]
        baseline_data = [
            (160.0, 100.0),  # 60s ago
            (145.0, 100.0),  # 45s ago
            (130.0, 100.0),  # 30s ago (baseline level)
        ]

        windows = [
            DataWindow(current_data, 100.0, 110.0, "price"),
            DataWindow(baseline_data, 160.0, 130.0, "price"),
        ]

        params = IndicatorParameters({"t1": 10.0, "t3": 60.0, "d": 30.0})

        result = pump_magnitude_pct_algorithm.calculate_from_windows(windows, params)

        # Should detect ~10% increase
        assert result is not None
        assert result > 0  # Positive = pump
        assert 8.0 < result < 12.0  # Approximately 10%

    def test_no_pump(self):
        """Test when there's no pump (stable price)."""
        # Stable price at 100
        current_data = [(100.0, 100.0), (105.0, 100.0)]
        baseline_data = [(160.0, 100.0), (145.0, 100.0), (130.0, 100.0)]

        windows = [
            DataWindow(current_data, 100.0, 110.0, "price"),
            DataWindow(baseline_data, 160.0, 130.0, "price"),
        ]

        params = IndicatorParameters({"t1": 10.0, "t3": 60.0, "d": 30.0})

        result = pump_magnitude_pct_algorithm.calculate_from_windows(windows, params)

        assert result is not None
        assert abs(result) < 1.0  # Should be near zero

    def test_dump_detection(self):
        """Test detection of price decrease (dump)."""
        # Price decreasing from 100 to 90 (-10% dump)
        current_data = [(100.0, 95.0), (105.0, 90.0)]
        baseline_data = [(160.0, 100.0), (145.0, 100.0), (130.0, 100.0)]

        windows = [
            DataWindow(current_data, 100.0, 110.0, "price"),
            DataWindow(baseline_data, 160.0, 130.0, "price"),
        ]

        params = IndicatorParameters({"t1": 10.0, "t3": 60.0, "d": 30.0})

        result = pump_magnitude_pct_algorithm.calculate_from_windows(windows, params)

        assert result is not None
        assert result < 0  # Negative = dump
        assert -12.0 < result < -8.0  # Approximately -10%


class TestVolumeSurgeRatio:
    """Test VOLUME_SURGE_RATIO indicator."""

    def test_volume_surge_detection(self):
        """Test detection of volume surge."""
        # Current volume: high (10 per second)
        current_data = [
            (100.0, 10.0),
            (101.0, 10.0),
            (102.0, 10.0),
        ]

        # Baseline volume: normal (2 per second)
        baseline_data = [
            (200.0, 2.0),
            (201.0, 2.0),
            (202.0, 2.0),
            (203.0, 2.0),
            (204.0, 2.0),
        ]

        windows = [
            DataWindow(current_data, 100.0, 103.0, "volume"),
            DataWindow(baseline_data, 200.0, 205.0, "volume"),
        ]

        params = IndicatorParameters({"t1": 30.0, "t2": 0.0, "t3": 600.0, "t4": 30.0})

        result = volume_surge_ratio_algorithm.calculate_from_windows(windows, params)

        assert result is not None
        assert result > 3.0  # Should detect ~5x surge

    def test_normal_volume(self):
        """Test when volume is normal (no surge)."""
        # Both current and baseline have similar volume
        current_data = [(100.0, 2.0), (101.0, 2.0), (102.0, 2.0)]
        baseline_data = [(200.0, 2.0), (201.0, 2.0), (202.0, 2.0)]

        windows = [
            DataWindow(current_data, 100.0, 103.0, "volume"),
            DataWindow(baseline_data, 200.0, 203.0, "volume"),
        ]

        params = IndicatorParameters({"t1": 30.0, "t2": 0.0, "t3": 600.0, "t4": 30.0})

        result = volume_surge_ratio_algorithm.calculate_from_windows(windows, params)

        assert result is not None
        assert 0.8 < result < 1.2  # Should be close to 1.0


class TestPriceVelocity:
    """Test PRICE_VELOCITY indicator."""

    def test_positive_velocity(self):
        """Test positive velocity (price increasing)."""
        # Price increasing from 100 to 110 over time
        current_data = [(100.0, 110.0)]
        baseline_data = [(160.0, 100.0), (145.0, 100.0)]

        windows = [
            DataWindow(current_data, 100.0, 105.0, "price"),
            DataWindow(baseline_data, 160.0, 145.0, "price"),
        ]

        params = IndicatorParameters({"t1": 10.0, "t3": 60.0, "d": 30.0})

        result = price_velocity_algorithm.calculate_from_windows(windows, params)

        assert result is not None
        assert result > 0  # Positive velocity

    def test_negative_velocity(self):
        """Test negative velocity (price decreasing)."""
        # Price decreasing from 100 to 90
        current_data = [(100.0, 90.0)]
        baseline_data = [(160.0, 100.0), (145.0, 100.0)]

        windows = [
            DataWindow(current_data, 100.0, 105.0, "price"),
            DataWindow(baseline_data, 160.0, 145.0, "price"),
        ]

        params = IndicatorParameters({"t1": 10.0, "t3": 60.0, "d": 30.0})

        result = price_velocity_algorithm.calculate_from_windows(windows, params)

        assert result is not None
        assert result < 0  # Negative velocity


class TestVelocityCascade:
    """Test VELOCITY_CASCADE indicator."""

    def test_acceleration_detection(self):
        """Test detection of acceleration (pump gaining speed)."""
        # Create data showing acceleration:
        # Short-term: fast rise
        # Medium-term: moderate rise
        # Long-term: slow rise

        # Ultra-short window: 110 to 115 (fast)
        ultra_short_current = [(5.0, 115.0)]
        ultra_short_baseline = [(15.0, 110.0)]

        # Short window: 105 to 110 (moderate)
        short_current = [(10.0, 110.0)]
        short_baseline = [(40.0, 105.0)]

        # Medium window: 100 to 105 (slow)
        medium_current = [(20.0, 105.0)]
        medium_baseline = [(80.0, 100.0)]

        windows = [
            DataWindow(ultra_short_current, 5.0, 5.0, "price"),
            DataWindow(ultra_short_baseline, 15.0, 15.0, "price"),
            DataWindow(short_current, 10.0, 10.0, "price"),
            DataWindow(short_baseline, 40.0, 40.0, "price"),
            DataWindow(medium_current, 20.0, 20.0, "price"),
            DataWindow(medium_baseline, 80.0, 80.0, "price"),
        ]

        params = IndicatorParameters({
            "windows": [
                {"t1": 5, "t3": 15, "d": 5, "label": "ultra_short"},
                {"t1": 10, "t3": 40, "d": 10, "label": "short"},
                {"t1": 20, "t3": 80, "d": 20, "label": "medium"}
            ]
        })

        result = velocity_cascade_algorithm.calculate_from_windows(windows, params)

        assert result is not None
        # Should detect acceleration (positive cascade index)
        assert result > 0

    def test_deceleration_detection(self):
        """Test detection of deceleration (pump slowing down)."""
        # Create data showing deceleration:
        # Short-term: slow rise
        # Medium-term: moderate rise
        # Long-term: fast rise

        # Ultra-short window: 110 to 111 (slow)
        ultra_short_current = [(5.0, 111.0)]
        ultra_short_baseline = [(15.0, 110.0)]

        # Short window: 105 to 110 (moderate)
        short_current = [(10.0, 110.0)]
        short_baseline = [(40.0, 105.0)]

        # Medium window: 100 to 110 (fast)
        medium_current = [(20.0, 110.0)]
        medium_baseline = [(80.0, 100.0)]

        windows = [
            DataWindow(ultra_short_current, 5.0, 5.0, "price"),
            DataWindow(ultra_short_baseline, 15.0, 15.0, "price"),
            DataWindow(short_current, 10.0, 10.0, "price"),
            DataWindow(short_baseline, 40.0, 40.0, "price"),
            DataWindow(medium_current, 20.0, 20.0, "price"),
            DataWindow(medium_baseline, 80.0, 80.0, "price"),
        ]

        params = IndicatorParameters({
            "windows": [
                {"t1": 5, "t3": 15, "d": 5},
                {"t1": 10, "t3": 40, "d": 10},
                {"t1": 20, "t3": 80, "d": 20}
            ]
        })

        result = velocity_cascade_algorithm.calculate_from_windows(windows, params)

        assert result is not None
        # Should detect deceleration (negative cascade index)
        assert result < 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
