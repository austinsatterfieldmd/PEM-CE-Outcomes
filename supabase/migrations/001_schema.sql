-- =============================================================================
-- CE Outcomes Dashboard — PostgreSQL Schema for Supabase
-- Migration 001: Full schema creation (17 tables + indexes + FTS + RBAC)
--
-- Run this in Supabase SQL Editor or via supabase db push
-- =============================================================================

-- ============================================================
-- 1. QUESTIONS — Core question data
-- ============================================================
CREATE TABLE IF NOT EXISTS questions (
    id SERIAL PRIMARY KEY,
    source_question_id INTEGER,                    -- Original question ID from source system
    source_id INTEGER,                             -- QUESTIONGROUPDESIGNATION (links to Snowflake)
    question_stem TEXT NOT NULL,
    correct_answer TEXT,
    incorrect_answers TEXT,                         -- JSON array of incorrect answer strings
    source_file TEXT,
    canonical_source_id TEXT,                       -- For dedup: points to canonical question's source_id
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- 2. TAGS — 70+ field tag schema (one row per question)
-- ============================================================
CREATE TABLE IF NOT EXISTS tags (
    question_id INTEGER PRIMARY KEY REFERENCES questions(id) ON DELETE CASCADE,

    -- Legacy core fields (kept for backward compat)
    topic TEXT,
    topic_confidence REAL,
    topic_method TEXT,
    disease_state TEXT,
    disease_state_confidence REAL,
    disease_stage TEXT,
    disease_stage_confidence REAL,
    disease_type TEXT,
    disease_type_confidence REAL,
    treatment_line TEXT,
    treatment_line_confidence REAL,
    treatment TEXT,
    treatment_confidence REAL,
    biomarker TEXT,
    biomarker_confidence REAL,
    trial TEXT,
    trial_confidence REAL,
    review_flags TEXT,                              -- JSON array: ['LLM_FALLBACK', 'LOW_CONFIDENCE', etc.]
    needs_review BOOLEAN DEFAULT FALSE,
    overall_confidence REAL,
    llm_calls_made INTEGER DEFAULT 0,
    flagged_at TIMESTAMPTZ,

    -- Split disease fields
    disease_state_1 TEXT,
    disease_state_2 TEXT,
    disease_type_1 TEXT,
    disease_type_2 TEXT,

    -- Multi-value treatment fields (5 slots)
    treatment_1 TEXT,
    treatment_2 TEXT,
    treatment_3 TEXT,
    treatment_4 TEXT,
    treatment_5 TEXT,

    -- Multi-value biomarker fields (5 slots)
    biomarker_1 TEXT,
    biomarker_2 TEXT,
    biomarker_3 TEXT,
    biomarker_4 TEXT,
    biomarker_5 TEXT,

    -- Multi-value trial fields (5 slots)
    trial_1 TEXT,
    trial_2 TEXT,
    trial_3 TEXT,
    trial_4 TEXT,
    trial_5 TEXT,

    -- Group B: Patient Characteristics
    treatment_eligibility TEXT,
    age_group TEXT,
    organ_dysfunction TEXT,
    fitness_status TEXT,
    disease_specific_factor TEXT,
    comorbidity_1 TEXT,
    comorbidity_2 TEXT,
    comorbidity_3 TEXT,

    -- Group C: Treatment Metadata
    drug_class_1 TEXT,
    drug_class_2 TEXT,
    drug_class_3 TEXT,
    drug_target_1 TEXT,
    drug_target_2 TEXT,
    drug_target_3 TEXT,
    prior_therapy_1 TEXT,
    prior_therapy_2 TEXT,
    prior_therapy_3 TEXT,
    resistance_mechanism TEXT,

    -- Group D: Clinical Context
    metastatic_site_1 TEXT,
    metastatic_site_2 TEXT,
    metastatic_site_3 TEXT,
    symptom_1 TEXT,
    symptom_2 TEXT,
    symptom_3 TEXT,
    performance_status TEXT,

    -- Group E: Safety/Toxicity
    toxicity_type_1 TEXT,
    toxicity_type_2 TEXT,
    toxicity_type_3 TEXT,
    toxicity_type_4 TEXT,
    toxicity_type_5 TEXT,
    toxicity_organ TEXT,
    toxicity_grade TEXT,

    -- Group F: Efficacy/Outcomes
    efficacy_endpoint_1 TEXT,
    efficacy_endpoint_2 TEXT,
    efficacy_endpoint_3 TEXT,
    outcome_context TEXT,
    clinical_benefit TEXT,

    -- Group G: Evidence/Guidelines
    guideline_source_1 TEXT,
    guideline_source_2 TEXT,
    evidence_type TEXT,

    -- Group H: Question Format/Quality
    cme_outcome_level TEXT,
    data_response_type TEXT,
    stem_type TEXT,
    lead_in_type TEXT,
    answer_format TEXT,
    answer_length_pattern TEXT,
    distractor_homogeneity TEXT,
    flaw_absolute_terms BOOLEAN,
    flaw_grammatical_cue BOOLEAN,
    flaw_implausible_distractor BOOLEAN,
    flaw_clang_association BOOLEAN,
    flaw_convergence_vulnerability BOOLEAN,
    flaw_double_negative BOOLEAN,

    -- Computed Fields
    answer_option_count INTEGER,
    correct_answer_position TEXT,

    -- Review metadata
    review_reason TEXT,
    agreement_level TEXT,

    -- Audit trail for human edits
    edited_by_user BOOLEAN DEFAULT FALSE,
    edited_at TIMESTAMPTZ,
    edited_fields TEXT,                             -- JSON array of edited field names
    review_notes TEXT,                              -- Reviewer comments

    -- Tag agreement status
    tag_status TEXT,                                -- 'verified', 'unanimous', 'majority', 'conflict'
    worst_case_agreement TEXT,                      -- Same values, across ALL field_votes

    -- Special populations (added to match normalizer fields)
    special_population_1 TEXT,
    special_population_2 TEXT,

    -- QCore Score
    qcore_score REAL,                              -- 0-100 quality score
    qcore_grade TEXT,                              -- A, B, C, D
    qcore_breakdown TEXT,                          -- JSON: {flaws: {}, structure_deductions: {}, structure_bonuses: {}}
    qcore_scored_at TIMESTAMPTZ,

    updated_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- 3. PERFORMANCE — Aggregate performance by audience segment
-- ============================================================
CREATE TABLE IF NOT EXISTS performance (
    id SERIAL PRIMARY KEY,
    question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    segment TEXT NOT NULL,                          -- 'overall', 'medical_oncologist', 'app', etc.
    pre_score REAL,
    post_score REAL,
    pre_n INTEGER,
    post_n INTEGER,
    UNIQUE(question_id, segment)
);

-- ============================================================
-- 4. ACTIVITIES — Course/activity metadata
-- ============================================================
CREATE TABLE IF NOT EXISTS activities (
    id SERIAL PRIMARY KEY,
    activity_name TEXT NOT NULL UNIQUE,
    activity_date DATE,
    quarter TEXT,                                   -- e.g. '2024 Q3'
    target_audience TEXT,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- 5. QUESTION_ACTIVITIES — Many-to-many: questions <-> activities
-- ============================================================
CREATE TABLE IF NOT EXISTS question_activities (
    id SERIAL PRIMARY KEY,
    question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    activity_name TEXT NOT NULL,
    activity_id INTEGER REFERENCES activities(id) ON DELETE SET NULL,
    activity_date DATE,
    quarter TEXT,
    UNIQUE(question_id, activity_name)
);

-- ============================================================
-- 6. DEMOGRAPHIC_PERFORMANCE — Granular performance by specialty/region
-- ============================================================
CREATE TABLE IF NOT EXISTS demographic_performance (
    id SERIAL PRIMARY KEY,
    question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    activity_id INTEGER REFERENCES activities(id) ON DELETE SET NULL,
    specialty TEXT,
    practice_setting TEXT,
    practice_state TEXT,
    region TEXT,
    pre_score REAL,
    post_score REAL,
    n_respondents INTEGER
);

-- ============================================================
-- 7. NOVEL_ENTITIES — LLM-extracted entities not in knowledge base
-- ============================================================
CREATE TABLE IF NOT EXISTS novel_entities (
    id SERIAL PRIMARY KEY,
    entity_name TEXT NOT NULL,
    entity_type TEXT NOT NULL,                      -- 'treatment', 'trial', 'disease', 'biomarker'
    normalized_name TEXT,
    confidence REAL DEFAULT 0.75,
    occurrence_count INTEGER DEFAULT 1,
    first_seen TIMESTAMPTZ DEFAULT now(),
    last_seen TIMESTAMPTZ DEFAULT now(),
    status TEXT DEFAULT 'pending',                  -- 'pending', 'approved', 'rejected', 'auto_approved'
    reviewed_by TEXT,
    reviewed_at TIMESTAMPTZ,
    drug_class TEXT,
    synonyms TEXT,                                  -- JSON array
    notes TEXT,
    UNIQUE(entity_name, entity_type)
);

-- ============================================================
-- 8. NOVEL_ENTITY_OCCURRENCES — Which questions surfaced each entity
-- ============================================================
CREATE TABLE IF NOT EXISTS novel_entity_occurrences (
    id SERIAL PRIMARY KEY,
    novel_entity_id INTEGER NOT NULL REFERENCES novel_entities(id) ON DELETE CASCADE,
    question_id INTEGER REFERENCES questions(id) ON DELETE SET NULL,
    source_text TEXT NOT NULL,
    extraction_confidence REAL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- 9. USER_DEFINED_VALUES — Custom dropdown values entered by users
-- ============================================================
CREATE TABLE IF NOT EXISTS user_defined_values (
    id SERIAL PRIMARY KEY,
    field_name TEXT NOT NULL,
    value TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    created_by TEXT,
    UNIQUE(field_name, value)
);

-- ============================================================
-- 10. DATA_ERROR_QUESTIONS — Questions flagged for data quality issues
-- ============================================================
CREATE TABLE IF NOT EXISTS data_error_questions (
    id SERIAL PRIMARY KEY,
    question_id INTEGER NOT NULL UNIQUE REFERENCES questions(id) ON DELETE CASCADE,
    error_type TEXT NOT NULL,
    error_details TEXT,
    reported_by TEXT DEFAULT 'user',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- 11. DUPLICATE_CLUSTERS — Groups of similar questions
-- ============================================================
CREATE TABLE IF NOT EXISTS duplicate_clusters (
    cluster_id SERIAL PRIMARY KEY,
    canonical_question_id INTEGER REFERENCES questions(id),
    canonical_source_id TEXT,
    status TEXT DEFAULT 'pending',                  -- 'pending', 'confirmed', 'rejected'
    similarity_threshold REAL,                      -- 0.90 or 0.95
    created_at TIMESTAMPTZ DEFAULT now(),
    reviewed_at TIMESTAMPTZ,
    reviewed_by TEXT
);

-- ============================================================
-- 12. CLUSTER_MEMBERS — Questions belonging to each cluster
-- ============================================================
CREATE TABLE IF NOT EXISTS cluster_members (
    id SERIAL PRIMARY KEY,
    cluster_id INTEGER REFERENCES duplicate_clusters(cluster_id) ON DELETE CASCADE,
    question_id INTEGER REFERENCES questions(id) ON DELETE CASCADE,
    source_id TEXT,
    similarity_to_canonical REAL,
    is_canonical BOOLEAN DEFAULT FALSE,
    UNIQUE(cluster_id, question_id)
);

-- ============================================================
-- 13. DUPLICATE_DECISIONS — Audit trail for dedup decisions
-- ============================================================
CREATE TABLE IF NOT EXISTS duplicate_decisions (
    id SERIAL PRIMARY KEY,
    cluster_id INTEGER REFERENCES duplicate_clusters(cluster_id),
    question_id_1 INTEGER,
    question_id_2 INTEGER,
    similarity_score REAL,
    decision TEXT,                                  -- 'duplicate', 'not_duplicate', 'undecided'
    decided_at TIMESTAMPTZ DEFAULT now(),
    decided_by TEXT
);

-- ============================================================
-- 14. TAG_PROPOSALS — Proposed tag values for retroactive application
-- ============================================================
CREATE TABLE IF NOT EXISTS tag_proposals (
    id SERIAL PRIMARY KEY,
    field_name TEXT NOT NULL,
    proposed_value TEXT NOT NULL,
    search_query TEXT,
    proposal_reason TEXT,
    status TEXT DEFAULT 'pending',                  -- 'pending', 'approved', 'rejected'
    match_count INTEGER DEFAULT 0,
    approved_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    created_by TEXT,
    completed_at TIMESTAMPTZ
);

-- ============================================================
-- 15. TAG_PROPOSAL_CANDIDATES — Questions matching proposal search
-- ============================================================
CREATE TABLE IF NOT EXISTS tag_proposal_candidates (
    id SERIAL PRIMARY KEY,
    proposal_id INTEGER REFERENCES tag_proposals(id) ON DELETE CASCADE,
    question_id INTEGER REFERENCES questions(id) ON DELETE CASCADE,
    match_score REAL,
    current_value TEXT,
    decision TEXT DEFAULT 'pending',                -- 'pending', 'approved', 'rejected'
    decided_at TIMESTAMPTZ,
    decided_by TEXT,
    notes TEXT,
    UNIQUE(proposal_id, question_id)
);

-- ============================================================
-- 16. (QCore scores embedded in tags table — no separate table needed)
-- ============================================================

-- ============================================================
-- 17. USER_ROLES — RBAC: maps auth.users to admin/ma/user
-- ============================================================
CREATE TABLE IF NOT EXISTS user_roles (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('admin', 'ma', 'user')),
    assigned_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id)
);


-- =============================================================================
-- INDEXES
-- =============================================================================

-- Tags indexes (most-queried fields)
CREATE INDEX IF NOT EXISTS idx_tags_topic ON tags(topic);
CREATE INDEX IF NOT EXISTS idx_tags_disease_state ON tags(disease_state);
CREATE INDEX IF NOT EXISTS idx_tags_disease_stage ON tags(disease_stage);
CREATE INDEX IF NOT EXISTS idx_tags_disease_type ON tags(disease_type);
CREATE INDEX IF NOT EXISTS idx_tags_disease_type_1 ON tags(disease_type_1);
CREATE INDEX IF NOT EXISTS idx_tags_treatment_line ON tags(treatment_line);
CREATE INDEX IF NOT EXISTS idx_tags_treatment ON tags(treatment);
CREATE INDEX IF NOT EXISTS idx_tags_treatment_1 ON tags(treatment_1);
CREATE INDEX IF NOT EXISTS idx_tags_biomarker ON tags(biomarker);
CREATE INDEX IF NOT EXISTS idx_tags_biomarker_1 ON tags(biomarker_1);
CREATE INDEX IF NOT EXISTS idx_tags_trial ON tags(trial);
CREATE INDEX IF NOT EXISTS idx_tags_trial_1 ON tags(trial_1);
CREATE INDEX IF NOT EXISTS idx_tags_needs_review ON tags(needs_review);
CREATE INDEX IF NOT EXISTS idx_tags_tag_status ON tags(tag_status);
CREATE INDEX IF NOT EXISTS idx_tags_edited_by_user ON tags(edited_by_user);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_performance_segment ON performance(segment);
CREATE INDEX IF NOT EXISTS idx_performance_question ON performance(question_id);

-- Activity indexes
CREATE INDEX IF NOT EXISTS idx_activities_name ON question_activities(activity_name);
CREATE INDEX IF NOT EXISTS idx_qa_quarter ON question_activities(quarter);
CREATE INDEX IF NOT EXISTS idx_qa_activity_date ON question_activities(activity_date);
CREATE INDEX IF NOT EXISTS idx_activities_quarter ON activities(quarter);
CREATE INDEX IF NOT EXISTS idx_activities_date ON activities(activity_date);

-- Demographic performance indexes
CREATE INDEX IF NOT EXISTS idx_demo_perf_specialty ON demographic_performance(specialty);
CREATE INDEX IF NOT EXISTS idx_demo_perf_setting ON demographic_performance(practice_setting);
CREATE INDEX IF NOT EXISTS idx_demo_perf_region ON demographic_performance(region);
CREATE INDEX IF NOT EXISTS idx_demo_perf_activity ON demographic_performance(activity_id);

-- Novel entity indexes
CREATE INDEX IF NOT EXISTS idx_novel_entities_status ON novel_entities(status);
CREATE INDEX IF NOT EXISTS idx_novel_entities_type ON novel_entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_novel_occurrences_entity ON novel_entity_occurrences(novel_entity_id);

-- User-defined values
CREATE INDEX IF NOT EXISTS idx_user_defined_values_field ON user_defined_values(field_name);

-- Dedup indexes
CREATE INDEX IF NOT EXISTS idx_dup_clusters_status ON duplicate_clusters(status);
CREATE INDEX IF NOT EXISTS idx_cluster_members_cluster ON cluster_members(cluster_id);
CREATE INDEX IF NOT EXISTS idx_cluster_members_question ON cluster_members(question_id);

-- Tag proposal indexes
CREATE INDEX IF NOT EXISTS idx_tag_proposals_status ON tag_proposals(status);
CREATE INDEX IF NOT EXISTS idx_tag_proposals_field ON tag_proposals(field_name);
CREATE INDEX IF NOT EXISTS idx_proposal_candidates_proposal ON tag_proposal_candidates(proposal_id);
CREATE INDEX IF NOT EXISTS idx_proposal_candidates_question ON tag_proposal_candidates(question_id);
CREATE INDEX IF NOT EXISTS idx_proposal_candidates_decision ON tag_proposal_candidates(decision);

-- Questions indexes
CREATE INDEX IF NOT EXISTS idx_questions_source_id ON questions(source_id);
CREATE INDEX IF NOT EXISTS idx_questions_canonical_source ON questions(canonical_source_id);

-- Data error indexes
CREATE INDEX IF NOT EXISTS idx_data_error_question ON data_error_questions(question_id);

-- User roles
CREATE INDEX IF NOT EXISTS idx_user_roles_user ON user_roles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_roles_role ON user_roles(role);


-- =============================================================================
-- FULL-TEXT SEARCH (replaces SQLite FTS5)
-- =============================================================================

-- Add tsvector column for full-text search
ALTER TABLE questions ADD COLUMN IF NOT EXISTS fts_vector tsvector;

-- GIN index for fast full-text search
CREATE INDEX IF NOT EXISTS idx_questions_fts ON questions USING GIN(fts_vector);

-- Trigger function: auto-update fts_vector on INSERT/UPDATE
CREATE OR REPLACE FUNCTION questions_fts_update() RETURNS trigger AS $$
BEGIN
    NEW.fts_vector := to_tsvector('english',
        coalesce(NEW.question_stem, '') || ' ' || coalesce(NEW.correct_answer, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Attach trigger
DROP TRIGGER IF EXISTS questions_fts_trigger ON questions;
CREATE TRIGGER questions_fts_trigger
    BEFORE INSERT OR UPDATE OF question_stem, correct_answer
    ON questions
    FOR EACH ROW
    EXECUTE FUNCTION questions_fts_update();


-- Backfill function for bulk data migration (run once after initial migration)
CREATE OR REPLACE FUNCTION backfill_fts_vectors() RETURNS void AS $$
BEGIN
    UPDATE questions
    SET fts_vector = to_tsvector('english',
        coalesce(question_stem, '') || ' ' || coalesce(correct_answer, ''))
    WHERE fts_vector IS NULL;
END;
$$ LANGUAGE plpgsql;


-- =============================================================================
-- RBAC HELPER FUNCTION
-- =============================================================================

-- Returns the role of the currently authenticated user (defaults to 'user')
CREATE OR REPLACE FUNCTION get_user_role() RETURNS TEXT AS $$
    SELECT COALESCE(
        (SELECT role FROM user_roles WHERE user_id = auth.uid()),
        'user'
    );
$$ LANGUAGE sql SECURITY DEFINER STABLE;

-- Expose get_user_role via RPC for frontend use
-- (Already accessible as supabase.rpc('get_user_role'))


-- =============================================================================
-- AUTO-UPDATE updated_at ON TAGS
-- =============================================================================

CREATE OR REPLACE FUNCTION update_tags_timestamp() RETURNS trigger AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tags_updated_at ON tags;
CREATE TRIGGER tags_updated_at
    BEFORE UPDATE ON tags
    FOR EACH ROW
    EXECUTE FUNCTION update_tags_timestamp();
