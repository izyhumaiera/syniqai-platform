-- ============================================================================
-- Fix Missing Timestamp Columns in silver_assets
-- ============================================================================
-- This script adds created_at and updated_at columns if they're missing

-- Add created_at column if it doesn't exist
ALTER TABLE silver_assets 
ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();

-- Add updated_at column if it doesn't exist
ALTER TABLE silver_assets 
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- Update existing rows to have timestamps
UPDATE silver_assets 
SET created_at = COALESCE(processed_at, NOW()),
    updated_at = COALESCE(processed_at, NOW())
WHERE created_at IS NULL OR updated_at IS NULL;

-- Recreate the updated_at trigger (in case it doesn't exist)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Drop trigger if exists, then recreate
DROP TRIGGER IF EXISTS update_silver_assets_updated_at ON silver_assets;
CREATE TRIGGER update_silver_assets_updated_at BEFORE UPDATE ON silver_assets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Verify the columns exist
SELECT 
    column_name, 
    data_type, 
    column_default,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'silver_assets' 
  AND column_name IN ('created_at', 'updated_at')
ORDER BY column_name;

-- Success message
DO $$
BEGIN
    RAISE NOTICE '✓ Timestamp columns fixed in silver_assets table';
    RAISE NOTICE '  - created_at: Added/verified';
    RAISE NOTICE '  - updated_at: Added/verified';
    RAISE NOTICE '  - Update trigger: Created';
END $$;
