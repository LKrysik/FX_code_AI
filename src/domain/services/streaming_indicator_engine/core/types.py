"""
Shared Types for Streaming Indicator Engine
============================================
All data types and enums extracted from monolithic file.

NOTE: IndicatorType and VariantType are now canonically defined in
domain/types/indicator_types.py and re-exported here for backward compatibility.
New code should import directly from domain.types.
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from collections import deque

# Import canonical types from domain/types for backward compatibility
# New code should import directly from domain.types
try:
    from ....types.indicator_types import IndicatorType, VariantType, VariantParameter
except Exception:
    from src.domain.types.indicator_types import IndicatorType, VariantType, VariantParameter


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
