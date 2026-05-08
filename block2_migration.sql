-- ============================================================================
-- Block 2 Database Migration - Add model tracking to silver_assets
-- ============================================================================
-- Run this script in pgAdmin or psql to add new columns for model selection tracking

-- Add model_was_overridden column to silver_assets
ALTER TABLE silver_assets 
ADD COLUMN IF NOT EXISTS model_was_overridden BOOLEAN DEFAULT FALSE;

-- Add comment for documentation
COMMENT ON COLUMN silver_assets.model_was_overridden IS 
'True if user manually selected the AI model for this file (override), False if default routing was used';

-- Update existing rows to default FALSE
UPDATE silver_assets 
SET model_was_overridden = FALSE 
WHERE model_was_overridden IS NULL;

-- Create routing_config table (already handled by settings_routes.py, but included for completeness)
CREATE TABLE IF NOT EXISTS routing_config (
    id SERIAL PRIMARY KEY,
    data_type VARCHAR(50) UNIQUE NOT NULL,
    model_id VARCHAR(200) NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(100) DEFAULT 'admin'
);

CREATE INDEX IF NOT EXISTS idx_routing_config_data_type ON routing_config(data_type);

-- Insert default routing configuration
INSERT INTO routing_config (data_type, model_id, updated_at, updated_by)
VALUES 
    ('image', 'qwen/qwen-2-vl-72b-instruct', CURRENT_TIMESTAMP, 'system'),
    ('scanned_pdf', 'qwen/qwen-2-vl-72b-instruct', CURRENT_TIMESTAMP, 'system'),
    ('plain_text', 'qwen/qwen-2.5-72b-instruct', CURRENT_TIMESTAMP, 'system'),
    ('audio', 'openai/whisper-large-v3', CURRENT_TIMESTAMP, 'system'),
    ('video', 'qwen/qwen-2-vl-72b-instruct', CURRENT_TIMESTAMP, 'system'),
    ('structured', 'none', CURRENT_TIMESTAMP, 'system')
ON CONFLICT (data_type) DO NOTHING;

-- Verify migration
SELECT 
    column_name, 
    data_type, 
    column_default,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'silver_assets' 
  AND column_name IN ('ai_model_used', 'model_was_overridden')
ORDER BY column_name;

-- Verify routing_config
SELECT * FROM routing_config ORDER BY data_type;

-- Success message
DO $$
BEGIN
    RAISE NOTICE '✓ Block 2 database migration complete';
    RAISE NOTICE '  - Added model_was_overridden to silver_assets';
    RAISE NOTICE '  - Created routing_config table';
    RAISE NOTICE '  - Inserted default routing configuration';
END $$;
