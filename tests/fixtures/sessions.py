"""
Session test fixtures.

Provides sample session data for testing:
- Data collection sessions
- Backtest sessions
- Live trading sessions
"""

from datetime import datetime, timezone
import pytest
import uuid


@pytest.fixture
def sample_session():
    """Sample data collection session"""
    return {
        'session_id': str(uuid.uuid4()),
        'symbols': ['BTC_USDT', 'ETH_USDT'],
        'data_types': ['prices', 'orderbook'],
        'status': 'running',
        'start_time': datetime.now(timezone.utc).isoformat(),
        'records_collected': 0
    }


@pytest.fixture
def sample_session_config():
    """Sample session configuration"""
    return {
        'symbols': ['BTC_USDT'],
        'data_types': ['prices', 'orderbook', 'trades'],
        'collection_interval_ms': 1000,
        'max_duration_minutes': 60,
        'save_to_database': True,
        'save_to_csv': False
    }
