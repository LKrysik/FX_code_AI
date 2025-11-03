"""
Streaming Indicator Engine - Modular Architecture
==================================================
Refactored from monolithic 5746-line file into maintainable modules.

Public API remains unchanged for backward compatibility.
"""

# ✅ FIX: Import StreamingIndicatorEngine from parent module (still in streaming_indicator_engine.py)
# Using relative import from parent directory
from ..streaming_indicator_engine import StreamingIndicatorEngine

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
