"""
Backtest API Routes
===================
REST endpoints for backtest session setup and management.
Story: 1b-1-backtest-session-setup

Endpoints:
- GET /api/backtest/data-availability - Check data availability for date range (AC4)
- POST /api/backtest/start - Start a backtest session (AC6)
"""

import asyncio
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from datetime import datetime, date, timezone, timedelta
import uuid

from src.core.logger import get_logger
from src.core.event_bus import EventBus
from src.data_feed.questdb_provider import QuestDBProvider
from src.api.auth_handler import UserSession
from src.trading.backtest_engine import BacktestEngine, run_backtest

# =============================================================================
# Router Setup
# =============================================================================

router = APIRouter(prefix="/api/backtest", tags=["backtest"])

logger = get_logger(__name__)

# Global dependencies (injected during startup)
_questdb_provider: Optional[QuestDBProvider] = None
_event_bus: Optional[EventBus] = None
_get_current_user_dependency = None
_verify_csrf_token_dependency = None

# Track running backtests
_running_backtests: Dict[str, asyncio.Task] = {}


def initialize_backtest_dependencies(
    questdb_provider: QuestDBProvider,
    event_bus: Optional[EventBus] = None,
    get_current_user_dependency=None,
    verify_csrf_token_dependency=None
) -> None:
    """
    Initialize backtest route dependencies.
    Called from unified_server.py during startup.
    """
    global _questdb_provider, _event_bus, _get_current_user_dependency, _verify_csrf_token_dependency
    _questdb_provider = questdb_provider
    _event_bus = event_bus
    _get_current_user_dependency = get_current_user_dependency
    _verify_csrf_token_dependency = verify_csrf_token_dependency

    logger.info("backtest_routes.dependencies_initialized", {
        "questdb_provider_available": _questdb_provider is not None,
        "event_bus_available": _event_bus is not None,
        "auth_dependency_available": _get_current_user_dependency is not None,
    })


def get_questdb_provider() -> QuestDBProvider:
    """Get QuestDB provider (dependency injection)."""
    if _questdb_provider is None:
        raise HTTPException(
            status_code=503,
            detail="QuestDB provider not initialized"
        )
    return _questdb_provider


def get_event_bus() -> Optional[EventBus]:
    """Get EventBus (dependency injection)."""
    return _event_bus


async def _run_backtest_task(session_id: str) -> None:
    """
    Background task to run backtest.

    Args:
        session_id: Backtest session ID to execute
    """
    try:
        logger.info("backtest_routes.task_started", {"session_id": session_id})

        if _questdb_provider is None:
            logger.error("backtest_routes.task_error_no_provider", {"session_id": session_id})
            return

        if _event_bus is None:
            logger.error("backtest_routes.task_error_no_eventbus", {"session_id": session_id})
            return

        engine = BacktestEngine(
            session_id=session_id,
            db_provider=_questdb_provider,
            event_bus=_event_bus
        )

        result = await engine.run()

        logger.info("backtest_routes.task_completed", {
            "session_id": session_id,
            "status": result.status.value,
            "final_pnl": result.final_pnl,
            "total_trades": result.total_trades
        })

    except Exception as e:
        logger.error("backtest_routes.task_failed", {
            "session_id": session_id,
            "error": str(e),
            "error_type": type(e).__name__
        })
    finally:
        # Clean up task reference
        if session_id in _running_backtests:
            del _running_backtests[session_id]


def get_current_user():
    """Get current user dependency wrapper."""
    if _get_current_user_dependency is None:
        async def auth_not_configured() -> UserSession:
            logger.error("backtest_routes.auth_not_configured")
            raise HTTPException(
                status_code=503,
                detail="Authentication not configured"
            )
        return auth_not_configured
    return _get_current_user_dependency


def verify_csrf_token():
    """Get CSRF token verification dependency wrapper."""
    if _verify_csrf_token_dependency is None:
        async def csrf_not_configured() -> str:
            logger.error("backtest_routes.csrf_not_configured")
            raise HTTPException(
                status_code=503,
                detail="CSRF protection not configured"
            )
        return csrf_not_configured
    return _verify_csrf_token_dependency


# =============================================================================
# Request/Response Models
# =============================================================================

class MissingRange(BaseModel):
    """A range of missing data."""
    start: str
    end: str
    gap_hours: float


class DataAvailabilityResponse(BaseModel):
    """Response model for data availability check."""
    available: bool
    symbol: str
    start_date: str
    end_date: str
    coverage_pct: float = Field(ge=0, le=100)
    total_records: int = Field(ge=0)
    expected_records: int = Field(ge=0)
    missing_ranges: List[MissingRange] = []
    data_quality: str = Field(description="good | warning | error")
    quality_issues: List[str] = []


class BacktestConfig(BaseModel):
    """Configuration options for backtest."""
    acceleration_factor: Optional[int] = Field(default=10, ge=1, le=100)
    initial_balance: Optional[float] = Field(default=10000, ge=100)
    stop_loss_percent: Optional[float] = Field(default=5.0, ge=0.1, le=50)
    take_profit_percent: Optional[float] = Field(default=10.0, ge=0.1, le=100)


class BacktestStartRequest(BaseModel):
    """Request model for starting a backtest."""
    strategy_id: str = Field(..., min_length=1, description="Strategy ID to test")
    symbol: str = Field(..., min_length=1, description="Trading symbol (e.g., BTCUSDT)")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")
    session_id: Optional[str] = Field(None, description="Data collection session ID (optional)")
    config: Optional[BacktestConfig] = Field(default_factory=BacktestConfig)


class BacktestStartResponse(BaseModel):
    """Response model for backtest start."""
    session_id: str
    status: str = "started"
    symbol: str
    strategy_id: str
    start_date: str
    end_date: str
    estimated_duration_seconds: Optional[int] = None


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/data-availability", response_model=Dict[str, Any])
async def check_data_availability(
    symbol: str = Query(..., description="Trading symbol (e.g., BTCUSDT)"),
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)")
) -> Dict[str, Any]:
    """
    Check data availability for a given symbol and date range.

    AC4: System validates that historical data exists for the selected range
    AC5: Warning shows if data is incomplete or missing for the range

    Args:
        symbol: Trading symbol (e.g., BTCUSDT)
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format

    Returns:
        Data availability information including coverage percentage and missing ranges
    """
    try:
        # Parse dates
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59, tzinfo=timezone.utc
            )
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid date format. Use YYYY-MM-DD. Error: {str(e)}"
            )

        # Validate date range
        if start_dt >= end_dt:
            raise HTTPException(
                status_code=400,
                detail="End date must be after start date"
            )

        if end_dt > datetime.now(timezone.utc):
            raise HTTPException(
                status_code=400,
                detail="End date cannot be in the future"
            )

        provider = get_questdb_provider()

        # Normalize symbol format (replace _ with nothing for QuestDB query)
        normalized_symbol = symbol.replace("_", "")

        # Query tick_prices table for the given symbol and date range
        # Count records to determine data availability
        count_query = """
            SELECT count() as record_count
            FROM tick_prices
            WHERE symbol = $1
              AND timestamp >= $2
              AND timestamp <= $3
        """

        logger.debug("backtest_routes.check_availability", {
            "symbol": normalized_symbol,
            "start_date": start_date,
            "end_date": end_date,
            "query": count_query
        })

        result = await provider.execute_query(count_query, [
            normalized_symbol,
            start_dt,
            end_dt
        ])

        total_records = 0
        if result and len(result) > 0:
            total_records = result[0].get("record_count", 0)

        # Calculate expected records
        # Assume tick data every 100ms = 36000 records per hour
        # For daily estimate, use a more conservative 1 tick per second = 86400 per day
        days_diff = (end_dt - start_dt).days + 1
        hours_diff = days_diff * 24
        expected_records = hours_diff * 3600  # 1 record per second

        # Calculate coverage percentage
        coverage_pct = 0.0
        if expected_records > 0:
            coverage_pct = min(100.0, (total_records / expected_records) * 100)

        # Determine data quality
        quality_issues: List[str] = []
        missing_ranges: List[MissingRange] = []

        if total_records == 0:
            data_quality = "error"
            quality_issues.append(f"No data found for {symbol} in the selected date range")
        elif coverage_pct < 50:
            data_quality = "warning"
            quality_issues.append(f"Low data coverage ({coverage_pct:.1f}%). Results may be unreliable.")

            # Try to find gaps in data (simplified approach)
            # In production, you'd want a more sophisticated gap detection
            gap_query = """
                SELECT
                    MIN(timestamp) as first_record,
                    MAX(timestamp) as last_record
                FROM tick_prices
                WHERE symbol = $1
                  AND timestamp >= $2
                  AND timestamp <= $3
            """
            gap_result = await provider.execute_query(gap_query, [
                normalized_symbol,
                start_dt,
                end_dt
            ])

            if gap_result and len(gap_result) > 0:
                first_record = gap_result[0].get("first_record")
                last_record = gap_result[0].get("last_record")

                if first_record and (first_record - start_dt).total_seconds() > 3600:
                    gap_hours = (first_record - start_dt).total_seconds() / 3600
                    missing_ranges.append(MissingRange(
                        start=start_dt.isoformat(),
                        end=first_record.isoformat(),
                        gap_hours=round(gap_hours, 1)
                    ))
                    quality_issues.append(f"Data starts {gap_hours:.1f} hours after requested start")

                if last_record and (end_dt - last_record).total_seconds() > 3600:
                    gap_hours = (end_dt - last_record).total_seconds() / 3600
                    missing_ranges.append(MissingRange(
                        start=last_record.isoformat(),
                        end=end_dt.isoformat(),
                        gap_hours=round(gap_hours, 1)
                    ))
                    quality_issues.append(f"Data ends {gap_hours:.1f} hours before requested end")

        elif coverage_pct < 90:
            data_quality = "warning"
            quality_issues.append(f"Partial data coverage ({coverage_pct:.1f}%). Some gaps may exist.")
        else:
            data_quality = "good"

        response = DataAvailabilityResponse(
            available=total_records > 0,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            coverage_pct=round(coverage_pct, 2),
            total_records=total_records,
            expected_records=expected_records,
            missing_ranges=missing_ranges,
            data_quality=data_quality,
            quality_issues=quality_issues
        )

        logger.info("backtest_routes.data_availability_checked", {
            "symbol": symbol,
            "start_date": start_date,
            "end_date": end_date,
            "total_records": total_records,
            "coverage_pct": coverage_pct,
            "data_quality": data_quality
        })

        return {
            "status": "success",
            "data": response.model_dump()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("backtest_routes.check_availability_error", {
            "symbol": symbol,
            "start_date": start_date,
            "end_date": end_date,
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start", response_model=Dict[str, Any])
async def start_backtest(
    request: BacktestStartRequest,
    current_user: UserSession = Depends(get_current_user),
    csrf_token: str = Depends(verify_csrf_token)
) -> Dict[str, Any]:
    """
    Start a backtest session with the given configuration.

    AC6: "Start Backtest" button starts the session and redirects to dashboard

    Args:
        request: Backtest configuration including strategy, symbol, and date range

    Returns:
        Session information including session_id for tracking
    """
    try:
        # Validate dates
        try:
            start_dt = datetime.strptime(request.start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            end_dt = datetime.strptime(request.end_date, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59, tzinfo=timezone.utc
            )
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid date format. Use YYYY-MM-DD. Error: {str(e)}"
            )

        if start_dt >= end_dt:
            raise HTTPException(
                status_code=400,
                detail="End date must be after start date"
            )

        # Generate session ID
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        short_uuid = str(uuid.uuid4())[:8]
        session_id = f"bt_{timestamp}_{short_uuid}"

        # Calculate estimated duration based on date range and acceleration factor
        days_diff = (end_dt - start_dt).days + 1
        acceleration = request.config.acceleration_factor if request.config else 10
        estimated_seconds = int((days_diff * 86400) / acceleration)

        provider = get_questdb_provider()

        # Verify strategy exists (query strategies table)
        # For now, we'll assume the strategy_id is valid
        # In production, you'd want to validate against the strategies table

        # Record backtest session in QuestDB
        # Create backtest_sessions table record
        try:
            insert_query = """
                INSERT INTO backtest_sessions (
                    session_id, strategy_id, symbol, start_date, end_date,
                    status, acceleration_factor, initial_balance,
                    created_at, created_by, timestamp
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11
                )
            """
            now = datetime.now(timezone.utc)
            await provider.execute(
                insert_query,
                session_id,
                request.strategy_id,
                request.symbol,
                start_dt,
                end_dt,
                "started",
                request.config.acceleration_factor if request.config else 10,
                request.config.initial_balance if request.config else 10000,
                now,
                current_user.username if current_user else "anonymous",
                now
            )
        except Exception as db_error:
            # Table might not exist yet, log warning and continue
            logger.warning("backtest_routes.session_insert_failed", {
                "session_id": session_id,
                "error": str(db_error),
                "note": "backtest_sessions table may not exist yet"
            })

        # Trigger backtest execution as background task
        # Story 1b-2: BacktestEngine integration
        if _event_bus is not None:
            task = asyncio.create_task(_run_backtest_task(session_id))
            _running_backtests[session_id] = task

            logger.info("backtest_routes.engine_triggered", {
                "session_id": session_id,
                "task_id": id(task)
            })
        else:
            logger.warning("backtest_routes.engine_not_triggered", {
                "session_id": session_id,
                "reason": "EventBus not available"
            })

        response = BacktestStartResponse(
            session_id=session_id,
            status="started",
            symbol=request.symbol,
            strategy_id=request.strategy_id,
            start_date=request.start_date,
            end_date=request.end_date,
            estimated_duration_seconds=estimated_seconds
        )

        logger.info("backtest_routes.backtest_started", {
            "session_id": session_id,
            "strategy_id": request.strategy_id,
            "symbol": request.symbol,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "acceleration_factor": request.config.acceleration_factor if request.config else 10,
            "user": current_user.username if current_user else "anonymous"
        })

        return {
            "status": "success",
            "data": response.model_dump()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("backtest_routes.start_backtest_error", {
            "strategy_id": request.strategy_id,
            "symbol": request.symbol,
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions", response_model=Dict[str, Any])
async def list_backtest_sessions(
    limit: int = Query(50, ge=1, le=200, description="Maximum sessions to return"),
    status: Optional[str] = Query(None, description="Filter by status")
) -> Dict[str, Any]:
    """
    List backtest sessions with optional filters.

    Args:
        limit: Maximum number of sessions to return
        status: Optional status filter

    Returns:
        List of backtest sessions
    """
    try:
        provider = get_questdb_provider()

        query = """
            SELECT session_id, strategy_id, symbol, start_date, end_date,
                   status, acceleration_factor, initial_balance,
                   created_at, created_by
            FROM backtest_sessions
            WHERE 1=1
        """
        params = []

        if status:
            params.append(status)
            query += f" AND status = ${len(params)}"

        query += f" ORDER BY created_at DESC LIMIT {limit}"

        result = await provider.execute_query(query, params if params else None)

        sessions = []
        for row in result:
            sessions.append({
                "session_id": row.get("session_id"),
                "strategy_id": row.get("strategy_id"),
                "symbol": row.get("symbol"),
                "start_date": row.get("start_date").isoformat() if row.get("start_date") else None,
                "end_date": row.get("end_date").isoformat() if row.get("end_date") else None,
                "status": row.get("status"),
                "acceleration_factor": row.get("acceleration_factor"),
                "initial_balance": row.get("initial_balance"),
                "created_at": row.get("created_at").isoformat() if row.get("created_at") else None,
                "created_by": row.get("created_by")
            })

        return {
            "status": "success",
            "data": {
                "sessions": sessions,
                "count": len(sessions)
            }
        }

    except Exception as e:
        logger.error("backtest_routes.list_sessions_error", {
            "error": str(e)
        })
        # Return empty list on error (table might not exist)
        return {
            "status": "success",
            "data": {
                "sessions": [],
                "count": 0
            }
        }


@router.get("/sessions/{session_id}", response_model=Dict[str, Any])
async def get_backtest_session(
    session_id: str
) -> Dict[str, Any]:
    """
    Get details of a specific backtest session.

    Args:
        session_id: Backtest session ID

    Returns:
        Session details including status and results
    """
    try:
        provider = get_questdb_provider()

        query = """
            SELECT session_id, strategy_id, symbol, start_date, end_date,
                   status, acceleration_factor, initial_balance,
                   created_at, created_by
            FROM backtest_sessions
            WHERE session_id = $1
            ORDER BY created_at DESC
            LIMIT 1
        """

        result = await provider.execute_query(query, [session_id])

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Backtest session not found: {session_id}"
            )

        row = result[0]

        return {
            "status": "success",
            "data": {
                "session_id": row.get("session_id"),
                "strategy_id": row.get("strategy_id"),
                "symbol": row.get("symbol"),
                "start_date": row.get("start_date").isoformat() if row.get("start_date") else None,
                "end_date": row.get("end_date").isoformat() if row.get("end_date") else None,
                "status": row.get("status"),
                "acceleration_factor": row.get("acceleration_factor"),
                "initial_balance": row.get("initial_balance"),
                "created_at": row.get("created_at").isoformat() if row.get("created_at") else None,
                "created_by": row.get("created_by")
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("backtest_routes.get_session_error", {
            "session_id": session_id,
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/stop", response_model=Dict[str, Any])
async def stop_backtest(
    session_id: str
) -> Dict[str, Any]:
    """
    Stop a running backtest session.

    Args:
        session_id: Backtest session ID to stop

    Returns:
        Status of stop operation
    """
    try:
        # Check if backtest is running
        if session_id not in _running_backtests:
            raise HTTPException(
                status_code=404,
                detail=f"No running backtest found with session_id: {session_id}"
            )

        task = _running_backtests[session_id]

        # Cancel the task
        if not task.done():
            task.cancel()
            logger.info("backtest_routes.stop_requested", {
                "session_id": session_id,
                "task_cancelled": True
            })

        # Update session status in database
        try:
            provider = get_questdb_provider()
            query = """
                UPDATE backtest_sessions
                SET status = $2, completed_at = $3
                WHERE session_id = $1
            """
            await provider.execute(query, session_id, "stopped", datetime.now(timezone.utc))
        except Exception as db_error:
            logger.warning("backtest_routes.stop_status_update_failed", {
                "session_id": session_id,
                "error": str(db_error)
            })

        return {
            "status": "success",
            "data": {
                "session_id": session_id,
                "stopped": True,
                "message": "Backtest stop requested"
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("backtest_routes.stop_error", {
            "session_id": session_id,
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active", response_model=Dict[str, Any])
async def list_active_backtests() -> Dict[str, Any]:
    """
    List all currently running backtest sessions.

    Returns:
        List of active backtest session IDs
    """
    try:
        active_sessions = []

        for session_id, task in list(_running_backtests.items()):
            if not task.done():
                active_sessions.append({
                    "session_id": session_id,
                    "running": True
                })
            else:
                # Clean up completed tasks
                del _running_backtests[session_id]

        return {
            "status": "success",
            "data": {
                "active_sessions": active_sessions,
                "count": len(active_sessions)
            }
        }

    except Exception as e:
        logger.error("backtest_routes.list_active_error", {
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail=str(e))
