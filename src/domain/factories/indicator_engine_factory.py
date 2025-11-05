"""
Indicator Engine Factory
========================
⚠️ DEPRECATED: Use Container.create_streaming_indicator_engine() instead.

This factory creates indicator engines WITHOUT variant_repository, which means:
- Variants cannot be persisted to QuestDB
- No shared algorithm registry with repository
- Inconsistent configuration across components

For production use, inject engine via Container:
    engine = await container.create_streaming_indicator_engine()

This factory is kept ONLY for backward compatibility with legacy tests.
Will be removed in future versions.
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
    ⚠️ DEPRECATED: Use Container instead for proper dependency injection.

    This factory creates incomplete engine instances without variant_repository.

    Legacy factory kept for backward compatibility. New code should use:
        container.create_streaming_indicator_engine()  # ✅ CORRECT

    Issues with this factory:
    - No variant persistence (variant_repository=None)
    - Duplicate algorithm registry creation
    - Cannot share state with API layer
    """
    
    # Class-level cache for engine instances
    _engine_cache: Dict[str, IIndicatorEngine] = {}
    
    @staticmethod
    def create_engine(mode: ExecutionMode,
                     event_bus: Optional[EventBus] = None,
                     logger: Optional[StructuredLogger] = None,
                     use_cache: bool = True) -> IIndicatorEngine:
        """
        ⚠️ DEPRECATED: Use Container.create_streaming_indicator_engine() instead.

        Creates indicator engine WITHOUT variant_repository (incomplete configuration).

        For production code, use proper DI:
            engine = await container.create_streaming_indicator_engine()

        Args:
            mode: Execution mode (live, backtest, historical)
            event_bus: Event bus for streaming engine (required for live mode)
            logger: Logger instance (optional, will create default if not provided)
            use_cache: Whether to use cached instances (default: True)

        Returns:
            IIndicatorEngine: Incomplete engine instance (no variant persistence)

        Raises:
            ValueError: If required parameters are missing for the mode
        """
        import warnings
        warnings.warn(
            "IndicatorEngineFactory is deprecated. Use Container.create_streaming_indicator_engine() instead.",
            DeprecationWarning,
            stacklevel=2
        )
        # Generate cache key based on mode only
        cache_key = IndicatorEngineFactory._generate_cache_key(mode)

        # Return cached instance if available and caching enabled
        if use_cache and cache_key in IndicatorEngineFactory._engine_cache:
            return IndicatorEngineFactory._engine_cache[cache_key]

        # Create new engine instance
        engine = IndicatorEngineFactory._create_engine_instance(mode, event_bus, logger)

        # Cache the instance if caching is enabled
        if use_cache:
            IndicatorEngineFactory._engine_cache[cache_key] = engine

        return engine

    @staticmethod
    def _create_engine_instance(mode: ExecutionMode,
                              event_bus: Optional[EventBus],
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
            return OfflineIndicatorEngine()
            
        else:
            raise ValueError(f"Unsupported execution mode: {mode}")
    
    @staticmethod
    def _generate_cache_key(mode: ExecutionMode) -> str:
        """Generate cache key for engine instances based on mode only."""
        return mode.value
    
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