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
-- PART 2: Indexes for session_id columns
-- ============================================================================
-- session_id is defined as SYMBOL type in tick_prices and tick_orderbook tables.
-- SYMBOL columns are automatically indexed in QuestDB (via CACHE keyword).
-- No additional CREATE INDEX statements needed.
--
-- Verification:
-- - tick_prices.session_id: SYMBOL capacity 2048 CACHE (auto-indexed)
-- - tick_orderbook.session_id: SYMBOL capacity 2048 CACHE (auto-indexed)

-- ============================================================================
-- VERIFICATION NOTES:
-- After running this migration:
-- 1. Verify indexes: SELECT * FROM tables() WHERE name IN ('tick_prices', 'tick_orderbook');
-- 2. Check query performance: EXPLAIN SELECT * FROM tick_prices WHERE session_id = 'test';
-- 3. Confirm strategy_templates dropped: SELECT * FROM tables() WHERE name = 'strategy_templates';
-- ============================================================================
