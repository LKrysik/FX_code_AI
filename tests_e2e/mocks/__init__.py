"""
Test mocks for fast unit testing.

These mocks allow tests to run without QuestDB or other heavy dependencies.
"""

from .indicator_engine import create_mock_indicator_engine
from .strategy_manager import create_mock_strategy_manager

__all__ = [
    "create_mock_indicator_engine",
    "create_mock_strategy_manager",
]
