"""
Trading Persistence Service
============================
Unified persistence for signals, orders, and positions across ALL trading modes.

Architecture:
- Subscribes to EventBus events (signal_generated, order_created, etc.)
- Writes to QuestDB tables (strategy_signals, orders, positions)
- Used by ALL modes: live, paper, backtest (NO mode-specific code)
- Single source of truth for trading data persistence

Database Tables:
- strategy_signals: S1, Z1, ZE1, E1, O1, EMERGENCY signals
- orders: Order lifecycle (NEW, FILLED, PARTIALLY_FILLED, CANCELLED)
- positions: Position snapshots (OPEN, CLOSED, LIQUIDATED)
"""

import asyncpg
import json
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from ...core.logger import StructuredLogger
from ...core.event_bus import EventBus


class TradingPersistenceService:
    """
    Unified trading persistence for all modes (live/paper/backtest).

    Responsibilities:
    1. Subscribe to EventBus trading events
    2. Persist signals to strategy_signals table
    3. Persist orders to orders table
    4. Persist positions to positions table
    5. Provide query methods for analysis

    Design Principles:
    - Mode-agnostic: Works identically for live/paper/backtest
    - EventBus-driven: Reacts to events, doesn't poll
    - Async-first: All I/O is non-blocking
    - Error-resilient: Logs errors but doesn't crash trading
    """

    def __init__(self,
                 host: str = '127.0.0.1',
                 port: int = 8812,
                 user: str = 'admin',
                 password: str = 'quest',
                 database: str = 'qdb',
                 event_bus: Optional[EventBus] = None,
                 logger: Optional[StructuredLogger] = None,
                 min_pool_size: int = 2,
                 max_pool_size: int = 10):
        """
        Initialize trading persistence service.

        Args:
            host: QuestDB host
            port: PostgreSQL wire protocol port (default: 8812)
            user: Database user
            password: Database password
            database: Database name (default: qdb)
            event_bus: EventBus for subscribing to trading events
            logger: Structured logger
            min_pool_size: Minimum connection pool size
            max_pool_size: Maximum connection pool size
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.event_bus = event_bus
        self.logger = logger
        self.min_pool_size = min_pool_size
        self.max_pool_size = max_pool_size

        self._pool: Optional[asyncpg.Pool] = None
        self._started = False

        if self.logger:
            self.logger.info("trading_persistence.initialized", {
                "host": host,
                "port": port,
                "database": database,
                "event_bus_enabled": event_bus is not None
            })

    async def start(self) -> None:
        """
        Start persistence service.

        1. Create connection pool
        2. Subscribe to EventBus events
        3. Ready to persist trading data
        """
        if self._started:
            return

        # Create connection pool
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                min_size=self.min_pool_size,
                max_size=self.max_pool_size
            )

            if self.logger:
                self.logger.info("trading_persistence.pool_created", {
                    "min_size": self.min_pool_size,
                    "max_size": self.max_pool_size
                })

        # Subscribe to EventBus events
        if self.event_bus:
            await self.event_bus.subscribe("signal_generated", self._on_signal_generated)
            await self.event_bus.subscribe("order_created", self._on_order_created)
            await self.event_bus.subscribe("order_filled", self._on_order_filled)
            await self.event_bus.subscribe("order_cancelled", self._on_order_cancelled)
            await self.event_bus.subscribe("position_opened", self._on_position_opened)
            await self.event_bus.subscribe("position_updated", self._on_position_updated)
            await self.event_bus.subscribe("position_closed", self._on_position_closed)

            if self.logger:
                self.logger.info("trading_persistence.subscribed_to_events", {
                    "events": [
                        "signal_generated",
                        "order_created",
                        "order_filled",
                        "order_cancelled",
                        "position_opened",
                        "position_updated",
                        "position_closed"
                    ]
                })

        self._started = True

    async def stop(self) -> None:
        """
        Stop persistence service.

        1. Unsubscribe from EventBus
        2. Close connection pool
        3. Clean up resources
        """
        if not self._started:
            return

        # Unsubscribe from EventBus
        if self.event_bus:
            await self.event_bus.unsubscribe("signal_generated", self._on_signal_generated)
            await self.event_bus.unsubscribe("order_created", self._on_order_created)
            await self.event_bus.unsubscribe("order_filled", self._on_order_filled)
            await self.event_bus.unsubscribe("order_cancelled", self._on_order_cancelled)
            await self.event_bus.unsubscribe("position_opened", self._on_position_opened)
            await self.event_bus.unsubscribe("position_updated", self._on_position_updated)
            await self.event_bus.unsubscribe("position_closed", self._on_position_closed)

            if self.logger:
                self.logger.info("trading_persistence.unsubscribed_from_events")

        # Close pool
        if self._pool:
            await self._pool.close()
            self._pool = None

            if self.logger:
                self.logger.info("trading_persistence.pool_closed")

        self._started = False

    # ========================================================================
    # Event Handlers - Signal Persistence
    # ========================================================================

    async def _on_signal_generated(self, data: Dict[str, Any]) -> None:
        """
        Handle signal_generated event and persist to strategy_signals table.

        Event data format:
        {
            "signal_id": "signal_123",
            "strategy_id": "strategy_uuid",
            "symbol": "BTC_USDT",
            "signal_type": "S1",  # S1, Z1, ZE1, E1, O1, EMERGENCY
            "triggered": True,
            "conditions_met": {"rsi": 30, "ema_cross": True},
            "indicator_values": {"RSI_14": 28.5, "EMA_12": 50000},
            "action": "BUY",  # BUY, SELL, CANCEL, CLOSE
            "price": 50000.0,
            "quantity": 0.001,
            "metadata": {...}
        }
        """
        try:
            # Extract signal data
            strategy_id = data.get("strategy_id", "unknown")
            symbol = data.get("symbol", "").upper()
            signal_type = data.get("signal_type", "UNKNOWN")
            timestamp = data.get("timestamp", time.time())
            triggered = data.get("triggered", False)
            conditions_met = data.get("conditions_met", {})
            indicator_values = data.get("indicator_values", {})
            action = data.get("action", "").upper()
            metadata = data.get("metadata", {})

            # Convert to JSON strings
            conditions_json = json.dumps(conditions_met) if conditions_met else None
            indicators_json = json.dumps(indicator_values) if indicator_values else None
            metadata_json = json.dumps(metadata) if metadata else None

            # Convert timestamp to datetime
            if isinstance(timestamp, (int, float)):
                timestamp_dt = datetime.fromtimestamp(timestamp)
            else:
                timestamp_dt = timestamp

            # Insert into strategy_signals table
            query = """
                INSERT INTO strategy_signals (
                    strategy_id,
                    symbol,
                    signal_type,
                    timestamp,
                    triggered,
                    conditions_met,
                    indicator_values,
                    action,
                    metadata
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """

            async with self._pool.acquire() as conn:
                await conn.execute(
                    query,
                    strategy_id,
                    symbol,
                    signal_type,
                    timestamp_dt,
                    triggered,
                    conditions_json,
                    indicators_json,
                    action,
                    metadata_json
                )

            if self.logger:
                self.logger.debug("trading_persistence.signal_saved", {
                    "strategy_id": strategy_id,
                    "symbol": symbol,
                    "signal_type": signal_type,
                    "action": action
                })

        except Exception as e:
            if self.logger:
                self.logger.error("trading_persistence.signal_save_failed", {
                    "signal_data": data,
                    "error": str(e),
                    "error_type": type(e).__name__
                })

    # ========================================================================
    # Event Handlers - Order Persistence
    # ========================================================================

    async def _on_order_created(self, data: Dict[str, Any]) -> None:
        """
        Handle order_created event and persist to orders table.

        Event data format:
        {
            "order_id": "order_123",
            "strategy_id": "strategy_uuid",
            "symbol": "BTC_USDT",
            "side": "BUY",  # BUY or SELL
            "order_type": "MARKET",  # MARKET, LIMIT, STOP_LOSS
            "quantity": 0.001,
            "price": 50000.0,  # null for MARKET
            "status": "NEW",
            "metadata": {...}
        }
        """
        try:
            # Extract order data
            order_id = data.get("order_id", "unknown")
            strategy_id = data.get("strategy_id", "unknown")
            symbol = data.get("symbol", "").upper()
            side = data.get("side", "").upper()
            order_type = data.get("order_type", "MARKET").upper()
            timestamp = data.get("timestamp", time.time())
            quantity = float(data.get("quantity", 0))
            price = float(data.get("price", 0)) if data.get("price") else None
            status = data.get("status", "NEW").upper()
            metadata = data.get("metadata", {})

            # Convert timestamp
            if isinstance(timestamp, (int, float)):
                timestamp_dt = datetime.fromtimestamp(timestamp)
            else:
                timestamp_dt = timestamp

            # Convert metadata to JSON
            metadata_json = json.dumps(metadata) if metadata else None

            # Insert into orders table
            query = """
                INSERT INTO orders (
                    order_id,
                    strategy_id,
                    symbol,
                    side,
                    order_type,
                    timestamp,
                    quantity,
                    price,
                    filled_quantity,
                    filled_price,
                    status,
                    commission,
                    metadata
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            """

            async with self._pool.acquire() as conn:
                await conn.execute(
                    query,
                    order_id,
                    strategy_id,
                    symbol,
                    side,
                    order_type,
                    timestamp_dt,
                    quantity,
                    price,
                    0.0,  # filled_quantity (initially 0)
                    None,  # filled_price (null until filled)
                    status,
                    0.0,  # commission (0 initially)
                    metadata_json
                )

            if self.logger:
                self.logger.debug("trading_persistence.order_created_saved", {
                    "order_id": order_id,
                    "symbol": symbol,
                    "side": side,
                    "quantity": quantity
                })

        except Exception as e:
            if self.logger:
                self.logger.error("trading_persistence.order_create_save_failed", {
                    "order_data": data,
                    "error": str(e),
                    "error_type": type(e).__name__
                })

    async def _on_order_filled(self, data: Dict[str, Any]) -> None:
        """
        Handle order_filled event and update orders table.

        Event data format:
        {
            "order_id": "order_123",
            "filled_quantity": 0.001,
            "filled_price": 50025.5,
            "commission": 0.05,
            "status": "FILLED"  # or PARTIALLY_FILLED
        }
        """
        try:
            order_id = data.get("order_id", "unknown")
            filled_quantity = float(data.get("filled_quantity", 0))
            filled_price = float(data.get("filled_price", 0))
            commission = float(data.get("commission", 0))
            status = data.get("status", "FILLED").upper()

            # Update orders table
            query = """
                UPDATE orders
                SET filled_quantity = $2,
                    filled_price = $3,
                    status = $4,
                    commission = $5
                WHERE order_id = $1
            """

            async with self._pool.acquire() as conn:
                result = await conn.execute(
                    query,
                    order_id,
                    filled_quantity,
                    filled_price,
                    status,
                    commission
                )

            if self.logger:
                self.logger.debug("trading_persistence.order_filled_updated", {
                    "order_id": order_id,
                    "filled_quantity": filled_quantity,
                    "filled_price": filled_price,
                    "status": status
                })

        except Exception as e:
            if self.logger:
                self.logger.error("trading_persistence.order_fill_update_failed", {
                    "order_data": data,
                    "error": str(e),
                    "error_type": type(e).__name__
                })

    async def _on_order_cancelled(self, data: Dict[str, Any]) -> None:
        """Handle order_cancelled event and update orders table."""
        try:
            order_id = data.get("order_id", "unknown")

            query = """
                UPDATE orders
                SET status = 'CANCELLED'
                WHERE order_id = $1
            """

            async with self._pool.acquire() as conn:
                await conn.execute(query, order_id)

            if self.logger:
                self.logger.debug("trading_persistence.order_cancelled_updated", {
                    "order_id": order_id
                })

        except Exception as e:
            if self.logger:
                self.logger.error("trading_persistence.order_cancel_update_failed", {
                    "order_data": data,
                    "error": str(e),
                    "error_type": type(e).__name__
                })

    # ========================================================================
    # Event Handlers - Position Persistence
    # ========================================================================

    async def _on_position_opened(self, data: Dict[str, Any]) -> None:
        """
        Handle position_opened event and persist to positions table.

        Event data format:
        {
            "position_id": "pos_123",
            "strategy_id": "strategy_uuid",
            "symbol": "BTC_USDT",
            "side": "LONG",  # LONG or SHORT
            "quantity": 0.001,
            "entry_price": 50000.0,
            "stop_loss": 49000.0,
            "take_profit": 52000.0,
            "metadata": {...}
        }
        """
        try:
            position_id = data.get("position_id", "unknown")
            strategy_id = data.get("strategy_id", "unknown")
            symbol = data.get("symbol", "").upper()
            side = data.get("side", "LONG").upper()
            timestamp = data.get("timestamp", time.time())
            quantity = float(data.get("quantity", 0))
            entry_price = float(data.get("entry_price", 0))
            current_price = float(data.get("current_price", entry_price))
            stop_loss = float(data.get("stop_loss", 0)) if data.get("stop_loss") else None
            take_profit = float(data.get("take_profit", 0)) if data.get("take_profit") else None
            status = "OPEN"
            metadata = data.get("metadata", {})

            # Convert timestamp
            if isinstance(timestamp, (int, float)):
                timestamp_dt = datetime.fromtimestamp(timestamp)
            else:
                timestamp_dt = timestamp

            metadata_json = json.dumps(metadata) if metadata else None

            # Insert into positions table
            query = """
                INSERT INTO positions (
                    position_id,
                    strategy_id,
                    symbol,
                    timestamp,
                    side,
                    quantity,
                    entry_price,
                    current_price,
                    unrealized_pnl,
                    realized_pnl,
                    stop_loss,
                    take_profit,
                    status,
                    metadata
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            """

            async with self._pool.acquire() as conn:
                await conn.execute(
                    query,
                    position_id,
                    strategy_id,
                    symbol,
                    timestamp_dt,
                    side,
                    quantity,
                    entry_price,
                    current_price,
                    0.0,  # unrealized_pnl (initially 0)
                    0.0,  # realized_pnl (0 until closed)
                    stop_loss,
                    take_profit,
                    status,
                    metadata_json
                )

            if self.logger:
                self.logger.debug("trading_persistence.position_opened_saved", {
                    "position_id": position_id,
                    "symbol": symbol,
                    "side": side,
                    "quantity": quantity
                })

        except Exception as e:
            if self.logger:
                self.logger.error("trading_persistence.position_open_save_failed", {
                    "position_data": data,
                    "error": str(e),
                    "error_type": type(e).__name__
                })

    async def _on_position_updated(self, data: Dict[str, Any]) -> None:
        """
        Handle position_updated event and persist to positions table.

        FIX (Agent 4): Support both INSERT (status="opened") and UPDATE (status="updated").
        PositionSyncService emits position_updated with status="opened" for new positions,
        so we need to INSERT first, then UPDATE on subsequent updates.
        """
        try:
            position_id = data.get("position_id", "unknown")
            symbol = data.get("symbol", "").upper()
            status_value = data.get("status", "updated").lower()  # "opened", "updated", "liquidated", "closed"
            side = data.get("side", "LONG").upper()
            quantity = float(data.get("quantity", 0))
            entry_price = float(data.get("entry_price", 0))
            current_price = float(data.get("current_price", 0))
            unrealized_pnl = float(data.get("unrealized_pnl", 0))
            margin_ratio = float(data.get("margin_ratio", 0))
            liquidation_price = float(data.get("liquidation_price", 0))
            timestamp = data.get("timestamp", time.time())

            # Convert timestamp to datetime
            if isinstance(timestamp, (int, float)):
                # Handle milliseconds
                if timestamp > 1e12:  # Milliseconds
                    timestamp = timestamp / 1000.0
                timestamp_dt = datetime.fromtimestamp(timestamp)
            else:
                timestamp_dt = timestamp

            async with self._pool.acquire() as conn:
                if status_value == "opened":
                    # INSERT new position (first time we see it)
                    query = """
                        INSERT INTO positions (
                            position_id,
                            strategy_id,
                            symbol,
                            timestamp,
                            side,
                            quantity,
                            entry_price,
                            current_price,
                            unrealized_pnl,
                            realized_pnl,
                            stop_loss,
                            take_profit,
                            status,
                            metadata
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                    """
                    await conn.execute(
                        query,
                        position_id,
                        "live_trading",  # Default strategy_id
                        symbol,
                        timestamp_dt,
                        side,
                        quantity,
                        entry_price,
                        current_price,
                        unrealized_pnl,
                        0.0,  # realized_pnl (0 until closed)
                        None,  # stop_loss (not tracked by PositionSyncService)
                        None,  # take_profit (not tracked by PositionSyncService)
                        "OPEN",  # status
                        None  # metadata
                    )

                    if self.logger:
                        self.logger.debug("trading_persistence.position_inserted", {
                            "position_id": position_id,
                            "symbol": symbol,
                            "side": side,
                            "quantity": quantity
                        })

                elif status_value == "liquidated":
                    # UPDATE to liquidated status
                    query = """
                        UPDATE positions
                        SET current_price = $2,
                            unrealized_pnl = 0.0,
                            status = 'LIQUIDATED',
                            quantity = 0.0
                        WHERE position_id = $1
                    """
                    await conn.execute(query, position_id, current_price)

                    if self.logger:
                        self.logger.warning("trading_persistence.position_liquidated", {
                            "position_id": position_id,
                            "liquidation_price": current_price
                        })

                elif status_value == "closed":
                    # UPDATE to closed status (handled by _on_position_closed, but support here too)
                    realized_pnl = float(data.get("realized_pnl", unrealized_pnl))
                    query = """
                        UPDATE positions
                        SET current_price = $2,
                            unrealized_pnl = 0.0,
                            realized_pnl = $3,
                            status = 'CLOSED',
                            quantity = 0.0
                        WHERE position_id = $1
                    """
                    await conn.execute(query, position_id, current_price, realized_pnl)

                    if self.logger:
                        self.logger.debug("trading_persistence.position_closed_via_updated", {
                            "position_id": position_id,
                            "realized_pnl": realized_pnl
                        })
                else:
                    # UPDATE existing position (price/PnL/quantity changes)
                    query = """
                        UPDATE positions
                        SET current_price = $2,
                            unrealized_pnl = $3,
                            quantity = $4
                        WHERE position_id = $1
                    """
                    await conn.execute(query, position_id, current_price, unrealized_pnl, quantity)

                    if self.logger:
                        self.logger.debug("trading_persistence.position_updated", {
                            "position_id": position_id,
                            "current_price": current_price,
                            "unrealized_pnl": unrealized_pnl,
                            "quantity": quantity
                        })

        except Exception as e:
            if self.logger:
                self.logger.error("trading_persistence.position_update_failed", {
                    "position_data": data,
                    "error": str(e),
                    "error_type": type(e).__name__
                })

    async def _on_position_closed(self, data: Dict[str, Any]) -> None:
        """Handle position_closed event and update positions table (final PnL)."""
        try:
            position_id = data.get("position_id", "unknown")
            current_price = float(data.get("current_price", 0))
            realized_pnl = float(data.get("realized_pnl", 0))
            status = "CLOSED"

            query = """
                UPDATE positions
                SET current_price = $2,
                    unrealized_pnl = 0.0,
                    realized_pnl = $3,
                    status = $4
                WHERE position_id = $1
            """

            async with self._pool.acquire() as conn:
                await conn.execute(query, position_id, current_price, realized_pnl, status)

            if self.logger:
                self.logger.debug("trading_persistence.position_closed_updated", {
                    "position_id": position_id,
                    "realized_pnl": realized_pnl
                })

        except Exception as e:
            if self.logger:
                self.logger.error("trading_persistence.position_close_update_failed", {
                    "position_data": data,
                    "error": str(e),
                    "error_type": type(e).__name__
                })
