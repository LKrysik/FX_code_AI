"""
Paper Trading Persistence Service
==================================
QuestDB-based persistence for paper trading sessions, orders, positions, and performance metrics.

Handles:
- Session creation and finalization
- Order recording with slippage tracking
- Position snapshots
- Performance metrics over time
- Query methods for analysis and visualization

Connection Management:
- Uses asyncpg connection pool (configured for 2-10 connections)
- Automatically releases connections after operations
- Thread-safe for concurrent access
"""

from __future__ import annotations

import json
import asyncpg
from typing import Dict, Any, List, Optional
from datetime import datetime
from ...core.logger import StructuredLogger


class PaperTradingPersistenceService:
    """
    Persistence service for paper trading data using QuestDB.

    Manages complete lifecycle of paper trading sessions:
    1. Create session with initial parameters
    2. Record orders as they execute
    3. Snapshot positions periodically
    4. Track performance metrics
    5. Finalize session with results
    """

    def __init__(self,
                 host: str,
                 port: int,
                 user: str,
                 password: str,
                 database: str = "qdb",
                 logger: Optional[StructuredLogger] = None,
                 min_pool_size: int = 2,
                 max_pool_size: int = 10):
        """
        Initialize persistence service.

        Args:
            host: QuestDB host
            port: PostgreSQL wire protocol port (default: 8812)
            user: Database user
            password: Database password
            database: Database name
            logger: Structured logger
            min_pool_size: Minimum connection pool size
            max_pool_size: Maximum connection pool size
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.logger = logger
        self.min_pool_size = min_pool_size
        self.max_pool_size = max_pool_size

        self._pool: Optional[asyncpg.Pool] = None

        if self.logger:
            self.logger.info("paper_trading_persistence.initialized", {
                "host": host,
                "port": port,
                "database": database
            })

    async def initialize(self) -> None:
        """Initialize connection pool."""
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
                self.logger.info("paper_trading_persistence.pool_created", {
                    "min_size": self.min_pool_size,
                    "max_size": self.max_pool_size
                })

    async def close(self) -> None:
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            if self.logger:
                self.logger.info("paper_trading_persistence.pool_closed")

    async def _get_connection(self) -> asyncpg.Connection:
        """Get connection from pool."""
        if not self._pool:
            await self.initialize()
        return await self._pool.acquire()

    async def _release_connection(self, conn: asyncpg.Connection) -> None:
        """Release connection back to pool."""
        if self._pool:
            await self._pool.release(conn)

    # ========================================
    # Session Management
    # ========================================

    async def create_session(self, session_data: Dict[str, Any]) -> str:
        """
        Create new paper trading session.

        Args:
            session_data: Session metadata
                - session_id: Unique session ID
                - strategy_id: Strategy ID
                - strategy_name: Strategy name
                - symbols: List of symbols (will be joined to string)
                - direction: LONG, SHORT, or BOTH
                - leverage: Leverage multiplier
                - initial_balance: Starting balance
                - created_by: User ID

        Returns:
            Session ID
        """
        conn = None
        try:
            session_id = session_data["session_id"]
            strategy_id = session_data.get("strategy_id", "")
            strategy_name = session_data.get("strategy_name", "")
            symbols = session_data.get("symbols", [])
            symbols_str = ",".join(symbols) if isinstance(symbols, list) else symbols
            direction = session_data.get("direction", "BOTH")
            leverage = session_data.get("leverage", 1.0)
            initial_balance = session_data.get("initial_balance", 10000.0)
            created_by = session_data.get("created_by", "system")
            notes = session_data.get("notes", "")

            conn = await self._get_connection()

            query = """
                INSERT INTO paper_trading_sessions (
                    session_id, strategy_id, strategy_name, symbols, direction,
                    leverage, initial_balance, final_balance, total_pnl, total_return_pct,
                    total_trades, winning_trades, losing_trades, win_rate, profit_factor,
                    max_drawdown, sharpe_ratio, sortino_ratio, status, start_time,
                    end_time, duration_seconds, created_by, notes
                ) VALUES (
                    $1, $2, $3, $4, $5,
                    $6, $7, $7, 0, 0,
                    0, 0, 0, 0, 0,
                    0, 0, 0, 'RUNNING', $8,
                    NULL, NULL, $9, $10
                )
            """

            now = datetime.utcnow()
            await conn.execute(
                query,
                session_id, strategy_id, strategy_name, symbols_str, direction,
                leverage, initial_balance, now, created_by, notes
            )

            if self.logger:
                self.logger.info("paper_trading_persistence.session_created", {
                    "session_id": session_id,
                    "strategy_name": strategy_name,
                    "symbols": symbols_str,
                    "initial_balance": initial_balance
                })

            return session_id

        finally:
            if conn:
                await self._release_connection(conn)

    async def update_session_status(self, session_id: str, status: str) -> None:
        """
        Update session status.

        Args:
            session_id: Session ID
            status: New status (RUNNING, COMPLETED, STOPPED, ERROR)
        """
        conn = None
        try:
            conn = await self._get_connection()

            query = """
                UPDATE paper_trading_sessions
                SET status = $2
                WHERE session_id = $1
            """

            await conn.execute(query, session_id, status)

            if self.logger:
                self.logger.info("paper_trading_persistence.session_status_updated", {
                    "session_id": session_id,
                    "status": status
                })

        finally:
            if conn:
                await self._release_connection(conn)

    async def finalize_session(self, session_id: str, final_metrics: Dict[str, Any]) -> None:
        """
        Finalize session with final results.

        Args:
            session_id: Session ID
            final_metrics: Final performance metrics
        """
        conn = None
        try:
            conn = await self._get_connection()

            end_time = datetime.utcnow()

            # Get start time for duration calculation
            start_time_query = "SELECT start_time FROM paper_trading_sessions WHERE session_id = $1"
            start_time_row = await conn.fetchrow(start_time_query, session_id)
            start_time = start_time_row['start_time'] if start_time_row else end_time
            duration_seconds = int((end_time - start_time).total_seconds())

            query = """
                UPDATE paper_trading_sessions
                SET
                    final_balance = $2,
                    total_pnl = $3,
                    total_return_pct = $4,
                    total_trades = $5,
                    winning_trades = $6,
                    losing_trades = $7,
                    win_rate = $8,
                    profit_factor = $9,
                    max_drawdown = $10,
                    sharpe_ratio = $11,
                    sortino_ratio = $12,
                    status = $13,
                    end_time = $14,
                    duration_seconds = $15
                WHERE session_id = $1
            """

            await conn.execute(
                query,
                session_id,
                final_metrics.get("final_balance", 0.0),
                final_metrics.get("total_pnl", 0.0),
                final_metrics.get("total_return_pct", 0.0),
                final_metrics.get("total_trades", 0),
                final_metrics.get("winning_trades", 0),
                final_metrics.get("losing_trades", 0),
                final_metrics.get("win_rate", 0.0),
                final_metrics.get("profit_factor", 0.0),
                final_metrics.get("max_drawdown", 0.0),
                final_metrics.get("sharpe_ratio", 0.0),
                final_metrics.get("sortino_ratio", 0.0),
                "COMPLETED",
                end_time,
                duration_seconds
            )

            if self.logger:
                self.logger.info("paper_trading_persistence.session_finalized", {
                    "session_id": session_id,
                    "total_trades": final_metrics.get("total_trades", 0),
                    "total_return_pct": final_metrics.get("total_return_pct", 0.0)
                })

        finally:
            if conn:
                await self._release_connection(conn)

    # ========================================
    # Order Recording
    # ========================================

    async def record_order(self, session_id: str, order_data: Dict[str, Any]) -> None:
        """
        Record paper trading order.

        Args:
            session_id: Session ID
            order_data: Order details
        """
        conn = None
        try:
            conn = await self._get_connection()

            query = """
                INSERT INTO paper_trading_orders (
                    session_id, order_id, symbol, side, position_side, order_type,
                    quantity, requested_price, execution_price, slippage_pct, leverage,
                    liquidation_price, status, commission, realized_pnl, strategy_signal,
                    timestamp
                ) VALUES (
                    $1, $2, $3, $4, $5, $6,
                    $7, $8, $9, $10, $11,
                    $12, $13, $14, $15, $16,
                    $17
                )
            """

            await conn.execute(
                query,
                session_id,
                order_data.get("order_id"),
                order_data.get("symbol"),
                order_data.get("side"),
                order_data.get("position_side"),
                order_data.get("type", "MARKET"),
                order_data.get("quantity", 0.0),
                order_data.get("requested_price", order_data.get("price", 0.0)),
                order_data.get("price", 0.0),
                order_data.get("slippage_pct", 0.0),
                order_data.get("leverage", 1.0),
                order_data.get("liquidation_price", 0.0),
                order_data.get("status", "FILLED"),
                order_data.get("commission", 0.0),
                order_data.get("realized_pnl", 0.0),
                order_data.get("strategy_signal", ""),
                datetime.utcnow()
            )

            if self.logger:
                self.logger.debug("paper_trading_persistence.order_recorded", {
                    "session_id": session_id,
                    "order_id": order_data.get("order_id"),
                    "symbol": order_data.get("symbol"),
                    "side": order_data.get("side")
                })

        finally:
            if conn:
                await self._release_connection(conn)

    # ========================================
    # Position Snapshots
    # ========================================

    async def snapshot_position(self, session_id: str, position_data: Dict[str, Any]) -> None:
        """
        Record position snapshot.

        Args:
            session_id: Session ID
            position_data: Position details
        """
        conn = None
        try:
            conn = await self._get_connection()

            query = """
                INSERT INTO paper_trading_positions (
                    session_id, symbol, position_side, position_amount, entry_price,
                    current_price, leverage, liquidation_price, unrealized_pnl,
                    unrealized_pnl_pct, margin_used, funding_cost_accrued, timestamp
                ) VALUES (
                    $1, $2, $3, $4, $5,
                    $6, $7, $8, $9,
                    $10, $11, $12, $13
                )
            """

            await conn.execute(
                query,
                session_id,
                position_data.get("symbol"),
                position_data.get("position_side"),
                position_data.get("position_amount", 0.0),
                position_data.get("entry_price", 0.0),
                position_data.get("current_price", 0.0),
                position_data.get("leverage", 1.0),
                position_data.get("liquidation_price", 0.0),
                position_data.get("unrealized_pnl", 0.0),
                position_data.get("unrealized_pnl_pct", 0.0),
                position_data.get("margin_used", 0.0),
                position_data.get("funding_cost_accrued", 0.0),
                datetime.utcnow()
            )

        finally:
            if conn:
                await self._release_connection(conn)

    # ========================================
    # Performance Metrics
    # ========================================

    async def record_performance(self, session_id: str, metrics: Dict[str, Any]) -> None:
        """
        Record performance metrics snapshot.

        Args:
            session_id: Session ID
            metrics: Performance metrics
        """
        conn = None
        try:
            conn = await self._get_connection()

            query = """
                INSERT INTO paper_trading_performance (
                    session_id, current_balance, total_pnl, total_return_pct, unrealized_pnl,
                    realized_pnl, total_trades, winning_trades, losing_trades, win_rate,
                    profit_factor, average_win, average_loss, largest_win, largest_loss,
                    max_drawdown, current_drawdown, sharpe_ratio, sortino_ratio, calmar_ratio,
                    open_positions, total_commission, total_funding_cost, timestamp
                ) VALUES (
                    $1, $2, $3, $4, $5,
                    $6, $7, $8, $9, $10,
                    $11, $12, $13, $14, $15,
                    $16, $17, $18, $19, $20,
                    $21, $22, $23, $24
                )
            """

            await conn.execute(
                query,
                session_id,
                metrics.get("current_balance", 0.0),
                metrics.get("total_pnl", 0.0),
                metrics.get("total_return_pct", 0.0),
                metrics.get("unrealized_pnl", 0.0),
                metrics.get("realized_pnl", 0.0),
                metrics.get("total_trades", 0),
                metrics.get("winning_trades", 0),
                metrics.get("losing_trades", 0),
                metrics.get("win_rate", 0.0),
                metrics.get("profit_factor", 0.0),
                metrics.get("average_win", 0.0),
                metrics.get("average_loss", 0.0),
                metrics.get("largest_win", 0.0),
                metrics.get("largest_loss", 0.0),
                metrics.get("max_drawdown", 0.0),
                metrics.get("current_drawdown", 0.0),
                metrics.get("sharpe_ratio", 0.0),
                metrics.get("sortino_ratio", 0.0),
                metrics.get("calmar_ratio", 0.0),
                metrics.get("open_positions", 0),
                metrics.get("total_commission", 0.0),
                metrics.get("total_funding_cost", 0.0),
                datetime.utcnow()
            )

        finally:
            if conn:
                await self._release_connection(conn)

    # ========================================
    # Query Methods
    # ========================================

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session by ID.

        Args:
            session_id: Session ID

        Returns:
            Session data or None
        """
        conn = None
        try:
            conn = await self._get_connection()

            query = "SELECT * FROM paper_trading_sessions WHERE session_id = $1"
            row = await conn.fetchrow(query, session_id)

            if row:
                return dict(row)
            return None

        finally:
            if conn:
                await self._release_connection(conn)

    async def get_session_orders(self, session_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get orders for session.

        Args:
            session_id: Session ID
            limit: Maximum number of orders

        Returns:
            List of orders
        """
        conn = None
        try:
            conn = await self._get_connection()

            query = """
                SELECT * FROM paper_trading_orders
                WHERE session_id = $1
                ORDER BY timestamp DESC
                LIMIT $2
            """
            rows = await conn.fetch(query, session_id, limit)

            return [dict(row) for row in rows]

        finally:
            if conn:
                await self._release_connection(conn)

    async def get_session_performance(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get performance metrics over time for session.

        Args:
            session_id: Session ID

        Returns:
            List of performance snapshots
        """
        conn = None
        try:
            conn = await self._get_connection()

            query = """
                SELECT * FROM paper_trading_performance
                WHERE session_id = $1
                ORDER BY timestamp ASC
            """
            rows = await conn.fetch(query, session_id)

            return [dict(row) for row in rows]

        finally:
            if conn:
                await self._release_connection(conn)

    async def list_sessions(self,
                           strategy_id: Optional[str] = None,
                           status: Optional[str] = None,
                           limit: int = 50) -> List[Dict[str, Any]]:
        """
        List paper trading sessions with optional filters.

        Args:
            strategy_id: Filter by strategy ID
            status: Filter by status
            limit: Maximum number of sessions

        Returns:
            List of sessions
        """
        conn = None
        try:
            conn = await self._get_connection()

            conditions = []
            params = []
            param_num = 1

            if strategy_id:
                conditions.append(f"strategy_id = ${param_num}")
                params.append(strategy_id)
                param_num += 1

            if status:
                conditions.append(f"status = ${param_num}")
                params.append(status)
                param_num += 1

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            query = f"""
                SELECT * FROM paper_trading_sessions
                WHERE {where_clause}
                ORDER BY start_time DESC
                LIMIT ${param_num}
            """
            params.append(limit)

            rows = await conn.fetch(query, *params)

            return [dict(row) for row in rows]

        finally:
            if conn:
                await self._release_connection(conn)
