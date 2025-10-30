-- ============================================================================
-- Migration 009: Recreate Indicators Table with Correct Schema
-- ============================================================================
-- Date: 2025-10-30
-- Purpose: Fix indicators table schema conflicts and ensure ILP compatibility
--
-- PROBLEMS FIXED:
-- 1. Migration 003 and 005 both tried to ADD session_id (conflict)
-- 2. session_id capacity mismatch (2048 vs 512)
-- 3. Extra columns (scope, user_id, created_by) not used in ILP writes
-- 4. ILP requires all SYMBOL fields defined in CREATE TABLE
--
-- SOLUTION:
-- - DROP and RECREATE indicators table with clean schema
-- - All required SYMBOL fields in CREATE TABLE (no ALTER TABLE ADD)
-- - Only columns actually used by the application
-- - No backward compatibility - clean slate
--
-- ============================================================================

-- Drop existing table (NO backward compatibility)
DROP TABLE IF EXISTS indicators;

-- Create indicators table with final schema
CREATE TABLE indicators (
    -- SYMBOL fields (must be in CREATE TABLE for ILP)
    session_id SYMBOL capacity 2048 CACHE,   -- REQUIRED: Links to data_collection_sessions
    symbol SYMBOL capacity 256 CACHE,        -- REQUIRED: Trading pair (BTC_USDT, ETH_USDT, etc.)
    indicator_id SYMBOL capacity 2048 CACHE, -- REQUIRED: Indicator variant ID

    -- Timestamp (designated timestamp column)
    timestamp TIMESTAMP,                     -- REQUIRED: Calculation timestamp

    -- Data columns
    value DOUBLE,                            -- REQUIRED: Indicator value
    confidence DOUBLE,                       -- OPTIONAL: Confidence score (0-1)
    metadata STRING                          -- OPTIONAL: JSON metadata

) timestamp(timestamp) PARTITION BY DAY WAL
DEDUP UPSERT KEYS(timestamp, session_id, symbol, indicator_id);

-- Create indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_indicators_session ON indicators(session_id);
CREATE INDEX IF NOT EXISTS idx_indicators_symbol ON indicators(symbol);

-- ============================================================================
-- SCHEMA NOTES
-- ============================================================================
--
-- SYMBOL columns (indexed, cached, efficient):
-- - session_id: REQUIRED (no NULL values allowed in application logic)
-- - symbol: REQUIRED
-- - indicator_id: REQUIRED
--
-- Data columns:
-- - value: REQUIRED (float)
-- - confidence: OPTIONAL (may be NULL)
-- - metadata: OPTIONAL (JSON string)
--
-- ILP Insert Format:
-- ```python
-- sender.row(
--     'indicators',
--     symbols={
--         'session_id': 'exec_20251029_224721_c27a2c23',
--         'symbol': 'AEVO_USDT',
--         'indicator_id': 'twpa_300_0'
--     },
--     columns={
--         'value': 123.45,
--         'confidence': 0.95,  # optional
--         'metadata': '{"source": "streaming"}'  # optional
--     },
--     at=TimestampNanos(timestamp_ns)
-- )
-- ```
--
-- Deduplication:
-- - UPSERT on (timestamp, session_id, symbol, indicator_id)
-- - Prevents duplicate inserts if recalculation happens
--
-- Partitioning:
-- - BY DAY for automatic cleanup (DROP PARTITION WHERE timestamp < X)
-- - WAL enabled for durability and crash recovery
--
-- ============================================================================
-- QUERY EXAMPLES
-- ============================================================================
--
-- Get all indicators for a session:
-- SELECT * FROM indicators
-- WHERE session_id = 'exec_20251029_224721_c27a2c23'
-- ORDER BY timestamp DESC;
--
-- Get specific indicator history:
-- SELECT timestamp, value
-- FROM indicators
-- WHERE session_id = 'exec_20251029_224721_c27a2c23'
--   AND symbol = 'AEVO_USDT'
--   AND indicator_id = 'twpa_300_0'
-- ORDER BY timestamp ASC;
--
-- Get latest indicator values:
-- SELECT symbol, indicator_id, value, timestamp
-- FROM indicators
-- WHERE session_id = 'exec_20251029_224721_c27a2c23'
-- LATEST BY symbol, indicator_id;
--
-- Count indicators per session:
-- SELECT session_id, symbol, indicator_id, COUNT(*) as count
-- FROM indicators
-- GROUP BY session_id, symbol, indicator_id;
--
-- ============================================================================
-- MIGRATION NOTES
-- ============================================================================
--
-- This migration:
-- - DROPS all existing indicator data
-- - NO backward compatibility
-- - Clean slate for correct architecture
--
-- After running this migration:
-- - All previous indicator data is LOST
-- - Users must recalculate indicators
-- - This is INTENTIONAL - old data had incorrect schema
--
-- ============================================================================
