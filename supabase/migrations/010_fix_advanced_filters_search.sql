-- =============================================================================
-- Migration 010: Implement p_advanced_filters parsing in search_questions
--
-- Bug: Advanced filter selections (drug_classes, drug_targets, toxicity_types,
-- etc.) from the UI are sent as p_advanced_filters JSONB but the RPC function
-- never reads or applies them, so the question list is never filtered.
--
-- Fix: Parse the JSONB object and build WHERE clauses for all 25 advanced
-- filter categories, matching the FastAPI backend logic.
-- =============================================================================

CREATE OR REPLACE FUNCTION search_questions(
    p_query TEXT DEFAULT NULL,
    p_topics TEXT[] DEFAULT NULL,
    p_disease_states TEXT[] DEFAULT NULL,
    p_disease_stages TEXT[] DEFAULT NULL,
    p_disease_types TEXT[] DEFAULT NULL,
    p_treatment_lines TEXT[] DEFAULT NULL,
    p_treatments TEXT[] DEFAULT NULL,
    p_biomarkers TEXT[] DEFAULT NULL,
    p_trials TEXT[] DEFAULT NULL,
    p_activities TEXT[] DEFAULT NULL,
    p_source_files TEXT[] DEFAULT NULL,
    p_treatment_eligibilities TEXT[] DEFAULT NULL,
    p_age_groups TEXT[] DEFAULT NULL,
    p_fitness_statuses TEXT[] DEFAULT NULL,
    p_organ_dysfunctions TEXT[] DEFAULT NULL,
    p_min_confidence REAL DEFAULT NULL,
    p_max_confidence REAL DEFAULT NULL,
    p_has_performance_data BOOLEAN DEFAULT NULL,
    p_min_sample_size INTEGER DEFAULT NULL,
    p_needs_review BOOLEAN DEFAULT NULL,
    p_worst_case_agreement TEXT DEFAULT NULL,
    p_tag_status_filter TEXT DEFAULT NULL,
    p_exclude_numeric BOOLEAN DEFAULT NULL,
    p_activity_start_after TEXT DEFAULT NULL,
    p_activity_start_before TEXT DEFAULT NULL,
    p_advanced_filters JSONB DEFAULT NULL,
    p_page INTEGER DEFAULT 1,
    p_page_size INTEGER DEFAULT 20,
    p_sort_by TEXT DEFAULT 'id',
    p_sort_desc BOOLEAN DEFAULT FALSE
)
RETURNS JSON AS $$
DECLARE
    v_offset INTEGER;
    v_total INTEGER;
    v_results JSON;
    v_where TEXT := '';
    v_sort_col TEXT;
    v_sort_dir TEXT;
    v_vals TEXT[];
    v_quoted TEXT;
BEGIN
    v_offset := (p_page - 1) * p_page_size;
    v_sort_dir := CASE WHEN p_sort_desc THEN 'DESC' ELSE 'ASC' END;

    -- Build sort column (must match columns in SELECT list)
    v_sort_col := CASE p_sort_by
        WHEN 'topic' THEN 't.topic'
        WHEN 'disease_state' THEN 't.disease_state'
        WHEN 'pre_score' THEN 'perf.pre_score'
        WHEN 'post_score' THEN 'perf.post_score'
        WHEN 'knowledge_gain' THEN '(COALESCE(perf.post_score, 0) - COALESCE(perf.pre_score, 0))'
        WHEN 'confidence' THEN 't.overall_confidence'
        WHEN 'sample_size' THEN '(COALESCE(perf.pre_n, 0) + COALESCE(perf.post_n, 0))'
        WHEN 'flagged_at' THEN 't.flagged_at'
        WHEN 'qcore_score' THEN 't.qcore_score'
        ELSE 'q.id'
    END;

    -- Base filters (always applied)
    v_where := '(q.is_oncology IS NULL OR q.is_oncology = TRUE)'
        || ' AND (q.canonical_source_id IS NULL OR q.canonical_source_id = CAST(q.source_id AS TEXT))'
        || ' AND q.id NOT IN (SELECT question_id FROM data_error_questions)';

    -- Full-text search
    IF p_query IS NOT NULL AND p_query != '' THEN
        v_where := v_where || ' AND q.fts_vector @@ plainto_tsquery(''english'', ' || quote_literal(p_query) || ')';
    END IF;

    -- Tag filters
    IF p_topics IS NOT NULL THEN
        v_where := v_where || ' AND t.topic = ANY(' || quote_literal(p_topics::TEXT) || '::TEXT[])';
    END IF;

    IF p_disease_states IS NOT NULL THEN
        v_where := v_where || ' AND (COALESCE(t.disease_state_1, t.disease_state) = ANY('
            || quote_literal(p_disease_states::TEXT) || '::TEXT[]) OR t.disease_state_2 = ANY('
            || quote_literal(p_disease_states::TEXT) || '::TEXT[]))';
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

    -- Patient characteristics (explicit params)
    IF p_treatment_eligibilities IS NOT NULL THEN
        v_where := v_where || ' AND t.treatment_eligibility = ANY(' || quote_literal(p_treatment_eligibilities::TEXT) || '::TEXT[])';
    END IF;

    IF p_age_groups IS NOT NULL THEN
        v_where := v_where || ' AND t.age_group = ANY(' || quote_literal(p_age_groups::TEXT) || '::TEXT[])';
    END IF;

    IF p_fitness_statuses IS NOT NULL THEN
        v_where := v_where || ' AND t.fitness_status = ANY(' || quote_literal(p_fitness_statuses::TEXT) || '::TEXT[])';
    END IF;

    IF p_organ_dysfunctions IS NOT NULL THEN
        v_where := v_where || ' AND t.organ_dysfunction = ANY(' || quote_literal(p_organ_dysfunctions::TEXT) || '::TEXT[])';
    END IF;

    -- Activity filter
    IF p_activities IS NOT NULL THEN
        v_where := v_where || ' AND q.id IN (SELECT question_id FROM question_activities WHERE activity_name = ANY('
            || quote_literal(p_activities::TEXT) || '::TEXT[]))';
    END IF;

    -- Source files
    IF p_source_files IS NOT NULL THEN
        v_where := v_where || ' AND q.source_file = ANY(' || quote_literal(p_source_files::TEXT) || '::TEXT[])';
    END IF;

    -- Confidence range
    IF p_min_confidence IS NOT NULL THEN
        v_where := v_where || ' AND t.overall_confidence >= ' || p_min_confidence;
    END IF;
    IF p_max_confidence IS NOT NULL THEN
        v_where := v_where || ' AND t.overall_confidence <= ' || p_max_confidence;
    END IF;

    -- Performance data filter
    IF p_has_performance_data = TRUE THEN
        v_where := v_where || ' AND perf.pre_n IS NOT NULL AND perf.pre_n > 0 AND perf.post_n IS NOT NULL AND perf.post_n > 0';
    ELSIF p_has_performance_data = FALSE THEN
        v_where := v_where || ' AND (perf.pre_n IS NULL OR perf.pre_n = 0 OR perf.post_n IS NULL OR perf.post_n = 0)';
    END IF;

    -- Sample size
    IF p_min_sample_size IS NOT NULL THEN
        v_where := v_where || ' AND (COALESCE(perf.pre_n, 0) + COALESCE(perf.post_n, 0)) >= ' || p_min_sample_size;
    END IF;

    -- Review queue
    IF p_needs_review = TRUE THEN
        v_where := v_where || ' AND t.needs_review = TRUE AND ((t.edited_by_user IS NULL OR t.edited_by_user = FALSE) OR (t.review_flags IS NOT NULL AND t.review_flags != ''[]''))';
    ELSIF p_needs_review = FALSE THEN
        v_where := v_where || ' AND (t.needs_review IS NULL OR t.needs_review = FALSE)';
    END IF;

    -- Agreement filters
    IF p_worst_case_agreement = 'verified_only' THEN
        v_where := v_where || ' AND t.worst_case_agreement = ''verified''';
    ELSIF p_worst_case_agreement = 'verified_or_unanimous' THEN
        v_where := v_where || ' AND t.worst_case_agreement IN (''verified'', ''unanimous'')';
    ELSIF p_worst_case_agreement = 'verified_unanimous_majority' THEN
        v_where := v_where || ' AND t.worst_case_agreement IN (''verified'', ''unanimous'', ''majority'')';
    END IF;

    IF p_tag_status_filter = 'verified_only' THEN
        v_where := v_where || ' AND t.tag_status = ''verified''';
    ELSIF p_tag_status_filter = 'verified_or_unanimous' THEN
        v_where := v_where || ' AND t.tag_status IN (''verified'', ''unanimous'')';
    ELSIF p_tag_status_filter = 'verified_unanimous_majority' THEN
        v_where := v_where || ' AND t.tag_status IN (''verified'', ''unanimous'', ''majority'')';
    END IF;

    -- Exclude numeric
    IF p_exclude_numeric = TRUE THEN
        v_where := v_where || ' AND (t.data_response_type IS NULL OR t.data_response_type != ''Numeric'')';
    END IF;

    -- Activity date range
    IF p_activity_start_after IS NOT NULL THEN
        v_where := v_where || ' AND q.id IN (SELECT DISTINCT dp2.question_id FROM demographic_performance dp2 JOIN activities a2 ON dp2.activity_id = a2.id WHERE a2.activity_date >= ' || quote_literal(p_activity_start_after || '-01') || '::DATE)';
    END IF;
    IF p_activity_start_before IS NOT NULL THEN
        v_where := v_where || ' AND q.id IN (SELECT DISTINCT dp2.question_id FROM demographic_performance dp2 JOIN activities a2 ON dp2.activity_id = a2.id WHERE a2.activity_date <= ' || quote_literal(p_activity_start_before || '-31') || '::DATE)';
    END IF;

    -- ================================================================
    -- Advanced filters (from p_advanced_filters JSONB)
    -- Covers all 25 categories from the Advanced Filters modal
    -- ================================================================
    IF p_advanced_filters IS NOT NULL THEN

        -- Patient Characteristics (also available as separate params, but UI sends via advanced_filters)
        IF p_advanced_filters ? 'treatment_eligibilities' AND p_treatment_eligibilities IS NULL THEN
            v_vals := ARRAY(SELECT jsonb_array_elements_text(p_advanced_filters->'treatment_eligibilities'));
            v_where := v_where || ' AND t.treatment_eligibility = ANY(' || quote_literal(v_vals::TEXT) || '::TEXT[])';
        END IF;

        IF p_advanced_filters ? 'age_groups' AND p_age_groups IS NULL THEN
            v_vals := ARRAY(SELECT jsonb_array_elements_text(p_advanced_filters->'age_groups'));
            v_where := v_where || ' AND t.age_group = ANY(' || quote_literal(v_vals::TEXT) || '::TEXT[])';
        END IF;

        IF p_advanced_filters ? 'fitness_statuses' AND p_fitness_statuses IS NULL THEN
            v_vals := ARRAY(SELECT jsonb_array_elements_text(p_advanced_filters->'fitness_statuses'));
            v_where := v_where || ' AND t.fitness_status = ANY(' || quote_literal(v_vals::TEXT) || '::TEXT[])';
        END IF;

        IF p_advanced_filters ? 'organ_dysfunctions' AND p_organ_dysfunctions IS NULL THEN
            v_vals := ARRAY(SELECT jsonb_array_elements_text(p_advanced_filters->'organ_dysfunctions'));
            v_where := v_where || ' AND t.organ_dysfunction = ANY(' || quote_literal(v_vals::TEXT) || '::TEXT[])';
        END IF;

        -- Single-column categories
        IF p_advanced_filters ? 'disease_specific_factors' THEN
            v_vals := ARRAY(SELECT jsonb_array_elements_text(p_advanced_filters->'disease_specific_factors'));
            v_where := v_where || ' AND t.disease_specific_factor = ANY(' || quote_literal(v_vals::TEXT) || '::TEXT[])';
        END IF;

        IF p_advanced_filters ? 'resistance_mechanisms' THEN
            v_vals := ARRAY(SELECT jsonb_array_elements_text(p_advanced_filters->'resistance_mechanisms'));
            v_where := v_where || ' AND t.resistance_mechanism = ANY(' || quote_literal(v_vals::TEXT) || '::TEXT[])';
        END IF;

        IF p_advanced_filters ? 'performance_statuses' THEN
            v_vals := ARRAY(SELECT jsonb_array_elements_text(p_advanced_filters->'performance_statuses'));
            v_where := v_where || ' AND t.performance_status = ANY(' || quote_literal(v_vals::TEXT) || '::TEXT[])';
        END IF;

        IF p_advanced_filters ? 'toxicity_organs' THEN
            v_vals := ARRAY(SELECT jsonb_array_elements_text(p_advanced_filters->'toxicity_organs'));
            v_where := v_where || ' AND t.toxicity_organ = ANY(' || quote_literal(v_vals::TEXT) || '::TEXT[])';
        END IF;

        IF p_advanced_filters ? 'toxicity_grades' THEN
            v_vals := ARRAY(SELECT jsonb_array_elements_text(p_advanced_filters->'toxicity_grades'));
            v_where := v_where || ' AND t.toxicity_grade = ANY(' || quote_literal(v_vals::TEXT) || '::TEXT[])';
        END IF;

        IF p_advanced_filters ? 'outcome_contexts' THEN
            v_vals := ARRAY(SELECT jsonb_array_elements_text(p_advanced_filters->'outcome_contexts'));
            v_where := v_where || ' AND t.outcome_context = ANY(' || quote_literal(v_vals::TEXT) || '::TEXT[])';
        END IF;

        IF p_advanced_filters ? 'clinical_benefits' THEN
            v_vals := ARRAY(SELECT jsonb_array_elements_text(p_advanced_filters->'clinical_benefits'));
            v_where := v_where || ' AND t.clinical_benefit = ANY(' || quote_literal(v_vals::TEXT) || '::TEXT[])';
        END IF;

        IF p_advanced_filters ? 'evidence_types' THEN
            v_vals := ARRAY(SELECT jsonb_array_elements_text(p_advanced_filters->'evidence_types'));
            v_where := v_where || ' AND t.evidence_type = ANY(' || quote_literal(v_vals::TEXT) || '::TEXT[])';
        END IF;

        IF p_advanced_filters ? 'cme_outcome_levels' THEN
            v_vals := ARRAY(SELECT jsonb_array_elements_text(p_advanced_filters->'cme_outcome_levels'));
            v_where := v_where || ' AND t.cme_outcome_level = ANY(' || quote_literal(v_vals::TEXT) || '::TEXT[])';
        END IF;

        IF p_advanced_filters ? 'stem_types' THEN
            v_vals := ARRAY(SELECT jsonb_array_elements_text(p_advanced_filters->'stem_types'));
            v_where := v_where || ' AND t.stem_type = ANY(' || quote_literal(v_vals::TEXT) || '::TEXT[])';
        END IF;

        IF p_advanced_filters ? 'lead_in_types' THEN
            v_vals := ARRAY(SELECT jsonb_array_elements_text(p_advanced_filters->'lead_in_types'));
            v_where := v_where || ' AND t.lead_in_type = ANY(' || quote_literal(v_vals::TEXT) || '::TEXT[])';
        END IF;

        IF p_advanced_filters ? 'answer_formats' THEN
            v_vals := ARRAY(SELECT jsonb_array_elements_text(p_advanced_filters->'answer_formats'));
            v_where := v_where || ' AND t.answer_format = ANY(' || quote_literal(v_vals::TEXT) || '::TEXT[])';
        END IF;

        IF p_advanced_filters ? 'distractor_homogeneities' THEN
            v_vals := ARRAY(SELECT jsonb_array_elements_text(p_advanced_filters->'distractor_homogeneities'));
            v_where := v_where || ' AND t.distractor_homogeneity = ANY(' || quote_literal(v_vals::TEXT) || '::TEXT[])';
        END IF;

        -- Multi-column categories (OR across slots)
        IF p_advanced_filters ? 'comorbidities' THEN
            v_vals := ARRAY(SELECT jsonb_array_elements_text(p_advanced_filters->'comorbidities'));
            v_quoted := quote_literal(v_vals::TEXT);
            v_where := v_where || ' AND (t.comorbidity_1 = ANY(' || v_quoted || '::TEXT[])'
                || ' OR t.comorbidity_2 = ANY(' || v_quoted || '::TEXT[])'
                || ' OR t.comorbidity_3 = ANY(' || v_quoted || '::TEXT[]))';
        END IF;

        IF p_advanced_filters ? 'drug_classes' THEN
            v_vals := ARRAY(SELECT jsonb_array_elements_text(p_advanced_filters->'drug_classes'));
            v_quoted := quote_literal(v_vals::TEXT);
            v_where := v_where || ' AND (t.drug_class_1 = ANY(' || v_quoted || '::TEXT[])'
                || ' OR t.drug_class_2 = ANY(' || v_quoted || '::TEXT[])'
                || ' OR t.drug_class_3 = ANY(' || v_quoted || '::TEXT[]))';
        END IF;

        IF p_advanced_filters ? 'drug_targets' THEN
            v_vals := ARRAY(SELECT jsonb_array_elements_text(p_advanced_filters->'drug_targets'));
            v_quoted := quote_literal(v_vals::TEXT);
            v_where := v_where || ' AND (t.drug_target_1 = ANY(' || v_quoted || '::TEXT[])'
                || ' OR t.drug_target_2 = ANY(' || v_quoted || '::TEXT[])'
                || ' OR t.drug_target_3 = ANY(' || v_quoted || '::TEXT[]))';
        END IF;

        IF p_advanced_filters ? 'prior_therapies' THEN
            v_vals := ARRAY(SELECT jsonb_array_elements_text(p_advanced_filters->'prior_therapies'));
            v_quoted := quote_literal(v_vals::TEXT);
            v_where := v_where || ' AND (t.prior_therapy_1 = ANY(' || v_quoted || '::TEXT[])'
                || ' OR t.prior_therapy_2 = ANY(' || v_quoted || '::TEXT[])'
                || ' OR t.prior_therapy_3 = ANY(' || v_quoted || '::TEXT[]))';
        END IF;

        IF p_advanced_filters ? 'metastatic_sites' THEN
            v_vals := ARRAY(SELECT jsonb_array_elements_text(p_advanced_filters->'metastatic_sites'));
            v_quoted := quote_literal(v_vals::TEXT);
            v_where := v_where || ' AND (t.metastatic_site_1 = ANY(' || v_quoted || '::TEXT[])'
                || ' OR t.metastatic_site_2 = ANY(' || v_quoted || '::TEXT[])'
                || ' OR t.metastatic_site_3 = ANY(' || v_quoted || '::TEXT[]))';
        END IF;

        IF p_advanced_filters ? 'symptoms' THEN
            v_vals := ARRAY(SELECT jsonb_array_elements_text(p_advanced_filters->'symptoms'));
            v_quoted := quote_literal(v_vals::TEXT);
            v_where := v_where || ' AND (t.symptom_1 = ANY(' || v_quoted || '::TEXT[])'
                || ' OR t.symptom_2 = ANY(' || v_quoted || '::TEXT[])'
                || ' OR t.symptom_3 = ANY(' || v_quoted || '::TEXT[]))';
        END IF;

        IF p_advanced_filters ? 'toxicity_types' THEN
            v_vals := ARRAY(SELECT jsonb_array_elements_text(p_advanced_filters->'toxicity_types'));
            v_quoted := quote_literal(v_vals::TEXT);
            v_where := v_where || ' AND (t.toxicity_type_1 = ANY(' || v_quoted || '::TEXT[])'
                || ' OR t.toxicity_type_2 = ANY(' || v_quoted || '::TEXT[])'
                || ' OR t.toxicity_type_3 = ANY(' || v_quoted || '::TEXT[])'
                || ' OR t.toxicity_type_4 = ANY(' || v_quoted || '::TEXT[])'
                || ' OR t.toxicity_type_5 = ANY(' || v_quoted || '::TEXT[]))';
        END IF;

        IF p_advanced_filters ? 'efficacy_endpoints' THEN
            v_vals := ARRAY(SELECT jsonb_array_elements_text(p_advanced_filters->'efficacy_endpoints'));
            v_quoted := quote_literal(v_vals::TEXT);
            v_where := v_where || ' AND (t.efficacy_endpoint_1 = ANY(' || v_quoted || '::TEXT[])'
                || ' OR t.efficacy_endpoint_2 = ANY(' || v_quoted || '::TEXT[])'
                || ' OR t.efficacy_endpoint_3 = ANY(' || v_quoted || '::TEXT[]))';
        END IF;

        IF p_advanced_filters ? 'guideline_sources' THEN
            v_vals := ARRAY(SELECT jsonb_array_elements_text(p_advanced_filters->'guideline_sources'));
            v_quoted := quote_literal(v_vals::TEXT);
            v_where := v_where || ' AND (t.guideline_source_1 = ANY(' || v_quoted || '::TEXT[])'
                || ' OR t.guideline_source_2 = ANY(' || v_quoted || '::TEXT[]))';
        END IF;

    END IF;  -- p_advanced_filters IS NOT NULL

    -- Get total count
    EXECUTE format(
        'SELECT COUNT(DISTINCT q.id) FROM questions q '
        || 'LEFT JOIN tags t ON q.id = t.question_id '
        || 'LEFT JOIN performance perf ON q.id = perf.question_id AND perf.segment = ''overall'' '
        || 'WHERE %s', v_where
    ) INTO v_total;

    -- Get paginated results (no DISTINCT — joins are 1:1, so no duplicates)
    EXECUTE format(
        'SELECT json_agg(row_data) FROM ('
        || 'SELECT q.id, q.source_id, q.question_stem, t.topic, t.topic_confidence, '
        || 't.disease_state, t.disease_state_confidence, t.treatment, '
        || 'perf.pre_score, perf.post_score, perf.pre_n, perf.post_n, '
        || '(SELECT COUNT(*) FROM question_activities qa WHERE qa.question_id = q.id) as activity_count, '
        || 't.tag_status, t.worst_case_agreement, t.qcore_score, t.qcore_grade, '
        || 't.overall_confidence, t.flagged_at, t.needs_review, t.edited_by_user '
        || 'FROM questions q '
        || 'LEFT JOIN tags t ON q.id = t.question_id '
        || 'LEFT JOIN performance perf ON q.id = perf.question_id AND perf.segment = ''overall'' '
        || 'WHERE %s '
        || 'ORDER BY %s %s NULLS LAST '
        || 'LIMIT %s OFFSET %s'
        || ') row_data',
        v_where, v_sort_col, v_sort_dir, p_page_size, v_offset
    ) INTO v_results;

    RETURN json_build_object(
        'questions', COALESCE(v_results, '[]'::JSON),
        'total', v_total,
        'page', p_page,
        'page_size', p_page_size
    );
END;
$$ LANGUAGE plpgsql STABLE;
