-- Migration 004: Fix lineage function to match actual table structure
-- The gold_lineage table doesn't have metadata column, so remove it from function

-- Drop the old function first
DROP FUNCTION IF EXISTS get_lineage_trail(UUID);

CREATE OR REPLACE FUNCTION get_lineage_trail(p_asset_id UUID)
RETURNS TABLE (
  event_type VARCHAR,
  event_time TIMESTAMPTZ,
  model_used VARCHAR,
  quality_score FLOAT,
  source_bucket VARCHAR,
  dest_bucket VARCHAR
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    gl.event_type,
    gl.event_time,
    gl.model_used,
    gl.quality_score,
    gl.source_bucket,
    gl.dest_bucket
  FROM gold_lineage gl
  WHERE gl.asset_id = p_asset_id
  ORDER BY gl.event_time ASC;
END;
$$ LANGUAGE plpgsql;

-- Success message
DO $$
BEGIN
  RAISE NOTICE '✓ Lineage function fixed successfully';
END $$;
