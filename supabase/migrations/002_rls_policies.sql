-- =============================================================================
-- CE Outcomes Dashboard — Row Level Security Policies
-- Migration 002: RBAC enforcement via RLS
--
-- Roles:
--   admin  — Full access + user management
--   ma     — Full write access (edit tags, review, proposals)
--   user   — Read-only (default for new users)
--
-- Python import pipeline uses service_role key → bypasses RLS
-- =============================================================================

-- ============================================================
-- Enable RLS on all tables
-- ============================================================
ALTER TABLE questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE tags ENABLE ROW LEVEL SECURITY;
ALTER TABLE performance ENABLE ROW LEVEL SECURITY;
ALTER TABLE activities ENABLE ROW LEVEL SECURITY;
ALTER TABLE question_activities ENABLE ROW LEVEL SECURITY;
ALTER TABLE demographic_performance ENABLE ROW LEVEL SECURITY;
ALTER TABLE novel_entities ENABLE ROW LEVEL SECURITY;
ALTER TABLE novel_entity_occurrences ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_defined_values ENABLE ROW LEVEL SECURITY;
ALTER TABLE data_error_questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE duplicate_clusters ENABLE ROW LEVEL SECURITY;
ALTER TABLE cluster_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE duplicate_decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE tag_proposals ENABLE ROW LEVEL SECURITY;
ALTER TABLE tag_proposal_candidates ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_roles ENABLE ROW LEVEL SECURITY;

-- ============================================================
-- SELECT policies — All authenticated users can read everything
-- ============================================================
CREATE POLICY "select_questions" ON questions
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "select_tags" ON tags
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "select_performance" ON performance
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "select_activities" ON activities
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "select_question_activities" ON question_activities
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "select_demographic_performance" ON demographic_performance
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "select_novel_entities" ON novel_entities
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "select_novel_entity_occurrences" ON novel_entity_occurrences
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "select_user_defined_values" ON user_defined_values
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "select_data_error_questions" ON data_error_questions
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "select_duplicate_clusters" ON duplicate_clusters
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "select_cluster_members" ON cluster_members
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "select_duplicate_decisions" ON duplicate_decisions
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "select_tag_proposals" ON tag_proposals
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "select_tag_proposal_candidates" ON tag_proposal_candidates
    FOR SELECT USING (auth.role() = 'authenticated');

-- User roles: everyone can read (to see their own role)
CREATE POLICY "select_user_roles" ON user_roles
    FOR SELECT USING (auth.role() = 'authenticated');

-- ============================================================
-- INSERT/UPDATE/DELETE policies — MA + Admin can write
-- ============================================================

-- Tags: MA + Admin can update (review queue edits)
CREATE POLICY "update_tags" ON tags
    FOR UPDATE USING (get_user_role() IN ('admin', 'ma'));

-- Tags: MA + Admin can insert (new tagging results)
CREATE POLICY "insert_tags" ON tags
    FOR INSERT WITH CHECK (get_user_role() IN ('admin', 'ma'));

-- Questions: MA + Admin can update (stem edits, oncology status)
CREATE POLICY "update_questions" ON questions
    FOR UPDATE USING (get_user_role() IN ('admin', 'ma'));

-- Data errors: MA + Admin can manage
CREATE POLICY "insert_data_errors" ON data_error_questions
    FOR INSERT WITH CHECK (get_user_role() IN ('admin', 'ma'));

CREATE POLICY "delete_data_errors" ON data_error_questions
    FOR DELETE USING (get_user_role() IN ('admin', 'ma'));

-- User-defined values: MA + Admin can manage
CREATE POLICY "insert_user_values" ON user_defined_values
    FOR INSERT WITH CHECK (get_user_role() IN ('admin', 'ma'));

CREATE POLICY "delete_user_values" ON user_defined_values
    FOR DELETE USING (get_user_role() IN ('admin', 'ma'));

-- Novel entities: MA + Admin can manage
CREATE POLICY "update_novel_entities" ON novel_entities
    FOR UPDATE USING (get_user_role() IN ('admin', 'ma'));

CREATE POLICY "insert_novel_entities" ON novel_entities
    FOR INSERT WITH CHECK (get_user_role() IN ('admin', 'ma'));

-- Dedup clusters: MA + Admin can manage
CREATE POLICY "insert_dup_clusters" ON duplicate_clusters
    FOR INSERT WITH CHECK (get_user_role() IN ('admin', 'ma'));

CREATE POLICY "update_dup_clusters" ON duplicate_clusters
    FOR UPDATE USING (get_user_role() IN ('admin', 'ma'));

CREATE POLICY "insert_cluster_members" ON cluster_members
    FOR INSERT WITH CHECK (get_user_role() IN ('admin', 'ma'));

CREATE POLICY "insert_dup_decisions" ON duplicate_decisions
    FOR INSERT WITH CHECK (get_user_role() IN ('admin', 'ma'));

-- Tag proposals: MA + Admin can manage full lifecycle
CREATE POLICY "insert_proposals" ON tag_proposals
    FOR INSERT WITH CHECK (get_user_role() IN ('admin', 'ma'));

CREATE POLICY "update_proposals" ON tag_proposals
    FOR UPDATE USING (get_user_role() IN ('admin', 'ma'));

CREATE POLICY "delete_proposals" ON tag_proposals
    FOR DELETE USING (get_user_role() IN ('admin', 'ma'));

CREATE POLICY "insert_proposal_candidates" ON tag_proposal_candidates
    FOR INSERT WITH CHECK (get_user_role() IN ('admin', 'ma'));

CREATE POLICY "update_proposal_candidates" ON tag_proposal_candidates
    FOR UPDATE USING (get_user_role() IN ('admin', 'ma'));

-- Activities: MA + Admin can update metadata
CREATE POLICY "update_activities" ON activities
    FOR UPDATE USING (get_user_role() IN ('admin', 'ma'));

-- ============================================================
-- ADMIN-ONLY policies
-- ============================================================

-- Questions: Only admin can delete
CREATE POLICY "delete_questions" ON questions
    FOR DELETE USING (get_user_role() = 'admin');

-- Questions: Only admin can insert (import pipeline uses service_role)
CREATE POLICY "insert_questions" ON questions
    FOR INSERT WITH CHECK (get_user_role() = 'admin');

-- User roles: Only admin can manage
CREATE POLICY "insert_user_roles" ON user_roles
    FOR INSERT WITH CHECK (get_user_role() = 'admin');

CREATE POLICY "update_user_roles" ON user_roles
    FOR UPDATE USING (get_user_role() = 'admin');

CREATE POLICY "delete_user_roles" ON user_roles
    FOR DELETE USING (get_user_role() = 'admin');
