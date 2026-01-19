-- Migration 002: Add tables for human review workflow
-- Supports iterative prompt refinement based on corrections

-- Store human corrections for prompt refinement
CREATE TABLE IF NOT EXISTS review_corrections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER NOT NULL,
    voting_result_id INTEGER,  -- Links to the voting result being corrected
    iteration INTEGER NOT NULL,

    -- Original vs corrected tags
    original_tags JSON NOT NULL,
    corrected_tags JSON NOT NULL,

    -- Categorization for analysis
    disagreement_category TEXT,  -- e.g., "disease_ambiguity", "novel_treatment", "staging_confusion"
    tag_fields_changed JSON,     -- Which specific tag fields were corrected

    -- Reviewer info
    reviewer_notes TEXT,
    reviewer_id TEXT,  -- Optional: track who reviewed

    -- Timestamps
    reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (question_id) REFERENCES questions(id),
    FOREIGN KEY (voting_result_id) REFERENCES voting_results(id)
);

-- Index for analysis queries
CREATE INDEX IF NOT EXISTS idx_review_question_id ON review_corrections(question_id);
CREATE INDEX IF NOT EXISTS idx_review_iteration ON review_corrections(iteration);
CREATE INDEX IF NOT EXISTS idx_review_category ON review_corrections(disagreement_category);

-- Track disagreement patterns across iterations
CREATE TABLE IF NOT EXISTS disagreement_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    iteration INTEGER NOT NULL,

    -- Pattern identification
    category TEXT NOT NULL,
    subcategory TEXT,
    description TEXT,

    -- Frequency and examples
    frequency INTEGER NOT NULL DEFAULT 1,
    example_question_ids JSON,

    -- Resolution
    recommended_action TEXT,
    prompt_change_suggestion TEXT,
    implemented BOOLEAN DEFAULT FALSE,
    implemented_in_version TEXT,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pattern_iteration ON disagreement_patterns(iteration);
CREATE INDEX IF NOT EXISTS idx_pattern_category ON disagreement_patterns(category);
CREATE INDEX IF NOT EXISTS idx_pattern_implemented ON disagreement_patterns(implemented);
