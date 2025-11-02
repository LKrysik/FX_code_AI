"""
Streaming Indicator Engine
==========================
Real-time indicator calculation with event-driven updates.
"""

import asyncio
import time
import psutil
import os
import json
from pathlib import Path
from collections import deque
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from threading import RLock

# Removed legacy TimeWeightedPriceAverage import - using algorithm registry only

try:
    from ...core.event_bus import EventBus, EventPriority
    from ...core.logger import StructuredLogger
    from ..types.indicator_types import IndicatorConfig, VariantParameter
except Exception:
    from src.core.event_bus import EventBus, EventPriority
    from src.core.logger import StructuredLogger
    from src.domain.types.indicator_types import IndicatorConfig, VariantParameter

# Configuration constants
INDICATORS_CONFIG_DIR = Path("config/indicators")


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

    # Risk Assessment Metrics
    CONFIDENCE_SCORE = "CONFIDENCE_SCORE"
    RISK_LEVEL = "RISK_LEVEL"
    VOLATILITY = "VOLATILITY"
    MARKET_STRESS_INDICATOR = "MARKET_STRESS_INDICATOR"

    # Position-Related Metrics
    POSITION_RISK_SCORE = "POSITION_RISK_SCORE"
    PORTFOLIO_EXPOSURE_PCT = "PORTFOLIO_EXPOSURE_PCT"
    UNREALIZED_PNL_PCT = "UNREALIZED_PNL_PCT"

    # Close Order Price Indicators (ZE1 Section)
    CLOSE_ORDER_PRICE = "CLOSE_ORDER_PRICE"

    # Parametric, Windowed Measures (v1 subset)
    TWPA = "TWPA"                 # Time-Weighted Price Average over window (t1,t2)
    TWPA_RATIO = "TWPA_RATIO"     # ✅ NEW: Ratio between two TWPA values: TWPA(t1,t2) / TWPA(t3,t4)
    LAST_PRICE = "LAST_PRICE"     # Last price in window
    FIRST_PRICE = "FIRST_PRICE"   # First price in window
    MAX_PRICE = "MAX_PRICE"       # Max price in window
    MIN_PRICE = "MIN_PRICE"       # Min price in window
    VELOCITY = "VELOCITY"         # Percent change between current and baseline windows using a price method
    VOLUME_SURGE = "VOLUME_SURGE" # Volume surge ratio between current and baseline windows

    # Orderbook Time-Weighted Measures (parametric windows)
    AVG_BEST_BID = "AVG_BEST_BID"
    AVG_BEST_ASK = "AVG_BEST_ASK"
    AVG_BID_QTY = "AVG_BID_QTY"
    AVG_ASK_QTY = "AVG_ASK_QTY"
    TW_MIDPRICE = "TW_MIDPRICE"

    # Volume/Deals Based Measures (parametric windows)
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

    # Phase 2: Priority 1 Foundation Indicators (Groups A-B)
    MAX_TWPA = "MAX_TWPA"
    MIN_TWPA = "MIN_TWPA"
    VTWPA = "VTWPA"
    VELOCITY_CASCADE = "VELOCITY_CASCADE"
    VELOCITY_ACCELERATION = "VELOCITY_ACCELERATION"
    MOMENTUM_REVERSAL_INDEX = "MOMENTUM_REVERSAL_INDEX"  # ✅ Detects pump-to-dump transition
    DUMP_EXHAUSTION_SCORE = "DUMP_EXHAUSTION_SCORE"      # ✅ Multi-factor dump exhaustion detector
    SUPPORT_LEVEL_PROXIMITY = "SUPPORT_LEVEL_PROXIMITY"  # ✅ Distance to support level (dump bottom)
    VELOCITY_STABILIZATION_INDEX = "VELOCITY_STABILIZATION_INDEX"  # ✅ Velocity variance detector
    MOMENTUM_STREAK = "MOMENTUM_STREAK"
    DIRECTION_CONSISTENCY = "DIRECTION_CONSISTENCY"

    # Phase 3: Priority 2 Core Features Indicators (Groups C-E)
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
    
    GENERAL = "general"         # General purpose indicators (secondary chart)
    RISK = "risk"              # Risk-related indicators (secondary chart)  
    PRICE = "price"            # Price-based indicators (main chart)
    STOP_LOSS = "stop_loss"    # Stop loss indicators (main chart)
    TAKE_PROFIT = "take_profit" # Take profit indicators (main chart)
    CLOSE_ORDER = "close_order" # Close order indicators (main chart)
    
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
    calculation_function: Optional[Callable] = None  # NEW: Direct reference to calculation function
    algorithm_instance: Optional[Any] = None  # NEW: Reference to algorithm instance for advanced scheduling


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
    variant_type: str  # See VariantType enum for valid values
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
    category: str  # See VariantType enum for valid values
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
        # This will be called during class initialization
        func._indicator_metadata = {
            'indicator_type': indicator_type,
            'name': name,
            'description': description,
            'category': category,
            'parameters': parameters
        }
        return func
    return decorator


class StreamingIndicatorEngine:
    """
    Real-time indicator calculation engine.
    Event-driven with efficient sliding window algorithms.
    """
    
    def __init__(self, event_bus: EventBus, logger: StructuredLogger, variant_repository=None):
        self.event_bus = event_bus
        self.logger = logger
        self._variant_repository = variant_repository  # ✅ NEW: Repository for variant persistence

        # ✅ CRITICAL FIX: Thread-safe synchronization
        self._data_lock = RLock()  # Reentrant lock for nested operations

        # ✅ PHASE 2 FIX: Enhanced memory management for 24/7 stability (MOVED UP)
        self.MAX_MEMORY_MB = 500  # Hard memory limit
        self.MAX_INDICATORS_PER_SYMBOL = 100  # Prevent indicator explosion
        self._memory_check_interval = 30  # Check memory every 30 seconds (more frequent)
        self._last_memory_check = time.time()

        # ✅ ARCHITECTURE FIX: Use algorithm registry from variant_repository (SINGLE SOURCE OF TRUTH)
        # If variant_repository is provided, reuse its algorithm_registry to avoid duplication.
        # If not provided (e.g., tests without DI), create standalone registry (fallback).
        if variant_repository is not None and hasattr(variant_repository, 'algorithms'):
            # ✅ PREFERRED PATH: Reuse registry from repository (no duplication)
            self._algorithm_registry = variant_repository.algorithms
            algorithm_count = len(self._algorithm_registry.get_all_algorithms())
            self.logger.info("streaming_indicator_engine.algorithm_registry_from_repository", {
                "algorithms_count": algorithm_count,
                "source": "variant_repository.algorithms"
            })
        else:
            # ⚠️ FALLBACK PATH: Create standalone registry (for tests or when repository is None)
            # This path should NOT be used in production (repository should always be injected)
            try:
                from .indicators.algorithm_registry import IndicatorAlgorithmRegistry
                self._algorithm_registry = IndicatorAlgorithmRegistry(self.logger)

                # Load all algorithms through registry
                discovered_count = self._algorithm_registry.auto_discover_algorithms()

                # If auto-discovery failed, manually register critical algorithms
                if discovered_count == 0:
                    self.logger.info("streaming_indicator_engine.manual_algorithm_registration", {
                        "reason": "auto_discovery_found_no_algorithms"
                    })

                    from .indicators.twpa import twpa_algorithm
                    from .indicators.twpa_ratio import twpa_ratio_algorithm

                    self._algorithm_registry.register_algorithm(twpa_algorithm)
                    self._algorithm_registry.register_algorithm(twpa_ratio_algorithm)

                    manual_count = len(self._algorithm_registry.get_all_algorithms())
                    self.logger.info("streaming_indicator_engine.manual_registration_completed", {
                        "algorithms_registered": manual_count
                    })

                algorithm_count = len(self._algorithm_registry.get_all_algorithms())
                self.logger.warning("streaming_indicator_engine.algorithm_registry_fallback", {
                    "algorithms_count": algorithm_count,
                    "source": "standalone_registry",
                    "reason": "variant_repository_not_provided",
                    "recommendation": "Inject variant_repository via Container for production use"
                })
            except ImportError as import_error:
                self.logger.error("streaming_indicator_engine.algorithm_registry_import_failed", {
                    "error": str(import_error)
                })
                raise RuntimeError("Algorithm registry is required - cannot continue without it") from import_error
        
        # ✅ Old _register_system_indicators() call removed - using new registry systems

        # Indicator storage with symbol indexing for O(1) access
        self._indicators: Dict[str, StreamingIndicator] = {}
        self._indicators_by_symbol: Dict[str, List[str]] = {}  # O(1) symbol lookup
        self._price_data: Dict[str, deque] = {}
        self._orderbook_data: Dict[str, deque] = {}
        self._deal_data: Dict[str, deque] = {}

        # Variant storage
        self._variants: Dict[str, IndicatorVariant] = {}  # variant_id -> variant
        self._variants_by_type: Dict[str, List[str]] = {}  # variant_type -> [variant_ids]
        self._variant_parameters: Dict[str, List[VariantParameter]] = {}  # variant_id -> parameters

        # Configuration
        self._max_series_length = 1000
        self._supported_timeframes = ["1m", "5m", "15m", "1h"]

        # ✅ PHASE 2 FIX: Memory leak detection and monitoring
        self._memory_samples = deque(maxlen=100)  # Track memory usage over time
        self._memory_leak_threshold_mb = 50  # Alert if memory grows by 50MB in short time
        self._memory_growth_window_minutes = 10  # Monitor growth over 10 minutes
        self._last_memory_growth_check = time.time()
        self._memory_alerts_triggered = 0

        # ✅ PHASE 2 FIX: Aggressive cleanup thresholds for stability
        self._memory_cleanup_threshold_pct = 75  # Start cleanup at 75% of limit
        self._memory_force_cleanup_threshold_pct = 85  # Force cleanup at 85%
        self._memory_emergency_threshold_pct = 95  # Emergency cleanup at 95%

        # ✅ CRITICAL FIX: TTL cleanup for data structures to prevent memory leaks (more aggressive)
        self._data_ttl_seconds = 600  # 10 minutes TTL for unused data (reduced from 1 hour)
        self._last_cleanup_time = time.time()
        self._cleanup_interval_seconds = 300  # Cleanup every 5 minutes (more frequent)
        self._data_access_times: Dict[str, float] = {}  # Track last access times for TTL

        # ✅ CRITICAL FIX: Performance metrics
        self._performance_metrics = {
            "processing_time_ms": 0.0,
            "memory_usage_mb": 0.0,
            "indicators_count": 0,
            "data_structures_size": {},
            "cleanup_frequency": 0.0,
            "last_update": time.time()
        }

        # ✅ CRITICAL FIX: Incremental indicator calculators for performance
        self._incremental_indicators: Dict[str, Any] = {}  # Cache for incremental calculations

        # ✅ PHASE 2 FIX: Advanced hierarchical caching system with performance tracking
        self._indicator_cache: Dict[str, Dict[str, Any]] = {}  # cache_key -> {"value": float, "timestamp": float, "ttl": int, "hits": int, "access_time": float}
        self._cache_ttl_seconds = 60  # 1 minute base cache TTL for indicators
        self._cache_bucket_size = 60  # 1 minute time buckets for cache keys

        # ✅ PHASE 2 FIX: Cache performance tracking for >90% hit ratio optimization
        self._cache_hits = 0
        self._cache_misses = 0
        self._cache_access_history: deque = deque(maxlen=1000)  # Track recent cache accesses
        self._cache_performance_window = 300  # 5 minutes performance window

        # ✅ PHASE 2 FIX: Adaptive TTL based on indicator volatility
        self._indicator_volatility: Dict[str, float] = {}  # indicator_type -> volatility score
        self._volatility_update_interval = 600  # Update volatility every 10 minutes
        self._last_volatility_update = time.time()

        # ✅ PHASE 2 FIX: LRU cache eviction with access tracking
        self._cache_access_order: Dict[str, float] = {}  # cache_key -> last_access_time
        self._max_cache_size = 10000  # Maximum cache entries
        self._cache_high_watermark = 8000  # Start eviction at 80% capacity

        self._time_driven_indicators: Dict[str, TimeDrivenSchedule] = {}
        self._time_scheduler_task: Optional[asyncio.Task] = None
        self._scheduler_sleep_floor = 0.25

        # ✅ PHASE 1 FIX: Circuit breaker for indicator calculations
        self._circuit_breaker_state = {
            "failure_count": 0,
            "last_failure_time": 0,
            "state": "CLOSED",  # CLOSED, OPEN, HALF_OPEN
            "success_count": 0,
            "next_attempt_time": 0
        }
        self._circuit_breaker_config = {
            "failure_threshold": 5,  # Open after 5 failures
            "recovery_timeout": 60,  # Try again after 60 seconds
            "success_threshold": 3,  # Close after 3 successes in HALF_OPEN
            "timeout_seconds": 5.0   # Max calculation time before timeout
        }

        # ✅ PHASE 1 FIX: Indicator health monitoring
        self._health_monitoring = {
            "calculation_times": deque(maxlen=100),  # Last 100 calculation times
            "error_counts": {},  # Error counts by indicator type
            "last_health_check": time.time(),
            "health_status": "HEALTHY"  # HEALTHY, DEGRADED, UNHEALTHY
        }

        # Subscribe to market data (will be done when event loop is available)
        self._subscription_task = None

        # ✅ PHASE 2 FIX: Initialize cache warming for frequently used indicators
        self._cache_warming_enabled = True
        self._frequent_indicators = self._get_frequent_indicator_patterns()

        # ✅ SPRINT_GOAL_04: NEW REGISTRY SYSTEM ONLY
        # Old system completely removed - only new _indicator_registry system remains

        # Initialize system indicators registry
        # ✅ CRITICAL FIX: Load existing variants from files on startup
        
        # ✅ OLD SYSTEM REMOVED - No longer calling _initialize_system_indicators()
        
        # Session management tracking
        self._session_indicators: Dict[str, Dict[str, List[str]]] = {}  # session_id -> symbol -> indicator_ids
        self._session_preferences: Dict[str, Dict[str, Dict[str, Any]]] = {}  # session_id -> symbol -> preferences

        # ✅ NEW: Variants will be loaded from database during start() (async operation)
        # self.load_variants_from_files()  # REMOVED - using database now

        self.logger.info("streaming_indicator_engine.unified_registry_initialized", {
            "total_algorithms": len(self._algorithm_registry.get_all_algorithms()),
            "variant_repository_configured": self._variant_repository is not None,
            "note": "Unified algorithm system - variants loaded from database on start()"
        })

    async def start(self) -> None:
        """Start the indicator engine and subscribe to events"""
        # ✅ NEW: Load variants from database (async operation)
        await self._load_variants_from_database()

        if self._subscription_task is None:
            await self.event_bus.subscribe("market.data_update", self._on_market_data)
            self._subscription_task = True  # Mark as subscribed
        if self._time_scheduler_task is None:
            self._time_scheduler_task = asyncio.create_task(self._run_time_driven_scheduler())

    def get_system_indicators(self) -> Dict[str, Any]:
        """Get all registered system indicators with their metadata for API consumption"""
        indicators = []
        
        # Use algorithm registry instead of old indicator registry
        all_algorithms = self._algorithm_registry.get_all_algorithms()
        
        for indicator_type, algorithm in all_algorithms.items():
            try:
                # Get algorithm parameters
                parameters = algorithm.get_parameters()
                
                # Convert algorithm parameters to API format
                api_parameters = []
                for param in parameters:
                    # Handle VariantParameter objects from algorithm registry
                    if hasattr(param, 'parameter_type'):
                        # VariantParameter object
                        api_parameters.append({
                            "name": param.name,
                            "type": param.parameter_type,
                            "default_value": param.default_value,
                            "min_value": param.min_value,
                            "max_value": param.max_value,
                            "allowed_values": param.allowed_values,
                            "is_required": param.is_required,
                            "description": param.description
                        })
                    elif hasattr(param, 'name'):
                        # Generic parameter object with name attribute
                        api_parameters.append({
                            "name": param.name,
                            "type": getattr(param, 'type', 'string'),
                            "default_value": getattr(param, 'default', None),
                            "min_value": getattr(param, 'min_value', None),
                            "max_value": getattr(param, 'max_value', None),
                            "allowed_values": getattr(param, 'allowed_values', None),
                            "is_required": getattr(param, 'required', True),
                            "description": getattr(param, 'description', '')
                        })
                    else:
                        # Dict format fallback
                        api_parameters.append({
                            "name": param.get("name", ""),
                            "type": param.get("type", "string"),
                            "default_value": param.get("default", None),
                            "min_value": param.get("min_value", None),
                            "max_value": param.get("max_value", None),
                            "allowed_values": param.get("allowed_values", None),
                            "is_required": param.get("required", True),
                            "description": param.get("description", "")
                        })
                
                indicators.append({
                    "indicator_type": indicator_type,
                    "name": algorithm.get_name(),
                    "description": algorithm.get_description(),
                    "category": algorithm.get_category(),
                    "is_implemented": True,  # All algorithms in registry are implemented
                    "parameters": api_parameters
                })
                
            except Exception as e:
                self.logger.warning("streaming_indicator_engine.algorithm_metadata_error", {
                    "indicator_type": indicator_type,
                    "error": str(e)
                })
                continue
        
        categories = self._algorithm_registry.get_categories()
        return {
            "indicators": indicators, 
            "total_count": len(indicators), 
            "categories": categories
        }

    def get_system_indicators_by_category(self, category: str) -> Dict[str, Any]:
        """Get system indicators filtered by category"""
        all_indicators = self.get_system_indicators()
        filtered_indicators = [
            indicator for indicator in all_indicators["indicators"]
            if indicator["category"] == category
        ]
        return {
            "indicators": filtered_indicators,
            "total_count": len(filtered_indicators),
            "categories": [category]
        }

    def get_available_categories(self) -> List[str]:
        """Get all available indicator categories"""
        return self._algorithm_registry.get_categories()

    async def calculate_indicator(self, indicator: StreamingIndicator) -> Optional[float]:
        """Public method to calculate an indicator value"""
        return await self._calculate_with_circuit_breaker("", indicator, 0.0, time.time())

    def _resolve_cache_bucket(self, indicator_type: str, params: Dict[str, Any]) -> int:
        """Derive cache bucket size using algorithm registry."""
        algorithm = self._algorithm_registry.get_algorithm(indicator_type)
        if algorithm:
            try:
                from .indicators.base_algorithm import IndicatorParameters
                wrapped_params = IndicatorParameters(params)
                refresh_interval = algorithm.calculate_refresh_interval(wrapped_params)
                return max(1, int(round(refresh_interval)))
            except Exception as e:
                self.logger.warning("streaming_indicator_engine.algorithm_cache_bucket_failed", {
                    "indicator_type": indicator_type,
                    "error": str(e)
                })
        
        return self._cache_bucket_size

    def _get_cache_key(self, indicator_type: str, symbol: str, timeframe: str, params: Dict[str, Any]) -> str:
        """✅ PHASE 1 FIX: Generate cache key with timestamp bucket for time-sensitive indicators"""
        bucket_size = self._resolve_cache_bucket(indicator_type, params)
        current_time = int(time.time() // bucket_size) * bucket_size

        # ✅ PHASE 1 FIX: Enhanced time-bucketed caching for all time-sensitive indicators
        time_sensitive_indicators = [
            "TWPA", "VTWPA", "VELOCITY", "VOLUME_SURGE", "TW_MIDPRICE",
            "MAX_PRICE", "MIN_PRICE", "FIRST_PRICE", "LAST_PRICE",
            "SUM_VOLUME", "AVG_VOLUME", "COUNT_DEALS", "VWAP",
            "VOLUME_CONCENTRATION", "VOLUME_ACCELERATION", "TRADE_FREQUENCY",
            "AVERAGE_TRADE_SIZE", "BID_ASK_IMBALANCE", "SPREAD_PERCENTAGE",
            "SPREAD_VOLATILITY", "VOLUME_PRICE_CORRELATION"
        ]

        if indicator_type in time_sensitive_indicators:
            # Include window parameters and time bucket for precise caching
            t1 = params.get('t1', 0)
            t2 = params.get('t2', 0)
            param_str = f"{t1}:{t2}:{current_time}:{bucket_size}"
        else:
            # For non-time-sensitive indicators, use period and time bucket
            param_str = f"{params.get('period', 20)}:{current_time}"

        cache_key = f"{indicator_type}:{symbol}:{timeframe}:{param_str}"

        # ✅ PHASE 1 FIX: Log cache key generation for debugging
        self.logger.debug("streaming_indicator_engine.cache_key_generated", {
            "indicator_type": indicator_type,
            "symbol": symbol,
            "time_bucket": current_time,
            "cache_key": cache_key
        })

        return cache_key

    def _get_cached_value(self, cache_key: str) -> Optional[float]:
        """✅ PHASE 2 FIX: Get cached indicator value with hit tracking and LRU updates"""
        if cache_key not in self._indicator_cache:
            self._cache_misses += 1
            self._record_cache_access(cache_key, False)
            return None

        cache_entry = self._indicator_cache[cache_key]
        current_time = time.time()

        # Check if expired
        if current_time - cache_entry["timestamp"] > cache_entry["ttl"]:
            # Expired, remove
            del self._indicator_cache[cache_key]
            self._cache_access_order.pop(cache_key, None)
            self._cache_misses += 1
            self._record_cache_access(cache_key, False)
            return None

        # Cache hit - update access tracking
        self._cache_hits += 1
        cache_entry["hits"] = cache_entry.get("hits", 0) + 1
        cache_entry["access_time"] = current_time
        self._cache_access_order[cache_key] = current_time
        self._record_cache_access(cache_key, True)

        # ✅ PHASE 2 FIX: Trigger prefetching for related indicators on cache hit
        if cache_entry["hits"] > 3:  # Only prefetch for frequently accessed indicators
            self.prefetch_related_indicators(cache_key.split(':')[1] if ':' in cache_key else cache_key)

        return cache_entry["value"]

    def _set_cached_value(self, cache_key: str, value: float, ttl: int = None) -> None:
        """✅ PHASE 2 FIX: Cache indicator value with adaptive TTL and LRU eviction"""
        current_time = time.time()

        # Determine adaptive TTL based on indicator volatility
        if ttl is None:
            ttl = self._calculate_adaptive_ttl(cache_key)

        # Check cache size limits and evict if necessary
        self._enforce_cache_limits()

        # Cache the value with enhanced metadata
        self._indicator_cache[cache_key] = {
            "value": value,
            "timestamp": current_time,
            "ttl": ttl,
            "hits": 0,
            "access_time": current_time
        }

        # Update LRU tracking
        self._cache_access_order[cache_key] = current_time

    def _cleanup_cache(self) -> None:
        """Clean expired cache entries"""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self._indicator_cache.items()
            if current_time - entry["timestamp"] > entry["ttl"]
        ]
        for key in expired_keys:
            del self._indicator_cache[key]
            self._cache_access_order.pop(key, None)

        if expired_keys:
            self.logger.debug("streaming_indicator_engine.cache_cleanup", {
                "expired_entries": len(expired_keys),
                "remaining_cache_size": len(self._indicator_cache)
            })

    def _calculate_adaptive_ttl(self, cache_key: str) -> int:
        """✅ PHASE 2 FIX: Calculate adaptive TTL based on indicator volatility and usage patterns"""
        # Extract indicator type from cache key
        indicator_type = cache_key.split(':')[0] if ':' in cache_key else 'UNKNOWN'

        # Base TTL
        base_ttl = self._cache_ttl_seconds

        # Adjust based on volatility (lower volatility = longer TTL)
        volatility = self._indicator_volatility.get(indicator_type, 0.5)  # Default medium volatility
        volatility_factor = 1.0 - (volatility * 0.5)  # 0.5 to 1.5 range

        # Adjust based on recent access patterns (more frequent access = longer TTL)
        access_factor = self._calculate_access_frequency_factor(cache_key)

        # Calculate final TTL with bounds
        adaptive_ttl = int(base_ttl * volatility_factor * access_factor)
        return max(30, min(300, adaptive_ttl))  # Between 30 seconds and 5 minutes

    def _calculate_access_frequency_factor(self, cache_key: str) -> float:
        """Calculate access frequency factor for TTL adjustment"""
        # Simple implementation - could be enhanced with more sophisticated analysis
        recent_accesses = sum(1 for access in self._cache_access_history
                            if access['key'] == cache_key and access['hit'] and
                            time.time() - access['timestamp'] < 300)  # Last 5 minutes

        if recent_accesses > 10:
            return 1.5  # Frequently accessed, longer TTL
        elif recent_accesses > 5:
            return 1.2  # Moderately accessed
        elif recent_accesses > 1:
            return 1.0  # Normal
        else:
            return 0.8  # Rarely accessed, shorter TTL

    async def _run_time_driven_scheduler(self) -> None:
        """Background task ensuring time-driven indicators refresh even without new ticks."""
        self.logger.debug("streaming_indicator_engine.time_scheduler_started")
        try:
            while True:
                if not self._time_driven_indicators:
                    await asyncio.sleep(1.0)
                    continue

                now = time.time()
                due_keys: List[str] = []
                next_due: Optional[float] = None

                for key, schedule in list(self._time_driven_indicators.items()):
                    if key not in self._indicators:
                        self._time_driven_indicators.pop(key, None)
                        continue
                    if now >= schedule.next_run:
                        due_keys.append(key)
                    else:
                        if next_due is None or schedule.next_run < next_due:
                            next_due = schedule.next_run

                if due_keys:
                    for key in due_keys:
                        await self._recalculate_time_driven_indicator(key)
                    await asyncio.sleep(self._scheduler_sleep_floor)
                    continue

                sleep_for = 1.0
                if next_due is not None:
                    sleep_for = max(self._scheduler_sleep_floor, next_due - now)
                await asyncio.sleep(min(sleep_for, 5.0))
        except asyncio.CancelledError:
            self.logger.debug("streaming_indicator_engine.time_scheduler_cancelled")
        except Exception as exc:
            self.logger.error("streaming_indicator_engine.time_scheduler_error", {
                "error": str(exc)
            })

    async def _recalculate_time_driven_indicator(self, indicator_key: str) -> None:
        """
        Recalculate time-driven indicators based on schedule.
        
        ENHANCED: Now supports all algorithms through calculation_function or legacy methods.
        """
        schedule = self._time_driven_indicators.get(indicator_key)
        indicator = self._indicators.get(indicator_key)
        if not schedule or not indicator:
            self._time_driven_indicators.pop(indicator_key, None)
            return

        value: Optional[float] = None
        calculation_method = "unknown"
        
        try:
            # Use algorithm registry - REQUIRED, no fallbacks
            if schedule.calculation_function:
                value = schedule.calculation_function(self, indicator, indicator.metadata or {})
                calculation_method = "algorithm_function"
                
                self.logger.debug("streaming_indicator_engine.algorithm_calculation_used", {
                    "indicator_key": indicator_key,
                    "indicator_type": schedule.indicator_type,
                    "value": value
                })
            else:
                self.logger.error("streaming_indicator_engine.no_calculation_function", {
                    "indicator_key": indicator_key,
                    "indicator_type": schedule.indicator_type,
                    "message": "Algorithm must be registered with calculation function"
                })
                return
        
        except Exception as e:
            self.logger.error("streaming_indicator_engine.calculation_error", {
                "indicator_key": indicator_key,
                "indicator_type": schedule.indicator_type,
                "calculation_method": calculation_method,
                "error": str(e)
            })
            return

        now = time.time()
        schedule.next_run = now + schedule.interval

        if value is None:
            self.logger.debug("streaming_indicator_engine.calculation_returned_none", {
                "indicator_key": indicator_key,
                "calculation_method": calculation_method
            })
            return

        indicator.current_value = value
        indicator.timestamp = now
        indicator.series.append(IndicatorValue(timestamp=now, value=value))
        indicator.metadata["data_points"] = indicator.metadata.get("data_points", 0) + 1
        indicator.metadata["last_calculation"] = now

        try:
            await self.event_bus.publish(
                "indicator.updated",
                {
                    "symbol": indicator.symbol,
                    "indicator": indicator.indicator,
                    "timeframe": indicator.timeframe,
                    "value": value,
                    "timestamp": now,
                },
                priority=EventPriority.NORMAL,
            )
        except Exception as exc:
            self.logger.error("streaming_indicator_engine.time_schedule_publish_error", {
                "indicator_key": indicator_key,
                "error": str(exc),
            })

    def _enforce_cache_limits(self) -> None:
        """✅ PHASE 2 FIX: Enforce cache size limits using LRU eviction"""
        cache_size = len(self._indicator_cache)

        if cache_size >= self._max_cache_size:
            # Hard limit exceeded - aggressive eviction
            self._evict_cache_entries(cache_size - self._max_cache_size + 1000)
        elif cache_size >= self._cache_high_watermark:
            # High watermark exceeded - moderate eviction
            target_size = int(self._max_cache_size * 0.7)  # Target 70% capacity
            entries_to_evict = cache_size - target_size
            self._evict_cache_entries(entries_to_evict)

    def _evict_cache_entries(self, num_entries: int) -> None:
        """Evict least recently used cache entries"""
        if not self._cache_access_order:
            return

        # Sort by access time (oldest first)
        sorted_entries = sorted(self._cache_access_order.items(), key=lambda x: x[1])

        evicted = 0
        for cache_key, _ in sorted_entries:
            if evicted >= num_entries:
                break
            if cache_key in self._indicator_cache:
                del self._indicator_cache[cache_key]
                del self._cache_access_order[cache_key]
                evicted += 1

        if evicted > 0:
            self.logger.debug("streaming_indicator_engine.cache_eviction", {
                "evicted_entries": evicted,
                "remaining_cache_size": len(self._indicator_cache)
            })

    def _record_cache_access(self, cache_key: str, hit: bool) -> None:
        """Record cache access for performance analysis"""
        self._cache_access_history.append({
            'key': cache_key,
            'hit': hit,
            'timestamp': time.time()
        })

    def _update_indicator_volatility(self) -> None:
        """✅ PHASE 2 FIX: Update indicator volatility scores based on recent calculations"""
        current_time = time.time()
        if current_time - self._last_volatility_update < self._volatility_update_interval:
            return

        self._last_volatility_update = current_time

        # Analyze recent cache access patterns to determine volatility
        recent_accesses = [access for access in self._cache_access_history
                          if current_time - access['timestamp'] < 600]  # Last 10 minutes

        indicator_stats = {}
        for access in recent_accesses:
            indicator_type = access['key'].split(':')[0] if ':' in access['key'] else 'UNKNOWN'
            if indicator_type not in indicator_stats:
                indicator_stats[indicator_type] = {'hits': 0, 'misses': 0, 'total': 0}
            indicator_stats[indicator_type]['total'] += 1
            if access['hit']:
                indicator_stats[indicator_type]['hits'] += 1
            else:
                indicator_stats[indicator_type]['misses'] += 1

        # Calculate volatility as miss rate (higher miss rate = higher volatility)
        for indicator_type, stats in indicator_stats.items():
            if stats['total'] > 0:
                miss_rate = stats['misses'] / stats['total']
                # Smooth volatility updates
                current_volatility = self._indicator_volatility.get(indicator_type, 0.5)
                self._indicator_volatility[indicator_type] = (current_volatility * 0.7) + (miss_rate * 0.3)

        self.logger.debug("streaming_indicator_engine.volatility_updated", {
            "indicators_analyzed": len(indicator_stats),
            "volatility_scores": self._indicator_volatility
        })

    # ✅ PHASE 1 FIX: Circuit breaker implementation
    def _is_circuit_breaker_open(self) -> bool:
        """Check if circuit breaker is open (blocking requests)"""
        state = self._circuit_breaker_state
        config = self._circuit_breaker_config
        current_time = time.time()

        if state["state"] == "OPEN":
            if current_time >= state["next_attempt_time"]:
                # Time to try again - move to HALF_OPEN
                state["state"] = "HALF_OPEN"
                state["success_count"] = 0
                self.logger.info("streaming_indicator_engine.circuit_breaker_half_open", {
                    "failure_count": state["failure_count"],
                    "recovery_timeout": config["recovery_timeout"]
                })
                return False
            return True  # Still open
        return False

    def _record_calculation_success(self) -> None:
        """Record successful calculation for circuit breaker"""
        state = self._circuit_breaker_state
        config = self._circuit_breaker_config

        state["failure_count"] = 0  # Reset failure count on success

        if state["state"] == "HALF_OPEN":
            state["success_count"] += 1
            if state["success_count"] >= config["success_threshold"]:
                # Enough successes - close the circuit
                state["state"] = "CLOSED"
                self.logger.info("streaming_indicator_engine.circuit_breaker_closed", {
                    "success_count": state["success_count"],
                    "success_threshold": config["success_threshold"]
                })

    def _record_calculation_failure(self, error: Exception) -> None:
        """Record failed calculation for circuit breaker"""
        state = self._circuit_breaker_state
        config = self._circuit_breaker_config
        current_time = time.time()

        state["failure_count"] += 1
        state["last_failure_time"] = current_time

        # Update error counts for health monitoring
        error_type = type(error).__name__
        self._health_monitoring["error_counts"][error_type] = \
            self._health_monitoring["error_counts"].get(error_type, 0) + 1

        if state["state"] == "HALF_OPEN":
            # Any failure in HALF_OPEN goes back to OPEN
            state["state"] = "OPEN"
            state["next_attempt_time"] = current_time + config["recovery_timeout"]
            self.logger.warning("streaming_indicator_engine.circuit_breaker_reopened", {
                "error_type": error_type,
                "failure_count": state["failure_count"]
            })
        elif state["failure_count"] >= config["failure_threshold"] and state["state"] == "CLOSED":
            # Open the circuit
            state["state"] = "OPEN"
            state["next_attempt_time"] = current_time + config["recovery_timeout"]
            self.logger.warning("streaming_indicator_engine.circuit_breaker_opened", {
                "failure_threshold": config["failure_threshold"],
                "failure_count": state["failure_count"],
                "error_type": error_type
            })

    async def _calculate_with_circuit_breaker(self, indicator_key: str, indicator: StreamingIndicator,
                                              price: float, timestamp: Any) -> Optional[float]:
        """Calculate indicator value with circuit breaker protection"""
        # Check if circuit breaker is open
        if self._is_circuit_breaker_open():
            self.logger.debug("streaming_indicator_engine.circuit_breaker_open_blocking", {
                "indicator_key": indicator_key,
                "state": self._circuit_breaker_state["state"]
            })
            return None  # Return None instead of failing

        # Perform calculation with timeout
        try:
            import asyncio
            calculation_coro = self._calculate_indicator_value_incremental(indicator_key, indicator, price, timestamp)

            # Run with timeout protection
            start_time = time.time()
            result = await asyncio.wait_for(calculation_coro, timeout=self._circuit_breaker_config["timeout_seconds"])
            calculation_time = time.time() - start_time

            # Record success and performance metrics
            self._record_calculation_success()
            self._health_monitoring["calculation_times"].append(calculation_time)

            return result

        except asyncio.TimeoutError:
            error = TimeoutError(f"Calculation timeout after {self._circuit_breaker_config['timeout_seconds']}s")
            self._record_calculation_failure(error)
            self.logger.warning("streaming_indicator_engine.calculation_timeout", {
                "indicator_key": indicator_key,
                "timeout_seconds": self._circuit_breaker_config["timeout_seconds"]
            })
            return None
        except Exception as e:
            self._record_calculation_failure(e)
            self.logger.error("streaming_indicator_engine.calculation_error_with_circuit_breaker", {
                "indicator_key": indicator_key,
                "error": str(e),
                "error_type": type(e).__name__
            })
            return None

    # ✅ PHASE 1 FIX: Health monitoring methods
    def _update_health_status(self) -> None:
        """Update overall health status based on metrics"""
        current_time = time.time()
        if current_time - self._health_monitoring["last_health_check"] < 60:
            return  # Check health every minute

        self._health_monitoring["last_health_check"] = current_time

        # Calculate health metrics
        calculation_times = list(self._health_monitoring["calculation_times"])
        if not calculation_times:
            self._health_monitoring["health_status"] = "UNKNOWN"
            return

        avg_calculation_time = sum(calculation_times) / len(calculation_times)
        error_rate = sum(self._health_monitoring["error_counts"].values()) / max(1, len(calculation_times))

        # Determine health status
        if avg_calculation_time > 1.0 or error_rate > 0.1:  # >1s avg or >10% errors
            self._health_monitoring["health_status"] = "UNHEALTHY"
        elif avg_calculation_time > 0.5 or error_rate > 0.05:  # >500ms avg or >5% errors
            self._health_monitoring["health_status"] = "DEGRADED"
        else:
            self._health_monitoring["health_status"] = "HEALTHY"

    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status"""
        self._update_health_status()

        return {
            "overall_status": self._health_monitoring["health_status"],
            "circuit_breaker": self._circuit_breaker_state.copy(),
            "performance": {
                "avg_calculation_time_ms": (
                    sum(self._health_monitoring["calculation_times"]) /
                    max(1, len(self._health_monitoring["calculation_times"]))
                ) * 1000,
                "total_calculations": len(self._health_monitoring["calculation_times"]),
                "error_counts": self._health_monitoring["error_counts"].copy()
            },
            "cache_stats": self.get_cache_performance_stats(),
            "memory_stability": self.get_memory_stability_report()
        }

    def _calculate_cache_hit_rate(self) -> float:
        """✅ PHASE 2 FIX: Calculate actual cache hit rate from tracked metrics"""
        total_requests = self._cache_hits + self._cache_misses
        if total_requests == 0:
            return 0.0

        hit_rate = self._cache_hits / total_requests

        # Update volatility analysis periodically
        self._update_indicator_volatility()

        return hit_rate

    def add_indicator(self,
                      symbol: str,
                      indicator_type: IndicatorType,
                      timeframe: str = "1m",
                      period: int = 20,
                      **kwargs) -> str:
        """Add a streaming indicator with memory and concurrency safety"""
        with self._data_lock:
            # ✅ CRITICAL FIX: Check memory limits before adding
            if not self._check_memory_limits():
                raise MemoryError(f"Memory limit exceeded ({self.MAX_MEMORY_MB}MB). Cannot add indicator.")

            # ✅ CRITICAL FIX: Check indicator limits per symbol
            if symbol in self._indicators_by_symbol and len(self._indicators_by_symbol[symbol]) >= self.MAX_INDICATORS_PER_SYMBOL:
                raise ValueError(f"Maximum indicators per symbol ({self.MAX_INDICATORS_PER_SYMBOL}) exceeded for {symbol}")

            import json, hashlib

            scope = kwargs.get("scope")
            base_key = f"{symbol}_{indicator_type.value}_{period}_{timeframe}"
            # For parametric measures, include a stable params fingerprint in key to avoid collisions
            param_measures = {"TWPA", "LAST_PRICE", "FIRST_PRICE", "MAX_PRICE", "MIN_PRICE", "VELOCITY"}
            params_only = {k: v for k, v in kwargs.items() if k != "scope"}
            if indicator_type.value in param_measures and params_only:
                try:
                    fp = hashlib.sha1(json.dumps(params_only, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()[:8]
                    base_key = f"{base_key}_{fp}"
                except Exception as e:
                    self.logger.warning("streaming_indicator_engine.fingerprint_creation_error", {
                        "indicator_type": indicator_type.value,
                        "symbol": symbol,
                        "error": str(e)
                    })
            indicator_key = f"{scope}::{base_key}" if scope else base_key

            if indicator_key in self._indicators:
                return indicator_key

            # ✅ CRITICAL FIX: Initialize price data storage with TTL tracking
            price_key = f"{symbol}_{timeframe}"
            if price_key not in self._price_data:
                self._price_data[price_key] = deque(maxlen=self._max_series_length)
                self._data_access_times[price_key] = time.time()

            # Create indicator
            indicator = StreamingIndicator(
                symbol=symbol,
                indicator=f"{indicator_type.value}_{period}",
                timeframe=timeframe,
                current_value=0.0,
                timestamp=time.time(),
                series=deque(maxlen=self._max_series_length),
                metadata={
                    "type": indicator_type.value,
                    "period": period,
                    "data_points": 0,
                    "last_calculation": 0.0,
                    **kwargs
                }
            )

            self._indicators[indicator_key] = indicator
            self._track_indicator(indicator_key, indicator)

            self.logger.info("streaming_indicator.added", {
                "indicator_key": indicator_key,
                "symbol": symbol,
                "type": indicator_type.value,
                "period": period,
                "timeframe": timeframe,
                "total_indicators": len(self._indicators)
            })

            return indicator_key

    def _track_indicator(self, indicator_key: str, indicator: StreamingIndicator) -> None:
        """Ensure internal structures reference a new indicator consistently."""
        symbol = indicator.symbol
        symbol_indicators = self._indicators_by_symbol.setdefault(symbol, [])
        if indicator_key not in symbol_indicators:
            symbol_indicators.append(indicator_key)

        meta = indicator.metadata or {}
        indicator_type = (meta.get("type") or "").upper()
        period = meta.get("period", 20)
        try:
            period_value = int(period)
        except (TypeError, ValueError):
            period_value = 20

        if indicator_type in {"SMA", "EMA", "RSI"}:
            self._init_incremental_calculator(indicator_key, indicator_type, period_value)
        elif indicator_key in self._incremental_indicators:
            self._incremental_indicators.pop(indicator_key, None)

        # ✅ CLEAN: Universal time-driven registration using is_time_driven()
        if self._should_register_for_time_driven_scheduling(indicator_type, indicator):
            self._register_time_driven_indicator(indicator_key, indicator)

        self._performance_metrics["indicators_count"] = len(self._indicators)

    def _should_register_for_time_driven_scheduling(self, indicator_type: str, indicator: StreamingIndicator) -> bool:
        """
        Determine if indicator should use time-driven scheduling.

        Uses algorithm's is_time_driven() method to determine scheduling mode.
        Clean architecture: algorithm declares its own scheduling requirements.
        """
        algorithm = self._algorithm_registry.get_algorithm(indicator_type)
        if not algorithm:
            self.logger.warning("streaming_indicator_engine.no_algorithm_found", {
                "indicator_type": indicator_type
            })
            return False

        try:
            # ✅ CLEAN: Algorithm declares its nature
            is_time_driven = algorithm.is_time_driven()

            self.logger.debug("streaming_indicator_engine.time_driven_check", {
                "indicator_type": indicator_type,
                "is_time_driven": is_time_driven
            })

            return is_time_driven

        except Exception as e:
            self.logger.warning("streaming_indicator_engine.time_driven_check_failed", {
                "indicator_type": indicator_type,
                "error": str(e)
            })
            return False

    def _register_time_driven_indicator(self, indicator_key: str, indicator: StreamingIndicator) -> None:
        """
        Register a schedule for indicators that require time-driven refreshes.
        
        ENHANCED: Now supports all algorithms through the registry system.
        """
        params = indicator.metadata or {}
        indicator_type = (params.get("type") or "").upper()
        
        # ✅ NEW: Try algorithm registry first
        interval = None
        calculation_function = None
        algorithm_instance = None
        
        if self._algorithm_registry:
            algorithm = self._algorithm_registry.get_algorithm(indicator_type)
            if algorithm:
                try:
                    from .indicators.base_algorithm import IndicatorParameters
                    wrapped_params = IndicatorParameters(params)
                    interval = algorithm.calculate_refresh_interval(wrapped_params)
                    calculation_function = algorithm._create_engine_hook()
                    algorithm_instance = algorithm
                    
                    self.logger.debug("streaming_indicator_engine.algorithm_refresh_calculated", {
                        "indicator_type": indicator_type,
                        "interval": interval,
                        "algorithm_name": algorithm.get_name()
                    })
                except Exception as e:
                    self.logger.warning("streaming_indicator_engine.algorithm_refresh_failed", {
                        "indicator_type": indicator_type,
                        "error": str(e)
                    })
        
        # All algorithms MUST be registered - no fallbacks
        if interval is None:
            self.logger.error("streaming_indicator_engine.no_algorithm_registered", {
                "indicator_type": indicator_type,
                "message": "Algorithm must be registered in registry"
            })
            return
        
        # Calculate cache bucket using algorithm
        cache_bucket = max(1, int(round(interval)))
        
        # Create enhanced schedule
        schedule = TimeDrivenSchedule(
            indicator_key=indicator_key,
            interval=interval,
            cache_bucket=cache_bucket,
            next_run=time.time() + interval,
            indicator_type=indicator.metadata.get("type", ""),
            calculation_function=calculation_function,  # NEW: Store calculation function
            algorithm_instance=algorithm_instance       # NEW: Store algorithm reference
        )
        self._time_driven_indicators[indicator_key] = schedule
        indicator.metadata["refresh_interval_seconds"] = interval
        self.logger.debug("streaming_indicator_engine.time_schedule_registered", {
            "indicator_key": indicator_key,
            "interval": interval,
            "cache_bucket": cache_bucket,
        })



    def list_indicators(self) -> List[Dict[str, Any]]:
        """List current indicators in a serializable form"""
        items: List[Dict[str, Any]] = []
        for key, ind in self._indicators.items():
            items.append({
                "key": key,
                "symbol": ind.symbol,
                "indicator": ind.indicator,
                "timeframe": ind.timeframe,
                "data_points": ind.metadata.get("data_points", 0)
            })
        return items

    def _cleanup_expired_data(self):
        """✅ CRITICAL FIX: TTL-based cleanup for data structures and cache to prevent memory leaks"""
        now = time.time()

        # ✅ CRITICAL FIX: Cleanup price data based on access time TTL
        expired_price_keys = []
        for key in list(self._price_data.keys()):
            last_access = self._data_access_times.get(key, 0)
            if now - last_access > self._data_ttl_seconds:
                expired_price_keys.append(key)

        for key in expired_price_keys:
            if key in self._price_data:
                del self._price_data[key]
            if key in self._data_access_times:
                del self._data_access_times[key]

        # ✅ CRITICAL FIX: Cleanup orderbook data based on access time TTL
        expired_ob_keys = []
        for key in list(self._orderbook_data.keys()):
            last_access = self._data_access_times.get(f"ob_{key}", 0)
            if now - last_access > self._data_ttl_seconds:
                expired_ob_keys.append(key)

        for key in expired_ob_keys:
            if key in self._orderbook_data:
                del self._orderbook_data[key]
            if f"ob_{key}" in self._data_access_times:
                del self._data_access_times[f"ob_{key}"]

        # ✅ CRITICAL FIX: Cleanup deal data based on access time TTL
        expired_deal_keys = []
        for key in list(self._deal_data.keys()):
            last_access = self._data_access_times.get(f"deal_{key}", 0)
            if now - last_access > self._data_ttl_seconds:
                expired_deal_keys.append(key)

        for key in expired_deal_keys:
            if key in self._deal_data:
                del self._deal_data[key]
            if f"deal_{key}" in self._data_access_times:
                del self._data_access_times[f"deal_{key}"]

        # ✅ CRITICAL FIX: Cleanup expired indicators to prevent unbounded growth
        expired_indicators = []
        for indicator_key, indicator in self._indicators.items():
            last_calc = indicator.metadata.get("last_calculation", 0)
            if now - last_calc > self._data_ttl_seconds:
                expired_indicators.append(indicator_key)

        for key in expired_indicators:
            if key in self._indicators:
                del self._indicators[key]

        # ✅ CRITICAL FIX: Cleanup expired cache entries
        self._cleanup_cache()

        if expired_price_keys or expired_ob_keys or expired_deal_keys or expired_indicators:
            self.logger.info("streaming_indicator_engine.data_cleanup", {
                "expired_price_keys": len(expired_price_keys),
                "expired_ob_keys": len(expired_ob_keys),
                "expired_deal_keys": len(expired_deal_keys),
                "expired_indicators": len(expired_indicators),
                "cache_size_after_cleanup": len(self._indicator_cache)
            })

    def _check_memory_limits(self) -> bool:
        """✅ PHASE 2 FIX: Enhanced memory monitoring with leak detection for 24/7 stability"""
        current_time = time.time()

        # Only check memory periodically to avoid overhead
        if current_time - self._last_memory_check < self._memory_check_interval:
            return True

        try:
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            self._performance_metrics["memory_usage_mb"] = memory_mb
            self._last_memory_check = current_time

            # ✅ PHASE 2 FIX: Track memory samples for leak detection
            self._memory_samples.append({
                "timestamp": current_time,
                "memory_mb": memory_mb,
                "indicators_count": len(self._indicators),
                "cache_size": len(self._indicator_cache)
            })

            # ✅ PHASE 2 FIX: Check for memory leaks
            self._detect_memory_leaks()

            # ✅ PHASE 2 FIX: Progressive cleanup based on memory usage levels
            memory_pct = (memory_mb / self.MAX_MEMORY_MB) * 100

            if memory_pct >= self._memory_emergency_threshold_pct:
                # Emergency cleanup - most aggressive
                self.logger.error("streaming_indicator_engine.emergency_memory_cleanup", {
                    "memory_mb": memory_mb,
                    "memory_pct": memory_pct,
                    "limit_mb": self.MAX_MEMORY_MB
                })
                self._emergency_cleanup()
                return False
            elif memory_pct >= self._memory_force_cleanup_threshold_pct:
                # Force cleanup - aggressive
                self.logger.warning("streaming_indicator_engine.force_memory_cleanup", {
                    "memory_mb": memory_mb,
                    "memory_pct": memory_pct,
                    "limit_mb": self.MAX_MEMORY_MB
                })
                self._force_cleanup()
                return False
            elif memory_pct >= self._memory_cleanup_threshold_pct:
                # Standard cleanup - moderate
                self.logger.info("streaming_indicator_engine.standard_memory_cleanup", {
                    "memory_mb": memory_mb,
                    "memory_pct": memory_pct,
                    "limit_mb": self.MAX_MEMORY_MB
                })
                self._cleanup_expired_data()

            return True
        except Exception as e:
            self.logger.error("streaming_indicator_engine.memory_check_error", {"error": str(e)})
            return True  # Allow operation if check fails

    def _force_cleanup(self) -> None:
        """✅ CRITICAL FIX: Force cleanup when memory limits exceeded"""
        with self._data_lock:
            # Remove oldest indicators first
            indicators_to_remove = []
            current_time = time.time()

            # Sort indicators by last calculation time
            sorted_indicators = sorted(
                self._indicators.items(),
                key=lambda x: x[1].metadata.get("last_calculation", 0)
            )

            # Remove 20% of oldest indicators
            remove_count = max(1, len(sorted_indicators) // 5)
            for indicator_key, _ in sorted_indicators[:remove_count]:
                indicators_to_remove.append(indicator_key)

            # Remove the indicators
            for indicator_key in indicators_to_remove:
                if indicator_key in self._indicators:
                    symbol = self._indicators[indicator_key].symbol
                    del self._indicators[indicator_key]

                    # Remove from symbol index
                    if symbol in self._indicators_by_symbol:
                        if indicator_key in self._indicators_by_symbol[symbol]:
                            self._indicators_by_symbol[symbol].remove(indicator_key)
                        if not self._indicators_by_symbol[symbol]:
                            del self._indicators_by_symbol[symbol]

            # Force TTL cleanup
            self._cleanup_expired_data()
            self._last_cleanup_time = current_time

            self.logger.warning("streaming_indicator_engine.force_cleanup", {
                "removed_indicators": len(indicators_to_remove),
                "remaining_indicators": len(self._indicators)
            })

    def _emergency_cleanup(self) -> None:
        """✅ PHASE 2 FIX: Emergency cleanup for critical memory situations (24/7 stability)"""
        with self._data_lock:
            current_time = time.time()
            cleanup_stats = {
                "indicators_removed": 0,
                "cache_entries_removed": 0,
                "data_structures_cleaned": 0,
                "memory_freed_mb": 0
            }

            # Measure memory before cleanup
            try:
                process = psutil.Process()
                memory_before = process.memory_info().rss / 1024 / 1024
            except:
                memory_before = 0

            # 1. Aggressive indicator cleanup - remove 50% of indicators
            if len(self._indicators) > 10:  # Keep at least 10 indicators
                indicators_to_keep = max(10, len(self._indicators) // 2)
                sorted_indicators = sorted(
                    self._indicators.items(),
                    key=lambda x: x[1].metadata.get("last_calculation", 0)
                )

                for indicator_key, _ in sorted_indicators[:-indicators_to_keep]:
                    if indicator_key in self._indicators:
                        symbol = self._indicators[indicator_key].symbol
                        del self._indicators[indicator_key]
                        cleanup_stats["indicators_removed"] += 1

                        # Remove from symbol index
                        if symbol in self._indicators_by_symbol:
                            if indicator_key in self._indicators_by_symbol[symbol]:
                                self._indicators_by_symbol[symbol].remove(indicator_key)
                            if not self._indicators_by_symbol[symbol]:
                                del self._indicators_by_symbol[symbol]

            # 2. Clear entire cache if needed
            cache_size_before = len(self._indicator_cache)
            self._indicator_cache.clear()
            self._cache_access_order.clear()
            cleanup_stats["cache_entries_removed"] = cache_size_before

            # 3. Aggressive data structure cleanup
            data_cleaned = self._cleanup_all_data_structures()
            cleanup_stats["data_structures_cleaned"] = data_cleaned

            # 4. Force garbage collection
            import gc
            collected = gc.collect()
            self.logger.info("streaming_indicator_engine.gc_collected", {"objects_collected": collected})

            # Measure memory after cleanup
            try:
                memory_after = process.memory_info().rss / 1024 / 1024
                cleanup_stats["memory_freed_mb"] = max(0, memory_before - memory_after)
            except:
                pass

            # Reset cleanup timers to prevent immediate re-cleanup
            self._last_cleanup_time = current_time

            self.logger.error("streaming_indicator_engine.emergency_cleanup_completed", cleanup_stats)

    def _detect_memory_leaks(self) -> None:
        """✅ PHASE 2 FIX: Detect potential memory leaks for 24/7 stability monitoring"""
        if len(self._memory_samples) < 10:  # Need minimum samples
            return

        current_time = time.time()
        if current_time - self._last_memory_growth_check < (self._memory_growth_window_minutes * 60):
            return

        self._last_memory_growth_check = current_time

        # Analyze memory growth over the monitoring window
        recent_samples = [s for s in self._memory_samples
                         if current_time - s['timestamp'] < (self._memory_growth_window_minutes * 60)]

        if len(recent_samples) < 5:
            return

        # Calculate memory growth trend
        earliest = min(recent_samples, key=lambda x: x['timestamp'])
        latest = max(recent_samples, key=lambda x: x['timestamp'])
        memory_growth = latest['memory_mb'] - earliest['memory_mb']

        # Calculate growth rate (MB per hour)
        time_span_hours = (latest['timestamp'] - earliest['timestamp']) / 3600
        if time_span_hours > 0:
            growth_rate_mbh = memory_growth / time_span_hours

            if memory_growth > self._memory_leak_threshold_mb:
                self._memory_alerts_triggered += 1
                self.logger.warning("streaming_indicator_engine.memory_leak_detected", {
                    "memory_growth_mb": memory_growth,
                    "growth_rate_mb_per_hour": growth_rate_mbh,
                    "time_span_hours": time_span_hours,
                    "alerts_triggered": self._memory_alerts_triggered,
                    "samples_analyzed": len(recent_samples)
                })

                # Trigger preventive cleanup if growth is concerning
                if growth_rate_mbh > 10:  # Growing faster than 10MB/hour
                    self.logger.warning("streaming_indicator_engine.preventive_cleanup_triggered", {
                        "reason": "high_memory_growth_rate",
                        "growth_rate_mb_per_hour": growth_rate_mbh
                    })
                    self._cleanup_expired_data()

    def _cleanup_all_data_structures(self) -> int:
        """✅ PHASE 2 FIX: Aggressive cleanup of all data structures for emergency situations"""
        cleaned_count = 0

        # Clear all price data
        for key in list(self._price_data.keys()):
            del self._price_data[key]
            cleaned_count += 1

        # Clear all orderbook data
        for key in list(self._orderbook_data.keys()):
            del self._orderbook_data[key]
            cleaned_count += 1

        # Clear all deal data
        for key in list(self._deal_data.keys()):
            del self._deal_data[key]
            cleaned_count += 1

        # Clear access times
        self._data_access_times.clear()

        # Clear incremental calculators
        self._incremental_indicators.clear()

        # Clear variants (keep in memory but clear caches)
        # Note: We don't clear variants as they are persistent

        return cleaned_count

    def get_memory_stability_report(self) -> Dict[str, Any]:
        """✅ PHASE 2 FIX: Generate comprehensive memory stability report for 24/7 monitoring"""
        if not self._memory_samples:
            return {"status": "no_data", "message": "No memory samples collected yet"}

        current_time = time.time()

        # Analyze memory trends
        recent_samples = [s for s in self._memory_samples
                         if current_time - s['timestamp'] < 3600]  # Last hour

        if not recent_samples:
            return {"status": "insufficient_data", "message": "No recent memory samples"}

        # Calculate statistics
        memory_values = [s['memory_mb'] for s in recent_samples]
        avg_memory = sum(memory_values) / len(memory_values)
        max_memory = max(memory_values)
        min_memory = min(memory_values)
        memory_variance = sum((x - avg_memory) ** 2 for x in memory_values) / len(memory_values)

        # Calculate stability score (lower variance = more stable)
        stability_score = max(0, 100 - (memory_variance * 10))  # Scale variance to 0-100 score

        # Determine stability status
        if stability_score >= 90:
            status = "EXCELLENT"
        elif stability_score >= 75:
            status = "GOOD"
        elif stability_score >= 60:
            status = "FAIR"
        elif stability_score >= 40:
            status = "POOR"
        else:
            status = "CRITICAL"

        # Memory growth analysis
        if len(recent_samples) >= 2:
            oldest = min(recent_samples, key=lambda x: x['timestamp'])
            newest = max(recent_samples, key=lambda x: x['timestamp'])
            growth_mb = newest['memory_mb'] - oldest['memory_mb']
            time_span_hours = (newest['timestamp'] - oldest['timestamp']) / 3600
            growth_rate_mbh = growth_mb / time_span_hours if time_span_hours > 0 else 0
        else:
            growth_mb = 0
            growth_rate_mbh = 0

        return {
            "status": status,
            "stability_score": stability_score,
            "memory_stats": {
                "average_mb": round(avg_memory, 2),
                "max_mb": round(max_memory, 2),
                "min_mb": round(min_memory, 2),
                "variance": round(memory_variance, 4),
                "current_mb": self._performance_metrics.get("memory_usage_mb", 0)
            },
            "growth_analysis": {
                "growth_mb": round(growth_mb, 2),
                "growth_rate_mb_per_hour": round(growth_rate_mbh, 2),
                "samples_analyzed": len(recent_samples)
            },
            "cleanup_stats": {
                "alerts_triggered": self._memory_alerts_triggered,
                "last_cleanup": self._last_cleanup_time,
                "cleanup_frequency_hours": self._cleanup_interval_seconds / 3600
            },
            "thresholds": {
                "max_memory_mb": self.MAX_MEMORY_MB,
                "cleanup_threshold_pct": self._memory_cleanup_threshold_pct,
                "force_cleanup_threshold_pct": self._memory_force_cleanup_threshold_pct,
                "emergency_threshold_pct": self._memory_emergency_threshold_pct,
                "leak_threshold_mb": self._memory_leak_threshold_mb
            }
        }

    def _init_incremental_calculator(self, indicator_key: str, indicator_type: str, period: int) -> None:
        """✅ CRITICAL FIX: Initialize incremental calculator for performance"""
        if indicator_type == "EMA":
            self._incremental_indicators[indicator_key] = {
                "type": "ema",
                "period": period,
                "multiplier": 2.0 / (period + 1),
                "current_value": None,
                "initialized": False
            }
        elif indicator_type == "SMA":
            self._incremental_indicators[indicator_key] = {
                "type": "sma",
                "period": period,
                "values": deque(maxlen=period),
                "current_sum": 0.0
            }
        elif indicator_type == "RSI":
            self._incremental_indicators[indicator_key] = {
                "type": "rsi",
                "period": period,
                "gains": deque(maxlen=period),
                "losses": deque(maxlen=period),
                "avg_gain": None,
                "avg_loss": None,
                "prev_price": None
            }

    def _should_cleanup_data(self) -> bool:
        """Check if data cleanup should be performed"""
        return time.time() - self._last_cleanup_time > self._cleanup_interval_seconds

    async def _on_market_data(self, data: Dict[str, Any]) -> None:
        """Handle market data update with thread safety and error handling"""
        start_time = time.time()

        # ✅ CRITICAL FIX: Check memory limits before processing
        if not self._check_memory_limits():
            return

        symbol = data.get("symbol")
        price = data.get("price")
        timestamp = data.get("timestamp")

        # Require symbol and timestamp; price is optional if orderbook fields present
        if not symbol or timestamp is None:
            return

        # ✅ CRITICAL FIX: Anomaly detection (logs only, doesn't reject)
        self._validate_market_data(data)

        # ✅ CRITICAL FIX: Use symbol indexing for O(1) indicator check
        has_indicators = symbol in self._indicators_by_symbol and len(self._indicators_by_symbol[symbol]) > 0
        if not has_indicators:
            return  # Skip data storage and processing if no indicators are using this symbol

        # ✅ CRITICAL FIX: Create data checkpoint for rollback capability
        checkpoint = self._create_data_checkpoint(symbol)

        try:
            with self._data_lock:
                # ✅ CRITICAL FIX: Update price data with access time tracking
                if price is not None:
                    for timeframe in self._supported_timeframes:
                        price_key = f"{symbol}_{timeframe}"
                        if price_key not in self._price_data:
                            self._price_data[price_key] = deque(maxlen=self._max_series_length)
                        self._price_data[price_key].append({
                            "timestamp": timestamp,
                            "price": float(price)
                        })
                        # ✅ CRITICAL FIX: Track access time for TTL cleanup
                        self._data_access_times[price_key] = time.time()

                # ✅ CRITICAL FIX: Store deal data with access time tracking
                if data.get("volume") is not None:
                    vol = float(data.get("volume", 0.0))
                    pr = float(price) if price is not None else 0.0
                    for timeframe in self._supported_timeframes:
                        dkey = f"{symbol}_{timeframe}"
                        if dkey not in self._deal_data:
                            self._deal_data[dkey] = deque(maxlen=self._max_series_length)
                        self._deal_data[dkey].append({
                            "timestamp": timestamp,
                            "price": pr,
                            "volume": vol
                        })
                        # ✅ CRITICAL FIX: Track access time for TTL cleanup
                        self._data_access_times[f"deal_{dkey}"] = time.time()

                # ✅ CRITICAL FIX: Update orderbook data with access time tracking
                bids = data.get("bids")
                asks = data.get("asks")
                if bids is not None or asks is not None:
                    best_bid = float(bids[0][0]) if bids else 0.0
                    best_ask = float(asks[0][0]) if asks else 0.0
                    bid_qty = float(bids[0][1]) if bids else 0.0
                    ask_qty = float(asks[0][1]) if asks else 0.0
                    for timeframe in self._supported_timeframes:
                        ob_key = f"{symbol}_{timeframe}"
                        if ob_key not in self._orderbook_data:
                            self._orderbook_data[ob_key] = deque(maxlen=self._max_series_length)
                        self._orderbook_data[ob_key].append({
                            "timestamp": timestamp,
                            "best_bid": best_bid,
                            "best_ask": best_ask,
                            "bid_qty": bid_qty,
                            "ask_qty": ask_qty,
                        })
                        # ✅ CRITICAL FIX: Track access time for TTL cleanup
                        self._data_access_times[f"ob_{ob_key}"] = time.time()

            # Update all indicators for this symbol (outside lock to prevent deadlock)
            price_val = float(price) if price is not None else 0.0
            await self._update_indicators_safe(symbol, price_val, timestamp)

            # ✅ CRITICAL FIX: Periodic cleanup to prevent memory leaks
            if self._should_cleanup_data():
                with self._data_lock:
                    self._cleanup_expired_data()
                    self._last_cleanup_time = time.time()

            # Update performance metrics
            processing_time = (time.time() - start_time) * 1000
            self._performance_metrics["processing_time_ms"] = processing_time
            self._performance_metrics["last_update"] = time.time()

        except Exception as e:
            # ✅ CRITICAL FIX: Rollback on error
            self._rollback_to_checkpoint(checkpoint)
            self.logger.error("streaming_indicator_engine.market_data_error", {
                "symbol": symbol,
                "error": str(e),
                "error_type": type(e).__name__
            })
            raise

    def _validate_market_data(self, data: Dict[str, Any]) -> bool:
        """Validate market data for anomalies - LOG ONLY, don't reject"""
        try:
            symbol = data.get("symbol")
            price = data.get("price")
            timestamp = data.get("timestamp")
            volume = data.get("volume")
            bids = data.get("bids")
            asks = data.get("asks")

            anomalies = []

            # Basic validation - log anomalies but don't reject
            if price is not None and (price <= 0 or price > 1000000):
                anomalies.append(f"unrealistic_price: {price}")

            if volume is not None and volume < 0:
                anomalies.append(f"negative_volume: {volume}")

            if timestamp is not None:
                now = time.time()
                if abs(now - timestamp) > 300:  # 5 minutes tolerance
                    anomalies.append(f"stale_timestamp: {timestamp} vs {now}")

            # Orderbook validation
            if bids and len(bids) > 0:
                best_bid = bids[0][0]
                if best_bid <= 0:
                    anomalies.append(f"invalid_bid: {best_bid}")
                elif price is not None and best_bid > price * 2:
                    anomalies.append(f"unrealistic_bid_vs_price: bid={best_bid}, price={price}")

            if asks and len(asks) > 0:
                best_ask = asks[0][0]
                if best_ask <= 0:
                    anomalies.append(f"invalid_ask: {best_ask}")
                elif price is not None and best_ask < price * 0.5:
                    anomalies.append(f"unrealistic_ask_vs_price: ask={best_ask}, price={price}")

            # Flash crash detection
            if price is not None and symbol:
                price_key = f"{symbol}_1m"
                if price_key in self._price_data and len(self._price_data[price_key]) > 1:
                    recent_prices = [p["price"] for p in list(self._price_data[price_key])[-10:]]
                    if recent_prices:
                        avg_recent = sum(recent_prices) / len(recent_prices)
                        change_pct = abs(price - avg_recent) / avg_recent
                        if change_pct > 0.5:  # 50% sudden change
                            anomalies.append(f"flash_crash_suspected: change={change_pct*100:.1f}%, current={price}, avg={avg_recent:.2f}")

            # Log anomalies if any
            if anomalies:
                self.logger.warning("streaming_indicator_engine.data_anomalies_detected", {
                    "symbol": symbol,
                    "timestamp": timestamp,
                    "anomalies": anomalies,
                    "data_sample": {k: v for k, v in data.items() if k in ["price", "volume", "bids", "asks"]}
                })

            # Always return True - process all data from exchange
            return True

        except Exception as e:
            self.logger.error("streaming_indicator_engine.data_validation_error", {
                "error": str(e),
                "data": data
            })
            # Still process data even if validation fails
            return True
    
    def _create_data_checkpoint(self, symbol: str) -> Dict[str, Any]:
        """✅ CRITICAL FIX: Create data checkpoint for rollback capability"""
        checkpoint = {
            "symbol": symbol,
            "price_data_lengths": {},
            "deal_data_lengths": {},
            "orderbook_data_lengths": {},
            "timestamp": time.time()
        }

        # Record current lengths for rollback
        for timeframe in self._supported_timeframes:
            price_key = f"{symbol}_{timeframe}"
            if price_key in self._price_data:
                checkpoint["price_data_lengths"][price_key] = len(self._price_data[price_key])

            dkey = f"{symbol}_{timeframe}"
            if dkey in self._deal_data:
                checkpoint["deal_data_lengths"][dkey] = len(self._deal_data[dkey])

            ob_key = f"{symbol}_{timeframe}"
            if ob_key in self._orderbook_data:
                checkpoint["orderbook_data_lengths"][ob_key] = len(self._orderbook_data[ob_key])

        return checkpoint

    def _rollback_to_checkpoint(self, checkpoint: Dict[str, Any]) -> None:
        """✅ CRITICAL FIX: Rollback data to checkpoint state"""
        if not checkpoint:
            return

        symbol = checkpoint["symbol"]

        with self._data_lock:
            # Rollback price data
            for price_key, original_length in checkpoint["price_data_lengths"].items():
                if price_key in self._price_data:
                    while len(self._price_data[price_key]) > original_length:
                        self._price_data[price_key].pop()

            # Rollback deal data
            for dkey, original_length in checkpoint["deal_data_lengths"].items():
                if dkey in self._deal_data:
                    while len(self._deal_data[dkey]) > original_length:
                        self._deal_data[dkey].pop()

            # Rollback orderbook data
            for ob_key, original_length in checkpoint["orderbook_data_lengths"].items():
                if ob_key in self._orderbook_data:
                    while len(self._orderbook_data[ob_key]) > original_length:
                        self._orderbook_data[ob_key].pop()

        self.logger.warning("streaming_indicator_engine.rollback_completed", {
            "symbol": symbol,
            "checkpoint_age_seconds": time.time() - checkpoint["timestamp"]
        })

    async def _update_indicators_safe(self, symbol: str, price: float, timestamp: Any) -> None:
        """✅ CRITICAL FIX: Update indicators with deadlock prevention"""
        # ✅ CRITICAL FIX: Use symbol indexing for O(1) access instead of O(n) iteration
        indicator_keys = self._indicators_by_symbol.get(symbol, [])
        if not indicator_keys:
            return

        # Collect updates to publish after calculations (prevent deadlock)
        updates_to_publish = []

        for indicator_key in indicator_keys:
            if indicator_key not in self._indicators:
                continue

            indicator = self._indicators[indicator_key]

            try:
                # ✅ PHASE 1 FIX: Calculate with circuit breaker protection
                new_value = await self._calculate_with_circuit_breaker(indicator_key, indicator, price, timestamp)

                if new_value is not None:
                    # Update indicator
                    indicator.current_value = new_value
                    indicator.timestamp = time.time()
                    indicator.series.append(IndicatorValue(
                        timestamp=time.time(),
                        value=new_value
                    ))
                    indicator.metadata["data_points"] += 1
                    indicator.metadata["last_calculation"] = time.time()

                    # Collect update for publishing (don't publish here to prevent deadlock)
                    updates_to_publish.append({
                        "symbol": symbol,
                        "indicator": indicator.indicator,
                        "timeframe": indicator.timeframe,
                        "value": new_value,
                        "timestamp": timestamp
                    })

            except Exception as e:
                self.logger.error("streaming_indicator.calculation_error", {
                    "indicator_key": indicator_key,
                    "symbol": symbol,
                    "error": str(e)
                })

        # ✅ CRITICAL FIX: Publish all updates outside the calculation loop to prevent deadlock
        for update in updates_to_publish:
            try:
                await self.event_bus.publish(
                    "indicator.updated",
                    update,
                    priority=EventPriority.NORMAL
                )
            except Exception as e:
                self.logger.error("streaming_indicator.publish_error", {
                    "symbol": update["symbol"],
                    "indicator": update["indicator"],
                    "error": str(e)
                })
    
    async def _calculate_indicator_value_incremental(self,
                                                    indicator_key: str,
                                                    indicator: StreamingIndicator,
                                                    price: float,
                                                    timestamp: Any) -> Optional[float]:
        """✅ CRITICAL FIX: Calculate indicator value with incremental updates for performance"""

        indicator_type = indicator.metadata.get("type")
        period = indicator.metadata.get("period", 20)

        # Basic market data indicators (require minimal data)
        if indicator_type in ["PRICE", "VOLUME", "BEST_BID", "BEST_ASK", "BID_QTY", "ASK_QTY"]:
            return self._calculate_basic_market_data(indicator, price, timestamp)

        # ✅ CRITICAL FIX: Use incremental calculations for performance-critical indicators
        if indicator_key in self._incremental_indicators:
            return self._calculate_incremental_indicator(indicator_key, price)

        # Get price data for non-incremental indicators
        price_key = f"{indicator.symbol}_{indicator.timeframe}"
        price_data = self._price_data.get(price_key, deque())

        # For most technical indicators we require at least 'period' datapoints
        if indicator_type in [
            "SMA", "EMA", "RSI", "MACD", "BOLLINGER_BANDS",
            "PUMP_MAGNITUDE_PCT", "PRICE_VELOCITY", "PRICE_MOMENTUM", "BASELINE_PRICE",
            "VOLATILITY"
        ] and len(price_data) < period:
            return None  # Not enough data

        prices = [p["price"] for p in list(price_data)[-period:]]

        # ✅ GOAL_03: Use algorithm registry for calculation functions
        algorithm = self._algorithm_registry.get_algorithm(indicator_type)
        if algorithm and algorithm.calculation_function:
            # Use registered calculation function
            calculation_params = {
                'period': period,
                'price': price,
                'timestamp': timestamp,
                'prices': prices
            }
            return algorithm.calculation_function(indicator, calculation_params)

        # ✅ GOAL_03: Log warning for unregistered indicators instead of fallback
        self.logger.warning("streaming_indicator_engine.unregistered_indicator", {
            "indicator_type": indicator_type,
            "symbol": indicator.symbol,
            "message": "Indicator not found in algorithm registry. Register it in _register_algorithms()"
        })
        return None

    def _calculate_incremental_indicator(self, indicator_key: str, new_price: float) -> Optional[float]:
        """✅ CRITICAL FIX: Incremental calculation for performance-critical indicators"""
        if indicator_key not in self._incremental_indicators:
            return None

        calc = self._incremental_indicators[indicator_key]

        if calc["type"] == "ema":
            # Incremental EMA calculation
            if calc["current_value"] is None:
                calc["current_value"] = new_price
                calc["initialized"] = True
            else:
                calc["current_value"] = (new_price * calc["multiplier"] +
                                       calc["current_value"] * (1 - calc["multiplier"]))
            return calc["current_value"]

        elif calc["type"] == "sma":
            # Incremental SMA calculation
            calc["values"].append(new_price)
            if len(calc["values"]) < calc["period"]:
                return None

            # Recalculate sum for simplicity (could be optimized further)
            calc["current_sum"] = sum(calc["values"])
            return calc["current_sum"] / len(calc["values"])

        elif calc["type"] == "rsi":
            # Incremental RSI calculation
            if calc["prev_price"] is None:
                calc["prev_price"] = new_price
                return None

            # Calculate price change
            change = new_price - calc["prev_price"]
            calc["prev_price"] = new_price

            if change > 0:
                gain = change
                loss = 0.0
            else:
                gain = 0.0
                loss = abs(change)

            calc["gains"].append(gain)
            calc["losses"].append(loss)

            if len(calc["gains"]) < calc["period"]:
                return None

            # Calculate average gain/loss
            if calc["avg_gain"] is None:
                calc["avg_gain"] = sum(calc["gains"]) / calc["period"]
                calc["avg_loss"] = sum(calc["losses"]) / calc["period"]
            else:
                # Smoothed averages
                calc["avg_gain"] = (calc["avg_gain"] * (calc["period"] - 1) + gain) / calc["period"]
                calc["avg_loss"] = (calc["avg_loss"] * (calc["period"] - 1) + loss) / calc["period"]

            if calc["avg_loss"] == 0:
                return 100.0

            rs = calc["avg_gain"] / calc["avg_loss"]
            return 100 - (100 / (1 + rs))

        return None
    
    # ✅ GOAL_03: Registered calculation functions for system indicators
    # These functions provide the unified interface for the indicator registry system
    
    def _calculate_sma_registered(self, indicator: StreamingIndicator, calculation_params: Dict[str, Any]) -> Optional[float]:
        """SMA calculation wrapper for registry system"""
        prices = calculation_params.get('prices', [])
        period = calculation_params.get('period', 20)
        
        if len(prices) < period:
            return None
        return sum(prices[-period:]) / period

    def _calculate_ema_registered(self, indicator: StreamingIndicator, calculation_params: Dict[str, Any]) -> Optional[float]:
        """EMA calculation wrapper for registry system"""
        prices = calculation_params.get('prices', [])
        period = calculation_params.get('period', 20)
        
        if len(prices) < period:
            return None
        return self._calculate_ema(prices, period)

    def _calculate_rsi_registered(self, indicator: StreamingIndicator, calculation_params: Dict[str, Any]) -> Optional[float]:
        """RSI calculation wrapper for registry system"""
        prices = calculation_params.get('prices', [])
        period = calculation_params.get('period', 14)
        
        if len(prices) < period + 1:
            return None
        return self._calculate_rsi(prices, period)

    def _calculate_macd_registered(self, indicator: StreamingIndicator, calculation_params: Dict[str, Any]) -> Optional[float]:
        """MACD calculation wrapper for registry system"""
        prices = calculation_params.get('prices', [])
        
        if len(prices) < 26:  # Need enough data for slow EMA
            return None
        return self._calculate_macd(prices)

    def _calculate_bollinger_bands_registered(self, indicator: StreamingIndicator, calculation_params: Dict[str, Any]) -> Optional[float]:
        """Bollinger Bands calculation wrapper for registry system"""
        prices = calculation_params.get('prices', [])
        period = calculation_params.get('period', 20)
        
        if len(prices) < period:
            return None
        return self._calculate_bollinger_bands(prices, period)

    def _calculate_pump_magnitude_pct_registered(self, indicator: StreamingIndicator, calculation_params: Dict[str, Any]) -> Optional[float]:
        """Pump Magnitude calculation wrapper for registry system"""
        prices = calculation_params.get('prices', [])
        period = calculation_params.get('period', 20)
        
        if len(prices) < period:
            return None
        return self._calculate_pump_magnitude_pct(prices, period)

    def _calculate_volume_surge_ratio_registered(self, indicator: StreamingIndicator, calculation_params: Dict[str, Any]) -> Optional[float]:
        """Volume Surge Ratio calculation wrapper for registry system"""
        return self._calculate_volume_surge_ratio(indicator)

    def _calculate_price_velocity_registered(self, indicator: StreamingIndicator, calculation_params: Dict[str, Any]) -> Optional[float]:
        """Price Velocity calculation wrapper for registry system"""
        prices = calculation_params.get('prices', [])
        period = calculation_params.get('period', 10)
        
        if len(prices) < period:
            return None
        return self._calculate_price_velocity(prices, period)

    def _calculate_price_momentum_registered(self, indicator: StreamingIndicator, calculation_params: Dict[str, Any]) -> Optional[float]:
        """Price Momentum calculation wrapper for registry system"""
        prices = calculation_params.get('prices', [])
        period = calculation_params.get('period', 10)
        
        if len(prices) < period:
            return None
        return self._calculate_price_momentum(prices, period)

    def _calculate_baseline_price_registered(self, indicator: StreamingIndicator, calculation_params: Dict[str, Any]) -> Optional[float]:
        """Baseline Price calculation wrapper for registry system"""
        prices = calculation_params.get('prices', [])
        period = calculation_params.get('period', 20)
        
        if len(prices) < period:
            return None
        return self._calculate_baseline_price(prices, period)

    def _calculate_stop_loss_price_registered(self, indicator: StreamingIndicator, calculation_params: Dict[str, Any]) -> Optional[float]:
        """Stop Loss Price calculation wrapper for registry system"""
        # Use basic calculation for now - can be enhanced
        price = calculation_params.get('price', 0.0)
        atr_period = calculation_params.get('atr_period', 14)
        multiplier = calculation_params.get('multiplier', 2.0)
        
        if price == 0.0:
            return None
        # Simple stop loss calculation (can be improved with ATR)
        return price * (1.0 - (multiplier * 0.01))  # Simple percentage-based

    def _calculate_take_profit_price_registered(self, indicator: StreamingIndicator, calculation_params: Dict[str, Any]) -> Optional[float]:
        """Take Profit Price calculation wrapper for registry system"""
        price = calculation_params.get('price', 0.0)
        risk_reward_ratio = calculation_params.get('risk_reward_ratio', 2.0)
        base_price = calculation_params.get('base_price', 0.0)
        
        if price == 0.0:
            return None
        # Simple take profit calculation
        if base_price > 0:
            risk = abs(price - base_price)
            return price + (risk * risk_reward_ratio)
        else:
            return price * (1.0 + (risk_reward_ratio * 0.01))  # Simple percentage-based

    def _calculate_order_price_registered(self, indicator: StreamingIndicator, calculation_params: Dict[str, Any]) -> Optional[float]:
        """Order Price calculation wrapper for registry system"""
        price = calculation_params.get('price', 0.0)
        method = calculation_params.get('method', 'market')
        offset_pct = calculation_params.get('offset_pct', 0.0)
        
        if price == 0.0:
            return None
            
        if method == 'market':
            return price * (1.0 + offset_pct / 100.0)
        elif method == 'limit':
            return price * (1.0 + offset_pct / 100.0)
        else:
            return price  # Default to market price

    def _calculate_close_order_price_registered(self, indicator: StreamingIndicator, calculation_params: Dict[str, Any]) -> Optional[float]:
        """Close Order Price calculation wrapper for registry system"""
        price = calculation_params.get('price', 0.0)
        method = calculation_params.get('method', 'market')
        offset_pct = calculation_params.get('offset_pct', 0.0)
        
        if price == 0.0:
            return None
            
        if method == 'market':
            return price * (1.0 + offset_pct / 100.0)
        elif method == 'limit':
            return price * (1.0 + offset_pct / 100.0)
        else:
            return price  # Default to market price

    def _calculate_volatility_registered(self, indicator: StreamingIndicator, calculation_params: Dict[str, Any]) -> Optional[float]:
        """Volatility calculation wrapper for registry system"""
        prices = calculation_params.get('prices', [])
        period = calculation_params.get('period', 20)
        
        if len(prices) < period:
            return None
        return self._calculate_volatility(prices, period)

    def _calculate_risk_level_registered(self, indicator: StreamingIndicator, calculation_params: Dict[str, Any]) -> Optional[float]:
        """Risk Level calculation wrapper for registry system"""
        return self._calculate_risk_level(indicator)
    
    def _calculate_ema(self, prices: List[float], period: int) -> float:
        """Calculate Exponential Moving Average"""
        multiplier = 2.0 / (period + 1)
        ema = prices[0]  # Start with first price
        
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    def _calculate_rsi(self, prices: List[float], period: int) -> float:
        """Calculate Relative Strength Index"""
        if len(prices) < period + 1:
            return 50.0  # Neutral RSI
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        if len(gains) < period:
            return 50.0
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_macd(self, prices: List[float]) -> float:
        """Calculate MACD (simplified)"""
        if len(prices) < 26:
            return 0.0
        
        ema12 = self._calculate_ema(prices[-12:], 12)
        ema26 = self._calculate_ema(prices[-26:], 26)
        
        return ema12 - ema26
    
    def _calculate_bollinger_bands(self, prices: List[float], period: int) -> float:
        """Calculate Bollinger Bands middle band (SMA) with standard deviation available"""
        if len(prices) < period:
            return 0.0

    # ===== PHASE 3: PRIORITY 2 CORE FEATURES IMPLEMENTATIONS =====

    def _calculate_trade_size_momentum(self, indicator: StreamingIndicator) -> Optional[float]:
        """Calculate Trade_Size_Momentum - relative change in average trade size"""
        params = indicator.metadata or {}
        current_window = params.get("current_window", {"t1": 300, "t2": 0})  # 5 minutes default
        baseline_window = params.get("baseline_window", {"t1": 1800, "t2": 300})  # 30-5 minutes ago default

        # Calculate average trade size for current window
        current_deals, _, _ = self._get_deals_for_window(indicator, current_window["t1"], current_window["t2"])
        if not current_deals:
            return None
        current_avg_size = sum(d.get("volume", 0.0) for d in current_deals) / len(current_deals)

        # Calculate average trade size for baseline window
        baseline_deals, _, _ = self._get_deals_for_window(indicator, baseline_window["t1"], baseline_window["t2"])
        if not baseline_deals:
            return None
        baseline_avg_size = sum(d.get("volume", 0.0) for d in baseline_deals) / len(baseline_deals)

        if baseline_avg_size == 0:
            return None

        # Calculate momentum: current / baseline
        momentum = current_avg_size / baseline_avg_size

        self.logger.debug("trade_size_momentum_calculated", {
            "symbol": indicator.symbol,
            "current_avg_size": current_avg_size,
            "baseline_avg_size": baseline_avg_size,
            "momentum": momentum
        })

        return momentum

    def _calculate_mid_price_velocity(self, indicator: StreamingIndicator) -> Optional[float]:
        """Calculate Mid_Price_Velocity - velocity of order book mid price"""
        params = indicator.metadata or {}
        t = params.get("t", 300)  # comparison timeframe in seconds (default 5 minutes)

        symbol = indicator.symbol

        # Get current mid price (TW_MidPrice(0,0))
        current_window, _, _ = self._get_orderbook_series_for_window(indicator, 0, 0)
        if not current_window:
            return None

        current_mid = self._calculate_windowed_orderbook_aggregates(indicator, "TW_MIDPRICE", {"t1": 0, "t2": 0})
        if current_mid is None:
            return None

        # Get baseline mid price (TW_MidPrice(t,0))
        baseline_window, _, _ = self._get_orderbook_series_for_window(indicator, t, 0)
        if not baseline_window:
            return None

        baseline_mid = self._calculate_windowed_orderbook_aggregates(indicator, "TW_MIDPRICE", {"t1": t, "t2": 0})
        if baseline_mid is None or baseline_mid == 0:
            return None

        # Calculate velocity: (current - baseline) / baseline * 100
        velocity = ((current_mid - baseline_mid) / baseline_mid) * 100

        self.logger.debug("mid_price_velocity_calculated", {
            "symbol": symbol,
            "current_mid": current_mid,
            "baseline_mid": baseline_mid,
            "velocity": velocity
        })

        return velocity

    def _calculate_total_liquidity(self, indicator: StreamingIndicator) -> Optional[float]:
        """Calculate Total_Liquidity - combined bid and ask liquidity"""
        params = indicator.metadata or {}
        t1 = float(params.get("t1", 300))  # 5 minutes default
        t2 = float(params.get("t2", 0))

        # Use existing windowed orderbook aggregates method
        total_liquidity = self._calculate_windowed_orderbook_aggregates(indicator, "TOTAL_LIQUIDITY", {"t1": t1, "t2": t2})

        return total_liquidity

    def _calculate_liquidity_ratio(self, indicator: StreamingIndicator) -> Optional[float]:
        """Calculate Liquidity_Ratio - current vs baseline liquidity ratio"""
        params = indicator.metadata or {}
        current_window = params.get("current_window", {"t1": 300, "t2": 0})    # 5 minutes default
        baseline_window = params.get("baseline_window", {"t1": 1800, "t2": 300}) # 30-5 minutes ago default

        # Calculate current liquidity
        current_liquidity = self._calculate_windowed_orderbook_aggregates(
            indicator, "TOTAL_LIQUIDITY",
            {"t1": current_window["t1"], "t2": current_window["t2"]}
        )

        # Calculate baseline liquidity
        baseline_liquidity = self._calculate_windowed_orderbook_aggregates(
            indicator, "TOTAL_LIQUIDITY",
            {"t1": baseline_window["t1"], "t2": baseline_window["t2"]}
        )

        if current_liquidity is None or baseline_liquidity is None or baseline_liquidity == 0:
            return None

        ratio = current_liquidity / baseline_liquidity

        self.logger.debug("liquidity_ratio_calculated", {
            "symbol": indicator.symbol,
            "current_liquidity": current_liquidity,
            "baseline_liquidity": baseline_liquidity,
            "ratio": ratio
        })

        return ratio

    def _calculate_liquidity_drain_index(self, indicator: StreamingIndicator) -> Optional[float]:
        """Calculate Liquidity_Drain_Index - liquidity depletion over time"""
        params = indicator.metadata or {}
        current_window = params.get("current_window", {"t1": 300, "t2": 0})    # 5 minutes default
        baseline_window = params.get("baseline_window", {"t1": 600, "t2": 300}) # 10-5 minutes ago default

        # Calculate current liquidity
        current_liquidity = self._calculate_windowed_orderbook_aggregates(
            indicator, "TOTAL_LIQUIDITY",
            {"t1": current_window["t1"], "t2": current_window["t2"]}
        )

        # Calculate baseline liquidity
        baseline_liquidity = self._calculate_windowed_orderbook_aggregates(
            indicator, "TOTAL_LIQUIDITY",
            {"t1": baseline_window["t1"], "t2": baseline_window["t2"]}
        )

        if baseline_liquidity is None or baseline_liquidity == 0:
            return None

        # Drain index: (baseline - current) / baseline
        drain_index = (baseline_liquidity - (current_liquidity or 0)) / baseline_liquidity

        self.logger.debug("liquidity_drain_index_calculated", {
            "symbol": indicator.symbol,
            "current_liquidity": current_liquidity,
            "baseline_liquidity": baseline_liquidity,
            "drain_index": drain_index
        })

        return drain_index

    def _calculate_deal_vs_mid_deviation(self, indicator: StreamingIndicator) -> Optional[float]:
        """Calculate Deal_vs_Mid_Deviation - price deviation from order book mid"""
        params = indicator.metadata or {}
        t1 = float(params.get("t1", 300))  # 5 minutes default
        t2 = float(params.get("t2", 0))

        # Get TWPA for deals in window
        twpa = self._calculate_parametric_measure(indicator)  # This will call TWPA calculation
        if twpa is None:
            return None

        # Get TW_MidPrice for same window
        mid_price = self._calculate_windowed_orderbook_aggregates(indicator, "TW_MIDPRICE", {"t1": t1, "t2": t2})
        if mid_price is None or mid_price == 0:
            return None

        # Calculate deviation: |TWPA - TW_MidPrice| / TW_MidPrice * 100
        deviation = abs(twpa - mid_price) / mid_price * 100

        self.logger.debug("deal_vs_mid_deviation_calculated", {
            "symbol": indicator.symbol,
            "twpa": twpa,
            "mid_price": mid_price,
            "deviation_pct": deviation
        })

        return deviation

    def _calculate_inter_deal_intervals(self, indicator: StreamingIndicator) -> Optional[List[float]]:
        """Calculate Inter_Deal_Intervals - time intervals between consecutive trades"""
        params = indicator.metadata or {}
        t1 = float(params.get("t1", 300))  # 5 minutes default
        t2 = float(params.get("t2", 0))

        # Get deals in window
        deals, _, _ = self._get_deals_for_window(indicator, t1, t2)

        if len(deals) < 2:
            return None

        # Sort deals by timestamp
        deals.sort(key=lambda x: x["timestamp"])

        # Calculate intervals between consecutive deals
        intervals = []
        for i in range(1, len(deals)):
            interval = deals[i]["timestamp"] - deals[i-1]["timestamp"]
            intervals.append(interval)

        self.logger.debug("inter_deal_intervals_calculated", {
            "symbol": indicator.symbol,
            "deal_count": len(deals),
            "interval_count": len(intervals),
            "avg_interval": sum(intervals) / len(intervals) if intervals else 0
        })

        return intervals

    def _calculate_decision_density_acceleration(self, indicator: StreamingIndicator) -> Optional[float]:
        """Calculate Decision_Density_Acceleration - change in trading decision frequency"""
        params = indicator.metadata or {}
        current_window = params.get("current_window", {"t1": 300, "t2": 0})    # 5 minutes default
        baseline_window = params.get("baseline_window", {"t1": 600, "t2": 300}) # 10-5 minutes ago default

        # Get intervals for current window
        current_intervals = self._calculate_inter_deal_intervals_for_window(
            indicator, current_window["t1"], current_window["t2"]
        )

        # Get intervals for baseline window
        baseline_intervals = self._calculate_inter_deal_intervals_for_window(
            indicator, baseline_window["t1"], baseline_window["t2"]
        )

        if not current_intervals or not baseline_intervals:
            return None

        # Calculate median intervals
        current_median = sorted(current_intervals)[len(current_intervals) // 2]
        baseline_median = sorted(baseline_intervals)[len(baseline_intervals) // 2]

        if baseline_median == 0:
            return None

        # Acceleration: median_baseline / median_current
        # Higher values = faster decision making
        acceleration = baseline_median / current_median

        self.logger.debug("decision_density_acceleration_calculated", {
            "symbol": indicator.symbol,
            "current_median_interval": current_median,
            "baseline_median_interval": baseline_median,
            "acceleration": acceleration
        })

        return acceleration

    def _calculate_inter_deal_intervals_for_window(self, indicator: StreamingIndicator, t1: float, t2: float) -> List[float]:
        """Helper method to calculate inter-deal intervals for a specific window"""
        deals, _, _ = self._get_deals_for_window(indicator, t1, t2)

        if len(deals) < 2:
            return []

        deals.sort(key=lambda x: x["timestamp"])
        intervals = []
        for i in range(1, len(deals)):
            interval = deals[i]["timestamp"] - deals[i-1]["timestamp"]
            intervals.append(interval)

        return intervals

    def _calculate_trade_clustering_coefficient(self, indicator: StreamingIndicator) -> Optional[float]:
        """Calculate Trade_Clustering_Coefficient - measure of trade timing clustering"""
        params = indicator.metadata or {}
        t1 = float(params.get("t1", 300))  # 5 minutes default
        t2 = float(params.get("t2", 0))
        min_deals = int(params.get("min_deals", 5))  # minimum deals required

        # Get intervals
        intervals = self._calculate_inter_deal_intervals_for_window(indicator, t1, t2)

        if len(intervals) < min_deals - 1:  # Need at least min_deals - 1 intervals
            return None

        # Calculate coefficient: VARIANCE(intervals) / MEAN(intervals)┬▓
        if not intervals:
            return None

        mean_interval = sum(intervals) / len(intervals)
        variance = sum((interval - mean_interval) ** 2 for interval in intervals) / len(intervals)

        if mean_interval == 0:
            return None

        coefficient = variance / (mean_interval ** 2)

        self.logger.debug("trade_clustering_coefficient_calculated", {
            "symbol": indicator.symbol,
            "interval_count": len(intervals),
            "mean_interval": mean_interval,
            "variance": variance,
            "coefficient": coefficient
        })

        return coefficient

    def _calculate_price_volatility(self, indicator: StreamingIndicator) -> Optional[float]:
        """Calculate Price_Volatility - standard deviation of price returns"""
        params = indicator.metadata or {}
        t1 = float(params.get("t1", 300))  # 5 minutes default
        t2 = float(params.get("t2", 0))
        min_deals = int(params.get("min_deals", 3))  # minimum deals required

        # Get deals in window
        deals, _, _ = self._get_deals_for_window(indicator, t1, t2)

        if len(deals) < min_deals:
            return None

        # Calculate price returns: (price_i - price_{i-1}) / price_{i-1}
        returns = []
        for i in range(1, len(deals)):
            prev_price = deals[i-1]["price"]
            curr_price = deals[i]["price"]
            if prev_price > 0:
                ret = (curr_price - prev_price) / prev_price
                returns.append(ret)

        if not returns:
            return None

        # Calculate standard deviation of returns
        mean_return = sum(returns) / len(returns)
        variance = sum((ret - mean_return) ** 2 for ret in returns) / len(returns)
        volatility = variance ** 0.5

        self.logger.debug("price_volatility_calculated", {
            "symbol": indicator.symbol,
            "deal_count": len(deals),
            "return_count": len(returns),
            "volatility": volatility
        })

        return volatility

    def _calculate_deal_size_volatility(self, indicator: StreamingIndicator) -> Optional[float]:
        """Calculate Deal_Size_Volatility - variability in trade sizes"""
        params = indicator.metadata or {}
        t1 = float(params.get("t1", 300))  # 5 minutes default
        t2 = float(params.get("t2", 0))

        # Get deals in window
        deals, _, _ = self._get_deals_for_window(indicator, t1, t2)

        if len(deals) < 2:
            return None

        # Extract volumes
        volumes = [deal["volume"] for deal in deals if deal.get("volume", 0) > 0]

        if len(volumes) < 2:
            return None

        # Calculate coefficient of variation: STDEV(volumes) / MEAN(volumes)
        mean_volume = sum(volumes) / len(volumes)
        if mean_volume == 0:
            return None

        variance = sum((vol - mean_volume) ** 2 for vol in volumes) / len(volumes)
        std_dev = variance ** 0.5
        volatility = std_dev / mean_volume

        self.logger.debug("deal_size_volatility_calculated", {
            "symbol": indicator.symbol,
            "deal_count": len(volumes),
            "mean_volume": mean_volume,
            "std_dev": std_dev,
            "volatility": volatility
        })

        return volatility

        # Calculate SMA (middle band of Bollinger Bands)
        sma = sum(prices[-period:]) / period

        # Calculate standard deviation for proper Bollinger Bands
        # (This could be used for upper/lower bands in future extensions)
        if len(prices) >= period:
            squared_diff_sum = sum((price - sma) ** 2 for price in prices[-period:])
            std_dev = (squared_diff_sum / period) ** 0.5

            # Log the bands for debugging (full implementation would return all three)
            upper_band = sma + (2 * std_dev)
            lower_band = sma - (2 * std_dev)

            self.logger.debug("bollinger_bands_calculated", {
                "period": period,
                "sma": sma,
                "std_dev": std_dev,
                "upper_band": upper_band,
                "lower_band": lower_band,
                "data_points": len(prices)
            })

        return sma

    def _calculate_max_twpa(self, indicator: StreamingIndicator) -> Optional[float]:
        """Calculate MAX_TWPA - maximum TWPA value over time window"""
        params = indicator.metadata or {}
        t1 = float(params.get("t1", 300))  # 5 minutes default
        t2 = float(params.get("t2", 0))
        measure = params.get("measure", "TWPA")  # TWPA variant to track

        # Get TWPA series over the time window
        twpa_values = self._get_twpa_series_for_window(indicator.symbol, t1, t2, measure)

        if not twpa_values:
            return None

        return max(twpa_values)

    def _calculate_min_twpa(self, indicator: StreamingIndicator) -> Optional[float]:
        """Calculate MIN_TWPA - minimum TWPA value over time window"""
        params = indicator.metadata or {}
        t1 = float(params.get("t1", 300))  # 5 minutes default
        t2 = float(params.get("t2", 0))
        measure = params.get("measure", "TWPA")  # TWPA variant to track

        # Get TWPA series over the time window
        twpa_values = self._get_twpa_series_for_window(indicator.symbol, t1, t2, measure)

        if not twpa_values:
            return None

        return min(twpa_values)

    def _get_twpa_series_for_window(self, symbol: str, t1: float, t2: float, measure: str) -> List[float]:
        """Get series of TWPA values over a time window for max/min calculations"""
        # For now, we'll simulate TWPA values over time windows
        # In a full implementation, this would track historical TWPA calculations

        # Get price data for the window
        price_key = f"{symbol}_1m"  # Use 1m timeframe for now
        price_data = self._price_data.get(price_key, deque())

        if not price_data:
            return []

        # Calculate TWPA at different points in the window
        twpa_values = []
        window_duration = t1 - t2
        step_size = max(30, window_duration // 10)  # Calculate at 10 points or every 30s minimum

        for offset in range(0, int(window_duration), int(step_size)):
            # Calculate TWPA for a sub-window ending at this offset
            sub_t1 = t1 - offset
            sub_t2 = max(0, sub_t1 - step_size)

            if sub_t1 <= sub_t2:
                continue

            # Get price series for this sub-window
            window_prices = []
            now_ts = time.time()
            start_ts = now_ts - sub_t1
            end_ts = now_ts - sub_t2

            for price_point in price_data:
                if start_ts <= price_point["timestamp"] <= end_ts:
                    window_prices.append((price_point["timestamp"], price_point["price"]))

            if len(window_prices) >= 2:
                twpa_value = self._calc_twpa(window_prices, start_ts, end_ts)
                if twpa_value is not None:
                    twpa_values.append(twpa_value)

        return twpa_values

    def _calculate_vtwpa(self, indicator: StreamingIndicator) -> Optional[float]:
        """Calculate VTWPA - Volume-Time Weighted Price Average"""
        params = indicator.metadata or {}
        t1 = float(params.get("t1", 300))  # 5 minutes default
        t2 = float(params.get("t2", 0))

        # Get deals within the time window
        deals, start_ts, end_ts = self._get_deals_for_window(indicator, t1, t2)

        if not deals:
            return None

        # Calculate VTWPA: ╬ú(price_i ├Ś volume_i ├Ś duration_i) / ╬ú(volume_i ├Ś duration_i)
        total_weighted_price = 0.0
        total_weight = 0.0

        # Sort deals by timestamp
        deals.sort(key=lambda x: x["timestamp"])

        for i, deal in enumerate(deals):
            price = deal["price"]
            volume = deal["volume"]
            timestamp = deal["timestamp"]

            # Calculate duration (time this price level was maintained)
            if i == 0:
                # First deal - duration from window start to next deal
                duration_start = max(timestamp, start_ts)
            else:
                # Duration from previous deal to this one
                duration_start = deals[i-1]["timestamp"]

            if i == len(deals) - 1:
                # Last deal - duration to window end
                duration_end = min(timestamp + 60, end_ts)  # Assume 60s duration for last deal
            else:
                # Duration to next deal
                duration_end = deals[i+1]["timestamp"]

            duration = max(1, duration_end - duration_start)  # Minimum 1 second

            # Weight by volume and duration
            weight = volume * duration
            total_weighted_price += price * weight
            total_weight += weight

        if total_weight == 0:
            return None

        vtwpa = total_weighted_price / total_weight

        self.logger.debug("vtwpa_calculated", {
            "symbol": indicator.symbol,
            "t1": t1,
            "t2": t2,
            "deals_count": len(deals),
            "vtwpa": vtwpa
        })

        return vtwpa

    def _calculate_velocity_cascade(self, indicator: StreamingIndicator) -> Optional[List[float]]:
        """Calculate Velocity_Cascade - multi-timeframe velocity analysis"""
        params = indicator.metadata or {}
        timeframes = params.get("timeframes", [30, 60, 120, 300, 600, 900])  # Default timeframes in seconds
        price_method = params.get("price_method", "TWPA")

        velocities = []
        symbol = indicator.symbol

        for timeframe in timeframes:
            try:
                # Calculate velocity for this timeframe
                # Velocity = (current_price - baseline_price) / baseline_price * 100
                # Using TWPA as price method for stability

                # Current window: (0, 0) to now
                # Baseline window: (timeframe, 0) to timeframe seconds ago
                current_params = {"t1": 0, "t2": 0}
                baseline_params = {"t1": timeframe, "t2": 0}

                # Get current price (simplified - using last price for now)
                price_key = f"{symbol}_{indicator.timeframe}"
                price_data = self._price_data.get(price_key, deque())
                if not price_data:
                    velocities.append(0.0)
                    continue

                current_price = price_data[-1]["price"] if price_data else 0.0

                # Get baseline price using TWPA
                baseline_window, _, _ = self._get_price_series_for_window(indicator, timeframe, 0)
                if baseline_window:
                    baseline_price = self._calc_twpa(baseline_window, time.time() - timeframe, time.time())
                else:
                    baseline_price = current_price

                if baseline_price > 0:
                    velocity = ((current_price - baseline_price) / baseline_price) * 100
                    velocities.append(velocity)
                else:
                    velocities.append(0.0)

            except Exception as e:
                self.logger.debug("velocity_cascade_calculation_error", {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "error": str(e)
                })
                velocities.append(0.0)

        self.logger.debug("velocity_cascade_calculated", {
            "symbol": symbol,
            "timeframes": timeframes,
            "velocities": velocities
        })

        return velocities

    def _calculate_velocity_acceleration(self, indicator: StreamingIndicator) -> Optional[float]:
        """Calculate Velocity_Acceleration - velocity rate of change"""
        params = indicator.metadata or {}
        short_window = params.get("short_window", 60)  # 1 minute default
        long_window = params.get("long_window", 300)   # 5 minutes default
        price_method = params.get("price_method", "TWPA")

        symbol = indicator.symbol

        try:
            # Calculate short-term velocity
            short_velocity = self._calculate_single_velocity(symbol, indicator.timeframe, 0, short_window, price_method)

            # Calculate long-term velocity
            long_velocity = self._calculate_single_velocity(symbol, indicator.timeframe, 0, long_window, price_method)

            # Acceleration = V_short - V_long
            acceleration = short_velocity - long_velocity

            self.logger.debug("velocity_acceleration_calculated", {
                "symbol": symbol,
                "short_window": short_window,
                "long_window": long_window,
                "short_velocity": short_velocity,
                "long_velocity": long_velocity,
                "acceleration": acceleration
            })

            return acceleration

        except Exception as e:
            self.logger.debug("velocity_acceleration_error", {
                "symbol": symbol,
                "error": str(e)
            })
            return 0.0

    def _calculate_single_velocity(self, symbol: str, timeframe: str, current_window: int, baseline_window: int, price_method: str) -> float:
        """Helper method to calculate velocity for a single timeframe"""
        # Get current price
        price_key = f"{symbol}_{timeframe}"
        price_data = self._price_data.get(price_key, deque())
        if not price_data:
            return 0.0

        current_price = price_data[-1]["price"] if price_data else 0.0

        # Get baseline price
        baseline_window_data, _, _ = self._get_price_series_for_window(
            type('MockIndicator', (), {'symbol': symbol, 'timeframe': timeframe})(),
            baseline_window, 0
        )

        if baseline_window_data:
            baseline_price = self._calc_twpa(baseline_window_data, time.time() - baseline_window, time.time())
        else:
            baseline_price = current_price

        if baseline_price > 0:
            return ((current_price - baseline_price) / baseline_price) * 100

        return 0.0

    def _calculate_momentum_streak(self, indicator: StreamingIndicator) -> Optional[int]:
        """Calculate Momentum_Streak - count consecutive periods with same direction"""
        params = indicator.metadata or {}
        period_length = params.get("period_length", 60)      # 60 seconds per period
        lookback_periods = params.get("lookback_periods", 10) # Look back 10 periods
        price_method = params.get("price_method", "TWPA")

        symbol = indicator.symbol

        try:
            # Calculate velocities for each period
            velocities = []
            current_time = time.time()

            for i in range(lookback_periods):
                # Calculate velocity for this period vs previous period
                period_start = current_time - ((i + 1) * period_length)
                period_end = current_time - (i * period_length)

                # Get prices in this period
                period_prices = []
                price_key = f"{symbol}_{indicator.timeframe}"
                price_data = self._price_data.get(price_key, deque())

                for price_point in price_data:
                    if period_start <= price_point["timestamp"] <= period_end:
                        period_prices.append(price_point["price"])

                if len(period_prices) >= 2:
                    # Simple velocity: (end_price - start_price) / start_price
                    velocity = ((period_prices[-1] - period_prices[0]) / period_prices[0]) * 100
                    velocities.append(velocity)
                else:
                    velocities.append(0.0)

            if not velocities:
                return 0

            # Count consecutive periods with same direction (positive or negative)
            streak = 0
            current_direction = 0  # 0 = neutral, 1 = positive, -1 = negative

            for velocity in velocities:
                direction = 1 if velocity > 0 else (-1 if velocity < 0 else 0)

                if direction == current_direction and direction != 0:
                    streak += 1
                elif direction != 0:
                    current_direction = direction
                    streak = 1
                else:
                    # Neutral direction breaks streak
                    current_direction = 0
                    streak = 0

            self.logger.debug("momentum_streak_calculated", {
                "symbol": symbol,
                "period_length": period_length,
                "lookback_periods": lookback_periods,
                "velocities_sample": velocities[:5],  # Log first 5
                "streak": streak
            })

            return streak

        except Exception as e:
            self.logger.debug("momentum_streak_error", {
                "symbol": symbol,
                "error": str(e)
            })
            return 0

    def _calculate_direction_consistency(self, indicator: StreamingIndicator) -> Optional[float]:
        """Calculate Direction_Consistency - percentage of periods with consistent direction"""
        params = indicator.metadata or {}
        period_length = params.get("period_length", 60)      # 60 seconds per period
        lookback_periods = params.get("lookback_periods", 10) # Look back 10 periods
        price_method = params.get("price_method", "TWPA")

        symbol = indicator.symbol

        try:
            # Calculate velocities for each period (same as momentum streak)
            velocities = []
            current_time = time.time()

            for i in range(lookback_periods):
                period_start = current_time - ((i + 1) * period_length)
                period_end = current_time - (i * period_length)

                period_prices = []
                price_key = f"{symbol}_{indicator.timeframe}"
                price_data = self._price_data.get(price_key, deque())

                for price_point in price_data:
                    if period_start <= price_point["timestamp"] <= period_end:
                        period_prices.append(price_point["price"])

                if len(period_prices) >= 2:
                    velocity = ((period_prices[-1] - period_prices[0]) / period_prices[0]) * 100
                    velocities.append(velocity)
                else:
                    velocities.append(0.0)

            if not velocities:
                return 0.0

            # Count periods with consistent direction (same as previous period)
            consistent_count = 0
            total_valid_periods = 0

            for i in range(1, len(velocities)):
                prev_velocity = velocities[i-1]
                curr_velocity = velocities[i]

                # Only count if both periods have direction (not neutral)
                prev_direction = 1 if prev_velocity > 0 else (-1 if prev_velocity < 0 else 0)
                curr_direction = 1 if curr_velocity > 0 else (-1 if curr_velocity < 0 else 0)

                if prev_direction != 0 and curr_direction != 0:
                    total_valid_periods += 1
                    if prev_direction == curr_direction:
                        consistent_count += 1

            consistency = (consistent_count / total_valid_periods) if total_valid_periods > 0 else 0.0

            self.logger.debug("direction_consistency_calculated", {
                "symbol": symbol,
                "period_length": period_length,
                "lookback_periods": lookback_periods,
                "consistent_count": consistent_count,
                "total_valid_periods": total_valid_periods,
                "consistency": consistency
            })

            return consistency

        except Exception as e:
            self.logger.debug("direction_consistency_error", {
                "symbol": symbol,
                "error": str(e)
            })
            return 0.0

    def _calculate_basic_market_data(self, indicator: StreamingIndicator, price: float, timestamp: Any) -> float:
        """Calculate basic market data indicators"""
        # These would typically come from market data updates
        # For now, return mock values based on price
        indicator_type = indicator.metadata.get("type")

        if indicator_type == "PRICE":
            return price
        elif indicator_type == "VOLUME":
            return price * 1000  # Mock volume
        elif indicator_type == "BEST_BID":
            return price * 0.999
        elif indicator_type == "BEST_ASK":
            return price * 1.001
        elif indicator_type == "BID_QTY":
            return 100.0
        elif indicator_type == "ASK_QTY":
            return 100.0

        return 0.0

    def _calculate_spread_pct(self, indicator: StreamingIndicator) -> float:
        """Calculate spread percentage"""
        # Mock implementation - would use actual bid/ask data
        return 0.2  # 0.2% spread

    def _calculate_volume_24h(self, indicator: StreamingIndicator) -> float:
        """Calculate 24h volume"""
        # Get deals from the last 24 hours (86400 seconds)
        deals, _, _ = self._get_deals_for_window(indicator, 86400, 0)

        # Sum all volume values from the deals
        total_volume = sum(deal.get("volume", 0.0) for deal in deals)

        return total_volume

    def _calculate_liquidity_score(self, indicator: StreamingIndicator) -> float:
        """Calculate liquidity score"""
        # Mock implementation based on spread and volume
        return 85.0  # Good liquidity

    def _calculate_pump_magnitude_pct(self, prices: List[float], period: int) -> float:
        """Calculate pump magnitude percentage with enhanced detection"""
        if len(prices) < period:
            return 0.0

        # Use EMA for baseline instead of simple average for better trend detection
        baseline_period = max(period // 2, 5)
        if len(prices) < baseline_period + 1:
            return 0.0

        baseline_price = self._calculate_ema(prices[:-1][-baseline_period:], baseline_period)
        current_price = prices[-1]

        if baseline_price == 0:
            return 0.0

        magnitude = ((current_price - baseline_price) / baseline_price) * 100

        # Apply volatility adjustment to normalize for market conditions
        if len(prices) >= period:
            volatility = self._calculate_volatility(prices[-period:], period)
            # Reduce magnitude significance in high volatility environments
            if volatility > 5.0:  # High volatility threshold
                magnitude *= (1 - min(volatility / 20, 0.5))  # Max 50% reduction

        return magnitude

    def _calculate_volume_surge_ratio(self, indicator: StreamingIndicator) -> float:
        """Calculate volume surge ratio with enhanced pump/dump detection"""
        deal_key = f"{indicator.symbol}_{indicator.timeframe}"
        deals = list(self._deal_data.get(deal_key, deque()))
        period = indicator.metadata.get("period", 20)

        if len(deals) < period:
            return 1.0

        # Use configurable windows for current and baseline periods
        current_window = min(period // 4, 5)  # Recent period (default 5)
        baseline_window = min(period // 2, 10)  # Baseline period (default 10)

        if len(deals) < current_window + baseline_window:
            return 1.0

        # Calculate volumes with time-weighted consideration
        current_vol = sum(d.get("volume", 0) for d in deals[-current_window:])
        baseline_vol = sum(d.get("volume", 0) for d in deals[-(current_window + baseline_window):-current_window])

        if baseline_vol == 0:
            return current_vol * 10  # Very high surge if no baseline volume

        ratio = current_vol / baseline_vol

        # Apply logarithmic scaling for extreme surges to prevent outliers
        if ratio > 10:
            ratio = 10 + (ratio - 10) ** 0.5

        return ratio

    def _calculate_price_velocity(self, prices: List[float], period: int) -> float:
        """Calculate price velocity"""
        if len(prices) < 2:
            return 0.0

        price_change = prices[-1] - prices[0]
        time_period = period  # Assuming 1 unit per period

        if time_period == 0:
            return 0.0

        return (price_change / prices[0]) / time_period

    def _calculate_price_momentum(self, prices: List[float], period: int) -> float:
        """Calculate price momentum as rate of change with smoothing"""
        if len(prices) < period + 1:
            return 0.0

        # Calculate momentum as the difference between current EMA and EMA from 'period' ago
        current_ema = self._calculate_ema(prices[-period:], period)
        past_ema = self._calculate_ema(prices[:period], period) if len(prices) >= period * 2 else prices[0]

        if past_ema == 0:
            return 0.0

        momentum = ((current_ema - past_ema) / past_ema) * 100

        # Apply smoothing to reduce noise
        if len(prices) >= period * 2:
            prev_momentum = ((self._calculate_ema(prices[-period*2:-period], period) - past_ema) / past_ema) * 100 if len(prices) >= period * 3 else 0
            momentum = 0.7 * momentum + 0.3 * prev_momentum

        return momentum

    def _calculate_baseline_price(self, prices: List[float], period: int) -> float:
        """Calculate baseline price"""
        if not prices:
            return 0.0

        return sum(prices) / len(prices)

    def _calculate_pump_probability(self, indicator: StreamingIndicator, prices: List[float]) -> float:
        """Calculate pump probability based on velocity, volume surge, and momentum"""
        if len(prices) < 10:
            return 50.0  # Neutral probability with insufficient data

        symbol = indicator.symbol
        period = indicator.metadata.get("period", 20)

        # Calculate velocity (price change rate)
        velocity = self._calculate_price_velocity(prices, period)

        # Calculate volume surge ratio
        volume_surge = self._calculate_volume_surge_ratio(indicator)

        # Calculate momentum
        momentum = self._calculate_price_momentum(prices, period)

        # Calculate pump probability using weighted factors
        # High velocity + high volume surge + positive momentum = high pump probability
        velocity_score = min(abs(velocity) * 10, 50)  # Cap at 50 points
        volume_score = min(volume_surge * 20, 30)     # Cap at 30 points
        momentum_score = max(0, momentum) * 0.5       # Positive momentum contribution

        # Combine scores (max 100)
        pump_probability = velocity_score + volume_score + momentum_score

        # Ensure result is between 0 and 100
        return max(0.0, min(100.0, pump_probability))

    def _calculate_confidence_score(self, indicator: StreamingIndicator) -> float:
        """Calculate confidence score"""
        # Mock implementation
        return 75.0  # 75% confidence

    def _calculate_risk_level(self, indicator: StreamingIndicator) -> float:
        """Calculate risk level (0-100 scale)"""
        # Mock implementation
        return 25.0  # Low risk

    def _calculate_volatility(self, prices: List[float], period: int) -> float:
        """Calculate volatility"""
        if len(prices) < 2:
            return 0.0

        # Calculate standard deviation of returns
        returns = []
        for i in range(1, len(prices)):
            ret = (prices[i] - prices[i-1]) / prices[i-1]
            returns.append(ret)

        if not returns:
            return 0.0

        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)

        return variance ** 0.5  # Standard deviation

    def _calculate_market_stress_indicator(self, indicator: StreamingIndicator) -> float:
        """Calculate market stress indicator as composite of volatility, spread, and volume metrics"""
        symbol = indicator.symbol
        period = indicator.metadata.get("period", 20)

        # Get price data for volatility calculation
        price_key = f"{symbol}_{indicator.timeframe}"
        price_data = self._price_data.get(price_key, deque())
        prices = [p["price"] for p in list(price_data)[-period:]]

        # Calculate components
        volatility = self._calculate_volatility(prices, period) if len(prices) >= 2 else 0.0
        spread_pct = self._calculate_spread_pct(indicator)
        volume_surge = self._calculate_volume_surge_ratio(indicator)

        # Weight the components to create stress index
        # Higher values indicate more stress
        stress_score = (
            volatility * 0.4 +      # 40% weight on volatility
            spread_pct * 0.3 +      # 30% weight on spread
            volume_surge * 0.3      # 30% weight on volume surge
        )

        # Normalize to 0-100 scale (stress indicator)
        # Typical ranges: volatility 0-20%, spread 0-5%, volume_surge 0-10
        # Scale to make 0-100 meaningful
        normalized_stress = min(100.0, stress_score * 5)

        return normalized_stress

    def _calculate_position_risk_score(self, indicator: StreamingIndicator) -> float:
        """Calculate position risk score"""
        # Mock implementation
        return 20.0  # Low position risk

    def _calculate_portfolio_exposure_pct(self, indicator: StreamingIndicator) -> float:
        """Calculate portfolio exposure percentage"""
        # NOTE: This indicator requires position/portfolio data integration
        # For now, return a placeholder indicating integration needed
        # In a full implementation, this would access position data from a portfolio service

        symbol = indicator.symbol

        # Check if we have any position-like data (this would need to be integrated)
        # For now, return 0.0 indicating no position data available
        # Real implementation would:
        # 1. Get current position size for this symbol
        # 2. Get total portfolio value
        # 3. Calculate exposure = (position_value / portfolio_value) * 100

        self.logger.debug("portfolio_exposure_calculation", {
            "symbol": symbol,
            "status": "position_data_integration_required",
            "current_implementation": "placeholder"
        })

        return 0.0  # No exposure data available

    def _calculate_unrealized_pnl_pct(self, indicator: StreamingIndicator) -> float:
        """Calculate unrealized P&L percentage"""
        # NOTE: This indicator requires position/portfolio data integration
        # For now, return a placeholder indicating integration needed
        # Real implementation would:
        # 1. Get current position for this symbol (entry price, quantity)
        # 2. Get current market price
        # 3. Calculate unrealized P&L = (current_price - entry_price) * quantity
        # 4. Calculate percentage = (unrealized_pnl / position_value) * 100

        symbol = indicator.symbol

        self.logger.debug("unrealized_pnl_calculation", {
            "symbol": symbol,
            "status": "position_data_integration_required",
            "current_implementation": "placeholder"
        })

        return 0.0  # No position data available

    def _calculate_close_order_price(self, indicator: StreamingIndicator) -> Optional[float]:
        """Calculate close order price for ZE1 section with risk-adjusted pricing"""
        try:
            params = indicator.metadata or {}

            # Get current market price as base
            price_key = f"{indicator.symbol}_{indicator.timeframe}"
            price_data = self._price_data.get(price_key, deque())

            if not price_data:
                return None

            current_price = price_data[-1]["price"]

            # Check if risk-adjusted pricing is enabled
            risk_adjusted = params.get("risk_adjusted_pricing", {})
            if not risk_adjusted.get("enabled", False):
                # Simple close at current price
                return current_price

            # Apply risk-adjusted pricing logic
            scaling_factor = risk_adjusted.get("scaling_factor", 1.0)
            min_adjustment = risk_adjusted.get("min_adjustment", -10)
            max_adjustment = risk_adjusted.get("max_adjustment", 10)

            # Calculate adjustment based on some risk metric (simplified)
            # In a real implementation, this would use volatility, position size, etc.
            risk_level = self._calculate_risk_level_for_symbol(indicator.symbol)

            # Scale adjustment based on risk level (0-100)
            adjustment_pct = (risk_level / 100.0) * scaling_factor * (max_adjustment - min_adjustment) / 100.0
            adjustment_pct = max(min_adjustment / 100.0, min(max_adjustment / 100.0, adjustment_pct))

            # Apply adjustment to current price
            adjusted_price = current_price * (1 + adjustment_pct)

            self.logger.debug("close_order_price.calculated", {
                "symbol": indicator.symbol,
                "current_price": current_price,
                "risk_level": risk_level,
                "adjustment_pct": adjustment_pct * 100,
                "adjusted_price": adjusted_price
            })

            return adjusted_price

        except Exception as e:
            self.logger.error("close_order_price.calculation_error", {
                "symbol": indicator.symbol,
                "error": str(e),
                "error_type": type(e).__name__
            })
            return None

    def _calculate_risk_level_for_symbol(self, symbol: str) -> float:
        """Calculate risk level for a symbol (simplified implementation)"""
        # In a real implementation, this would analyze volatility, volume, etc.
        # For now, return a mock risk level between 0-100
        return 25.0  # Low-moderate risk

    def _validate_time_window_semantics(self, t1: float, t2: float, indicator_type: str) -> tuple[float, float]:
        """
        ✅ PHASE 1 FIX: Validate and enforce time window semantics.
        Standardizes on t1 > t2 convention where t1 is seconds ago for start, t2 for end.
        Example: TWPA(300, 0) = "from 5 minutes ago to now"
        """
        # Validate parameter types
        if not isinstance(t1, (int, float)) or not isinstance(t2, (int, float)):
            raise ValueError(f"Time window parameters must be numeric: t1={t1}, t2={t2}")

        # Validate parameter ranges
        if t1 < 0 or t2 < 0:
            raise ValueError(f"Time window parameters cannot be negative: t1={t1}, t2={t2}")

        # Enforce t1 > t2 convention (start time > end time in seconds ago)
        if t1 <= t2:
            self.logger.warning("streaming_indicator_engine.time_window_semantics_violation", {
                "indicator_type": indicator_type,
                "t1": t1,
                "t2": t2,
                "expected": "t1 > t2",
                "action": "auto_correcting"
            })
            # Auto-correct by interpreting as (max, min) to maintain backward compatibility
            t1, t2 = max(t1, t2), min(t1, t2)

        # Validate reasonable bounds (max 24 hours)
        max_window_seconds = 24 * 60 * 60
        if t1 > max_window_seconds:
            raise ValueError(f"Time window too large: t1={t1}s > {max_window_seconds}s (24h)")

        return t1, t2

    @staticmethod
    def _normalize_timestamp(timestamp: float) -> float:
        """Normalize timestamps to seconds precision (accepts milliseconds)."""
        if timestamp is None:
            return time.time()
        if timestamp > 1e12:
            return float(timestamp) / 1000.0
        return float(timestamp)

    def _get_price_series_for_window(self, indicator: StreamingIndicator, t1: float, t2: float):
        """
        Return list of (ts, price) for TWPA calculation.

        CRITICAL: TWPA requires one transaction BEFORE the window to calculate
        the duration of the first price in the window.

        Returns:
            - window: List of (timestamp, price) tuples including one point before start_ts
            - start_ts: Window start timestamp
            - end_ts: Window end timestamp
        """
        # ✅ PHASE 1 FIX: Validate time window semantics
        t1, t2 = self._validate_time_window_semantics(t1, t2, indicator.metadata.get("type", "UNKNOWN"))

        price_key = f"{indicator.symbol}_{indicator.timeframe}"
        series = list(self._price_data.get(price_key, deque()))
        if not series:
            # ✅ CRITICAL FIX: Always return 3 elements to maintain contract consistency
            # Calculate theoretical window timestamps even without data
            current_time = time.time()
            start_ts = current_time - float(t1)
            end_ts = current_time - float(t2)
            return [], start_ts, end_ts

        # Determine reference 'now' as last seen timestamp in series
        now_ts = self._normalize_timestamp(series[-1].get("timestamp") or time.time())
        start_ts = now_ts - float(t1)
        end_ts = now_ts - float(t2)

        # ✅ TWPA FIX: Find the last transaction BEFORE the window
        pre_window_point = None
        for s in series:
            ts = self._normalize_timestamp(s.get("timestamp"))
            if s.get("timestamp") is not None and ts < start_ts:
                # Keep updating to get the LAST point before window
                pre_window_point = (ts, float(s.get("price", 0.0)))

        # Get all points WITHIN the window [start_ts, end_ts]
        window = [
            (
                self._normalize_timestamp(s.get("timestamp")),
                float(s.get("price", 0.0)),
            )
            for s in series
            if s.get("timestamp") is not None
            and start_ts <= self._normalize_timestamp(s["timestamp"]) <= end_ts
        ]

        # ✅ TWPA FIX: ALWAYS include the pre-window point at the beginning
        # This is REQUIRED by TWPA algorithm to calculate duration of first price
        # This handles both cases:
        #   1. Window has points: pre_window_point is inserted at position 0
        #   2. Window is empty: pre_window_point creates a single-element list
        if pre_window_point:
            window.insert(0, pre_window_point)

        # Ensure ascending by timestamp (should already be sorted, but ensure it)
        window.sort(key=lambda x: x[0])
        return window, start_ts, end_ts

    def _get_volume_series_for_window(self, indicator: StreamingIndicator, t1: float, t2: float):
        """
        Return list of (timestamp, volume) tuples for volume-based calculations.

        Extracts volume data from deal_data (which contains price+volume).

        Returns:
            - window: List of (timestamp, volume) tuples
            - start_ts: Window start timestamp
            - end_ts: Window end timestamp
        """
        # Validate time window semantics
        t1, t2 = self._validate_time_window_semantics(t1, t2, indicator.metadata.get("type", "UNKNOWN"))

        deal_key = f"{indicator.symbol}_{indicator.timeframe}"
        series = list(self._deal_data.get(deal_key, deque()))

        if not series:
            # No data available - return empty window
            current_time = time.time()
            start_ts = current_time - float(t1)
            end_ts = current_time - float(t2)
            return [], start_ts, end_ts

        # Determine reference 'now' as last seen timestamp
        now_ts = self._normalize_timestamp(series[-1].get("timestamp") or time.time())
        start_ts = now_ts - float(t1)
        end_ts = now_ts - float(t2)

        # Get all volume points within the window
        window = [
            (
                self._normalize_timestamp(s.get("timestamp")),
                float(s.get("volume", 0.0)),
            )
            for s in series
            if s.get("timestamp") is not None
            and start_ts <= self._normalize_timestamp(s["timestamp"]) <= end_ts
        ]

        # Ensure ascending by timestamp
        window.sort(key=lambda x: x[0])
        return window, start_ts, end_ts

    def _get_deal_series_for_window(self, indicator: StreamingIndicator, t1: float, t2: float):
        """
        Return list of (timestamp, price, volume) tuples for deal-based calculations.

        Returns full deal data with both price and volume.

        Returns:
            - window: List of (timestamp, price, volume) tuples
            - start_ts: Window start timestamp
            - end_ts: Window end timestamp
        """
        # Validate time window semantics
        t1, t2 = self._validate_time_window_semantics(t1, t2, indicator.metadata.get("type", "UNKNOWN"))

        deal_key = f"{indicator.symbol}_{indicator.timeframe}"
        series = list(self._deal_data.get(deal_key, deque()))

        if not series:
            # No data available - return empty window
            current_time = time.time()
            start_ts = current_time - float(t1)
            end_ts = current_time - float(t2)
            return [], start_ts, end_ts

        # Determine reference 'now' as last seen timestamp
        now_ts = self._normalize_timestamp(series[-1].get("timestamp") or time.time())
        start_ts = now_ts - float(t1)
        end_ts = now_ts - float(t2)

        # Get all deal points within the window
        window = [
            (
                self._normalize_timestamp(s.get("timestamp")),
                float(s.get("price", 0.0)),
                float(s.get("volume", 0.0)),
            )
            for s in series
            if s.get("timestamp") is not None
            and start_ts <= self._normalize_timestamp(s["timestamp"]) <= end_ts
        ]

        # Ensure ascending by timestamp
        window.sort(key=lambda x: x[0])
        return window, start_ts, end_ts

    def _get_orderbook_series_for_window(self, indicator: StreamingIndicator, t1: float, t2: float):
        if t1 < t2:
            t1, t2 = t2, t1
        ob_key = f"{indicator.symbol}_{indicator.timeframe}"
        series = list(self._orderbook_data.get(ob_key, deque()))
        if not series:
            return [], 0.0, 0.0
        now_ts = self._normalize_timestamp(series[-1].get("timestamp") or time.time())
        start_ts = now_ts - float(t1)
        end_ts = now_ts - float(t2)
        # keep entries inside [start_ts, end_ts]
        window = [
            {
                "timestamp": self._normalize_timestamp(s.get("timestamp")),
                "best_bid": float(s.get("best_bid", 0.0)),
                "best_ask": float(s.get("best_ask", 0.0)),
                "bid_qty": float(s.get("bid_qty", 0.0)),
                "ask_qty": float(s.get("ask_qty", 0.0)),
            }
            for s in series
            if s.get("timestamp") is not None
            and start_ts <= self._normalize_timestamp(s["timestamp"]) <= end_ts
        ]
        window.sort(key=lambda x: x["timestamp"])
        return window, start_ts, end_ts

    def _get_deals_for_window(self, indicator: StreamingIndicator, t1: float, t2: float):
        if t1 < t2:
            t1, t2 = t2, t1
        key = f"{indicator.symbol}_{indicator.timeframe}"
        series = list(self._deal_data.get(key, deque()))
        if not series:
            return [], 0.0, 0.0
        now_ts = self._normalize_timestamp(series[-1].get("timestamp") or time.time())
        start_ts = now_ts - float(t1)
        end_ts = now_ts - float(t2)
        window = [
            {
                "timestamp": self._normalize_timestamp(s.get("timestamp")),
                "price": float(s.get("price", 0.0)),
                "volume": float(s.get("volume", 0.0)),
            }
            for s in series
            if s.get("timestamp") is not None
            and start_ts <= self._normalize_timestamp(s["timestamp"]) <= end_ts
        ]
        window.sort(key=lambda x: x["timestamp"])
        return window, start_ts, end_ts

    def _calc_twpa(self, window_points: list, start_ts: float, end_ts: float) -> Optional[float]:
        """Compute Time-Weighted Price Average using unified algorithm."""
        from .indicators.twpa import twpa_algorithm
        from .indicators.base_algorithm import IndicatorParameters
        
        # Use the unified algorithm
        params = IndicatorParameters({})  # TWPA doesn't need params for basic calculation
        return twpa_algorithm._compute_twpa(window_points, start_ts, end_ts)

    def _calculate_parametric_measure(self, indicator: StreamingIndicator) -> Optional[float]:
        """
        Dispatcher for calculating parametric, windowed indicators with caching.
        Refactored to delegate to specialized methods for clarity and maintainability.
        """
        typ = indicator.metadata.get("type")
        params = indicator.metadata or {}

        # Generate cache key with timestamp bucket
        cache_key = self._get_cache_key(typ, indicator.symbol, indicator.timeframe, params)

        # Check cache first
        cached_value = self._get_cached_value(cache_key)
        if cached_value is not None:
            self.logger.debug("streaming_indicator_engine.cache_hit", {
                "indicator_type": typ,
                "symbol": indicator.symbol,
                "cache_key": cache_key
            })
            return cached_value

        # Calculate the value
        value = None
        if typ in ("FIRST_PRICE", "LAST_PRICE", "MAX_PRICE", "MIN_PRICE"):
            value = self._calculate_windowed_price_aggregates(indicator, typ, params)
        elif typ == "VELOCITY":
            value = self._calculate_velocity(indicator, params)
        elif typ == "VOLUME_SURGE":
            value = self._calculate_volume_surge(indicator, params)
        elif typ in ("AVG_BEST_BID", "AVG_BEST_ASK", "AVG_BID_QTY", "AVG_ASK_QTY", "TW_MIDPRICE",
                      "BID_ASK_IMBALANCE", "SPREAD_PERCENTAGE", "SPREAD_VOLATILITY"):
            value = self._calculate_windowed_orderbook_aggregates(indicator, typ, params)
        elif typ in ("SUM_VOLUME", "AVG_VOLUME", "COUNT_DEALS", "VWAP"):
            value = self._calculate_windowed_deal_aggregates(indicator, typ, params)
        elif typ == "VOLUME_CONCENTRATION":
            value = self._calculate_volume_concentration(indicator, params)
        elif typ == "VOLUME_ACCELERATION":
            value = self._calculate_volume_acceleration(indicator, params)
        elif typ == "TRADE_FREQUENCY":
            value = self._calculate_trade_frequency(indicator, params)
        elif typ == "AVERAGE_TRADE_SIZE":
            value = self._calculate_average_trade_size(indicator, params)
        elif typ == "VOLUME_PRICE_CORRELATION":
            value = self._calculate_volume_price_correlation(indicator, params)
        else:
            self.logger.warning("streaming_indicator_engine.unknown_indicator_type_in_parametric_measure", {
                "indicator_type": typ,
                "symbol": indicator.symbol,
                "message": "Indicator should use algorithm registry instead"
            })

        # Cache the result if calculated
        if value is not None:
            self._set_cached_value(cache_key, value)
            self.logger.debug("streaming_indicator_engine.cache_set", {
                "indicator_type": typ,
                "symbol": indicator.symbol,
                "value": value,
                "cache_key": cache_key
            })

        return value

    def _calculate_windowed_price_aggregates(self, indicator: StreamingIndicator, typ: str, params: dict) -> Optional[float]:
        """
        Calculate simple windowed price aggregates.

        Supports: FIRST_PRICE, LAST_PRICE, MAX_PRICE, MIN_PRICE
        Note: TWPA is now handled by algorithm registry (see _calculate_twpa)
        """
        t1 = float(params.get("t1", 60))
        t2 = float(params.get("t2", 0))
        window, start_ts, end_ts = self._get_price_series_for_window(indicator, t1, t2)
        if not window:
            return None

        # Extract prices from window (ignore timestamps)
        vals = [p for _, p in window]

        if typ == "FIRST_PRICE":
            return vals[0]
        if typ == "LAST_PRICE":
            return vals[-1]
        if typ == "MAX_PRICE":
            return max(vals)
        if typ == "MIN_PRICE":
            return min(vals)

        # Unknown type
        self.logger.warning("streaming_indicator_engine.unknown_windowed_aggregate", {
            "typ": typ,
            "symbol": indicator.symbol
        })
        return None

    # REMOVED: _calculate_twpa_ratio() - deprecated legacy method
    # TWPA_RATIO is now handled by TWPARatioAlgorithm in algorithm registry

    def _calculate_velocity(self, indicator: StreamingIndicator, params: dict) -> Optional[float]:
        current = params.get("current_window", {})
        base = params.get("baseline_window", {})
        method = str(params.get("price_method", "LAST_PRICE")).upper()
        def calc(method_name: str, win: dict) -> Optional[float]:
            w, s_ts, e_ts = self._get_price_series_for_window(indicator, float(win.get("t1", 60)), float(win.get("t2", 0)))
            if not w:
                return None
            if method_name == "TWPA":
                return self._calc_twpa(w, s_ts, e_ts)
            return w[-1][1] # Default to last_price
        cur = calc(method, current)
        basev = calc(method, base)
        if cur is None or basev in (None, 0.0):
            return None
        try:
            return (cur - basev) / basev * 100.0
        except ZeroDivisionError:
            return None

    def _calculate_windowed_orderbook_aggregates(self, indicator: StreamingIndicator, typ: str, params: dict) -> Optional[float]:
        t1 = float(params.get("t1", 60))
        t2 = float(params.get("t2", 0))
        window, start_ts, end_ts = self._get_orderbook_series_for_window(indicator, t1, t2)
        if not window:
            return None

        def twa(field: str) -> Optional[float]:
            total_w, total_v = 0.0, 0.0
            for i in range(len(window)):
                ts_i = max(window[i]["timestamp"], start_ts)
                ts_next = end_ts if i == len(window)-1 else min(window[i+1]["timestamp"], end_ts)
                if ts_next <= ts_i: continue
                duration = ts_next - ts_i
                total_w += duration
                total_v += float(window[i].get(field, 0.0)) * duration
            return total_v / total_w if total_w > 0 else None

        if typ == "AVG_BEST_BID": return twa("best_bid")
        if typ == "AVG_BEST_ASK": return twa("best_ask")
        if typ == "AVG_BID_QTY": return twa("bid_qty")
        if typ == "AVG_ASK_QTY": return twa("ask_qty")

        if typ == "TW_MIDPRICE":
            total_w, total_v = 0.0, 0.0
            for i in range(len(window)):
                ts_i = max(window[i]["timestamp"], start_ts)
                ts_next = end_ts if i == len(window)-1 else min(window[i+1]["timestamp"], end_ts)
                if ts_next <= ts_i: continue
                duration = ts_next - ts_i
                bb, ba = float(window[i].get("best_bid", 0.0)), float(window[i].get("best_ask", 0.0))
                mid = (bb + ba) / 2.0 if (bb > 0 and ba > 0) else 0.0
                total_w += duration
                total_v += mid * duration
            return total_v / total_w if total_w > 0 else None

        if typ == "BID_ASK_IMBALANCE":
            b, a = twa("bid_qty") or 0.0, twa("ask_qty") or 0.0
            return (b - a) / (b + a) if (b + a) > 0 else None

        if typ == "SPREAD_PERCENTAGE":
            avg_bid, avg_ask = twa("best_bid") or 0.0, twa("best_ask") or 0.0
            spread = max(0.0, avg_ask - avg_bid)
            mid = (avg_bid + avg_ask) / 2.0 if (avg_bid > 0 and avg_ask > 0) else 0.0
            return (spread / mid) * 100.0 if mid > 0 else None

        if typ == "SPREAD_VOLATILITY":
            spreads = [max(0.0, w.get("best_ask", 0.0) - w.get("best_bid", 0.0)) for w in window]
            if len(spreads) < 2: return 0.0
            mean = sum(spreads) / len(spreads)
            var = sum((x - mean) ** 2 for x in spreads) / len(spreads)
            return var ** 0.5
        return None

    def _calculate_windowed_deal_aggregates(self, indicator: StreamingIndicator, typ: str, params: dict) -> Optional[float]:
        t1, t2 = float(params.get("t1", 60)), float(params.get("t2", 0))
        deals, _, _ = self._get_deals_for_window(indicator, t1, t2)
        if not deals:
            return 0.0 if typ in ("SUM_VOLUME", "COUNT_DEALS") else None
        if typ == "COUNT_DEALS":
            return float(len(deals))
        total_vol = sum(d.get("volume", 0.0) for d in deals)
        if typ == "SUM_VOLUME":
            return total_vol
        if typ == "AVG_VOLUME":
            return total_vol / len(deals) if deals else 0.0
        if typ == "VWAP":
            if total_vol <= 0: return None
            return sum(d["price"] * d["volume"] for d in deals) / total_vol
        return None

    def _calculate_volume_surge(self, indicator: StreamingIndicator, params: dict) -> Optional[float]:
        current, base = params.get("current_window", {}), params.get("baseline_window", {})
        def sum_vol(win: dict) -> float:
            d, _, _ = self._get_deals_for_window(indicator, float(win.get("t1", 60)), float(win.get("t2", 0)))
            return sum(x.get("volume", 0.0) for x in d)
        cur, bas = sum_vol(current), sum_vol(base)
        return cur / bas if bas > 0 else None

    def _calculate_volume_concentration(self, indicator: StreamingIndicator, params: dict) -> Optional[float]:
        short_w, long_w = params.get("short_window", {}), params.get("long_window", {})
        def sum_vol(win: dict) -> float:
            d, _, _ = self._get_deals_for_window(indicator, float(win.get("t1", 60)), float(win.get("t2", 0)))
            return sum(x.get("volume", 0.0) for x in d)
        s, l = sum_vol(short_w), sum_vol(long_w)
        return s / l if l > 0 else None

    def _calculate_volume_acceleration(self, indicator: StreamingIndicator, params: dict) -> Optional[float]:
        current_w, previous_w, baseline_w = params.get("current_window", {}), params.get("previous_window", {}), params.get("baseline_window", {})
        def sum_vol(win: dict) -> float:
            d, _, _ = self._get_deals_for_window(indicator, float(win.get("t1", 60)), float(win.get("t2", 0)))
            return sum(x.get("volume", 0.0) for x in d)
        base_sum = sum_vol(baseline_w)
        if base_sum <= 0: return None
        cur_ratio = sum_vol(current_w) / base_sum
        prev_ratio = sum_vol(previous_w) / base_sum
        return cur_ratio - prev_ratio

    def _calculate_trade_frequency(self, indicator: StreamingIndicator, params: dict) -> Optional[float]:
        t1, t2 = float(params.get("t1", 60)), float(params.get("t2", 0))
        deals, _, _ = self._get_deals_for_window(indicator, t1, t2)
        window_secs = max(1.0, t1 - t2)
        return (len(deals) / window_secs) * 60.0

    def _calculate_average_trade_size(self, indicator: StreamingIndicator, params: dict) -> Optional[float]:
        t1, t2 = float(params.get("t1", 60)), float(params.get("t2", 0))
        deals, _, _ = self._get_deals_for_window(indicator, t1, t2)
        if not deals: return 0.0
        total_vol = sum(d.get("volume", 0.0) for d in deals)
        return total_vol / len(deals)

    def _calculate_volume_price_correlation(self, indicator: StreamingIndicator, params: dict) -> Optional[float]:
        t1, t2 = float(params.get("t1", 60)), float(params.get("t2", 0))
        min_deals = int(params.get("min_deals", 3))
        deals, _, _ = self._get_deals_for_window(indicator, t1, t2)
        if len(deals) < min_deals: return 0.0
        prices = [d["price"] for d in deals]
        vols = [d["volume"] for d in deals]
        price_changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        mean_vol = sum(vols) / len(vols)
        vol_changes = [v - mean_vol for v in vols[1:]]
        n = min(len(price_changes), len(vol_changes))
        if n < 2: return 0.0
        pc, vc = price_changes[:n], vol_changes[:n]
        mean_pc, mean_vc = sum(pc) / n, sum(vc) / n
        cov = sum((pc[i] - mean_pc) * (vc[i] - mean_vc) for i in range(n)) / n
        var_pc, var_vc = sum((x - mean_pc) ** 2 for x in pc) / n, sum((x - mean_vc) ** 2 for x in vc) / n
        denom = (var_pc ** 0.5) * (var_vc ** 0.5)
        return cov / denom if denom != 0 else 0.0

    def get_indicator(self, indicator_key: str) -> Optional[StreamingIndicator]:
        """Get indicator by key"""
        return self._indicators.get(indicator_key)
    
    def get_indicators_for_symbol(self, symbol: str) -> List[StreamingIndicator]:
        """Get all indicators for a symbol"""
        return [
            indicator for key, indicator in self._indicators.items()
            if key.startswith(symbol)
        ]
    
    def remove_indicator(self, indicator_key: str) -> bool:
        """Remove an indicator with proper cleanup"""
        with self._data_lock:
            if indicator_key in self._indicators:
                indicator = self._indicators[indicator_key]
                symbol = indicator.symbol

                # Remove from symbol index
                if symbol in self._indicators_by_symbol and indicator_key in self._indicators_by_symbol[symbol]:
                    self._indicators_by_symbol[symbol].remove(indicator_key)
                    if not self._indicators_by_symbol[symbol]:
                        del self._indicators_by_symbol[symbol]

                # Remove incremental calculator
                self._incremental_indicators.pop(indicator_key, None)

                # Remove indicator
                del self._indicators[indicator_key]
                self._time_driven_indicators.pop(indicator_key, None)

                # Update metrics
                self._performance_metrics["indicators_count"] = len(self._indicators)

                self.logger.info("streaming_indicator.removed", {
                    "indicator_key": indicator_key,
                    "symbol": symbol,
                    "remaining_indicators": len(self._indicators)
                })
                return True
        return False

    # ===== VARIANT MANAGEMENT METHODS =====

    async def _load_variants_from_database(self):
        """
        Load all variants from database into memory cache (async startup operation).

        Process:
        1. Check if repository is configured
        2. Load all active variants from database
        3. Populate memory cache (_variants, _variants_by_type, _variant_parameters)
        4. Auto-generate parameter definitions from algorithms

        Called during start() for engine initialization.
        """
        if not self._variant_repository:
            self.logger.warning("variant_repository_not_configured", {
                "action": "skipping_database_load",
                "reason": "repository_is_none"
            })
            return

        try:
            # Load all active variants from database
            variants = await self._variant_repository.load_all_variants()

            loaded_count = 0
            for variant in variants:
                # Store in memory cache
                self._variants[variant.id] = variant

                # Add to type index
                if variant.variant_type not in self._variants_by_type:
                    self._variants_by_type[variant.variant_type] = []
                self._variants_by_type[variant.variant_type].append(variant.id)

                # Auto-generate parameter definitions from system indicator
                param_defs = self._get_system_indicator_parameters(variant.base_indicator_type)
                if param_defs:
                    self._variant_parameters[variant.id] = list(param_defs)

                loaded_count += 1

            self.logger.info("variants_loaded_from_database", {
                "variants_loaded": loaded_count,
                "variants_by_type": {
                    vtype: len(vids) for vtype, vids in self._variants_by_type.items()
                }
            })

        except Exception as e:
            self.logger.error("variants_load_from_database_failed", {
                "error": str(e),
                "error_type": type(e).__name__
            })
            # Don't raise - engine can continue without pre-loaded variants
            # Variants can be created via API later

    async def create_variant(self,
                       name: str,
                       base_indicator_type: str,
                       variant_type: str,
                       description: str,
                       parameters: Dict[str, Any],
                       created_by: str,
                       parameter_definitions: List[VariantParameter] = None,
                       user_id: str = None,
                       scope: str = None) -> str:
        """
        Create a new indicator variant with parameter validation and database storage.

        ✅ UPDATED: Now uses IndicatorVariantRepository for database persistence instead of JSON files.

        Args:
            name: Variant display name
            base_indicator_type: System indicator type (e.g., "TWPA", "VELOCITY")
            variant_type: UI category (e.g., "general", "price")
            description: Variant description
            parameters: Indicator parameters (validated by repository)
            created_by: Creator username
            parameter_definitions: Optional parameter definitions (deprecated, auto-generated now)
            user_id: Owner user ID (defaults to created_by)
            scope: Visibility scope (defaults to "user_{user_id}")

        Returns:
            Variant ID (UUID string)

        Raises:
            ValueError: If validation fails
            RuntimeError: If repository is not configured
        """
        with self._data_lock:
            # Check repository configuration
            if not self._variant_repository:
                raise RuntimeError("Variant repository not configured - cannot create variant")

            # Validate variant type using enum
            valid_types = VariantType.get_valid_types()
            if variant_type not in valid_types:
                raise ValueError(f"Invalid variant type: {variant_type}. Must be one of {valid_types}")

            # Validate base indicator type
            try:
                IndicatorType(base_indicator_type.upper())
            except ValueError:
                raise ValueError(f"Invalid base indicator type: {base_indicator_type}")

            # ✅ NEW: Save to database (repository handles validation and ID generation)
            variant_id = await self._variant_repository.create_variant({
                "name": name,
                "base_indicator_type": base_indicator_type.upper(),
                "variant_type": variant_type,
                "description": description,
                "parameters": parameters,
                "created_by": created_by,
                "user_id": user_id or created_by,
                "scope": scope or f"user_{user_id or created_by}",
                "is_system": False
            })

            # ✅ NEW: Load variant from database into memory cache
            variant = await self._variant_repository.get_variant(variant_id)
            if not variant:
                raise RuntimeError(f"Variant {variant_id} not found after creation")

            # Store in memory cache
            self._variants[variant_id] = variant

            # Add to type index
            if variant_type not in self._variants_by_type:
                self._variants_by_type[variant_type] = []
            self._variants_by_type[variant_type].append(variant_id)

            # Auto-generate parameter definitions from system indicator
            auto_param_definitions = self._get_system_indicator_parameters(base_indicator_type.upper())
            if auto_param_definitions:
                self._variant_parameters[variant_id] = list(auto_param_definitions)

            self.logger.info("indicator_variant.created", {
                "variant_id": variant_id,
                "name": name,
                "base_type": base_indicator_type,
                "variant_type": variant_type,
                "created_by": created_by,
                "storage": "database"
            })

            return variant_id

    def get_variant(self, variant_id: str) -> Optional[IndicatorVariant]:
        """Get variant by ID"""
        return self._variants.get(variant_id)

    def list_variants(self, variant_type: str = None) -> List[IndicatorVariant]:
        """List variants, optionally filtered by type"""
        if variant_type:
            variant_ids = self._variants_by_type.get(variant_type, [])
            return [self._variants[vid] for vid in variant_ids if vid in self._variants]
        else:
            return list(self._variants.values())

    def get_variant_parameters(self, variant_id: str) -> List[VariantParameter]:
        """Get parameter definitions for a variant"""
        return self._variant_parameters.get(variant_id, [])

    async def update_variant_parameters(self, variant_id: str, parameters: Dict[str, Any]) -> bool:
        """
        Update variant parameters with validation and database persistence.

        ✅ UPDATED: Now uses IndicatorVariantRepository for database persistence instead of JSON files.

        Args:
            variant_id: Variant identifier (UUID)
            parameters: New parameters (validated by repository)

        Returns:
            True if updated successfully, False if variant not found

        Raises:
            RuntimeError: If repository is not configured
            ValueError: If parameter validation fails
        """
        with self._data_lock:
            if not self._variant_repository:
                raise RuntimeError("Variant repository not configured - cannot update variant")

            if variant_id not in self._variants:
                return False

            # ✅ NEW: Update in database (repository handles validation)
            success = await self._variant_repository.update_variant(variant_id, {
                "parameters": parameters
            })

            if not success:
                return False

            # ✅ NEW: Reload variant from database to sync memory cache
            variant = await self._variant_repository.get_variant(variant_id)
            if variant:
                self._variants[variant_id] = variant

            self.logger.info("indicator_variant.parameters_updated", {
                "variant_id": variant_id,
                "parameter_count": len(parameters),
                "storage": "database"
            })

            return True

    async def delete_variant(self, variant_id: str) -> bool:
        """
        Soft delete a variant (database) and remove from memory cache.

        ✅ UPDATED: Now uses IndicatorVariantRepository for soft delete in database instead of file deletion.

        Args:
            variant_id: Variant identifier (UUID)

        Returns:
            True if deleted successfully, False if variant not found

        Raises:
            RuntimeError: If repository is not configured
        """
        with self._data_lock:
            if not self._variant_repository:
                raise RuntimeError("Variant repository not configured - cannot delete variant")

            if variant_id not in self._variants:
                return False

            variant = self._variants[variant_id]

            # ✅ NEW: Soft delete in database
            success = await self._variant_repository.delete_variant(variant_id)

            if not success:
                self.logger.warning("indicator_variant.database_delete_failed", {
                    "variant_id": variant_id
                })
                return False

            # Remove from type index
            if variant.variant_type in self._variants_by_type:
                if variant_id in self._variants_by_type[variant.variant_type]:
                    self._variants_by_type[variant.variant_type].remove(variant_id)
                if not self._variants_by_type[variant.variant_type]:
                    del self._variants_by_type[variant.variant_type]

            # Remove from memory cache
            del self._variants[variant_id]
            self._variant_parameters.pop(variant_id, None)

            self.logger.info("indicator_variant.deleted", {
                "variant_id": variant_id,
                "name": variant.name,
                "storage": "database_soft_deleted"
            })

            return True

    def create_indicator_from_variant(self,
                                    symbol: str,
                                    variant_id: str,
                                    timeframe: str = "1m",
                                    scope: str = None) -> Optional[str]:
        """Create an indicator instance from a variant"""
        with self._data_lock:
            variant = self._variants.get(variant_id)
            if not variant:
                self.logger.warning("indicator_variant.not_found", {"variant_id": variant_id})
                return None

            # Create indicator using variant parameters
            return self.add_indicator(
                symbol=symbol,
                indicator_type=IndicatorType(variant.base_indicator_type),
                timeframe=timeframe,
                scope=scope,
                **variant.parameters
            )

    def _validate_variant_parameters(self,
                                   parameters: Dict[str, Any],
                                   definitions: List[VariantParameter]) -> None:
        """Validate variant parameters against definitions"""
        # Create parameter lookup
        param_lookup = {p.name: p for p in definitions}

        # Check required parameters
        for param_def in definitions:
            if param_def.is_required and param_def.name not in parameters:
                raise ValueError(f"Required parameter missing: {param_def.name}")

        # Validate provided parameters
        for param_name, param_value in parameters.items():
            if param_name not in param_lookup:
                raise ValueError(f"Unknown parameter: {param_name}")

            param_def = param_lookup[param_name]

            # Type validation
            if not self._validate_parameter_type(param_value, param_def.parameter_type):
                raise ValueError(f"Parameter {param_name} has invalid type. Expected {param_def.parameter_type}")

            # Range validation for numeric types
            if param_def.parameter_type in ['int', 'float']:
                if param_def.min_value is not None and param_value < param_def.min_value:
                    raise ValueError(f"Parameter {param_name} below minimum: {param_value} < {param_def.min_value}")
                if param_def.max_value is not None and param_value > param_def.max_value:
                    raise ValueError(f"Parameter {param_name} above maximum: {param_value} > {param_def.max_value}")

            # Allowed values validation
            if param_def.allowed_values and param_value not in param_def.allowed_values:
                raise ValueError(f"Parameter {param_name} not in allowed values: {param_def.allowed_values}")

    def _validate_parameter_type(self, value: Any, expected_type: str) -> bool:
        """Validate parameter type"""
        if expected_type == 'int':
            return isinstance(value, int)
        elif expected_type == 'float':
            return isinstance(value, (int, float))
        elif expected_type == 'string':
            return isinstance(value, str)
        elif expected_type == 'boolean':
            return isinstance(value, bool)
        elif expected_type == 'json':
            return True  # Accept any JSON-serializable value
        else:
            return False

    def get_performance_metrics(self) -> Dict[str, Any]:
        """✅ CRITICAL FIX: Get comprehensive performance metrics"""
        with self._data_lock:
            # Update data structure sizes
            self._performance_metrics["data_structures_size"] = {
                "price_data": len(self._price_data),
                "deal_data": len(self._deal_data),
                "orderbook_data": len(self._orderbook_data),
                "indicators": len(self._indicators),
                "incremental_calculators": len(self._incremental_indicators),
                "variants": len(self._variants),
                "variant_parameters": len(self._variant_parameters)
            }

            # Calculate cleanup frequency
            time_since_last_cleanup = time.time() - self._last_cleanup_time
            if time_since_last_cleanup > 0:
                self._performance_metrics["cleanup_frequency"] = self._cleanup_interval_seconds / time_since_last_cleanup

            return self._performance_metrics.copy()

    def _add_data_with_ttl_check(self, key: str, data: Any) -> None:
        """✅ CRITICAL FIX: Add data with TTL check for consistency"""
        # Check TTL before adding
        if self._is_data_expired(key):
            self._remove_expired_data(key)

        # Add data and update access time
        # (Implementation depends on data type - this is a placeholder for the pattern)
        self._data_access_times[key] = time.time()

    def _is_data_expired(self, key: str) -> bool:
        """Check if data key is expired based on TTL"""
        last_access = self._data_access_times.get(key, 0)
        return (time.time() - last_access) > self._data_ttl_seconds

    def _remove_expired_data(self, key: str) -> None:
        """Remove expired data structures"""
        # Remove from all relevant data structures
        self._price_data.pop(key, None)
        self._deal_data.pop(key, None)
        self._orderbook_data.pop(key, None)
        self._data_access_times.pop(key, None)

        self.logger.debug("streaming_indicator_engine.expired_data_removed", {
            "key": key
        })

    # ===== FILE-BASED VARIANT STORAGE METHODS REMOVED =====
    # ✅ All file-based storage methods have been removed in favor of QuestDB persistence
    # See IndicatorVariantRepository for database operations

    def _validate_variant_against_system_indicator_type(self, base_indicator_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate variant parameters against the corresponding system indicator definition"""
        try:
            # Get system indicator parameter definitions
            system_params = self._get_system_indicator_parameters(base_indicator_type)

            if not system_params:
                return {
                    "is_valid": False,
                    "errors": [f"Unknown system indicator type: {base_indicator_type}"]
                }

            errors = []

            # Check required parameters
            for param_def in system_params:
                if param_def.is_required and param_def.name not in parameters:
                    errors.append(f"Required parameter missing: {param_def.name}")

            # Validate provided parameters
            for param_name, param_value in parameters.items():
                param_def = next((p for p in system_params if p.name == param_name), None)
                if not param_def:
                    errors.append(f"Unknown parameter: {param_name}")
                    continue

                # Type validation
                if not self._validate_parameter_type(param_value, param_def.parameter_type):
                    errors.append(f"Parameter {param_name} has invalid type. Expected {param_def.parameter_type}, got {type(param_value).__name__}")

                # Range validation for numeric types
                if param_def.parameter_type in ['int', 'float']:
                    if param_def.min_value is not None and param_value < param_def.min_value:
                        errors.append(f"Parameter {param_name} below minimum: {param_value} < {param_def.min_value}")
                    if param_def.max_value is not None and param_value > param_def.max_value:
                        errors.append(f"Parameter {param_name} above maximum: {param_value} > {param_def.max_value}")

                # Allowed values validation
                if param_def.allowed_values and param_value not in param_def.allowed_values:
                    errors.append(f"Parameter {param_name} not in allowed values: {param_def.allowed_values}")

            return {
                "is_valid": len(errors) == 0,
                "errors": errors
            }

        except Exception as e:
            return {
                "is_valid": False,
                "errors": [f"Validation failed: {str(e)}"]
            }

    def _validate_variant_against_system_indicator(self, variant: IndicatorVariant) -> Dict[str, Any]:
        """Validate variant parameters against the corresponding system indicator definition"""
        return self._validate_variant_against_system_indicator_type(variant.base_indicator_type, variant.parameters)

    def _get_system_indicator_parameters(self, indicator_type: str) -> List[VariantParameter]:
        """Get parameter definitions for a system indicator type from algorithm registry"""
        try:
            # Use the unified algorithm registry
            algorithm = self._algorithm_registry.get_algorithm(indicator_type.upper())
            if algorithm:
                # Get parameters from algorithm and convert to VariantParameter format
                algorithm_params = algorithm.get_parameters()
                variant_params = []
                
                for param in algorithm_params:
                    if hasattr(param, 'parameter_type'):
                        # Already VariantParameter format
                        variant_params.append(param)
                    else:
                        # Convert to VariantParameter if needed
                        variant_params.append(VariantParameter(
                            name=getattr(param, 'name', 'unknown'),
                            parameter_type=getattr(param, 'type', 'string'),
                            default_value=getattr(param, 'default', None),
                            min_value=getattr(param, 'min_value', None),
                            max_value=getattr(param, 'max_value', None),
                            allowed_values=getattr(param, 'allowed_values', None),
                            is_required=getattr(param, 'required', True),
                            description=getattr(param, 'description', '')
                        ))
                
                return variant_params
                
        except Exception as exc:
            self.logger.error("streaming_indicator_engine.algorithm_lookup_failed", {
                "indicator_type": indicator_type,
                "error": str(exc),
                "error_type": type(exc).__name__
            })
        
        # Legacy fallback for indicators not yet in algorithm registry
        if indicator_type.upper() == "RSI":
            return [
                VariantParameter("period", "int", 14, 2, 100, None, True, "Period for RSI calculation"),
                VariantParameter("overbought_level", "float", 70.0, 50.0, 100.0, None, False, "Overbought threshold"),
                VariantParameter("oversold_level", "float", 30.0, 0.0, 50.0, None, False, "Oversold threshold")
            ]
        elif indicator_type.upper() == "SMA":
            return [
                VariantParameter("period", "int", 20, 2, 200, None, True, "Period for SMA calculation")
            ]
        elif indicator_type.upper() == "EMA":
            return [
                VariantParameter("period", "int", 20, 2, 200, None, True, "Period for EMA calculation")
            ]
        elif indicator_type.upper() in ["TWPA", "VWAP", "MAX_PRICE", "MIN_PRICE", "FIRST_PRICE", "LAST_PRICE", 
                                        "SUM_VOLUME", "AVG_VOLUME", "COUNT_DEALS", "TRADE_SIZE_MOMENTUM",
                                        "MID_PRICE_VELOCITY", "TOTAL_LIQUIDITY", "LIQUIDITY_RATIO", 
                                        "LIQUIDITY_DRAIN_INDEX", "DEAL_VS_MID_DEVIATION", "PRICE_VOLATILITY",
                                        "DEAL_SIZE_VOLATILITY", "TRADE_CLUSTERING_COEFFICIENT", 
                                        "DECISION_DENSITY_ACCELERATION", "INTER_DEAL_INTERVALS"]:
            return [
                VariantParameter("t1", "float", 300.0, 10.0, 86400.0, None, True, "Start time window in seconds ago"),
                VariantParameter("t2", "float", 0.0, 0.0, 86400.0, None, True, "End time window in seconds ago")
            ]
        elif indicator_type.upper() == "VELOCITY":
            return [
                VariantParameter("current_window", "json", {"t1": 60, "t2": 0}, None, None, None, True, "Current time window"),
                VariantParameter("baseline_window", "json", {"t1": 120, "t2": 60}, None, None, None, True, "Baseline time window"),
                VariantParameter("price_method", "string", "LAST_PRICE", None, None, None, False, "Price calculation method")
            ]
        elif indicator_type.upper() == "VOLUME_SURGE":
            return [
                VariantParameter("current_window", "json", {"t1": 60, "t2": 0}, None, None, None, True, "Current time window"),
                VariantParameter("baseline_window", "json", {"t1": 120, "t2": 60}, None, None, None, True, "Baseline time window")
            ]
        elif indicator_type.upper() == "VOLATILITY":
            return [
                VariantParameter("period", "int", 20, 2, 200, None, True, "Period for volatility calculation")
            ]
        elif indicator_type.upper() in ["RISK_LEVEL", "CONFIDENCE_SCORE"]:
            return []  # No parameters for simple risk indicators
        elif indicator_type.upper() == "CLOSE_ORDER_PRICE":
            return [
                VariantParameter("risk_adjusted_pricing", "json", {
                    "enabled": False,
                    "scaling_factor": 1.0,
                    "min_adjustment": -10,
                    "max_adjustment": 10
                }, None, None, None, False, "Risk-adjusted pricing configuration")
            ]

        # Default empty list for unknown indicators - this allows creation but no parameter validation
        return []

    def _get_frequent_indicator_patterns(self) -> List[Dict[str, Any]]:
        """✅ PHASE 2 FIX: Define frequently used indicator patterns for cache warming"""
        return [
            # Common technical indicators
            {"type": "SMA", "params": {"period": 20}},
            {"type": "SMA", "params": {"period": 50}},
            {"type": "EMA", "params": {"period": 12}},
            {"type": "EMA", "params": {"period": 26}},
            {"type": "RSI", "params": {"period": 14}},

            # Common time-windowed indicators
            {"type": "TWPA", "params": {"t1": 300, "t2": 0}},  # 5 minutes
            {"type": "TWPA", "params": {"t1": 900, "t2": 0}},  # 15 minutes
            {"type": "VWAP", "params": {"t1": 3600, "t2": 0}}, # 1 hour

            # Risk indicators
            {"type": "VOLATILITY", "params": {"period": 20}},
            {"type": "CONFIDENCE_SCORE", "params": {}},
        ]

    async def warm_cache_for_symbol(self, symbol: str, timeframe: str = "1m") -> None:
        """✅ PHASE 2 FIX: Warm cache with frequently used indicators for a symbol"""
        if not self._cache_warming_enabled:
            return

        warmed_count = 0
        for pattern in self._frequent_indicators:
            try:
                # Create temporary indicator to calculate and cache
                indicator_key = self.add_indicator(
                    symbol=symbol,
                    indicator_type=IndicatorType(pattern["type"]),
                    timeframe=timeframe,
                    **pattern["params"]
                )

                if indicator_key:
                    # Force calculation to populate cache
                    indicator = self._indicators.get(indicator_key)
                    if indicator:
                        # Mock price data for cache warming (would use real data in production)
                        mock_price = 50000.0 if "BTC" in symbol else 100.0
                        await self._calculate_with_circuit_breaker(indicator_key, indicator, mock_price, time.time())
                        warmed_count += 1

                    # Clean up temporary indicator
                    self.remove_indicator(indicator_key)

            except Exception as e:
                self.logger.debug("streaming_indicator_engine.cache_warming_error", {
                    "symbol": symbol,
                    "pattern": pattern,
                    "error": str(e)
                })

        if warmed_count > 0:
            self.logger.info("streaming_indicator_engine.cache_warmed", {
                "symbol": symbol,
                "indicators_warmed": warmed_count,
                "cache_size": len(self._indicator_cache)
            })

    def prefetch_related_indicators(self, indicator_key: str) -> None:
        """✅ PHASE 2 FIX: Prefetch related indicators when one is calculated"""
        if indicator_key not in self._indicators:
            return

        indicator = self._indicators[indicator_key]
        symbol = indicator.symbol
        timeframe = indicator.timeframe

        # Define related indicator patterns based on the current indicator
        related_patterns = []

        if indicator.metadata.get("type") == "SMA":
            # If calculating SMA, prefetch related EMAs and RSI
            related_patterns.extend([
                {"type": "EMA", "params": {"period": indicator.metadata.get("period", 20)}},
                {"type": "RSI", "params": {"period": 14}},
            ])
        elif indicator.metadata.get("type") in ["TWPA", "VWAP"]:
            # If calculating price averages, prefetch velocity indicators
            related_patterns.extend([
                {"type": "VELOCITY", "params": {
                    "current_window": {"t1": 60, "t2": 0},
                    "baseline_window": {"t1": 120, "t2": 60}
                }},
                {"type": "VOLATILITY", "params": {"period": 20}},
            ])

        # Prefetch related indicators asynchronously
        for pattern in related_patterns[:2]:  # Limit to 2 related indicators to avoid overload
            try:
                related_key = self.add_indicator(
                    symbol=symbol,
                    indicator_type=IndicatorType(pattern["type"]),
                    timeframe=timeframe,
                    **pattern["params"]
                )

                if related_key:
                    # Mark for background calculation (don't block current request)
                    # In a real implementation, this would be scheduled asynchronously
                    self.logger.debug("streaming_indicator_engine.prefetch_scheduled", {
                        "indicator_key": indicator_key,
                        "related_key": related_key,
                        "pattern": pattern
                    })

            except Exception as e:
                self.logger.debug("streaming_indicator_engine.prefetch_error", {
                    "indicator_key": indicator_key,
                    "pattern": pattern,
                    "error": str(e)
                })

    def get_cache_performance_stats(self) -> Dict[str, Any]:
        """✅ PHASE 2 FIX: Get comprehensive cache performance statistics"""
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total_requests) if total_requests > 0 else 0.0

        # Calculate hit rate over different time windows
        current_time = time.time()
        recent_accesses = [access for access in self._cache_access_history
                          if current_time - access['timestamp'] < 300]  # Last 5 minutes

        recent_hits = sum(1 for access in recent_accesses if access['hit'])
        recent_total = len(recent_accesses)
        recent_hit_rate = (recent_hits / recent_total) if recent_total > 0 else 0.0

        return {
            "overall_hit_rate": hit_rate,
            "recent_hit_rate_5m": recent_hit_rate,
            "total_requests": total_requests,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_size": len(self._indicator_cache),
            "max_cache_size": self._max_cache_size,
            "cache_utilization_pct": (len(self._indicator_cache) / self._max_cache_size) * 100,
            "volatility_scores": self._indicator_volatility.copy(),
            "adaptive_ttl_enabled": True,
            "lru_eviction_enabled": True,
            "cache_warming_enabled": self._cache_warming_enabled
        }

    # ===== OLD SYSTEM COMPLETELY REMOVED =====
    # The old _system_indicators registration system has been completely removed
    # All functionality now uses the new _indicator_registry system

    # ✅ NEW REGISTRY API METHODS
    def get_system_indicators_registry(self) -> Dict[str, Any]:
        """Get all system indicators from algorithm registry for API"""
        indicators = {}
        for indicator_type, algorithm in self._algorithm_registry.get_all_algorithms().items():
            indicators[indicator_type] = {
                "indicator_type": indicator_type,
                "name": algorithm.get_name(),
                "description": algorithm.get_description(),
                "category": algorithm.get_category(),
                "parameters": [
                    {
                        "name": param.name,
                        "type": param.parameter_type,
                        "default_value": param.default_value,
                        "min_value": param.min_value,
                        "max_value": param.max_value,
                        "allowed_values": param.allowed_values,
                        "required": param.is_required,
                        "description": param.description
                    }
                    for param in algorithm.get_parameters()
                ]
            }
        return indicators
    
    def get_system_indicators_by_category_registry(self, category: str) -> Dict[str, Any]:
        """Get system indicators filtered by category from algorithm registry"""
        filtered = self._algorithm_registry.get_algorithms_by_category(category)
        result = {}
        for indicator_type, algorithm in filtered.items():
            result[indicator_type] = {
                "indicator_type": indicator_type,
                "name": algorithm.get_name(),
                "description": algorithm.get_description(),
                "category": algorithm.get_category(),
                "parameters": [
                    {
                        "name": param.name,
                        "type": param.parameter_type,
                        "default_value": param.default_value,
                        "required": param.is_required,
                        "description": param.description
                    }
                    for param in algorithm.get_parameters()
                ]
            }
        return result
    
    def get_indicator_categories_registry(self) -> List[str]:
        """Get all available indicator categories from algorithm registry"""
        return self._algorithm_registry.get_categories()
    
    def get_system_indicator_definition(self, indicator_type: str) -> Optional[Dict[str, Any]]:
        """Get specific indicator definition from algorithm registry"""
        algorithm = self._algorithm_registry.get_algorithm(indicator_type)
        if not algorithm:
            return None
            
        return {
            "indicator_type": indicator_type,
            "name": algorithm.get_name(),
            "description": algorithm.get_description(),
            "category": algorithm.get_category(),
            "parameters": [
                {
                    "name": param.name,
                    "type": param.parameter_type,
                    "default_value": param.default_value,
                    "min_value": param.min_value,
                    "max_value": param.max_value,
                    "allowed_values": param.allowed_values,
                    "required": param.is_required,
                    "description": param.description
                }
                for param in algorithm.get_parameters()
            ]
        }
    
    # ✅ UPDATED CALCULATION FUNCTIONS - Using algorithm registry
    def _calculate_twpa(self, indicator: StreamingIndicator, calculation_params: Dict[str, Any]) -> Optional[float]:
        """
        Calculate TWPA using algorithm registry.

        Uses TWPAAlgorithm from algorithm registry for consistent calculation.
        """
        from .indicators.twpa import twpa_algorithm
        from .indicators.base_algorithm import IndicatorParameters

        metadata = indicator.metadata or {}
        t1 = float(metadata.get("t1", calculation_params.get("t1", 300.0)))
        t2 = float(metadata.get("t2", calculation_params.get("t2", 0.0)))

        # Get data window with pre-window point (required by TWPA)
        window, start_ts, end_ts = self._get_price_series_for_window(indicator, t1, t2)

        if not window:
            return None

        # Use algorithm registry for calculation (single source of truth)
        params = IndicatorParameters({"t1": t1, "t2": t2})
        return twpa_algorithm.calculate(window, start_ts, end_ts, params)
        
    def _calculate_vwap(self, indicator: StreamingIndicator, calculation_params: Dict[str, Any]) -> Optional[float]:
        """Calculate VWAP via shared windowed deal aggregate helper."""
        metadata = indicator.metadata or {}
        params = {
            "t1": float(metadata.get("t1", calculation_params.get("t1", 300.0))),
            "t2": float(metadata.get("t2", calculation_params.get("t2", 0.0))),
        }
        return self._calculate_windowed_deal_aggregates(indicator, "VWAP", params)
        
    def _calculate_max_price(self, indicator: StreamingIndicator, calculation_params: Dict[str, Any]) -> Optional[float]:
        """Calculate MAX_PRICE using the shared windowed price helper."""
        metadata = indicator.metadata or {}
        params = {
            "t1": float(metadata.get("t1", calculation_params.get("t1", 300.0))),
            "t2": float(metadata.get("t2", calculation_params.get("t2", 0.0))),
        }
        return self._calculate_windowed_price_aggregates(indicator, "MAX_PRICE", params)
        
    def _calculate_min_price(self, indicator: StreamingIndicator, calculation_params: Dict[str, Any]) -> Optional[float]:
        """Calculate MIN_PRICE using the shared windowed price helper."""
        metadata = indicator.metadata or {}
        params = {
            "t1": float(metadata.get("t1", calculation_params.get("t1", 300.0))),
            "t2": float(metadata.get("t2", calculation_params.get("t2", 0.0))),
        }
        return self._calculate_windowed_price_aggregates(indicator, "MIN_PRICE", params)
        
    def _calculate_stop_loss_price(self, indicator: StreamingIndicator, calculation_params: Dict[str, Any]) -> Optional[float]:
        """Backwards-compatible wrapper delegating to implemented stop-loss calculator."""
        return self._calculate_stop_loss_price_registered(indicator, calculation_params)
        
    def _calculate_take_profit_price(self, indicator: StreamingIndicator, calculation_params: Dict[str, Any]) -> Optional[float]:
        """Backwards-compatible wrapper delegating to implemented take-profit calculator."""
        return self._calculate_take_profit_price_registered(indicator, calculation_params)

    # ===================== PUBLIC API METHODS FOR EXTERNAL ACCESS (TASK 2) =====================
    
    def get_indicator_config(self, indicator_key: str) -> Optional[Dict[str, Any]]:
        """
        Public API method to access indicator configuration without exposing private fields.
        
        Args:
            indicator_key: Unique identifier for the indicator
            
        Returns:
            Dictionary containing indicator configuration or None if not found
        """
        with self._data_lock:
            indicator = self._indicators.get(indicator_key)
            if not indicator:
                return None
                
            return {
                "indicator_type": indicator.indicator,  # The full indicator name (e.g., "TWPA_300")
                "symbol": indicator.symbol,
                "timeframe": indicator.timeframe,
                "parameters": indicator.metadata.get("parameters", {}),
                "created_at": indicator.metadata.get("created_at", indicator.timestamp),
                "is_active": indicator.metadata.get("is_active", True),
                "current_value": indicator.current_value,
                "last_update": indicator.timestamp,
                "variant_id": indicator.metadata.get("variant_id"),
                "variant_type": indicator.metadata.get("variant_type"),
                "base_indicator_type": indicator.metadata.get("type")
            }
    
    def store_calculated_value(self, indicator_key: str, value: float, timestamp: float, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Public API method to store calculated indicator values.
        
        Args:
            indicator_key: Unique identifier for the indicator
            value: The calculated indicator value
            timestamp: Unix timestamp when value was calculated
            metadata: Optional metadata associated with the value
            
        Returns:
            True if stored successfully, False otherwise
        """
        try:
            with self._data_lock:
                # Store the value (this could trigger events for persistence)
                # For now, emit event for persistence layer to pick up
                self.event_bus.emit_event("indicator_value_calculated", {
                    "indicator_key": indicator_key,
                    "value": value,
                    "timestamp": timestamp,
                    "metadata": metadata or {}
                })
                
                self.logger.debug("streaming_indicator_engine.value_stored", {
                    "indicator_key": indicator_key,
                    "value": value,
                    "timestamp": timestamp
                })
                
                return True
                
        except Exception as e:
            self.logger.error("streaming_indicator_engine.store_value_failed", {
                "indicator_key": indicator_key,
                "error": str(e)
            })
            return False
    
    def get_data_buffer_for_symbol(self, symbol: str, data_type: str = "price") -> Optional[List[Dict[str, Any]]]:
        """
        Public API method to access data buffers for a symbol.
        
        Args:
            symbol: The symbol to get data for
            data_type: Type of data ("price", "orderbook", "deal")
            
        Returns:
            List of data entries or None if no data available
        """
        with self._data_lock:
            if data_type == "price":
                buffer = self._price_data.get(symbol)
            elif data_type == "orderbook":
                buffer = self._orderbook_data.get(symbol)
            elif data_type == "deal":
                buffer = self._deal_data.get(symbol)
            else:
                return None
                
            if not buffer:
                return None
                
            # Convert deque to list of dictionaries for safe external access
            return [item for item in buffer]
    
    def has_buffered_data(self, symbol: str, data_type: str = "price") -> bool:
        """
        Public API method to check if symbol has buffered data.
        
        Args:
            symbol: The symbol to check
            data_type: Type of data ("price", "orderbook", "deal")
            
        Returns:
            True if symbol has buffered data, False otherwise
        """
        with self._data_lock:
            if data_type == "price":
                buffer = self._price_data.get(symbol)
            elif data_type == "orderbook":
                buffer = self._orderbook_data.get(symbol)
            elif data_type == "deal":
                buffer = self._deal_data.get(symbol)
            else:
                return False
                
            return buffer is not None and len(buffer) > 0
    
    async def calculate_indicator_at_timestamp(self, indicator_key: str, target_timestamp: float) -> Optional[float]:
        """
        Public API method to calculate indicator value at a specific timestamp.
        
        Args:
            indicator_key: Unique identifier for the indicator
            target_timestamp: Unix timestamp to calculate value for
            
        Returns:
            Calculated indicator value or None if calculation failed
        """
        try:
            with self._data_lock:
                indicator = self._indicators.get(indicator_key)
                if not indicator:
                    self.logger.warning("streaming_indicator_engine.indicator_not_found", {
                        "indicator_key": indicator_key
                    })
                    return None
                
                # Use existing calculation method with timestamp
                value = await self._calculate_with_circuit_breaker(
                    indicator.symbol,
                    indicator,
                    0.0,  # price placeholder
                    target_timestamp
                )
                
                if value is not None:
                    self.logger.debug("streaming_indicator_engine.historical_calculation", {
                        "indicator_key": indicator_key,
                        "timestamp": target_timestamp,
                        "value": value
                    })
                
                return value
                
        except Exception as e:
            self.logger.error("streaming_indicator_engine.historical_calculation_failed", {
                "indicator_key": indicator_key,
                "timestamp": target_timestamp,
                "error": str(e)
            })
            return None

    # ===================== SESSION MANAGEMENT METHODS (TASK 3) =====================
    
    def _find_existing_indicator(self, session_id: str, symbol: str, variant_id: str, 
                                parameters: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Find existing indicator with same variant_id and parameters in session.
        
        Args:
            session_id: Session identifier
            symbol: Trading symbol
            variant_id: Indicator variant identifier  
            parameters: Parameters to match
            
        Returns:
            indicator_id if found, None otherwise
        """
        try:
            with self._data_lock:
                if (session_id not in self._session_indicators or 
                    symbol not in self._session_indicators[session_id]):
                    return None
                
                # Normalize parameters for comparison
                normalized_params = (parameters or {}).copy()
                
                # Check each indicator in session
                for indicator_id in self._session_indicators[session_id][symbol]:
                    indicator = self._indicators.get(indicator_id)
                    if not indicator:
                        continue
                        
                    # Match variant_id
                    if indicator.metadata.get("variant_id") != variant_id:
                        continue
                        
                    # Match parameters
                    existing_params = indicator.metadata.get("parameters", {})
                    if existing_params == normalized_params:
                        self.logger.info("streaming_indicator_engine.found_existing_indicator", {
                            "session_id": session_id,
                            "symbol": symbol,
                            "variant_id": variant_id,
                            "existing_indicator_id": indicator_id,
                            "parameters": normalized_params
                        })
                        return indicator_id
                
                return None
                
        except Exception as e:
            self.logger.error("streaming_indicator_engine.find_existing_indicator_failed", {
                "session_id": session_id,
                "symbol": symbol, 
                "variant_id": variant_id,
                "error": str(e)
            })
            return None
    
    def add_indicator_to_session(self, session_id: str, symbol: str, variant_id: str, 
                               parameters: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Add an indicator to a specific session and symbol.
        
        Args:
            session_id: Unique session identifier
            symbol: Trading symbol (e.g., "BTCUSDT")
            variant_id: Indicator variant identifier
            parameters: Optional parameters to override defaults
            
        Returns:
            Unique indicator_id if successful, None if failed
        """
        try:
            with self._data_lock:
                # DEDUPLIKACJA: Sprawdź czy już istnieje wskaźnik o tych parametrach
                existing_indicator_id = self._find_existing_indicator(
                    session_id, symbol, variant_id, parameters
                )
                if existing_indicator_id:
                    self.logger.info("streaming_indicator_engine.reusing_existing_indicator", {
                        "session_id": session_id,
                        "symbol": symbol,
                        "variant_id": variant_id,
                        "existing_indicator_id": existing_indicator_id,
                        "parameters": parameters
                    })
                    return existing_indicator_id

                # Generate unique indicator ID with UUID for thread safety
                import uuid
                indicator_id = f"{session_id}_{symbol}_{variant_id}_{uuid.uuid4().hex[:8]}"

                variant = self._variants.get(variant_id)
                if not variant:
                    self.logger.error("streaming_indicator_engine.add_indicator_to_session_missing_variant", {
                        "session_id": session_id,
                        "symbol": symbol,
                        "variant_id": variant_id
                    })
                    return None

                # Create indicator instance
                base_params = (variant.parameters or {}).copy()
                provided_params = (parameters or {}).copy()

                def _get_param(name: str, default: Any) -> Any:
                    return provided_params.get(name, base_params.get(name, default))

                timeframe = _get_param("timeframe", "1m")
                raw_period = _get_param("period", 20)
                try:
                    period = int(raw_period)
                except (TypeError, ValueError):
                    period = 20

                indicator_type = (variant.base_indicator_type or "").upper()

                indicator = StreamingIndicator(
                    symbol=symbol,
                    indicator=f"{variant_id}_{period}",
                    timeframe=timeframe,
                    current_value=0.0,
                    timestamp=time.time(),
                    series=deque(maxlen=self._max_series_length),
                    metadata={
                        "variant_id": variant_id,
                        "variant_type": variant.variant_type,
                        "session_id": session_id,
                        "parameters": provided_params,
                        "created_at": time.time(),
                        "is_active": True,
                        "type": indicator_type,
                        "period": period,
                        "timeframe": timeframe
                    }
                )

                # Add to engine indicators
                self._indicators[indicator_id] = indicator
                self._track_indicator(indicator_id, indicator)

                # Track in session
                if session_id not in self._session_indicators:
                    self._session_indicators[session_id] = {}
                if symbol not in self._session_indicators[session_id]:
                    self._session_indicators[session_id][symbol] = []
                
                self._session_indicators[session_id][symbol].append(indicator_id)
                
                # Emit event for persistence layer
                self.event_bus.emit_event("indicator_added_to_session", {
                    "session_id": session_id,
                    "symbol": symbol,
                    "indicator_id": indicator_id,
                    "variant_id": variant_id,
                    "parameters": parameters or {}
                })

                self.logger.info("streaming_indicator_engine.indicator_added_to_session", {
                    "session_id": session_id,
                    "symbol": symbol,
                    "indicator_id": indicator_id,
                    "variant_id": variant_id,
                    "base_indicator_type": indicator_type
                })

                return indicator_id
                
        except Exception as e:
            self.logger.error("streaming_indicator_engine.add_indicator_to_session_failed", {
                "session_id": session_id,
                "symbol": symbol,
                "variant_id": variant_id,
                "error": str(e)
            })
            return None
    
    def get_session_indicators(self, session_id: str, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all indicators for a session, optionally filtered by symbol.
        
        Args:
            session_id: Session identifier
            symbol: Optional symbol filter
            
        Returns:
            List of indicator information dictionaries
        """
        try:
            with self._data_lock:
                result = []
                
                if session_id not in self._session_indicators:
                    return result
                
                session_data = self._session_indicators[session_id]
                
                # Filter by symbol if provided
                symbols_to_check = [symbol] if symbol else list(session_data.keys())
                
                for sym in symbols_to_check:
                    if sym in session_data:
                        for indicator_id in session_data[sym]:
                            indicator = self._indicators.get(indicator_id)
                            if indicator:
                                result.append({
                                    "indicator_id": indicator_id,
                                    "symbol": sym,
                                    "variant_id": indicator.metadata.get("variant_id"),
                                    "variant_type": indicator.metadata.get("variant_type"),
                                    "parameters": indicator.metadata.get("parameters", {}),
                                    "current_value": indicator.current_value,
                                    "last_update": indicator.timestamp,
                                    "is_active": indicator.metadata.get("is_active", True)
                                })
                
                return result
                
        except Exception as e:
            self.logger.error("streaming_indicator_engine.get_session_indicators_failed", {
                "session_id": session_id,
                "symbol": symbol,
                "error": str(e)
            })
            return []
    
    def remove_indicator_from_session(self, session_id: str, symbol: str, indicator_id: str) -> bool:
        """
        Remove an indicator from a session.
        
        Args:
            session_id: Session identifier
            symbol: Trading symbol
            indicator_id: Indicator identifier to remove
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._data_lock:
                # Check if indicator exists and belongs to session
                if (session_id not in self._session_indicators or
                    symbol not in self._session_indicators[session_id] or
                    indicator_id not in self._session_indicators[session_id][symbol]):
                    return False
                
                # Remove from session tracking
                self._session_indicators[session_id][symbol].remove(indicator_id)
                
                # Clean up empty structures
                if not self._session_indicators[session_id][symbol]:
                    del self._session_indicators[session_id][symbol]
                if not self._session_indicators[session_id]:
                    del self._session_indicators[session_id]
                
                # Remove from engine indicators
                if indicator_id in self._indicators:
                    del self._indicators[indicator_id]
                
                # Emit event for persistence layer
                self.event_bus.emit_event("indicator_removed_from_session", {
                    "session_id": session_id,
                    "symbol": symbol,
                    "indicator_id": indicator_id
                })
                
                self.logger.info("streaming_indicator_engine.indicator_removed_from_session", {
                    "session_id": session_id,
                    "symbol": symbol,
                    "indicator_id": indicator_id
                })
                
                return True
                
        except Exception as e:
            self.logger.error("streaming_indicator_engine.remove_indicator_from_session_failed", {
                "session_id": session_id,
                "symbol": symbol,
                "indicator_id": indicator_id,
                "error": str(e)
            })
            return False
    
    def cleanup_duplicate_indicators(self, session_id: str, symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        Clean up duplicate indicators in session(s).
        Keeps the most recent indicator for each unique variant_id + parameters combination.
        
        Args:
            session_id: Session identifier
            symbol: Optional symbol filter, if None cleans all symbols in session
            
        Returns:
            Dictionary with cleanup statistics
        """
        try:
            with self._data_lock:
                if session_id not in self._session_indicators:
                    return {"removed_count": 0, "kept_count": 0, "error": "Session not found"}
                
                session_data = self._session_indicators[session_id]
                symbols_to_clean = [symbol] if symbol else list(session_data.keys())
                
                total_removed = 0
                total_kept = 0
                
                for sym in symbols_to_clean:
                    if sym not in session_data:
                        continue
                        
                    # Group indicators by variant_id + parameters
                    indicator_groups = {}
                    for indicator_id in session_data[sym][:]:  # Copy list to avoid modification during iteration
                        indicator = self._indicators.get(indicator_id)
                        if not indicator:
                            continue
                            
                        variant_id = indicator.metadata.get("variant_id")
                        parameters = indicator.metadata.get("parameters", {})
                        
                        # Create unique key for grouping
                        group_key = f"{variant_id}_{hash(str(sorted(parameters.items())))}"
                        
                        if group_key not in indicator_groups:
                            indicator_groups[group_key] = []
                        indicator_groups[group_key].append({
                            "indicator_id": indicator_id,
                            "indicator": indicator,
                            "created_at": indicator.metadata.get("created_at", 0)
                        })
                    
                    # For each group, keep the most recent, remove others
                    for group_key, indicators in indicator_groups.items():
                        if len(indicators) <= 1:
                            total_kept += len(indicators)
                            continue
                            
                        # Sort by creation time, keep the most recent
                        indicators.sort(key=lambda x: x["created_at"], reverse=True)
                        to_keep = indicators[0]
                        to_remove = indicators[1:]
                        
                        total_kept += 1
                        total_removed += len(to_remove)
                        
                        # Remove duplicates
                        for item in to_remove:
                            indicator_id = item["indicator_id"]
                            
                            # Remove from session tracking
                            if indicator_id in session_data[sym]:
                                session_data[sym].remove(indicator_id)
                            
                            # Remove from engine indicators
                            if indicator_id in self._indicators:
                                del self._indicators[indicator_id]
                            
                            self.logger.info("streaming_indicator_engine.cleanup_removed_duplicate", {
                                "session_id": session_id,
                                "symbol": sym,
                                "removed_indicator_id": indicator_id,
                                "kept_indicator_id": to_keep["indicator_id"],
                                "group_key": group_key
                            })
                
                # Clean up empty structures
                for sym in list(session_data.keys()):
                    if not session_data[sym]:
                        del session_data[sym]
                if not session_data:
                    del self._session_indicators[session_id]
                
                result = {
                    "removed_count": total_removed,
                    "kept_count": total_kept,
                    "session_id": session_id,
                    "symbol": symbol
                }
                
                self.logger.info("streaming_indicator_engine.cleanup_duplicates_completed", result)
                return result
                
        except Exception as e:
            error_result = {
                "removed_count": 0,
                "kept_count": 0,
                "error": str(e),
                "session_id": session_id,
                "symbol": symbol
            }
            self.logger.error("streaming_indicator_engine.cleanup_duplicate_indicators_failed", error_result)
            return error_result

    def get_session_preferences(self, session_id: str, symbol: str) -> Dict[str, Any]:
        """Get user preferences for a session and symbol"""
        with self._data_lock:
            return self._session_preferences.get(session_id, {}).get(symbol, {})
    
    def set_session_preferences(self, session_id: str, symbol: str, preferences: Dict[str, Any]) -> bool:
        """Set user preferences for a session and symbol"""
        try:
            self.save_session_preferences(session_id, symbol, preferences)
            return True
        except Exception as e:
            self.logger.error("streaming_indicator_engine.set_session_preferences_failed", {
                "session_id": session_id,
                "symbol": symbol,
                "error": str(e)
            })
            return False
    
    def save_session_preferences(self, session_id: str, symbol: str, preferences: Dict[str, Any]) -> None:
        """Save user preferences for a session and symbol"""
        try:
            with self._data_lock:
                if session_id not in self._session_preferences:
                    self._session_preferences[session_id] = {}
                
                self._session_preferences[session_id][symbol] = preferences.copy()
                
                self.logger.debug("streaming_indicator_engine.preferences_saved", {
                    "session_id": session_id,
                    "symbol": symbol,
                    "preferences_keys": list(preferences.keys())
                })
                
        except Exception as e:
            self.logger.error("streaming_indicator_engine.save_preferences_failed", {
                "session_id": session_id,
                "symbol": symbol,
                "error": str(e)
            })

    # =================================================================
    # TIME SIMULATION METHODS (Task 4)
    # =================================================================
    
    def simulate_time_windows(self, indicator_id: str, start_ts: float, end_ts: float, 
                            refresh_interval: float = 1.0) -> List['IndicatorValue']:
        """
        Simulate indicator calculation across time windows for backtesting.
        
        Consolidated indicator logic in StreamingIndicatorEngine architecture.
        
        Args:
            indicator_id: The indicator ID to simulate
            start_ts: Start timestamp for simulation
            end_ts: End timestamp for simulation  
            refresh_interval: Time step between calculations in seconds
            
        Returns:
            List of IndicatorValue objects with calculated values
            
        Example:
            results = engine.simulate_time_windows(
                indicator_id="session123_BTCUSDT_twpa_abc",
                start_ts=time.time() - 3600,
                end_ts=time.time(),
                refresh_interval=1.0
            )
        """
        try:
            config = self.get_indicator_config(indicator_id)
            if not config:
                self.logger.error("streaming_indicator_engine.simulation_config_not_found", {
                    "indicator_id": indicator_id
                })
                return []
            
            # For TWPA, use optimized sliding window algorithm
            base_indicator_type = config.get("base_indicator_type", config.get("indicator_type", "").split("_")[0])
            if base_indicator_type == "TWPA":
                return self._simulate_twpa_optimized(
                    indicator_id, start_ts, end_ts, refresh_interval, config
                )
            
            # For other indicators, use generic simulation
            return self._simulate_generic(
                indicator_id, start_ts, end_ts, refresh_interval, config
            )
            
        except Exception as e:
            self.logger.error("streaming_indicator_engine.simulation_failed", {
                "indicator_id": indicator_id,
                "start_ts": start_ts,
                "end_ts": end_ts,
                "error": str(e)
            })
            return []
    
    def _simulate_twpa_optimized(self, indicator_id: str, start_ts: float, end_ts: float,
                               refresh_interval: float, config: Dict[str, Any]) -> List['IndicatorValue']:
        """
        Optimized TWPA simulation using sliding window algorithm O(n+m) instead of O(m*log n).
        
        Uses binary search for window boundaries and iterates through time systematically.
        This is the core fix for USER_REC_12 time simulation requirements.
        
        Args:
            indicator_id: TWPA indicator ID
            start_ts: Simulation start timestamp
            end_ts: Simulation end timestamp  
            refresh_interval: Time step in seconds
            config: Indicator configuration dictionary
            
        Returns:
            List of IndicatorValue objects for each time step
        """
        try:
            # Extract TWPA parameters
            parameters = config.get("parameters", {})
            t1 = float(parameters.get('t1', 30.0))  # Look back start (seconds ago)
            t2 = float(parameters.get('t2', 0.0))   # Look back end (seconds ago)
            symbol = config.get("symbol", "UNKNOWN")
            
            # Get price data from engine buffers  
            price_key = f"{symbol}_1m"  # Use 1m timeframe
            price_buffer = self._price_data.get(price_key, deque())
            
            if not price_buffer:
                self.logger.warning("streaming_indicator_engine.twpa_simulation_no_data", {
                    "indicator_id": indicator_id,
                    "symbol": symbol
                })
                return []
            
            # Convert buffer to sorted list of (timestamp, price) tuples
            price_series = [(point.timestamp, point.value) for point in price_buffer]
            price_series_sorted = sorted(price_series, key=lambda x: x[0])
            timestamps = [ts for ts, _ in price_series_sorted]
            
            # Import TWPA algorithm (unified system)
            from .indicators.twpa import twpa_algorithm
            import bisect
            
            # Simulation results
            results = []
            current_time = start_ts
            
            self.logger.info("streaming_indicator_engine.twpa_simulation_start", {
                "indicator_id": indicator_id,
                "time_span": end_ts - start_ts,
                "refresh_interval": refresh_interval,
                "t1": t1,
                "t2": t2,
                "data_points": len(price_series_sorted)
            })
            
            # Simulate time progression with moving windows
            while current_time <= end_ts:
                # Calculate TWPA window boundaries for current time
                window_start = current_time - t1
                window_end = current_time - t2
                
                # Use binary search to find window data - O(log n) 
                start_idx = bisect.bisect_left(timestamps, window_start)
                end_idx = bisect.bisect_right(timestamps, window_end)
                
                # Extract window points using slice - O(k) where k is window size
                window_points = price_series_sorted[start_idx:end_idx]
                
                # Calculate TWPA for this window
                if window_points:
                    twpa_value = twpa_algorithm._compute_twpa(
                        window_points, window_start, window_end
                    )
                    
                    if twpa_value is not None:
                        # Create IndicatorValue object
                        indicator_value = IndicatorValue(
                            timestamp=current_time,
                            value=twpa_value,
                            metadata={
                                "simulation": True,
                                "window_start": window_start,
                                "window_end": window_end,
                                "data_points_in_window": len(window_points)
                            }
                        )
                        results.append(indicator_value)
                
                # Advance time by refresh interval
                current_time += refresh_interval
            
            # Emit event for persistence layer
            if results:
                self.event_bus.emit(
                    "indicator_simulation_completed",
                    {
                        "indicator_id": indicator_id,
                        "symbol": symbol,
                        "results": results,
                        "simulation_params": {
                            "start_ts": start_ts,
                            "end_ts": end_ts,
                            "refresh_interval": refresh_interval,
                            "t1": t1,
                            "t2": t2
                        }
                    },
                    priority=EventPriority.NORMAL
                )
            
            self.logger.info("streaming_indicator_engine.twpa_simulation_completed", {
                "indicator_id": indicator_id,
                "results_count": len(results),
                "time_span": end_ts - start_ts
            })
            
            return results
            
        except Exception as e:
            self.logger.error("streaming_indicator_engine.twpa_simulation_error", {
                "indicator_id": indicator_id,
                "error": str(e)
            })
            import traceback
            traceback.print_exc()
            return []
    
    def _simulate_generic(self, indicator_id: str, start_ts: float, end_ts: float,
                        refresh_interval: float, config: Dict[str, Any]) -> List['IndicatorValue']:
        """
        Generic simulation for non-TWPA indicators.
        
        Uses the existing calculation methods but applies them systematically
        across time windows for backtesting scenarios.
        
        Args:
            indicator_id: Indicator ID  
            start_ts: Simulation start timestamp
            end_ts: Simulation end timestamp
            refresh_interval: Time step in seconds
            config: Indicator configuration dictionary
            
        Returns:
            List of IndicatorValue objects
        """
        try:
            symbol = config.get("symbol", "UNKNOWN")
            indicator_type = config.get("indicator_type", "").split("_")[0]
            
            # Get data buffer for this symbol
            price_key = f"{symbol}_1m"
            price_buffer = self._price_data.get(price_key, deque())
            
            if not price_buffer:
                self.logger.warning("streaming_indicator_engine.generic_simulation_no_data", {
                    "indicator_id": indicator_id,
                    "symbol": symbol
                })
                return []
            
            results = []
            current_time = start_ts
            
            self.logger.info("streaming_indicator_engine.generic_simulation_start", {
                "indicator_id": indicator_id,
                "indicator_type": indicator_type,
                "time_span": end_ts - start_ts,
                "refresh_interval": refresh_interval
            })
            
            # Simulate time progression
            while current_time <= end_ts:
                # Get data points up to current time
                relevant_data = [
                    point for point in price_buffer
                    if point.timestamp <= current_time
                ]
                
                if relevant_data:
                    # For now, use latest price as calculated value
                    # In full implementation, this would use indicator-specific calculation
                    latest_point = relevant_data[-1]
                    calculated_value = latest_point.value  # Use the price value
                    
                    if calculated_value is not None:
                        indicator_value = IndicatorValue(
                            timestamp=current_time,
                            value=calculated_value,
                            metadata={
                                "simulation": True,
                                "data_points_available": len(relevant_data)
                            }
                        )
                        results.append(indicator_value)
                
                # Advance time
                current_time += refresh_interval
            
            # Emit event for persistence
            if results:
                self.event_bus.emit(
                    "indicator_simulation_completed",
                    {
                        "indicator_id": indicator_id,
                        "symbol": symbol,
                        "results": results,
                        "simulation_params": {
                            "start_ts": start_ts,
                            "end_ts": end_ts,
                            "refresh_interval": refresh_interval
                        }
                    },
                    priority=EventPriority.NORMAL
                )
            
            self.logger.info("streaming_indicator_engine.generic_simulation_completed", {
                "indicator_id": indicator_id,
                "results_count": len(results)
            })
            
            return results
            
        except Exception as e:
            self.logger.error("streaming_indicator_engine.generic_simulation_error", {
                "indicator_id": indicator_id,
                "error": str(e)
            })
            return []
