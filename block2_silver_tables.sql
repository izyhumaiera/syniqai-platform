-- =============================================================================
-- Block 2: Silver Layer Tables for AI-Processed Assets
-- =============================================================================
-- This migration creates the tables needed for the AI processing pipeline:
--   1. silver_assets: Stores metadata and paths for AI-processed files
--   2. silver_quality_flags: Stores quality flags for processed assets
--
-- Run this migration after Block 1 is complete and before starting ai_processor.py
-- =============================================================================

-- Drop tables if they exist (for clean re-runs)
DROP TABLE IF EXISTS silver_quality_flags CASCADE;
DROP TABLE IF EXISTS silver_assets CASCADE;

-- Main table for AI-processed assets
CREATE TABLE silver_assets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source VARCHAR(255),                    -- Source system or upload method
  file_type VARCHAR(50),                  -- image, pdf, txt, docx, etc.
  bronze_minio_key VARCHAR(500) NOT NULL, -- Path to raw file in syniqai-bronze/
  silver_minio_key VARCHAR(500),          -- Path to AI output JSON in syniqai-silver/
  processed_at TIMESTAMPTZ,               -- When AI processing completed
  ai_model_used VARCHAR(255),             -- Actual model string used (e.g., qwen/qwen3-vl-8b-thinking)
  extraction_status VARCHAR(50) DEFAULT 'pending', -- pending | success | failed
  ai_confidence_score FLOAT,              -- Confidence score from AI model (0.0-1.0)
  file_size_bytes BIGINT,                 -- Size of original file in bytes
  content_tags JSONB,                     -- Tags extracted from AI processing
  summary TEXT,                           -- AI-generated summary
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Quality flags for processed assets (e.g., low confidence, incomplete OCR, etc.)
CREATE TABLE silver_quality_flags (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  asset_id UUID REFERENCES silver_assets(id) ON DELETE CASCADE,
  flag_type VARCHAR(100),                 -- low_confidence | ocr_incomplete | extraction_failed | etc.
  flag_value VARCHAR(500),                -- Additional context or value
  flagged_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_silver_assets_file_type ON silver_assets(file_type);
CREATE INDEX idx_silver_assets_status ON silver_assets(extraction_status);
CREATE INDEX idx_silver_assets_processed_at ON silver_assets(processed_at DESC);
CREATE INDEX idx_silver_assets_bronze_key ON silver_assets(bronze_minio_key);
CREATE INDEX idx_silver_quality_flags_asset_id ON silver_quality_flags(asset_id);
CREATE INDEX idx_silver_quality_flags_type ON silver_quality_flags(flag_type);

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_silver_assets_updated_at BEFORE UPDATE ON silver_assets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Success message
DO $$
BEGIN
    RAISE NOTICE '✓ Silver layer tables created successfully';
    RAISE NOTICE '  - silver_assets: Stores AI-processed asset metadata';
    RAISE NOTICE '  - silver_quality_flags: Stores quality flags for assets';
    RAISE NOTICE '';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '  1. Update .env with OPENROUTER_API_KEY and OPENROUTER_MODEL';
    RAISE NOTICE '  2. Start ai_processor.py to begin processing bronze-ready files';
    RAISE NOTICE '  3. Monitor silver-ready Kafka topic for processed files';
END $$;
