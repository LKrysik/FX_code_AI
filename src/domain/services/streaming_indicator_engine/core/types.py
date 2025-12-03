"""
Shared Types for Streaming Indicator Engine
============================================
All data types and enums extracted from monolithic file.
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from collections import deque

try:
    from ....domain.types.indicator_types import VariantParameter
except Exception:
    from src.domain.types.indicator_types import VariantParameter


class IndicatorType(Enum):
    """Supported indicator types"""

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
    SIGNAL_AGE_SECONDS = "SIGNAL_AGE_SECONDS"  # Time since signal was detected (for O1 cancellation)

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
    """Supported variant types for indicator categorization and UI grouping"""

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
class IndicatorValue:
    """Single indicator value"""
    timestamp: float
    value: float
    metadata: Dict[str, Any] = None


@dataclass
class TimeDrivenSchedule:
    """Track refresh cadence for time-driven indicators with algorithm support."""
    indicator_key: str
    interval: float
    cache_bucket: int
    next_run: float
    indicator_type: str
    calculation_function: Optional[Callable] = None
    algorithm_instance: Optional[Any] = None


@dataclass
class StreamingIndicator:
    """Streaming indicator data structure"""
    symbol: str
    indicator: str
    timeframe: str
    current_value: float
    timestamp: float
    series: deque
    metadata: Dict[str, Any]


@dataclass
class IndicatorVariant:
    """Indicator variant with parameterized configuration"""
    id: str
    name: str
    base_indicator_type: str
    variant_type: str
    description: str
    parameters: Dict[str, Any]
    is_system: bool
    created_by: str
    created_at: float
    updated_at: float


@dataclass
class SystemIndicatorDefinition:
    """Definition for a system indicator with metadata"""
    indicator_type: str
    name: str
    description: str
    category: str
    parameters: List[VariantParameter]
    calculation_function: Optional[Callable] = None
    is_implemented: bool = True


class IndicatorRegistry:
    """Registry for system indicators with metadata and calculation functions"""

    def __init__(self):
        self._indicators: Dict[str, SystemIndicatorDefinition] = {}

    def register(self,
                 indicator_type: str,
                 name: str,
                 description: str,
                 category: str,
                 parameters: List[VariantParameter],
                 calculation_function: Callable = None) -> None:
        """Register a system indicator with metadata"""
        definition = SystemIndicatorDefinition(
            indicator_type=indicator_type,
            name=name,
            description=description,
            category=category,
            parameters=parameters,
            calculation_function=calculation_function,
            is_implemented=calculation_function is not None
        )
        self._indicators[indicator_type] = definition

    def get_indicator(self, indicator_type: str) -> Optional[SystemIndicatorDefinition]:
        """Get indicator definition by type"""
        return self._indicators.get(indicator_type)

    def get_all_indicators(self) -> Dict[str, SystemIndicatorDefinition]:
        """Get all registered indicators"""
        return self._indicators.copy()

    def get_indicators_by_category(self, category: str) -> Dict[str, SystemIndicatorDefinition]:
        """Get indicators filtered by category"""
        return {
            k: v for k, v in self._indicators.items()
            if v.category == category
        }

    def get_categories(self) -> List[str]:
        """Get all available categories"""
        return list(set(indicator.category for indicator in self._indicators.values()))


def indicator_registration(indicator_type: str,
                          name: str,
                          description: str,
                          category: str,
                          parameters: List[VariantParameter]):
    """Decorator for registering indicator calculation functions"""
    def decorator(func: Callable):
        func._indicator_metadata = {
            'indicator_type': indicator_type,
            'name': name,
            'description': description,
            'category': category,
            'parameters': parameters
        }
        return func
    return decorator
