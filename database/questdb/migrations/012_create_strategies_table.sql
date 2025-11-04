-- ============================================================================
-- MIGRATION 012: Create strategies table for persistent strategy storage
-- ============================================================================
-- Date: 2025-11-03
-- Purpose: Store active trading strategies with SHORT support
--
-- This table stores ACTIVE strategies (not templates).
-- Templates are in strategy_templates table (for sharing/reuse).
-- Active strategies are user's configured strategies ready for execution.
--
-- Design considerations:
-- 1. JSON storage for flexibility (schema can evolve without migrations)
-- 2. direction field extracted for fast filtering (LONG/SHORT/BOTH)
-- 3. enabled field for quick activation status
-- 4. Relational table (not time-series) - strategies are long-lived
-- ============================================================================

-- Drop existing table if it exists
DROP TABLE IF EXISTS strategies;

-- Create strategies table
CREATE TABLE strategies (
    id STRING,                              -- UUID as string (primary key)
    strategy_name STRING,                   -- Unique strategy name (user-defined)
    description STRING,                     -- Strategy description
    direction STRING,                       -- Trading direction: LONG, SHORT, or BOTH
    enabled BOOLEAN,                        -- Whether strategy is active

    -- Full configuration stored as JSON (flexible schema)
    strategy_json STRING,                   -- Complete strategy config including all sections

    -- Metadata
    author STRING,                          -- Strategy creator (user_id or "system")
    category STRING,                        -- Optional category (trend_following, pump_dump, etc.)
    tags STRING,                            -- Comma-separated tags for search

    -- Template reference (optional - if created from template)
    template_id STRING,                     -- Reference to strategy_templates.id

    -- Runtime state (not persisted from StrategyManager in-memory state)
    -- These are reset on load:
    -- - current_state: Always starts as INACTIVE
    -- - symbol: Empty until activated
    -- - position_active: false

    -- Timestamps
    created_at TIMESTAMP,                   -- Creation timestamp
    updated_at TIMESTAMP,                   -- Last update timestamp
    last_activated_at TIMESTAMP             -- Last time strategy was activated
);

-- ============================================================================
-- INDEXES for fast lookup
-- ============================================================================

-- Index on strategy_name for unique constraint enforcement
ALTER TABLE strategies ALTER COLUMN strategy_name ADD INDEX;

-- Index on direction for filtering LONG/SHORT strategies
ALTER TABLE strategies ALTER COLUMN direction ADD INDEX;

-- Index on enabled for filtering active strategies
ALTER TABLE strategies ALTER COLUMN enabled ADD INDEX;

-- ============================================================================
-- SAMPLE DATA - Example LONG strategy
-- ============================================================================
/*
INSERT INTO strategies VALUES (
    'strat-uuid-long-1',
    'Momentum LONG v1',
    'Simple momentum strategy for LONG positions',
    'LONG',
    true,
    '{
        "strategy_name": "Momentum LONG v1",
        "direction": "LONG",
        "signal_detection_conditions": {
            "price_velocity": {"min": 0.5}
        },
        "entry_conditions": {},
        "global_limits": {
            "max_leverage": 1.0,
            "base_position_pct": 0.1
        }
    }',
    'admin',
    'momentum',
    'momentum,long,simple',
    null,
    systimestamp(),
    systimestamp(),
    null
);
*/

-- ============================================================================
-- SAMPLE DATA - Example SHORT strategy (pump & dump detection)
-- ============================================================================
/*
INSERT INTO strategies VALUES (
    'strat-uuid-short-1',
    'SHORT Pump Dump Hunter v1',
    'Detect pump & dump and profit from price drop',
    'SHORT',
    true,
    '{
        "strategy_name": "SHORT Pump Dump Hunter v1",
        "direction": "SHORT",
        "signal_detection_conditions": {
            "pump_magnitude_pct": {"min": 15.0},
            "volume_surge_ratio": {"min": 3.0}
        },
        "entry_conditions": {},
        "signal_cancellation_conditions": {
            "momentum_reversal": {"max": -20.0}
        },
        "emergency_exit_conditions": {
            "momentum_reversal": {"min": 50.0}
        },
        "global_limits": {
            "max_leverage": 3.0,
            "base_position_pct": 0.02,
            "emergency_exit_cooldown_minutes": 60
        }
    }',
    'admin',
    'pump_dump',
    'short,pump_dump,leverage',
    null,
    systimestamp(),
    systimestamp(),
    null
);
*/

-- ============================================================================
-- QUERY EXAMPLES
-- ============================================================================

-- Get all enabled strategies
-- SELECT id, strategy_name, direction, enabled FROM strategies WHERE enabled = true;

-- Get all SHORT strategies
-- SELECT id, strategy_name, direction FROM strategies WHERE direction = 'SHORT';

-- Get strategy by name (unique lookup)
-- SELECT * FROM strategies WHERE strategy_name = 'Momentum LONG v1';

-- Get all strategies ordered by last activation
-- SELECT strategy_name, direction, enabled, last_activated_at
-- FROM strategies
-- ORDER BY last_activated_at DESC NULLS LAST;

-- Update strategy configuration
-- UPDATE strategies
-- SET strategy_json = '{"new": "config"}',
--     updated_at = systimestamp()
-- WHERE strategy_name = 'Momentum LONG v1';

-- Mark strategy as activated
-- UPDATE strategies
-- SET last_activated_at = systimestamp()
-- WHERE strategy_name = 'Momentum LONG v1';

-- ============================================================================
-- NOTES
-- ============================================================================
/*
1. RELATIONAL TABLE (not time-series):
   - No PARTITION BY - strategies are long-lived objects
   - No WAL needed - not high-frequency writes
   - Standard relational table for CRUD operations

2. JSON STORAGE STRATEGY:
   - strategy_json: Full config as JSON string
   - Allows schema evolution without migrations
   - Easy to serialize/deserialize with Python json.dumps/loads
   - Can query specific fields: strategy_json::json->>'direction'

3. UNIQUE CONSTRAINT:
   - strategy_name should be unique per user (enforced in application layer)
   - id is UUID for global uniqueness
   - Index on strategy_name enables fast duplicate detection

4. DIRECTION FIELD:
   - Extracted from JSON for fast filtering
   - Values: "LONG", "SHORT", "BOTH"
   - Indexed for fast WHERE direction = 'SHORT' queries

5. ENABLED FIELD:
   - Quick on/off toggle without deleting strategy
   - Indexed for fast "get all active strategies" query
   - enabled = false: Strategy exists but won't be loaded into StrategyManager

6. RUNTIME STATE NOT PERSISTED:
   - current_state: Always INACTIVE on load
   - symbol: Empty string until activated for specific symbol
   - position_active: false
   - These are transient state managed by StrategyManager in-memory

7. SCHEMA FLEXIBILITY:
   - Adding new fields to strategy config: Just update JSON, no migration needed
   - Example: Adding "max_drawdown": Update strategy_json, application handles it
   - Backward compatible: Old strategies without new field use defaults

8. MIGRATION SAFETY:
   - DROP TABLE IF EXISTS: Safe to re-run migration
   - No data loss risk - table starts empty
   - Production: Comment out DROP after initial deployment
*/

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Check table was created
SELECT table_name, designatedTimestamp, partitionBy, walEnabled
FROM tables()
WHERE table_name = 'strategies';

-- Expected result:
-- table_name | designatedTimestamp | partitionBy | walEnabled
-- strategies | null                | NONE        | false

-- Check table is empty initially
SELECT count(*) as row_count FROM strategies;

-- Expected result: 0
