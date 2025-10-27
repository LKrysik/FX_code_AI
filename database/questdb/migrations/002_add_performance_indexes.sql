-- Migration 002: Add Performance Indexes and Optimizations
-- Date: 2025-10-27
-- Description: Additional indexes and settings for production performance

-- ============================================================================
-- SAMPLE DATA (Example - remove in production)
-- ============================================================================
-- This migration includes sample data for testing
-- Remove this section when deploying to production

-- Sample price data
INSERT INTO prices VALUES (
    'BTC/USD',
    to_timestamp('2025-10-27T12:00:00', 'yyyy-MM-ddTHH:mm:ss'),
    50000.0,
    50100.0,
    49900.0,
    50050.0,
    1000000.0,
    50048.0,
    50052.0,
    4.0
);

-- Sample indicators
INSERT INTO indicators VALUES (
    'BTC/USD',
    'RSI_14',
    to_timestamp('2025-10-27T12:00:00', 'yyyy-MM-ddTHH:mm:ss'),
    45.5,
    0.95,
    '{"period": 14, "source": "close"}'
);

INSERT INTO indicators VALUES (
    'BTC/USD',
    'EMA_50',
    to_timestamp('2025-10-27T12:00:00', 'yyyy-MM-ddTHH:mm:ss'),
    49800.0,
    1.0,
    '{"period": 50}'
);

-- Sample strategy template
INSERT INTO strategy_templates VALUES (
    'template-uuid-001',
    'RSI Mean Reversion',
    'Buy when RSI < 30 (oversold), sell when RSI > 70 (overbought)',
    'mean_reversion',
    '{"s1_signal": {"conditions": [{"id": "1", "indicatorId": "RSI_14", "operator": "<", "value": 30}]}}',
    'system',
    true,
    true,
    0,
    null,
    null,
    'rsi,mean_reversion,beginner-friendly',
    1,
    null,
    systimestamp(),
    systimestamp()
);

-- ============================================================================
-- NOTE: This is an example migration showing how to add data
-- Future migrations would add:
-- - Additional indexes
-- - New columns
-- - Performance optimizations
-- - Data transformations
-- ============================================================================
