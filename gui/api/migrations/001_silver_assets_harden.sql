-- ============================================================================
-- Silver Assets Hardening Migration
-- ============================================================================
-- Purpose: Add constraints, indexes, and ensure data integrity for silver_assets
-- Version: 001
-- Date: March 29, 2026
-- Author: SyniqAI Engineering Team
-- ============================================================================

-- Step 1: Backfill any NULL bronze_minio_key or silver_minio_key values
-- (should ideally be zero, but let's be safe)
BEGIN;

DO $$
DECLARE
    null_bronze_count INTEGER;
    null_silver_count INTEGER;
BEGIN
    -- Check for NULL bronze_minio_key
    SELECT COUNT(*) INTO null_bronze_count 
    FROM silver_assets 
    WHERE bronze_minio_key IS NULL;
    
    IF null_bronze_count > 0 THEN
        RAISE NOTICE 'Found % rows with NULL bronze_minio_key - setting placeholder', null_bronze_count;
        UPDATE silver_assets 
        SET bronze_minio_key = 'syniqai-bronze/MISSING/' || id::text
        WHERE bronze_minio_key IS NULL;
    ELSE
        RAISE NOTICE '✓ All rows have bronze_minio_key populated';
    END IF;
    
    -- Check for NULL silver_minio_key
    SELECT COUNT(*) INTO null_silver_count 
    FROM silver_assets 
    WHERE silver_minio_key IS NULL AND extraction_status = 'success';
    
    IF null_silver_count > 0 THEN
        RAISE NOTICE 'Found % rows with NULL silver_minio_key but success status - setting placeholder', null_silver_count;
        UPDATE silver_assets 
        SET silver_minio_key = 'syniqai-silver/MISSING/' || id::text || '.json'
        WHERE silver_minio_key IS NULL AND extraction_status = 'success';
    ELSE
        RAISE NOTICE '✓ All successful rows have silver_minio_key populated';
    END IF;
END $$;

-- Step 2: Add NOT NULL constraints to ensure future rows always have these paths
ALTER TABLE silver_assets 
ALTER COLUMN bronze_minio_key SET NOT NULL;

-- silver_minio_key can be NULL for pending/failed status, but should be NOT NULL for success
-- We'll add a CHECK constraint instead
ALTER TABLE silver_assets 
ADD CONSTRAINT silver_key_required_on_success 
CHECK (
    (extraction_status != 'success') OR 
    (extraction_status = 'success' AND silver_minio_key IS NOT NULL)
);

COMMENT ON CONSTRAINT silver_key_required_on_success ON silver_assets IS 
'Ensures silver_minio_key is populated when extraction_status is success';

-- Step 3: Add CHECK constraints to prevent path mix-ups
ALTER TABLE silver_assets 
ADD CONSTRAINT bronze_key_must_start_with_prefix
CHECK (bronze_minio_key LIKE 'syniqai-bronze/%');

ALTER TABLE silver_assets 
ADD CONSTRAINT silver_key_must_start_with_prefix
CHECK (
    silver_minio_key IS NULL OR 
    silver_minio_key LIKE 'syniqai-silver/%'
);

COMMENT ON CONSTRAINT bronze_key_must_start_with_prefix ON silver_assets IS 
'Prevents accidental path swaps - bronze keys must start with syniqai-bronze/';

COMMENT ON CONSTRAINT silver_key_must_start_with_prefix ON silver_assets IS 
'Prevents accidental path swaps - silver keys must start with syniqai-silver/';

-- Step 4: Add performance indexes (if not already existing)
-- Note: Some of these may already exist from block2_silver_tables.sql, using IF NOT EXISTS syntax

-- Composite index for common query patterns
CREATE INDEX IF NOT EXISTS idx_silver_assets_status_processed 
ON silver_assets(extraction_status, processed_at DESC);

CREATE INDEX IF NOT EXISTS idx_silver_assets_filetype_processed 
ON silver_assets(file_type, processed_at DESC);

-- Index for UUID lookups (primary key already indexed, but good to be explicit)
-- Already exists as PK, but we'll add comment
COMMENT ON INDEX silver_assets_pkey IS 
'Primary key index on id (UUID) for fast asset lookups by asset_id';

-- Index on silver_minio_key for reverse lookups (less common but useful)
CREATE INDEX IF NOT EXISTS idx_silver_assets_silver_key 
ON silver_assets(silver_minio_key) 
WHERE silver_minio_key IS NOT NULL;

-- Step 5: Add useful views for common queries

-- View: Failed assets that need attention
CREATE OR REPLACE VIEW v_silver_failed_assets AS
SELECT 
    id,
    source,
    file_type,
    bronze_minio_key,
    ai_model_used,
    processed_at,
    created_at,
    EXTRACT(EPOCH FROM (NOW() - created_at)) / 3600 AS hours_since_created
FROM silver_assets
WHERE extraction_status = 'failed'
ORDER BY created_at DESC;

COMMENT ON VIEW v_silver_failed_assets IS 
'Quick view of failed processing jobs for troubleshooting';

-- View: Assets awaiting processing
CREATE OR REPLACE VIEW v_silver_pending_assets AS
SELECT 
    id,
    source,
    file_type,
    bronze_minio_key,
    created_at,
    EXTRACT(EPOCH FROM (NOW() - created_at)) / 3600 AS hours_since_created
FROM silver_assets
WHERE extraction_status = 'pending'
ORDER BY created_at ASC;

COMMENT ON VIEW v_silver_pending_assets IS 
'Assets waiting for AI processing';

-- View: Successfully processed assets summary
CREATE OR REPLACE VIEW v_silver_success_summary AS
SELECT 
    file_type,
    ai_model_used,
    COUNT(*) AS total_processed,
    AVG(ai_confidence_score) AS avg_confidence,
    MIN(processed_at) AS first_processed,
    MAX(processed_at) AS last_processed
FROM silver_assets
WHERE extraction_status = 'success'
GROUP BY file_type, ai_model_used
ORDER BY total_processed DESC;

COMMENT ON VIEW v_silver_success_summary IS 
'Summary statistics of successfully processed assets by type and model';

-- Step 6: Add trigger to validate paths on INSERT/UPDATE
CREATE OR REPLACE FUNCTION validate_silver_asset_paths()
RETURNS TRIGGER AS $$
BEGIN
    -- Validate bronze path
    IF NEW.bronze_minio_key IS NOT NULL AND NOT (NEW.bronze_minio_key LIKE 'syniqai-bronze/%') THEN
        RAISE EXCEPTION 'Invalid bronze_minio_key: must start with syniqai-bronze/ but got %', NEW.bronze_minio_key;
    END IF;
    
    -- Validate silver path
    IF NEW.silver_minio_key IS NOT NULL AND NOT (NEW.silver_minio_key LIKE 'syniqai-silver/%') THEN
        RAISE EXCEPTION 'Invalid silver_minio_key: must start with syniqai-silver/ but got %', NEW.silver_minio_key;
    END IF;
    
    -- Ensure silver_minio_key exists when status is success
    IF NEW.extraction_status = 'success' AND NEW.silver_minio_key IS NULL THEN
        RAISE EXCEPTION 'silver_minio_key cannot be NULL when extraction_status is success';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validate_silver_asset_paths
BEFORE INSERT OR UPDATE ON silver_assets
FOR EACH ROW
EXECUTE FUNCTION validate_silver_asset_paths();

COMMENT ON FUNCTION validate_silver_asset_paths() IS 
'Validates MinIO paths and status consistency before INSERT/UPDATE';

-- Step 7: Verify migration success
DO $$
DECLARE
    total_assets INTEGER;
    successful_assets INTEGER;
    failed_assets INTEGER;
    pending_assets INTEGER;
    assets_with_both_keys INTEGER;
BEGIN
    SELECT COUNT(*) INTO total_assets FROM silver_assets;
    SELECT COUNT(*) INTO successful_assets FROM silver_assets WHERE extraction_status = 'success';
    SELECT COUNT(*) INTO failed_assets FROM silver_assets WHERE extraction_status = 'failed';
    SELECT COUNT(*) INTO pending_assets FROM silver_assets WHERE extraction_status = 'pending';
    SELECT COUNT(*) INTO assets_with_both_keys FROM silver_assets WHERE bronze_minio_key IS NOT NULL AND silver_minio_key IS NOT NULL;
    
    RAISE NOTICE '';
    RAISE NOTICE '╔════════════════════════════════════════════════════════════╗';
    RAISE NOTICE '║       Silver Assets Hardening Migration Complete!         ║';
    RAISE NOTICE '╚════════════════════════════════════════════════════════════╝';
    RAISE NOTICE '';
    RAISE NOTICE '✓ Added NOT NULL constraint on bronze_minio_key';
    RAISE NOTICE '✓ Added CHECK constraint: silver_key required when status=success';
    RAISE NOTICE '✓ Added PATH validation: bronze keys must start with syniqai-bronze/';
    RAISE NOTICE '✓ Added PATH validation: silver keys must start with syniqai-silver/';
    RAISE NOTICE '✓ Added performance indexes on (status, processed_at) and (file_type, processed_at)';
    RAISE NOTICE '✓ Created validation trigger: trg_validate_silver_asset_paths';
    RAISE NOTICE '✓ Created utility views: v_silver_failed_assets, v_silver_pending_assets, v_silver_success_summary';
    RAISE NOTICE '';
    RAISE NOTICE 'Current Stats:';
    RAISE NOTICE '  - Total assets:        %', total_assets;
    RAISE NOTICE '  - Successful:          %', successful_assets;
    RAISE NOTICE '  - Failed:              %', failed_assets;
    RAISE NOTICE '  - Pending:             %', pending_assets;
    RAISE NOTICE '  - With both keys:      %', assets_with_both_keys;
    RAISE NOTICE '';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '  1. Review failed assets: SELECT * FROM v_silver_failed_assets;';
    RAISE NOTICE '  2. Check pending queue: SELECT * FROM v_silver_pending_assets;';
    RAISE NOTICE '  3. View success summary: SELECT * FROM v_silver_success_summary;';
    RAISE NOTICE '';
END $$;

COMMIT;
