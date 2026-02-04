"""
Export Dashboard Data to Static JSON Files

This script exports the SQLite database to static JSON files that can be
deployed with the Vercel frontend for read-only access.

Usage:
    python scripts/export_static_data.py

Output:
    dashboard/frontend/public/data/questions.json
    dashboard/frontend/public/data/filters.json
    dashboard/frontend/public/data/stats.json
    dashboard/frontend/public/data/performance.json
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime


def export_data():
    # Paths
    project_root = Path(__file__).parent.parent
    db_path = project_root / "dashboard" / "data" / "questions.db"
    output_dir = project_root / "dashboard" / "frontend" / "public" / "data"

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Connect to database
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    print(f"Connected to database: {db_path}")

    # Export all questions with tags
    print("Exporting questions...")
    cursor = conn.execute("""
        SELECT
            q.id,
            q.source_id,
            q.source_question_id,
            q.question_stem,
            q.correct_answer,
            q.incorrect_answers,
            q.source_file,
            q.is_oncology,
            t.qcore_score,
            t.qcore_grade,
            t.qcore_breakdown,
            -- Tags
            t.topic,
            t.topic_confidence,
            t.disease_state,
            t.disease_state_confidence,
            t.disease_state_1,
            t.disease_state_2,
            t.disease_stage,
            t.disease_type_1,
            t.disease_type_2,
            t.treatment_line,
            t.treatment_1, t.treatment_2, t.treatment_3, t.treatment_4, t.treatment_5,
            t.biomarker_1, t.biomarker_2, t.biomarker_3, t.biomarker_4, t.biomarker_5,
            t.trial_1, t.trial_2, t.trial_3, t.trial_4, t.trial_5,
            t.treatment_eligibility,
            t.age_group,
            t.organ_dysfunction,
            t.fitness_status,
            t.disease_specific_factor,
            t.comorbidity_1, t.comorbidity_2, t.comorbidity_3,
            t.drug_class_1, t.drug_class_2, t.drug_class_3,
            t.drug_target_1, t.drug_target_2, t.drug_target_3,
            t.prior_therapy_1, t.prior_therapy_2, t.prior_therapy_3,
            t.resistance_mechanism,
            t.metastatic_site_1, t.metastatic_site_2, t.metastatic_site_3,
            t.symptom_1, t.symptom_2, t.symptom_3,
            t.performance_status,
            t.toxicity_type_1, t.toxicity_type_2, t.toxicity_type_3, t.toxicity_type_4, t.toxicity_type_5,
            t.toxicity_organ,
            t.toxicity_grade,
            t.efficacy_endpoint_1, t.efficacy_endpoint_2, t.efficacy_endpoint_3,
            t.outcome_context,
            t.clinical_benefit,
            t.guideline_source_1, t.guideline_source_2,
            t.evidence_type,
            t.cme_outcome_level,
            t.data_response_type,
            t.stem_type,
            t.lead_in_type,
            t.answer_format,
            t.answer_length_pattern,
            t.distractor_homogeneity,
            t.flaw_absolute_terms,
            t.flaw_grammatical_cue,
            t.flaw_implausible_distractor,
            t.flaw_clang_association,
            t.flaw_convergence_vulnerability,
            t.flaw_double_negative,
            t.answer_option_count,
            t.correct_answer_position,
            t.needs_review,
            t.review_flags,
            t.review_reason,
            t.agreement_level,
            t.tag_status,
            t.worst_case_agreement
        FROM questions q
        LEFT JOIN tags t ON q.id = t.question_id
        WHERE q.is_oncology = 1
        ORDER BY q.id
    """)

    questions = []
    for row in cursor:
        q = dict(row)
        questions.append(q)

    print(f"  Found {len(questions)} questions")

    # Export to JSON
    questions_file = output_dir / "questions.json"
    with open(questions_file, "w", encoding="utf-8") as f:
        json.dump({"questions": questions, "total": len(questions)}, f)
    print(f"  Saved to {questions_file}")

    # Export filter options
    print("Exporting filter options...")
    filter_options = {}

    # Get unique values for each filter field
    filter_fields = [
        ("topic", "topics", "tags"),
        ("disease_state", "disease_states", "tags"),
        ("disease_stage", "disease_stages", "tags"),
        ("disease_type_1", "disease_types", "tags"),
        ("treatment_line", "treatment_lines", "tags"),
        ("source_file", "source_files", "questions"),
    ]

    for db_field, option_name, table in filter_fields:
        if table == "tags":
            cursor = conn.execute(f"""
                SELECT t.{db_field}, COUNT(*) as count
                FROM tags t
                JOIN questions q ON q.id = t.question_id
                WHERE t.{db_field} IS NOT NULL AND t.{db_field} != '' AND q.is_oncology = 1
                GROUP BY t.{db_field}
                ORDER BY count DESC
            """)
        else:
            cursor = conn.execute(f"""
                SELECT {db_field}, COUNT(*) as count
                FROM {table}
                WHERE {db_field} IS NOT NULL AND {db_field} != '' AND is_oncology = 1
                GROUP BY {db_field}
                ORDER BY count DESC
            """)
        filter_options[option_name] = [
            {"value": row[0], "count": row[1]}
            for row in cursor
        ]

    # Export multi-value fields (treatment_1-5, trial_1-5, biomarker_1-5, drug_class_1-3, etc.)
    multi_value_fields = [
        (["treatment_1", "treatment_2", "treatment_3", "treatment_4", "treatment_5"], "treatments"),
        (["trial_1", "trial_2", "trial_3", "trial_4", "trial_5"], "trials"),
        (["biomarker_1", "biomarker_2", "biomarker_3", "biomarker_4", "biomarker_5"], "biomarkers"),
        (["drug_class_1", "drug_class_2", "drug_class_3"], "drug_classes"),
        (["drug_target_1", "drug_target_2", "drug_target_3"], "drug_targets"),
        (["prior_therapy_1", "prior_therapy_2", "prior_therapy_3"], "prior_therapies"),
        (["metastatic_site_1", "metastatic_site_2", "metastatic_site_3"], "metastatic_sites"),
        (["symptom_1", "symptom_2", "symptom_3"], "symptoms"),
        (["toxicity_type_1", "toxicity_type_2", "toxicity_type_3", "toxicity_type_4", "toxicity_type_5"], "toxicity_types"),
        (["efficacy_endpoint_1", "efficacy_endpoint_2", "efficacy_endpoint_3"], "efficacy_endpoints"),
        (["guideline_source_1", "guideline_source_2"], "guideline_sources"),
        (["comorbidity_1", "comorbidity_2", "comorbidity_3"], "comorbidities"),
    ]

    for field_columns, option_name in multi_value_fields:
        # Build UNION ALL query to aggregate values from all columns
        union_parts = []
        for col in field_columns:
            union_parts.append(f"""
                SELECT t.{col} as value
                FROM tags t
                JOIN questions q ON q.id = t.question_id
                WHERE t.{col} IS NOT NULL AND t.{col} != '' AND q.is_oncology = 1
            """)
        union_query = " UNION ALL ".join(union_parts)

        cursor = conn.execute(f"""
            SELECT value, COUNT(*) as count
            FROM ({union_query})
            GROUP BY value
            ORDER BY count DESC
        """)
        filter_options[option_name] = [
            {"value": row[0], "count": row[1]}
            for row in cursor
        ]
        print(f"    {option_name}: {len(filter_options[option_name])} unique values")

    filters_file = output_dir / "filters.json"
    with open(filters_file, "w", encoding="utf-8") as f:
        json.dump(filter_options, f)
    print(f"  Saved to {filters_file}")

    # Export stats
    print("Exporting stats...")
    cursor = conn.execute("""
        SELECT COUNT(*) FROM questions WHERE is_oncology = 1
    """)
    total_questions = cursor.fetchone()[0]

    cursor = conn.execute("""
        SELECT COUNT(*)
        FROM tags t
        JOIN questions q ON q.id = t.question_id
        WHERE t.needs_review = 1 AND q.is_oncology = 1
    """)
    needs_review = cursor.fetchone()[0]

    cursor = conn.execute("""
        SELECT COUNT(DISTINCT t.disease_state)
        FROM tags t
        JOIN questions q ON q.id = t.question_id
        WHERE t.disease_state IS NOT NULL AND q.is_oncology = 1
    """)
    unique_diseases = cursor.fetchone()[0]

    stats = {
        "total_questions": total_questions,
        "unique_diseases": unique_diseases,
        "needs_review": needs_review,
        "exported_at": datetime.now().isoformat()
    }

    stats_file = output_dir / "stats.json"
    with open(stats_file, "w", encoding="utf-8") as f:
        json.dump(stats, f)
    print(f"  Saved to {stats_file}")

    # Export performance data (aggregated by question)
    print("Exporting performance data...")
    cursor = conn.execute("""
        SELECT
            p.question_id,
            p.segment,
            p.pre_score,
            p.post_score,
            p.pre_n,
            p.post_n
        FROM performance p
        JOIN questions q ON q.id = p.question_id
        WHERE q.is_oncology = 1
    """)

    performance = {}
    for row in cursor:
        qid = row[0]
        if qid not in performance:
            performance[qid] = []
        performance[qid].append({
            "activity_name": row[1],
            "pre_score": row[2],
            "post_score": row[3],
            "sample_size": row[4] or row[5]  # Use pre_n or post_n
        })

    performance_file = output_dir / "performance.json"
    with open(performance_file, "w", encoding="utf-8") as f:
        json.dump(performance, f)
    print(f"  Saved to {performance_file}")

    conn.close()

    print("\nExport complete!")
    print(f"  Questions: {len(questions)}")
    print(f"  Output directory: {output_dir}")
    print("\nTo deploy to Vercel, commit these files and push to the repository.")


if __name__ == "__main__":
    export_data()
