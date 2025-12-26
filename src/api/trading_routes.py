"""
Live Trading API Routes - Agent 6
===================================
REST endpoints for live trading operations: positions, orders, performance.

Endpoints:
- GET /api/trading/positions - Query live positions
- POST /api/trading/positions/{position_id}/close - Close a position
- PATCH /api/trading/positions/{position_id}/sl-tp - Modify SL/TP (PM-03)
- GET /api/trading/orders - Query live orders
- POST /api/trading/orders/{order_id}/cancel - Cancel an order
- GET /api/trading/performance/{session_id} - Calculate session performance
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, Path, Depends
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import json
import asyncio
import time

from src.core.logger import get_logger
from src.data_feed.questdb_provider import QuestDBProvider
from src.api.auth_handler import UserSession


# =============================================================================
# SEC-0-1: Position Lock Manager - Prevents race conditions on position operations
# =============================================================================
class PositionLockManager:
    """
    Manages locks for position operations to prevent race conditions.

    SEC-P0 Fix: Prevents double-close bugs, incorrect P&L calculations,
    and orphaned orders by ensuring only one operation per position at a time.
    """

    def __init__(self, lock_timeout: float = 30.0):
        self._locks: Dict[str, asyncio.Lock] = {}
        self._lock_times: Dict[str, float] = {}
        self._lock_owners: Dict[str, str] = {}  # position_id -> operation type
        self._manager_lock = asyncio.Lock()  # Protects the locks dict itself
        self._timeout = lock_timeout
        self._logger = get_logger(__name__)

    async def acquire(self, position_id: str, operation: str = "unknown") -> bool:
        """
        Acquire a lock for a position operation.

        Args:
            position_id: The position ID to lock
            operation: Description of the operation (for logging)

        Returns:
            True if lock acquired, False if timeout or already locked
        """
        async with self._manager_lock:
            if position_id not in self._locks:
                self._locks[position_id] = asyncio.Lock()

        lock = self._locks[position_id]

        # Check if already locked by another operation
        if lock.locked():
            existing_op = self._lock_owners.get(position_id, "unknown")
            self._logger.warning("position_lock.already_locked", {
                "position_id": position_id,
                "requested_operation": operation,
                "existing_operation": existing_op,
                "lock_time": self._lock_times.get(position_id)
            })
            return False

        try:
            await asyncio.wait_for(lock.acquire(), timeout=self._timeout)
            self._lock_times[position_id] = time.time()
            self._lock_owners[position_id] = operation
            self._logger.info("position_lock.acquired", {
                "position_id": position_id,
                "operation": operation
            })
            return True
        except asyncio.TimeoutError:
            self._logger.error("position_lock.timeout", {
                "position_id": position_id,
                "operation": operation,
                "timeout": self._timeout
            })
            return False

    def release(self, position_id: str) -> None:
        """Release a lock for a position."""
        if position_id in self._locks and self._locks[position_id].locked():
            operation = self._lock_owners.pop(position_id, "unknown")
            lock_duration = time.time() - self._lock_times.pop(position_id, time.time())
            self._locks[position_id].release()
            self._logger.info("position_lock.released", {
                "position_id": position_id,
                "operation": operation,
                "duration_seconds": round(lock_duration, 3)
            })

    def is_locked(self, position_id: str) -> bool:
        """Check if a position is currently locked."""
        return position_id in self._locks and self._locks[position_id].locked()

    def get_lock_info(self, position_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a position lock."""
        if not self.is_locked(position_id):
            return None
        return {
            "position_id": position_id,
            "operation": self._lock_owners.get(position_id),
            "locked_at": self._lock_times.get(position_id),
            "locked_for_seconds": time.time() - self._lock_times.get(position_id, time.time())
        }


# Global position lock manager instance
_position_lock_manager = PositionLockManager()

# Create router
router = APIRouter(prefix="/api/trading", tags=["live-trading"])

# Module-level logger
logger = get_logger(__name__)

# Global database provider (injected during startup)
_questdb_provider: Optional[QuestDBProvider] = None
_live_order_manager = None  # Will be injected
_get_current_user_dependency = None  # Will be injected from unified_server
_verify_csrf_token_dependency = None  # Will be injected from unified_server


def initialize_trading_dependencies(
    questdb_provider: QuestDBProvider,
    live_order_manager=None,
    get_current_user_dependency=None,
    verify_csrf_token_dependency=None
) -> None:
    """
    Initialize trading route dependencies.

    Called from unified_server.py during startup.

    Args:
        questdb_provider: QuestDB provider for database queries
        live_order_manager: LiveOrderManager service (optional, for order operations)
        get_current_user_dependency: FastAPI dependency for authentication
        verify_csrf_token_dependency: FastAPI dependency for CSRF protection
    """
    global _questdb_provider, _live_order_manager, _get_current_user_dependency, _verify_csrf_token_dependency
    _questdb_provider = questdb_provider
    _live_order_manager = live_order_manager
    _get_current_user_dependency = get_current_user_dependency
    _verify_csrf_token_dependency = verify_csrf_token_dependency

    logger.info("trading_routes.dependencies_initialized", {
        "questdb_provider_available": _questdb_provider is not None,
        "live_order_manager_available": _live_order_manager is not None,
        "auth_dependency_available": _get_current_user_dependency is not None,
        "csrf_dependency_available": _verify_csrf_token_dependency is not None
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
        # SECURITY: Fail hard if authentication not configured
        async def auth_not_configured() -> UserSession:
            logger.error("trading_routes.auth_not_configured",
                        {"message": "Authentication system not configured - trading endpoints unavailable"})
            raise HTTPException(
                status_code=503,
                detail="Authentication not configured - system unavailable. Contact administrator."
            )
        return auth_not_configured
    return _get_current_user_dependency


def verify_csrf_token():
    """
    Get CSRF token verification dependency (wrapper for unified_server's implementation).

    This function returns the actual dependency function that should be used with Depends().
    """
    if _verify_csrf_token_dependency is None:
        # SECURITY: Fail hard if CSRF protection not configured
        async def csrf_not_configured() -> str:
            logger.error("trading_routes.csrf_not_configured",
                        {"message": "CSRF protection not configured - trading endpoints unavailable"})
            raise HTTPException(
                status_code=503,
                detail="CSRF protection not configured - system unavailable. Contact administrator."
            )
        return csrf_not_configured
    return _verify_csrf_token_dependency


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


class ModifySlTpRequest(BaseModel):
    """Request to modify SL/TP for a position (PM-03)."""
    stop_loss: Optional[float] = Field(None, description="New stop loss price (null to remove)")
    take_profit: Optional[float] = Field(None, description="New take profit price (null to remove)")


class ModifySlTpResponse(BaseModel):
    """Response after modifying SL/TP."""
    success: bool
    message: str
    position_id: str
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    updated_at: str


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
        positions = await provider.execute_query(query, params)

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
    current_user: UserSession = Depends(get_current_user),
    csrf_token: str = Depends(verify_csrf_token)
) -> ClosePositionResponse:
    """
    Close a live position by creating a reverse order.

    Position ID format: "session_id:symbol" (e.g., "live_20251107_abc123:BTC_USDT")

    This endpoint:
    1. Acquires position lock (SEC-0-1: prevents race conditions)
    2. Fetches the position from live_positions table
    3. Creates a reverse order (LONG → SELL, SHORT → BUY)
    4. Submits the order via LiveOrderManager
    5. Returns order ID and estimated P&L
    6. Releases position lock

    Args:
        position_id: Position identifier (session_id:symbol)
        request: Close position request with reason

    Returns:
        Close position response with order ID and P&L

    Raises:
        HTTPException 409: If position is already being closed (race condition prevented)
    """
    # SEC-0-1: Acquire position lock to prevent race conditions
    lock_acquired = await _position_lock_manager.acquire(position_id, "close")
    if not lock_acquired:
        lock_info = _position_lock_manager.get_lock_info(position_id)
        logger.warning("trading_api.close_position.race_condition_prevented", {
            "position_id": position_id,
            "lock_info": lock_info
        })
        raise HTTPException(
            status_code=409,
            detail=f"Position {position_id} is already being closed by another operation. Please wait and try again."
        )

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
        positions = await provider.execute_query(query, [session_id, symbol])

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
    finally:
        # SEC-0-1: Always release the position lock
        _position_lock_manager.release(position_id)


@router.patch("/positions/{position_id}/sl-tp", response_model=ModifySlTpResponse)
async def modify_sl_tp(
    position_id: str = Path(..., description="Position ID (format: session_id:symbol)"),
    request: ModifySlTpRequest = ModifySlTpRequest(),
    current_user: UserSession = Depends(get_current_user),
    csrf_token: str = Depends(verify_csrf_token)
) -> ModifySlTpResponse:
    """
    Modify Stop Loss and Take Profit for an open position (PM-03).

    Position ID format: "session_id:symbol" (e.g., "live_20251107_abc123:BTC_USDT")

    This endpoint:
    1. Acquires position lock (SEC-0-1: prevents race conditions)
    2. Validates the position exists and is OPEN
    3. Validates SL/TP values (SL below entry for SHORT, above for LONG, etc.)
    4. Updates SL/TP in live_positions table
    5. Optionally creates/modifies conditional orders on exchange
    6. Releases position lock

    Args:
        position_id: Position identifier (session_id:symbol)
        request: New SL/TP values (null to remove)

    Returns:
        Updated SL/TP values with timestamp

    Raises:
        HTTPException 409: If position is being modified by another operation
    """
    # SEC-0-1: Acquire position lock to prevent race conditions
    lock_acquired = await _position_lock_manager.acquire(position_id, "modify_sl_tp")
    if not lock_acquired:
        lock_info = _position_lock_manager.get_lock_info(position_id)
        logger.warning("trading_api.modify_sl_tp.race_condition_prevented", {
            "position_id": position_id,
            "lock_info": lock_info
        })
        raise HTTPException(
            status_code=409,
            detail=f"Position {position_id} is being modified by another operation. Please wait and try again."
        )

    try:
        provider = get_questdb_provider()

        # Parse position_id (format: session_id:symbol)
        parts = position_id.split(":")
        if len(parts) != 2:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid position_id format. Expected 'session_id:symbol', got '{position_id}'"
            )

        session_id, symbol = parts

        # Fetch current position
        query = """
            SELECT * FROM live_positions
            WHERE session_id = $1 AND symbol = $2 AND status = 'OPEN'
            ORDER BY updated_at DESC LIMIT 1
        """
        positions = await provider.execute_query(query, [session_id, symbol])

        if not positions:
            raise HTTPException(
                status_code=404,
                detail=f"Position not found: {position_id} (or already closed)"
            )

        position = positions[0]
        entry_price = position.get("entry_price", 0.0)
        side = position.get("side", "")

        # Validate SL/TP values based on position side
        if request.stop_loss is not None:
            if side == "LONG" and request.stop_loss >= entry_price:
                raise HTTPException(
                    status_code=400,
                    detail=f"Stop Loss ({request.stop_loss}) must be below entry price ({entry_price}) for LONG position"
                )
            if side == "SHORT" and request.stop_loss <= entry_price:
                raise HTTPException(
                    status_code=400,
                    detail=f"Stop Loss ({request.stop_loss}) must be above entry price ({entry_price}) for SHORT position"
                )

        if request.take_profit is not None:
            if side == "LONG" and request.take_profit <= entry_price:
                raise HTTPException(
                    status_code=400,
                    detail=f"Take Profit ({request.take_profit}) must be above entry price ({entry_price}) for LONG position"
                )
            if side == "SHORT" and request.take_profit >= entry_price:
                raise HTTPException(
                    status_code=400,
                    detail=f"Take Profit ({request.take_profit}) must be below entry price ({entry_price}) for SHORT position"
                )

        # Update position in database
        # Note: QuestDB uses INSERT for updates (time-series append)
        # We create a new row with updated values
        update_time = datetime.now(timezone.utc)

        # Prepare updated values (keep existing if not provided)
        new_sl = request.stop_loss if request.stop_loss is not None else position.get("stop_loss_price")
        new_tp = request.take_profit if request.take_profit is not None else position.get("take_profit_price")

        # Insert updated position record
        insert_query = """
            INSERT INTO live_positions (
                session_id, symbol, side, quantity, entry_price, current_price,
                liquidation_price, unrealized_pnl, unrealized_pnl_pct, margin,
                leverage, margin_ratio, stop_loss_price, take_profit_price,
                opened_at, updated_at, status, timestamp
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18
            )
        """
        await provider.execute(
            insert_query,
            session_id,
            symbol,
            position.get("side"),
            position.get("quantity"),
            position.get("entry_price"),
            position.get("current_price"),
            position.get("liquidation_price"),
            position.get("unrealized_pnl"),
            position.get("unrealized_pnl_pct"),
            position.get("margin"),
            position.get("leverage"),
            position.get("margin_ratio"),
            new_sl,
            new_tp,
            position.get("opened_at"),
            update_time,
            "OPEN",
            update_time
        )

        logger.info("trading_api.sl_tp_modified", {
            "position_id": position_id,
            "symbol": symbol,
            "side": side,
            "old_sl": position.get("stop_loss_price"),
            "new_sl": new_sl,
            "old_tp": position.get("take_profit_price"),
            "new_tp": new_tp
        })

        return ModifySlTpResponse(
            success=True,
            message=f"SL/TP updated for position {position_id}",
            position_id=position_id,
            stop_loss=new_sl,
            take_profit=new_tp,
            updated_at=update_time.isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("trading_api.modify_sl_tp_error", {
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
        orders = await provider.execute_query(query, params if params else None)

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
    current_user: UserSession = Depends(get_current_user),
    csrf_token: str = Depends(verify_csrf_token)
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
        orders = await provider.execute_query(query, [order_id])

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
            cancelled_at=datetime.now(timezone.utc).isoformat()
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
        orders = await provider.execute_query(orders_query, [session_id])

        # 2. Fetch all positions (to get unrealized P&L)
        positions_query = """
            SELECT symbol, unrealized_pnl, status, opened_at, closed_at
            FROM live_positions
            WHERE session_id = $1
            ORDER BY opened_at ASC
        """
        positions = await provider.execute_query(positions_query, [session_id])

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

        # Fetch equity curve data for max_drawdown and sharpe_ratio calculations
        equity_query = """
            SELECT current_balance, max_drawdown, timestamp
            FROM paper_trading_performance
            WHERE session_id = $1
            ORDER BY timestamp ASC
        """
        equity_data = await provider.execute_query(equity_query, [session_id])

        # Max drawdown from equity curve
        if equity_data and len(equity_data) > 0:
            max_drawdown = max([row.get("max_drawdown", 0.0) for row in equity_data])
        else:
            max_drawdown = 0.0

        # Sharpe ratio calculation from balance series
        # PH2 FIX: Initialize to 0.0 instead of None to avoid placeholder
        sharpe_ratio = 0.0
        if equity_data and len(equity_data) >= 2:
            balances = [row.get("current_balance", 0.0) for row in equity_data]
            # Calculate period returns (percentage change between snapshots)
            returns = []
            for i in range(1, len(balances)):
                if balances[i-1] > 0:
                    period_return = (balances[i] - balances[i-1]) / balances[i-1]
                    returns.append(period_return)

            if len(returns) >= 2:
                import statistics
                mean_return = statistics.mean(returns)
                std_return = statistics.stdev(returns)
                if std_return > 0:
                    # Annualized Sharpe ratio (assuming ~252 trading days)
                    # For intraday: use sqrt of periods per year
                    risk_free_rate = 0.0  # Simplified: 0% risk-free rate
                    sharpe_ratio = (mean_return - risk_free_rate) / std_return * (252 ** 0.5)
                else:
                    # No volatility = no risk = sharpe ratio of 0.0
                    sharpe_ratio = 0.0
            # else: < 2 returns, sharpe_ratio stays 0.0

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

        # Fetch initial balance from session config
        session_query = """
            SELECT initial_balance
            FROM paper_trading_sessions
            WHERE session_id = $1
            LIMIT 1
        """
        session_data = await provider.execute_query(session_query, [session_id])
        initial_balance = 10000.0  # Default fallback
        if session_data and len(session_data) > 0:
            initial_balance = session_data[0].get("initial_balance", 10000.0)

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
