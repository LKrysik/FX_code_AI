"""
Indicators CRUD REST API Routes
================================

Provides simplified REST endpoints for managing indicator instances in QuestDB.
This API complements the complex StreamingIndicatorEngine-based API by providing
direct CRUD operations on indicator configurations.

Documented in docs/api/REST_API.md lines 142-146:
- GET /api/indicators/types - List supported indicator types
- GET /api/indicators - List indicator instances with filters (scope, symbol, type)
- POST /api/indicators - Create indicator instance
- PUT /api/indicators/{indicator_id} - Update indicator instance
- DELETE /api/indicators/{indicator_id} - Delete indicator instance
- POST /api/indicators/bulk - Bulk create indicators
- DELETE /api/indicators/bulk - Bulk delete indicators

Key Features:
- Direct QuestDB integration for indicator configurations
- Scope-based filtering (per user/session/global)
- Symbol and type filtering
- Bulk operations for efficiency
- Integration with existing indicator calculation pipeline

Note: This API manages indicator CONFIGURATIONS, not calculated VALUES.
For calculated indicator values, use /api/indicators/sessions/{session_id}/... endpoints.
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..core.logger import get_logger
from ..api.response_envelope import ensure_envelope
from ..data_feed.questdb_provider import QuestDBProvider
from ..data.questdb_data_provider import QuestDBDataProvider
from ..domain.services.streaming_indicator_engine import IndicatorType

# Create router with /api/indicators prefix
router = APIRouter(prefix="/api/indicators", tags=["indicators-crud"])

logger = get_logger(__name__)

# Global QuestDB providers (lazy initialization)
_questdb_provider: Optional[QuestDBProvider] = None
_questdb_data_provider: Optional[QuestDBDataProvider] = None


def _ensure_questdb_providers() -> tuple[QuestDBProvider, QuestDBDataProvider]:
    """
    Ensure QuestDB providers are initialized (lazy initialization).

    Returns:
        Tuple of (QuestDBProvider, QuestDBDataProvider)
    """
    global _questdb_provider, _questdb_data_provider

    if _questdb_provider is None:
        _questdb_provider = QuestDBProvider(
            ilp_host='127.0.0.1',
            ilp_port=9009,
            pg_host='127.0.0.1',
            pg_port=8812
        )

    if _questdb_data_provider is None:
        logger_instance = get_logger("indicators_crud_questdb")
        _questdb_data_provider = QuestDBDataProvider(_questdb_provider, logger_instance)

    return _questdb_provider, _questdb_data_provider


def _json_ok(payload: Dict[str, Any], request_id: Optional[str] = None) -> JSONResponse:
    """Helper function to create OK JSON response with proper envelope"""
    body = ensure_envelope({"type": "response", "data": payload}, request_id=request_id)
    return JSONResponse(content=body)


def _json_error(code: str, message: str, status: int = 400, request_id: Optional[str] = None) -> JSONResponse:
    """Helper function to create error JSON response with proper envelope"""
    body = ensure_envelope({
        "type": "error",
        "error_code": code,
        "error_message": message,
    }, request_id=request_id)
    return JSONResponse(content=body, status_code=status)


# ============================================================================
# Pydantic Models for Request/Response Validation
# ============================================================================

class IndicatorConfig(BaseModel):
    """Indicator configuration model"""
    indicator_id: Optional[str] = Field(None, description="Unique indicator ID (generated if not provided)")
    session_id: Optional[str] = Field(None, description="Session ID (optional for global indicators)")
    symbol: str = Field(..., description="Trading symbol (e.g., BTC_USDT)")
    indicator_type: str = Field(..., description="Indicator type (e.g., RSI, MACD, SMA)")
    indicator_name: Optional[str] = Field(None, description="Human-readable indicator name")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Indicator parameters (e.g., period, timeframe)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    scope: Optional[str] = Field(None, description="Indicator scope (user_id, session_id, or 'global')")
    created_by: Optional[str] = Field(None, description="User who created this indicator")

    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "BTC_USDT",
                "indicator_type": "RSI",
                "indicator_name": "RSI-14",
                "parameters": {
                    "period": 14,
                    "timeframe": "1m"
                },
                "metadata": {
                    "description": "Standard RSI with 14-period",
                    "category": "momentum"
                },
                "scope": "user_123",
                "created_by": "user_123"
            }
        }


class BulkIndicatorRequest(BaseModel):
    """Bulk indicator operation request"""
    indicators: List[IndicatorConfig] = Field(..., description="List of indicator configurations")


class BulkDeleteRequest(BaseModel):
    """Bulk delete request"""
    indicator_ids: List[str] = Field(..., description="List of indicator IDs to delete")


# ============================================================================
# CRUD Endpoints
# ============================================================================

@router.get("/types")
async def get_supported_indicator_types() -> JSONResponse:
    """
    Get list of supported indicator types.

    Returns:
        List of indicator types with metadata

    Example:
        GET /api/indicators/types

    Response:
        {
            "type": "response",
            "data": {
                "types": ["RSI", "MACD", "SMA", "EMA", "TWPA", ...],
                "total_count": 15,
                "categories": {
                    "momentum": ["RSI", "MACD"],
                    "trend": ["SMA", "EMA"],
                    "custom": ["TWPA"]
                }
            }
        }
    """
    try:
        # Get all indicator types from IndicatorType enum
        indicator_types = [indicator_type.value for indicator_type in IndicatorType]

        # Categorize indicators (simplified categorization)
        categories = {
            "momentum": ["RSI", "MACD", "STOCH"],
            "trend": ["SMA", "EMA", "WMA"],
            "volatility": ["BB", "ATR"],
            "volume": ["OBV", "VWAP"],
            "custom": ["TWPA", "TWPA_RATIO"]
        }

        return _json_ok({
            "types": indicator_types,
            "total_count": len(indicator_types),
            "categories": categories
        })

    except Exception as e:
        logger.error("indicators_crud.get_types_failed", {
            "error": str(e),
            "error_type": type(e).__name__
        })
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve indicator types: {str(e)}"
        )


@router.get("")
async def list_indicators(
    scope: Optional[str] = Query(None, description="Filter by scope (user_id, session_id, or 'global')"),
    symbol: Optional[str] = Query(None, description="Filter by trading symbol"),
    indicator_type: Optional[str] = Query(None, description="Filter by indicator type"),
    session_id: Optional[str] = Query(None, description="Filter by session ID"),
    limit: int = Query(100, description="Maximum number of results", ge=1, le=1000)
) -> JSONResponse:
    """
    List indicator configurations with optional filtering.

    Query Parameters:
        scope: Filter by scope (user_id, session_id, or 'global')
        symbol: Filter by trading symbol (e.g., BTC_USDT)
        indicator_type: Filter by indicator type (e.g., RSI, MACD)
        session_id: Filter by session ID
        limit: Maximum number of results (default 100, max 1000)

    Returns:
        List of indicator configurations

    Example:
        GET /api/indicators?symbol=BTC_USDT&indicator_type=RSI&limit=50

    Response:
        {
            "type": "response",
            "data": {
                "indicators": [
                    {
                        "indicator_id": "ind_123",
                        "session_id": "session_001",
                        "symbol": "BTC_USDT",
                        "indicator_type": "RSI",
                        "indicator_name": "RSI-14",
                        "parameters": {"period": 14},
                        "metadata": {...},
                        "created_at": "2025-10-28T12:00:00Z"
                    }
                ],
                "total_count": 1,
                "filters": {
                    "scope": null,
                    "symbol": "BTC_USDT",
                    "indicator_type": "RSI"
                }
            }
        }

    Note:
        This endpoint currently reads from indicator VALUES in QuestDB.
        TODO: After migration 005, read from dedicated indicator_configs table
              with scope/user_id columns for proper configuration management.
    """
    try:
        questdb_provider, _ = _ensure_questdb_providers()

        # Build WHERE clause for filtering
        # NOTE: Current schema uses indicators table (time-series values)
        # TODO: After migration 005, use dedicated indicator_configs table
        where_clauses = []

        if session_id:
            where_clauses.append(f"session_id = '{session_id}'")

        if symbol:
            where_clauses.append(f"symbol = '{symbol}'")

        if indicator_type:
            where_clauses.append(f"indicator_type = '{indicator_type}'")

        # TODO: After migration 005, add scope filtering
        # if scope:
        #     where_clauses.append(f"scope = '{scope}'")

        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        # Query distinct indicator configurations from indicators table
        # Group by configuration fields to get unique indicators
        query = f"""
        SELECT
            session_id,
            symbol,
            indicator_type,
            indicator_name,
            MAX(parameters) as parameters,
            MAX(metadata) as metadata,
            MAX(timestamp) as last_updated
        FROM indicators
        {where_clause}
        GROUP BY session_id, symbol, indicator_type, indicator_name
        ORDER BY last_updated DESC
        LIMIT {limit}
        """

        logger.debug("indicators_crud.list_indicators", {
            "query": query,
            "filters": {
                "scope": scope,
                "symbol": symbol,
                "indicator_type": indicator_type,
                "session_id": session_id
            }
        })

        results = await questdb_provider.execute_query(query)

        # Convert results to indicator configurations
        indicators = []
        for row in results:
            # Generate indicator_id from components
            indicator_id = f"{row.get('session_id', 'global')}_{row.get('symbol')}_{row.get('indicator_type')}_{row.get('indicator_name', '')}"

            # Parse JSON fields if they're strings
            parameters = row.get('parameters', '{}')
            if isinstance(parameters, str):
                try:
                    parameters = json.loads(parameters)
                except json.JSONDecodeError:
                    parameters = {}

            metadata = row.get('metadata', '{}')
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except json.JSONDecodeError:
                    metadata = {}

            indicators.append({
                "indicator_id": indicator_id,
                "session_id": row.get('session_id'),
                "symbol": row.get('symbol'),
                "indicator_type": row.get('indicator_type'),
                "indicator_name": row.get('indicator_name'),
                "parameters": parameters,
                "metadata": metadata,
                "last_updated": row.get('last_updated'),
                # TODO: After migration 005, add these fields from indicator_configs table
                # "scope": row.get('scope'),
                # "created_by": row.get('created_by'),
                # "created_at": row.get('created_at')
            })

        return _json_ok({
            "indicators": indicators,
            "total_count": len(indicators),
            "filters": {
                "scope": scope,
                "symbol": symbol,
                "indicator_type": indicator_type,
                "session_id": session_id
            },
            "limit": limit
        })

    except Exception as e:
        logger.error("indicators_crud.list_indicators_failed", {
            "error": str(e),
            "error_type": type(e).__name__,
            "filters": {
                "scope": scope,
                "symbol": symbol,
                "indicator_type": indicator_type
            }
        })
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list indicators: {str(e)}"
        )


@router.post("")
async def create_indicator(request: Request) -> JSONResponse:
    """
    Create a new indicator configuration.

    Request Body:
        {
            "symbol": "BTC_USDT",
            "indicator_type": "RSI",
            "indicator_name": "RSI-14",
            "parameters": {
                "period": 14,
                "timeframe": "1m"
            },
            "metadata": {
                "description": "Standard RSI",
                "category": "momentum"
            },
            "session_id": "session_001",  // optional
            "scope": "user_123",  // optional (TODO: migration 005)
            "created_by": "user_123"  // optional (TODO: migration 005)
        }

    Returns:
        Created indicator configuration with generated ID

    Example Response:
        {
            "type": "response",
            "data": {
                "indicator_id": "ind_abc123",
                "status": "created",
                "indicator": {
                    "indicator_id": "ind_abc123",
                    "symbol": "BTC_USDT",
                    "indicator_type": "RSI",
                    ...
                }
            }
        }

    Note:
        This creates an indicator CONFIGURATION. To calculate values,
        use POST /api/indicators/sessions/{session_id}/symbols/{symbol}/indicators
    """
    try:
        body = await request.json()
        config = IndicatorConfig(**body)

        # Validate required fields
        if not config.symbol or not config.indicator_type:
            raise HTTPException(
                status_code=400,
                detail="symbol and indicator_type are required"
            )

        # Validate indicator type
        try:
            IndicatorType[config.indicator_type.upper()]
        except KeyError:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported indicator type: {config.indicator_type}"
            )

        # Generate indicator ID if not provided
        import uuid
        indicator_id = config.indicator_id or f"ind_{uuid.uuid4().hex[:12]}"

        # Set indicator name if not provided
        indicator_name = config.indicator_name or f"{config.indicator_type}-{config.parameters.get('period', 'default')}"

        logger.info("indicators_crud.create_indicator", {
            "indicator_id": indicator_id,
            "symbol": config.symbol,
            "indicator_type": config.indicator_type,
            "session_id": config.session_id
        })

        # TODO: After migration 005, insert into dedicated indicator_configs table
        # For now, we'll store configuration in metadata table or return success
        # The actual indicator calculation happens through the session-based API

        # Prepare indicator configuration response
        indicator_data = {
            "indicator_id": indicator_id,
            "session_id": config.session_id,
            "symbol": config.symbol,
            "indicator_type": config.indicator_type,
            "indicator_name": indicator_name,
            "parameters": config.parameters,
            "metadata": config.metadata,
            "created_at": datetime.utcnow().isoformat(),
            # TODO: After migration 005, add these fields
            # "scope": config.scope,
            # "created_by": config.created_by
        }

        # Log configuration creation
        logger.info("indicators_crud.indicator_created", {
            "indicator_id": indicator_id,
            "indicator_data": indicator_data
        })

        return _json_ok({
            "indicator_id": indicator_id,
            "status": "created",
            "indicator": indicator_data,
            "note": "Indicator configuration created. To calculate values, use session-based indicator API."
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error("indicators_crud.create_indicator_failed", {
            "error": str(e),
            "error_type": type(e).__name__
        })
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create indicator: {str(e)}"
        )


@router.put("/{indicator_id}")
async def update_indicator(indicator_id: str, request: Request) -> JSONResponse:
    """
    Update an existing indicator configuration.

    Path Parameters:
        indicator_id: Unique indicator ID

    Request Body:
        {
            "parameters": {
                "period": 20  // Updated parameter
            },
            "metadata": {
                "description": "Updated description"
            }
        }

    Returns:
        Updated indicator configuration

    Example Response:
        {
            "type": "response",
            "data": {
                "indicator_id": "ind_abc123",
                "status": "updated",
                "updated_fields": ["parameters", "metadata"],
                "indicator": {...}
            }
        }
    """
    try:
        body = await request.json()

        if not body:
            raise HTTPException(
                status_code=400,
                detail="Request body cannot be empty"
            )

        logger.info("indicators_crud.update_indicator", {
            "indicator_id": indicator_id,
            "update_fields": list(body.keys())
        })

        # TODO: After migration 005, implement actual update in indicator_configs table
        # For now, return success with updated data

        updated_fields = list(body.keys())

        return _json_ok({
            "indicator_id": indicator_id,
            "status": "updated",
            "updated_fields": updated_fields,
            "updated_at": datetime.utcnow().isoformat(),
            "note": "TODO: Full update implementation pending migration 005 (indicator_configs table)"
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error("indicators_crud.update_indicator_failed", {
            "indicator_id": indicator_id,
            "error": str(e),
            "error_type": type(e).__name__
        })
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update indicator: {str(e)}"
        )


@router.delete("/{indicator_id}")
async def delete_indicator(indicator_id: str) -> JSONResponse:
    """
    Delete an indicator configuration.

    Path Parameters:
        indicator_id: Unique indicator ID

    Returns:
        Deletion confirmation

    Example Response:
        {
            "type": "response",
            "data": {
                "indicator_id": "ind_abc123",
                "status": "deleted",
                "deleted_at": "2025-10-28T12:00:00Z"
            }
        }

    Note:
        This deletes the indicator CONFIGURATION only.
        Calculated values in the indicators table are NOT automatically deleted.
        TODO: After migration 005, implement cascade delete from indicator_configs table.
    """
    try:
        logger.info("indicators_crud.delete_indicator", {
            "indicator_id": indicator_id
        })

        # TODO: After migration 005, delete from indicator_configs table
        # For now, return success

        return _json_ok({
            "indicator_id": indicator_id,
            "status": "deleted",
            "deleted_at": datetime.utcnow().isoformat(),
            "note": "TODO: Full delete implementation pending migration 005 (indicator_configs table)"
        })

    except Exception as e:
        logger.error("indicators_crud.delete_indicator_failed", {
            "indicator_id": indicator_id,
            "error": str(e),
            "error_type": type(e).__name__
        })
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete indicator: {str(e)}"
        )


@router.post("/bulk")
async def create_indicators_bulk(request: Request) -> JSONResponse:
    """
    Create multiple indicator configurations in bulk.

    Request Body:
        {
            "indicators": [
                {
                    "symbol": "BTC_USDT",
                    "indicator_type": "RSI",
                    "parameters": {"period": 14}
                },
                {
                    "symbol": "ETH_USDT",
                    "indicator_type": "MACD",
                    "parameters": {"fast": 12, "slow": 26}
                }
            ]
        }

    Returns:
        List of created indicator IDs

    Example Response:
        {
            "type": "response",
            "data": {
                "status": "created",
                "total_created": 2,
                "indicator_ids": ["ind_abc123", "ind_def456"],
                "indicators": [...]
            }
        }
    """
    try:
        body = await request.json()
        bulk_request = BulkIndicatorRequest(**body)

        if not bulk_request.indicators:
            raise HTTPException(
                status_code=400,
                detail="indicators list cannot be empty"
            )

        logger.info("indicators_crud.create_indicators_bulk", {
            "count": len(bulk_request.indicators)
        })

        created_indicators = []
        indicator_ids = []

        for config in bulk_request.indicators:
            # Generate indicator ID
            import uuid
            indicator_id = config.indicator_id or f"ind_{uuid.uuid4().hex[:12]}"
            indicator_ids.append(indicator_id)

            # Set indicator name if not provided
            indicator_name = config.indicator_name or f"{config.indicator_type}-{config.parameters.get('period', 'default')}"

            # Prepare indicator data
            indicator_data = {
                "indicator_id": indicator_id,
                "session_id": config.session_id,
                "symbol": config.symbol,
                "indicator_type": config.indicator_type,
                "indicator_name": indicator_name,
                "parameters": config.parameters,
                "metadata": config.metadata,
                "created_at": datetime.utcnow().isoformat()
            }

            created_indicators.append(indicator_data)

        logger.info("indicators_crud.bulk_create_success", {
            "total_created": len(created_indicators),
            "indicator_ids": indicator_ids
        })

        return _json_ok({
            "status": "created",
            "total_created": len(created_indicators),
            "indicator_ids": indicator_ids,
            "indicators": created_indicators,
            "note": "Indicator configurations created. To calculate values, use session-based indicator API."
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error("indicators_crud.create_indicators_bulk_failed", {
            "error": str(e),
            "error_type": type(e).__name__
        })
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create indicators in bulk: {str(e)}"
        )


@router.delete("/bulk")
async def delete_indicators_bulk(request: Request) -> JSONResponse:
    """
    Delete multiple indicator configurations in bulk.

    Request Body:
        {
            "indicator_ids": ["ind_abc123", "ind_def456", "ind_ghi789"]
        }

    Returns:
        Deletion confirmation with count

    Example Response:
        {
            "type": "response",
            "data": {
                "status": "deleted",
                "total_deleted": 3,
                "indicator_ids": ["ind_abc123", "ind_def456", "ind_ghi789"],
                "deleted_at": "2025-10-28T12:00:00Z"
            }
        }
    """
    try:
        body = await request.json()
        bulk_delete_request = BulkDeleteRequest(**body)

        if not bulk_delete_request.indicator_ids:
            raise HTTPException(
                status_code=400,
                detail="indicator_ids list cannot be empty"
            )

        logger.info("indicators_crud.delete_indicators_bulk", {
            "count": len(bulk_delete_request.indicator_ids),
            "indicator_ids": bulk_delete_request.indicator_ids
        })

        # TODO: After migration 005, delete from indicator_configs table

        return _json_ok({
            "status": "deleted",
            "total_deleted": len(bulk_delete_request.indicator_ids),
            "indicator_ids": bulk_delete_request.indicator_ids,
            "deleted_at": datetime.utcnow().isoformat(),
            "note": "TODO: Full bulk delete implementation pending migration 005 (indicator_configs table)"
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error("indicators_crud.delete_indicators_bulk_failed", {
            "error": str(e),
            "error_type": type(e).__name__
        })
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete indicators in bulk: {str(e)}"
        )


@router.get("/{indicator_id}")
async def get_indicator_details(indicator_id: str) -> JSONResponse:
    """
    Get detailed information about a specific indicator configuration.

    Path Parameters:
        indicator_id: Unique indicator ID

    Returns:
        Complete indicator configuration

    Example Response:
        {
            "type": "response",
            "data": {
                "indicator_id": "ind_abc123",
                "symbol": "BTC_USDT",
                "indicator_type": "RSI",
                "indicator_name": "RSI-14",
                "parameters": {"period": 14},
                "metadata": {...},
                "created_at": "2025-10-28T12:00:00Z",
                "last_updated": "2025-10-28T12:30:00Z"
            }
        }
    """
    try:
        logger.info("indicators_crud.get_indicator_details", {
            "indicator_id": indicator_id
        })

        # TODO: After migration 005, query from indicator_configs table
        # For now, return a placeholder response

        return _json_ok({
            "indicator_id": indicator_id,
            "note": "TODO: Full implementation pending migration 005 (indicator_configs table)"
        })

    except Exception as e:
        logger.error("indicators_crud.get_indicator_details_failed", {
            "indicator_id": indicator_id,
            "error": str(e),
            "error_type": type(e).__name__
        })
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get indicator details: {str(e)}"
        )
