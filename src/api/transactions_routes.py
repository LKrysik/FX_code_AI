"""
Transaction History API Routes
================================

REST endpoints for viewing order/transaction history.

Endpoints:
- GET /api/transactions/history - Get transaction history with filtering

Performance Requirements:
- All endpoints MUST return within <100ms
- Uses QuestDB indexes for fast lookups

Related Tables:
- orders (migration 019)
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
import json

from src.core.logger import get_logger
from src.data_feed.questdb_provider import QuestDBProvider
from src.api.response_envelope import ensure_envelope

logger = get_logger(__name__)
router = APIRouter(prefix="/api/transactions", tags=["transactions"])

# Dependency injection - will be set during app startup
_questdb_provider: Optional[QuestDBProvider] = None


def initialize_transactions_dependencies(questdb_provider: QuestDBProvider):
    """
    Initialize dependencies for transactions routes.
    Called from unified_server.py during startup.

    Args:
        questdb_provider: QuestDB database provider
    """
    global _questdb_provider
    _questdb_provider = questdb_provider
    logger.info("transactions_routes.dependencies_initialized")


def _ensure_dependencies():
    """Verify dependencies are initialized."""
    if _questdb_provider is None:
        raise RuntimeError(
            "Transactions routes dependencies not initialized. "
            "Call initialize_transactions_dependencies() during app startup."
        )
    return _questdb_provider


@router.get("/history")
async def get_transaction_history(
    session_id: str = Query(..., description="Session ID"),
    symbol: Optional[str] = Query(None, description="Filter by symbol (e.g., BTC_USDT)"),
    status: Optional[str] = Query(None, description="Filter by status (NEW, FILLED, PARTIALLY_FILLED, CANCELLED)"),
    side: Optional[str] = Query(None, description="Filter by side (BUY, SELL)"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of transactions to return")
) -> JSONResponse:
    """
    Get transaction (order) history with optional filtering.

    Performance Target: <100ms

    Query Parameters:
    - session_id: Required - Session identifier
    - symbol: Optional - Filter by trading pair
    - status: Optional - Filter by order status (NEW, FILLED, PARTIALLY_FILLED, CANCELLED)
    - side: Optional - Filter by side (BUY, SELL)
    - limit: Optional - Max results (default 100, max 500)

    Returns:
        {
            "session_id": "session_123",
            "filters": {
                "symbol": "BTC_USDT",
                "status": "FILLED",
                "side": "BUY"
            },
            "transactions": [
                {
                    "order_id": "order_123",
                    "strategy_id": "strategy_1",
                    "symbol": "BTC_USDT",
                    "side": "BUY",
                    "order_type": "MARKET",
                    "timestamp": "2025-11-16T12:00:00Z",
                    "quantity": 0.1,
                    "price": 50000,
                    "filled_quantity": 0.1,
                    "filled_price": 50010,
                    "status": "FILLED",
                    "commission": 5.0,
                    "slippage": 10,
                    "metadata": {...}
                }
            ],
            "total_count": 42,
            "summary": {
                "total_filled": 35,
                "total_cancelled": 5,
                "total_failed": 2,
                "total_commission": 175.5
            }
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
                order_id, strategy_id, symbol, session_id, side, order_type,
                timestamp, quantity, price, filled_quantity, filled_price, status, commission, metadata
            FROM orders
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

        if status:
            query_parts.append(f"AND status = ${param_idx}")
            params.append(status)
            param_idx += 1

        if side:
            query_parts.append(f"AND side = ${param_idx}")
            params.append(side)
            param_idx += 1

        # Add ordering and limit
        query_parts.append(f"ORDER BY timestamp DESC LIMIT ${param_idx}")
        params.append(limit)

        query = "\n".join(query_parts)

        # Execute query
        async with questdb.pg_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        # Parse rows and calculate summary
        transactions = []
        summary = {
            "total_filled": 0,
            "total_cancelled": 0,
            "total_failed": 0,
            "total_commission": 0.0
        }

        for row in rows:
            # Calculate slippage
            slippage = None
            if row['filled_price'] and row['price']:
                slippage = float(row['filled_price']) - float(row['price'])

            transaction_data = {
                "order_id": row['order_id'],
                "strategy_id": row['strategy_id'],
                "symbol": row['symbol'],
                "session_id": row['session_id'],
                "side": row['side'],
                "order_type": row['order_type'],
                "timestamp": row['timestamp'].isoformat() if row['timestamp'] else None,
                "quantity": float(row['quantity']) if row['quantity'] else 0.0,
                "price": float(row['price']) if row['price'] else None,
                "filled_quantity": float(row['filled_quantity']) if row['filled_quantity'] else 0.0,
                "filled_price": float(row['filled_price']) if row['filled_price'] else None,
                "status": row['status'],
                "commission": float(row['commission']) if row['commission'] else 0.0,
                "slippage": slippage,
            }

            # Parse metadata
            try:
                transaction_data['metadata'] = json.loads(row['metadata']) if row['metadata'] else {}
            except (json.JSONDecodeError, TypeError):
                transaction_data['metadata'] = {}

            transactions.append(transaction_data)

            # Update summary
            if row['status'] in ('FILLED', 'PARTIALLY_FILLED'):
                summary['total_filled'] += 1
            elif row['status'] == 'CANCELLED':
                summary['total_cancelled'] += 1
            elif row['status'] in ('FAILED', 'REJECTED'):
                summary['total_failed'] += 1

            if row['commission']:
                summary['total_commission'] += float(row['commission'])

        elapsed_ms = (time.time() - start_time) * 1000

        logger.info("transactions_routes.history_success", {
            "session_id": session_id,
            "filters": {"symbol": symbol, "status": status, "side": side},
            "total_count": len(transactions),
            "elapsed_ms": elapsed_ms
        })

        response = {
            "session_id": session_id,
            "filters": {
                "symbol": symbol,
                "status": status,
                "side": side
            },
            "transactions": transactions,
            "total_count": len(transactions),
            "summary": summary
        }

        return JSONResponse(content=ensure_envelope(response))

    except Exception as e:
        logger.error("transactions_routes.history_failed", {
            "session_id": session_id,
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail=f"Failed to get transaction history: {str(e)}")
