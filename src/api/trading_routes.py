"""
Live Trading API Routes - Agent 6
===================================
REST endpoints for live trading operations: positions, orders, performance.

Endpoints:
- GET /api/trading/positions - Query live positions
- POST /api/trading/positions/{position_id}/close - Close a position
- GET /api/trading/orders - Query live orders
- POST /api/trading/orders/{order_id}/cancel - Cancel an order
- GET /api/trading/performance/{session_id} - Calculate session performance
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, Path, Depends
from pydantic import BaseModel, Field
from datetime import datetime
import json

from src.core.logger import get_logger
from src.data_feed.questdb_provider import QuestDBProvider
from src.api.auth_handler import UserSession

# Create router
router = APIRouter(prefix="/api/trading", tags=["live-trading"])

# Module-level logger
logger = get_logger(__name__)

# Global database provider (injected during startup)
_questdb_provider: Optional[QuestDBProvider] = None
_live_order_manager = None  # Will be injected
_get_current_user_dependency = None  # Will be injected from unified_server


def initialize_trading_dependencies(
    questdb_provider: QuestDBProvider,
    live_order_manager=None,
    get_current_user_dependency=None
) -> None:
    """
    Initialize trading route dependencies.

    Called from unified_server.py during startup.

    Args:
        questdb_provider: QuestDB provider for database queries
        live_order_manager: LiveOrderManager service (optional, for order operations)
        get_current_user_dependency: FastAPI dependency for authentication
    """
    global _questdb_provider, _live_order_manager, _get_current_user_dependency
    _questdb_provider = questdb_provider
    _live_order_manager = live_order_manager
    _get_current_user_dependency = get_current_user_dependency

    logger.info("trading_routes.dependencies_initialized", {
        "questdb_provider_available": _questdb_provider is not None,
        "live_order_manager_available": _live_order_manager is not None,
        "auth_dependency_available": _get_current_user_dependency is not None
    })


def get_questdb_provider() -> QuestDBProvider:
    """Get QuestDB provider (dependency injection)."""
    if _questdb_provider is None:
        raise HTTPException(
            status_code=503,
            detail="QuestDB provider not initialized"
        )
    return _questdb_provider


def get_live_order_manager():
    """Get live order manager (dependency injection)."""
    if _live_order_manager is None:
        raise HTTPException(
            status_code=503,
            detail="Live order manager not initialized"
        )
    return _live_order_manager


def get_current_user():
    """
    Get current user dependency (wrapper for unified_server's implementation).

    This function returns the actual dependency function that should be used with Depends().
    """
    if _get_current_user_dependency is None:
        # Fallback for development/testing - return a dummy dependency
        async def no_auth_dummy() -> UserSession:
            logger.warning("trading_routes.no_auth_configured",
                          {"message": "Authentication not configured - using dummy session"})
            from datetime import datetime
            return UserSession(
                user_id="dev_user",
                username="developer",
                permissions=["admin_system"],
                last_activity=datetime.now()
            )
        return no_auth_dummy
    return _get_current_user_dependency


# ========================================
# Response Models
# ========================================

class PositionResponse(BaseModel):
    """Live position response model."""
    session_id: str
    symbol: str
    side: str
    quantity: float
    entry_price: float
    current_price: float
    liquidation_price: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    margin: float
    leverage: float
    margin_ratio: float
    opened_at: str
    updated_at: str
    status: str


class OrderResponse(BaseModel):
    """Live order response model."""
    session_id: str
    order_id: str
    exchange_order_id: Optional[str]
    symbol: str
    side: str
    order_type: str
    quantity: float
    requested_price: float
    filled_quantity: float
    average_fill_price: Optional[float]
    status: str
    error_message: Optional[str]
    slippage: Optional[float]
    commission: Optional[float]
    created_at: str
    updated_at: str
    filled_at: Optional[str]


class PerformanceResponse(BaseModel):
    """Session performance metrics response."""
    session_id: str
    total_pnl: float
    total_pnl_pct: float
    win_rate: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    profit_factor: float
    max_drawdown: float
    sharpe_ratio: Optional[float]
    start_time: str
    end_time: Optional[str]
    duration_seconds: Optional[int]


class ClosePositionRequest(BaseModel):
    """Request to close a position."""
    reason: str = Field(default="USER_REQUESTED", description="Reason for closing")


class ClosePositionResponse(BaseModel):
    """Response after closing a position."""
    success: bool
    message: str
    order_id: Optional[str] = None
    closed_pnl: Optional[float] = None


class CancelOrderResponse(BaseModel):
    """Response after canceling an order."""
    success: bool
    message: str
    order_id: str
    cancelled_at: str


# ========================================
# Endpoints
# ========================================

@router.get("/positions", response_model=Dict[str, Any])
async def get_positions(
    session_id: Optional[str] = Query(None, description="Filter by session ID"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    status: str = Query("OPEN", description="Filter by status (OPEN, CLOSED, LIQUIDATED)")
) -> Dict[str, Any]:
    """
    Get live positions from QuestDB.

    Query live_positions table with optional filters.
    Default: Returns only OPEN positions (current active positions).

    Args:
        session_id: Optional session ID filter
        symbol: Optional symbol filter (e.g., BTC_USDT)
        status: Position status (default: OPEN)

    Returns:
        List of positions matching the filters
    """
    try:
        provider = get_questdb_provider()

        # Build query
        query = "SELECT * FROM live_positions WHERE status = $1"
        params = [status]

        if session_id:
            query += " AND session_id = $2"
            params.append(session_id)

        if symbol:
            param_idx = len(params) + 1
            query += f" AND symbol = ${param_idx}"
            params.append(symbol)

        query += " ORDER BY updated_at DESC"

        logger.debug("trading_api.query_positions", {
            "session_id": session_id,
            "symbol": symbol,
            "status": status,
            "query": query
        })

        # Execute query
        positions = await provider.fetch(query, *params)

        # Convert to response models
        position_list = []
        for pos in positions:
            position_list.append({
                "session_id": pos.get("session_id"),
                "symbol": pos.get("symbol"),
                "side": pos.get("side"),
                "quantity": pos.get("quantity", 0.0),
                "entry_price": pos.get("entry_price", 0.0),
                "current_price": pos.get("current_price", 0.0),
                "liquidation_price": pos.get("liquidation_price", 0.0),
                "unrealized_pnl": pos.get("unrealized_pnl", 0.0),
                "unrealized_pnl_pct": pos.get("unrealized_pnl_pct", 0.0),
                "margin": pos.get("margin", 0.0),
                "leverage": pos.get("leverage", 1.0),
                "margin_ratio": pos.get("margin_ratio", 0.0),
                "opened_at": pos.get("opened_at").isoformat() if pos.get("opened_at") else None,
                "updated_at": pos.get("updated_at").isoformat() if pos.get("updated_at") else None,
                "status": pos.get("status", "UNKNOWN")
            })

        logger.info("trading_api.positions_fetched", {
            "count": len(position_list),
            "session_id": session_id,
            "status": status
        })

        return {
            "success": True,
            "positions": position_list,
            "count": len(position_list)
        }

    except Exception as e:
        logger.error("trading_api.get_positions_error", {
            "error": str(e),
            "session_id": session_id,
            "symbol": symbol
        })
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/positions/{position_id}/close", response_model=ClosePositionResponse)
async def close_position(
    position_id: str = Path(..., description="Position ID to close (format: session_id:symbol)"),
    request: ClosePositionRequest = ClosePositionRequest(),
    current_user: UserSession = Depends(get_current_user)
) -> ClosePositionResponse:
    """
    Close a live position by creating a reverse order.

    Position ID format: "session_id:symbol" (e.g., "live_20251107_abc123:BTC_USDT")

    This endpoint:
    1. Fetches the position from live_positions table
    2. Creates a reverse order (LONG → SELL, SHORT → BUY)
    3. Submits the order via LiveOrderManager
    4. Returns order ID and estimated P&L

    Args:
        position_id: Position identifier (session_id:symbol)
        request: Close position request with reason

    Returns:
        Close position response with order ID and P&L
    """
    try:
        live_order_manager = get_live_order_manager()
        provider = get_questdb_provider()

        # Parse position_id (format: session_id:symbol)
        parts = position_id.split(":")
        if len(parts) != 2:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid position_id format. Expected 'session_id:symbol', got '{position_id}'"
            )

        session_id, symbol = parts

        # Fetch position
        query = """
            SELECT * FROM live_positions
            WHERE session_id = $1 AND symbol = $2 AND status = 'OPEN'
            ORDER BY updated_at DESC LIMIT 1
        """
        positions = await provider.fetch(query, session_id, symbol)

        if not positions:
            raise HTTPException(
                status_code=404,
                detail=f"Position not found: {position_id} (or already closed)"
            )

        position = positions[0]

        # Create reverse order
        # LONG position → SELL to close
        # SHORT position → BUY to close
        reverse_side = "SELL" if position["side"] == "LONG" else "BUY"

        # Call LiveOrderManager to close position
        # (This will create a MARKET order to close the position)
        order_result = await live_order_manager.close_position(
            session_id=session_id,
            symbol=symbol,
            quantity=position["quantity"],
            side=reverse_side,
            reason=request.reason
        )

        logger.info("trading_api.position_closed", {
            "position_id": position_id,
            "symbol": symbol,
            "side": position["side"],
            "quantity": position["quantity"],
            "order_id": order_result.get("order_id"),
            "unrealized_pnl": position["unrealized_pnl"]
        })

        return ClosePositionResponse(
            success=True,
            message=f"Position {position_id} close order submitted successfully",
            order_id=order_result.get("order_id"),
            closed_pnl=position["unrealized_pnl"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("trading_api.close_position_error", {
            "position_id": position_id,
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders", response_model=Dict[str, Any])
async def get_orders(
    session_id: Optional[str] = Query(None, description="Filter by session ID"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    status: Optional[str] = Query(None, description="Filter by status (PENDING, FILLED, CANCELLED, etc.)"),
    limit: int = Query(50, ge=1, le=200, description="Max orders to return")
) -> Dict[str, Any]:
    """
    Get live orders from QuestDB.

    Query live_orders table with optional filters.
    Orders are sorted by created_at DESC (most recent first).

    Args:
        session_id: Optional session ID filter
        symbol: Optional symbol filter
        status: Optional status filter
        limit: Maximum orders to return (default: 50)

    Returns:
        List of orders matching the filters
    """
    try:
        provider = get_questdb_provider()

        # Build query
        query = "SELECT * FROM live_orders WHERE 1=1"
        params = []

        if session_id:
            params.append(session_id)
            query += f" AND session_id = ${len(params)}"

        if symbol:
            params.append(symbol)
            query += f" AND symbol = ${len(params)}"

        if status:
            params.append(status)
            query += f" AND status = ${len(params)}"

        query += f" ORDER BY created_at DESC LIMIT {limit}"

        logger.debug("trading_api.query_orders", {
            "session_id": session_id,
            "symbol": symbol,
            "status": status,
            "limit": limit,
            "query": query
        })

        # Execute query
        orders = await provider.fetch(query, *params)

        # Convert to response models
        order_list = []
        for order in orders:
            order_list.append({
                "session_id": order.get("session_id"),
                "order_id": order.get("order_id"),
                "exchange_order_id": order.get("exchange_order_id"),
                "symbol": order.get("symbol"),
                "side": order.get("side"),
                "order_type": order.get("order_type"),
                "quantity": order.get("quantity", 0.0),
                "requested_price": order.get("requested_price", 0.0),
                "filled_quantity": order.get("filled_quantity", 0.0),
                "average_fill_price": order.get("average_fill_price"),
                "status": order.get("status"),
                "error_message": order.get("error_message"),
                "slippage": order.get("slippage"),
                "commission": order.get("commission"),
                "created_at": order.get("created_at").isoformat() if order.get("created_at") else None,
                "updated_at": order.get("updated_at").isoformat() if order.get("updated_at") else None,
                "filled_at": order.get("filled_at").isoformat() if order.get("filled_at") else None
            })

        logger.info("trading_api.orders_fetched", {
            "count": len(order_list),
            "session_id": session_id,
            "status": status
        })

        return {
            "success": True,
            "orders": order_list,
            "count": len(order_list)
        }

    except Exception as e:
        logger.error("trading_api.get_orders_error", {
            "error": str(e),
            "session_id": session_id,
            "symbol": symbol
        })
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/orders/{order_id}/cancel", response_model=CancelOrderResponse)
async def cancel_order(
    order_id: str = Path(..., description="Order ID to cancel"),
    current_user: UserSession = Depends(get_current_user)
) -> CancelOrderResponse:
    """
    Cancel a pending or partially filled order.

    This endpoint:
    1. Validates order exists and is cancellable (status: PENDING or PARTIALLY_FILLED)
    2. Calls LiveOrderManager.cancel_order()
    3. Updates order status to CANCELLED in live_orders table
    4. Returns confirmation

    Args:
        order_id: Order ID to cancel

    Returns:
        Cancel confirmation with timestamp
    """
    try:
        live_order_manager = get_live_order_manager()
        provider = get_questdb_provider()

        # Fetch order to validate
        query = "SELECT * FROM live_orders WHERE order_id = $1 LIMIT 1"
        orders = await provider.fetch(query, order_id)

        if not orders:
            raise HTTPException(
                status_code=404,
                detail=f"Order not found: {order_id}"
            )

        order = orders[0]

        # Check if order is cancellable
        if order["status"] not in ["PENDING", "SUBMITTED", "PARTIALLY_FILLED"]:
            raise HTTPException(
                status_code=400,
                detail=f"Order cannot be cancelled. Current status: {order['status']}"
            )

        # Call LiveOrderManager to cancel
        cancel_result = await live_order_manager.cancel_order(order_id)

        if not cancel_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to cancel order: {cancel_result.get('error', 'Unknown error')}"
            )

        logger.info("trading_api.order_cancelled", {
            "order_id": order_id,
            "symbol": order["symbol"],
            "side": order["side"],
            "quantity": order["quantity"]
        })

        return CancelOrderResponse(
            success=True,
            message=f"Order {order_id} cancelled successfully",
            order_id=order_id,
            cancelled_at=datetime.utcnow().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("trading_api.cancel_order_error", {
            "order_id": order_id,
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/{session_id}", response_model=PerformanceResponse)
async def get_performance(
    session_id: str = Path(..., description="Session ID to calculate performance for")
) -> PerformanceResponse:
    """
    Calculate session performance metrics from live_orders and live_positions.

    Metrics calculated:
    - Total P&L (realized + unrealized)
    - Win rate (winning trades / total trades)
    - Profit factor (gross profit / gross loss)
    - Max drawdown (peak-to-trough decline)
    - Sharpe ratio (risk-adjusted returns)
    - Total trades, winning trades, losing trades

    Args:
        session_id: Session ID to analyze

    Returns:
        Performance metrics for the session
    """
    try:
        provider = get_questdb_provider()

        # 1. Fetch all filled orders for the session
        orders_query = """
            SELECT order_id, symbol, side, quantity, average_fill_price, filled_at, slippage, commission
            FROM live_orders
            WHERE session_id = $1 AND status = 'FILLED'
            ORDER BY filled_at ASC
        """
        orders = await provider.fetch(orders_query, session_id)

        # 2. Fetch all positions (to get unrealized P&L)
        positions_query = """
            SELECT symbol, unrealized_pnl, status, opened_at, closed_at
            FROM live_positions
            WHERE session_id = $1
            ORDER BY opened_at ASC
        """
        positions = await provider.fetch(positions_query, session_id)

        # 3. Calculate metrics
        if not orders and not positions:
            raise HTTPException(
                status_code=404,
                detail=f"No trading activity found for session: {session_id}"
            )

        # Initialize metrics
        total_realized_pnl = 0.0
        total_unrealized_pnl = 0.0
        winning_trades = 0
        losing_trades = 0
        total_trades = 0
        gross_profit = 0.0
        gross_loss = 0.0

        # Calculate from closed positions
        for pos in positions:
            if pos.get("status") == "CLOSED":
                pnl = pos.get("unrealized_pnl", 0.0)
                total_realized_pnl += pnl
                total_trades += 1
                if pnl > 0:
                    winning_trades += 1
                    gross_profit += pnl
                else:
                    losing_trades += 1
                    gross_loss += abs(pnl)

        # Add unrealized P&L from open positions
        for pos in positions:
            if pos.get("status") == "OPEN":
                total_unrealized_pnl += pos.get("unrealized_pnl", 0.0)

        # Total P&L
        total_pnl = total_realized_pnl + total_unrealized_pnl

        # Win rate
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0

        # Profit factor
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')

        # Max drawdown (simplified: would need equity curve for accurate calculation)
        max_drawdown = 0.0  # Placeholder (requires equity curve)

        # Sharpe ratio (placeholder: requires return series)
        sharpe_ratio = None

        # Session timing
        start_time = None
        end_time = None
        if positions:
            start_time = min([p.get("opened_at") for p in positions if p.get("opened_at")])
            closed_positions = [p for p in positions if p.get("closed_at")]
            if closed_positions:
                end_time = max([p.get("closed_at") for p in closed_positions])

        duration_seconds = None
        if start_time and end_time:
            duration_seconds = int((end_time - start_time).total_seconds())

        # Total P&L percentage (assuming initial balance, would need from session config)
        initial_balance = 10000.0  # Placeholder (should fetch from session config)
        total_pnl_pct = (total_pnl / initial_balance * 100) if initial_balance > 0 else 0.0

        logger.info("trading_api.performance_calculated", {
            "session_id": session_id,
            "total_pnl": total_pnl,
            "win_rate": win_rate,
            "total_trades": total_trades
        })

        return PerformanceResponse(
            session_id=session_id,
            total_pnl=total_pnl,
            total_pnl_pct=total_pnl_pct,
            win_rate=win_rate,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            profit_factor=profit_factor if profit_factor != float('inf') else 0.0,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            start_time=start_time.isoformat() if start_time else None,
            end_time=end_time.isoformat() if end_time else None,
            duration_seconds=duration_seconds
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("trading_api.get_performance_error", {
            "session_id": session_id,
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail=str(e))
