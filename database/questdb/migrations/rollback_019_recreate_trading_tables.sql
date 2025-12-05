-- ============================================================================
-- Migration 019 ROLLBACK: Drop Trading Tables
-- Date: 2025-11-08
-- Purpose: Rollback migration 019 if needed
--
-- WARNING: This will delete ALL trading data (signals, orders, positions)
-- Backup data before running this rollback if needed
--
-- To backup data before rollback:
--   1. Export strategy_signals: COPY strategy_signals TO '/path/to/backup/strategy_signals.csv';
--   2. Export orders: COPY orders TO '/path/to/backup/orders.csv';
--   3. Export positions: COPY positions TO '/path/to/backup/positions.csv';
--
-- To rollback:
--   1. Run this script via QuestDB Web UI (http://127.0.0.1:9000)
--   2. Or via REST API: curl -G "http://localhost:9000/exec" --data-urlencode "query=$(cat this_file)"
--   3. Or via Python: psycopg2.connect(...).execute(script)
-- ============================================================================


-- Drop strategy_signals table
DROP TABLE IF EXISTS strategy_signals;

-- Drop orders table
DROP TABLE IF EXISTS orders;

-- Drop positions table
DROP TABLE IF EXISTS positions;


-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Verify tables are dropped (should return 0 rows)
SELECT table_name
FROM tables()
WHERE table_name IN ('strategy_signals', 'orders', 'positions');


-- ============================================================================
-- ROLLBACK COMPLETE
-- ============================================================================
-- Summary:
--   ✓ Dropped strategy_signals table
--   ✓ Dropped orders table
--   ✓ Dropped positions table
--
-- Next steps:
--   1. If you need these tables back, re-run migration 019
--   2. If you backed up data, restore from backup
--   3. Update container to not wire TradingPersistenceService
-- ============================================================================
