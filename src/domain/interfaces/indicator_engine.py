"""
Indicator Engine Interface
==========================
Abstract interface for indicator calculation engines.
Supports multiple modes: streaming (real-time), offline (historical), backtest.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from enum import Enum

from ..types import IndicatorType


class EngineMode(Enum):
    """Indicator engine operation modes."""
    STREAMING = "streaming"  # Real-time WebSocket data
    OFFLINE = "offline"      # Historical CSV data
    BACKTEST = "backtest"    # Backtest simulation


class IIndicatorEngine(ABC):
    """
    Abstract interface for indicator calculation engines.
    
    Enables polymorphic usage across different execution contexts:
    - StreamingIndicatorEngine: Real-time trading
    - OfflineIndicatorEngine: Historical analysis and backtesting
    """
    
    @property
    @abstractmethod
    def mode(self) -> EngineMode:
        """Get the engine's operation mode."""
        pass
    
    @abstractmethod
    def add_indicator(self,
                     symbol: str,
                     indicator_type: IndicatorType,
                     timeframe: str = "1m",
                     period: int = 20,
                     scope: Optional[str] = None,
                     **kwargs) -> str:
        """
        Add an indicator for calculation.
        
        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")
            indicator_type: Type of indicator to calculate
            timeframe: Time interval for calculations
            period: Calculation period (if applicable)
            scope: Context scope (e.g., "chart", "trading")
            **kwargs: Additional parameters (e.g., t1, t2 for TWPA)
            
        Returns:
            str: Unique identifier for the indicator
        """
        pass
    
    @abstractmethod
    def remove_indicator(self, indicator_key: str) -> bool:
        """
        Remove an indicator.
        
        Args:
            indicator_key: Unique identifier returned by add_indicator
            
        Returns:
            bool: True if removed successfully
        """
        pass
    
    @abstractmethod
    def get_indicator_value(self, indicator_key: str) -> Optional[Dict[str, Any]]:
        """
        Get current value of an indicator.
        
        Args:
            indicator_key: Unique identifier for the indicator
            
        Returns:
            Dict containing current value and metadata, or None if not found
        """
        pass
    
    @abstractmethod
    def get_indicators_for_symbol(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Get all indicators for a specific symbol.
        
        Args:
            symbol: Trading symbol to query
            
        Returns:
            List of indicator configurations and current values
        """
        pass
    
    @abstractmethod
    def calculate_for_data(self, symbol: str, data: List[Dict[str, Any]]) -> Dict[str, List[float]]:
        """
        Calculate indicator values for provided data points.
        
        Args:
            symbol: Trading symbol
            data: List of price/volume data points
            
        Returns:
            Dict mapping indicator keys to calculated value arrays
        """
        pass
    
    @abstractmethod
    def get_all_indicators(self) -> List[Dict[str, Any]]:
        """
        Get all active indicators across all symbols.
        
        Returns:
            List of all indicator configurations and states
        """
        pass