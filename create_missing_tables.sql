-- Migration to create missing PostgreSQL tables for SyniqAI
-- Run this against syniqai_metadata database

CREATE TABLE IF NOT EXISTS bronze_assets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source VARCHAR,
  file_type VARCHAR,
  bronze_minio_key VARCHAR NOT NULL,
  original_filename VARCHAR,
  size_bytes BIGINT,
  domain VARCHAR DEFAULT 'general',
  ingested_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS routing_config (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  data_type VARCHAR NOT NULL UNIQUE,
  model_id VARCHAR NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT now()
);

INSERT INTO routing_config (data_type, model_id) VALUES
  ('image', 'qwen/qwen3-vl-8b-thinking'),
  ('pdf_scanned', 'qwen/qwen3-vl-8b-thinking'),
  ('pdf_text', 'qwen/qwen3-8b'),
  ('txt', 'qwen/qwen3-8b'),
  ('docx', 'qwen/qwen3-8b'),
  ('audio', 'openai/gpt-audio-mini'),
  ('video', 'qwen/qwen3-vl-8b-thinking')
ON CONFLICT (data_type) DO NOTHING;

CREATE TABLE IF NOT EXISTS pipeline_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_type VARCHAR,
  status VARCHAR DEFAULT 'pending',
  source VARCHAR,
  file_type VARCHAR,
  bronze_minio_key VARCHAR,
  error_message TEXT,
  started_at TIMESTAMPTZ DEFAULT now(),
  completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS data_lineage (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  asset_id UUID,
  event_type VARCHAR,
  source_bucket VARCHAR,
  dest_bucket VARCHAR,
  model_used VARCHAR,
  event_time TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS data_quality_metrics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  asset_id UUID REFERENCES silver_assets(id),
  metric_name VARCHAR,
  metric_value FLOAT,
  recorded_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS gold_lineage (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  asset_id UUID REFERENCES silver_assets(id),
  event_type VARCHAR,
  event_time TIMESTAMPTZ DEFAULT now(),
  model_used VARCHAR,
  quality_score FLOAT,
  source_bucket VARCHAR,
  dest_bucket VARCHAR
);

CREATE MATERIALIZED VIEW IF NOT EXISTS gold_assets AS
SELECT
  sa.id, sa.source, sa.file_type, sa.summary,
  sa.content_tags, sa.ai_confidence_score,
  sa.silver_minio_key, sa.bronze_minio_key,
  sa.processed_at, sa.ai_model_used
FROM silver_assets sa
WHERE sa.extraction_status = 'success';

CREATE UNIQUE INDEX IF NOT EXISTS gold_assets_id_idx ON gold_assets (id);
