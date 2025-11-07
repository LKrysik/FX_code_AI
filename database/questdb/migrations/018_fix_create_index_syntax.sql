-- Migration 018: Fix CREATE INDEX syntax errors
-- =================================================
-- Issue: Migrations 013, 015, 016 use "CREATE INDEX" syntax
--        QuestDB does NOT support CREATE INDEX statements
--
-- Resolution: Use ALTER TABLE ... ALTER COLUMN ... ADD INDEX
--
-- QuestDB Indexing Rules:
-- 1. SYMBOL columns are AUTOMATICALLY indexed (no action needed)
-- 2. STRING columns can be indexed using ALTER TABLE
-- 3. Other types (INT, DOUBLE, BOOLEAN, TIMESTAMP) cannot be indexed
--
-- Evidence:
-- - 013_create_paper_trading_tables.sql (lines 47-49, 76-78, 101-102, 136)
-- - 015_risk_events.sql (lines 22-25)
-- - 016_live_trading.sql (lines 39-43, 69-71, 96-100)
-- =================================================

-- ========================================
-- Fix Migration 013: Paper Trading Tables
-- ========================================

-- paper_trading_sessions
-- session_id: STRING → add index
-- strategy_id: STRING → add index
-- status: STRING → add index
ALTER TABLE paper_trading_sessions ALTER COLUMN session_id ADD INDEX;
ALTER TABLE paper_trading_sessions ALTER COLUMN strategy_id ADD INDEX;
ALTER TABLE paper_trading_sessions ALTER COLUMN status ADD INDEX;

-- paper_trading_orders
-- session_id: SYMBOL → already indexed (skip)
-- order_id: STRING → add index
-- symbol: SYMBOL → already indexed (skip)
ALTER TABLE paper_trading_orders ALTER COLUMN order_id ADD INDEX;

-- paper_trading_positions
-- session_id: SYMBOL → already indexed (skip)
-- symbol: SYMBOL → already indexed (skip)
-- No STRING columns needing indexes

-- paper_trading_performance
-- session_id: SYMBOL → already indexed (skip)
-- No STRING columns needing indexes

-- ========================================
-- Fix Migration 015: Risk Events
-- ========================================

-- risk_events
-- alert_id: STRING → add index
-- session_id: STRING → add index
-- severity: STRING → add index (limited values: CRITICAL, WARNING, INFO)
-- alert_type: STRING → add index
ALTER TABLE risk_events ALTER COLUMN alert_id ADD INDEX;
ALTER TABLE risk_events ALTER COLUMN session_id ADD INDEX;
ALTER TABLE risk_events ALTER COLUMN severity ADD INDEX;
ALTER TABLE risk_events ALTER COLUMN alert_type ADD INDEX;

-- ========================================
-- Fix Migration 016: Live Trading
-- ========================================

-- live_orders
-- order_id: STRING → add index
-- exchange_order_id: STRING → add index
-- session_id: STRING → add index
-- symbol: SYMBOL → already indexed (skip)
-- side: STRING → add index (limited values: BUY, SELL)
-- status: STRING → add index (limited values: PENDING, FILLED, etc.)
ALTER TABLE live_orders ALTER COLUMN order_id ADD INDEX;
ALTER TABLE live_orders ALTER COLUMN exchange_order_id ADD INDEX;
ALTER TABLE live_orders ALTER COLUMN session_id ADD INDEX;
ALTER TABLE live_orders ALTER COLUMN side ADD INDEX;
ALTER TABLE live_orders ALTER COLUMN status ADD INDEX;

-- live_positions
-- position_id: STRING → add index
-- session_id: STRING → add index
-- symbol: SYMBOL → already indexed (skip)
-- status: STRING → add index
ALTER TABLE live_positions ALTER COLUMN position_id ADD INDEX;
ALTER TABLE live_positions ALTER COLUMN session_id ADD INDEX;
ALTER TABLE live_positions ALTER COLUMN status ADD INDEX;

-- signal_history
-- signal_id: STRING → add index
-- session_id: STRING → add index
-- symbol: SYMBOL → already indexed (skip)
-- signal_type: STRING → add index (limited values: S1, Z1, ZE1, E1)
-- strategy_id: STRING → add index
-- created_by: STRING → add index
ALTER TABLE signal_history ALTER COLUMN signal_id ADD INDEX;
ALTER TABLE signal_history ALTER COLUMN session_id ADD INDEX;
ALTER TABLE signal_history ALTER COLUMN signal_type ADD INDEX;
ALTER TABLE signal_history ALTER COLUMN strategy_id ADD INDEX;
ALTER TABLE signal_history ALTER COLUMN created_by ADD INDEX;

-- ========================================
-- Verification
-- ========================================
-- After running this migration, verify indexes were created:
-- SELECT * FROM tables() WHERE name = 'paper_trading_sessions';
-- Check columns metadata to see which have indexes
-- ========================================
