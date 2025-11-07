-- Migration 015: Risk Events Table
-- ==================================
-- Purpose: Store risk alerts and events from RiskManager
-- Author: Agent 2 (Risk Management)
-- Date: 2025-11-07
-- Dependencies: EventBus (Agent 1), RiskManager

-- Risk events table for tracking all risk alerts
-- Supports RiskAlerts UI component and risk monitoring
CREATE TABLE IF NOT EXISTS risk_events (
    alert_id STRING,
    session_id STRING,
    timestamp TIMESTAMP,
    severity STRING,  -- CRITICAL, WARNING, INFO
    alert_type STRING,  -- POSITION_SIZE_EXCEEDED, MAX_POSITIONS_EXCEEDED, CONCENTRATION_EXCEEDED, DAILY_LOSS_LIMIT, MAX_DRAWDOWN, MARGIN_UTILIZATION_HIGH, MARGIN_RATIO_LOW, ORDER_REJECTED
    message STRING,   -- Human-readable alert message
    details STRING,   -- JSON with additional context
    acknowledged BOOLEAN  -- Whether alert was acknowledged by user
) timestamp(timestamp) PARTITION BY DAY WAL;

-- Create indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_risk_events_session ON risk_events (session_id);
CREATE INDEX IF NOT EXISTS idx_risk_events_severity ON risk_events (severity);
CREATE INDEX IF NOT EXISTS idx_risk_events_type ON risk_events (alert_type);
CREATE INDEX IF NOT EXISTS idx_risk_events_acknowledged ON risk_events (acknowledged);

-- Sample query patterns (for reference)
-- =====================================
-- 1. Get all critical alerts for session:
--    SELECT * FROM risk_events WHERE session_id = 'xxx' AND severity = 'CRITICAL' ORDER BY timestamp DESC;
--
-- 2. Get unacknowledged alerts:
--    SELECT * FROM risk_events WHERE acknowledged = false ORDER BY timestamp DESC;
--
-- 3. Get daily loss limit breaches:
--    SELECT * FROM risk_events WHERE alert_type = 'DAILY_LOSS_LIMIT' ORDER BY timestamp DESC;
--
-- 4. Get margin-related alerts:
--    SELECT * FROM risk_events WHERE alert_type IN ('MARGIN_UTILIZATION_HIGH', 'MARGIN_RATIO_LOW') ORDER BY timestamp DESC;

-- Performance notes:
-- ==================
-- - Partitioned by DAY for efficient time-range queries
-- - WAL (Write-Ahead Log) enabled for fast writes from EventBus
-- - Indexes on session_id, severity, alert_type for common filters
-- - acknowledged index for filtering unread alerts

-- Data retention:
-- ===============
-- Consider implementing cleanup job to delete old acknowledged alerts:
-- DELETE FROM risk_events WHERE acknowledged = true AND timestamp < dateadd('d', -30, now());
