"""
Shared Indicator Types
======================

Common data structures and types used across all indicator engines.
Extracted from UnifiedIndicatorEngine to provide single source of truth.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union, Tuple
from enum import Enum
from pathlib import Path


class IndicatorMode(Enum):
    """Calculation mode for indicators"""
    HISTORICAL = "historical"  # Batch processing of historical data
    LIVE = "live"              # Real-time streaming data processing


class IndicatorCategory(Enum):
    """Indicator category that determines display location"""
    GENERAL = "general"        # Secondary chart (0-1 range)
    RISK = "risk"             # Secondary chart (0-100 range)
    PRICE = "price"           # Main chart (price values)
    STOP_LOSS = "stop_loss"   # Main chart (price values)
    TAKE_PROFIT = "take_profit"  # Main chart (price values)
    CLOSE_ORDER = "close_order"  # Main chart (price values)


@dataclass
class MarketDataPoint:
    """Single market data point"""
    timestamp: float
    symbol: str
    price: float
    volume: float
    bid_prices: Optional[List[float]] = None
    ask_prices: Optional[List[float]] = None
    bid_quantities: Optional[List[float]] = None
    ask_quantities: Optional[List[float]] = None


@dataclass
class IndicatorValue:
    """Calculated indicator value"""
    timestamp: float
    symbol: str
    indicator_id: str
    value: Union[float, Dict[str, float], None]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TimeWindow:
    """Time window configuration for indicators"""
    t1: float  # Start offset in seconds (0 = current time)
    t2: float  # End offset in seconds (0 = current time)
    
    def get_time_range(self, current_time: float) -> Tuple[float, float]:
        """Get actual time range for current timestamp"""
        return (current_time - self.t1, current_time - self.t2)


@dataclass
class IndicatorConfig:
    """Configuration for a single indicator instance"""
    id: str
    variant_id: str
    symbol: str
    base_indicator_type: str
    variant_type: str  # See VariantType enum in streaming_indicator_engine
    parameters: Dict[str, Any]
    time_dependent: bool = False
    update_frequency: float = 1.0  # seconds
    max_data_points: int = 10000
    session_id: str = "default"
    storage_override_path: Optional[Path] = None
    
    @property
    def category(self) -> IndicatorCategory:
        """Get indicator category from variant type"""
        return IndicatorCategory(self.variant_type)


@dataclass
class VariantParameter:
    """
    Parameter definition for indicator variants.

    Located in types module (not streaming_indicator_engine) to avoid circular imports:
    - streaming_indicator_engine imports algorithm classes from indicators/
    - Algorithm classes need VariantParameter for get_parameters() method
    - Both can safely import from this shared types module

    This structure allows algorithm files to define their parameters without
    creating import cycles or using try-except import workarounds.
    """
    name: str
    parameter_type: str  # 'int', 'float', 'string', 'boolean', 'json'
    default_value: Any
    min_value: Any = None
    max_value: Any = None
    allowed_values: List[Any] = None
    is_required: bool = True
    description: str = ""
    validation_rules: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert VariantParameter to dictionary for JSON serialization."""
        import math

        # Helper function to handle inf/nan values
        def sanitize_value(value):
            if isinstance(value, float):
                if math.isinf(value) or math.isnan(value):
                    return None
            return value

        return {
            "name": self.name,
            "parameter_type": self.parameter_type,
            "default_value": sanitize_value(self.default_value),
            "min_value": sanitize_value(self.min_value),
            "max_value": sanitize_value(self.max_value),
            "allowed_values": self.allowed_values,
            "is_required": self.is_required,
            "description": self.description,
            "validation_rules": self.validation_rules
        }


# Export all types for easy importing
__all__ = [
    'IndicatorMode',
    'IndicatorCategory',
    'MarketDataPoint',
    'IndicatorValue',
    'TimeWindow',
    'IndicatorConfig',
    'VariantParameter'
]