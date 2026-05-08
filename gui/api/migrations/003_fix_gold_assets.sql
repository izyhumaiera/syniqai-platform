-- ============================================================================
-- MIGRATION: 003_fix_gold_assets.sql
-- Fix Gold Assets Materialized View (Remove quality_flag dependency)
-- ============================================================================
-- Purpose: Recreate gold_assets view without dependency on silver_quality_flags
-- ============================================================================

-- Drop existing materialized view
DROP MATERIALIZED VIEW IF EXISTS gold_assets CASCADE;

-- ============================================================================
-- GOLD ASSETS MATERIALIZED VIEW (Simplified)
-- ============================================================================
-- Only successful extractions are promoted to Gold layer
-- Materialized for performance - refresh controlled by application layer

CREATE MATERIALIZED VIEW gold_assets AS
SELECT
  sa.id,
  sa.source,
  sa.file_type,
  sa.summary,
  sa.content_tags,
  sa.ai_confidence_score,
  sa.silver_minio_key,
  sa.bronze_minio_key,
  sa.processed_at,
  sa.ai_model_used
FROM silver_assets sa
WHERE sa.extraction_status = 'success';

-- Create unique index for efficient lookups
CREATE UNIQUE INDEX idx_gold_assets_id ON gold_assets (id);

-- Additional indexes for common query patterns
CREATE INDEX idx_gold_assets_file_type ON gold_assets (file_type);
CREATE INDEX idx_gold_assets_processed_at ON gold_assets (processed_at DESC);
CREATE INDEX idx_gold_assets_source ON gold_assets (source);

-- ============================================================================
-- Refresh materialized view with data
-- ============================================================================
REFRESH MATERIALIZED VIEW gold_assets;

-- Grant permissions
GRANT SELECT ON gold_assets TO syniqai_user;

-- Confirmation message
DO $$
BEGIN
  RAISE NOTICE '✓ Gold assets materialized view recreated successfully';
  RAISE NOTICE 'Total Gold assets: %', (SELECT COUNT(*) FROM gold_assets);
END $$;
