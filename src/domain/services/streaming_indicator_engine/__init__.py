"""
Streaming Indicator Engine - Modular Architecture
==================================================
Refactored from monolithic 5746-line file into maintainable modules.

Public API remains unchanged for backward compatibility.
"""

# ✅ RESTRUCTURED: Import StreamingIndicatorEngine from engine.py inside package
# This avoids circular import caused by package/module name collision
from .engine import StreamingIndicatorEngine

# Import types from refactored module
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
