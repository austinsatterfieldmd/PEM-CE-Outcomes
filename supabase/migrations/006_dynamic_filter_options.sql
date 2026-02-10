-- =============================================================================
-- Migration 006: Add get_dynamic_filter_options RPC function
--
-- Returns filter options (DISTINCT values + counts) for each filter category,
-- applying all OTHER active filters except the one being queried.
-- This enables cascading/dependent filter dropdowns.
-- =============================================================================

CREATE OR REPLACE FUNCTION get_dynamic_filter_options(
    p_topics TEXT[] DEFAULT NULL,
    p_disease_states TEXT[] DEFAULT NULL,
    p_disease_stages TEXT[] DEFAULT NULL,
    p_disease_types TEXT[] DEFAULT NULL,
    p_treatment_lines TEXT[] DEFAULT NULL,
    p_treatments TEXT[] DEFAULT NULL,
    p_biomarkers TEXT[] DEFAULT NULL,
    p_trials TEXT[] DEFAULT NULL,
    p_treatment_eligibilities TEXT[] DEFAULT NULL,
    p_age_groups TEXT[] DEFAULT NULL,
    p_fitness_statuses TEXT[] DEFAULT NULL,
    p_organ_dysfunctions TEXT[] DEFAULT NULL,
    p_advanced_filters JSONB DEFAULT NULL
) RETURNS JSON AS $$
DECLARE
    v_base TEXT;
    -- Individual filter condition strings
    c_topic TEXT := '';
    c_disease_state TEXT := '';
    c_disease_stage TEXT := '';
    c_disease_type TEXT := '';
    c_treatment_line TEXT := '';
    c_treatment TEXT := '';
    c_biomarker TEXT := '';
    c_trial TEXT := '';
    c_treatment_elig TEXT := '';
    c_age_group TEXT := '';
    c_fitness TEXT := '';
    c_organ TEXT := '';
    c_advanced TEXT := '';
    -- Result parts
    v_topics JSON;
    v_disease_states JSON;
    v_disease_stages JSON;
    v_disease_types JSON;
    v_treatment_lines JSON;
    v_treatments JSON;
    v_biomarkers JSON;
    v_trials JSON;
    v_treatment_eligibilities JSON;
    v_age_groups JSON;
    v_fitness_statuses JSON;
    v_organ_dysfunctions JSON;
    v_source_files JSON;
    v_where TEXT;
    v_adv_key TEXT;
    v_adv_vals TEXT[];
BEGIN
    -- Base conditions (always applied, same as search_questions)
    v_base := '(q.is_oncology IS NULL OR q.is_oncology = TRUE)'
        || ' AND (q.canonical_source_id IS NULL OR q.canonical_source_id = CAST(q.source_id AS TEXT))'
        || ' AND q.id NOT IN (SELECT question_id FROM data_error_questions)';

    -- Build individual filter conditions
    IF p_topics IS NOT NULL THEN
        c_topic := ' AND t.topic = ANY(' || quote_literal(p_topics::TEXT) || '::TEXT[])';
    END IF;

    IF p_disease_states IS NOT NULL THEN
        c_disease_state := ' AND (COALESCE(t.disease_state_1, t.disease_state) = ANY('
            || quote_literal(p_disease_states::TEXT) || '::TEXT[]) OR t.disease_state_2 = ANY('
            || quote_literal(p_disease_states::TEXT) || '::TEXT[]))';
    END IF;

    IF p_disease_stages IS NOT NULL THEN
        c_disease_stage := ' AND t.disease_stage = ANY(' || quote_literal(p_disease_stages::TEXT) || '::TEXT[])';
    END IF;

    IF p_disease_types IS NOT NULL THEN
        c_disease_type := ' AND (t.disease_type_1 = ANY(' || quote_literal(p_disease_types::TEXT) || '::TEXT[])'
            || ' OR t.disease_type_2 = ANY(' || quote_literal(p_disease_types::TEXT) || '::TEXT[]))';
    END IF;

    IF p_treatment_lines IS NOT NULL THEN
        c_treatment_line := ' AND t.treatment_line = ANY(' || quote_literal(p_treatment_lines::TEXT) || '::TEXT[])';
    END IF;

    IF p_treatments IS NOT NULL THEN
        c_treatment := ' AND (t.treatment_1 = ANY(' || quote_literal(p_treatments::TEXT) || '::TEXT[])'
            || ' OR t.treatment_2 = ANY(' || quote_literal(p_treatments::TEXT) || '::TEXT[])'
            || ' OR t.treatment_3 = ANY(' || quote_literal(p_treatments::TEXT) || '::TEXT[])'
            || ' OR t.treatment_4 = ANY(' || quote_literal(p_treatments::TEXT) || '::TEXT[])'
            || ' OR t.treatment_5 = ANY(' || quote_literal(p_treatments::TEXT) || '::TEXT[]))';
    END IF;

    IF p_biomarkers IS NOT NULL THEN
        c_biomarker := ' AND (t.biomarker_1 = ANY(' || quote_literal(p_biomarkers::TEXT) || '::TEXT[])'
            || ' OR t.biomarker_2 = ANY(' || quote_literal(p_biomarkers::TEXT) || '::TEXT[])'
            || ' OR t.biomarker_3 = ANY(' || quote_literal(p_biomarkers::TEXT) || '::TEXT[])'
            || ' OR t.biomarker_4 = ANY(' || quote_literal(p_biomarkers::TEXT) || '::TEXT[])'
            || ' OR t.biomarker_5 = ANY(' || quote_literal(p_biomarkers::TEXT) || '::TEXT[]))';
    END IF;

    IF p_trials IS NOT NULL THEN
        c_trial := ' AND (t.trial_1 = ANY(' || quote_literal(p_trials::TEXT) || '::TEXT[])'
            || ' OR t.trial_2 = ANY(' || quote_literal(p_trials::TEXT) || '::TEXT[])'
            || ' OR t.trial_3 = ANY(' || quote_literal(p_trials::TEXT) || '::TEXT[])'
            || ' OR t.trial_4 = ANY(' || quote_literal(p_trials::TEXT) || '::TEXT[])'
            || ' OR t.trial_5 = ANY(' || quote_literal(p_trials::TEXT) || '::TEXT[]))';
    END IF;

    IF p_treatment_eligibilities IS NOT NULL THEN
        c_treatment_elig := ' AND t.treatment_eligibility = ANY(' || quote_literal(p_treatment_eligibilities::TEXT) || '::TEXT[])';
    END IF;

    IF p_age_groups IS NOT NULL THEN
        c_age_group := ' AND t.age_group = ANY(' || quote_literal(p_age_groups::TEXT) || '::TEXT[])';
    END IF;

    IF p_fitness_statuses IS NOT NULL THEN
        c_fitness := ' AND t.fitness_status = ANY(' || quote_literal(p_fitness_statuses::TEXT) || '::TEXT[])';
    END IF;

    IF p_organ_dysfunctions IS NOT NULL THEN
        c_organ := ' AND t.organ_dysfunction = ANY(' || quote_literal(p_organ_dysfunctions::TEXT) || '::TEXT[])';
    END IF;

    -- Advanced filters (applied to all queries)
    IF p_advanced_filters IS NOT NULL THEN
        FOR v_adv_key IN SELECT jsonb_object_keys(p_advanced_filters) LOOP
            SELECT ARRAY(SELECT jsonb_array_elements_text(p_advanced_filters -> v_adv_key)) INTO v_adv_vals;
            IF array_length(v_adv_vals, 1) > 0 THEN
                c_advanced := c_advanced || ' AND t.' || quote_ident(v_adv_key) || ' = ANY(' || quote_literal(v_adv_vals::TEXT) || '::TEXT[])';
            END IF;
        END LOOP;
    END IF;

    -- ========================================
    -- Topic options (exclude topic filter)
    -- ========================================
    v_where := v_base || c_disease_state || c_disease_stage || c_disease_type || c_treatment_line
        || c_treatment || c_biomarker || c_trial || c_treatment_elig || c_age_group || c_fitness || c_organ || c_advanced;
    EXECUTE format(
        'SELECT COALESCE(json_agg(json_build_object(''value'', val, ''count'', cnt) ORDER BY cnt DESC), ''[]''::JSON) '
        || 'FROM (SELECT t.topic as val, COUNT(DISTINCT q.id) as cnt '
        || 'FROM questions q JOIN tags t ON q.id = t.question_id WHERE %s '
        || 'AND t.topic IS NOT NULL AND t.topic != '''' GROUP BY t.topic) sub', v_where
    ) INTO v_topics;

    -- ========================================
    -- Disease state options (exclude disease_state filter)
    -- ========================================
    v_where := v_base || c_topic || c_disease_stage || c_disease_type || c_treatment_line
        || c_treatment || c_biomarker || c_trial || c_treatment_elig || c_age_group || c_fitness || c_organ || c_advanced;
    EXECUTE format(
        'SELECT COALESCE(json_agg(json_build_object(''value'', val, ''count'', cnt) ORDER BY cnt DESC), ''[]''::JSON) '
        || 'FROM (SELECT ds as val, COUNT(DISTINCT q.id) as cnt FROM ('
        || '  SELECT q.id, COALESCE(t.disease_state_1, t.disease_state) as ds FROM questions q JOIN tags t ON q.id = t.question_id WHERE %s AND COALESCE(t.disease_state_1, t.disease_state) IS NOT NULL'
        || '  UNION ALL'
        || '  SELECT q.id, t.disease_state_2 FROM questions q JOIN tags t ON q.id = t.question_id WHERE %s AND t.disease_state_2 IS NOT NULL AND t.disease_state_2 != '''''
        || ') sub GROUP BY ds) sub2', v_where, v_where
    ) INTO v_disease_states;

    -- ========================================
    -- Disease stage options (exclude disease_stage filter)
    -- ========================================
    v_where := v_base || c_topic || c_disease_state || c_disease_type || c_treatment_line
        || c_treatment || c_biomarker || c_trial || c_treatment_elig || c_age_group || c_fitness || c_organ || c_advanced;
    EXECUTE format(
        'SELECT COALESCE(json_agg(json_build_object(''value'', val, ''count'', cnt) ORDER BY cnt DESC), ''[]''::JSON) '
        || 'FROM (SELECT t.disease_stage as val, COUNT(DISTINCT q.id) as cnt '
        || 'FROM questions q JOIN tags t ON q.id = t.question_id WHERE %s '
        || 'AND t.disease_stage IS NOT NULL AND t.disease_stage != '''' GROUP BY t.disease_stage) sub', v_where
    ) INTO v_disease_stages;

    -- ========================================
    -- Disease type options (exclude disease_type filter)
    -- ========================================
    v_where := v_base || c_topic || c_disease_state || c_disease_stage || c_treatment_line
        || c_treatment || c_biomarker || c_trial || c_treatment_elig || c_age_group || c_fitness || c_organ || c_advanced;
    EXECUTE format(
        'SELECT COALESCE(json_agg(json_build_object(''value'', val, ''count'', cnt) ORDER BY cnt DESC), ''[]''::JSON) '
        || 'FROM (SELECT dt as val, COUNT(DISTINCT q.id) as cnt FROM ('
        || '  SELECT q.id, t.disease_type_1 as dt FROM questions q JOIN tags t ON q.id = t.question_id WHERE %s AND t.disease_type_1 IS NOT NULL AND t.disease_type_1 != '''''
        || '  UNION ALL'
        || '  SELECT q.id, t.disease_type_2 FROM questions q JOIN tags t ON q.id = t.question_id WHERE %s AND t.disease_type_2 IS NOT NULL AND t.disease_type_2 != '''''
        || ') sub GROUP BY dt) sub2', v_where, v_where
    ) INTO v_disease_types;

    -- ========================================
    -- Treatment line options (exclude treatment_line filter)
    -- ========================================
    v_where := v_base || c_topic || c_disease_state || c_disease_stage || c_disease_type
        || c_treatment || c_biomarker || c_trial || c_treatment_elig || c_age_group || c_fitness || c_organ || c_advanced;
    EXECUTE format(
        'SELECT COALESCE(json_agg(json_build_object(''value'', val, ''count'', cnt) ORDER BY cnt DESC), ''[]''::JSON) '
        || 'FROM (SELECT t.treatment_line as val, COUNT(DISTINCT q.id) as cnt '
        || 'FROM questions q JOIN tags t ON q.id = t.question_id WHERE %s '
        || 'AND t.treatment_line IS NOT NULL AND t.treatment_line != '''' GROUP BY t.treatment_line) sub', v_where
    ) INTO v_treatment_lines;

    -- ========================================
    -- Treatment options (exclude treatment filter, UNION 5 slots)
    -- ========================================
    v_where := v_base || c_topic || c_disease_state || c_disease_stage || c_disease_type || c_treatment_line
        || c_biomarker || c_trial || c_treatment_elig || c_age_group || c_fitness || c_organ || c_advanced;
    EXECUTE format(
        'SELECT COALESCE(json_agg(json_build_object(''value'', val, ''count'', cnt) ORDER BY cnt DESC), ''[]''::JSON) '
        || 'FROM (SELECT tx as val, COUNT(DISTINCT qid) as cnt FROM ('
        || '  SELECT q.id as qid, t.treatment_1 as tx FROM questions q JOIN tags t ON q.id = t.question_id WHERE %s AND t.treatment_1 IS NOT NULL AND t.treatment_1 != '''''
        || '  UNION ALL SELECT q.id, t.treatment_2 FROM questions q JOIN tags t ON q.id = t.question_id WHERE %s AND t.treatment_2 IS NOT NULL AND t.treatment_2 != '''''
        || '  UNION ALL SELECT q.id, t.treatment_3 FROM questions q JOIN tags t ON q.id = t.question_id WHERE %s AND t.treatment_3 IS NOT NULL AND t.treatment_3 != '''''
        || '  UNION ALL SELECT q.id, t.treatment_4 FROM questions q JOIN tags t ON q.id = t.question_id WHERE %s AND t.treatment_4 IS NOT NULL AND t.treatment_4 != '''''
        || '  UNION ALL SELECT q.id, t.treatment_5 FROM questions q JOIN tags t ON q.id = t.question_id WHERE %s AND t.treatment_5 IS NOT NULL AND t.treatment_5 != '''''
        || ') sub GROUP BY tx) sub2', v_where, v_where, v_where, v_where, v_where
    ) INTO v_treatments;

    -- ========================================
    -- Biomarker options (exclude biomarker filter, UNION 5 slots)
    -- ========================================
    v_where := v_base || c_topic || c_disease_state || c_disease_stage || c_disease_type || c_treatment_line
        || c_treatment || c_trial || c_treatment_elig || c_age_group || c_fitness || c_organ || c_advanced;
    EXECUTE format(
        'SELECT COALESCE(json_agg(json_build_object(''value'', val, ''count'', cnt) ORDER BY cnt DESC), ''[]''::JSON) '
        || 'FROM (SELECT bm as val, COUNT(DISTINCT qid) as cnt FROM ('
        || '  SELECT q.id as qid, t.biomarker_1 as bm FROM questions q JOIN tags t ON q.id = t.question_id WHERE %s AND t.biomarker_1 IS NOT NULL AND t.biomarker_1 != '''''
        || '  UNION ALL SELECT q.id, t.biomarker_2 FROM questions q JOIN tags t ON q.id = t.question_id WHERE %s AND t.biomarker_2 IS NOT NULL AND t.biomarker_2 != '''''
        || '  UNION ALL SELECT q.id, t.biomarker_3 FROM questions q JOIN tags t ON q.id = t.question_id WHERE %s AND t.biomarker_3 IS NOT NULL AND t.biomarker_3 != '''''
        || '  UNION ALL SELECT q.id, t.biomarker_4 FROM questions q JOIN tags t ON q.id = t.question_id WHERE %s AND t.biomarker_4 IS NOT NULL AND t.biomarker_4 != '''''
        || '  UNION ALL SELECT q.id, t.biomarker_5 FROM questions q JOIN tags t ON q.id = t.question_id WHERE %s AND t.biomarker_5 IS NOT NULL AND t.biomarker_5 != '''''
        || ') sub GROUP BY bm) sub2', v_where, v_where, v_where, v_where, v_where
    ) INTO v_biomarkers;

    -- ========================================
    -- Trial options (exclude trial filter, UNION 5 slots)
    -- ========================================
    v_where := v_base || c_topic || c_disease_state || c_disease_stage || c_disease_type || c_treatment_line
        || c_treatment || c_biomarker || c_treatment_elig || c_age_group || c_fitness || c_organ || c_advanced;
    EXECUTE format(
        'SELECT COALESCE(json_agg(json_build_object(''value'', val, ''count'', cnt) ORDER BY cnt DESC), ''[]''::JSON) '
        || 'FROM (SELECT tr as val, COUNT(DISTINCT qid) as cnt FROM ('
        || '  SELECT q.id as qid, t.trial_1 as tr FROM questions q JOIN tags t ON q.id = t.question_id WHERE %s AND t.trial_1 IS NOT NULL AND t.trial_1 != '''''
        || '  UNION ALL SELECT q.id, t.trial_2 FROM questions q JOIN tags t ON q.id = t.question_id WHERE %s AND t.trial_2 IS NOT NULL AND t.trial_2 != '''''
        || '  UNION ALL SELECT q.id, t.trial_3 FROM questions q JOIN tags t ON q.id = t.question_id WHERE %s AND t.trial_3 IS NOT NULL AND t.trial_3 != '''''
        || '  UNION ALL SELECT q.id, t.trial_4 FROM questions q JOIN tags t ON q.id = t.question_id WHERE %s AND t.trial_4 IS NOT NULL AND t.trial_4 != '''''
        || '  UNION ALL SELECT q.id, t.trial_5 FROM questions q JOIN tags t ON q.id = t.question_id WHERE %s AND t.trial_5 IS NOT NULL AND t.trial_5 != '''''
        || ') sub GROUP BY tr) sub2', v_where, v_where, v_where, v_where, v_where
    ) INTO v_trials;

    -- ========================================
    -- Treatment eligibility options
    -- ========================================
    v_where := v_base || c_topic || c_disease_state || c_disease_stage || c_disease_type || c_treatment_line
        || c_treatment || c_biomarker || c_trial || c_age_group || c_fitness || c_organ || c_advanced;
    EXECUTE format(
        'SELECT COALESCE(json_agg(json_build_object(''value'', val, ''count'', cnt) ORDER BY cnt DESC), ''[]''::JSON) '
        || 'FROM (SELECT t.treatment_eligibility as val, COUNT(DISTINCT q.id) as cnt '
        || 'FROM questions q JOIN tags t ON q.id = t.question_id WHERE %s '
        || 'AND t.treatment_eligibility IS NOT NULL AND t.treatment_eligibility != '''' GROUP BY t.treatment_eligibility) sub', v_where
    ) INTO v_treatment_eligibilities;

    -- ========================================
    -- Source files (always apply all filters)
    -- ========================================
    v_where := v_base || c_topic || c_disease_state || c_disease_stage || c_disease_type || c_treatment_line
        || c_treatment || c_biomarker || c_trial || c_treatment_elig || c_age_group || c_fitness || c_organ || c_advanced;
    EXECUTE format(
        'SELECT COALESCE(json_agg(json_build_object(''value'', val, ''count'', cnt) ORDER BY cnt DESC), ''[]''::JSON) '
        || 'FROM (SELECT q.source_file as val, COUNT(DISTINCT q.id) as cnt '
        || 'FROM questions q JOIN tags t ON q.id = t.question_id WHERE %s '
        || 'AND q.source_file IS NOT NULL AND q.source_file != '''' GROUP BY q.source_file) sub', v_where
    ) INTO v_source_files;

    -- Build final result
    RETURN json_build_object(
        'topics', v_topics,
        'disease_states', v_disease_states,
        'disease_stages', v_disease_stages,
        'disease_types', v_disease_types,
        'treatment_lines', v_treatment_lines,
        'treatments', v_treatments,
        'biomarkers', v_biomarkers,
        'trials', v_trials,
        'treatment_eligibilities', v_treatment_eligibilities,
        'age_groups', COALESCE(v_age_groups, '[]'::JSON),
        'fitness_statuses', COALESCE(v_fitness_statuses, '[]'::JSON),
        'organ_dysfunctions', COALESCE(v_organ_dysfunctions, '[]'::JSON),
        'source_files', v_source_files
    );
END;
$$ LANGUAGE plpgsql STABLE;
