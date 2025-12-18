-- Migration: Add session_id to Trading Persistence Tables
-- Created: 2025-12-17
-- Purpose: Enable session separation for backtests, live, and paper trading
-- Related: AUDIT_FINAL_REPORT.md - Issue #2 (Session Separation)

-- ============================================================================
-- CRITICAL FIX: Session Separation for Frontend Visibility
-- ============================================================================

-- Add session_id column to strategy_signals
ALTER TABLE strategy_signals ADD COLUMN IF NOT EXISTS session_id SYMBOL;

-- Add session_id column to orders
ALTER TABLE orders ADD COLUMN IF NOT EXISTS session_id SYMBOL;

-- Add session_id column to positions
ALTER TABLE positions ADD COLUMN IF NOT EXISTS session_id SYMBOL;

-- ============================================================================
-- NOTE: QuestDB automatically creates indices for SYMBOL columns
-- No explicit CREATE INDEX needed - SYMBOL type is indexed by default
-- ============================================================================
