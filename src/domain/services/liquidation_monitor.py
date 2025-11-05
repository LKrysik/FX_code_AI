"""
Liquidation Monitor Service - TIER 1.4
=======================================
Monitors leveraged positions in real-time and publishes warnings when positions
approach liquidation prices to prevent catastrophic losses.

Key Features:
- Real-time tracking of open positions with leverage
- Distance to liquidation calculation for LONG and SHORT positions
- Warning levels: CRITICAL (<10%), HIGH (10-20%), MEDIUM (20-30%)
- EventBus integration for position updates and market data
- Automatic cleanup of closed positions

Warning Thresholds:
- CRITICAL: Distance to liquidation < 10% (immediate action required)
- HIGH: Distance 10-20% (high risk, close monitoring)
- MEDIUM: Distance 20-30% (elevated risk, prepare exit strategy)
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
import asyncio

from src.core.logger import StructuredLogger


@dataclass
class PositionInfo:
    """Tracked position information for liquidation monitoring."""

    # Identification
    session_id: str
    symbol: str

    # Position details
    position_side: str  # "LONG" or "SHORT"
    entry_price: float
    current_price: float
    position_amount: float
    leverage: float

    # Risk metrics
    liquidation_price: float
    distance_to_liquidation_pct: float = 0.0

    # Tracking
    last_updated: datetime = field(default_factory=datetime.utcnow)
    last_warning_level: Optional[str] = None
    warning_count: int = 0


class LiquidationMonitor:
    """
    Real-time liquidation monitor for leveraged positions.

    Monitors all open leveraged positions and calculates distance to liquidation
    price. Publishes warnings to EventBus when positions approach dangerous levels.

    Architecture:
    - Subscribes to paper_trading.position_updated events
    - Subscribes to market_data events for price updates
    - Publishes liquidation_warning events when thresholds crossed
    - Memory-efficient: tracks only open positions with leverage > 1
    """

    def __init__(
        self,
        event_bus: Any,
        logger: Optional[StructuredLogger] = None
    ):
        """
        Initialize liquidation monitor.

        Args:
            event_bus: EventBus instance for pub/sub
            logger: Structured logger instance
        """
        self.event_bus = event_bus
        self.logger = logger

        # Active positions: {session_id: {symbol: PositionInfo}}
        self.active_positions: Dict[str, Dict[str, PositionInfo]] = {}

        # Warning thresholds (percentage distance to liquidation)
        self.CRITICAL_THRESHOLD = 10.0  # < 10% = CRITICAL
        self.HIGH_THRESHOLD = 20.0      # 10-20% = HIGH
        self.MEDIUM_THRESHOLD = 30.0    # 20-30% = MEDIUM

        # Suppress duplicate warnings within this interval (seconds)
        self.WARNING_COOLDOWN = 60

        self._running = False
        self._subscription_tasks: List[asyncio.Task] = []

    async def start(self) -> None:
        """Start monitoring service and subscribe to events."""
        if self._running:
            if self.logger:
                self.logger.warning("liquidation_monitor.already_running")
            return

        self._running = True

        # Subscribe to position updates
        position_task = asyncio.create_task(
            self.event_bus.subscribe("paper_trading.position_updated", self._handle_position_update)
        )
        self._subscription_tasks.append(position_task)

        # Subscribe to market data
        market_task = asyncio.create_task(
            self.event_bus.subscribe("market_data", self._handle_market_data)
        )
        self._subscription_tasks.append(market_task)

        if self.logger:
            self.logger.info("liquidation_monitor.started")

    async def stop(self) -> None:
        """Stop monitoring service and cleanup."""
        if not self._running:
            return

        self._running = False

        # Cancel subscription tasks
        for task in self._subscription_tasks:
            task.cancel()

        # Wait for tasks to finish
        await asyncio.gather(*self._subscription_tasks, return_exceptions=True)
        self._subscription_tasks.clear()

        # Clear tracked positions
        self.active_positions.clear()

        if self.logger:
            self.logger.info("liquidation_monitor.stopped")

    async def _handle_position_update(self, event: Dict[str, Any]) -> None:
        """
        Handle position update event.

        Updates tracked position or removes if closed.

        Args:
            event: Position update event data
        """
        try:
            session_id = event.get("session_id")
            symbol = event.get("symbol")

            if not session_id or not symbol:
                return

            # Check if position is closed
            position_amount = event.get("position_amount", 0.0)
            if position_amount == 0.0:
                # Position closed - remove from tracking
                self._remove_position(session_id, symbol)
                return

            # Check leverage - only monitor leveraged positions
            leverage = event.get("leverage", 1.0)
            if leverage <= 1.0:
                # No leverage - no liquidation risk
                self._remove_position(session_id, symbol)
                return

            # Create or update position info
            position = PositionInfo(
                session_id=session_id,
                symbol=symbol,
                position_side=event.get("position_side", "LONG"),
                entry_price=event.get("entry_price", 0.0),
                current_price=event.get("current_price", 0.0),
                position_amount=position_amount,
                leverage=leverage,
                liquidation_price=event.get("liquidation_price", 0.0)
            )

            # Calculate distance to liquidation
            if position.liquidation_price > 0:
                position.distance_to_liquidation_pct = self._calculate_distance_to_liquidation(
                    position.current_price,
                    position.liquidation_price,
                    position.position_side
                )

            # Store position
            if session_id not in self.active_positions:
                self.active_positions[session_id] = {}

            self.active_positions[session_id][symbol] = position

            # Check if warning needed
            await self._check_and_publish_warning(position)

            if self.logger:
                self.logger.debug("liquidation_monitor.position_tracked", {
                    "session_id": session_id,
                    "symbol": symbol,
                    "leverage": leverage,
                    "distance_pct": round(position.distance_to_liquidation_pct, 2)
                })

        except Exception as e:
            if self.logger:
                self.logger.error("liquidation_monitor.position_update_error", {
                    "error": str(e),
                    "event": event
                })

    async def _handle_market_data(self, event: Dict[str, Any]) -> None:
        """
        Handle market data event - update current prices and check liquidation distance.

        Args:
            event: Market data event with current price
        """
        try:
            symbol = event.get("symbol")
            current_price = event.get("price")

            if not symbol or not current_price:
                return

            # Update all positions for this symbol
            for session_id, positions in self.active_positions.items():
                if symbol not in positions:
                    continue

                position = positions[symbol]
                position.current_price = current_price
                position.last_updated = datetime.utcnow()

                # Recalculate distance to liquidation
                if position.liquidation_price > 0:
                    position.distance_to_liquidation_pct = self._calculate_distance_to_liquidation(
                        current_price,
                        position.liquidation_price,
                        position.position_side
                    )

                    # Check if warning needed
                    await self._check_and_publish_warning(position)

        except Exception as e:
            if self.logger:
                self.logger.error("liquidation_monitor.market_data_error", {
                    "error": str(e),
                    "symbol": event.get("symbol")
                })

    def _calculate_distance_to_liquidation(
        self,
        current_price: float,
        liquidation_price: float,
        position_side: str
    ) -> float:
        """
        Calculate percentage distance from current price to liquidation price.

        Formula:
        - LONG: distance = (current_price - liquidation_price) / current_price * 100
        - SHORT: distance = (liquidation_price - current_price) / current_price * 100

        Positive distance = safe, negative distance = already liquidated

        Args:
            current_price: Current market price
            liquidation_price: Position liquidation price
            position_side: "LONG" or "SHORT"

        Returns:
            Percentage distance (positive = safe, negative = danger)
        """
        if current_price <= 0:
            return 0.0

        if position_side == "LONG":
            # LONG: liquidation below entry, price must drop
            distance = ((current_price - liquidation_price) / current_price) * 100
        else:
            # SHORT: liquidation above entry, price must rise
            distance = ((liquidation_price - current_price) / current_price) * 100

        return distance

    async def _check_and_publish_warning(self, position: PositionInfo) -> None:
        """
        Check position risk level and publish warning if threshold crossed.

        Args:
            position: Position to check
        """
        distance = position.distance_to_liquidation_pct

        # Determine warning level
        warning_level = None
        if distance < 0:
            warning_level = "LIQUIDATED"  # Already liquidated
        elif distance < self.CRITICAL_THRESHOLD:
            warning_level = "CRITICAL"
        elif distance < self.HIGH_THRESHOLD:
            warning_level = "HIGH"
        elif distance < self.MEDIUM_THRESHOLD:
            warning_level = "MEDIUM"

        if not warning_level:
            # Reset warning tracking if position is now safe
            if position.last_warning_level:
                position.last_warning_level = None
                position.warning_count = 0
            return

        # Check if we should suppress duplicate warning (cooldown)
        should_publish = False
        if position.last_warning_level != warning_level:
            # Warning level changed - always publish
            should_publish = True
        elif position.warning_count == 0:
            # First warning - always publish
            should_publish = True
        else:
            # Check cooldown
            time_since_last = (datetime.utcnow() - position.last_updated).total_seconds()
            if time_since_last > self.WARNING_COOLDOWN:
                should_publish = True

        if should_publish:
            await self._publish_warning(position, warning_level, distance)
            position.last_warning_level = warning_level
            position.warning_count += 1

    async def _publish_warning(
        self,
        position: PositionInfo,
        warning_level: str,
        distance: float
    ) -> None:
        """
        Publish liquidation warning event to EventBus.

        Args:
            position: Position at risk
            warning_level: CRITICAL, HIGH, MEDIUM, or LIQUIDATED
            distance: Percentage distance to liquidation
        """
        event_data = {
            "session_id": position.session_id,
            "symbol": position.symbol,
            "position_side": position.position_side,
            "leverage": position.leverage,
            "entry_price": position.entry_price,
            "current_price": position.current_price,
            "liquidation_price": position.liquidation_price,
            "distance_pct": round(distance, 2),
            "warning_level": warning_level,
            "timestamp": datetime.utcnow().isoformat(),
            "position_amount": position.position_amount,
            "unrealized_pnl": self._calculate_unrealized_pnl(position)
        }

        await self.event_bus.publish("paper_trading.liquidation_warning", event_data)

        if self.logger:
            self.logger.warning("liquidation_monitor.warning_published", {
                "session_id": position.session_id,
                "symbol": position.symbol,
                "warning_level": warning_level,
                "distance_pct": round(distance, 2),
                "leverage": position.leverage
            })

    def _calculate_unrealized_pnl(self, position: PositionInfo) -> float:
        """
        Calculate unrealized P&L for position.

        Args:
            position: Position to calculate P&L for

        Returns:
            Unrealized P&L in USDT
        """
        if position.position_side == "LONG":
            pnl = (position.current_price - position.entry_price) * position.position_amount
        else:
            pnl = (position.entry_price - position.current_price) * abs(position.position_amount)

        return pnl

    def _remove_position(self, session_id: str, symbol: str) -> None:
        """
        Remove position from tracking.

        Args:
            session_id: Session ID
            symbol: Trading symbol
        """
        if session_id in self.active_positions:
            if symbol in self.active_positions[session_id]:
                del self.active_positions[session_id][symbol]

                if self.logger:
                    self.logger.debug("liquidation_monitor.position_removed", {
                        "session_id": session_id,
                        "symbol": symbol
                    })

                # Clean up empty session
                if not self.active_positions[session_id]:
                    del self.active_positions[session_id]

    def get_tracked_positions(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        Get all currently tracked positions (for debugging/monitoring).

        Returns:
            Dict of {session_id: {symbol: position_data}}
        """
        result = {}
        for session_id, positions in self.active_positions.items():
            result[session_id] = {}
            for symbol, position in positions.items():
                result[session_id][symbol] = {
                    "symbol": position.symbol,
                    "position_side": position.position_side,
                    "leverage": position.leverage,
                    "entry_price": position.entry_price,
                    "current_price": position.current_price,
                    "liquidation_price": position.liquidation_price,
                    "distance_pct": round(position.distance_to_liquidation_pct, 2),
                    "last_warning_level": position.last_warning_level,
                    "unrealized_pnl": self._calculate_unrealized_pnl(position)
                }
        return result

    def get_high_risk_positions(self, threshold: float = 20.0) -> List[Dict[str, Any]]:
        """
        Get all positions with distance to liquidation below threshold.

        Args:
            threshold: Distance threshold in percent (default 20%)

        Returns:
            List of high-risk positions
        """
        high_risk = []
        for session_id, positions in self.active_positions.items():
            for symbol, position in positions.items():
                if position.distance_to_liquidation_pct < threshold:
                    high_risk.append({
                        "session_id": session_id,
                        "symbol": symbol,
                        "distance_pct": round(position.distance_to_liquidation_pct, 2),
                        "leverage": position.leverage,
                        "current_price": position.current_price,
                        "liquidation_price": position.liquidation_price
                    })
        return high_risk
