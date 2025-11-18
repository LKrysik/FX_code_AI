-- ============================================================================
-- Migration 021: Add confidence field to strategy_signals
-- Date: 2025-11-16
-- Purpose: Add confidence score to strategy signals for UI display
--
-- ISSUE: Frontend Dashboard and SignalHistoryPanel expect confidence field
-- but it doesn't exist in strategy_signals table (migration 019)
--
-- SOLUTION: Add confidence column as DOUBLE (0.0 to 1.0)
-- ============================================================================

-- Add confidence column to strategy_signals
ALTER TABLE strategy_signals ADD COLUMN IF NOT EXISTS confidence DOUBLE;

-- Verify the change
SELECT column_name, column_type
FROM table_columns('strategy_signals')
WHERE column_name = 'confidence';

-- ============================================================================
-- Migration Notes
-- ============================================================================
--
-- Confidence represents signal strength/certainty (0.0 = no confidence, 1.0 = maximum confidence)
-- Expected to be populated by TradingPersistenceService when writing signals
-- Frontend displays as percentage: (confidence * 100).toFixed(0) + '%'
--
-- Existing rows will have NULL confidence - frontend should handle gracefully
-- ============================================================================
