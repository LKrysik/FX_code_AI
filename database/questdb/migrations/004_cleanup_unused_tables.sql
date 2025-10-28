-- Migration 004: Cleanup Unused Tables and Add Missing Indexes
-- Date: 2025-10-28
-- Description: Remove unused strategy_templates table, add session_id indexes

-- ============================================================================
-- PART 1: Remove unused strategy_templates table
-- ============================================================================
-- Rationale: Grep analysis shows zero usage in codebase
-- StrategyBlueprintsAPI removed, StrategyStorage uses file-based persistence
-- This table was never integrated with any system

DROP TABLE IF EXISTS strategy_templates;

-- ============================================================================
-- PART 2: Add missing indexes for session_id columns
-- ============================================================================
-- Rationale: session_id added in migration 003 but indexes only for indicators
-- tick_prices and tick_orderbook queries by session_id are slow without indexes

-- Index for tick_prices.session_id (enables fast session-based queries)
CREATE INDEX IF NOT EXISTS idx_tick_prices_session ON tick_prices(session_id);

-- Index for tick_orderbook.session_id (enables fast session-based queries)
CREATE INDEX IF NOT EXISTS idx_tick_orderbook_session ON tick_orderbook(session_id);

-- ============================================================================
-- VERIFICATION NOTES:
-- After running this migration:
-- 1. Verify indexes: SELECT * FROM tables() WHERE name IN ('tick_prices', 'tick_orderbook');
-- 2. Check query performance: EXPLAIN SELECT * FROM tick_prices WHERE session_id = 'test';
-- 3. Confirm strategy_templates dropped: SELECT * FROM tables() WHERE name = 'strategy_templates';
-- ============================================================================
