-- SyniqAI Silver Assets PostgreSQL Schema
-- Run this after connecting to syniqai_metadata database

-- =============================================================================
-- silver_assets table - stores processed AI extraction results
-- =============================================================================

CREATE TABLE IF NOT EXISTS silver_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source VARCHAR(50) NOT NULL,
    file_type VARCHAR(20) NOT NULL,
    bronze_minio_key VARCHAR(500) NOT NULL,
    silver_minio_key VARCHAR(500) NOT NULL,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ai_model_used VARCHAR(100),
    extraction_status VARCHAR(20) NOT NULL,
    ai_confidence_score FLOAT,
    file_size_bytes BIGINT,
    content_tags JSONB,
    summary TEXT,
    
    CONSTRAINT valid_status CHECK (extraction_status IN ('pending', 'success', 'failed'))
);

CREATE INDEX IF NOT EXISTS idx_silver_assets_file_type ON silver_assets(file_type);
CREATE INDEX IF NOT EXISTS idx_silver_assets_source ON silver_assets(source);
CREATE INDEX IF NOT EXISTS idx_silver_assets_status ON silver_assets(extraction_status);
CREATE INDEX IF NOT EXISTS idx_silver_assets_processed_at ON silver_assets(processed_at DESC);
CREATE INDEX IF NOT EXISTS idx_silver_assets_tags ON silver_assets USING GIN (content_tags);


-- =============================================================================
-- silver_quality_flags table
-- =============================================================================

CREATE TABLE IF NOT EXISTS silver_quality_flags (
    id SERIAL PRIMARY KEY,
    asset_id UUID NOT NULL REFERENCES silver_assets(id) ON DELETE CASCADE,
    flag_type VARCHAR(50) NOT NULL,
    flag_value TEXT,
    flagged_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_quality_flags_asset_id ON silver_quality_flags(asset_id);
CREATE INDEX IF NOT EXISTS idx_quality_flags_type ON silver_quality_flags(flag_type);


-- =============================================================================
-- Grant permissions to syniqai_user
-- =============================================================================

GRANT ALL PRIVILEGES ON silver_assets TO syniqai_user;
GRANT ALL PRIVILEGES ON silver_quality_flags TO syniqai_user;
GRANT ALL PRIVILEGES ON silver_quality_flags_id_seq TO syniqai_user;

-- Verification
SELECT '✓ Silver tables created successfully!' as status;
