-- Migration 012: Add eval_metrics table for LLM evaluation dashboard
--
-- Stores pre-computed evaluation metrics as JSONB so the Vercel frontend
-- can read them directly from Supabase without needing a FastAPI backend.
-- A Python script computes metrics from checkpoint files and uploads here.

CREATE TABLE IF NOT EXISTS eval_metrics (
    id SERIAL PRIMARY KEY,
    metrics JSONB NOT NULL,
    generated_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS: allow anyone to read, only service role to write
ALTER TABLE eval_metrics ENABLE ROW LEVEL SECURITY;

CREATE POLICY "eval_metrics_read_all" ON eval_metrics
    FOR SELECT USING (true);

CREATE POLICY "eval_metrics_insert_service" ON eval_metrics
    FOR INSERT WITH CHECK (auth.role() = 'service_role');

CREATE POLICY "eval_metrics_delete_service" ON eval_metrics
    FOR DELETE USING (auth.role() = 'service_role');
