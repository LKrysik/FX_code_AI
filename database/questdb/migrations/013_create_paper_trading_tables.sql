-- Migration 013: Paper Trading Tables
-- =================================================
-- Creates tables for paper trading sessions, orders, positions, and performance tracking.
--
-- Tables:
-- - paper_trading_sessions: Session metadata and final results
-- - paper_trading_orders: Individual order records
-- - paper_trading_positions: Position snapshots over time
-- - paper_trading_performance: Performance metrics snapshots
--
-- Dependencies: None
-- Author: Claude (TIER 1.2)
-- Date: 2025-11-04

-- ========================================
-- 1. Paper Trading Sessions
-- ========================================
-- Tracks complete paper trading sessions with metadata and final results
CREATE TABLE IF NOT EXISTS paper_trading_sessions (
    session_id STRING,
    strategy_id STRING,
    strategy_name STRING,
    symbols STRING,  -- Comma-separated list of symbols
    direction STRING,  -- LONG, SHORT, or BOTH
    leverage DOUBLE,
    initial_balance DOUBLE,
    final_balance DOUBLE,
    total_pnl DOUBLE,
    total_return_pct DOUBLE,
    total_trades INT,
    winning_trades INT,
    losing_trades INT,
    win_rate DOUBLE,
    profit_factor DOUBLE,
    max_drawdown DOUBLE,
    sharpe_ratio DOUBLE,
    sortino_ratio DOUBLE,
    status STRING,  -- RUNNING, COMPLETED, STOPPED, ERROR
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    duration_seconds INT,
    created_by STRING,
    notes STRING
) timestamp(start_time) PARTITION BY DAY WAL;

-- Index for fast session lookups
CREATE INDEX IF NOT EXISTS idx_paper_sessions_id ON paper_trading_sessions (session_id);
CREATE INDEX IF NOT EXISTS idx_paper_sessions_strategy ON paper_trading_sessions (strategy_id);
CREATE INDEX IF NOT EXISTS idx_paper_sessions_status ON paper_trading_sessions (status);

-- ========================================
-- 2. Paper Trading Orders
-- ========================================
-- Records all orders placed during paper trading sessions
CREATE TABLE IF NOT EXISTS paper_trading_orders (
    session_id SYMBOL,
    order_id STRING,
    symbol SYMBOL,
    side STRING,  -- BUY, SELL
    position_side STRING,  -- LONG, SHORT
    order_type STRING,  -- MARKET, LIMIT
    quantity DOUBLE,
    requested_price DOUBLE,
    execution_price DOUBLE,
    slippage_pct DOUBLE,
    leverage DOUBLE,
    liquidation_price DOUBLE,
    status STRING,  -- FILLED, CANCELLED, REJECTED
    commission DOUBLE,
    realized_pnl DOUBLE,  -- P&L realized by this order (for closing orders)
    strategy_signal STRING,  -- Which strategy section triggered this (S1, Z1, ZE1, E1)
    timestamp TIMESTAMP
) timestamp(timestamp) PARTITION BY DAY WAL;

-- Indexes for order queries
CREATE INDEX IF NOT EXISTS idx_paper_orders_session ON paper_trading_orders (session_id);
CREATE INDEX IF NOT EXISTS idx_paper_orders_order_id ON paper_trading_orders (order_id);
CREATE INDEX IF NOT EXISTS idx_paper_orders_symbol ON paper_trading_orders (symbol);

-- ========================================
-- 3. Paper Trading Positions
-- ========================================
-- Snapshots of positions over time (updated periodically and on position changes)
CREATE TABLE IF NOT EXISTS paper_trading_positions (
    session_id SYMBOL,
    symbol SYMBOL,
    position_side STRING,  -- LONG, SHORT
    position_amount DOUBLE,
    entry_price DOUBLE,
    current_price DOUBLE,
    leverage DOUBLE,
    liquidation_price DOUBLE,
    unrealized_pnl DOUBLE,
    unrealized_pnl_pct DOUBLE,
    margin_used DOUBLE,
    funding_cost_accrued DOUBLE,  -- Cumulative funding cost
    timestamp TIMESTAMP
) timestamp(timestamp) PARTITION BY DAY WAL;

-- Indexes for position queries
CREATE INDEX IF NOT EXISTS idx_paper_positions_session ON paper_trading_positions (session_id);
CREATE INDEX IF NOT EXISTS idx_paper_positions_symbol ON paper_trading_positions (symbol);

-- ========================================
-- 4. Paper Trading Performance
-- ========================================
-- Performance metrics snapshots over time (updated every N minutes)
CREATE TABLE IF NOT EXISTS paper_trading_performance (
    session_id SYMBOL,
    current_balance DOUBLE,
    total_pnl DOUBLE,
    total_return_pct DOUBLE,
    unrealized_pnl DOUBLE,
    realized_pnl DOUBLE,
    total_trades INT,
    winning_trades INT,
    losing_trades INT,
    win_rate DOUBLE,
    profit_factor DOUBLE,
    average_win DOUBLE,
    average_loss DOUBLE,
    largest_win DOUBLE,
    largest_loss DOUBLE,
    max_drawdown DOUBLE,
    current_drawdown DOUBLE,
    sharpe_ratio DOUBLE,
    sortino_ratio DOUBLE,
    calmar_ratio DOUBLE,
    open_positions INT,
    total_commission DOUBLE,
    total_funding_cost DOUBLE,
    timestamp TIMESTAMP
) timestamp(timestamp) PARTITION BY DAY WAL;

-- Index for performance queries
CREATE INDEX IF NOT EXISTS idx_paper_performance_session ON paper_trading_performance (session_id);

-- ========================================
-- 5. Comments and Metadata
-- ========================================
COMMENT ON TABLE paper_trading_sessions IS 'Paper trading sessions with final results and metadata';
COMMENT ON TABLE paper_trading_orders IS 'Individual orders placed during paper trading';
COMMENT ON TABLE paper_trading_positions IS 'Position snapshots over time for paper trading';
COMMENT ON TABLE paper_trading_performance IS 'Performance metrics snapshots during paper trading';

-- ========================================
-- Migration Complete
-- ========================================
-- Tables created:
-- ✓ paper_trading_sessions - Session tracking with final results
-- ✓ paper_trading_orders - Order history with slippage and P&L
-- ✓ paper_trading_positions - Position snapshots for monitoring
-- ✓ paper_trading_performance - Performance metrics over time
--
-- Features:
-- - Full leverage and SHORT position support
-- - Slippage tracking
-- - Funding cost tracking
-- - Real-time performance metrics
-- - Comprehensive trade history
-- - Session-based organization
