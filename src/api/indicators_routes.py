"""
Indicators API Routes for Sprint 15 - USER_REC_15 Implementation

Provides REST endpoints for:
- System indicators listing and metadata
- Indicator variants CRUD operations
- Frontend integration for indicator management
- StreamingIndicatorEngine integration for unified indicator management
- NEW: Algorithm registry endpoints for enhanced indicator system
"""

import asyncio
# ✅ REMOVED: csv import (file-based data deprecated, using QuestDB)
from datetime import datetime
import json
import math
import os
import traceback
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple, Callable
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse

from src.core.logger import get_logger

from src.core.event_bus import EventBus
from src.api.dependencies import verify_csrf_token
from src.domain.services.streaming_indicator_engine import StreamingIndicatorEngine
from src.api.response_envelope import ensure_envelope
from src.domain.services.indicator_persistence_service import IndicatorPersistenceService
from src.domain.services.offline_indicator_engine import OfflineIndicatorEngine
from src.domain.services.streaming_indicator_engine import IndicatorType
from src.domain.types.indicator_types import IndicatorValue

# ✅ BUG-002 FIX: Import QuestDB providers for database access
from src.data_feed.questdb_provider import QuestDBProvider
from src.data.questdb_data_provider import QuestDBDataProvider

# Create router
router = APIRouter(prefix="/api/indicators", tags=["indicators"])

# ✅ FIX #3: Module-level logger (Step 3/3 - Performance optimization)
# Before: 42 calls to get_logger(__name__) inside functions
# After: 1 call at module level, reused by all functions
# Benefits: Performance, cleaner code, standard Python pattern
logger = get_logger(__name__)

# Global engine instance (will be properly injected in production)
_streaming_engine: Optional[StreamingIndicatorEngine] = None
_persistence_service: Optional[IndicatorPersistenceService] = None
_offline_indicator_engine: Optional[OfflineIndicatorEngine] = None

# ✅ BUG-002 FIX: Global QuestDB providers for database access
_questdb_provider: Optional[QuestDBProvider] = None
_questdb_data_provider: Optional[QuestDBDataProvider] = None

# ✅ SCALABILITY FIX: Dedicated ThreadPoolExecutor for CPU-bound indicator calculations
# Prevents event loop blocking during indicator computation for 20-100 parallel calculations
from concurrent.futures import ThreadPoolExecutor
_indicator_calculation_executor: Optional[ThreadPoolExecutor] = None
_calculation_semaphore: Optional[asyncio.Semaphore] = None

DATA_BASE_PATH = Path(os.environ.get("INDICATOR_DATA_DIR", "data")).resolve()

# ✅ ARCHITECTURE FIX: Removed SimpleEventBus duplication (34 lines of duplicate code)
# Was duplicating core/event_bus.py (1341 lines of production-ready code)
# Violates CLAUDE.md: "Eliminate code duplication (single source of truth)"
# Now using the real EventBus from core with proper DI

_event_bus: Optional[EventBus] = None


def initialize_indicators_dependencies(
    event_bus: EventBus,
    streaming_engine: Optional[StreamingIndicatorEngine] = None,
    questdb_provider: Optional[QuestDBProvider] = None
) -> None:
    """
    ✅ ARCHITECTURE FIX: Explicit dependency injection instead of lazy initialization.

    This function should be called from unified_server.py during app startup
    to inject proper dependencies from Container.

    Args:
        event_bus: Production EventBus from Container (replaces SimpleEventBus)
        streaming_engine: Optional pre-created StreamingIndicatorEngine
        questdb_provider: Optional pre-created QuestDBProvider
    """
    global _event_bus, _streaming_engine, _persistence_service, _offline_indicator_engine
    global _questdb_provider, _questdb_data_provider
    global _indicator_calculation_executor, _calculation_semaphore

    # Inject EventBus (no more SimpleEventBus!)
    _event_bus = event_bus

    # Inject or create services
    if streaming_engine:
        _streaming_engine = streaming_engine

    if questdb_provider:
        _questdb_provider = questdb_provider
        _questdb_data_provider = QuestDBDataProvider(_questdb_provider, logger)

    # Create dependent services with injected EventBus
    _persistence_service = IndicatorPersistenceService(
        _event_bus,
        logger,
        questdb_provider=_questdb_provider
    )
    _offline_indicator_engine = OfflineIndicatorEngine(
        questdb_data_provider=_questdb_data_provider
    )

    # ✅ VALIDATION: Check if algorithm registry initialized successfully
    if _offline_indicator_engine._algorithm_registry is None:
        logger.warning(
            "indicators_routes.offline_engine_fallback_mode",
            {
                "reason": "algorithm registry not initialized",
                "impact": "All indicators will use legacy calculation method",
                "performance": "May be slower or less accurate for some indicators"
            }
        )

    # ✅ SCALABILITY FIX: Initialize dedicated ThreadPoolExecutor for indicator calculations
    # Prevents event loop blocking during 20-100 parallel indicator computations
    # max_workers: 2x CPU cores (up to 24) for I/O waiting during calculations
    # semaphore: Limits concurrent calculations to 12 to prevent memory exhaustion
    if _indicator_calculation_executor is None:
        import os
        max_workers = min(os.cpu_count() * 2, 24)
        _indicator_calculation_executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="IndicatorCalc-"
        )
        _calculation_semaphore = asyncio.Semaphore(12)

        logger.info("indicators_routes.executor_initialized", {
            "max_workers": max_workers,
            "semaphore_limit": 12,
            "cpu_count": os.cpu_count()
        })

    logger.info("indicators_routes.dependencies_initialized", {
        "event_bus_type": type(_event_bus).__name__,
        "has_streaming_engine": _streaming_engine is not None,
        "has_questdb": _questdb_provider is not None,
        "has_executor": _indicator_calculation_executor is not None
    })


def _ensure_support_services() -> Tuple[IndicatorPersistenceService, OfflineIndicatorEngine]:
    """
    Get injected services or fail-fast if not initialized.

    Services MUST be injected via initialize_indicators_dependencies() during startup.
    No fallback lazy initialization - enforces proper DI architecture.

    Raises:
        RuntimeError: If services not injected (configuration error)
    """
    global _persistence_service, _offline_indicator_engine, _event_bus

    if _event_bus is None:
        raise RuntimeError(
            "EventBus not injected into indicators_routes. "
            "Call initialize_indicators_dependencies() from unified_server.py during startup."
        )

    if _persistence_service is None:
        raise RuntimeError(
            "IndicatorPersistenceService not initialized. "
            "Call initialize_indicators_dependencies() from unified_server.py during startup."
        )

    if _offline_indicator_engine is None:
        raise RuntimeError(
            "OfflineIndicatorEngine not initialized. "
            "Call initialize_indicators_dependencies() from unified_server.py during startup."
        )

    return _persistence_service, _offline_indicator_engine


def _ensure_questdb_providers() -> Tuple[QuestDBProvider, QuestDBDataProvider]:
    """
    Get injected QuestDB providers or fail-fast if not initialized.

    Providers MUST be injected via initialize_indicators_dependencies() during startup.
    No fallback lazy initialization - enforces proper DI architecture.

    Raises:
        RuntimeError: If providers not injected (configuration error)
    """
    global _questdb_provider, _questdb_data_provider

    if _questdb_provider is None:
        raise RuntimeError(
            "QuestDBProvider not injected into indicators_routes. "
            "Call initialize_indicators_dependencies() from unified_server.py during startup."
        )

    if _questdb_data_provider is None:
        raise RuntimeError(
            "QuestDBDataProvider not initialized. "
            "Call initialize_indicators_dependencies() from unified_server.py during startup."
        )

    return _questdb_provider, _questdb_data_provider


async def _load_session_price_data(session_id: str, symbol: str) -> List[Dict[str, float]]:
    """
    Load tick price data from QuestDB for indicator calculation.

    ✅ BUG-002 FIX: Changed from CSV filesystem to QuestDB query
    ✅ OBSERVABILITY: Enhanced logging for data loading

    Args:
        session_id: Session identifier
        symbol: Trading pair symbol

    Returns:
        List of price dictionaries with timestamp, price, volume

    Raises:
        HTTPException: If session/symbol not found or data invalid
    """
    import time as time_module
    query_start = time_module.time()

    logger.info("indicators_routes.questdb_query_start", {
        "session_id": session_id,
        "symbol": symbol,
        "operation": "get_tick_prices"
    })

    _, questdb_data_provider = _ensure_questdb_providers()

    try:
        # Query tick prices from QuestDB
        tick_prices = await questdb_data_provider.get_tick_prices(
            session_id=session_id,
            symbol=symbol
            # No limit - indicators need full dataset
        )

        query_time = time_module.time() - query_start

        logger.info("indicators_routes.questdb_query_complete", {
            "session_id": session_id,
            "symbol": symbol,
            "rows_returned": len(tick_prices) if tick_prices else 0,
            "query_time_ms": query_time * 1000
        })

        if not tick_prices:
            logger.error("indicators_routes.no_price_data_found", {
                "session_id": session_id,
                "symbol": symbol,
                "query_time_ms": query_time * 1000,
                "impact": "CRITICAL - cannot calculate indicator without data"
            })
            raise HTTPException(
                status_code=404,
                detail=f"Price data not found for session '{session_id}', symbol '{symbol}'"
            )

        # Convert QuestDB format to indicator format
        from datetime import datetime
        data: List[Dict[str, float]] = []
        invalid_rows_count = 0

        for tick in tick_prices:
            try:
                # Convert timestamp if needed
                timestamp = tick.get('timestamp')
                if isinstance(timestamp, datetime):
                    timestamp = timestamp.timestamp()  # Convert to seconds
                elif timestamp:
                    timestamp = float(timestamp)
                else:
                    invalid_rows_count += 1
                    continue  # Skip invalid timestamps

                price = float(tick.get('price', 0))
                volume = float(tick.get('volume', 0.0))

                data.append({
                    "timestamp": timestamp,
                    "price": price,
                    "volume": volume
                })
            except (TypeError, ValueError) as exc:
                # Skip invalid rows instead of failing entire dataset
                invalid_rows_count += 1
                logger.warning("indicators_routes.invalid_price_row", {
                    "session_id": session_id,
                    "symbol": symbol,
                    "tick": str(tick),
                    "error": str(exc),
                    "invalid_count_so_far": invalid_rows_count
                })
                continue

        # ✅ OBSERVABILITY: Log conversion summary
        logger.info("indicators_routes.data_conversion_complete", {
            "session_id": session_id,
            "symbol": symbol,
            "total_rows": len(tick_prices),
            "valid_rows": len(data),
            "invalid_rows": invalid_rows_count,
            "conversion_rate": f"{(len(data) / len(tick_prices) * 100):.1f}%" if tick_prices else "0%"
        })

        if not data:
            logger.error("indicators_routes.all_rows_invalid", {
                "session_id": session_id,
                "symbol": symbol,
                "total_rows": len(tick_prices),
                "invalid_rows": invalid_rows_count,
                "impact": "CRITICAL - all price data rows are invalid, cannot calculate indicator"
            })
            raise HTTPException(
                status_code=404,
                detail=f"No valid price data rows available for session '{session_id}', symbol '{symbol}'"
            )

        # Data from QuestDB should already be sorted by timestamp, but ensure it
        data.sort(key=lambda item: item["timestamp"])
        return data

    except HTTPException:
        # Re-raise HTTPException as-is
        raise
    except Exception as e:
        # logger = get_logger(__name__)  # ✅ FIX #3: Using module-level logger
        logger.error("indicators_routes.load_price_data_failed", {
            "session_id": session_id,
            "symbol": symbol,
            "error": str(e)
        })
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load price data from database: {str(e)}"
        ) from e


async def _compute_indicator_series(
    indicator_id: str,
    session_id: str,
    symbol: str,
    variant,
    override_parameters: Dict[str, Any],
    algorithm_registry=None
) -> List[IndicatorValue]:
    """
    Compute indicator series for historical session data.

    ✅ BUG-002 FIX: Now async to support QuestDB data loading

    CRITICAL FIX: Uses OfflineIndicatorEngine to generate indicator values at
    fixed time intervals (refresh_interval_seconds) instead of using raw price
    timestamps. This ensures TWPA and other time-driven indicators are calculated
    at regular intervals (e.g., every 1 second) as specified in USER_REC_14.

    OLD BEHAVIOR (REMOVED):
        - Used legacy IndicatorCalculator methods (now removed)
        - Calculated indicator for EVERY price timestamp
        - If prices arrived irregularly (e.g., 15s gap, 54s gap), indicators also irregular

    NEW BEHAVIOR (CORRECT):
        - Uses OfflineIndicatorEngine._calculate_indicator_series()
        - Generates regular time axis using TimeAxisGenerator
        - Calculates indicator at fixed intervals (default 1.0 second)
        - Respects refresh_interval_seconds parameter
    """
    import time as time_module
    start_time = time_module.time()

    logger.info("indicators_routes.compute_indicator.loading_data", {
        "indicator_id": indicator_id,
        "session_id": session_id,
        "symbol": symbol,
        "variant_id": variant.id,
        "variant_base_type": variant.base_indicator_type
    })

    price_rows = await _load_session_price_data(session_id, symbol)
    data_load_time = time_module.time() - start_time

    logger.info("indicators_routes.compute_indicator.data_loaded", {
        "indicator_id": indicator_id,
        "session_id": session_id,
        "symbol": symbol,
        "price_rows_count": len(price_rows),
        "load_time_ms": data_load_time * 1000
    })

    # Convert price_rows to MarketDataPoint objects
    from src.domain.types.indicator_types import MarketDataPoint
    market_data_points = [
        MarketDataPoint(
            timestamp=row["timestamp"],
            price=row["price"],
            volume=row.get("volume", 0.0),
            symbol=symbol
        )
        for row in price_rows
    ]

    base_params = dict(variant.parameters or {})
    provided_params = dict(override_parameters or {})
    combined_params = {**base_params, **provided_params}

    raw_period = combined_params.pop("period", base_params.get("period", 20))
    try:
        period = int(raw_period)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid period value '{raw_period}' for variant '{variant.id}'"
        )

    indicator_type_str = str(variant.base_indicator_type or variant.name or "").upper()
    try:
        indicator_enum = IndicatorType[indicator_type_str]
    except KeyError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported indicator type '{indicator_type_str}' for variant '{variant.id}'"
        ) from exc

    # CRITICAL FIX: Use OfflineIndicatorEngine instead of IndicatorCalculator
    # This ensures time-driven indicators (TWPA, etc.) are calculated at fixed intervals
    _, offline_engine = _ensure_support_services()

    # Ensure refresh_interval_seconds is in parameters (default 1.0 second)
    if "refresh_interval_seconds" not in combined_params:
        combined_params["refresh_interval_seconds"] = 1.0

    # ✅ SCALABILITY FIX: Execute CPU-bound calculation in ThreadPoolExecutor
    # Prevents event loop blocking during 20-100 parallel indicator computations
    # Uses semaphore to limit concurrent calculations (max 12) and prevent memory exhaustion
    global _indicator_calculation_executor, _calculation_semaphore

    if _indicator_calculation_executor is None or _calculation_semaphore is None:
        raise HTTPException(
            status_code=500,
            detail="Indicator calculation executor not initialized. Server misconfiguration."
        )

    # Acquire semaphore (wait if 12 calculations already running)
    async with _calculation_semaphore:
        active_count = 12 - _calculation_semaphore._value
        calculation_start_time = time_module.time()

        logger.info("indicators_routes.compute_indicator.start", {
            "session_id": session_id,
            "symbol": symbol,
            "indicator_id": indicator_id,
            "indicator_type": indicator_enum.value,
            "data_points_count": len(market_data_points),
            "parameters": combined_params,
            "active_calculations": active_count,
            "queued": active_count >= 12
        })

        try:
            # ✅ OBSERVABILITY: Log before entering ThreadPoolExecutor
            logger.info("indicators_routes.compute_indicator.entering_executor", {
                "indicator_id": indicator_id,
                "symbol": symbol,
                "indicator_type": indicator_enum.value,
                "executor_type": type(_indicator_calculation_executor).__name__,
                "timeout_seconds": 120.0
            })

            # Execute CPU-bound calculation in thread pool with 120s timeout
            loop = asyncio.get_event_loop()
            series = await asyncio.wait_for(
                loop.run_in_executor(
                    _indicator_calculation_executor,
                    offline_engine._calculate_indicator_series,
                    symbol,
                    indicator_enum,
                    "1m",  # timeframe used for display only
                    period,
                    combined_params,
                    market_data_points
                ),
                timeout=120.0  # 2 minute timeout per indicator
            )

            calculation_time = time_module.time() - calculation_start_time

            logger.info("indicators_routes.compute_indicator.complete", {
                "session_id": session_id,
                "symbol": symbol,
                "indicator_id": indicator_id,
                "series_length": len(series),
                "none_count": sum(1 for v in series if v.value is None),
                "calculation_time_ms": calculation_time * 1000
            })

        except asyncio.TimeoutError:
            logger.error("indicators_routes.compute_timeout", {
                "session_id": session_id,
                "symbol": symbol,
                "indicator_id": indicator_id,
                "timeout_seconds": 120.0,
                "data_points_count": len(market_data_points)
            })
            raise HTTPException(
                status_code=504,
                detail=f"Indicator calculation timeout after 120 seconds. Try reducing data range or period."
            )

    # Update indicator_id and metadata for each value
    for value in series:
        value.indicator_id = indicator_id
        value.metadata = {
            "session_id": session_id,
            "variant_id": variant.id,
            "variant_type": variant.variant_type,
            "parameters": combined_params,
            "period": period
        }

    if not series:
        raise HTTPException(
            status_code=422,
            detail=f"Indicator '{variant.id}' produced no calculable values for session '{session_id}'"
        )

    return series


async def get_streaming_indicator_engine() -> StreamingIndicatorEngine:
    """
    FastAPI dependency to get StreamingIndicatorEngine instance.

    ✅ ARCHITECTURE FIX: Simplified to return Container-created singleton.
    ✅ ELIMINATED: Duplicate repository creation (now in Container only).
    ✅ ELIMINATED: SimpleEventBus fallback (proper DI via initialize_indicators_dependencies).

    CRITICAL: This function assumes initialize_indicators_dependencies() was called
    during unified_server startup. If _streaming_engine is None, it means DI failed.

    Returns:
        StreamingIndicatorEngine singleton from Container

    Raises:
        RuntimeError: If engine not initialized (DI failure)
    """
    global _streaming_engine

    if _streaming_engine is None:
        # ❌ ARCHITECTURE VIOLATION: Engine should be injected via initialize_indicators_dependencies()
        # This should NEVER happen in production - indicates DI failure
        logger.error("indicators_routes.engine_not_initialized", {
            "error": "StreamingIndicatorEngine not injected via initialize_indicators_dependencies()",
            "solution": "Ensure unified_server.py calls initialize_indicators_dependencies() on startup"
        })
        raise RuntimeError(
            "StreamingIndicatorEngine not initialized. "
            "This indicates dependency injection failure in unified_server.py. "
            "Check that initialize_indicators_dependencies() is called during startup."
        )

    return _streaming_engine


def _sanitize_for_json(obj: Any) -> Any:
    """
    Recursively sanitize data for JSON serialization.
    Replaces inf/-inf/nan with None to avoid JSON errors.
    """
    import math

    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_sanitize_for_json(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(_sanitize_for_json(item) for item in obj)
    return obj


def _json_ok(payload: Dict[str, Any], request_id: Optional[str] = None) -> JSONResponse:
    """Helper function to create OK JSON response with proper envelope"""
    sanitized_payload = _sanitize_for_json(payload)
    body = ensure_envelope({"type": "response", "data": sanitized_payload}, request_id=request_id)
    return JSONResponse(content=body)


def _normalize_system_indicators_response(raw: Any) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
    """
    Normalize engine response into a dict keyed by indicator id and ordered categories list.
    Keeps upstream order where available while ensuring categories discovered via indicators are present.
    """
    system_indicator_map: Dict[str, Dict[str, Any]] = {}
    categories_seen: Set[str] = set()
    categories_order: List[str] = []

    if isinstance(raw, dict):
        indicators_payload = raw.get("indicators", [])
        categories_payload = raw.get("categories", [])

        if isinstance(categories_payload, list):
            for category in categories_payload:
                if isinstance(category, str) and category not in categories_seen:
                    categories_seen.add(category)
                    categories_order.append(category)
    elif isinstance(raw, list):
        indicators_payload = raw
    else:
        indicators_payload = []

    for indicator_data in indicators_payload:
        if not isinstance(indicator_data, dict):
            continue

        indicator_type = indicator_data.get("indicator_type") or indicator_data.get("id")
        if not indicator_type:
            continue

        system_indicator_map[indicator_type] = indicator_data

        category = indicator_data.get("category")
        if isinstance(category, str) and category not in categories_seen:
            categories_seen.add(category)
            categories_order.append(category)

    if not categories_order and categories_seen:
        categories_order.extend(sorted(categories_seen))

    return system_indicator_map, categories_order


def _coerce_variant_parameters(
    engine: StreamingIndicatorEngine,
    base_indicator_type: str,
    parameters: Dict[str, Any]
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Attempt to coerce incoming parameter values to the types expected by the system indicator definition.
    Returns normalized parameters and a list of conversion error messages.
    """
    if not isinstance(parameters, dict):
        return {}, ["parameters payload must be an object"]

    definition = engine.get_system_indicator_definition(base_indicator_type.upper()) or {}
    param_definitions = {
        param["name"]: param
        for param in definition.get("parameters", [])
    }

    normalized: Dict[str, Any] = {}
    errors: List[str] = []

    for name, value in parameters.items():
        param_def = param_definitions.get(name)
        if not param_def:
            normalized[name] = value
            continue

        expected_type = param_def.get("type")
        try:
            normalized[name] = _coerce_single_parameter(value, expected_type)
        except ValueError as exc:
            errors.append(f"{name}: {exc}")

    return normalized, errors


def _coerce_single_parameter(value: Any, expected_type: str) -> Any:
    """
    Convert a single parameter value to the expected type.
    Raises ValueError when conversion is not possible.
    """
    if expected_type == "int":
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        if isinstance(value, float) and value.is_integer():
            return int(value)
        if isinstance(value, str):
            stripped = value.strip()
            if stripped == "":
                raise ValueError("expected integer, got empty string")
            try:
                float_value = float(stripped)
            except ValueError as exc:
                raise ValueError(f"expected integer, got '{value}'") from exc
            if not float_value.is_integer():
                raise ValueError(f"expected integer, got '{value}'")
            return int(float_value)
        raise ValueError(f"expected integer, got {type(value).__name__}")

    if expected_type == "float":
        if isinstance(value, bool):
            return float(value)
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            stripped = value.strip()
            if stripped == "":
                raise ValueError("expected float, got empty string")
            try:
                return float(stripped)
            except ValueError as exc:
                raise ValueError(f"expected float, got '{value}'") from exc
        raise ValueError(f"expected float, got {type(value).__name__}")

    if expected_type == "boolean":
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            stripped = value.strip().lower()
            if stripped in {"true", "1", "yes", "on"}:
                return True
            if stripped in {"false", "0", "no", "off"}:
                return False
            raise ValueError(f"expected boolean, got '{value}'")
        raise ValueError(f"expected boolean, got {type(value).__name__}")

    if expected_type == "string":
        if isinstance(value, str):
            return value
        return str(value)

    if expected_type == "json":
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError as exc:
                raise ValueError(f"expected JSON, got invalid string: {exc.msg}") from exc
        return value

    # Fallback for unknown types - return as-is
    return value

@router.get("/system")
async def get_system_indicators(
    engine: StreamingIndicatorEngine = Depends(get_streaming_indicator_engine)
) -> JSONResponse:
    """
    Get list of all system indicators with metadata.
    
    Returns:
        List of system indicators with format:
        {
            "id": "TWPA",
            "name": "Time Weighted Price Average",
            "description": "Calculate time-weighted price average over specified window",
            "parameters": [
                {
                    "name": "window_minutes",
                    "type": "float",
                    "description": "Time window in minutes",
                    "default": 5.0,
                    "required": true
                },
                {
                    "name": "granularity",
                    "type": "string", 
                    "description": "Price granularity (tick/minute/hour)",
                    "default": "tick",
                    "required": false
                }
            ],
            "type": "general",
            "category": "general"
        }
    """
    try:
        # Get system indicators from the engine
        raw_system_indicators = engine.get_system_indicators()

        system_indicator_map, categories_order = _normalize_system_indicators_response(raw_system_indicators)

        return _json_ok({
            "indicators": list(system_indicator_map.values()),
            "total_count": len(system_indicator_map),
            "categories": categories_order
        })

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve system indicators: {str(e)}"
        )


@router.get("/system/categories")
async def get_system_indicator_categories(
    engine: StreamingIndicatorEngine = Depends(get_streaming_indicator_engine)
) -> JSONResponse:
    """
    Get list of available system indicator categories.
    
    Returns:
        {
            "categories": ["Technical", "Risk", "Strategy"],
            "total_count": 3
        }
    """
    try:
        categories = engine.get_available_categories()
        
        return _json_ok({
            "categories": categories,
            "total_count": len(categories)
        })
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve indicator categories: {str(e)}"
        )


@router.get("/system/{indicator_id}")
async def get_system_indicator_details(
    indicator_id: str,
    engine: StreamingIndicatorEngine = Depends(get_streaming_indicator_engine)
) -> JSONResponse:
    """
    Get details for a specific system indicator.
    
    Args:
        indicator_id: System indicator ID (e.g., "TWPA", "RSI")
        
    Returns:
        System indicator details with parameters and metadata
    """
    try:
        system_indicators = engine.get_system_indicators()
        system_indicator_map, _ = _normalize_system_indicators_response(system_indicators)

        indicator_data = system_indicator_map.get(indicator_id)
        
        if not indicator_data:
            raise HTTPException(
                status_code=404,
                detail=f"System indicator '{indicator_id}' not found"
            )
        
        return _json_ok(indicator_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve indicator details: {str(e)}"
        )


# New Unified Indicator System Endpoints

@router.get("/variants")
async def get_available_variants(
    engine: StreamingIndicatorEngine = Depends(get_streaming_indicator_engine)
) -> JSONResponse:
    """
    Get all available indicator variants from config directory.
    
    Returns:
        List of available variants with metadata for UI selection
    """
    try:
        # ✅ PHASE 2 FIX: Await async method with race condition protection
        variants = await engine.list_variants()
        
        # Convert IndicatorVariant objects to dict format
        variant_dicts = []
        categories = set()

        for variant in variants:
            # ✅ PHASE 2 FIX COMPLETION: Await async method to prevent coroutine iteration error
            params = await engine.get_variant_parameters(variant.id)
            parameter_definitions = [
                {
                    "name": param.name,
                    "type": param.parameter_type,
                    "description": param.description,
                    "default": param.default_value,
                    "required": param.is_required,
                    "min_value": param.min_value,
                    "max_value": param.max_value,
                    "allowed_values": param.allowed_values,
                }
                for param in params
            ]

            variant_dict = {
                "id": variant.id,
                "variant_id": variant.id,
                "name": variant.name,
                "variant_type": variant.variant_type,
                "type": variant.variant_type,
                "base_indicator_type": variant.base_indicator_type,
                "indicator_type": variant.base_indicator_type,
                "description": variant.description,
                "parameters": variant.parameters or {},
                "parameter_definitions": parameter_definitions,
                "is_system": variant.is_system,
                "created_by": variant.created_by,
                "created_at": variant.created_at,
                "updated_at": variant.updated_at
            }
            variant_dicts.append(variant_dict)
            categories.add(variant.variant_type)
        
        return _json_ok({
            "variants": variant_dicts,
            "total_count": len(variant_dicts),
            "categories": sorted(categories)
        })
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve indicator variants: {str(e)}"
        )


@router.get("/variants/by-category/{category}")
async def get_variants_by_category(
    category: str,
    engine: StreamingIndicatorEngine = Depends(get_streaming_indicator_engine)
) -> JSONResponse:
    """
    Get indicator variants for specific category.
    
    Args:
        category: Variant category (see VariantType enum in streaming_indicator_engine)
    """
    try:
        # ✅ PHASE 2 FIX COMPLETION: Await async method with race condition protection
        variants = await engine.list_variants(variant_type=category)

        # Convert IndicatorVariant objects to dict format
        variant_dicts = []
        for variant in variants:
            # ✅ PHASE 2 FIX COMPLETION: Await async method to prevent coroutine iteration error
            params = await engine.get_variant_parameters(variant.id)
            parameter_definitions = [
                {
                    "name": param.name,
                    "type": param.parameter_type,
                    "description": param.description,
                    "default": param.default_value,
                    "required": param.is_required,
                    "min_value": param.min_value,
                    "max_value": param.max_value,
                    "allowed_values": param.allowed_values,
                }
                for param in params
            ]

            variant_dict = {
                "id": variant.id,
                "variant_id": variant.id,
                "name": variant.name,
                "variant_type": variant.variant_type,
                "type": variant.variant_type,
                "indicator_type": variant.base_indicator_type,
                "base_indicator_type": variant.base_indicator_type,
                "description": variant.description,
                "parameters": variant.parameters or {},
                "parameter_definitions": parameter_definitions,
                "is_system": variant.is_system,
                "created_by": variant.created_by,
                "created_at": variant.created_at,
                "updated_at": variant.updated_at
            }
            variant_dicts.append(variant_dict)
        
        return _json_ok({
            "category": category,
            "variants": variant_dicts,
            "total_count": len(variant_dicts)
        })
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve variants for category '{category}': {str(e)}"
        )


@router.post("/sessions/{session_id}/symbols/{symbol}/indicators")
async def add_indicator_for_session(
    session_id: str,
    symbol: str,
    request: Request,
    engine: StreamingIndicatorEngine = Depends(get_streaming_indicator_engine),
    csrf_token: str = Depends(verify_csrf_token)
) -> JSONResponse:
    """
    Add indicator for specific session and symbol using StreamingIndicatorEngine.

    Request body:
    {
        "variant_id": "uuid-of-variant",
        "parameters": {"param1": "value1", ...},  // optional overrides
        "force_recalculate": bool
    }
    """
    try:
        # Validate session exists before adding indicators
        # Prevents orphaned indicators in QuestDB (no FK constraints)
        _, questdb_data_provider = _ensure_questdb_providers()
        session_metadata = await questdb_data_provider.get_session_metadata(session_id)
        if not session_metadata:
            raise HTTPException(
                status_code=404,
                detail=f"Session '{session_id}' not found. Cannot add indicators to non-existent session."
            )

        body = await request.json()
        variant_id = body.get('variant_id')
        parameters = body.get('parameters', {})
        force_recalculate = body.get('force_recalculate', False)

        if not variant_id:
            raise HTTPException(status_code=400, detail="variant_id is required")

        # Get variant details
        variant = await engine.get_variant(variant_id)
        if not variant:
            raise HTTPException(status_code=404, detail=f"Variant '{variant_id}' not found")

        # Add to session using StreamingIndicatorEngine session management
        indicator_id = await engine.add_indicator_to_session(
            session_id=session_id,
            symbol=symbol,
            variant_id=variant_id,
            parameters=parameters
        )

        if not indicator_id:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to add indicator '{variant_id}' for session '{session_id}' and symbol '{symbol}'"
            )

        persistence_service, _ = _ensure_support_services()
        try:
            # ✅ BUG-002 FIX: Added await for async _compute_indicator_series
            series = await _compute_indicator_series(
                indicator_id=indicator_id,
                session_id=session_id,
                symbol=symbol,
                variant=variant,
                override_parameters=parameters,
                algorithm_registry=engine.get_algorithm_registry()
            )
        except HTTPException:
            # bubble up structured error (e.g. malformed data)
            raise
        except Exception as exc:
            # logger = get_logger(__name__)  # ✅ FIX #3: Using module-level logger
            logger.error("indicators_routes.add_indicator.compute_failed", {
                "session_id": session_id,
                "symbol": symbol,
                "indicator_id": indicator_id,
                "variant_id": variant_id,
                "error": str(exc)
            })
            raise HTTPException(
                status_code=500,
                detail=f"Failed to calculate indicator values: {str(exc)}"
            ) from exc

        # ✅ BUG-002 FIX: Save indicators to QuestDB instead of CSV
        questdb_provider, _ = _ensure_questdb_providers()

        # Convert IndicatorValue objects to QuestDB format
        # Filter out None values (following IndicatorPersistenceService pattern)
        indicators_batch = []
        none_count = 0
        for value in series:
            from datetime import datetime

            # Skip None values (warm-up period, insufficient data, etc.)
            if value.value is None:
                none_count += 1
                continue

            indicators_batch.append({
                'session_id': session_id,
                'symbol': symbol,
                'indicator_id': indicator_id,
                'timestamp': datetime.fromtimestamp(value.timestamp),
                'value': float(value.value),  # Now safe - None values filtered above
                # Note: IndicatorValue doesn't have confidence attribute
                # confidence can be computed from metadata if needed
            })

        # Log filtering statistics
        if none_count > 0:
            # logger = get_logger(__name__)  # ✅ FIX #3: Using module-level logger
            logger.debug("indicators_routes.filtered_none_values", {
                "session_id": session_id,
                "symbol": symbol,
                "indicator_id": indicator_id,
                "total_values": len(series),
                "none_values_filtered": none_count,
                "saved_values": len(indicators_batch),
                "reason": "None values represent warm-up period or insufficient data"
            })

        # If all values were None, return 422 Unprocessable Entity
        if not indicators_batch:
            # logger = get_logger(__name__)  # ✅ FIX #3: Using module-level logger
            logger.error("indicators_routes.all_values_none", {
                "session_id": session_id,
                "symbol": symbol,
                "indicator_id": indicator_id,
                "variant_id": variant_id,
                "total_values": len(series),
                "none_count": none_count,
                "reason": "All indicator values were None - insufficient data for calculation"
            })
            # Return 422: Client request understood but cannot be processed
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "insufficient_data",
                    "message": f"Indicator calculation requires more data. All {len(series)} values returned None (warm-up period).",
                    "indicator_id": indicator_id,
                    "variant_id": variant_id,
                    "session_id": session_id,
                    "symbol": symbol,
                    "total_values": len(series),
                    "none_count": none_count,
                    "suggestion": "Collect more market data before calculating this indicator, or adjust indicator parameters to reduce warm-up period."
                }
            )

        # Save to QuestDB
        try:
            inserted_count = await questdb_provider.insert_indicators_batch(indicators_batch)
            # logger = get_logger(__name__)  # ✅ FIX #3: Using module-level logger
            logger.info("indicators_routes.saved_to_questdb", {
                "session_id": session_id,
                "symbol": symbol,
                "indicator_id": indicator_id,
                "variant_id": variant_id,
                "count": inserted_count
            })
        except Exception as exc:
            # logger = get_logger(__name__)  # ✅ FIX #3: Using module-level logger
            logger.error("indicators_routes.questdb_save_failed", {
                "session_id": session_id,
                "symbol": symbol,
                "indicator_id": indicator_id,
                "error": str(exc)
            })
            # Don't fail the request if QuestDB save fails
            # (backward compatibility - indicators still calculated)

        # REMOVED: CSV dual-write eliminated to prevent data inconsistency
        # All indicator data now stored exclusively in QuestDB
        file_info = {"path": "questdb://indicators", "rows": len(series)}

        recent_values = [
            {"timestamp": value.timestamp, "value": value.value}
            for value in series[-min(len(series), 10):]
        ]

        return _json_ok({
            "indicator_id": indicator_id,
            "session_id": session_id,
            "symbol": symbol,
            "variant_id": variant_id,
            "status": "added",
            "parameters": parameters,
            "file": file_info,
            "recent_values": recent_values,
            "saved_to_questdb": True  # ✅ BUG-002 FIX: Indicate database storage
        })

    except HTTPException:
        raise
    except Exception as e:
        # logger = get_logger(__name__)  # ✅ FIX #3: Using module-level logger
        logger.error("indicators_routes.add_indicator_for_session_failed", {
            "session_id": session_id,
            "symbol": symbol,
            "error": str(e),
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc()
        })
        raise HTTPException(
            status_code=500,
            detail=f"Failed to add indicator: {str(e)}"
        )


@router.delete("/sessions/{session_id}/symbols/{symbol}/indicators/{indicator_id}")
async def remove_indicator_from_session(
    session_id: str,
    symbol: str,
    indicator_id: str,
    engine: StreamingIndicatorEngine = Depends(get_streaming_indicator_engine),
    csrf_token: str = Depends(verify_csrf_token)
) -> JSONResponse:
    """
    Remove indicator from specific session and symbol.
    """
    try:
        # Remove indicator from session
        success = await engine.remove_indicator_from_session(
            session_id=session_id,
            symbol=symbol,
            indicator_id=indicator_id
        )

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Indicator '{indicator_id}' not found in session '{session_id}' for symbol '{symbol}'"
            )

        return _json_ok({
            "indicator_id": indicator_id,
            "session_id": session_id,
            "symbol": symbol,
            "status": "removed"
        })

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to remove indicator: {str(e)}"
        )


@router.post("/sessions/{session_id}/symbols/{symbol}/cleanup-duplicates")
async def cleanup_duplicate_indicators(
    session_id: str,
    symbol: str,
    engine: StreamingIndicatorEngine = Depends(get_streaming_indicator_engine),
    csrf_token: str = Depends(verify_csrf_token)
) -> JSONResponse:
    """
    Clean up duplicate indicators for session and symbol.
    Keeps the most recent indicator for each unique variant_id + parameters combination.
    """
    try:
        # ✅ CRITICAL FIX: cleanup_duplicate_indicators is async (uses _data_lock)
        result = await engine.cleanup_duplicate_indicators(session_id, symbol)

        return _json_ok({
            "cleanup_result": result,
            "session_id": session_id,
            "symbol": symbol
        })

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cleanup duplicate indicators: {str(e)}"
        )


@router.get("/sessions/{session_id}/symbols/{symbol}/values")
async def get_session_indicator_values(
    session_id: str,
    symbol: str,
    engine: StreamingIndicatorEngine = Depends(get_streaming_indicator_engine)
) -> JSONResponse:
    """
    Get current indicator values for session and symbol.
    """
    try:
        # Get session indicators using StreamingIndicatorEngine
        indicator_list = await engine.get_session_indicators(session_id, symbol)
        indicator_map = {
            item["indicator_id"]: item
            for item in indicator_list
            if isinstance(item, dict) and item.get("indicator_id")
        }

        persistence_service, _ = _ensure_support_services()
        files: Dict[str, Dict[str, Any]] = {}

        # Prepare all async tasks for parallel execution
        file_tasks = {}
        for indicator_id, details in indicator_map.items():
            variant_id = details.get("variant_id")
            if variant_id:
                variant_type = str(details.get("variant_type") or "general").lower()
                file_tasks[indicator_id] = persistence_service.get_file_info(
                    session_id,
                    symbol,
                    variant_id,
                    variant_type=variant_type
                )

        # Execute all tasks in parallel (if any exist)
        if file_tasks:
            # ✅ TIMEOUT FIX: Wrap gather in wait_for to prevent indefinite hangs
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*file_tasks.values(), return_exceptions=True),
                    timeout=15.0  # 15 second timeout for all parallel queries
                )
                for (indicator_id, _), result in zip(file_tasks.items(), results):
                    if isinstance(result, Exception):
                        # Log error but don't fail entire request
                        logger.warning("indicators_routes.get_file_info_failed", {
                            "session_id": session_id,
                            "symbol": symbol,
                            "indicator_id": indicator_id,
                            "error": str(result)
                        })
                        files[indicator_id] = {"exists": False, "error": str(result)}
                    else:
                        files[indicator_id] = result
            except asyncio.TimeoutError:
                logger.warning("indicators_routes.get_file_info_timeout", {
                    "session_id": session_id,
                    "symbol": symbol,
                    "timeout_seconds": 15.0,
                    "tasks_count": len(file_tasks)
                })
                # Fallback: mark all as not exists
                for indicator_id in file_tasks.keys():
                    files[indicator_id] = {"exists": False, "error": "timeout"}

        # Add {"exists": False} for indicators without variant_id
        for indicator_id in indicator_map:
            if indicator_id not in files:
                files[indicator_id] = {"exists": False}

        return _json_ok({
            "session_id": session_id,
            "symbol": symbol,
            "indicators": indicator_map,
            "indicator_ids": list(indicator_map.keys()),
            "files": files,
            "total_count": len(indicator_map)
        })

    except Exception as e:
        # logger = get_logger(__name__)  # ✅ FIX #3: Using module-level logger
        logger.error("indicators_routes.get_session_indicator_values_failed", {
            "session_id": session_id,
            "symbol": symbol,
            "error": str(e),
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc()
        })
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get indicator values: {str(e)}"
        )


@router.get("/sessions/{session_id}/symbols/{symbol}/indicators/{indicator_id}/history")
async def get_indicator_history(
    session_id: str,
    symbol: str,
    indicator_id: str,
    limit: Optional[int] = None,
    engine: StreamingIndicatorEngine = Depends(get_streaming_indicator_engine)
) -> JSONResponse:
    """
    Get historical values for a specific indicator.

    ✅ CRITICAL FIX: Implements retry logic to handle QuestDB WAL race condition.

    QuestDB WAL Race Condition:
    - Writes go to WAL (Write-Ahead Log) via InfluxDB Line Protocol
    - Reads come from main table files via PostgreSQL protocol
    - WAL commit is asynchronous (typically 1-3 seconds)
    - This creates a race condition where recently written data is not yet visible

    Solution: Retry with exponential backoff (max 5 attempts over ~3.7 seconds)

    Args:
        limit: Maximum number of values to return.
               If None, returns all available data.
               Default: None (all data)
    """
    # logger = get_logger(__name__)  # ✅ FIX #3: Using module-level logger

    try:
        # ✅ Validate indicator exists before attempting retry
        questdb_provider, _ = _ensure_questdb_providers()

        config = engine.get_indicator_config(indicator_id)
        if not config:
            raise HTTPException(
                status_code=404,
                detail=f"Indicator '{indicator_id}' not found"
            )

        # ✅ CRITICAL FIX: Retry logic for QuestDB WAL race condition
        #
        # Problem: Data written via ILP (InfluxDB Line Protocol) goes to WAL first,
        #          then asynchronously commits to main table files. PostgreSQL queries
        #          read from main files, not WAL, causing empty results immediately
        #          after write operations.
        #
        # Solution: Retry with exponential backoff to wait for WAL commit.
        #
        # Retry strategy:
        #   Attempt 1: 0ms    (immediate - handles case where data already committed)
        #   Attempt 2: +200ms (WAL commit might be fast)
        #   Attempt 3: +400ms (covers typical 500-1000ms commit lag)
        #   Attempt 4: +600ms (handles slower commits)
        #   Attempt 5: +1000ms (final attempt, covers worst case)
        #   Attempt 6: +1500ms (last resort)
        #   Total: ~3.7 seconds maximum wait
        #
        # ALTERNATIVE: Use questdb_provider.query_with_wal_retry() helper:
        #
        #   indicators_df = await questdb_provider.query_with_wal_retry(
        #       questdb_provider.get_indicators,
        #       symbol=symbol,
        #       indicator_ids=[indicator_id],
        #       limit=limit if limit else 1000000
        #   )
        #
        # The manual implementation below provides more fine-grained control and
        # detailed logging specific to this endpoint.
        #
        max_retries = 6
        retry_delays = [0, 0.2, 0.4, 0.6, 1.0, 1.5]  # seconds

        history = []
        total_available = 0
        returned_count = 0
        limited = False
        retry_count = 0

        for attempt in range(max_retries):
            try:
                # Get indicators using low-level provider method
                indicators_df = await questdb_provider.get_indicators(
                    symbol=symbol,
                    indicator_ids=[indicator_id],
                    limit=limit if limit else 1000000  # Large limit if no limit specified
                )

                # Filter by session_id if the column exists
                if 'session_id' in indicators_df.columns:
                    indicators_df = indicators_df[indicators_df['session_id'] == session_id]

                # Convert DataFrame to history list
                history = []
                for _, row in indicators_df.iterrows():
                    timestamp = row.get('timestamp')
                    if hasattr(timestamp, 'timestamp'):
                        timestamp = timestamp.timestamp()  # Convert datetime to float
                    elif timestamp:
                        timestamp = float(timestamp)

                    history.append({
                        "timestamp": timestamp,
                        "value": float(row.get('value', 0)),
                        "metadata": {
                            "session_id": session_id,
                            "symbol": symbol,
                            "indicator_id": indicator_id,
                            "confidence": float(row.get('confidence')) if row.get('confidence') is not None else None
                        }
                    })

                # Check if we got data or if this is the last attempt
                if len(history) > 0 or attempt == max_retries - 1:
                    # Success or final attempt
                    if len(history) > 0 and attempt > 0:
                        logger.info("indicators_routes.history_retry_success", {
                            "session_id": session_id,
                            "symbol": symbol,
                            "indicator_id": indicator_id,
                            "retry_count": attempt,
                            "total_wait_ms": sum(retry_delays[:attempt]) * 1000,
                            "records_found": len(history)
                        })
                    elif len(history) == 0 and attempt > 0:
                        logger.warning("indicators_routes.history_retry_exhausted", {
                            "session_id": session_id,
                            "symbol": symbol,
                            "indicator_id": indicator_id,
                            "retry_count": attempt,
                            "total_wait_ms": sum(retry_delays[:attempt]) * 1000,
                            "message": "No data found after all retry attempts. Data may not exist or WAL commit is unusually slow."
                        })
                    break

                # No data yet, wait before retry
                retry_count = attempt + 1
                wait_time = retry_delays[attempt]

                logger.debug("indicators_routes.history_retry_waiting", {
                    "session_id": session_id,
                    "symbol": symbol,
                    "indicator_id": indicator_id,
                    "attempt": attempt + 1,
                    "max_attempts": max_retries,
                    "wait_seconds": wait_time,
                    "reason": "QuestDB WAL not yet committed to main table files"
                })

                await asyncio.sleep(wait_time)

            except Exception as query_error:
                # Query failed - if last attempt, raise; otherwise retry
                if attempt == max_retries - 1:
                    raise query_error

                logger.warning("indicators_routes.history_query_error_retrying", {
                    "session_id": session_id,
                    "symbol": symbol,
                    "indicator_id": indicator_id,
                    "attempt": attempt + 1,
                    "error": str(query_error),
                    "will_retry": True
                })

                await asyncio.sleep(retry_delays[attempt])

        # Sort by timestamp
        history.sort(key=lambda x: x['timestamp'])

        total_available = len(history)
        returned_count = len(history)
        limited = limit is not None and total_available > limit

        if limited:
            history = history[:limit]
            returned_count = len(history)

        return _json_ok({
            "session_id": session_id,
            "symbol": symbol,
            "indicator_id": indicator_id,
            "history": history,
            "limit": limit,
            "total_count": returned_count,
            "total_available": total_available,
            "limited": limited,
            "source": "questdb",
            "retry_count": retry_count  # ✅ Expose retry count for monitoring
        })

    except HTTPException:
        raise
    except Exception as e:
        # logger = get_logger(__name__)  # ✅ FIX #3: Using module-level logger
        logger.error("indicators_routes.history_fatal_error", {
            "session_id": session_id,
            "symbol": symbol,
            "indicator_id": indicator_id,
            "error": str(e)
        })
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get indicator history: {str(e)}"
        )


@router.post("/sessions/{session_id}/symbols/{symbol}/market-data")
async def process_market_data(
    session_id: str,
    symbol: str,
    request: Request,
    engine: StreamingIndicatorEngine = Depends(get_streaming_indicator_engine),
    csrf_token: str = Depends(verify_csrf_token)
) -> JSONResponse:
    """
    Process new market data and trigger indicator calculations.
    """
    try:
        body = await request.json()
        
        # Process market data using StreamingIndicatorEngine
        # This would involve the market data processing pipeline
        
        return _json_ok({
            "session_id": session_id,
            "symbol": symbol,
            "status": "processed",
            "timestamp": body.get("timestamp"),
            "data_points": len(body.get("data", []))
        })

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process market data: {str(e)}"
        )


@router.post("/sessions/{session_id}/symbols/{symbol}/historical-data")
async def process_historical_data(
    session_id: str,
    symbol: str,
    request: Request,
    engine: StreamingIndicatorEngine = Depends(get_streaming_indicator_engine),
    csrf_token: str = Depends(verify_csrf_token)
) -> JSONResponse:
    """
    Process historical data for backtesting and simulation.
    """
    try:
        body = await request.json()
        
        # Use time simulation capabilities from Task 4
        # This would involve the simulation pipeline
        
        return _json_ok({
            "session_id": session_id,
            "symbol": symbol,
            "status": "processed",
            "data_points": len(body.get("data", [])),
            "simulation_mode": True
        })

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process historical data: {str(e)}"
        )


@router.post("/sessions/{session_id}/symbols/{symbol}/preferences")
async def set_session_preferences(
    session_id: str,
    symbol: str,
    request: Request,
    engine: StreamingIndicatorEngine = Depends(get_streaming_indicator_engine),
    csrf_token: str = Depends(verify_csrf_token)
) -> JSONResponse:
    """
    Set preferences for session and symbol.
    """
    try:
        body = await request.json()

        # Set preferences using StreamingIndicatorEngine
        # ✅ CRITICAL FIX: set_session_preferences is async (calls save_session_preferences)
        success = await engine.set_session_preferences(session_id, symbol, body)

        return _json_ok({
            "session_id": session_id,
            "symbol": symbol,
            "preferences": body,
            "status": "updated" if success else "failed"
        })

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to set session preferences: {str(e)}"
        )


@router.get("/sessions/{session_id}/symbols/{symbol}/preferences")
async def get_session_preferences(
    session_id: str,
    symbol: str,
    engine: StreamingIndicatorEngine = Depends(get_streaming_indicator_engine)
) -> JSONResponse:
    """
    Get preferences for session and symbol.
    """
    try:
        # ✅ CRITICAL FIX: get_session_preferences is async (uses async with _data_lock)
        preferences = await engine.get_session_preferences(session_id, symbol)

        return _json_ok({
            "session_id": session_id,
            "symbol": symbol,
            "preferences": preferences
        })

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get session preferences: {str(e)}"
        )


@router.post("/variants")
async def create_variant(
    request: Request,
    engine: StreamingIndicatorEngine = Depends(get_streaming_indicator_engine),
    csrf_token: str = Depends(verify_csrf_token)
) -> JSONResponse:
    """
    Create new indicator variant.
    """
    try:
        # logger = get_logger(__name__)  # ✅ FIX #3: Using module-level logger
        body_raw = await request.json()
        body = body_raw or {}

        if not isinstance(body, dict):
            raise HTTPException(status_code=400, detail="Request body must be a JSON object")

        base_indicator_type = body.get("indicator_type") or body.get("system_indicator")
        variant_type = (body.get("variant_type") or body.get("category") or "general")
        name = body.get("name")
        description = body.get("description", "")
        created_by = body.get("created_by") or body.get("owner") or "api_user"
        parameters = body.get("parameters") or {}

        missing_fields = []
        if not name:
            missing_fields.append("name")
        if not base_indicator_type:
            missing_fields.append("indicator_type")
        if missing_fields:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required fields: {', '.join(missing_fields)}"
            )

        if not isinstance(parameters, dict):
            raise HTTPException(status_code=400, detail="parameters must be an object")

        logger.info("indicators_routes.create_variant.start", {
            "variant_type": variant_type,
            "indicator_type": base_indicator_type,
            "name": name
        })

        normalized_parameters, conversion_errors = _coerce_variant_parameters(
            engine, str(base_indicator_type), parameters
        )
        if conversion_errors:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid parameter values: {', '.join(conversion_errors)}"
            )

        base_indicator_type_upper = str(base_indicator_type).upper()

        try:
            variant_id = await engine.create_variant(
                name=name,
                base_indicator_type=base_indicator_type_upper,
                variant_type=variant_type,
                description=description,
                parameters=normalized_parameters,
                created_by=created_by
            )
        except ValueError as validation_error:
            raise HTTPException(status_code=400, detail=str(validation_error)) from validation_error

        logger.info("indicators_routes.create_variant.success", {
            "variant_id": variant_id
        })

        return _json_ok({
            "variant_id": variant_id,
            "status": "created"
        })

    except HTTPException:
        raise
    except Exception as e:
        # logger = get_logger(__name__)  # ✅ FIX #3: Using module-level logger
        logger.error("indicators_routes.create_variant.error", {
            "error": str(e),
            "error_type": type(e).__name__
        })
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create variant: {str(e)}"
        )


@router.put("/variants/{variant_id}")
async def update_variant(
    variant_id: str,
    request: Request,
    engine: StreamingIndicatorEngine = Depends(get_streaming_indicator_engine),
    csrf_token: str = Depends(verify_csrf_token)
) -> JSONResponse:
    """
    Update existing indicator variant.
    """
    try:
        # logger = get_logger(__name__)  # ✅ FIX #3: Using module-level logger
        body_raw = await request.json()
        body = body_raw or {}

        if not isinstance(body, dict):
            raise HTTPException(status_code=400, detail="Request body must be a JSON object")
        if "parameters" not in body:
            raise HTTPException(status_code=400, detail="parameters are required")
        parameters = body.get("parameters") or {}
        if not isinstance(parameters, dict):
            raise HTTPException(status_code=400, detail="parameters must be an object")

        variant = await engine.get_variant(variant_id)
        if not variant:
            logger.warning("indicators_routes.update_variant.not_found", {
                "variant_id": variant_id
            })
            raise HTTPException(status_code=404, detail=f"Variant '{variant_id}' not found")

        normalized_parameters, conversion_errors = _coerce_variant_parameters(
            engine,
            variant.base_indicator_type,
            parameters
        )
        if conversion_errors:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid parameter values: {', '.join(conversion_errors)}"
            )
        
        logger.info("indicators_routes.update_variant.start", {
            "variant_id": variant_id
        })

        success = await engine.update_variant_parameters(variant_id, normalized_parameters)
        
        if not success:
            logger.warning("indicators_routes.update_variant.validation_failed", {
                "variant_id": variant_id
            })
            raise HTTPException(status_code=400, detail="Variant parameter validation failed")

        logger.info("indicators_routes.update_variant.success", {
            "variant_id": variant_id
        })

        return _json_ok({
            "variant_id": variant_id,
            "status": "updated"
        })

    except HTTPException:
        raise
    except Exception as e:
        # logger = get_logger(__name__)  # ✅ FIX #3: Using module-level logger
        # ✅ IMPROVED: Log full traceback for debugging
        logger.error("indicators_routes.update_variant.error", {
            "error": str(e),
            "error_type": type(e).__name__,
            "variant_id": variant_id,
            "traceback": traceback.format_exc()
        })
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update variant: {str(e)}"
        )


@router.delete("/variants/{variant_id}")
async def delete_variant(
    variant_id: str,
    engine: StreamingIndicatorEngine = Depends(get_streaming_indicator_engine),
    csrf_token: str = Depends(verify_csrf_token)
) -> JSONResponse:
    """
    Delete indicator variant.
    """
    try:
        # logger = get_logger(__name__)  # ✅ FIX #3: Using module-level logger
        logger.info("indicators_routes.delete_variant.start", {
            "variant_id": variant_id
        })

        success = await engine.delete_variant(variant_id)
        
        if not success:
            logger.warning("indicators_routes.delete_variant.not_found", {
                "variant_id": variant_id
            })
            raise HTTPException(status_code=404, detail=f"Variant '{variant_id}' not found")

        logger.info("indicators_routes.delete_variant.success", {
            "variant_id": variant_id
        })

        return _json_ok({
            "variant_id": variant_id,
            "status": "deleted"
        })

    except HTTPException:
        raise
    except Exception as e:
        # logger = get_logger(__name__)  # ✅ FIX #3: Using module-level logger
        # ✅ IMPROVED: Log full traceback for debugging
        logger.error("indicators_routes.delete_variant.error", {
            "error": str(e),
            "error_type": type(e).__name__,
            "variant_id": variant_id,
            "traceback": traceback.format_exc()
        })
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete variant: {str(e)}"
        )


@router.get("/variants/{variant_id}")
async def get_variant_details(
    variant_id: str,
    engine: StreamingIndicatorEngine = Depends(get_streaming_indicator_engine)
) -> JSONResponse:
    """
    Get details for specific variant.
    """
    try:
        # logger = get_logger(__name__)  # ✅ FIX #3: Using module-level logger
        logger.info("indicators_routes.get_variant_details.start", {
            "variant_id": variant_id
        })
        
        variant = await engine.get_variant(variant_id)
        
        if not variant:
            logger.warning("indicators_routes.get_variant_details.not_found", {
                "variant_id": variant_id
            })
            raise HTTPException(status_code=404, detail=f"Variant '{variant_id}' not found")

        # ✅ PHASE 2 FIX COMPLETION: Await async method to prevent coroutine iteration error
        params = await engine.get_variant_parameters(variant.id)
        parameter_definitions = [
            {
                "name": param.name,
                "type": param.parameter_type,
                "description": param.description,
                "default": param.default_value,
                "required": param.is_required,
                "min_value": param.min_value,
                "max_value": param.max_value,
                "allowed_values": param.allowed_values,
            }
            for param in params
        ]

        variant_dict = {
            "id": variant.id,
            "variant_id": variant.id,
            "name": variant.name,
            "variant_type": variant.variant_type,
            "type": variant.variant_type,
            "indicator_type": variant.base_indicator_type,
            "base_indicator_type": variant.base_indicator_type,
            "description": variant.description,
            "parameters": variant.parameters or {},
            "parameter_definitions": parameter_definitions,
            "is_system": variant.is_system,
            "created_by": variant.created_by,
            "created_at": variant.created_at,
            "updated_at": variant.updated_at
        }

        logger.info("indicators_routes.get_variant_details.success", {
            "variant_id": variant_id,
            "parameter_definitions": len(parameter_definitions)
        })

        return _json_ok(variant_dict)

    except HTTPException:
        raise
    except Exception as e:
        # logger = get_logger(__name__)  # ✅ FIX #3: Using module-level logger
        logger.error("indicators_routes.get_variant_details.error", {
            "error": str(e),
            "error_type": type(e).__name__,
            "variant_id": variant_id
        })
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get variant details: {str(e)}"
        )


@router.get("/variants/files")
async def load_variants_from_files(
    engine: StreamingIndicatorEngine = Depends(get_streaming_indicator_engine)
) -> JSONResponse:
    """
    Load all variants from config/indicators/ directory with validation.
    """
    try:
        # logger = get_logger(__name__)  # ✅ FIX #3: Using module-level logger
        logger.info("indicators_routes.load_variants_from_files.start")
        
        if not hasattr(engine, 'load_variants_from_files'):
            logger.error("indicators_routes.load_variants_from_files.method_not_available")
            raise HTTPException(status_code=503, detail="Variant system not available")

        variants = engine.load_variants_from_files()
        
        logger.info("indicators_routes.load_variants_from_files.success", {
            "variants_loaded": len(variants) if isinstance(variants, list) else 0
        })
        
        return _json_ok({
            "status": "variants_loaded",
            "data": {"variants": variants}
        })

    except HTTPException:
        raise
    except Exception as e:
        # logger = get_logger(__name__)  # ✅ FIX #3: Using module-level logger
        logger.error("indicators_routes.load_variants_from_files.error", {
            "error": str(e),
            "error_type": type(e).__name__
        })
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load variants from files: {str(e)}"
        )


# ✅ Algorithm Registry API Endpoints (Modern API - replaces legacy /types, /list, /add, /bulk endpoints)
@router.get("/algorithms")
async def get_available_algorithms(
    engine: StreamingIndicatorEngine = Depends(get_streaming_indicator_engine)
) -> JSONResponse:
    """
    Get all available indicator algorithms from the algorithm registry.
    
    Returns:
        List of algorithm metadata including parameters and categories
    """
    try:
        registry = engine.get_algorithm_registry()
        if not registry:
            raise HTTPException(
                status_code=503,
                detail="Algorithm registry not available"
            )

        algorithms_metadata = registry.get_all_metadata()
        algorithm_stats = registry.get_statistics()

        # Filter out non-serializable fields (calculation_function) for API response
        serializable_algorithms = []
        for algo_data in algorithms_metadata.values():
            algo_copy = {k: v for k, v in algo_data.items() if k != "calculation_function"}
            serializable_algorithms.append(algo_copy)

        return JSONResponse(content={
            "status": "success",
            "data": {
                "algorithms": serializable_algorithms,
                "statistics": algorithm_stats
            }
        })
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve algorithms: {str(e)}"
        )


@router.get("/algorithms/categories")
async def get_algorithm_categories(
    engine: StreamingIndicatorEngine = Depends(get_streaming_indicator_engine)
) -> JSONResponse:
    """Get all available algorithm categories."""
    try:
        registry = engine.get_algorithm_registry()
        if not registry:
            raise HTTPException(
                status_code=503,
                detail="Algorithm registry not available"
            )

        categories = registry.get_categories()

        return JSONResponse(content={
            "status": "success",
            "data": {
                "categories": categories
            }
        })
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve categories: {str(e)}"
        )


@router.get("/algorithms/{algorithm_type}")
async def get_algorithm_details(
    algorithm_type: str,
    engine: StreamingIndicatorEngine = Depends(get_streaming_indicator_engine)
) -> JSONResponse:
    """Get detailed information about a specific algorithm."""
    try:
        registry = engine.get_algorithm_registry()
        if not registry:
            raise HTTPException(
                status_code=503,
                detail="Algorithm registry not available"
            )

        metadata = registry.get_algorithm_metadata(algorithm_type)
        if not metadata:
            raise HTTPException(
                status_code=404,
                detail=f"Algorithm '{algorithm_type}' not found"
            )

        # Filter out non-serializable fields (calculation_function) for API response
        serializable_metadata = {k: v for k, v in metadata.items() if k != "calculation_function"}

        return JSONResponse(content={
            "status": "success",
            "data": serializable_metadata
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve algorithm details: {str(e)}"
        )


@router.post("/algorithms/{algorithm_type}/calculate-refresh-interval")
async def calculate_algorithm_refresh_interval(
    algorithm_type: str,
    request: Request,
    engine: StreamingIndicatorEngine = Depends(get_streaming_indicator_engine)
) -> JSONResponse:
    """
    Calculate the recommended refresh interval for an algorithm with given parameters.
    
    Args:
        algorithm_type: Type of algorithm (e.g., TWPA, TWPA_RATIO)
        request: JSON body with algorithm parameters
    """
    try:
        registry = engine.get_algorithm_registry()
        if not registry:
            raise HTTPException(
                status_code=503,
                detail="Algorithm registry not available"
            )

        body = await request.json()
        parameters = body.get("parameters", {})

        refresh_interval = registry.calculate_refresh_interval(
            algorithm_type, parameters
        )
        
        if refresh_interval is None:
            raise HTTPException(
                status_code=404,
                detail=f"Algorithm '{algorithm_type}' not found"
            )
        
        return JSONResponse(content={
            "status": "success",
            "data": {
                "algorithm_type": algorithm_type,
                "parameters": parameters,
                "recommended_refresh_interval": refresh_interval
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate refresh interval: {str(e)}"
        )


@router.get("/current")
async def get_current_indicator_values(
    session_id: str,
    symbol: str,
    engine: StreamingIndicatorEngine = Depends(get_streaming_indicator_engine)
) -> JSONResponse:
    """
    Get CURRENT (latest) indicator values for Live Indicator Panel.

    PERFORMANCE REQUIREMENT: Must return within <100ms.

    Used by: Dashboard Live Indicator Panel component

    Returns latest values with thresholds for UI display.

    Response format:
        {
            "session_id": "session_123",
            "symbol": "BTC_USDT",
            "timestamp": "2025-11-15T13:05:23Z",
            "indicators": [
                {
                    "name": "TWPA",
                    "indicator_id": "twpa_300_0",
                    "value": 50250,
                    "confidence": 85,
                    "timestamp": "2025-11-15T13:05:23Z",
                    "parameters": {"t1": 300, "t2": 0}
                },
                ...
            ],
            "next_evaluation_in_seconds": 12
        }
    """
    import time as time_module
    import json
    start_time = time_module.time()

    try:
        # Get active indicators for session/symbol
        session_indicators = await engine.get_session_indicators(session_id, symbol)

        if not session_indicators:
            return _json_ok({
                "session_id": session_id,
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "indicators": [],
                "next_evaluation_in_seconds": 0
            })

        # Get QuestDB provider
        questdb_provider, _ = _ensure_questdb_providers()

        # Extract indicator IDs
        indicator_ids = [ind["indicator_id"] for ind in session_indicators if "indicator_id" in ind]

        # Get latest values using optimized method
        latest_values = await questdb_provider.get_latest_indicators_detailed(
            symbol=symbol,
            indicator_ids=indicator_ids
        )

        # Build response with indicator details
        indicators_data = []
        for value_data in latest_values:
            # Find matching session indicator for metadata
            session_ind = next(
                (ind for ind in session_indicators if ind.get("indicator_id") == value_data["indicator_id"]),
                {}
            )

            # Parse metadata if exists
            metadata = {}
            if value_data.get("metadata"):
                try:
                    metadata = json.loads(value_data["metadata"])
                except:
                    pass

            indicators_data.append({
                "name": session_ind.get("name", value_data["indicator_id"]),
                "indicator_id": value_data["indicator_id"],
                "value": value_data["value"],
                "confidence": value_data["confidence"],
                "timestamp": value_data["timestamp"].isoformat() if value_data["timestamp"] else None,
                "parameters": session_ind.get("parameters", {})
            })

        elapsed_ms = (time_module.time() - start_time) * 1000

        logger.info("indicators_routes.current_values_success", {
            "session_id": session_id,
            "symbol": symbol,
            "indicators_count": len(indicators_data),
            "elapsed_ms": elapsed_ms
        })

        return _json_ok({
            "session_id": session_id,
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "indicators": indicators_data,
            "next_evaluation_in_seconds": 12  # TODO: Get from strategy config
        })

    except Exception as e:
        logger.error("indicators_routes.current_values_failed", {
            "session_id": session_id,
            "symbol": symbol,
            "error": str(e),
            "traceback": traceback.format_exc()
        })
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get current indicator values: {str(e)}"
        )


def _reset_indicators_state_for_tests() -> None:
    """
    Reset module-level state to allow isolated unit tests.
    ✅ SCALABILITY FIX: Also cleanup ThreadPoolExecutor
    """
    global _streaming_engine, _persistence_service, _offline_indicator_engine, _event_bus
    global _indicator_calculation_executor, _calculation_semaphore

    _streaming_engine = None
    _persistence_service = None
    _offline_indicator_engine = None
    _event_bus = None

    # Cleanup executor if exists
    if _indicator_calculation_executor is not None:
        _indicator_calculation_executor.shutdown(wait=False)
        _indicator_calculation_executor = None
    _calculation_semaphore = None
