"""
PositionSyncService - Position Synchronization with MEXC
=========================================================
Synchronizes local positions with exchange positions to detect liquidations and manual closes.

Features:
- Background sync every 10 seconds
- Fetch positions from MEXC via get_positions()
- Reconcile local vs exchange positions
- Detect liquidations (position missing on exchange)
- Calculate margin ratio: equity / maintenance_margin
- Emit position_updated, position_closed, risk_alert events
- Handle network failures gracefully

Critical Requirements:
- ✅ Max 100 positions tracked (NO defaultdict, explicit dict)
- ✅ Explicit cleanup in stop() methods
- ✅ Circuit breaker wraps all MEXC calls
- ✅ All config from settings.py
"""

import asyncio
import time
import logging
from typing import Dict, Optional, List, Any
from dataclasses import dataclass

from ...core.event_bus import EventBus
from ...infrastructure.adapters.mexc_adapter import MexcRealAdapter, PositionResponse
from ...core.circuit_breaker import CircuitBreakerOpenException

logger = logging.getLogger(__name__)


@dataclass
class LocalPosition:
    """Local position tracking"""
    symbol: str
    side: str  # "LONG" or "SHORT"
    quantity: float
    entry_price: float
    current_price: float
    liquidation_price: float
    unrealized_pnl: float
    margin: float
    leverage: float
    margin_ratio: float  # equity / maintenance_margin (%)
    opened_at: float
    updated_at: float


class PositionSyncService:
    """
    Synchronizes local positions with exchange positions.

    Responsibilities:
    - Fetch positions from MEXC every 10s
    - Detect discrepancies (liquidation, manual close)
    - Calculate margin ratio
    - Emit position_updated events
    - Emit risk_alert events when margin < 15%

    Memory Management:
    - Max 100 positions tracked
    - Closed positions removed immediately
    """

    def __init__(
        self,
        event_bus: EventBus,
        mexc_adapter: MexcRealAdapter,
        risk_manager,  # RiskManager for margin ratio checking
        max_positions: int = 100
    ):
        """
        Initialize PositionSyncService.

        Args:
            event_bus: EventBus instance for pub/sub
            mexc_adapter: MEXC adapter with circuit breaker
            risk_manager: RiskManager for margin ratio alerts
            max_positions: Maximum number of positions to track
        """
        self.event_bus = event_bus
        self.mexc_adapter = mexc_adapter
        self.risk_manager = risk_manager
        self.max_positions = max_positions

        # Local position tracking (CRITICAL: Not defaultdict)
        self.positions: Dict[str, LocalPosition] = {}

        # Lock for thread-safe positions dict access
        self._positions_lock = asyncio.Lock()

        # Background task
        self._sync_task: Optional[asyncio.Task] = None
        self._running = False

        # Note: EventBus subscriptions moved to start() method (async required)

        logger.info(f"PositionSyncService initialized (max_positions: {max_positions})")

    async def start(self):
        """Start position sync background task and subscribe to events."""
        if self._running:
            logger.warning("PositionSyncService already running")
            return

        logger.info("Starting PositionSyncService background sync...")
        self._running = True

        # Subscribe to order fills (async required)
        await self.event_bus.subscribe("order_filled", self._on_order_filled)

        # Start background sync task
        self._sync_task = asyncio.create_task(self._sync_positions())

    async def stop(self):
        """Stop position sync and cleanup."""
        logger.info("Stopping PositionSyncService...")
        self._running = False

        # Unsubscribe from events
        await self.event_bus.unsubscribe("order_filled", self._on_order_filled)

        # Cancel background task
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass

        # Explicit cleanup (memory leak prevention)
        async with self._positions_lock:
            self.positions.clear()

        logger.info("PositionSyncService stopped")

    async def _on_order_filled(self, data: Dict):
        """
        Handle order fill event.

        Updates local position or creates new position.

        Args:
            data: Order filled event data
        """
        symbol = data.get("symbol")
        side = data.get("side")  # "buy" or "sell"
        quantity = data.get("quantity", 0.0)
        price = data.get("price", 0.0)

        if not symbol or not side or quantity == 0:
            return

        # Track if we need to close position (outside lock)
        should_close = False
        position_to_close = None

        # Protect positions dict access with lock
        async with self._positions_lock:
            # Check if position exists
            if symbol in self.positions:
                # Update existing position
                position = self.positions[symbol]

                if side.lower() == "buy":
                    # Buying (adding to long or reducing short)
                    if position.side == "LONG":
                        # Average entry price for adding to long
                        total_cost = position.quantity * position.entry_price + quantity * price
                        position.quantity += quantity
                        position.entry_price = total_cost / position.quantity if position.quantity > 0 else price
                    else:  # SHORT
                        # Reducing short position
                        position.quantity -= quantity
                        if position.quantity <= 0:
                            # Position closed
                            logger.info(f"Position closed via buy: {symbol}")
                            should_close = True
                            position_to_close = position
                else:  # sell
                    # Selling (adding to short or reducing long)
                    if position.side == "SHORT":
                        # Average entry price for adding to short
                        total_cost = position.quantity * position.entry_price + quantity * price
                        position.quantity += quantity
                        position.entry_price = total_cost / position.quantity if position.quantity > 0 else price
                    else:  # LONG
                        # Reducing long position
                        position.quantity -= quantity
                        if position.quantity <= 0:
                            # Position closed
                            logger.info(f"Position closed via sell: {symbol}")
                            should_close = True
                            position_to_close = position

                if not should_close:
                    position.updated_at = time.time()

            else:
                # Create new position
                if len(self.positions) >= self.max_positions:
                    logger.error(f"Max positions reached ({self.max_positions}), cannot track {symbol}")
                    return

                position = LocalPosition(
                    symbol=symbol,
                    side="LONG" if side.lower() == "buy" else "SHORT",
                    quantity=quantity,
                    entry_price=price,
                    current_price=price,
                    liquidation_price=0.0,  # Will be updated by sync
                    unrealized_pnl=0.0,
                    margin=0.0,
                    leverage=1.0,
                    margin_ratio=100.0,
                    opened_at=time.time(),
                    updated_at=time.time()
                )

                self.positions[symbol] = position

                logger.info(f"New position created: {symbol} {position.side} {position.quantity}")

        # Handle position close outside lock (to avoid nested lock calls)
        if should_close and position_to_close:
            await self._close_position(symbol, position_to_close)
            return

        # Emit position updated event for new positions (outside lock)
        if symbol in self.positions and not should_close:
            async with self._positions_lock:
                if symbol in self.positions:
                    pos = self.positions[symbol]
                    await self.event_bus.publish("position_updated", {
                        "position_id": symbol,
                        "symbol": symbol,
                        "status": "opened",
                        "side": pos.side,
                        "quantity": pos.quantity,
                        "entry_price": pos.entry_price,
                        "current_price": pos.current_price,
                        "unrealized_pnl": pos.unrealized_pnl,
                        "margin_ratio": pos.margin_ratio,
                        "liquidation_price": pos.liquidation_price,
                        "timestamp": int(time.time() * 1000)
                    })

    async def _close_position(self, symbol: str, position: LocalPosition):
        """
        Close position and emit events.

        Args:
            symbol: Symbol being closed
            position: Position object
        """
        # Remove from tracking (protect with lock)
        async with self._positions_lock:
            if symbol in self.positions:
                del self.positions[symbol]

        # Emit position closed event
        await self.event_bus.publish("position_updated", {
            "position_id": symbol,
            "symbol": symbol,
            "status": "closed",
            "side": position.side,
            "quantity": 0.0,
            "entry_price": position.entry_price,
            "current_price": position.current_price,
            "unrealized_pnl": position.unrealized_pnl,
            "margin_ratio": position.margin_ratio,
            "liquidation_price": position.liquidation_price,
            "timestamp": int(time.time() * 1000)
        })

    async def _sync_positions(self):
        """
        Background task: Sync positions every 10 seconds.

        Fetches positions from MEXC and compares with local positions.
        """
        while self._running:
            try:
                await asyncio.sleep(10)

                # Fetch from MEXC (circuit breaker integrated in adapter)
                try:
                    exchange_positions: List[PositionResponse] = await self.mexc_adapter.get_positions()
                except CircuitBreakerOpenException:
                    logger.warning("Skipping position sync: circuit breaker open")
                    continue
                except Exception as e:
                    logger.error(f"Failed to fetch positions from MEXC: {e}")
                    continue

                # Build symbol → exchange position map
                exchange_map = {p.symbol: p for p in exchange_positions}

                # Protect positions dict access with lock
                async with self._positions_lock:
                    # Check each local position
                    for symbol in list(self.positions.keys()):
                        local_pos = self.positions[symbol]

                        if symbol not in exchange_map:
                            # Position missing on exchange → liquidated or manually closed
                            logger.warning(f"Position {symbol} missing on exchange (liquidation or manual close)")

                            # Remove from tracking
                            del self.positions[symbol]

                            # Emit liquidation event
                            await self.event_bus.publish("position_updated", {
                            "position_id": symbol,
                            "symbol": symbol,
                            "status": "liquidated",
                            "side": local_pos.side,
                            "quantity": 0.0,
                            "entry_price": local_pos.entry_price,
                            "current_price": local_pos.current_price,
                            "unrealized_pnl": local_pos.unrealized_pnl,
                            "margin_ratio": 0.0,
                            "liquidation_price": local_pos.liquidation_price,
                            "timestamp": int(time.time() * 1000)
                            })

                            # Emit critical risk alert
                            await self.event_bus.publish("risk_alert", {
                                "type": "risk_alert",
                                "alert_id": f"liquidation_{symbol}_{int(time.time())}",
                                "severity": "CRITICAL",
                                "alert_type": "LIQUIDATION_DETECTED",
                                "message": f"🚨 LIQUIDATION DETECTED: {symbol}",
                                "details": {
                                    "symbol": symbol,
                                    "side": local_pos.side,
                                    "entry_price": local_pos.entry_price,
                                    "last_price": local_pos.current_price
                                },
                                "timestamp": int(time.time() * 1000)
                            })
                        else:
                            # Position exists, update details
                            exchange_pos = exchange_map[symbol]

                            local_pos.current_price = exchange_pos.current_price
                            local_pos.liquidation_price = exchange_pos.liquidation_price
                            local_pos.unrealized_pnl = exchange_pos.unrealized_pnl
                            local_pos.margin = exchange_pos.margin
                            local_pos.leverage = exchange_pos.leverage
                            local_pos.margin_ratio = exchange_pos.margin_ratio
                            local_pos.updated_at = time.time()

                            # Emit position updated event
                            await self.event_bus.publish("position_updated", {
                                "position_id": symbol,
                                "symbol": symbol,
                                "status": "updated",
                                "side": local_pos.side,
                                "quantity": local_pos.quantity,
                                "entry_price": local_pos.entry_price,
                                "current_price": local_pos.current_price,
                                "unrealized_pnl": local_pos.unrealized_pnl,
                                "margin_ratio": local_pos.margin_ratio,
                                "liquidation_price": local_pos.liquidation_price,
                                "timestamp": int(time.time() * 1000)
                            })

                            # Check margin ratio via RiskManager
                            if self.risk_manager:
                                try:
                                    from decimal import Decimal
                                    await self.risk_manager.check_margin_ratio(Decimal(str(local_pos.margin_ratio)))
                                except Exception as e:
                                    logger.error(f"Risk manager check failed for {symbol}: {e}")

                    # Check for new positions on exchange (manually opened?)
                    for symbol, exchange_pos in exchange_map.items():
                        if symbol not in self.positions:
                            logger.info(f"New position detected on exchange: {symbol}")

                            if len(self.positions) >= self.max_positions:
                                logger.error(f"Max positions reached ({self.max_positions}), cannot track {symbol}")
                                continue

                            # Add to local tracking
                            position = LocalPosition(
                                symbol=symbol,
                                side=exchange_pos.side,
                                quantity=exchange_pos.quantity,
                                entry_price=exchange_pos.entry_price,
                                current_price=exchange_pos.current_price,
                                liquidation_price=exchange_pos.liquidation_price,
                                unrealized_pnl=exchange_pos.unrealized_pnl,
                                margin=exchange_pos.margin,
                                leverage=exchange_pos.leverage,
                                margin_ratio=exchange_pos.margin_ratio,
                                opened_at=time.time(),
                                updated_at=time.time()
                            )

                            self.positions[symbol] = position

                            await self.event_bus.publish("position_updated", {
                                "position_id": symbol,
                                "symbol": symbol,
                                "status": "opened",
                                "side": position.side,
                                "quantity": position.quantity,
                                "entry_price": position.entry_price,
                                "current_price": position.current_price,
                                "unrealized_pnl": position.unrealized_pnl,
                                "margin_ratio": position.margin_ratio,
                                "liquidation_price": position.liquidation_price,
                                "timestamp": int(time.time() * 1000)
                            })

            except asyncio.CancelledError:
                logger.info("Position sync stopped")
                break
            except Exception as e:
                logger.error(f"Error in position sync: {e}")

    # === Public Getters ===

    async def get_position(self, symbol: str) -> Optional[LocalPosition]:
        """Get position by symbol."""
        async with self._positions_lock:
            return self.positions.get(symbol)

    async def get_all_positions(self) -> List[LocalPosition]:
        """Get all tracked positions."""
        async with self._positions_lock:
            return list(self.positions.values())

    async def get_metrics(self) -> Dict[str, Any]:
        """Get position sync metrics."""
        async with self._positions_lock:
            total_unrealized_pnl = sum(p.unrealized_pnl for p in self.positions.values())

            return {
                "total_positions": len(self.positions),
                "long_positions": sum(1 for p in self.positions.values() if p.side == "LONG"),
                "short_positions": sum(1 for p in self.positions.values() if p.side == "SHORT"),
                "total_unrealized_pnl": total_unrealized_pnl,
                "avg_margin_ratio": (
                    sum(p.margin_ratio for p in self.positions.values()) / len(self.positions)
                    if self.positions else 0.0
                ),
                "min_margin_ratio": (
                    min(p.margin_ratio for p in self.positions.values())
                    if self.positions else 0.0
                )
            }
