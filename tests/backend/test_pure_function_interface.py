"""
Unit tests for pure function interface in indicator algorithms.

Tests the new calculate_from_windows() and get_window_specs() methods.
"""

import pytest
from src.domain.services.indicators.twpa_ratio import twpa_ratio_algorithm
from src.domain.services.indicators.base_algorithm import (
    IndicatorParameters,
    DataWindow,
    WindowSpec
)


class TestWindowSpec:
    """Test WindowSpec dataclass."""

    def test_window_spec_creation(self):
        """Test creating WindowSpec."""
        spec = WindowSpec(300.0, 60.0)
        assert spec.t1 == 300.0
        assert spec.t2 == 60.0

    def test_window_spec_immutable(self):
        """Test that WindowSpec is immutable."""
        spec = WindowSpec(300.0, 60.0)
        with pytest.raises(AttributeError):
            spec.t1 = 100.0


class TestDataWindow:
    """Test DataWindow dataclass."""

    def test_data_window_creation(self):
        """Test creating DataWindow."""
        data = [(100.0, 1.0), (110.0, 2.0)]
        window = DataWindow(data=data, start_ts=100.0, end_ts=120.0)

        assert len(window) == 2
        assert window.start_ts == 100.0
        assert window.end_ts == 120.0
        assert window.data == data

    def test_data_window_immutable(self):
        """Test that DataWindow is immutable."""
        data = [(100.0, 1.0)]
        window = DataWindow(data=data, start_ts=100.0, end_ts=120.0)

        with pytest.raises(AttributeError):
            window.start_ts = 200.0


class TestTWPARatioNewInterface:
    """Test TWPA Ratio pure function interface."""

    def test_get_window_specs(self):
        """Test that get_window_specs returns correct specs."""
        params = IndicatorParameters({
            't1': 60.0,
            't2': 0.0,
            't3': 300.0,
            't4': 0.0
        })

        specs = twpa_ratio_algorithm.get_window_specs(params)

        assert len(specs) == 2
        assert specs[0].t1 == 60.0
        assert specs[0].t2 == 0.0
        assert specs[1].t1 == 300.0
        assert specs[1].t2 == 0.0

    def test_get_window_specs_defaults(self):
        """Test get_window_specs with default parameters."""
        params = IndicatorParameters({})

        specs = twpa_ratio_algorithm.get_window_specs(params)

        assert len(specs) == 2
        assert specs[0].t1 == 300.0  # Default t1
        assert specs[0].t2 == 60.0   # Default t2
        assert specs[1].t1 == 1800.0 # Default t3
        assert specs[1].t2 == 300.0  # Default t4

    def test_calculate_from_windows_basic(self):
        """Test calculate_from_windows with basic data."""
        # Window 1: price 2.0
        window1 = DataWindow(
            data=[(100.0, 2.0), (110.0, 2.0)],
            start_ts=100.0,
            end_ts=120.0
        )

        # Window 2: price 1.0
        window2 = DataWindow(
            data=[(80.0, 1.0), (90.0, 1.0)],
            start_ts=80.0,
            end_ts=100.0
        )

        params = IndicatorParameters({})
        result = twpa_ratio_algorithm.calculate_from_windows([window1, window2], params)

        # TWPA1 / TWPA2 = 2.0 / 1.0 = 2.0
        assert result is not None
        assert result == pytest.approx(2.0, rel=1e-6)

    def test_calculate_from_windows_none_when_empty(self):
        """Test that calculate_from_windows returns None with empty windows."""
        window1 = DataWindow(data=[], start_ts=100.0, end_ts=120.0)
        window2 = DataWindow(data=[], start_ts=80.0, end_ts=100.0)

        params = IndicatorParameters({})
        result = twpa_ratio_algorithm.calculate_from_windows([window1, window2], params)

        assert result is None

    def test_calculate_from_windows_wrong_count(self):
        """Test that calculate_from_windows returns None with wrong window count."""
        window1 = DataWindow(data=[(100.0, 1.0)], start_ts=100.0, end_ts=120.0)

        params = IndicatorParameters({})
        result = twpa_ratio_algorithm.calculate_from_windows([window1], params)

        assert result is None

    def test_calculate_from_windows_division_by_zero_protection(self):
        """Test division by zero protection."""
        # Window 1: price 1.0
        window1 = DataWindow(
            data=[(100.0, 1.0)],
            start_ts=100.0,
            end_ts=120.0
        )

        # Window 2: price very small (below min_denominator)
        window2 = DataWindow(
            data=[(80.0, 0.0001)],
            start_ts=80.0,
            end_ts=100.0
        )

        params = IndicatorParameters({'min_denominator': 0.001})
        result = twpa_ratio_algorithm.calculate_from_windows([window1, window2], params)

        # Should return None due to division protection
        assert result is None


class TestBackwardCompatibility:
    """Test that old interface still works."""

    def test_old_calculate_multi_window_still_works(self):
        """Test that calculate_multi_window (old interface) still works."""
        windows = [
            ([(100.0, 2.0), (110.0, 2.0)], 100.0, 120.0),
            ([(80.0, 1.0), (90.0, 1.0)], 80.0, 100.0)
        ]

        params = IndicatorParameters({})
        result = twpa_ratio_algorithm.calculate_multi_window(windows, params)

        assert result is not None
        assert result == pytest.approx(2.0, rel=1e-6)
