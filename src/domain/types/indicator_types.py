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


class IndicatorType(Enum):
    """
    Supported indicator types.

    Canonical location: domain/types/indicator_types.py
    This enum defines all indicator types available in the system.
    Moved here from streaming_indicator_engine to enable proper dependency inversion.
    """

    # Basic Market Data
    PRICE = "PRICE"
    VOLUME = "VOLUME"
    BEST_BID = "BEST_BID"
    BEST_ASK = "BEST_ASK"
    BID_QTY = "BID_QTY"
    ASK_QTY = "ASK_QTY"

    # Derived Market Metrics
    SPREAD_PCT = "SPREAD_PCT"
    VOLUME_24H = "VOLUME_24H"
    LIQUIDITY_SCORE = "LIQUIDITY_SCORE"

    # Technical Indicators
    SMA = "SMA"
    EMA = "EMA"
    RSI = "RSI"
    MACD = "MACD"
    BOLLINGER_BANDS = "BOLLINGER_BANDS"

    # Strategy-Specific Indicators
    PUMP_MAGNITUDE_PCT = "PUMP_MAGNITUDE_PCT"
    VOLUME_SURGE_RATIO = "VOLUME_SURGE_RATIO"
    PRICE_VELOCITY = "PRICE_VELOCITY"
    PRICE_MOMENTUM = "PRICE_MOMENTUM"
    BASELINE_PRICE = "BASELINE_PRICE"
    PUMP_PROBABILITY = "PUMP_PROBABILITY"

    # Signal Timing Indicators
    SIGNAL_AGE_SECONDS = "SIGNAL_AGE_SECONDS"

    # Risk Assessment Metrics
    CONFIDENCE_SCORE = "CONFIDENCE_SCORE"
    RISK_LEVEL = "RISK_LEVEL"
    VOLATILITY = "VOLATILITY"
    MARKET_STRESS_INDICATOR = "MARKET_STRESS_INDICATOR"

    # Position-Related Metrics
    POSITION_RISK_SCORE = "POSITION_RISK_SCORE"
    PORTFOLIO_EXPOSURE_PCT = "PORTFOLIO_EXPOSURE_PCT"
    UNREALIZED_PNL_PCT = "UNREALIZED_PNL_PCT"

    # Close Order Price Indicators
    CLOSE_ORDER_PRICE = "CLOSE_ORDER_PRICE"

    # Parametric, Windowed Measures
    TWPA = "TWPA"
    TWPA_RATIO = "TWPA_RATIO"
    LAST_PRICE = "LAST_PRICE"
    FIRST_PRICE = "FIRST_PRICE"
    MAX_PRICE = "MAX_PRICE"
    MIN_PRICE = "MIN_PRICE"
    VELOCITY = "VELOCITY"
    VOLUME_SURGE = "VOLUME_SURGE"

    # Orderbook Time-Weighted Measures
    AVG_BEST_BID = "AVG_BEST_BID"
    AVG_BEST_ASK = "AVG_BEST_ASK"
    AVG_BID_QTY = "AVG_BID_QTY"
    AVG_ASK_QTY = "AVG_ASK_QTY"
    TW_MIDPRICE = "TW_MIDPRICE"

    # Volume/Deals Based Measures
    SUM_VOLUME = "SUM_VOLUME"
    AVG_VOLUME = "AVG_VOLUME"
    COUNT_DEALS = "COUNT_DEALS"
    VWAP = "VWAP"
    VOLUME_CONCENTRATION = "VOLUME_CONCENTRATION"
    VOLUME_ACCELERATION = "VOLUME_ACCELERATION"
    TRADE_FREQUENCY = "TRADE_FREQUENCY"
    AVERAGE_TRADE_SIZE = "AVERAGE_TRADE_SIZE"
    BID_ASK_IMBALANCE = "BID_ASK_IMBALANCE"
    SPREAD_PERCENTAGE = "SPREAD_PERCENTAGE"
    SPREAD_VOLATILITY = "SPREAD_VOLATILITY"
    VOLUME_PRICE_CORRELATION = "VOLUME_PRICE_CORRELATION"

    # Phase 2: Priority 1 Foundation Indicators
    MAX_TWPA = "MAX_TWPA"
    MIN_TWPA = "MIN_TWPA"
    VTWPA = "VTWPA"
    VELOCITY_CASCADE = "VELOCITY_CASCADE"
    VELOCITY_ACCELERATION = "VELOCITY_ACCELERATION"
    MOMENTUM_REVERSAL_INDEX = "MOMENTUM_REVERSAL_INDEX"
    DUMP_EXHAUSTION_SCORE = "DUMP_EXHAUSTION_SCORE"
    SUPPORT_LEVEL_PROXIMITY = "SUPPORT_LEVEL_PROXIMITY"
    VELOCITY_STABILIZATION_INDEX = "VELOCITY_STABILIZATION_INDEX"
    MOMENTUM_STREAK = "MOMENTUM_STREAK"
    DIRECTION_CONSISTENCY = "DIRECTION_CONSISTENCY"

    # Phase 3: Priority 2 Core Features Indicators
    TRADE_SIZE_MOMENTUM = "TRADE_SIZE_MOMENTUM"
    MID_PRICE_VELOCITY = "MID_PRICE_VELOCITY"
    TOTAL_LIQUIDITY = "TOTAL_LIQUIDITY"
    LIQUIDITY_RATIO = "LIQUIDITY_RATIO"
    LIQUIDITY_DRAIN_INDEX = "LIQUIDITY_DRAIN_INDEX"
    DEAL_VS_MID_DEVIATION = "DEAL_VS_MID_DEVIATION"
    INTER_DEAL_INTERVALS = "INTER_DEAL_INTERVALS"
    DECISION_DENSITY_ACCELERATION = "DECISION_DENSITY_ACCELERATION"
    TRADE_CLUSTERING_COEFFICIENT = "TRADE_CLUSTERING_COEFFICIENT"
    PRICE_VOLATILITY = "PRICE_VOLATILITY"
    DEAL_SIZE_VOLATILITY = "DEAL_SIZE_VOLATILITY"


class VariantType(Enum):
    """
    Supported variant types for indicator categorization and UI grouping.

    Canonical location: domain/types/indicator_types.py
    Moved here from streaming_indicator_engine to enable proper dependency inversion.
    """

    GENERAL = "general"
    RISK = "risk"
    PRICE = "price"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    CLOSE_ORDER = "close_order"

    @classmethod
    def get_valid_types(cls) -> List[str]:
        """Get list of valid variant type strings for validation"""
        return [variant.value for variant in cls]

    @classmethod
    def get_main_chart_types(cls) -> List[str]:
        """Get variant types that should be displayed on main chart"""
        return [cls.PRICE.value, cls.STOP_LOSS.value, cls.TAKE_PROFIT.value, cls.CLOSE_ORDER.value]

    @classmethod
    def get_secondary_chart_types(cls) -> List[str]:
        """Get variant types that should be displayed on secondary chart"""
        return [cls.GENERAL.value, cls.RISK.value]


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
    variant_type: str  # See VariantType enum in this module
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
    'IndicatorType',
    'VariantType',
    'MarketDataPoint',
    'IndicatorValue',
    'TimeWindow',
    'IndicatorConfig',
    'VariantParameter'
]