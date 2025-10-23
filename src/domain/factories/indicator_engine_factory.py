"""
Indicator Engine Factory
========================
Factory for creating appropriate indicator engines based on execution mode.
Enhanced with caching for improved performance and resource management.
"""

from typing import Optional, Dict
from enum import Enum

from ..interfaces.indicator_engine import IIndicatorEngine, EngineMode
from ..services.streaming_indicator_engine import StreamingIndicatorEngine
from ..services.offline_indicator_engine import OfflineIndicatorEngine
from ...core.event_bus import EventBus
from ...core.logger import StructuredLogger, get_logger


class ExecutionMode(Enum):
    """System execution modes."""
    LIVE = "live"           # Real-time trading
    BACKTEST = "backtest"   # Backtesting simulation
    HISTORICAL = "historical"  # Historical analysis


class IndicatorEngineFactory:
    """
    Factory for creating indicator engines based on execution context.
    Features:
    - Instance caching for improved performance
    - Proper resource management with weak references
    - Direct engine creation without adapter layer
    """
    
    # Class-level cache for engine instances
    _engine_cache: Dict[str, IIndicatorEngine] = {}
    
    @staticmethod
    def create_engine(mode: ExecutionMode, 
                     event_bus: Optional[EventBus] = None,
                     data_path: Optional[str] = None,
                     logger: Optional[StructuredLogger] = None,
                     use_cache: bool = True) -> IIndicatorEngine:
        """
        Create appropriate indicator engine for the given mode.
        
        Args:
            mode: Execution mode (live, backtest, historical)
            event_bus: Event bus for streaming engine (required for live mode)
            data_path: Data path for offline engine (used for backtest/historical)
            logger: Logger instance (optional, will create default if not provided)
            use_cache: Whether to use cached instances (default: True)
            
        Returns:
            IIndicatorEngine: Appropriate engine instance
            
        Raises:
            ValueError: If required parameters are missing for the mode
        """
        # Generate cache key based on mode and parameters
        cache_key = IndicatorEngineFactory._generate_cache_key(mode, data_path)
        
        # Return cached instance if available and caching enabled
        if use_cache and cache_key in IndicatorEngineFactory._engine_cache:
            return IndicatorEngineFactory._engine_cache[cache_key]
        
        # Create new engine instance
        engine = IndicatorEngineFactory._create_engine_instance(mode, event_bus, data_path, logger)
        
        # Cache the instance if caching is enabled
        if use_cache:
            IndicatorEngineFactory._engine_cache[cache_key] = engine
            
        return engine
    
    @staticmethod
    def _create_engine_instance(mode: ExecutionMode,
                              event_bus: Optional[EventBus],
                              data_path: Optional[str],
                              logger: Optional[StructuredLogger]) -> IIndicatorEngine:
        """Create engine instance without caching logic."""
        if mode == ExecutionMode.LIVE:
            if not event_bus:
                raise ValueError("EventBus is required for live mode")
            if not logger:
                logger = get_logger("streaming_indicator_engine")
            
            # Direct return of StreamingIndicatorEngine - adapter pattern removed
            streaming_engine = StreamingIndicatorEngine(event_bus, logger)
            return streaming_engine
            
        elif mode in [ExecutionMode.BACKTEST, ExecutionMode.HISTORICAL]:
            data_path = data_path or "data"
            return OfflineIndicatorEngine(data_path)
            
        else:
            raise ValueError(f"Unsupported execution mode: {mode}")
    
    @staticmethod
    def _generate_cache_key(mode: ExecutionMode, data_path: Optional[str] = None) -> str:
        """Generate cache key for engine instances."""
        if mode == ExecutionMode.LIVE:
            return f"live"
        else:
            # Include data_path in key for offline engines
            path_key = data_path or "default"
            return f"{mode.value}_{path_key}"
    
    @staticmethod
    def clear_cache():
        """Clear the engine cache. Useful for testing and cleanup."""
        IndicatorEngineFactory._engine_cache.clear()
    
    @staticmethod
    def get_cache_info() -> Dict[str, int]:
        """Get information about cached engines."""
        return {
            "cached_engines": len(IndicatorEngineFactory._engine_cache),
            "cache_keys": list(IndicatorEngineFactory._engine_cache.keys())
        }
    
    @staticmethod
    def get_engine_mode(engine: IIndicatorEngine) -> EngineMode:
        """Get the mode of an existing engine."""
        return engine.mode