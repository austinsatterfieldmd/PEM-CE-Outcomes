-- =============================================================================
-- Migration 009: Fix get_question_detail activities — use question_activities
--
-- The activities section was pulling ONLY from demographic_performance, which
-- meant questions without demographic_performance rows showed 0 activities
-- even if they had entries in question_activities.
--
-- Fix: Pull activities from question_activities (which every question has),
-- and optionally attach per-activity performance from demographic_performance.
-- =============================================================================

CREATE OR REPLACE FUNCTION get_question_detail(p_question_id INTEGER)
RETURNS JSON AS $$
DECLARE
    v_question JSONB;
    v_tags JSONB;
    v_performance JSON;
    v_activities JSON;
BEGIN
    -- Get question base fields
    SELECT jsonb_build_object(
        'id', q.id,
        'source_question_id', q.source_question_id,
        'source_id', q.source_id,
        'question_stem', q.question_stem,
        'correct_answer', q.correct_answer,
        'incorrect_answers', q.incorrect_answers,
        'source_file', q.source_file
    ) INTO v_question
    FROM questions q
    WHERE q.id = p_question_id;

    IF v_question IS NULL THEN
        RETURN NULL;
    END IF;

    -- Build tags JSONB in chunks (each under 50 key-value pairs = 100 args)
    -- Chunk 1: Core fields (25 pairs = 50 args)
    SELECT jsonb_build_object(
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
        'treatment_eligibility', t.treatment_eligibility
    )
    -- Chunk 2: Patient + Treatment metadata (25 pairs)
    || jsonb_build_object(
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
        'special_population_1', t.special_population_1
    )
    -- Chunk 3: Safety + Efficacy + Quality (25 pairs)
    || jsonb_build_object(
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
        'flaw_grammatical_cue', t.flaw_grammatical_cue
    )
    -- Chunk 4: Remaining quality + review + metadata (19 pairs)
    || jsonb_build_object(
        'flaw_implausible_distractor', t.flaw_implausible_distractor,
        'flaw_clang_association', t.flaw_clang_association,
        'flaw_convergence_vulnerability', t.flaw_convergence_vulnerability,
        'flaw_double_negative', t.flaw_double_negative,
        'answer_option_count', t.answer_option_count,
        'correct_answer_position', t.correct_answer_position,
        'needs_review', t.needs_review,
        'review_reason', t.review_reason,
        'review_notes', t.review_notes,
        'review_flags', t.review_flags,
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
    INTO v_tags
    FROM tags t
    WHERE t.question_id = p_question_id;

    -- Merge tags into question
    v_question := v_question || jsonb_build_object('tags', COALESCE(v_tags, '{}'::JSONB));

    -- Get performance by segment from the performance table (already pre-aggregated)
    SELECT json_agg(json_build_object(
        'segment', p.segment,
        'pre_score', p.pre_score,
        'post_score', p.post_score,
        'pre_n', p.pre_n,
        'post_n', p.post_n
    ) ORDER BY CASE p.segment
        WHEN 'overall' THEN 1
        WHEN 'medical_oncologist' THEN 2
        WHEN 'app' THEN 3
        WHEN 'academic' THEN 4
        WHEN 'community' THEN 5
        WHEN 'surgical_oncologist' THEN 6
        WHEN 'radiation_oncologist' THEN 7
        WHEN 'nursing' THEN 8
        ELSE 9
    END) INTO v_performance
    FROM performance p
    WHERE p.question_id = p_question_id;

    -- Get activities from question_activities table
    -- Left join demographic_performance for optional per-activity performance data
    SELECT json_agg(act_row ORDER BY act_row->>'act_date' DESC NULLS LAST) INTO v_activities
    FROM (
        SELECT json_build_object(
            'activity_name', a.activity_name,
            'act_date', a.activity_date,
            'quarter', a.quarter,
            'performance', (
                SELECT json_agg(json_build_object(
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
                    'n_respondents', dp.n_respondents
                ))
                FROM demographic_performance dp
                WHERE dp.question_id = p_question_id AND dp.activity_id = a.id
            )
        ) as act_row
        FROM (
            SELECT DISTINCT a2.id, a2.activity_name, a2.activity_date, a2.quarter
            FROM question_activities qa
            JOIN activities a2 ON qa.activity_id = a2.id
            WHERE qa.question_id = p_question_id
        ) a
    ) sub;

    -- Merge into final result
    RETURN v_question || jsonb_build_object(
        'performance', COALESCE(v_performance, '[]'::JSON),
        'activities', COALESCE(v_activities, '[]'::JSON)
    );
END;
$$ LANGUAGE plpgsql STABLE;
