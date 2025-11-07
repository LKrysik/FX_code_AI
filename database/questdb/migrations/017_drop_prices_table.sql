-- Migration 017: Drop unused 'prices' table
-- =================================================
-- Issue: Migration 001 created 'prices' table (OHLCV format)
--        Migration 003 created 'tick_prices' table (tick format)
--        Both tables exist causing data duplication and confusion
--
-- Resolution: Drop 'prices' table - all code should use 'tick_prices'
--
-- Evidence:
-- - questdb_provider.py writes to both tables (lines 682, 1128)
-- - backtest_data_provider_questdb.py reads from 'prices' (lines 148, 159)
--
-- Impact: Code must be updated to use 'tick_prices' exclusively
--
-- Related Migrations:
-- - 001_create_initial_schema.sql:85 - Created prices table
-- - 003_data_collection_schema.sql:82 - Created tick_prices table
-- =================================================

-- Drop the prices table (replaced by tick_prices)
DROP TABLE IF EXISTS prices;

-- Verification query (should return 0 rows after migration):
-- SELECT COUNT(*) FROM prices;  -- Should error: "Table does not exist"

-- Note: If you need to migrate data from prices to tick_prices before dropping:
-- INSERT INTO tick_prices (session_id, symbol, timestamp, price, volume, quote_volume)
-- SELECT session_id, symbol, timestamp, close AS price, volume, quote_volume FROM prices;
