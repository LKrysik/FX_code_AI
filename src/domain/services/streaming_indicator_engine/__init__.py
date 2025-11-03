"""
Streaming Indicator Engine - Modular Architecture
==================================================
Refactored from monolithic 5746-line file into maintainable modules.

Public API remains unchanged for backward compatibility.
"""

from .core.engine import StreamingIndicatorEngine
from .core.types import (
    IndicatorType,
    VariantType,
    IndicatorValue,
    TimeDrivenSchedule,
    StreamingIndicator,
    IndicatorVariant,
    SystemIndicatorDefinition,
    IndicatorRegistry,
    indicator_registration
)

__all__ = [
    "StreamingIndicatorEngine",
    "IndicatorType",
    "VariantType",
    "IndicatorValue",
    "TimeDrivenSchedule",
    "StreamingIndicator",
    "IndicatorVariant",
    "SystemIndicatorDefinition",
    "IndicatorRegistry",
    "indicator_registration",
]
