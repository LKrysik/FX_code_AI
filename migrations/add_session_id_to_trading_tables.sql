-- Migration: Add session_id to trading persistence tables
-- Date: 2025-12-17
-- Purpose: Enable session separation for backtests, live, and paper trading
-- Related: AUDIT_FINAL_REPORT.md - Issue #2

-- ============================================================================
-- Add session_id column to strategy_signals
-- ============================================================================
ALTER TABLE strategy_signals ADD COLUMN session_id SYMBOL;

-- Create index for faster session-based queries
CREATE INDEX IF NOT EXISTS idx_strategy_signals_session_id ON strategy_signals(session_id);

-- ============================================================================
-- Add session_id column to orders
-- ============================================================================
ALTER TABLE orders ADD COLUMN session_id SYMBOL;

-- Create index for faster session-based queries
CREATE INDEX IF NOT EXISTS idx_orders_session_id ON orders(session_id);

-- ============================================================================
-- Add session_id column to positions
-- ============================================================================
ALTER TABLE positions ADD COLUMN session_id SYMBOL;

-- Create index for faster session-based queries
CREATE INDEX IF NOT EXISTS idx_positions_session_id ON positions(session_id);

-- ============================================================================
-- Verification Queries
-- ============================================================================
-- Run these to verify migration success:
-- SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'strategy_signals';
-- SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'orders';
-- SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'positions';
