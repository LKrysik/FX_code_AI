-- ============================================================================
-- FX_code_AI TimescaleDB Schema
-- ============================================================================
-- Setup complete time-series database with:
-- - Hypertables with SEGMENT BY symbol
-- - Continuous aggregates (1m, 5m)
-- - Columnar compression
-- - Retention policies

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ============================================================================
-- TABLE 1: market_data (Raw tick data)
-- ============================================================================
CREATE TABLE IF NOT EXISTS market_data (
    ts TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    open DOUBLE PRECISION,
    high DOUBLE PRECISION,
    low DOUBLE PRECISION,
    close DOUBLE PRECISION,
    volume DOUBLE PRECISION,
    trades_count INTEGER DEFAULT 0,
    vwap DOUBLE PRECISION,
    PRIMARY KEY (ts, symbol)
);

-- Convert to hypertable with SEGMENT BY symbol (per user requirement)
SELECT create_hypertable(
    'market_data',
    'ts',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Add SEGMENT BY symbol for partitioning (user requirement)
-- Note: segment_by is set at hypertable creation in newer versions
-- For explicit segmentation, we use additional indexing
CREATE INDEX IF NOT EXISTS idx_market_data_symbol_ts
    ON market_data (symbol, ts DESC);

-- Enable columnar compression (user requirement)
ALTER TABLE market_data SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol',
    timescaledb.compress_orderby = 'ts DESC'
);

-- Compression policy: compress data older than 1 day
SELECT add_compression_policy(
    'market_data',
    INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Retention policy: keep 6 months (user: "wg potrzeb" - adjustable)
SELECT add_retention_policy(
    'market_data',
    INTERVAL '6 months',
    if_not_exists => TRUE
);

-- ============================================================================
-- TABLE 2: indicators (Calculated indicator values)
-- ============================================================================
CREATE TABLE IF NOT EXISTS indicators (
    ts TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    indicator_type TEXT NOT NULL,  -- e.g., "EMA_20", "RSI_14", "PUMP_MAGNITUDE_PCT"
    indicator_id TEXT NOT NULL,     -- Unique ID for variant
    value DOUBLE PRECISION,
    metadata JSONB,                 -- Optional: store params, confidence, etc.
    PRIMARY KEY (ts, symbol, indicator_id)
);

-- Convert to hypertable
SELECT create_hypertable(
    'indicators',
    'ts',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Index for fast indicator queries
CREATE INDEX IF NOT EXISTS idx_indicators_symbol_type_ts
    ON indicators (symbol, indicator_type, ts DESC);

CREATE INDEX IF NOT EXISTS idx_indicators_id_ts
    ON indicators (indicator_id, ts DESC);

-- Enable compression
ALTER TABLE indicators SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol,indicator_type',
    timescaledb.compress_orderby = 'ts DESC'
);

-- Compression policy
SELECT add_compression_policy(
    'indicators',
    INTERVAL '7 days',
    if_not_exists => TRUE
);

-- Retention policy: 3 months for indicators
SELECT add_retention_policy(
    'indicators',
    INTERVAL '3 months',
    if_not_exists => TRUE
);

-- ============================================================================
-- CONTINUOUS AGGREGATE: market_data_1m (1-minute bars)
-- ============================================================================
-- User requirement: "Continuous aggregate dla 1m/5m, nie do 1s RT"
CREATE MATERIALIZED VIEW IF NOT EXISTS market_data_1m
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 minute', ts) AS bucket,
    symbol,
    first(open, ts) AS open,
    max(high) AS high,
    min(low) AS low,
    last(close, ts) AS close,
    sum(volume) AS volume,
    sum(trades_count) AS trades_count,
    -- VWAP calculation
    CASE
        WHEN sum(volume) > 0 THEN sum(vwap * volume) / sum(volume)
        ELSE NULL
    END AS vwap
FROM market_data
GROUP BY bucket, symbol
WITH NO DATA;

-- Refresh policy: update every 1 minute
SELECT add_continuous_aggregate_policy(
    'market_data_1m',
    start_offset => INTERVAL '2 hours',
    end_offset => INTERVAL '1 minute',
    schedule_interval => INTERVAL '1 minute',
    if_not_exists => TRUE
);

-- Index on continuous aggregate
CREATE INDEX IF NOT EXISTS idx_market_data_1m_symbol_bucket
    ON market_data_1m (symbol, bucket DESC);

-- ============================================================================
-- CONTINUOUS AGGREGATE: market_data_5m (5-minute bars)
-- ============================================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS market_data_5m
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('5 minutes', ts) AS bucket,
    symbol,
    first(open, ts) AS open,
    max(high) AS high,
    min(low) AS low,
    last(close, ts) AS close,
    sum(volume) AS volume,
    sum(trades_count) AS trades_count,
    CASE
        WHEN sum(volume) > 0 THEN sum(vwap * volume) / sum(volume)
        ELSE NULL
    END AS vwap
FROM market_data
GROUP BY bucket, symbol
WITH NO DATA;

-- Refresh policy: update every 5 minutes
SELECT add_continuous_aggregate_policy(
    'market_data_5m',
    start_offset => INTERVAL '6 hours',
    end_offset => INTERVAL '5 minutes',
    schedule_interval => INTERVAL '5 minutes',
    if_not_exists => TRUE
);

-- Index
CREATE INDEX IF NOT EXISTS idx_market_data_5m_symbol_bucket
    ON market_data_5m (symbol, bucket DESC);

-- ============================================================================
-- TABLE 3: trades (Individual trade records for detailed analysis)
-- ============================================================================
CREATE TABLE IF NOT EXISTS trades (
    ts TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    trade_id TEXT,
    price DOUBLE PRECISION NOT NULL,
    quantity DOUBLE PRECISION NOT NULL,
    side TEXT,  -- 'buy' or 'sell'
    is_buyer_maker BOOLEAN
);

-- Hypertable
SELECT create_hypertable(
    'trades',
    'ts',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_trades_symbol_ts
    ON trades (symbol, ts DESC);

-- Compression
ALTER TABLE trades SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol',
    timescaledb.compress_orderby = 'ts DESC'
);

SELECT add_compression_policy(
    'trades',
    INTERVAL '7 days',
    if_not_exists => TRUE
);

-- Retention: 1 month (trades are large volume)
SELECT add_retention_policy(
    'trades',
    INTERVAL '1 month',
    if_not_exists => TRUE
);

-- ============================================================================
-- TABLE 4: orderbook_snapshots (Orderbook depth snapshots)
-- ============================================================================
CREATE TABLE IF NOT EXISTS orderbook_snapshots (
    ts TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    bids JSONB NOT NULL,  -- [{price, quantity}, ...]
    asks JSONB NOT NULL,
    best_bid DOUBLE PRECISION,
    best_ask DOUBLE PRECISION,
    bid_qty DOUBLE PRECISION,
    ask_qty DOUBLE PRECISION
);

-- Hypertable
SELECT create_hypertable(
    'orderbook_snapshots',
    'ts',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Index
CREATE INDEX IF NOT EXISTS idx_orderbook_symbol_ts
    ON orderbook_snapshots (symbol, ts DESC);

-- Compression
ALTER TABLE orderbook_snapshots SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol',
    timescaledb.compress_orderby = 'ts DESC'
);

SELECT add_compression_policy(
    'orderbook_snapshots',
    INTERVAL '3 days',
    if_not_exists => TRUE
);

-- Retention: 1 week (orderbook data is ephemeral)
SELECT add_retention_policy(
    'orderbook_snapshots',
    INTERVAL '1 week',
    if_not_exists => TRUE
);

-- ============================================================================
-- UTILITY FUNCTIONS
-- ============================================================================

-- Function to get latest price for a symbol
CREATE OR REPLACE FUNCTION get_latest_price(p_symbol TEXT)
RETURNS DOUBLE PRECISION AS $$
    SELECT close
    FROM market_data
    WHERE symbol = p_symbol
    ORDER BY ts DESC
    LIMIT 1;
$$ LANGUAGE SQL STABLE;

-- Function to get OHLCV for time range (uses continuous aggregate if possible)
CREATE OR REPLACE FUNCTION get_ohlcv_range(
    p_symbol TEXT,
    p_start TIMESTAMPTZ,
    p_end TIMESTAMPTZ,
    p_interval TEXT DEFAULT '1m'
)
RETURNS TABLE (
    bucket TIMESTAMPTZ,
    open DOUBLE PRECISION,
    high DOUBLE PRECISION,
    low DOUBLE PRECISION,
    close DOUBLE PRECISION,
    volume DOUBLE PRECISION
) AS $$
BEGIN
    IF p_interval = '1m' THEN
        RETURN QUERY
        SELECT m.bucket, m.open, m.high, m.low, m.close, m.volume
        FROM market_data_1m m
        WHERE m.symbol = p_symbol
          AND m.bucket BETWEEN p_start AND p_end
        ORDER BY m.bucket ASC;
    ELSIF p_interval = '5m' THEN
        RETURN QUERY
        SELECT m.bucket, m.open, m.high, m.low, m.close, m.volume
        FROM market_data_5m m
        WHERE m.symbol = p_symbol
          AND m.bucket BETWEEN p_start AND p_end
        ORDER BY m.bucket ASC;
    ELSE
        -- Raw data for other intervals
        RETURN QUERY
        SELECT
            time_bucket(p_interval::INTERVAL, m.ts) AS bucket,
            first(m.open, m.ts) AS open,
            max(m.high) AS high,
            min(m.low) AS low,
            last(m.close, m.ts) AS close,
            sum(m.volume) AS volume
        FROM market_data m
        WHERE m.symbol = p_symbol
          AND m.ts BETWEEN p_start AND p_end
        GROUP BY bucket
        ORDER BY bucket ASC;
    END IF;
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================================================
-- SUMMARY VIEW: Database statistics
-- ============================================================================
CREATE OR REPLACE VIEW database_stats AS
SELECT
    'market_data' AS table_name,
    COUNT(*) AS row_count,
    MIN(ts) AS oldest_data,
    MAX(ts) AS newest_data,
    COUNT(DISTINCT symbol) AS symbol_count,
    pg_size_pretty(pg_total_relation_size('market_data')) AS total_size
FROM market_data
UNION ALL
SELECT
    'indicators' AS table_name,
    COUNT(*) AS row_count,
    MIN(ts) AS oldest_data,
    MAX(ts) AS newest_data,
    COUNT(DISTINCT symbol) AS symbol_count,
    pg_size_pretty(pg_total_relation_size('indicators')) AS total_size
FROM indicators
UNION ALL
SELECT
    'trades' AS table_name,
    COUNT(*) AS row_count,
    MIN(ts) AS oldest_data,
    MAX(ts) AS newest_data,
    COUNT(DISTINCT symbol) AS symbol_count,
    pg_size_pretty(pg_total_relation_size('trades')) AS total_size
FROM trades;

-- ============================================================================
-- GRANTS (adjust as needed for security)
-- ============================================================================
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO trading_user;
GRANT USAGE ON SCHEMA public TO trading_user;

-- ============================================================================
-- INITIALIZATION COMPLETE
-- ============================================================================
\echo 'TimescaleDB schema initialization complete!'
\echo 'Tables: market_data, indicators, trades, orderbook_snapshots'
\echo 'Continuous aggregates: market_data_1m, market_data_5m'
\echo 'Compression: Enabled with policies'
\echo 'Retention: Configured per table'
