"""
Indicator Calculator Utilities
==============================
Utility functions for indicator key generation and timestamp normalization.

NOTE: All indicator CALCULATIONS are handled by IndicatorAlgorithmRegistry.
This module only provides utility functions used across the codebase.

MIGRATION (2025-01-21):
- Removed all calculation methods (SMA, EMA, RSI, TWPA, VWAP, etc.)
- Algorithm Registry is now the TRUE single source of truth for calculations
- Both StreamingIndicatorEngine and OfflineIndicatorEngine share the same registry
"""

import json
import hashlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..services.streaming_indicator_engine import IndicatorType


class IndicatorCalculator:
    """
    Utility class for indicator operations.

    NOTE: All indicator calculations are handled by IndicatorAlgorithmRegistry.
    This class only provides utility functions:
    - create_indicator_key(): Generate unique indicator identifiers
    - _normalize_timestamp(): Normalize Unix timestamps to seconds precision
    """

    @staticmethod
    def _normalize_timestamp(timestamp: float) -> float:
        """
        Normalize Unix timestamps to seconds precision.

        Args:
            timestamp: Unix timestamp (can be in seconds or milliseconds)

        Returns:
            Timestamp in seconds
        """
        if timestamp is None:
            return 0.0
        if timestamp > 1e12:
            return float(timestamp) / 1000.0
        return float(timestamp)

    @staticmethod
    def create_indicator_key(symbol: str,
                             indicator_type: 'IndicatorType',
                             period: int,
                             timeframe: str,
                             **kwargs) -> str:
        """
        Create a unique key for an indicator configuration.

        Matches the key generation logic from StreamingIndicatorEngine.

        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")
            indicator_type: Type of indicator (IndicatorType enum)
            period: Period parameter for indicator
            timeframe: Timeframe string (e.g., "1m", "5m")
            **kwargs: Additional parameters for parametric indicators

        Returns:
            Unique indicator key string
        """
        base_key = f"{symbol}_{indicator_type.value}_{period}_{timeframe}"

        # For parametric measures, include parameter fingerprint
        param_measures = {"TWPA", "LAST_PRICE", "FIRST_PRICE", "MAX_PRICE", "MIN_PRICE", "VELOCITY"}
        if indicator_type.value in param_measures and kwargs:
            params_only = {k: v for k, v in kwargs.items() if k not in ["scope"]}
            if params_only:
                fp = hashlib.sha1(
                    json.dumps(params_only, sort_keys=True, separators=(",", ":")).encode("utf-8")
                ).hexdigest()[:8]
                base_key = f"{base_key}_{fp}"

        return base_key
