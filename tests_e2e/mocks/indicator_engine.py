"""Mock for StreamingIndicatorEngine."""

from unittest.mock import AsyncMock, MagicMock


def create_mock_indicator_engine():
    """
    Create mock StreamingIndicatorEngine for tests.

    Returns mock with realistic return values.
    """
    from src.domain.services.streaming_indicator_engine.engine import StreamingIndicatorEngine

    mock = MagicMock(spec=StreamingIndicatorEngine)

    # Mock async methods
    mock.start = AsyncMock()
    mock.stop = AsyncMock()
    mock.create_variant = AsyncMock(return_value="variant_id_12345")
    mock.delete_variant = AsyncMock()
    mock.get_variant = AsyncMock(return_value={
        "id": "variant_id_12345",
        "name": "TWPA_5min",
        "base_indicator_type": "TWPA",
        "variant_type": "price",
        "parameters": {"t1": 300, "t2": 0},
        "created_by": "test_user"
    })
    mock.get_indicators = AsyncMock(return_value={
        "BTC_USDT": {
            "TWPA_5min": {
                "value": 50000.0,
                "timestamp": "2025-11-12T10:00:00Z",
                "confidence": 1.0
            }
        }
    })
    mock.process_market_data = AsyncMock()

    return mock
