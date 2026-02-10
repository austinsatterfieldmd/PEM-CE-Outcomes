-- =============================================================================
-- Migration 007: Fix search_questions ORDER BY + SELECT DISTINCT incompatibility
--
-- Bug: PostgreSQL error "for SELECT DISTINCT, ORDER BY expressions must appear
-- in select list" when sorting by knowledge_gain, confidence, sample_size, etc.
--
-- Root cause: SELECT DISTINCT was used, but ORDER BY expressions like
-- (perf.post_score - perf.pre_score) were not in the SELECT list.
--
-- Fix: Remove DISTINCT (joins are 1:1 so no duplicates) and add computed
-- sort columns to SELECT for json_agg output.
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

    -- Patient characteristics
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
