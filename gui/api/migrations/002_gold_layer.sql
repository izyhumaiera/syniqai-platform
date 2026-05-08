-- ============================================================================
-- MIGRATION: 002_gold_layer.sql
-- Block 4: Gold Layer - CDW Views + Lineage Tracking
-- ============================================================================
-- Purpose: Create Gold layer materialized views and lineage tracking system
-- Dependencies: silver_assets, silver_quality_flags tables must exist
-- ============================================================================

-- Drop existing objects if they exist (for re-running migration)
DROP MATERIALIZED VIEW IF EXISTS gold_assets CASCADE;
DROP TABLE IF EXISTS gold_lineage CASCADE;

-- ============================================================================
-- GOLD ASSETS MATERIALIZED VIEW
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
-- GOLD LINEAGE TABLE
-- ============================================================================
-- Records every hop in the data pipeline: Bronze → Silver → Gold
-- Enables full data lineage tracking and audit trails

CREATE TABLE gold_lineage (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  asset_id UUID REFERENCES silver_assets(id) ON DELETE CASCADE,
  event_type VARCHAR(50) NOT NULL,  -- 'bronze_ingested', 'silver_processed', 'gold_promoted'
  event_time TIMESTAMPTZ DEFAULT now() NOT NULL,
  model_used VARCHAR(100),
  quality_score FLOAT,
  source_bucket VARCHAR(100),
  dest_bucket VARCHAR(100),
  metadata JSONB,  -- Additional event-specific metadata
  created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- Indexes for lineage queries
CREATE INDEX idx_gold_lineage_asset_id ON gold_lineage (asset_id);
CREATE INDEX idx_gold_lineage_event_type ON gold_lineage (event_type);
CREATE INDEX idx_gold_lineage_event_time ON gold_lineage (event_time DESC);

-- Composite index for common lineage trail queries
CREATE INDEX idx_gold_lineage_asset_event ON gold_lineage (asset_id, event_time DESC);

-- ============================================================================
-- UTILITY VIEWS
-- ============================================================================

-- View: Complete lineage summary with asset details
CREATE OR REPLACE VIEW v_gold_lineage_summary AS
SELECT
  gl.asset_id,
  sa.file_type,
  sa.source,
  COUNT(*) as total_events,
  MIN(gl.event_time) as first_event,
  MAX(gl.event_time) as last_event,
  ARRAY_AGG(gl.event_type ORDER BY gl.event_time) as event_sequence
FROM gold_lineage gl
JOIN silver_assets sa ON sa.id = gl.asset_id
GROUP BY gl.asset_id, sa.file_type, sa.source;

-- View: Gold assets with row count and last refresh time
CREATE OR REPLACE VIEW v_gold_assets_metadata AS
SELECT
  COUNT(*) as total_gold_assets,
  COUNT(DISTINCT file_type) as unique_file_types,
  COUNT(DISTINCT source) as unique_sources,
  MIN(processed_at) as earliest_asset,
  MAX(processed_at) as latest_asset,
  AVG(ai_confidence_score) as avg_confidence_score
FROM gold_assets;

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Function: Get lineage trail for a specific asset
CREATE OR REPLACE FUNCTION get_lineage_trail(p_asset_id UUID)
RETURNS TABLE (
  event_type VARCHAR,
  event_time TIMESTAMPTZ,
  model_used VARCHAR,
  quality_score FLOAT,
  source_bucket VARCHAR,
  dest_bucket VARCHAR,
  metadata JSONB
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    gl.event_type,
    gl.event_time,
    gl.model_used,
    gl.quality_score,
    gl.source_bucket,
    gl.dest_bucket,
    gl.metadata
  FROM gold_lineage gl
  WHERE gl.asset_id = p_asset_id
  ORDER BY gl.event_time ASC;
END;
$$ LANGUAGE plpgsql;

-- Function: Refresh gold materialized view and return stats
CREATE OR REPLACE FUNCTION refresh_gold_view()
RETURNS TABLE (
  refreshed_at TIMESTAMPTZ,
  total_assets BIGINT,
  new_assets BIGINT
) AS $$
DECLARE
  old_count BIGINT;
  new_count BIGINT;
BEGIN
  -- Get count before refresh
  SELECT COUNT(*) INTO old_count FROM gold_assets;
  
  -- Refresh the materialized view
  REFRESH MATERIALIZED VIEW gold_assets;
  
  -- Get count after refresh
  SELECT COUNT(*) INTO new_count FROM gold_assets;
  
  RETURN QUERY
  SELECT
    now() as refreshed_at,
    new_count as total_assets,
    (new_count - old_count) as new_assets;
END;
$$ LANGUAGE plpgsql;

-- Function: Insert lineage event (helper for application layer)
CREATE OR REPLACE FUNCTION insert_lineage_event(
  p_asset_id UUID,
  p_event_type VARCHAR,
  p_model_used VARCHAR DEFAULT NULL,
  p_quality_score FLOAT DEFAULT NULL,
  p_source_bucket VARCHAR DEFAULT NULL,
  p_dest_bucket VARCHAR DEFAULT NULL,
  p_metadata JSONB DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
  v_lineage_id UUID;
BEGIN
  INSERT INTO gold_lineage (
    asset_id,
    event_type,
    model_used,
    quality_score,
    source_bucket,
    dest_bucket,
    metadata
  ) VALUES (
    p_asset_id,
    p_event_type,
    p_model_used,
    p_quality_score,
    p_source_bucket,
    p_dest_bucket,
    p_metadata
  )
  RETURNING id INTO v_lineage_id;
  
  RETURN v_lineage_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- CONSTRAINTS & VALIDATION
-- ============================================================================

-- Check constraint: event_type must be one of the valid types
ALTER TABLE gold_lineage ADD CONSTRAINT chk_event_type 
  CHECK (event_type IN ('bronze_ingested', 'silver_processed', 'gold_promoted', 'quality_check'));

-- Check constraint: quality_score must be between 0 and 1
ALTER TABLE gold_lineage ADD CONSTRAINT chk_quality_score 
  CHECK (quality_score IS NULL OR (quality_score >= 0 AND quality_score <= 1));

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON MATERIALIZED VIEW gold_assets IS 'Gold layer: curated, high-quality assets from successful Silver extractions';
COMMENT ON TABLE gold_lineage IS 'Data lineage tracking: records every transformation event in the pipeline';
COMMENT ON FUNCTION get_lineage_trail(UUID) IS 'Returns complete lineage trail for a specific asset';
COMMENT ON FUNCTION refresh_gold_view() IS 'Refreshes gold_assets materialized view and returns statistics';
COMMENT ON FUNCTION insert_lineage_event IS 'Helper function to insert lineage events with validation';

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================

-- Display migration summary
DO $$
BEGIN
  RAISE NOTICE '═══════════════════════════════════════════════════════════════';
  RAISE NOTICE 'Migration 002_gold_layer.sql completed successfully';
  RAISE NOTICE '═══════════════════════════════════════════════════════════════';
  RAISE NOTICE 'Created objects:';
  RAISE NOTICE '  ✓ Materialized View: gold_assets';
  RAISE NOTICE '  ✓ Table: gold_lineage';
  RAISE NOTICE '  ✓ View: v_gold_lineage_summary';
  RAISE NOTICE '  ✓ View: v_gold_assets_metadata';
  RAISE NOTICE '  ✓ Function: get_lineage_trail(UUID)';
  RAISE NOTICE '  ✓ Function: refresh_gold_view()';
  RAISE NOTICE '  ✓ Function: insert_lineage_event(...)';
  RAISE NOTICE '  ✓ Indexes: 8 indexes created';
  RAISE NOTICE '═══════════════════════════════════════════════════════════════';
  RAISE NOTICE 'Next steps:';
  RAISE NOTICE '  1. Start gold_lineage_consumer.py to track lineage events';
  RAISE NOTICE '  2. Call refresh_gold_view() to populate initial data';
  RAISE NOTICE '  3. Test API endpoints: /api/gold/assets, /api/gold/lineage/{id}';
  RAISE NOTICE '═══════════════════════════════════════════════════════════════';
END $$;
