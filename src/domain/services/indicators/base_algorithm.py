"""
Base Algorithm Interface for Indicator Calculations
==================================================
Unified interface for all indicator algorithms with refresh interval control.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Sequence, Tuple, Any
from dataclasses import dataclass


@dataclass(frozen=True)
class DataWindow:
    """
    Immutable data window for indicator calculation.

    Pure data structure with no engine dependencies.
    Thread-safe due to immutability.
    """
    data: Sequence[Tuple[float, float]]  # [(timestamp, price), ...]
    start_ts: float  # Window start timestamp
    end_ts: float    # Window end timestamp

    def __len__(self) -> int:
        """Return number of data points in window."""
        return len(self.data)


@dataclass(frozen=True)
class WindowSpec:
    """
    Specification for a time window.

    Uses the t1/t2 convention where:
    - t1: seconds ago from target timestamp for window start
    - t2: seconds ago from target timestamp for window end

    Example: WindowSpec(300, 0) means "last 5 minutes"
    """
    t1: float  # Seconds ago for window start (further back in time)
    t2: float  # Seconds ago for window end (closer to present)


@dataclass(frozen=True)
class IndicatorParameters:
    """Encapsulate parameters for indicator calculations."""

    params: Dict[str, Any]
    refresh_interval_override: Optional[float] = None
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get parameter value with default."""
        return self.params.get(key, default)
    
    def get_float(self, key: str, default: float) -> float:
        """Get float parameter with validation."""
        value = self.params.get(key, default)
        return float(value) if value is not None else default
    
    def get_refresh_override(self) -> Optional[float]:
        """Get refresh interval override from multiple possible parameter names."""
        return (
            self.refresh_interval_override or
            self.params.get("refresh_interval_seconds") or
            self.params.get("refresh_interval_override") or
            self.params.get("r")  # For convenience in new algorithms
        )


class IndicatorAlgorithm(ABC):
    """
    Base class for all indicator algorithms.
    
    Provides unified interface for:
    - Parameter definitions
    - Refresh interval calculation
    - Value computation
    - Metadata registration
    """
    
    @abstractmethod
    def get_indicator_type(self) -> str:
        """Return unique identifier for this algorithm."""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Return human-readable name."""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Return description of what this indicator calculates."""
        pass
    
    @abstractmethod
    def get_category(self) -> str:
        """Return category for UI grouping."""
        pass
    
    @abstractmethod
    def get_parameters(self) -> List:
        """Return parameter definitions for this algorithm."""
        pass
    
    @abstractmethod
    def calculate(self, 
                 data: Sequence[Tuple[float, float]], 
                 start_ts: float, 
                 end_ts: float, 
                 params: IndicatorParameters) -> Optional[float]:
        """
        Calculate indicator value.
        
        Args:
            data: Sequence of (timestamp, price) tuples in ascending order
            start_ts: Start of evaluation window (epoch seconds)
            end_ts: End of evaluation window (epoch seconds)
            params: Wrapped parameters with convenience methods
            
        Returns:
            Calculated indicator value or None if cannot calculate
        """
        pass
    
    def get_default_refresh_interval(self) -> float:
        """Default refresh interval in seconds if no override specified."""
        return 1.0
    
    def get_min_refresh_interval(self) -> float:
        """Minimum allowed refresh interval in seconds."""
        return 0.5
    
    def get_max_refresh_interval(self) -> float:
        """Maximum allowed refresh interval in seconds."""
        return 3600.0
    
    def calculate_refresh_interval(self, params: IndicatorParameters) -> float:
        """
        Calculate appropriate refresh interval for this algorithm instance.

        Base implementation uses override or default, but algorithms can
        implement custom logic based on their parameters.
        """
        override = params.get_refresh_override()
        if override:
            return max(self.get_min_refresh_interval(),
                      min(self.get_max_refresh_interval(), float(override)))
        return self.get_default_refresh_interval()

    def is_time_driven(self) -> bool:
        """
        Determine if this indicator requires time-driven scheduling.

        Time-driven indicators are recalculated on a regular wall-clock schedule,
        independent of whether new market data arrives. These indicators typically:
        - Use time windows (t1, t2 parameters)
        - Calculate time-weighted metrics (e.g., TWPA, VTWPA)
        - Need consistent sampling intervals

        Event-driven indicators are recalculated only when new market data arrives.
        These indicators typically:
        - Use fixed periods (e.g., SMA, RSI, MACD)
        - Don't depend on wall-clock time
        - Process discrete data points

        Examples:
            Time-driven: TWPA, TWPA_RATIO, VTWPA, VELOCITY, TW_MIDPRICE
            Event-driven: SMA, EMA, RSI, MACD, BOLLINGER_BANDS

        Returns:
            True if indicator requires time-based scheduling
            False if indicator should recalculate on data arrival (default)
        """
        return False  # Safe default: event-driven

    # ========================================
    # NEW PURE FUNCTION INTERFACE (Phase 1)
    # ========================================

    def get_window_specs(self, params: IndicatorParameters) -> List[WindowSpec]:
        """
        Specify what data windows this algorithm needs.

        NEW INTERFACE: Override this in new algorithms.
        Default implementation uses t1/t2 for single window (backward compatible).

        Args:
            params: Algorithm parameters

        Returns:
            List of WindowSpec objects describing needed windows

        Example:
            # Single window (default)
            return [WindowSpec(60, 0)]  # Last 60 seconds

            # Multiple windows (e.g., TWPA Ratio)
            return [
                WindowSpec(60, 0),   # Window 1
                WindowSpec(300, 0),  # Window 2
            ]
        """
        t1 = params.get_float("t1", 60.0)
        t2 = params.get_float("t2", 0.0)
        return [WindowSpec(t1, t2)]

    def calculate_from_windows(self,
                               data_windows: List[DataWindow],
                               params: IndicatorParameters) -> Optional[float]:
        """
        Calculate indicator value from pre-prepared data windows.

        NEW INTERFACE: Override this in new algorithms for pure function implementation.
        Default implementation delegates to old single-window calculate() for backward compatibility.

        This is a PURE FUNCTION:
        - No engine dependency
        - No side effects
        - Easy to test
        - Thread-safe

        Args:
            data_windows: Pre-prepared data windows (engine's responsibility)
            params: Algorithm parameters

        Returns:
            Calculated indicator value or None

        Example:
            def calculate_from_windows(self, data_windows, params):
                window = data_windows[0]
                # Pure calculation logic
                return self._compute_twpa(window.data, window.start_ts, window.end_ts)
        """
        # Default: delegate to old single-window interface for backward compatibility
        if len(data_windows) == 1:
            window = data_windows[0]
            return self.calculate(window.data, window.start_ts, window.end_ts, params)
        elif len(data_windows) == 0:
            return None
        else:
            # Multi-window but algorithm hasn't implemented new interface
            raise NotImplementedError(
                f"{self.__class__.__name__} requires multiple windows but hasn't "
                f"implemented calculate_from_windows(). Please migrate to new interface."
            )

    def get_registry_metadata(self) -> Dict[str, Any]:
        """Return complete metadata for engine registration."""
        return {
            "indicator_type": self.get_indicator_type(),
            "name": self.get_name(),
            "description": self.get_description(),
            "category": self.get_category(),
            "parameters": self.get_parameters(),
            "calculation_function": self._create_engine_hook()
        }
    
    def _create_engine_hook(self):
        """Create hook function for engine integration."""
        def compute_indicator_value(engine, indicator, params):
            """Hook used by the engine registry to calculate values."""
            # Extract window data using engine's method
            # This is algorithm-specific, base implementation for simple cases
            wrapped_params = IndicatorParameters(params)
            
            # Get basic price series (algorithms can override for different data)
            window, start_ts, end_ts = self._get_data_window(engine, indicator, wrapped_params)
            
            return self.calculate(window, start_ts, end_ts, wrapped_params)
        
        return compute_indicator_value
    
    def _get_data_window(self, engine, indicator, params: IndicatorParameters):
        """
        Get data window for calculation. 
        Base implementation for price data - algorithms can override.
        """
        # Default to single window based on t1, t2 parameters
        t1 = params.get_float("t1", 60.0)
        t2 = params.get_float("t2", 0.0)
        
        return engine._get_price_series_for_window(indicator, t1, t2)


class MultiWindowIndicatorAlgorithm(IndicatorAlgorithm):
    """
    Base class for algorithms that need multiple time windows.
    
    Handles the complexity of managing multiple data windows
    for algorithms like TWPA Ratio.
    """
    
    @abstractmethod
    def calculate_multi_window(self, 
                              windows: List[Tuple[Sequence[Tuple[float, float]], float, float]], 
                              params: IndicatorParameters) -> Optional[float]:
        """
        Calculate value using multiple time windows.
        
        Args:
            windows: List of (data, start_ts, end_ts) tuples for each window
            params: Algorithm parameters
            
        Returns:
            Calculated value or None
        """
        pass
    
    def calculate(self, 
                 data: Sequence[Tuple[float, float]], 
                 start_ts: float, 
                 end_ts: float, 
                 params: IndicatorParameters) -> Optional[float]:
        """
        Single window interface - not used for multi-window algorithms.
        This will be called by the engine hook which handles multi-window setup.
        """
        raise NotImplementedError("Multi-window algorithms use calculate_multi_window")
    
    def _create_engine_hook(self):
        """Create specialized hook for multi-window algorithms."""
        def compute_indicator_value(engine, indicator, params):
            """Hook for multi-window calculation."""
            wrapped_params = IndicatorParameters(params)
            windows = self._get_multiple_data_windows(engine, indicator, wrapped_params)
            return self.calculate_multi_window(windows, wrapped_params)
        
        return compute_indicator_value
    
    @abstractmethod
    def _get_multiple_data_windows(self, engine, indicator, params: IndicatorParameters):
        """Get multiple data windows needed for calculation."""
        pass