"""
Signal History API Routes
==========================

REST endpoints for viewing trading signal history and details.

Endpoints:
- GET /api/signals/history - Get signal history with filtering
- GET /api/signals/{signal_id} - Get signal detail with linked order/position

Performance Requirements:
- All endpoints MUST return within <100ms
- Uses QuestDB indexes for fast lookups

Related Tables:
- strategy_signals (migration 019)
- orders (migration 019)
- positions (migration 019)
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Path
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
import json

from src.core.logger import get_logger
from src.data_feed.questdb_provider import QuestDBProvider
from src.api.response_envelope import ensure_envelope

logger = get_logger(__name__)
router = APIRouter(prefix="/api/signals", tags=["signals"])

# Dependency injection - will be set during app startup
_questdb_provider: Optional[QuestDBProvider] = None


def initialize_signals_dependencies(questdb_provider: QuestDBProvider):
    """
    Initialize dependencies for signals routes.
    Called from unified_server.py during startup.

    Args:
        questdb_provider: QuestDB database provider
    """
    global _questdb_provider
    _questdb_provider = questdb_provider
    logger.info("signals_routes.dependencies_initialized")


def _ensure_dependencies():
    """Verify dependencies are initialized."""
    if _questdb_provider is None:
        raise RuntimeError(
            "Signals routes dependencies not initialized. "
            "Call initialize_signals_dependencies() during app startup."
        )
    return _questdb_provider


@router.get("/history")
async def get_signal_history(
    session_id: str = Query(..., description="Session ID"),
    symbol: Optional[str] = Query(None, description="Filter by symbol (e.g., BTC_USDT)"),
    signal_type: Optional[str] = Query(None, description="Filter by signal type (S1, Z1, ZE1, E1)"),
    triggered: Optional[bool] = Query(None, description="Filter by triggered status"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of signals to return")
) -> JSONResponse:
    """
    Get signal history with optional filtering.

    Performance Target: <100ms

    Query Parameters:
    - session_id: Required - Session identifier
    - symbol: Optional - Filter by trading pair
    - signal_type: Optional - Filter by signal type (S1, Z1, ZE1, E1, O1, EMERGENCY)
    - triggered: Optional - Filter by triggered status (true/false)
    - limit: Optional - Max results (default 100, max 500)

    Returns:
        {
            "session_id": "session_123",
            "filters": {
                "symbol": "BTC_USDT",
                "signal_type": "S1",
                "triggered": true
            },
            "signals": [
                {
                    "signal_id": "sig_123",
                    "strategy_id": "strategy_1",
                    "symbol": "BTC_USDT",
                    "signal_type": "S1",
                    "timestamp": "2025-11-16T12:00:00Z",
                    "triggered": true,
                    "action": "BUY",
                    "conditions_met": {...},
                    "indicator_values": {...},
                    "metadata": {...}
                }
            ],
            "total_count": 42
        }
    """
    import time
    start_time = time.time()

    questdb = _ensure_dependencies()

    try:
        # Build dynamic query with filters
        query_parts = [
            """
            SELECT
                signal_id, strategy_id, symbol, session_id, signal_type,
                timestamp, triggered, action, confidence, conditions_met, indicator_values, metadata
            FROM strategy_signals
            WHERE session_id = $1
            """
        ]
        params = [session_id]
        param_idx = 2

        # Add optional filters
        if symbol:
            query_parts.append(f"AND symbol = ${param_idx}")
            params.append(symbol)
            param_idx += 1

        if signal_type:
            query_parts.append(f"AND signal_type = ${param_idx}")
            params.append(signal_type)
            param_idx += 1

        if triggered is not None:
            query_parts.append(f"AND triggered = ${param_idx}")
            params.append(triggered)
            param_idx += 1

        # Add ordering and limit
        query_parts.append(f"ORDER BY timestamp DESC LIMIT ${param_idx}")
        params.append(limit)

        query = "\n".join(query_parts)

        # Execute query
        async with questdb.pg_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        # Parse JSON fields and build response
        signals = []
        for row in rows:
            signal_data = {
                "signal_id": row['signal_id'],
                "strategy_id": row['strategy_id'],
                "symbol": row['symbol'],
                "session_id": row['session_id'],
                "signal_type": row['signal_type'],
                "timestamp": row['timestamp'].isoformat() if row['timestamp'] else None,
                "triggered": row['triggered'],
                "action": row['action'],
                "confidence": float(row['confidence']) if row['confidence'] is not None else None,
            }

            # Parse JSON fields safely
            try:
                signal_data['conditions_met'] = json.loads(row['conditions_met']) if row['conditions_met'] else {}
            except (json.JSONDecodeError, TypeError):
                signal_data['conditions_met'] = {}

            try:
                signal_data['indicator_values'] = json.loads(row['indicator_values']) if row['indicator_values'] else {}
            except (json.JSONDecodeError, TypeError):
                signal_data['indicator_values'] = {}

            try:
                signal_data['metadata'] = json.loads(row['metadata']) if row['metadata'] else {}
            except (json.JSONDecodeError, TypeError):
                signal_data['metadata'] = {}

            signals.append(signal_data)

        elapsed_ms = (time.time() - start_time) * 1000

        logger.info("signals_routes.history_success", {
            "session_id": session_id,
            "filters": {"symbol": symbol, "signal_type": signal_type, "triggered": triggered},
            "total_count": len(signals),
            "elapsed_ms": elapsed_ms
        })

        response = {
            "session_id": session_id,
            "filters": {
                "symbol": symbol,
                "signal_type": signal_type,
                "triggered": triggered
            },
            "signals": signals,
            "total_count": len(signals)
        }

        return JSONResponse(content=ensure_envelope(response))

    except Exception as e:
        logger.error("signals_routes.history_failed", {
            "session_id": session_id,
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail=f"Failed to get signal history: {str(e)}")


@router.get("/{signal_id}")
async def get_signal_detail(
    signal_id: str = Path(..., description="Signal ID")
) -> JSONResponse:
    """
    Get detailed information about a single signal, including linked order and position.

    Performance Target: <100ms

    Returns:
        {
            "signal": {
                "signal_id": "sig_123",
                "strategy_id": "strategy_1",
                "symbol": "BTC_USDT",
                "signal_type": "S1",
                "timestamp": "2025-11-16T12:00:00Z",
                "triggered": true,
                "action": "BUY",
                "conditions_met": {...},
                "indicator_values": {...},
                "metadata": {...}
            },
            "order": {
                "order_id": "order_456",
                "status": "FILLED",
                "quantity": 0.1,
                "price": 50000,
                "filled_price": 50010,
                "commission": 5.0
            },
            "position": {
                "position_id": "pos_789",
                "side": "LONG",
                "entry_price": 50010,
                "current_price": 50250,
                "unrealized_pnl": 24.0,
                "status": "OPEN"
            }
        }
    """
    import time
    start_time = time.time()

    questdb = _ensure_dependencies()

    try:
        # Get signal details
        signal_query = """
            SELECT
                signal_id, strategy_id, symbol, session_id, signal_type,
                timestamp, triggered, action, confidence, conditions_met, indicator_values, metadata
            FROM strategy_signals
            WHERE signal_id = $1
            LIMIT 1
        """

        async with questdb.pg_pool.acquire() as conn:
            signal_row = await conn.fetchrow(signal_query, signal_id)

        if not signal_row:
            raise HTTPException(status_code=404, detail=f"Signal not found: {signal_id}")

        # Parse signal data
        signal_data = {
            "signal_id": signal_row['signal_id'],
            "strategy_id": signal_row['strategy_id'],
            "symbol": signal_row['symbol'],
            "session_id": signal_row['session_id'],
            "signal_type": signal_row['signal_type'],
            "timestamp": signal_row['timestamp'].isoformat() if signal_row['timestamp'] else None,
            "triggered": signal_row['triggered'],
            "action": signal_row['action'],
        }

        # Parse JSON fields
        try:
            signal_data['conditions_met'] = json.loads(signal_row['conditions_met']) if signal_row['conditions_met'] else {}
        except (json.JSONDecodeError, TypeError):
            signal_data['conditions_met'] = {}

        try:
            signal_data['indicator_values'] = json.loads(signal_row['indicator_values']) if signal_row['indicator_values'] else {}
        except (json.JSONDecodeError, TypeError):
            signal_data['indicator_values'] = {}

        try:
            signal_data['metadata'] = json.loads(signal_row['metadata']) if signal_row['metadata'] else {}
        except (json.JSONDecodeError, TypeError):
            signal_data['metadata'] = {}

        # Try to find linked order (order metadata might contain signal_id)
        order_query = """
            SELECT
                order_id, strategy_id, symbol, session_id, side, order_type,
                timestamp, quantity, price, filled_quantity, filled_price, status, commission, metadata
            FROM orders
            WHERE session_id = $1 AND symbol = $2 AND strategy_id = $3
            AND timestamp >= dateadd('m', -5, $4)
            AND timestamp <= dateadd('m', 5, $4)
            ORDER BY timestamp ASC
            LIMIT 1
        """

        async with questdb.pg_pool.acquire() as conn:
            order_row = await conn.fetchrow(
                order_query,
                signal_row['session_id'],
                signal_row['symbol'],
                signal_row['strategy_id'],
                signal_row['timestamp']
            )

        order_data = None
        if order_row:
            order_data = {
                "order_id": order_row['order_id'],
                "strategy_id": order_row['strategy_id'],
                "symbol": order_row['symbol'],
                "side": order_row['side'],
                "order_type": order_row['order_type'],
                "timestamp": order_row['timestamp'].isoformat() if order_row['timestamp'] else None,
                "quantity": float(order_row['quantity']) if order_row['quantity'] else 0.0,
                "price": float(order_row['price']) if order_row['price'] else None,
                "filled_quantity": float(order_row['filled_quantity']) if order_row['filled_quantity'] else 0.0,
                "filled_price": float(order_row['filled_price']) if order_row['filled_price'] else None,
                "status": order_row['status'],
                "commission": float(order_row['commission']) if order_row['commission'] else 0.0,
            }

            # Try to find linked position
            position_query = """
                SELECT
                    position_id, strategy_id, symbol, side, timestamp,
                    quantity, entry_price, current_price, unrealized_pnl, realized_pnl,
                    stop_loss, take_profit, status, metadata
                FROM positions
                WHERE session_id = $1 AND symbol = $2 AND strategy_id = $3
                ORDER BY timestamp DESC
                LIMIT 1
            """

            async with questdb.pg_pool.acquire() as conn:
                position_row = await conn.fetchrow(
                    position_query,
                    signal_row['session_id'],
                    signal_row['symbol'],
                    signal_row['strategy_id']
                )

            position_data = None
            if position_row:
                position_data = {
                    "position_id": position_row['position_id'],
                    "strategy_id": position_row['strategy_id'],
                    "symbol": position_row['symbol'],
                    "side": position_row['side'],
                    "timestamp": position_row['timestamp'].isoformat() if position_row['timestamp'] else None,
                    "quantity": float(position_row['quantity']) if position_row['quantity'] else 0.0,
                    "entry_price": float(position_row['entry_price']) if position_row['entry_price'] else 0.0,
                    "current_price": float(position_row['current_price']) if position_row['current_price'] else 0.0,
                    "unrealized_pnl": float(position_row['unrealized_pnl']) if position_row['unrealized_pnl'] else 0.0,
                    "realized_pnl": float(position_row['realized_pnl']) if position_row['realized_pnl'] else 0.0,
                    "stop_loss": float(position_row['stop_loss']) if position_row['stop_loss'] else None,
                    "take_profit": float(position_row['take_profit']) if position_row['take_profit'] else None,
                    "status": position_row['status'],
                }

        elapsed_ms = (time.time() - start_time) * 1000

        logger.info("signals_routes.detail_success", {
            "signal_id": signal_id,
            "has_order": order_data is not None,
            "has_position": position_data is not None if order_data else False,
            "elapsed_ms": elapsed_ms
        })

        response = {
            "signal": signal_data,
            "order": order_data,
            "position": position_data if order_data else None
        }

        return JSONResponse(content=ensure_envelope(response))

    except HTTPException:
        raise
    except Exception as e:
        logger.error("signals_routes.detail_failed", {
            "signal_id": signal_id,
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail=f"Failed to get signal detail: {str(e)}")
