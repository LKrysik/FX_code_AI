"""
Dashboard API Routes
====================

REST endpoints for Unified Trading Dashboard.
Optimized for TARGET_STATE_TRADING_INTERFACE.md requirements.

Endpoints:
- GET /api/dashboard/summary - Complete dashboard data (single request)
- GET /api/dashboard/watchlist - Real-time watchlist data
- GET /api/indicators/current - Current indicator values

Performance Requirements:
- All endpoints MUST return within <100ms
- Uses cache tables for pre-aggregated data
- Leverages QuestDB LATEST BY for O(1) lookups
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from datetime import datetime, timezone

from src.core.logger import get_logger
from src.data_feed.questdb_provider import QuestDBProvider
from src.domain.services.streaming_indicator_engine import StreamingIndicatorEngine
from src.api.dependencies import verify_csrf_token
from src.api.response_envelope import ensure_envelope

logger = get_logger(__name__)
router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

# Dependency injection - will be set during app startup
_questdb_provider: Optional[QuestDBProvider] = None
_streaming_engine: Optional[StreamingIndicatorEngine] = None
_get_current_user: Optional[Any] = None


def initialize_dashboard_dependencies(
    questdb_provider: QuestDBProvider,
    streaming_engine: StreamingIndicatorEngine,
    get_current_user_dependency: Any = None
):
    """
    Initialize dependencies for dashboard routes.
    Called from unified_server.py during startup.

    Args:
        questdb_provider: QuestDB database provider
        streaming_engine: Streaming indicator engine
        get_current_user_dependency: FastAPI dependency for user authentication
    """
    global _questdb_provider, _streaming_engine, _get_current_user
    _questdb_provider = questdb_provider
    _streaming_engine = streaming_engine
    _get_current_user = get_current_user_dependency

    logger.info("dashboard_routes.dependencies_initialized")


def _ensure_dependencies():
    """Verify dependencies are initialized."""
    if _questdb_provider is None or _streaming_engine is None:
        raise RuntimeError(
            "Dashboard dependencies not initialized. "
            "Call initialize_dashboard_dependencies() during app startup."
        )
    return _questdb_provider, _streaming_engine


def _get_current_user_dep():
    """Helper to get current user dependency (set during initialization)."""
    if _get_current_user is None:
        # If auth not configured, allow unauthenticated access (backwards compatibility)
        return None
    return _get_current_user


@router.get("/summary")
async def get_dashboard_summary(
    session_id: str = Query(..., description="Session ID")
    # NOTE: Authentication temporarily disabled for backwards compatibility
    # TODO: Enable after frontend implements auth: current_user: Any = Depends(_get_current_user_dep)
) -> JSONResponse:
    """
    Get complete dashboard data in SINGLE request.

    Combines data from:
    - Active positions
    - Recent signals (last 10)
    - Current indicator values
    - Risk metrics
    - Symbol watchlist data

    This endpoint is optimized for dashboard initial load.
    Frontend should call this ONCE on mount, then use WebSocket for updates.

    Performance Target: <100ms

    Returns:
        {
            "session_id": "session_123",
            "global_pnl": 400.50,
            "symbols": [
                {
                    "symbol": "BTC_USDT",
                    "price": 50250,
                    "change_pct": 5.2,
                    "position": {...},
                    "pnl": 150,
                    "indicators": [...]
                },
                ...
            ],
            "recent_signals": [...],
            "risk_metrics": {
                "budget_utilization_pct": 75,
                "avg_margin_ratio": 35,
                "max_drawdown_pct": -4.5,
                "active_alerts": []
            },
            "last_updated": "2025-11-15T13:05:23Z"
        }
    """
    import time
    start_time = time.time()

    questdb, streaming_engine = _ensure_dependencies()

    try:
        # Read from dashboard_summary_cache (fast aggregated data)
        summary_cache = await _get_summary_from_cache(questdb, session_id)

        # Get watchlist data (symbols with prices + positions)
        symbols_data = await _get_watchlist_data(questdb, session_id)

        # Get recent signals
        recent_signals = await _get_recent_signals(questdb, session_id, limit=10)

        # Build response
        response = {
            "session_id": session_id,
            "global_pnl": summary_cache.get('global_pnl', 0.0),
            "total_positions": summary_cache.get('total_positions', 0),
            "total_signals": summary_cache.get('total_signals', 0),
            "symbols": symbols_data,
            "recent_signals": recent_signals,
            "risk_metrics": {
                "budget_utilization_pct": summary_cache.get('budget_utilization_pct', 0.0),
                "avg_margin_ratio": summary_cache.get('avg_margin_ratio', 0.0),
                "max_drawdown_pct": summary_cache.get('max_drawdown_pct', 0.0),
                "active_alerts": []  # TODO: Implement alert system
            },
            "last_updated": datetime.now(timezone.utc).isoformat()
        }

        elapsed_ms = (time.time() - start_time) * 1000

        logger.info("dashboard_routes.summary_success", {
            "session_id": session_id,
            "elapsed_ms": elapsed_ms,
            "symbols_count": len(symbols_data)
        })

        return JSONResponse(content=ensure_envelope(response))

    except Exception as e:
        logger.error("dashboard_routes.summary_failed", {
            "session_id": session_id,
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard summary: {str(e)}")


@router.get("/watchlist")
async def get_watchlist_data(
    session_id: str = Query(..., description="Session ID"),
    symbols: str = Query(..., description="Comma-separated list of symbols (e.g., BTC_USDT,ETH_USDT)")
) -> JSONResponse:
    """
    Get real-time data for symbol watchlist.

    Optimized for frequent polling (every 1-2 seconds).
    Reads from watchlist_cache table (updated every 1s by DashboardCacheService).

    Performance Target: <50ms

    Returns:
        {
            "session_id": "session_123",
            "symbols": [
                {
                    "symbol": "BTC_USDT",
                    "latest_price": 50250,
                    "price_change_pct": 5.2,
                    "volume_24h": 1000000,
                    "position": {
                        "side": "LONG",
                        "pnl": 150,
                        "margin_ratio": 45
                    }
                },
                ...
            ],
            "last_updated": "2025-11-15T13:05:23Z"
        }
    """
    import time
    start_time = time.time()

    questdb, _ = _ensure_dependencies()

    try:
        symbol_list = [s.strip() for s in symbols.split(',')]

        # Query watchlist_cache table
        # ✅ FIX (BUG-003-3): Use correct QuestDB LATEST ON syntax
        query = """
            SELECT symbol, latest_price, price_change_pct, volume_24h,
                   position_side, position_pnl, position_margin_ratio
            FROM watchlist_cache
            WHERE session_id = $1 AND symbol = ANY($2)
            LATEST ON last_updated PARTITION BY symbol
        """

        async with questdb.pg_pool.acquire() as conn:
            rows = await conn.fetch(query, session_id, symbol_list)

        # Build response
        symbols_data = []
        for row in rows:
            symbol_data = {
                "symbol": row['symbol'],
                "latest_price": float(row['latest_price']) if row['latest_price'] else 0.0,
                "price_change_pct": float(row['price_change_pct']) if row['price_change_pct'] else 0.0,
                "volume_24h": float(row['volume_24h']) if row['volume_24h'] else 0.0
            }

            # Add position data if exists
            if row['position_side']:
                symbol_data['position'] = {
                    "side": row['position_side'],
                    "pnl": float(row['position_pnl']) if row['position_pnl'] else 0.0,
                    "margin_ratio": float(row['position_margin_ratio']) if row['position_margin_ratio'] else 0.0
                }

            symbols_data.append(symbol_data)

        elapsed_ms = (time.time() - start_time) * 1000

        logger.debug("dashboard_routes.watchlist_success", {
            "session_id": session_id,
            "symbols_count": len(symbols_data),
            "elapsed_ms": elapsed_ms
        })

        response = {
            "session_id": session_id,
            "symbols": symbols_data,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }

        return JSONResponse(content=ensure_envelope(response))

    except Exception as e:
        logger.error("dashboard_routes.watchlist_failed", {
            "session_id": session_id,
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail=f"Failed to get watchlist data: {str(e)}")


# Helper functions

async def _get_summary_from_cache(questdb: QuestDBProvider, session_id: str) -> Dict[str, Any]:
    """Read aggregated metrics from dashboard_summary_cache."""
    try:
        # ✅ FIX (BUG-003-3): Use correct QuestDB LATEST ON syntax
        query = """
            SELECT global_pnl, total_positions, total_signals,
                   budget_utilization_pct, avg_margin_ratio, max_drawdown_pct
            FROM dashboard_summary_cache
            WHERE session_id = $1
            LATEST ON last_updated PARTITION BY session_id
        """

        async with questdb.pg_pool.acquire() as conn:
            row = await conn.fetchrow(query, session_id)

        if not row:
            # No cache yet - return defaults
            return {
                'global_pnl': 0.0,
                'total_positions': 0,
                'total_signals': 0,
                'budget_utilization_pct': 0.0,
                'avg_margin_ratio': 0.0,
                'max_drawdown_pct': 0.0
            }

        return {
            'global_pnl': float(row['global_pnl']) if row['global_pnl'] else 0.0,
            'total_positions': int(row['total_positions']) if row['total_positions'] else 0,
            'total_signals': int(row['total_signals']) if row['total_signals'] else 0,
            'budget_utilization_pct': float(row['budget_utilization_pct']) if row['budget_utilization_pct'] else 0.0,
            'avg_margin_ratio': float(row['avg_margin_ratio']) if row['avg_margin_ratio'] else 0.0,
            'max_drawdown_pct': float(row['max_drawdown_pct']) if row['max_drawdown_pct'] else 0.0
        }

    except Exception as e:
        logger.error("dashboard_routes.get_summary_cache_failed", {
            "session_id": session_id,
            "error": str(e)
        })
        # Return defaults on error
        return {
            'global_pnl': 0.0,
            'total_positions': 0,
            'total_signals': 0,
            'budget_utilization_pct': 0.0,
            'avg_margin_ratio': 0.0,
            'max_drawdown_pct': 0.0
        }


async def _get_watchlist_data(questdb: QuestDBProvider, session_id: str) -> List[Dict[str, Any]]:
    """Get watchlist data for all symbols in session."""
    try:
        # ✅ FIX (BUG-003-3): Use correct QuestDB LATEST ON syntax
        query = """
            SELECT symbol, latest_price, price_change_pct, volume_24h,
                   position_side, position_pnl, position_margin_ratio
            FROM watchlist_cache
            WHERE session_id = $1
            LATEST ON last_updated PARTITION BY symbol
            LIMIT 20
        """

        async with questdb.pg_pool.acquire() as conn:
            rows = await conn.fetch(query, session_id)

        symbols_data = []
        for row in rows:
            symbol_data = {
                "symbol": row['symbol'],
                "price": float(row['latest_price']) if row['latest_price'] else 0.0,
                "change_pct": float(row['price_change_pct']) if row['price_change_pct'] else 0.0,
                "volume_24h": float(row['volume_24h']) if row['volume_24h'] else 0.0
            }

            # Add position if exists
            if row['position_side']:
                symbol_data['position'] = {
                    "side": row['position_side'],
                    "pnl": float(row['position_pnl']) if row['position_pnl'] else 0.0,
                    "margin_ratio": float(row['position_margin_ratio']) if row['position_margin_ratio'] else 0.0
                }

            symbols_data.append(symbol_data)

        return symbols_data

    except Exception as e:
        logger.error("dashboard_routes.get_watchlist_failed", {
            "session_id": session_id,
            "error": str(e)
        })
        return []


async def _get_recent_signals(questdb: QuestDBProvider, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent signals for session."""
    try:
        # Correct columns: strategy_signals table has action (not side) and triggered (not execution_status)
        query = """
            SELECT signal_id, symbol, signal_type, action, confidence,
                   triggered, timestamp
            FROM strategy_signals
            WHERE session_id = $1
            ORDER BY timestamp DESC
            LIMIT $2
        """

        async with questdb.pg_pool.acquire() as conn:
            rows = await conn.fetch(query, session_id, limit)

        signals = []
        for row in rows:
            signals.append({
                "signal_id": row['signal_id'],
                "symbol": row['symbol'],
                "signal_type": row['signal_type'],
                "action": row['action'],  # BUY/SELL action from signal
                "confidence": float(row['confidence']) if row['confidence'] else 0.0,
                "triggered": row['triggered'],  # Whether signal was triggered
                "timestamp": row['timestamp'].isoformat() if row['timestamp'] else None
            })

        return signals

    except Exception as e:
        logger.error("dashboard_routes.get_signals_failed", {
            "session_id": session_id,
            "error": str(e)
        })
        return []


@router.get("/equity-curve")
async def get_equity_curve(
    session_id: str = Query(..., description="Session ID"),
    limit: int = Query(100, description="Max data points to return")
) -> JSONResponse:
    """
    Get equity curve data for EquityCurveChart component.

    Reads from paper_trading_performance table (time-series of balance snapshots).

    Returns data in format expected by EquityCurveChart:
    - timestamp
    - current_balance
    - total_pnl
    - total_return_pct

    Performance Target: <100ms
    """
    import time
    start_time = time.time()

    questdb, _ = _ensure_dependencies()

    try:
        # Get performance snapshots from paper_trading_performance
        query = """
            SELECT
                timestamp,
                current_balance,
                total_pnl,
                total_return_pct,
                max_drawdown,
                current_drawdown
            FROM paper_trading_performance
            WHERE session_id = $1
            ORDER BY timestamp ASC
            LIMIT $2
        """

        async with questdb.pg_pool.acquire() as conn:
            rows = await conn.fetch(query, session_id, limit)

        # Get initial balance from session
        session_query = """
            SELECT initial_balance
            FROM paper_trading_sessions
            WHERE session_id = $1
            LIMIT 1
        """

        async with questdb.pg_pool.acquire() as conn:
            session_row = await conn.fetchrow(session_query, session_id)

        initial_balance = 10000.0  # Default
        if session_row and session_row['initial_balance']:
            initial_balance = float(session_row['initial_balance'])

        # Build equity curve data
        equity_curve = []
        for row in rows:
            equity_curve.append({
                "timestamp": row['timestamp'].isoformat() if row['timestamp'] else None,
                "current_balance": float(row['current_balance']) if row['current_balance'] else initial_balance,
                "total_pnl": float(row['total_pnl']) if row['total_pnl'] else 0.0,
                "total_return_pct": float(row['total_return_pct']) if row['total_return_pct'] else 0.0,
                "max_drawdown": float(row['max_drawdown']) if row['max_drawdown'] else 0.0,
                "current_drawdown": float(row['current_drawdown']) if row['current_drawdown'] else 0.0
            })

        elapsed_ms = (time.time() - start_time) * 1000

        logger.info("dashboard_routes.equity_curve_success", {
            "session_id": session_id,
            "data_points": len(equity_curve),
            "elapsed_ms": elapsed_ms
        })

        response = {
            "session_id": session_id,
            "initial_balance": initial_balance,
            "equity_curve": equity_curve,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }

        return JSONResponse(content=ensure_envelope(response))

    except Exception as e:
        logger.error("dashboard_routes.equity_curve_failed", {
            "session_id": session_id,
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail=f"Failed to get equity curve: {str(e)}")
