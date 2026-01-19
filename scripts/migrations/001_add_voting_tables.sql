-- Migration 001: Add voting tables for 3-model LLM voting system
-- Run this after migrating the V2 database to V3

-- Store 3-model voting results for each question
CREATE TABLE IF NOT EXISTS voting_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER NOT NULL,
    iteration INTEGER NOT NULL DEFAULT 1,
    prompt_version TEXT NOT NULL,

    -- Individual model responses (JSON)
    gpt_tags JSON NOT NULL,
    claude_tags JSON NOT NULL,
    gemini_tags JSON NOT NULL,

    -- Aggregated result
    aggregated_tags JSON NOT NULL,

    -- Agreement metrics
    agreement_level TEXT CHECK(agreement_level IN ('unanimous', 'majority', 'conflict')),
    agreement_details JSON,  -- Which tags agreed/disagreed

    -- Review status
    needs_review BOOLEAN DEFAULT FALSE,
    review_priority INTEGER DEFAULT 0,  -- Higher = more urgent

    -- Web search usage
    web_searches JSON,  -- Log of web searches triggered

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (question_id) REFERENCES questions(id)
);

-- Index for efficient queries
CREATE INDEX IF NOT EXISTS idx_voting_question_id ON voting_results(question_id);
CREATE INDEX IF NOT EXISTS idx_voting_needs_review ON voting_results(needs_review);
CREATE INDEX IF NOT EXISTS idx_voting_agreement ON voting_results(agreement_level);
CREATE INDEX IF NOT EXISTS idx_voting_iteration ON voting_results(iteration);
