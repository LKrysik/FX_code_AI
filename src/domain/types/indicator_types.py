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


# Export all types for easy importing
__all__ = [
    'IndicatorMode',
    'IndicatorCategory', 
    'MarketDataPoint',
    'IndicatorValue',
    'TimeWindow',
    'IndicatorConfig'
]