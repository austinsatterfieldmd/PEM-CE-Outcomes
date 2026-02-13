-- Migration 011: Add missing performance columns for Supabase-first writes
--
-- The SQLite question_activities table has per-activity performance scores
-- (pre_score, post_score, pre_n, post_n) that were previously skipped
-- during SQLite→Supabase sync. Now that import scripts write directly to
-- Supabase, these columns need to exist.
--
-- Similarly, demographic_performance needs pre_n and post_n for sample sizes.

-- Add per-activity performance columns to question_activities
ALTER TABLE question_activities ADD COLUMN IF NOT EXISTS pre_score REAL;
ALTER TABLE question_activities ADD COLUMN IF NOT EXISTS post_score REAL;
ALTER TABLE question_activities ADD COLUMN IF NOT EXISTS pre_n INTEGER;
ALTER TABLE question_activities ADD COLUMN IF NOT EXISTS post_n INTEGER;

-- Add sample size columns to demographic_performance
ALTER TABLE demographic_performance ADD COLUMN IF NOT EXISTS pre_n INTEGER;
ALTER TABLE demographic_performance ADD COLUMN IF NOT EXISTS post_n INTEGER;
