-- =============================================================================
-- CE Outcomes Dashboard — Fix aggregate_by_tag + add segment comparison
-- Migration 013: Complete rewrite of reporting RPCs
--
-- Fixes:
--   1. Missing WHERE clauses for disease_types, treatments, biomarkers, trials
--   2. Wrong aggregation math (AVG of percentages → weighted average)
--   3. Expanded group-by column mapping (7 → 25 fields)
--   4. New aggregate_by_tag_with_segments() for audience comparison
-- =============================================================================


-- =============================================================================
-- 1. REPLACE aggregate_by_tag() — Full filter support + weighted averages
-- =============================================================================
DROP FUNCTION IF EXISTS aggregate_by_tag(TEXT, TEXT[], TEXT[], TEXT[], TEXT[], TEXT[], TEXT[], TEXT[]);

CREATE OR REPLACE FUNCTION aggregate_by_tag(
    p_group_by TEXT,
    p_topics TEXT[] DEFAULT NULL,
    p_disease_states TEXT[] DEFAULT NULL,
    p_disease_stages TEXT[] DEFAULT NULL,
    p_disease_types TEXT[] DEFAULT NULL,
    p_treatment_lines TEXT[] DEFAULT NULL,
    p_treatments TEXT[] DEFAULT NULL,
    p_biomarkers TEXT[] DEFAULT NULL,
    p_trials TEXT[] DEFAULT NULL,
    p_activities TEXT[] DEFAULT NULL,
    p_quarters TEXT[] DEFAULT NULL
)
RETURNS JSON AS $$
DECLARE
    v_col TEXT;
    v_where TEXT;
    v_activity_join TEXT := '';
    v_result JSON;
BEGIN
    -- Validate and map group_by to actual column (prevents SQL injection)
    v_col := CASE p_group_by
        -- Core fields
        WHEN 'topic' THEN 't.topic'
        WHEN 'disease_state' THEN 'COALESCE(t.disease_state_1, t.disease_state)'
        WHEN 'disease_stage' THEN 't.disease_stage'
        WHEN 'disease_type' THEN 't.disease_type_1'
        WHEN 'treatment_line' THEN 't.treatment_line'
        WHEN 'treatment' THEN 't.treatment_1'
        WHEN 'biomarker' THEN 't.biomarker_1'
        WHEN 'trial' THEN 't.trial_1'
        -- Treatment metadata
        WHEN 'drug_class' THEN 't.drug_class_1'
        WHEN 'drug_target' THEN 't.drug_target_1'
        -- Patient characteristics
        WHEN 'treatment_eligibility' THEN 't.treatment_eligibility'
        WHEN 'age_group' THEN 't.age_group'
        WHEN 'fitness_status' THEN 't.fitness_status'
        WHEN 'organ_dysfunction' THEN 't.organ_dysfunction'
        -- Clinical context
        WHEN 'metastatic_site' THEN 't.metastatic_site_1'
        WHEN 'performance_status' THEN 't.performance_status'
        -- Safety/Toxicity
        WHEN 'toxicity_type' THEN 't.toxicity_type_1'
        WHEN 'toxicity_organ' THEN 't.toxicity_organ'
        WHEN 'toxicity_grade' THEN 't.toxicity_grade'
        -- Efficacy/Outcomes
        WHEN 'efficacy_endpoint' THEN 't.efficacy_endpoint_1'
        WHEN 'outcome_context' THEN 't.outcome_context'
        WHEN 'clinical_benefit' THEN 't.clinical_benefit'
        -- Evidence/Guidelines
        WHEN 'guideline_source' THEN 't.guideline_source_1'
        WHEN 'evidence_type' THEN 't.evidence_type'
        -- Question quality
        WHEN 'cme_outcome_level' THEN 't.cme_outcome_level'
        ELSE NULL
    END;

    IF v_col IS NULL THEN
        RETURN json_build_object('error', 'Invalid group_by field: ' || p_group_by);
    END IF;

    -- Base filters: oncology, canonical, not data error, group-by column not null
    v_where := '(q.is_oncology IS NULL OR q.is_oncology = TRUE)'
        || ' AND (q.canonical_source_id IS NULL OR q.canonical_source_id = CAST(q.source_id AS TEXT))'
        || ' AND q.id NOT IN (SELECT question_id FROM data_error_questions)'
        || ' AND ' || v_col || ' IS NOT NULL AND ' || v_col || ' != ''''';

    -- ── Tag filters ──

    IF p_topics IS NOT NULL THEN
        v_where := v_where || ' AND t.topic = ANY(' || quote_literal(p_topics::TEXT) || '::TEXT[])';
    END IF;

    IF p_disease_states IS NOT NULL THEN
        v_where := v_where || ' AND (COALESCE(t.disease_state_1, t.disease_state) = ANY('
            || quote_literal(p_disease_states::TEXT) || '::TEXT[])'
            || ' OR t.disease_state_2 = ANY(' || quote_literal(p_disease_states::TEXT) || '::TEXT[]))';
    END IF;

    IF p_disease_stages IS NOT NULL THEN
        v_where := v_where || ' AND t.disease_stage = ANY(' || quote_literal(p_disease_stages::TEXT) || '::TEXT[])';
    END IF;

    IF p_disease_types IS NOT NULL THEN
        v_where := v_where || ' AND (t.disease_type_1 = ANY(' || quote_literal(p_disease_types::TEXT) || '::TEXT[])'
            || ' OR t.disease_type_2 = ANY(' || quote_literal(p_disease_types::TEXT) || '::TEXT[]))';
    END IF;

    IF p_treatment_lines IS NOT NULL THEN
        v_where := v_where || ' AND t.treatment_line = ANY(' || quote_literal(p_treatment_lines::TEXT) || '::TEXT[])';
    END IF;

    IF p_treatments IS NOT NULL THEN
        v_where := v_where || ' AND (t.treatment_1 = ANY(' || quote_literal(p_treatments::TEXT) || '::TEXT[])'
            || ' OR t.treatment_2 = ANY(' || quote_literal(p_treatments::TEXT) || '::TEXT[])'
            || ' OR t.treatment_3 = ANY(' || quote_literal(p_treatments::TEXT) || '::TEXT[])'
            || ' OR t.treatment_4 = ANY(' || quote_literal(p_treatments::TEXT) || '::TEXT[])'
            || ' OR t.treatment_5 = ANY(' || quote_literal(p_treatments::TEXT) || '::TEXT[]))';
    END IF;

    IF p_biomarkers IS NOT NULL THEN
        v_where := v_where || ' AND (t.biomarker_1 = ANY(' || quote_literal(p_biomarkers::TEXT) || '::TEXT[])'
            || ' OR t.biomarker_2 = ANY(' || quote_literal(p_biomarkers::TEXT) || '::TEXT[])'
            || ' OR t.biomarker_3 = ANY(' || quote_literal(p_biomarkers::TEXT) || '::TEXT[])'
            || ' OR t.biomarker_4 = ANY(' || quote_literal(p_biomarkers::TEXT) || '::TEXT[])'
            || ' OR t.biomarker_5 = ANY(' || quote_literal(p_biomarkers::TEXT) || '::TEXT[]))';
    END IF;

    IF p_trials IS NOT NULL THEN
        v_where := v_where || ' AND (t.trial_1 = ANY(' || quote_literal(p_trials::TEXT) || '::TEXT[])'
            || ' OR t.trial_2 = ANY(' || quote_literal(p_trials::TEXT) || '::TEXT[])'
            || ' OR t.trial_3 = ANY(' || quote_literal(p_trials::TEXT) || '::TEXT[])'
            || ' OR t.trial_4 = ANY(' || quote_literal(p_trials::TEXT) || '::TEXT[])'
            || ' OR t.trial_5 = ANY(' || quote_literal(p_trials::TEXT) || '::TEXT[]))';
    END IF;

    -- ── Activity / quarter filters ──

    IF p_activities IS NOT NULL OR p_quarters IS NOT NULL THEN
        v_activity_join := ' JOIN question_activities qa ON q.id = qa.question_id JOIN activities a ON qa.activity_id = a.id';
        IF p_activities IS NOT NULL THEN
            v_where := v_where || ' AND qa.activity_name = ANY(' || quote_literal(p_activities::TEXT) || '::TEXT[])';
        END IF;
        IF p_quarters IS NOT NULL THEN
            v_where := v_where || ' AND a.quarter = ANY(' || quote_literal(p_quarters::TEXT) || '::TEXT[])';
        END IF;
    END IF;

    -- ── Execute with weighted average aggregation ──

    EXECUTE format(
        'SELECT json_agg(row_data) FROM ('
        || 'SELECT %s as group_value, '
        || 'ROUND(CAST('
        ||   'SUM(CASE WHEN p.pre_score IS NOT NULL AND p.pre_n > 0 THEN p.pre_score * p.pre_n ELSE 0 END) '
        ||   '/ NULLIF(SUM(CASE WHEN p.pre_score IS NOT NULL AND p.pre_n > 0 THEN p.pre_n ELSE 0 END), 0)'
        || ' AS NUMERIC), 1) as avg_pre_score, '
        || 'ROUND(CAST('
        ||   'SUM(CASE WHEN p.post_score IS NOT NULL AND p.post_n > 0 THEN p.post_score * p.post_n ELSE 0 END) '
        ||   '/ NULLIF(SUM(CASE WHEN p.post_score IS NOT NULL AND p.post_n > 0 THEN p.post_n ELSE 0 END), 0)'
        || ' AS NUMERIC), 1) as avg_post_score, '
        || 'SUM(COALESCE(p.pre_n, 0)) as total_pre_n, '
        || 'SUM(COALESCE(p.post_n, 0)) as total_post_n, '
        || 'COUNT(DISTINCT q.id) as question_count '
        || 'FROM questions q '
        || 'JOIN tags t ON q.id = t.question_id '
        || 'LEFT JOIN performance p ON q.id = p.question_id AND p.segment = ''overall'' '
        || '%s '  -- activity join
        || 'WHERE %s '
        || 'GROUP BY %s '
        || 'ORDER BY question_count DESC'
        || ') row_data',
        v_col, v_activity_join, v_where, v_col
    ) INTO v_result;

    RETURN COALESCE(v_result, '[]'::JSON);
END;
$$ LANGUAGE plpgsql STABLE;


-- =============================================================================
-- 2. CREATE aggregate_by_tag_with_segments() — Audience comparison
-- =============================================================================
CREATE OR REPLACE FUNCTION aggregate_by_tag_with_segments(
    p_group_by TEXT,
    p_segments TEXT[],
    p_topics TEXT[] DEFAULT NULL,
    p_disease_states TEXT[] DEFAULT NULL,
    p_disease_stages TEXT[] DEFAULT NULL,
    p_disease_types TEXT[] DEFAULT NULL,
    p_treatment_lines TEXT[] DEFAULT NULL,
    p_treatments TEXT[] DEFAULT NULL,
    p_biomarkers TEXT[] DEFAULT NULL,
    p_trials TEXT[] DEFAULT NULL,
    p_activities TEXT[] DEFAULT NULL,
    p_quarters TEXT[] DEFAULT NULL
)
RETURNS JSON AS $$
DECLARE
    v_col TEXT;
    v_where TEXT;
    v_activity_join TEXT := '';
    v_result JSON;
BEGIN
    -- Same column mapping as aggregate_by_tag
    v_col := CASE p_group_by
        WHEN 'topic' THEN 't.topic'
        WHEN 'disease_state' THEN 'COALESCE(t.disease_state_1, t.disease_state)'
        WHEN 'disease_stage' THEN 't.disease_stage'
        WHEN 'disease_type' THEN 't.disease_type_1'
        WHEN 'treatment_line' THEN 't.treatment_line'
        WHEN 'treatment' THEN 't.treatment_1'
        WHEN 'biomarker' THEN 't.biomarker_1'
        WHEN 'trial' THEN 't.trial_1'
        WHEN 'drug_class' THEN 't.drug_class_1'
        WHEN 'drug_target' THEN 't.drug_target_1'
        WHEN 'treatment_eligibility' THEN 't.treatment_eligibility'
        WHEN 'age_group' THEN 't.age_group'
        WHEN 'fitness_status' THEN 't.fitness_status'
        WHEN 'organ_dysfunction' THEN 't.organ_dysfunction'
        WHEN 'metastatic_site' THEN 't.metastatic_site_1'
        WHEN 'performance_status' THEN 't.performance_status'
        WHEN 'toxicity_type' THEN 't.toxicity_type_1'
        WHEN 'toxicity_organ' THEN 't.toxicity_organ'
        WHEN 'toxicity_grade' THEN 't.toxicity_grade'
        WHEN 'efficacy_endpoint' THEN 't.efficacy_endpoint_1'
        WHEN 'outcome_context' THEN 't.outcome_context'
        WHEN 'clinical_benefit' THEN 't.clinical_benefit'
        WHEN 'guideline_source' THEN 't.guideline_source_1'
        WHEN 'evidence_type' THEN 't.evidence_type'
        WHEN 'cme_outcome_level' THEN 't.cme_outcome_level'
        ELSE NULL
    END;

    IF v_col IS NULL THEN
        RETURN json_build_object('error', 'Invalid group_by field: ' || p_group_by);
    END IF;

    -- Base filters
    v_where := '(q.is_oncology IS NULL OR q.is_oncology = TRUE)'
        || ' AND (q.canonical_source_id IS NULL OR q.canonical_source_id = CAST(q.source_id AS TEXT))'
        || ' AND q.id NOT IN (SELECT question_id FROM data_error_questions)'
        || ' AND ' || v_col || ' IS NOT NULL AND ' || v_col || ' != ''''';

    -- Segment filter
    IF p_segments IS NOT NULL THEN
        v_where := v_where || ' AND p.segment = ANY(' || quote_literal(p_segments::TEXT) || '::TEXT[])';
    END IF;

    -- ── Tag filters (identical to aggregate_by_tag) ──

    IF p_topics IS NOT NULL THEN
        v_where := v_where || ' AND t.topic = ANY(' || quote_literal(p_topics::TEXT) || '::TEXT[])';
    END IF;

    IF p_disease_states IS NOT NULL THEN
        v_where := v_where || ' AND (COALESCE(t.disease_state_1, t.disease_state) = ANY('
            || quote_literal(p_disease_states::TEXT) || '::TEXT[])'
            || ' OR t.disease_state_2 = ANY(' || quote_literal(p_disease_states::TEXT) || '::TEXT[]))';
    END IF;

    IF p_disease_stages IS NOT NULL THEN
        v_where := v_where || ' AND t.disease_stage = ANY(' || quote_literal(p_disease_stages::TEXT) || '::TEXT[])';
    END IF;

    IF p_disease_types IS NOT NULL THEN
        v_where := v_where || ' AND (t.disease_type_1 = ANY(' || quote_literal(p_disease_types::TEXT) || '::TEXT[])'
            || ' OR t.disease_type_2 = ANY(' || quote_literal(p_disease_types::TEXT) || '::TEXT[]))';
    END IF;

    IF p_treatment_lines IS NOT NULL THEN
        v_where := v_where || ' AND t.treatment_line = ANY(' || quote_literal(p_treatment_lines::TEXT) || '::TEXT[])';
    END IF;

    IF p_treatments IS NOT NULL THEN
        v_where := v_where || ' AND (t.treatment_1 = ANY(' || quote_literal(p_treatments::TEXT) || '::TEXT[])'
            || ' OR t.treatment_2 = ANY(' || quote_literal(p_treatments::TEXT) || '::TEXT[])'
            || ' OR t.treatment_3 = ANY(' || quote_literal(p_treatments::TEXT) || '::TEXT[])'
            || ' OR t.treatment_4 = ANY(' || quote_literal(p_treatments::TEXT) || '::TEXT[])'
            || ' OR t.treatment_5 = ANY(' || quote_literal(p_treatments::TEXT) || '::TEXT[]))';
    END IF;

    IF p_biomarkers IS NOT NULL THEN
        v_where := v_where || ' AND (t.biomarker_1 = ANY(' || quote_literal(p_biomarkers::TEXT) || '::TEXT[])'
            || ' OR t.biomarker_2 = ANY(' || quote_literal(p_biomarkers::TEXT) || '::TEXT[])'
            || ' OR t.biomarker_3 = ANY(' || quote_literal(p_biomarkers::TEXT) || '::TEXT[])'
            || ' OR t.biomarker_4 = ANY(' || quote_literal(p_biomarkers::TEXT) || '::TEXT[])'
            || ' OR t.biomarker_5 = ANY(' || quote_literal(p_biomarkers::TEXT) || '::TEXT[]))';
    END IF;

    IF p_trials IS NOT NULL THEN
        v_where := v_where || ' AND (t.trial_1 = ANY(' || quote_literal(p_trials::TEXT) || '::TEXT[])'
            || ' OR t.trial_2 = ANY(' || quote_literal(p_trials::TEXT) || '::TEXT[])'
            || ' OR t.trial_3 = ANY(' || quote_literal(p_trials::TEXT) || '::TEXT[])'
            || ' OR t.trial_4 = ANY(' || quote_literal(p_trials::TEXT) || '::TEXT[])'
            || ' OR t.trial_5 = ANY(' || quote_literal(p_trials::TEXT) || '::TEXT[]))';
    END IF;

    -- ── Activity / quarter filters ──

    IF p_activities IS NOT NULL OR p_quarters IS NOT NULL THEN
        v_activity_join := ' JOIN question_activities qa ON q.id = qa.question_id JOIN activities a ON qa.activity_id = a.id';
        IF p_activities IS NOT NULL THEN
            v_where := v_where || ' AND qa.activity_name = ANY(' || quote_literal(p_activities::TEXT) || '::TEXT[])';
        END IF;
        IF p_quarters IS NOT NULL THEN
            v_where := v_where || ' AND a.quarter = ANY(' || quote_literal(p_quarters::TEXT) || '::TEXT[])';
        END IF;
    END IF;

    -- ── Execute with weighted average, grouped by tag + segment ──

    EXECUTE format(
        'SELECT json_agg(row_data ORDER BY question_count DESC, segment) FROM ('
        || 'SELECT %s as group_value, '
        || 'p.segment, '
        || 'ROUND(CAST('
        ||   'SUM(CASE WHEN p.pre_score IS NOT NULL AND p.pre_n > 0 THEN p.pre_score * p.pre_n ELSE 0 END) '
        ||   '/ NULLIF(SUM(CASE WHEN p.pre_score IS NOT NULL AND p.pre_n > 0 THEN p.pre_n ELSE 0 END), 0)'
        || ' AS NUMERIC), 1) as avg_pre_score, '
        || 'ROUND(CAST('
        ||   'SUM(CASE WHEN p.post_score IS NOT NULL AND p.post_n > 0 THEN p.post_score * p.post_n ELSE 0 END) '
        ||   '/ NULLIF(SUM(CASE WHEN p.post_score IS NOT NULL AND p.post_n > 0 THEN p.post_n ELSE 0 END), 0)'
        || ' AS NUMERIC), 1) as avg_post_score, '
        || 'SUM(COALESCE(p.pre_n, 0)) as total_pre_n, '
        || 'SUM(COALESCE(p.post_n, 0)) as total_post_n, '
        || 'COUNT(DISTINCT q.id) as question_count '
        || 'FROM questions q '
        || 'JOIN tags t ON q.id = t.question_id '
        || 'JOIN performance p ON q.id = p.question_id '
        || '%s '  -- activity join
        || 'WHERE %s '
        || 'GROUP BY %s, p.segment'
        || ') row_data',
        v_col, v_activity_join, v_where, v_col
    ) INTO v_result;

    RETURN COALESCE(v_result, '[]'::JSON);
END;
$$ LANGUAGE plpgsql STABLE;
