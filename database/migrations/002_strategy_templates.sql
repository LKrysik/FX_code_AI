-- Migration 002: Strategy Templates
-- Phase 2 Sprint 2
-- ==========================================
-- Database schema for storing and managing strategy templates

-- Strategy Templates Table
CREATE TABLE IF NOT EXISTS strategy_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    category TEXT NOT NULL,  -- 'trend_following', 'mean_reversion', 'breakout', 'momentum', 'volatility'

    -- Strategy data (5-section format)
    strategy_json JSONB NOT NULL,

    -- Metadata
    author TEXT DEFAULT 'system',
    is_public BOOLEAN DEFAULT true,
    is_featured BOOLEAN DEFAULT false,

    -- Usage statistics
    usage_count INTEGER DEFAULT 0,
    success_rate DECIMAL(5,2),  -- NULL if not backtested yet
    avg_return DECIMAL(10,4),   -- NULL if not backtested yet

    -- Versioning
    version INTEGER DEFAULT 1,
    parent_template_id UUID REFERENCES strategy_templates(id),  -- For template variations

    -- Tags for search
    tags TEXT[],

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Indexes
    CONSTRAINT valid_category CHECK (category IN (
        'trend_following',
        'mean_reversion',
        'breakout',
        'momentum',
        'volatility',
        'scalping',
        'swing',
        'position',
        'other'
    ))
);

-- Indexes for performance
CREATE INDEX idx_templates_category ON strategy_templates(category);
CREATE INDEX idx_templates_author ON strategy_templates(author);
CREATE INDEX idx_templates_public ON strategy_templates(is_public) WHERE is_public = true;
CREATE INDEX idx_templates_featured ON strategy_templates(is_featured) WHERE is_featured = true;
CREATE INDEX idx_templates_tags ON strategy_templates USING GIN(tags);
CREATE INDEX idx_templates_created ON strategy_templates(created_at DESC);

-- Full-text search index
CREATE INDEX idx_templates_search ON strategy_templates USING GIN(
    to_tsvector('english', name || ' ' || COALESCE(description, ''))
);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_strategy_template_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update timestamp
CREATE TRIGGER trigger_update_template_timestamp
    BEFORE UPDATE ON strategy_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_strategy_template_timestamp();

-- Function to increment usage count
CREATE OR REPLACE FUNCTION increment_template_usage(template_id UUID)
RETURNS VOID AS $$
BEGIN
    UPDATE strategy_templates
    SET usage_count = usage_count + 1
    WHERE id = template_id;
END;
$$ LANGUAGE plpgsql;

-- User Template Favorites (for future use)
CREATE TABLE IF NOT EXISTS user_template_favorites (
    user_id TEXT NOT NULL,
    template_id UUID NOT NULL REFERENCES strategy_templates(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, template_id)
);

CREATE INDEX idx_favorites_user ON user_template_favorites(user_id);
CREATE INDEX idx_favorites_template ON user_template_favorites(template_id);

-- Template Usage History (for analytics)
CREATE TABLE IF NOT EXISTS template_usage_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id UUID NOT NULL REFERENCES strategy_templates(id) ON DELETE CASCADE,
    user_id TEXT,
    action TEXT NOT NULL,  -- 'view', 'use', 'fork', 'backtest'
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_usage_template ON template_usage_history(template_id);
CREATE INDEX idx_usage_created ON template_usage_history(created_at DESC);

-- Convert to hypertable for time-series optimization
SELECT create_hypertable(
    'template_usage_history',
    'created_at',
    chunk_time_interval => INTERVAL '30 days',
    if_not_exists => TRUE
);

-- Add retention policy (keep 1 year of usage history)
SELECT add_retention_policy('template_usage_history', INTERVAL '1 year', if_not_exists => TRUE);

COMMENT ON TABLE strategy_templates IS 'Stores pre-built and user-created strategy templates';
COMMENT ON TABLE user_template_favorites IS 'User favorite templates for quick access';
COMMENT ON TABLE template_usage_history IS 'Analytics data for template usage tracking';
