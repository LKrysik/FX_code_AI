"""
Comprehensive tests for TWPA (Time-Weighted Price Average) algorithm.

These tests verify that TWPA correctly implements the specification:
1. ALWAYS takes one transaction before the window
2. Handles empty windows correctly
3. Calculates time-weighted averages accurately
"""

import pytest
from src.domain.services.indicators.twpa import twpa_algorithm


class TestTWPAAlgorithm:
    """Test suite for TWPAAlgorithm._compute_twpa()"""

    def test_twpa_includes_transaction_before_window(self):
        """
        CRITICAL TEST: Verify TWPA uses transaction before window.

        Example:
            Data: [(50, 1.00), (110, 2.00), (130, 3.00)]
            Window: [100, 120]

            Expected calculation:
            - From t=100 to t=110: price 1.00 (from point before window)
            - From t=110 to t=120: price 2.00
            - TWPA = (1.00*10 + 2.00*10) / 20 = 1.50
        """
        # Data with transaction before window
        window_data = [
            (50.0, 1.00),   # Before window - this MUST be included
            (110.0, 2.00),  # In window
        ]

        # Window: [100, 120]
        start_ts = 100.0
        end_ts = 120.0

        result = twpa_algorithm._compute_twpa(window_data, start_ts, end_ts)

        # Manual calculation:
        # Point 50 (price 1.00): from max(50,100)=100 to min(110,120)=110 = 10s
        # Point 110 (price 2.00): from max(110,100)=110 to 120 = 10s
        # TWPA = (1.00*10 + 2.00*10) / 20 = 30/20 = 1.50
        expected = 1.50

        assert result is not None, "TWPA should return a value"
        assert result == pytest.approx(expected, rel=1e-9), \
            f"Expected {expected}, got {result}"

    def test_twpa_with_no_transactions_in_window(self):
        """
        Test when window is empty but there's a transaction before it.

        Example:
            Data: [(50, 1.00)]
            Window: [100, 120]

            Expected: Price 1.00 applies for entire window (20 seconds)
        """
        # Only transaction before window
        window_data = [
            (50.0, 1.00),  # Before window
        ]

        # Window: [100, 120] - empty
        start_ts = 100.0
        end_ts = 120.0

        result = twpa_algorithm._compute_twpa(window_data, start_ts, end_ts)

        # Price 1.00 from max(50,100)=100 to 120 = 20s
        # TWPA = 1.00*20 / 20 = 1.00
        expected = 1.00

        assert result is not None
        assert result == pytest.approx(expected, rel=1e-9)

    def test_twpa_multiple_prices_in_window(self):
        """
        Test TWPA with multiple price changes in window.

        Example:
            Data: [(90, 1.00), (110, 2.00), (115, 3.00), (130, 4.00)]
            Window: [100, 120]

            Calculation:
            - t=100-110: price 1.00 (10s)
            - t=110-115: price 2.00 (5s)
            - t=115-120: price 3.00 (5s)
            TWPA = (1.00*10 + 2.00*5 + 3.00*5) / 20 = 35/20 = 1.75
        """
        window_data = [
            (90.0, 1.00),   # Before window
            (110.0, 2.00),  # In window
            (115.0, 3.00),  # In window
        ]

        start_ts = 100.0
        end_ts = 120.0

        result = twpa_algorithm._compute_twpa(window_data, start_ts, end_ts)

        # Manual calculation:
        # 90 -> max(90,100)=100 to min(110,120)=110 = 10s @ 1.00
        # 110 -> max(110,100)=110 to min(115,120)=115 = 5s @ 2.00
        # 115 -> max(115,100)=115 to 120 (end) = 5s @ 3.00
        # TWPA = (1.00*10 + 2.00*5 + 3.00*5) / 20 = 35/20 = 1.75
        expected = 1.75

        assert result is not None
        assert result == pytest.approx(expected, rel=1e-9)

    def test_twpa_window_start_equals_transaction_time(self):
        """
        Test edge case where window starts exactly at transaction time.

        Example:
            Data: [(100, 1.00), (110, 2.00)]
            Window: [100, 120]
        """
        window_data = [
            (100.0, 1.00),  # Exactly at window start
            (110.0, 2.00),
        ]

        start_ts = 100.0
        end_ts = 120.0

        result = twpa_algorithm._compute_twpa(window_data, start_ts, end_ts)

        # 100 -> max(100,100)=100 to min(110,120)=110 = 10s @ 1.00
        # 110 -> max(110,100)=110 to 120 = 10s @ 2.00
        # TWPA = (1.00*10 + 2.00*10) / 20 = 1.50
        expected = 1.50

        assert result is not None
        assert result == pytest.approx(expected, rel=1e-9)

    def test_twpa_all_transactions_after_window(self):
        """
        Test edge case where all transactions are after the window.
        Should return None (no data in window).
        """
        window_data = [
            (150.0, 1.00),
            (160.0, 2.00),
        ]

        start_ts = 100.0
        end_ts = 120.0

        result = twpa_algorithm._compute_twpa(window_data, start_ts, end_ts)

        # No points contribute to the window
        assert result is None, "Should return None when no data in window"

    def test_twpa_single_price_entire_window(self):
        """
        Test when single price is valid for entire window.

        Example:
            Data: [(50, 1.00), (150, 2.00)]
            Window: [100, 120]

            Price 1.00 is valid from 50 to 150, so entire window has price 1.00
        """
        window_data = [
            (50.0, 1.00),   # Before window
        ]

        start_ts = 100.0
        end_ts = 120.0

        result = twpa_algorithm._compute_twpa(window_data, start_ts, end_ts)

        # Single price for 20 seconds
        expected = 1.00

        assert result is not None
        assert result == pytest.approx(expected, rel=1e-9)

    def test_twpa_empty_data(self):
        """Test that empty data returns None."""
        window_data = []
        start_ts = 100.0
        end_ts = 120.0

        result = twpa_algorithm._compute_twpa(window_data, start_ts, end_ts)

        assert result is None, "Empty data should return None"

    def test_twpa_very_short_durations(self):
        """
        Test TWPA with sub-second price changes.

        Verifies precision for high-frequency data.
        """
        window_data = [
            (100.0, 1.00),
            (100.1, 2.00),
            (100.2, 3.00),
            (100.3, 4.00),
        ]

        start_ts = 100.0
        end_ts = 100.5

        result = twpa_algorithm._compute_twpa(window_data, start_ts, end_ts)

        # Calculation:
        # 100.0-100.1: 0.1s @ 1.00
        # 100.1-100.2: 0.1s @ 2.00
        # 100.2-100.3: 0.1s @ 3.00
        # 100.3-100.5: 0.2s @ 4.00
        # TWPA = (1*0.1 + 2*0.1 + 3*0.1 + 4*0.2) / 0.5 = 1.4/0.5 = 2.8
        expected = 2.8

        assert result is not None
        assert result == pytest.approx(expected, rel=1e-6)

    def test_twpa_realistic_trading_scenario(self):
        """
        Test with realistic trading data from the specification example.

        From specification:
            timestamp,price,volume,quote_volume
            1759841342.46,0.1064,92,9.7888
            1759841353.46,0.1065,128,13.632
            1759841368.46,0.1064,102,10.8528
        """
        # Simulate 30-second window from latest timestamp
        latest_ts = 1759841368.46
        window_data = [
            (1759841342.46, 0.1064),  # 26s before latest
            (1759841353.46, 0.1065),  # 15s before latest
            (1759841368.46, 0.1064),  # latest
        ]

        # Window: last 20 seconds (from -20s to now)
        start_ts = latest_ts - 20.0  # 1759841348.46
        end_ts = latest_ts            # 1759841368.46

        result = twpa_algorithm._compute_twpa(window_data, start_ts, end_ts)

        # Manual calculation:
        # Point 1759841342.46 (before window, price 0.1064):
        #   max(1759841342.46, 1759841348.46) = 1759841348.46
        #   min(1759841353.46, 1759841368.46) = 1759841353.46
        #   Duration: 5s @ 0.1064
        #
        # Point 1759841353.46 (in window, price 0.1065):
        #   max(1759841353.46, 1759841348.46) = 1759841353.46
        #   min(1759841368.46, 1759841368.46) = 1759841368.46
        #   Duration: 15s @ 0.1065
        #
        # Point 1759841368.46 (end of window, price 0.1064):
        #   max(1759841368.46, 1759841348.46) = 1759841368.46
        #   end_ts = 1759841368.46
        #   Duration: 0s (doesn't contribute)
        #
        # TWPA = (0.1064*5 + 0.1065*15) / 20
        #      = (0.532 + 1.5975) / 20
        #      = 2.1295 / 20
        #      = 0.106475

        expected = (0.1064 * 5 + 0.1065 * 15) / 20

        assert result is not None
        assert result == pytest.approx(expected, rel=1e-6)


class TestTWPACalculateMethod:
    """Test the public calculate() interface of TWPAAlgorithm."""

    def test_calculate_interface(self):
        """Test that calculate() method works correctly."""
        from src.domain.services.indicators.base_algorithm import IndicatorParameters

        window_data = [
            (50.0, 1.00),
            (110.0, 2.00),
        ]
        start_ts = 100.0
        end_ts = 120.0
        params = IndicatorParameters({"t1": 20.0, "t2": 0.0})

        result = twpa_algorithm.calculate(window_data, start_ts, end_ts, params)

        expected = 1.50
        assert result is not None
        assert result == pytest.approx(expected, rel=1e-9)
