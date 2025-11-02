"""
Market data test fixtures.

Provides sample market data for testing:
- Price ticks
- Order book snapshots
- OHLCV candles
"""

from datetime import datetime, timezone
import pytest


@pytest.fixture
def sample_price_data():
    """Sample price tick data"""
    return {
        'symbol': 'BTC_USDT',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'price': 50000.0,
        'volume': 1.5,
        'quote_volume': 75000.0
    }


@pytest.fixture
def sample_orderbook():
    """Sample order book snapshot"""
    return {
        'symbol': 'BTC_USDT',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'bids': [
            {'price': 49995.0, 'quantity': 1.2},
            {'price': 49990.0, 'quantity': 2.5},
            {'price': 49985.0, 'quantity': 3.0}
        ],
        'asks': [
            {'price': 50005.0, 'quantity': 1.1},
            {'price': 50010.0, 'quantity': 2.3},
            {'price': 50015.0, 'quantity': 2.8}
        ]
    }


@pytest.fixture
def sample_ohlcv():
    """Sample OHLCV candle data"""
    return {
        'symbol': 'BTC_USDT',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'timeframe': '1m',
        'open': 49950.0,
        'high': 50100.0,
        'low': 49900.0,
        'close': 50000.0,
        'volume': 125.5,
        'quote_volume': 6275000.0
    }
