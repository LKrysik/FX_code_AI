-- Migration 016: Live Trading Tables
-- =================================================
-- Creates tables for live trading orders, positions, and signal history.
--
-- Tables:
-- - live_orders: Order tracking with exchange IDs and fill status
-- - live_positions: Position snapshots and real-time tracking
-- - signal_history: Signal audit trail for compliance and analysis
--
-- Dependencies: Migration 015 (risk_events)
-- Author: Claude (Agent 3 - Phase 2)
-- Date: 2025-11-07

-- ========================================
-- 1. Live Orders Table
-- ========================================
-- Tracks all orders submitted to MEXC exchange
CREATE TABLE IF NOT EXISTS live_orders (
    session_id SYMBOL,
    order_id STRING,
    exchange_order_id STRING,
    symbol SYMBOL,
    side STRING,  -- BUY, SELL
    order_type STRING,  -- MARKET, LIMIT
    quantity DOUBLE,
    requested_price DOUBLE,
    filled_quantity DOUBLE,
    average_fill_price DOUBLE,
    status STRING,  -- PENDING, SUBMITTED, FILLED, PARTIALLY_FILLED, CANCELLED, FAILED
    error_message STRING,
    slippage DOUBLE,
    commission DOUBLE,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    filled_at TIMESTAMP
) timestamp(created_at) PARTITION BY DAY WAL;

-- Indexes for fast order lookups
CREATE INDEX IF NOT EXISTS idx_live_orders_order_id ON live_orders (order_id);
CREATE INDEX IF NOT EXISTS idx_live_orders_exchange_id ON live_orders (exchange_order_id);
CREATE INDEX IF NOT EXISTS idx_live_orders_symbol ON live_orders (symbol);
CREATE INDEX IF NOT EXISTS idx_live_orders_status ON live_orders (status);
CREATE INDEX IF NOT EXISTS idx_live_orders_session ON live_orders (session_id);

-- ========================================
-- 2. Live Positions Table
-- ========================================
-- Real-time position snapshots from MEXC
CREATE TABLE IF NOT EXISTS live_positions (
    session_id SYMBOL,
    symbol SYMBOL,
    side STRING,  -- LONG, SHORT
    quantity DOUBLE,
    entry_price DOUBLE,
    current_price DOUBLE,
    liquidation_price DOUBLE,
    unrealized_pnl DOUBLE,
    unrealized_pnl_pct DOUBLE,
    margin DOUBLE,
    leverage DOUBLE,
    margin_ratio DOUBLE,  -- equity / maintenance_margin (%)
    opened_at TIMESTAMP,
    updated_at TIMESTAMP,
    closed_at TIMESTAMP,
    status STRING  -- OPEN, CLOSED, LIQUIDATED
) timestamp(updated_at) PARTITION BY DAY WAL;

-- Indexes for position queries
CREATE INDEX IF NOT EXISTS idx_live_positions_symbol ON live_positions (symbol);
CREATE INDEX IF NOT EXISTS idx_live_positions_status ON live_positions (status);
CREATE INDEX IF NOT EXISTS idx_live_positions_session ON live_positions (session_id);

-- ========================================
-- 3. Signal History Table
-- ========================================
-- Audit trail of all trading signals generated
CREATE TABLE IF NOT EXISTS signal_history (
    session_id SYMBOL,
    signal_id STRING,
    signal_type STRING,  -- S1, Z1, ZE1, E1
    symbol SYMBOL,
    side STRING,  -- BUY, SELL
    quantity DOUBLE,
    price DOUBLE,
    confidence DOUBLE,
    strategy_name STRING,
    indicator_values STRING,  -- JSON string
    risk_score DOUBLE,
    approved BOOLEAN,  -- Risk manager approval
    rejection_reason STRING,
    order_id STRING,  -- Linked order ID (if created)
    created_at TIMESTAMP
) timestamp(created_at) PARTITION BY DAY WAL;

-- Indexes for signal queries
CREATE INDEX IF NOT EXISTS idx_signal_history_signal_id ON signal_history (signal_id);
CREATE INDEX IF NOT EXISTS idx_signal_history_symbol ON signal_history (symbol);
CREATE INDEX IF NOT EXISTS idx_signal_history_signal_type ON signal_history (signal_type);
CREATE INDEX IF NOT EXISTS idx_signal_history_session ON signal_history (session_id);
CREATE INDEX IF NOT EXISTS idx_signal_history_approved ON signal_history (approved);

-- ========================================
-- 4. Comments and Metadata
-- ========================================
COMMENT ON TABLE live_orders IS 'Live trading orders submitted to MEXC exchange';
COMMENT ON TABLE live_positions IS 'Real-time position snapshots from MEXC';
COMMENT ON TABLE signal_history IS 'Audit trail of all trading signals (compliance and analysis)';

-- ========================================
-- Migration Complete
-- ========================================
-- Tables created:
-- ✓ live_orders - Order tracking with exchange IDs and fill status
-- ✓ live_positions - Real-time position snapshots with margin ratio
-- ✓ signal_history - Signal audit trail for compliance

-- Features:
-- - Full order lifecycle tracking (pending → submitted → filled/cancelled)
-- - Position sync with MEXC (detect liquidations)
-- - Signal approval tracking (risk manager validation)
-- - Comprehensive indexing for fast queries
-- - Partitioned by DAY for optimal query performance
-- - WAL enabled for durability
