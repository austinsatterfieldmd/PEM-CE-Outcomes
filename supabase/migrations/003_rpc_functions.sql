-- =============================================================================
-- CE Outcomes Dashboard — PostgreSQL RPC Functions for Supabase
-- Migration 003: Server-side functions called via supabase.rpc()
--
-- These replace the FastAPI endpoint logic in database.py
-- =============================================================================


-- =============================================================================
-- HELPER: Canonical question filter (reusable)
-- =============================================================================
-- "Canonical" means: not a confirmed duplicate pointing to another question
-- Matches: WHERE (q.canonical_source_id IS NULL OR q.canonical_source_id = CAST(q.source_id AS TEXT))


-- =============================================================================
-- 1. get_stats_summary() — Dashboard overview counts
-- =============================================================================
CREATE OR REPLACE FUNCTION get_stats_summary()
RETURNS JSON AS $$
DECLARE
    total_questions INTEGER;
    tagged_questions INTEGER;
    total_activities INTEGER;
    needs_review_count INTEGER;
    duplicate_count INTEGER;
    data_error_count INTEGER;
BEGIN
    -- Count unique canonical oncology questions (excluding data errors)
    SELECT COUNT(*) INTO total_questions
    FROM questions
    WHERE (is_oncology IS NULL OR is_oncology = TRUE)
    AND (canonical_source_id IS NULL OR canonical_source_id = CAST(source_id AS TEXT))
    AND id NOT IN (SELECT question_id FROM data_error_questions);

    -- Count tagged canonical oncology questions
    SELECT COUNT(*) INTO tagged_questions
    FROM tags t
    JOIN questions q ON t.question_id = q.id
    WHERE (q.is_oncology IS NULL OR q.is_oncology = TRUE)
    AND (q.canonical_source_id IS NULL OR q.canonical_source_id = CAST(q.source_id AS TEXT))
    AND q.id NOT IN (SELECT question_id FROM data_error_questions);

    -- Count distinct activities
    SELECT COUNT(DISTINCT activity_name) INTO total_activities
    FROM question_activities;

    -- Count questions needing review (excluding user-edited unless flagged)
    SELECT COUNT(*) INTO needs_review_count
    FROM tags t
    JOIN questions q ON t.question_id = q.id
    WHERE t.needs_review = TRUE
    AND ((t.edited_by_user IS NULL OR t.edited_by_user = FALSE)
         OR (t.review_flags IS NOT NULL AND t.review_flags != '[]'))
    AND (q.is_oncology IS NULL OR q.is_oncology = TRUE)
    AND (q.canonical_source_id IS NULL OR q.canonical_source_id = CAST(q.source_id AS TEXT))
    AND q.id NOT IN (SELECT question_id FROM data_error_questions);

    -- Count duplicate questions
    SELECT COUNT(*) INTO duplicate_count
    FROM questions
    WHERE canonical_source_id IS NOT NULL
    AND canonical_source_id != CAST(source_id AS TEXT);

    -- Count data error questions
    SELECT COUNT(*) INTO data_error_count
    FROM data_error_questions;

    RETURN json_build_object(
        'total_questions', total_questions,
        'tagged_questions', tagged_questions,
        'total_activities', total_activities,
        'needs_review', needs_review_count,
        'duplicate_count', duplicate_count,
        'data_error_count', data_error_count
    );
END;
$$ LANGUAGE plpgsql STABLE;


-- =============================================================================
-- 2. search_questions() — Full-featured search with 23+ filters
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

    -- Build sort column
    v_sort_col := CASE p_sort_by
        WHEN 'topic' THEN 't.topic'
        WHEN 'disease_state' THEN 't.disease_state'
        WHEN 'pre_score' THEN 'dp_agg.pre_score'
        WHEN 'post_score' THEN 'dp_agg.post_score'
        WHEN 'knowledge_gain' THEN '(dp_agg.post_score - dp_agg.pre_score)'
        WHEN 'confidence' THEN 't.overall_confidence'
        WHEN 'sample_size' THEN '(COALESCE(dp_agg.pre_n, 0) + COALESCE(dp_agg.post_n, 0))'
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
        v_where := v_where || ' AND dp_agg.pre_n IS NOT NULL AND dp_agg.pre_n > 0 AND dp_agg.post_n IS NOT NULL AND dp_agg.post_n > 0';
    ELSIF p_has_performance_data = FALSE THEN
        v_where := v_where || ' AND (dp_agg.pre_n IS NULL OR dp_agg.pre_n = 0 OR dp_agg.post_n IS NULL OR dp_agg.post_n = 0)';
    END IF;

    -- Sample size
    IF p_min_sample_size IS NOT NULL THEN
        v_where := v_where || ' AND (COALESCE(dp_agg.pre_n, 0) + COALESCE(dp_agg.post_n, 0)) >= ' || p_min_sample_size;
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
        'SELECT COUNT(DISTINCT q.id) FROM questions q LEFT JOIN tags t ON q.id = t.question_id '
        || 'LEFT JOIN (SELECT question_id, '
        || 'SUM(CASE WHEN pre_score IS NOT NULL AND pre_n > 0 THEN pre_score * pre_n ELSE 0 END) / NULLIF(SUM(CASE WHEN pre_score IS NOT NULL AND pre_n > 0 THEN pre_n ELSE 0 END), 0) as pre_score, '
        || 'SUM(CASE WHEN post_score IS NOT NULL AND post_n > 0 THEN post_score * post_n ELSE 0 END) / NULLIF(SUM(CASE WHEN post_score IS NOT NULL AND post_n > 0 THEN post_n ELSE 0 END), 0) as post_score, '
        || 'SUM(CASE WHEN pre_score IS NOT NULL THEN pre_n ELSE 0 END) as pre_n, '
        || 'SUM(CASE WHEN post_score IS NOT NULL THEN post_n ELSE 0 END) as post_n '
        || 'FROM demographic_performance GROUP BY question_id) dp_agg ON q.id = dp_agg.question_id '
        || 'WHERE %s', v_where
    ) INTO v_total;

    -- Get paginated results
    EXECUTE format(
        'SELECT json_agg(row_data) FROM ('
        || 'SELECT DISTINCT q.id, q.source_id, q.question_stem, t.topic, t.topic_confidence, '
        || 't.disease_state, t.disease_state_confidence, t.treatment, '
        || 'dp_agg.pre_score, dp_agg.post_score, dp_agg.pre_n, dp_agg.post_n, '
        || '(SELECT COUNT(*) FROM question_activities qa WHERE qa.question_id = q.id) as activity_count, '
        || 't.tag_status, t.worst_case_agreement, t.qcore_score, t.qcore_grade '
        || 'FROM questions q '
        || 'LEFT JOIN tags t ON q.id = t.question_id '
        || 'LEFT JOIN (SELECT question_id, '
        || 'SUM(CASE WHEN pre_score IS NOT NULL AND pre_n > 0 THEN pre_score * pre_n ELSE 0 END) / NULLIF(SUM(CASE WHEN pre_score IS NOT NULL AND pre_n > 0 THEN pre_n ELSE 0 END), 0) as pre_score, '
        || 'SUM(CASE WHEN post_score IS NOT NULL AND post_n > 0 THEN post_score * post_n ELSE 0 END) / NULLIF(SUM(CASE WHEN post_score IS NOT NULL AND post_n > 0 THEN post_n ELSE 0 END), 0) as post_score, '
        || 'SUM(CASE WHEN pre_score IS NOT NULL THEN pre_n ELSE 0 END) as pre_n, '
        || 'SUM(CASE WHEN post_score IS NOT NULL THEN post_n ELSE 0 END) as post_n '
        || 'FROM demographic_performance GROUP BY question_id) dp_agg ON q.id = dp_agg.question_id '
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


-- =============================================================================
-- 3. get_question_detail() — Full question with tags, performance, activities
-- =============================================================================
CREATE OR REPLACE FUNCTION get_question_detail(p_question_id INTEGER)
RETURNS JSON AS $$
DECLARE
    v_question JSON;
    v_performance JSON;
    v_activities JSON;
BEGIN
    -- Get question + tags
    SELECT json_build_object(
        'id', q.id,
        'source_question_id', q.source_question_id,
        'source_id', q.source_id,
        'question_stem', q.question_stem,
        'correct_answer', q.correct_answer,
        'incorrect_answers', q.incorrect_answers,
        'source_file', q.source_file,
        'tags', json_build_object(
            'topic', t.topic,
            'topic_confidence', t.topic_confidence,
            'disease_state', t.disease_state,
            'disease_state_1', COALESCE(t.disease_state_1, t.disease_state),
            'disease_state_2', t.disease_state_2,
            'disease_stage', t.disease_stage,
            'disease_type_1', t.disease_type_1,
            'disease_type_2', t.disease_type_2,
            'treatment_line', t.treatment_line,
            'treatment_1', t.treatment_1, 'treatment_2', t.treatment_2,
            'treatment_3', t.treatment_3, 'treatment_4', t.treatment_4,
            'treatment_5', t.treatment_5,
            'biomarker_1', t.biomarker_1, 'biomarker_2', t.biomarker_2,
            'biomarker_3', t.biomarker_3, 'biomarker_4', t.biomarker_4,
            'biomarker_5', t.biomarker_5,
            'trial_1', t.trial_1, 'trial_2', t.trial_2,
            'trial_3', t.trial_3, 'trial_4', t.trial_4,
            'trial_5', t.trial_5,
            'treatment_eligibility', t.treatment_eligibility,
            'age_group', t.age_group,
            'organ_dysfunction', t.organ_dysfunction,
            'fitness_status', t.fitness_status,
            'disease_specific_factor', t.disease_specific_factor,
            'comorbidity_1', t.comorbidity_1, 'comorbidity_2', t.comorbidity_2,
            'comorbidity_3', t.comorbidity_3,
            'drug_class_1', t.drug_class_1, 'drug_class_2', t.drug_class_2,
            'drug_class_3', t.drug_class_3,
            'drug_target_1', t.drug_target_1, 'drug_target_2', t.drug_target_2,
            'drug_target_3', t.drug_target_3,
            'prior_therapy_1', t.prior_therapy_1, 'prior_therapy_2', t.prior_therapy_2,
            'prior_therapy_3', t.prior_therapy_3,
            'resistance_mechanism', t.resistance_mechanism,
            'metastatic_site_1', t.metastatic_site_1, 'metastatic_site_2', t.metastatic_site_2,
            'metastatic_site_3', t.metastatic_site_3,
            'symptom_1', t.symptom_1, 'symptom_2', t.symptom_2,
            'symptom_3', t.symptom_3,
            'performance_status', t.performance_status,
            'special_population_1', t.special_population_1,
            'special_population_2', t.special_population_2,
            'toxicity_type_1', t.toxicity_type_1, 'toxicity_type_2', t.toxicity_type_2,
            'toxicity_type_3', t.toxicity_type_3, 'toxicity_type_4', t.toxicity_type_4,
            'toxicity_type_5', t.toxicity_type_5,
            'toxicity_organ', t.toxicity_organ,
            'toxicity_grade', t.toxicity_grade,
            'efficacy_endpoint_1', t.efficacy_endpoint_1,
            'efficacy_endpoint_2', t.efficacy_endpoint_2,
            'efficacy_endpoint_3', t.efficacy_endpoint_3,
            'outcome_context', t.outcome_context,
            'clinical_benefit', t.clinical_benefit,
            'guideline_source_1', t.guideline_source_1,
            'guideline_source_2', t.guideline_source_2,
            'evidence_type', t.evidence_type,
            'cme_outcome_level', t.cme_outcome_level,
            'data_response_type', t.data_response_type,
            'stem_type', t.stem_type,
            'lead_in_type', t.lead_in_type,
            'answer_format', t.answer_format,
            'answer_length_pattern', t.answer_length_pattern,
            'distractor_homogeneity', t.distractor_homogeneity,
            'flaw_absolute_terms', t.flaw_absolute_terms,
            'flaw_grammatical_cue', t.flaw_grammatical_cue,
            'flaw_implausible_distractor', t.flaw_implausible_distractor,
            'flaw_clang_association', t.flaw_clang_association,
            'flaw_convergence_vulnerability', t.flaw_convergence_vulnerability,
            'flaw_double_negative', t.flaw_double_negative,
            'answer_option_count', t.answer_option_count,
            'correct_answer_position', t.correct_answer_position,
            'needs_review', t.needs_review,
            'review_reason', t.review_reason,
            'review_notes', t.review_notes,
            'agreement_level', t.agreement_level,
            'tag_status', t.tag_status,
            'worst_case_agreement', t.worst_case_agreement,
            'edited_by_user', t.edited_by_user,
            'edited_at', t.edited_at,
            'edited_fields', t.edited_fields,
            'qcore_score', t.qcore_score,
            'qcore_grade', t.qcore_grade,
            'qcore_breakdown', t.qcore_breakdown
        )
    ) INTO v_question
    FROM questions q
    LEFT JOIN tags t ON q.id = t.question_id
    WHERE q.id = p_question_id;

    IF v_question IS NULL THEN
        RETURN NULL;
    END IF;

    -- Get performance by segment (aggregated from demographic_performance)
    SELECT json_agg(perf) INTO v_performance
    FROM (
        -- Overall aggregate
        SELECT
            'overall' as segment,
            SUM(CASE WHEN pre_score IS NOT NULL AND pre_n > 0 THEN pre_score * pre_n ELSE 0 END) /
                NULLIF(SUM(CASE WHEN pre_score IS NOT NULL AND pre_n > 0 THEN pre_n ELSE 0 END), 0) as pre_score,
            SUM(CASE WHEN post_score IS NOT NULL AND post_n > 0 THEN post_score * post_n ELSE 0 END) /
                NULLIF(SUM(CASE WHEN post_score IS NOT NULL AND post_n > 0 THEN post_n ELSE 0 END), 0) as post_score,
            SUM(CASE WHEN pre_score IS NOT NULL THEN pre_n ELSE 0 END) as pre_n,
            SUM(CASE WHEN post_score IS NOT NULL THEN post_n ELSE 0 END) as post_n
        FROM demographic_performance
        WHERE question_id = p_question_id
        HAVING SUM(pre_n) > 0 OR SUM(post_n) > 0

        UNION ALL

        -- Per-specialty segments
        SELECT
            CASE specialty
                WHEN 'MedicalOncology' THEN 'medical_oncologist'
                WHEN 'SurgicalOncology' THEN 'surgical_oncologist'
                WHEN 'RadiationOncology' THEN 'radiation_oncologist'
                WHEN 'NP/PA' THEN 'app'
                WHEN 'CommunityOncology' THEN 'community'
                WHEN 'AcademicOncology' THEN 'academic'
                WHEN 'NursingOncology' THEN 'nursing'
                ELSE LOWER(specialty)
            END as segment,
            SUM(CASE WHEN pre_score IS NOT NULL AND pre_n > 0 THEN pre_score * pre_n ELSE 0 END) /
                NULLIF(SUM(CASE WHEN pre_score IS NOT NULL AND pre_n > 0 THEN pre_n ELSE 0 END), 0) as pre_score,
            SUM(CASE WHEN post_score IS NOT NULL AND post_n > 0 THEN post_score * post_n ELSE 0 END) /
                NULLIF(SUM(CASE WHEN post_score IS NOT NULL AND post_n > 0 THEN post_n ELSE 0 END), 0) as post_score,
            SUM(CASE WHEN pre_score IS NOT NULL THEN pre_n ELSE 0 END) as pre_n,
            SUM(CASE WHEN post_score IS NOT NULL THEN post_n ELSE 0 END) as post_n
        FROM demographic_performance
        WHERE question_id = p_question_id
        GROUP BY specialty
    ) perf;

    -- Get activities with per-activity performance
    SELECT json_agg(act ORDER BY act_date DESC NULLS LAST) INTO v_activities
    FROM (
        SELECT DISTINCT
            a.activity_name as activity_name,
            a.activity_date as act_date,
            a.quarter as quarter,
            (SELECT json_agg(json_build_object(
                'segment', CASE dp.specialty
                    WHEN 'MedicalOncology' THEN 'medical_oncologist'
                    WHEN 'SurgicalOncology' THEN 'surgical_oncologist'
                    WHEN 'RadiationOncology' THEN 'radiation_oncologist'
                    WHEN 'NP/PA' THEN 'app'
                    WHEN 'CommunityOncology' THEN 'community'
                    WHEN 'AcademicOncology' THEN 'academic'
                    WHEN 'NursingOncology' THEN 'nursing'
                    ELSE LOWER(dp.specialty)
                END,
                'pre_score', dp.pre_score,
                'post_score', dp.post_score,
                'pre_n', dp.pre_n,
                'post_n', dp.post_n
            ))
            FROM demographic_performance dp
            WHERE dp.question_id = p_question_id AND dp.activity_id = a.id
            ) as performance
        FROM demographic_performance dp2
        JOIN activities a ON dp2.activity_id = a.id
        WHERE dp2.question_id = p_question_id
    ) act;

    -- Merge into final result
    RETURN v_question::JSONB || jsonb_build_object(
        'performance', COALESCE(v_performance, '[]'::JSON),
        'activities', COALESCE(v_activities, '[]'::JSON)
    );
END;
$$ LANGUAGE plpgsql STABLE;


-- =============================================================================
-- 4. get_filter_options() — Distinct values for all filter dropdowns
-- =============================================================================
CREATE OR REPLACE FUNCTION get_filter_options()
RETURNS JSON AS $$
DECLARE
    v_result JSONB := '{}'::JSONB;
    v_oncology_filter TEXT := '(q.is_oncology IS NULL OR q.is_oncology = TRUE) AND (q.canonical_source_id IS NULL OR q.canonical_source_id = CAST(q.source_id AS TEXT))';
BEGIN
    -- Simple single-column fields
    SELECT jsonb_agg(json_build_object('value', value, 'count', cnt) ORDER BY cnt DESC)
    INTO v_result FROM (
        SELECT t.topic as value, COUNT(*) as cnt
        FROM tags t JOIN questions q ON t.question_id = q.id
        WHERE t.topic IS NOT NULL AND t.topic != ''
        AND (q.is_oncology IS NULL OR q.is_oncology = TRUE)
        AND (q.canonical_source_id IS NULL OR q.canonical_source_id = CAST(q.source_id AS TEXT))
        GROUP BY t.topic
    ) x;
    v_result := jsonb_build_object('topics', COALESCE(v_result, '[]'::JSONB));

    -- Disease states (merge disease_state_1, disease_state_2, legacy disease_state)
    v_result := v_result || jsonb_build_object('disease_states', (
        SELECT COALESCE(jsonb_agg(json_build_object('value', value, 'count', cnt) ORDER BY cnt DESC), '[]'::JSONB)
        FROM (
            SELECT value, SUM(cnt) as cnt FROM (
                SELECT t.disease_state_1 as value, COUNT(*) as cnt FROM tags t JOIN questions q ON t.question_id = q.id WHERE t.disease_state_1 IS NOT NULL AND t.disease_state_1 != '' AND (q.is_oncology IS NULL OR q.is_oncology = TRUE) AND (q.canonical_source_id IS NULL OR q.canonical_source_id = CAST(q.source_id AS TEXT)) GROUP BY t.disease_state_1
                UNION ALL
                SELECT t.disease_state_2, COUNT(*) FROM tags t JOIN questions q ON t.question_id = q.id WHERE t.disease_state_2 IS NOT NULL AND t.disease_state_2 != '' AND (q.is_oncology IS NULL OR q.is_oncology = TRUE) AND (q.canonical_source_id IS NULL OR q.canonical_source_id = CAST(q.source_id AS TEXT)) GROUP BY t.disease_state_2
                UNION ALL
                SELECT t.disease_state, COUNT(*) FROM tags t JOIN questions q ON t.question_id = q.id WHERE t.disease_state IS NOT NULL AND t.disease_state != '' AND t.disease_state_1 IS NULL AND (q.is_oncology IS NULL OR q.is_oncology = TRUE) AND (q.canonical_source_id IS NULL OR q.canonical_source_id = CAST(q.source_id AS TEXT)) GROUP BY t.disease_state
            ) sub GROUP BY value
        ) grouped
    ));

    -- Disease stages
    v_result := v_result || jsonb_build_object('disease_stages', (
        SELECT COALESCE(jsonb_agg(json_build_object('value', value, 'count', cnt) ORDER BY cnt DESC), '[]'::JSONB)
        FROM (SELECT t.disease_stage as value, COUNT(*) as cnt FROM tags t JOIN questions q ON t.question_id = q.id WHERE t.disease_stage IS NOT NULL AND t.disease_stage != '' AND (q.is_oncology IS NULL OR q.is_oncology = TRUE) AND (q.canonical_source_id IS NULL OR q.canonical_source_id = CAST(q.source_id AS TEXT)) GROUP BY t.disease_stage) x
    ));

    -- Disease types (merge _1 and _2)
    v_result := v_result || jsonb_build_object('disease_types', (
        SELECT COALESCE(jsonb_agg(json_build_object('value', value, 'count', cnt) ORDER BY cnt DESC), '[]'::JSONB)
        FROM (
            SELECT value, SUM(cnt) as cnt FROM (
                SELECT t.disease_type_1 as value, COUNT(*) as cnt FROM tags t JOIN questions q ON t.question_id = q.id WHERE t.disease_type_1 IS NOT NULL AND t.disease_type_1 != '' AND (q.is_oncology IS NULL OR q.is_oncology = TRUE) AND (q.canonical_source_id IS NULL OR q.canonical_source_id = CAST(q.source_id AS TEXT)) GROUP BY t.disease_type_1
                UNION ALL
                SELECT t.disease_type_2, COUNT(*) FROM tags t JOIN questions q ON t.question_id = q.id WHERE t.disease_type_2 IS NOT NULL AND t.disease_type_2 != '' AND (q.is_oncology IS NULL OR q.is_oncology = TRUE) AND (q.canonical_source_id IS NULL OR q.canonical_source_id = CAST(q.source_id AS TEXT)) GROUP BY t.disease_type_2
            ) sub GROUP BY value
        ) grouped
    ));

    -- Treatment lines
    v_result := v_result || jsonb_build_object('treatment_lines', (
        SELECT COALESCE(jsonb_agg(json_build_object('value', value, 'count', cnt) ORDER BY cnt DESC), '[]'::JSONB)
        FROM (SELECT t.treatment_line as value, COUNT(*) as cnt FROM tags t JOIN questions q ON t.question_id = q.id WHERE t.treatment_line IS NOT NULL AND t.treatment_line != '' AND (q.is_oncology IS NULL OR q.is_oncology = TRUE) AND (q.canonical_source_id IS NULL OR q.canonical_source_id = CAST(q.source_id AS TEXT)) GROUP BY t.treatment_line) x
    ));

    -- Treatments (merge 5 slots)
    v_result := v_result || jsonb_build_object('treatments', (
        SELECT COALESCE(jsonb_agg(json_build_object('value', value, 'count', cnt) ORDER BY cnt DESC), '[]'::JSONB)
        FROM (
            SELECT value, SUM(cnt) as cnt FROM (
                SELECT t.treatment_1 as value, COUNT(*) as cnt FROM tags t JOIN questions q ON t.question_id = q.id WHERE t.treatment_1 IS NOT NULL AND t.treatment_1 != '' AND (q.is_oncology IS NULL OR q.is_oncology = TRUE) AND (q.canonical_source_id IS NULL OR q.canonical_source_id = CAST(q.source_id AS TEXT)) GROUP BY t.treatment_1
                UNION ALL SELECT t.treatment_2, COUNT(*) FROM tags t JOIN questions q ON t.question_id = q.id WHERE t.treatment_2 IS NOT NULL AND t.treatment_2 != '' AND (q.is_oncology IS NULL OR q.is_oncology = TRUE) AND (q.canonical_source_id IS NULL OR q.canonical_source_id = CAST(q.source_id AS TEXT)) GROUP BY t.treatment_2
                UNION ALL SELECT t.treatment_3, COUNT(*) FROM tags t JOIN questions q ON t.question_id = q.id WHERE t.treatment_3 IS NOT NULL AND t.treatment_3 != '' AND (q.is_oncology IS NULL OR q.is_oncology = TRUE) AND (q.canonical_source_id IS NULL OR q.canonical_source_id = CAST(q.source_id AS TEXT)) GROUP BY t.treatment_3
                UNION ALL SELECT t.treatment_4, COUNT(*) FROM tags t JOIN questions q ON t.question_id = q.id WHERE t.treatment_4 IS NOT NULL AND t.treatment_4 != '' AND (q.is_oncology IS NULL OR q.is_oncology = TRUE) AND (q.canonical_source_id IS NULL OR q.canonical_source_id = CAST(q.source_id AS TEXT)) GROUP BY t.treatment_4
                UNION ALL SELECT t.treatment_5, COUNT(*) FROM tags t JOIN questions q ON t.question_id = q.id WHERE t.treatment_5 IS NOT NULL AND t.treatment_5 != '' AND (q.is_oncology IS NULL OR q.is_oncology = TRUE) AND (q.canonical_source_id IS NULL OR q.canonical_source_id = CAST(q.source_id AS TEXT)) GROUP BY t.treatment_5
            ) sub GROUP BY value
        ) grouped
    ));

    -- Biomarkers (merge 5 slots)
    v_result := v_result || jsonb_build_object('biomarkers', (
        SELECT COALESCE(jsonb_agg(json_build_object('value', value, 'count', cnt) ORDER BY cnt DESC), '[]'::JSONB)
        FROM (
            SELECT value, SUM(cnt) as cnt FROM (
                SELECT t.biomarker_1 as value, COUNT(*) as cnt FROM tags t JOIN questions q ON t.question_id = q.id WHERE t.biomarker_1 IS NOT NULL AND t.biomarker_1 != '' AND (q.is_oncology IS NULL OR q.is_oncology = TRUE) AND (q.canonical_source_id IS NULL OR q.canonical_source_id = CAST(q.source_id AS TEXT)) GROUP BY t.biomarker_1
                UNION ALL SELECT t.biomarker_2, COUNT(*) FROM tags t JOIN questions q ON t.question_id = q.id WHERE t.biomarker_2 IS NOT NULL AND t.biomarker_2 != '' AND (q.is_oncology IS NULL OR q.is_oncology = TRUE) AND (q.canonical_source_id IS NULL OR q.canonical_source_id = CAST(q.source_id AS TEXT)) GROUP BY t.biomarker_2
                UNION ALL SELECT t.biomarker_3, COUNT(*) FROM tags t JOIN questions q ON t.question_id = q.id WHERE t.biomarker_3 IS NOT NULL AND t.biomarker_3 != '' AND (q.is_oncology IS NULL OR q.is_oncology = TRUE) AND (q.canonical_source_id IS NULL OR q.canonical_source_id = CAST(q.source_id AS TEXT)) GROUP BY t.biomarker_3
                UNION ALL SELECT t.biomarker_4, COUNT(*) FROM tags t JOIN questions q ON t.question_id = q.id WHERE t.biomarker_4 IS NOT NULL AND t.biomarker_4 != '' AND (q.is_oncology IS NULL OR q.is_oncology = TRUE) AND (q.canonical_source_id IS NULL OR q.canonical_source_id = CAST(q.source_id AS TEXT)) GROUP BY t.biomarker_4
                UNION ALL SELECT t.biomarker_5, COUNT(*) FROM tags t JOIN questions q ON t.question_id = q.id WHERE t.biomarker_5 IS NOT NULL AND t.biomarker_5 != '' AND (q.is_oncology IS NULL OR q.is_oncology = TRUE) AND (q.canonical_source_id IS NULL OR q.canonical_source_id = CAST(q.source_id AS TEXT)) GROUP BY t.biomarker_5
            ) sub GROUP BY value
        ) grouped
    ));

    -- Trials (merge 5 slots)
    v_result := v_result || jsonb_build_object('trials', (
        SELECT COALESCE(jsonb_agg(json_build_object('value', value, 'count', cnt) ORDER BY cnt DESC), '[]'::JSONB)
        FROM (
            SELECT value, SUM(cnt) as cnt FROM (
                SELECT t.trial_1 as value, COUNT(*) as cnt FROM tags t JOIN questions q ON t.question_id = q.id WHERE t.trial_1 IS NOT NULL AND t.trial_1 != '' AND (q.is_oncology IS NULL OR q.is_oncology = TRUE) AND (q.canonical_source_id IS NULL OR q.canonical_source_id = CAST(q.source_id AS TEXT)) GROUP BY t.trial_1
                UNION ALL SELECT t.trial_2, COUNT(*) FROM tags t JOIN questions q ON t.question_id = q.id WHERE t.trial_2 IS NOT NULL AND t.trial_2 != '' AND (q.is_oncology IS NULL OR q.is_oncology = TRUE) AND (q.canonical_source_id IS NULL OR q.canonical_source_id = CAST(q.source_id AS TEXT)) GROUP BY t.trial_2
                UNION ALL SELECT t.trial_3, COUNT(*) FROM tags t JOIN questions q ON t.question_id = q.id WHERE t.trial_3 IS NOT NULL AND t.trial_3 != '' AND (q.is_oncology IS NULL OR q.is_oncology = TRUE) AND (q.canonical_source_id IS NULL OR q.canonical_source_id = CAST(q.source_id AS TEXT)) GROUP BY t.trial_3
                UNION ALL SELECT t.trial_4, COUNT(*) FROM tags t JOIN questions q ON t.question_id = q.id WHERE t.trial_4 IS NOT NULL AND t.trial_4 != '' AND (q.is_oncology IS NULL OR q.is_oncology = TRUE) AND (q.canonical_source_id IS NULL OR q.canonical_source_id = CAST(q.source_id AS TEXT)) GROUP BY t.trial_4
                UNION ALL SELECT t.trial_5, COUNT(*) FROM tags t JOIN questions q ON t.question_id = q.id WHERE t.trial_5 IS NOT NULL AND t.trial_5 != '' AND (q.is_oncology IS NULL OR q.is_oncology = TRUE) AND (q.canonical_source_id IS NULL OR q.canonical_source_id = CAST(q.source_id AS TEXT)) GROUP BY t.trial_5
            ) sub GROUP BY value
        ) grouped
    ));

    -- Activities
    v_result := v_result || jsonb_build_object('activities', (
        SELECT COALESCE(jsonb_agg(json_build_object('value', value, 'count', cnt) ORDER BY cnt DESC), '[]'::JSONB)
        FROM (SELECT qa.activity_name as value, COUNT(*) as cnt FROM question_activities qa JOIN questions q ON qa.question_id = q.id WHERE qa.activity_name IS NOT NULL AND qa.activity_name != '' AND (q.is_oncology IS NULL OR q.is_oncology = TRUE) AND (q.canonical_source_id IS NULL OR q.canonical_source_id = CAST(q.source_id AS TEXT)) GROUP BY qa.activity_name) x
    ));

    -- Source files
    v_result := v_result || jsonb_build_object('source_files', (
        SELECT COALESCE(jsonb_agg(json_build_object('value', value, 'count', cnt) ORDER BY cnt DESC), '[]'::JSONB)
        FROM (SELECT source_file as value, COUNT(*) as cnt FROM questions WHERE source_file IS NOT NULL AND source_file != '' AND (is_oncology IS NULL OR is_oncology = TRUE) GROUP BY source_file) x
    ));

    RETURN v_result;
END;
$$ LANGUAGE plpgsql STABLE;


-- =============================================================================
-- 5. aggregate_by_tag() — Performance grouped by any tag field
-- =============================================================================
CREATE OR REPLACE FUNCTION aggregate_by_tag(
    p_group_by TEXT,
    p_topics TEXT[] DEFAULT NULL,
    p_disease_states TEXT[] DEFAULT NULL,
    p_disease_stages TEXT[] DEFAULT NULL,
    p_treatment_lines TEXT[] DEFAULT NULL,
    p_treatments TEXT[] DEFAULT NULL,
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
    -- Validate group_by column (prevent SQL injection)
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

    -- Optional filters
    IF p_topics IS NOT NULL THEN
        v_where := v_where || ' AND t.topic = ANY(' || quote_literal(p_topics::TEXT) || '::TEXT[])';
    END IF;
    IF p_disease_states IS NOT NULL THEN
        v_where := v_where || ' AND (COALESCE(t.disease_state_1, t.disease_state) = ANY(' || quote_literal(p_disease_states::TEXT) || '::TEXT[]))';
    END IF;
    IF p_disease_stages IS NOT NULL THEN
        v_where := v_where || ' AND t.disease_stage = ANY(' || quote_literal(p_disease_stages::TEXT) || '::TEXT[])';
    END IF;
    IF p_treatment_lines IS NOT NULL THEN
        v_where := v_where || ' AND t.treatment_line = ANY(' || quote_literal(p_treatment_lines::TEXT) || '::TEXT[])';
    END IF;

    -- Activity/quarter join
    IF p_activities IS NOT NULL OR p_quarters IS NOT NULL THEN
        v_activity_join := ' JOIN question_activities qa ON q.id = qa.question_id JOIN activities a ON qa.activity_id = a.id';
        IF p_activities IS NOT NULL THEN
            v_where := v_where || ' AND qa.activity_name = ANY(' || quote_literal(p_activities::TEXT) || '::TEXT[])';
        END IF;
        IF p_quarters IS NOT NULL THEN
            v_where := v_where || ' AND a.quarter = ANY(' || quote_literal(p_quarters::TEXT) || '::TEXT[])';
        END IF;
    END IF;

    EXECUTE format(
        'SELECT json_agg(row_data) FROM ('
        || 'SELECT %s as group_value, '
        || 'AVG(p.pre_score) as avg_pre_score, '
        || 'AVG(p.post_score) as avg_post_score, '
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
-- 6. aggregate_by_segment() — Performance by audience segment
-- =============================================================================
CREATE OR REPLACE FUNCTION aggregate_by_segment(
    p_segments TEXT[] DEFAULT NULL,
    p_topics TEXT[] DEFAULT NULL,
    p_disease_states TEXT[] DEFAULT NULL,
    p_disease_stages TEXT[] DEFAULT NULL,
    p_treatment_lines TEXT[] DEFAULT NULL
)
RETURNS JSON AS $$
DECLARE
    v_where TEXT;
    v_tag_join TEXT := '';
    v_result JSON;
BEGIN
    v_where := '(q.is_oncology IS NULL OR q.is_oncology = TRUE)'
        || ' AND (q.canonical_source_id IS NULL OR q.canonical_source_id = CAST(q.source_id AS TEXT))'
        || ' AND q.id NOT IN (SELECT question_id FROM data_error_questions)';

    -- Segment filter
    IF p_segments IS NOT NULL THEN
        v_where := v_where || ' AND p.segment = ANY(' || quote_literal(p_segments::TEXT) || '::TEXT[])';
    END IF;

    -- Tag filters require join
    IF p_topics IS NOT NULL OR p_disease_states IS NOT NULL OR p_disease_stages IS NOT NULL OR p_treatment_lines IS NOT NULL THEN
        v_tag_join := ' JOIN tags t ON q.id = t.question_id';
        IF p_topics IS NOT NULL THEN
            v_where := v_where || ' AND t.topic = ANY(' || quote_literal(p_topics::TEXT) || '::TEXT[])';
        END IF;
        IF p_disease_states IS NOT NULL THEN
            v_where := v_where || ' AND (COALESCE(t.disease_state_1, t.disease_state) = ANY(' || quote_literal(p_disease_states::TEXT) || '::TEXT[]))';
        END IF;
        IF p_disease_stages IS NOT NULL THEN
            v_where := v_where || ' AND t.disease_stage = ANY(' || quote_literal(p_disease_stages::TEXT) || '::TEXT[])';
        END IF;
        IF p_treatment_lines IS NOT NULL THEN
            v_where := v_where || ' AND t.treatment_line = ANY(' || quote_literal(p_treatment_lines::TEXT) || '::TEXT[])';
        END IF;
    END IF;

    EXECUTE format(
        'SELECT json_agg(row_data ORDER BY sort_order) FROM ('
        || 'SELECT p.segment, '
        || 'AVG(p.pre_score) as avg_pre_score, '
        || 'AVG(p.post_score) as avg_post_score, '
        || 'SUM(COALESCE(p.pre_n, 0)) as total_pre_n, '
        || 'SUM(COALESCE(p.post_n, 0)) as total_post_n, '
        || 'COUNT(DISTINCT q.id) as question_count, '
        || 'CASE p.segment '
        || '  WHEN ''overall'' THEN 1 WHEN ''medical_oncologist'' THEN 2 '
        || '  WHEN ''app'' THEN 3 WHEN ''academic'' THEN 4 '
        || '  WHEN ''community'' THEN 5 WHEN ''surgical_oncologist'' THEN 6 '
        || '  WHEN ''radiation_oncologist'' THEN 7 ELSE 8 END as sort_order '
        || 'FROM questions q '
        || 'JOIN performance p ON q.id = p.question_id '
        || '%s '  -- tag join
        || 'WHERE %s '
        || 'GROUP BY p.segment'
        || ') row_data',
        v_tag_join, v_where
    ) INTO v_result;

    RETURN COALESCE(v_result, '[]'::JSON);
END;
$$ LANGUAGE plpgsql STABLE;


-- =============================================================================
-- 7. get_performance_trends() — Performance over time by quarter
-- =============================================================================
CREATE OR REPLACE FUNCTION get_performance_trends(
    p_segment_by TEXT DEFAULT NULL,
    p_topics TEXT[] DEFAULT NULL,
    p_disease_states TEXT[] DEFAULT NULL,
    p_treatment_lines TEXT[] DEFAULT NULL
)
RETURNS JSON AS $$
DECLARE
    v_where TEXT;
    v_tag_join TEXT := '';
    v_result JSON;
BEGIN
    v_where := '(q.is_oncology IS NULL OR q.is_oncology = TRUE)'
        || ' AND (q.canonical_source_id IS NULL OR q.canonical_source_id = CAST(q.source_id AS TEXT))'
        || ' AND q.id NOT IN (SELECT question_id FROM data_error_questions)';

    -- Tag filters
    IF p_topics IS NOT NULL OR p_disease_states IS NOT NULL OR p_treatment_lines IS NOT NULL THEN
        v_tag_join := ' JOIN tags t ON q.id = t.question_id';
        IF p_topics IS NOT NULL THEN
            v_where := v_where || ' AND t.topic = ANY(' || quote_literal(p_topics::TEXT) || '::TEXT[])';
        END IF;
        IF p_disease_states IS NOT NULL THEN
            v_where := v_where || ' AND (COALESCE(t.disease_state_1, t.disease_state) = ANY(' || quote_literal(p_disease_states::TEXT) || '::TEXT[]))';
        END IF;
        IF p_treatment_lines IS NOT NULL THEN
            v_where := v_where || ' AND t.treatment_line = ANY(' || quote_literal(p_treatment_lines::TEXT) || '::TEXT[])';
        END IF;
    END IF;

    IF p_segment_by IS NOT NULL AND p_segment_by IN ('specialty', 'practice_setting', 'region') THEN
        -- Segmented trends from demographic_performance
        EXECUTE format(
            'SELECT json_agg(row_data ORDER BY quarter, segment_value) FROM ('
            || 'SELECT a.quarter, dp.%I as segment_value, '
            || 'AVG(dp.pre_score) as avg_pre_score, '
            || 'AVG(dp.post_score) as avg_post_score, '
            || 'SUM(COALESCE(dp.pre_n, 0) + COALESCE(dp.post_n, 0)) as total_n '
            || 'FROM demographic_performance dp '
            || 'JOIN questions q ON dp.question_id = q.id '
            || 'JOIN activities a ON dp.activity_id = a.id '
            || '%s '  -- tag join
            || 'WHERE %s AND dp.%I IS NOT NULL AND a.quarter IS NOT NULL '
            || 'GROUP BY a.quarter, dp.%I '
            || 'ORDER BY a.quarter, dp.%I'
            || ') row_data',
            p_segment_by, v_tag_join, v_where, p_segment_by, p_segment_by, p_segment_by
        ) INTO v_result;
    ELSE
        -- Overall trends
        EXECUTE format(
            'SELECT json_agg(row_data ORDER BY quarter) FROM ('
            || 'SELECT a.quarter, ''Overall'' as segment_value, '
            || 'AVG(p.pre_score) as avg_pre_score, '
            || 'AVG(p.post_score) as avg_post_score, '
            || 'SUM(COALESCE(p.pre_n, 0)) as total_n '
            || 'FROM questions q '
            || 'JOIN question_activities qa ON q.id = qa.question_id '
            || 'JOIN activities a ON qa.activity_id = a.id '
            || 'LEFT JOIN performance p ON q.id = p.question_id AND p.segment = ''overall'' '
            || '%s '  -- tag join
            || 'WHERE %s AND a.quarter IS NOT NULL '
            || 'GROUP BY a.quarter'
            || ') row_data',
            v_tag_join, v_where
        ) INTO v_result;
    END IF;

    RETURN COALESCE(v_result, '[]'::JSON);
END;
$$ LANGUAGE plpgsql STABLE;


-- =============================================================================
-- 8. list_users_with_roles() — Admin: list all users and their roles
-- =============================================================================
CREATE OR REPLACE FUNCTION list_users_with_roles()
RETURNS JSON AS $$
BEGIN
    -- Only admin can call this (enforced by RLS on user_roles + frontend check)
    IF get_user_role() != 'admin' THEN
        RETURN json_build_object('error', 'Unauthorized');
    END IF;

    RETURN (
        SELECT COALESCE(json_agg(json_build_object(
            'user_id', u.id,
            'email', u.email,
            'role', COALESCE(ur.role, 'user'),
            'last_sign_in', u.last_sign_in_at,
            'created_at', u.created_at
        ) ORDER BY u.email), '[]'::JSON)
        FROM auth.users u
        LEFT JOIN user_roles ur ON u.id = ur.user_id
    );
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;


-- =============================================================================
-- 9. set_user_role() — Admin: assign a role to a user
-- =============================================================================
CREATE OR REPLACE FUNCTION set_user_role(
    p_user_id UUID,
    p_role TEXT
)
RETURNS JSON AS $$
BEGIN
    -- Only admin can call this
    IF get_user_role() != 'admin' THEN
        RETURN json_build_object('error', 'Unauthorized');
    END IF;

    -- Validate role
    IF p_role NOT IN ('admin', 'ma', 'user') THEN
        RETURN json_build_object('error', 'Invalid role. Must be admin, ma, or user');
    END IF;

    -- Upsert role
    INSERT INTO user_roles (user_id, role, assigned_by)
    VALUES (p_user_id, p_role, auth.uid())
    ON CONFLICT (user_id)
    DO UPDATE SET role = p_role, assigned_by = auth.uid();

    RETURN json_build_object('success', TRUE, 'user_id', p_user_id, 'role', p_role);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
