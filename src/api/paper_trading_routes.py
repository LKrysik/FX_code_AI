"""
Paper Trading API Routes - TIER 1.2
====================================
REST endpoints for paper trading session management, performance tracking, and analysis.

Endpoints:
- POST /api/paper-trading/sessions - Create new paper trading session
- GET /api/paper-trading/sessions - List sessions
- GET /api/paper-trading/sessions/{session_id} - Get session details
- GET /api/paper-trading/sessions/{session_id}/performance - Get performance metrics
- GET /api/paper-trading/sessions/{session_id}/orders - Get order history
- GET /api/paper-trading/sessions/{session_id}/positions - Get position snapshots
- POST /api/paper-trading/sessions/{session_id}/stop - Stop session
- DELETE /api/paper-trading/sessions/{session_id} - Delete session
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.core.logger import get_logger
from src.domain.services.paper_trading_persistence import PaperTradingPersistenceService

# Create router
router = APIRouter(prefix="/api/paper-trading", tags=["paper-trading"])

# Module-level logger
logger = get_logger(__name__)

# Global persistence service (injected during startup)
_persistence_service: Optional[PaperTradingPersistenceService] = None


def initialize_paper_trading_dependencies(
    persistence_service: PaperTradingPersistenceService
) -> None:
    """
    Initialize paper trading route dependencies.

    Called from unified_server.py during startup.

    Args:
        persistence_service: Paper trading persistence service
    """
    global _persistence_service
    _persistence_service = persistence_service

    logger.info("paper_trading_routes.dependencies_initialized")


def get_persistence_service() -> PaperTradingPersistenceService:
    """Get persistence service (dependency injection)."""
    if _persistence_service is None:
        raise HTTPException(
            status_code=503,
            detail="Paper trading service not initialized"
        )
    return _persistence_service


# ========================================
# Request/Response Models
# ========================================

class CreateSessionRequest(BaseModel):
    """Request to create new paper trading session."""
    strategy_id: str = Field(..., description="Strategy ID to test")
    strategy_name: str = Field(..., description="Strategy name")
    symbols: List[str] = Field(..., description="List of symbols to trade")
    direction: str = Field(default="BOTH", description="LONG, SHORT, or BOTH")
    leverage: float = Field(default=1.0, ge=1.0, le=10.0, description="Leverage multiplier")
    initial_balance: float = Field(default=10000.0, description="Starting balance in USDT")
    notes: Optional[str] = Field(default="", description="Optional session notes")


class SessionResponse(BaseModel):
    """Paper trading session response."""
    session_id: str
    strategy_id: str
    strategy_name: str
    symbols: str
    direction: str
    leverage: float
    initial_balance: float
    final_balance: Optional[float] = None
    total_pnl: Optional[float] = None
    total_return_pct: Optional[float] = None
    total_trades: Optional[int] = None
    winning_trades: Optional[int] = None
    losing_trades: Optional[int] = None
    win_rate: Optional[float] = None
    profit_factor: Optional[float] = None
    max_drawdown: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    status: str
    start_time: str
    end_time: Optional[str] = None
    duration_seconds: Optional[int] = None
    notes: Optional[str] = None


# ========================================
# Endpoints
# ========================================

@router.post("/sessions", response_model=Dict[str, Any])
async def create_session(request: CreateSessionRequest) -> Dict[str, Any]:
    """
    Create new paper trading session.

    Args:
        request: Session creation parameters

    Returns:
        Created session data with session_id
    """
    try:
        persistence = get_persistence_service()

        # Generate session ID
        import uuid
        from datetime import datetime
        session_id = f"paper_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        # Create session
        session_data = {
            "session_id": session_id,
            "strategy_id": request.strategy_id,
            "strategy_name": request.strategy_name,
            "symbols": request.symbols,
            "direction": request.direction,
            "leverage": request.leverage,
            "initial_balance": request.initial_balance,
            "created_by": "user",  # TODO: Get from auth context
            "notes": request.notes or ""
        }

        await persistence.create_session(session_data)

        logger.info("paper_trading_api.session_created", {
            "session_id": session_id,
            "strategy_name": request.strategy_name
        })

        return {
            "success": True,
            "session_id": session_id,
            "message": "Paper trading session created successfully"
        }

    except Exception as e:
        logger.error("paper_trading_api.create_session_error", {
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions", response_model=Dict[str, Any])
async def list_sessions(
    strategy_id: Optional[str] = Query(None, description="Filter by strategy ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=200, description="Max sessions to return")
) -> Dict[str, Any]:
    """
    List paper trading sessions with optional filters.

    Args:
        strategy_id: Optional strategy ID filter
        status: Optional status filter (RUNNING, COMPLETED, STOPPED, ERROR)
        limit: Maximum sessions to return

    Returns:
        List of sessions
    """
    try:
        persistence = get_persistence_service()

        sessions = await persistence.list_sessions(
            strategy_id=strategy_id,
            status=status,
            limit=limit
        )

        logger.debug("paper_trading_api.sessions_listed", {
            "count": len(sessions),
            "strategy_id": strategy_id,
            "status": status
        })

        return {
            "success": True,
            "sessions": sessions,
            "count": len(sessions)
        }

    except Exception as e:
        logger.error("paper_trading_api.list_sessions_error", {
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}", response_model=Dict[str, Any])
async def get_session(session_id: str) -> Dict[str, Any]:
    """
    Get paper trading session details.

    Args:
        session_id: Session ID

    Returns:
        Session details
    """
    try:
        persistence = get_persistence_service()

        session = await persistence.get_session(session_id)

        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found"
            )

        return {
            "success": True,
            "session": session
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("paper_trading_api.get_session_error", {
            "session_id": session_id,
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/performance", response_model=Dict[str, Any])
async def get_session_performance(
    session_id: str,
    interval: Optional[str] = Query("1m", description="Time interval (1m, 5m, 1h)")
) -> Dict[str, Any]:
    """
    Get performance metrics over time for session.

    Args:
        session_id: Session ID
        interval: Time interval for aggregation

    Returns:
        Performance metrics time series
    """
    try:
        persistence = get_persistence_service()

        # Get session to verify it exists
        session = await persistence.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found"
            )

        # Get performance snapshots
        performance = await persistence.get_session_performance(session_id)

        return {
            "success": True,
            "session_id": session_id,
            "performance": performance,
            "count": len(performance)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("paper_trading_api.get_performance_error", {
            "session_id": session_id,
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/orders", response_model=Dict[str, Any])
async def get_session_orders(
    session_id: str,
    limit: int = Query(100, ge=1, le=1000, description="Max orders to return")
) -> Dict[str, Any]:
    """
    Get order history for session.

    Args:
        session_id: Session ID
        limit: Maximum orders to return

    Returns:
        List of orders
    """
    try:
        persistence = get_persistence_service()

        # Get session to verify it exists
        session = await persistence.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found"
            )

        # Get orders
        orders = await persistence.get_session_orders(session_id, limit=limit)

        return {
            "success": True,
            "session_id": session_id,
            "orders": orders,
            "count": len(orders)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("paper_trading_api.get_orders_error", {
            "session_id": session_id,
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/stop", response_model=Dict[str, Any])
async def stop_session(session_id: str) -> Dict[str, Any]:
    """
    Stop running paper trading session.

    Args:
        session_id: Session ID

    Returns:
        Success confirmation
    """
    try:
        persistence = get_persistence_service()

        # Get session to verify it exists
        session = await persistence.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found"
            )

        if session["status"] != "RUNNING":
            raise HTTPException(
                status_code=400,
                detail=f"Session is not running (status: {session['status']})"
            )

        # Update status to STOPPED
        await persistence.update_session_status(session_id, "STOPPED")

        logger.info("paper_trading_api.session_stopped", {
            "session_id": session_id
        })

        return {
            "success": True,
            "session_id": session_id,
            "message": "Session stopped successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("paper_trading_api.stop_session_error", {
            "session_id": session_id,
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/{session_id}", response_model=Dict[str, Any])
async def delete_session(session_id: str) -> Dict[str, Any]:
    """
    Delete paper trading session (soft delete - updates status).

    Args:
        session_id: Session ID

    Returns:
        Success confirmation
    """
    try:
        persistence = get_persistence_service()

        # Get session to verify it exists
        session = await persistence.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found"
            )

        # Soft delete: update status to DELETED
        # (Keep data for analysis, don't actually delete from DB)
        await persistence.update_session_status(session_id, "DELETED")

        logger.info("paper_trading_api.session_deleted", {
            "session_id": session_id
        })

        return {
            "success": True,
            "session_id": session_id,
            "message": "Session deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("paper_trading_api.delete_session_error", {
            "session_id": session_id,
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=Dict[str, Any])
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for paper trading service.

    Returns:
        Service health status
    """
    try:
        persistence = get_persistence_service()

        # Test database connection by querying sessions
        sessions = await persistence.list_sessions(limit=1)

        return {
            "success": True,
            "service": "paper-trading",
            "status": "healthy",
            "database": "connected"
        }

    except Exception as e:
        logger.error("paper_trading_api.health_check_error", {
            "error": str(e)
        })
        return {
            "success": False,
            "service": "paper-trading",
            "status": "unhealthy",
            "error": str(e)
        }
