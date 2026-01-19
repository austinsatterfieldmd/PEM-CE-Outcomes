-- Migration 003: Add prompt version tracking
-- Tracks prompt versions and their performance metrics

-- Track prompt versions and performance
CREATE TABLE IF NOT EXISTS prompt_versions (
    version TEXT PRIMARY KEY,
    iteration INTEGER NOT NULL,

    -- Prompt content (or path to file)
    system_prompt_hash TEXT,  -- Hash of system prompt for change detection
    system_prompt_path TEXT,  -- Path to prompt file

    -- Associated data
    examples_hash TEXT,
    edge_cases_hash TEXT,

    -- Changes from previous version
    changelog TEXT,
    changes_from_previous JSON,

    -- Performance metrics (updated after each run)
    performance_metrics JSON,
    -- Expected structure:
    -- {
    --   "total_questions": 100,
    --   "unanimous_count": 70,
    --   "unanimous_rate": 0.70,
    --   "majority_count": 20,
    --   "majority_rate": 0.20,
    --   "conflict_count": 10,
    --   "conflict_rate": 0.10,
    --   "accuracy_after_review": 0.98,
    --   "avg_web_searches_per_question": 0.15
    -- }

    -- Status
    is_current BOOLEAN DEFAULT FALSE,
    is_deprecated BOOLEAN DEFAULT FALSE,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_prompt_iteration ON prompt_versions(iteration);
CREATE INDEX IF NOT EXISTS idx_prompt_current ON prompt_versions(is_current);

-- Track API costs per run
CREATE TABLE IF NOT EXISTS api_cost_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,  -- UUID for the batch run
    prompt_version TEXT NOT NULL,

    -- Question counts
    questions_processed INTEGER NOT NULL,

    -- Token usage by model
    gpt_input_tokens INTEGER DEFAULT 0,
    gpt_output_tokens INTEGER DEFAULT 0,
    claude_input_tokens INTEGER DEFAULT 0,
    claude_output_tokens INTEGER DEFAULT 0,
    gemini_input_tokens INTEGER DEFAULT 0,
    gemini_output_tokens INTEGER DEFAULT 0,
    search_tokens INTEGER DEFAULT 0,
    search_requests INTEGER DEFAULT 0,

    -- Calculated costs (in USD)
    gpt_cost REAL DEFAULT 0,
    claude_cost REAL DEFAULT 0,
    gemini_cost REAL DEFAULT 0,
    search_cost REAL DEFAULT 0,
    total_cost REAL DEFAULT 0,

    -- Timing
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds INTEGER,

    FOREIGN KEY (prompt_version) REFERENCES prompt_versions(version)
);

CREATE INDEX IF NOT EXISTS idx_cost_run_id ON api_cost_tracking(run_id);
CREATE INDEX IF NOT EXISTS idx_cost_prompt_version ON api_cost_tracking(prompt_version);
