"""
Upload LLM Evaluation Metrics to Supabase

Computes accuracy metrics from checkpoint files and uploads to the
eval_metrics table so the Vercel frontend can display them.

Usage:
    python scripts/upload_eval_metrics.py           # Compute and upload
    python scripts/upload_eval_metrics.py --dry-run  # Preview without uploading
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime
from collections import defaultdict

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

CHECKPOINT_DIR = PROJECT_ROOT / "data" / "checkpoints"
CHECKPOINT_PATTERN = "stage2_tagged_*.json"

FIELD_GROUPS = {
    "Core Fields": [
        "topic", "disease_stage", "disease_type_1", "disease_type_2",
        "treatment_line", "treatment_1", "treatment_2", "treatment_3",
        "treatment_4", "treatment_5", "biomarker_1", "biomarker_2",
        "biomarker_3", "biomarker_4", "biomarker_5", "trial_1", "trial_2",
        "trial_3", "trial_4", "trial_5"
    ],
    "Treatment Metadata": [
        "drug_class_1", "drug_class_2", "drug_class_3",
        "drug_target_1", "drug_target_2", "drug_target_3",
        "prior_therapy_1", "prior_therapy_2", "prior_therapy_3",
        "resistance_mechanism"
    ],
    "Clinical Context": [
        "metastatic_site_1", "metastatic_site_2", "metastatic_site_3",
        "symptom_1", "symptom_2", "symptom_3",
        "special_population_1", "special_population_2",
        "performance_status", "age_group", "treatment_eligibility",
        "fitness_status", "disease_specific_factor"
    ],
    "Safety/Toxicity": [
        "toxicity_type_1", "toxicity_type_2", "toxicity_type_3",
        "toxicity_type_4", "toxicity_type_5",
        "toxicity_organ", "toxicity_grade"
    ],
    "Efficacy/Outcomes": [
        "efficacy_endpoint_1", "efficacy_endpoint_2", "efficacy_endpoint_3",
        "outcome_context", "clinical_benefit"
    ],
    "Evidence/Guidelines": [
        "guideline_source_1", "guideline_source_2", "evidence_type"
    ],
    "Question Format/Quality": [
        "cme_outcome_level", "data_response_type", "stem_type",
        "lead_in_type", "answer_format", "answer_length_pattern",
        "distractor_homogeneity", "flaw_absolute_terms",
        "flaw_grammatical_cue", "flaw_implausible_distractor",
        "flaw_clang_association", "flaw_convergence_vulnerability",
        "flaw_double_negative"
    ]
}


def normalize_value(v):
    if v in (None, "", "null", "None", "none"):
        return None
    return str(v).strip().lower()


def get_correction_type(llm_value, human_value):
    llm_is_null = llm_value is None
    human_is_null = human_value is None
    if llm_is_null and not human_is_null:
        return "null_to_added"
    elif not llm_is_null and human_is_null:
        return "value_to_cleared"
    elif not llm_is_null and not human_is_null:
        return "wrong_to_fixed"
    return "no_change"


def extract_batch(tagged_at):
    if not tagged_at:
        return "Unknown"
    try:
        dt = datetime.fromisoformat(tagged_at.replace("Z", "+00:00"))
        return dt.strftime("%b-%d")
    except Exception:
        return "Unknown"


def get_field_group(field_name):
    for group, fields in FIELD_GROUPS.items():
        if field_name in fields:
            return group
    return "Other"


def get_real_errors(q):
    field_votes = q.get("field_votes", {}) or {}
    final_tags = q.get("final_tags", {}) or {}
    real_errors = []
    for field, fv in field_votes.items():
        if not isinstance(fv, dict):
            continue
        llm_value = normalize_value(fv.get("final_value"))
        human_value = normalize_value(final_tags.get(field))
        if llm_value != human_value:
            real_errors.append(field)
    return real_errors


def load_checkpoints():
    if not CHECKPOINT_DIR.exists():
        raise FileNotFoundError(f"Checkpoint directory not found: {CHECKPOINT_DIR}")

    all_questions = []
    checkpoint_files = sorted(CHECKPOINT_DIR.glob(CHECKPOINT_PATTERN))
    checkpoint_files = [f for f in checkpoint_files if not f.name.endswith('.bak')]

    if not checkpoint_files:
        raise FileNotFoundError(f"No checkpoint files found matching {CHECKPOINT_PATTERN}")

    logger.info(f"Loading {len(checkpoint_files)} checkpoint files")
    for cp in checkpoint_files:
        try:
            with open(cp, "r", encoding="utf-8") as f:
                questions = json.load(f)
            disease = cp.stem.replace("stage2_tagged_", "").upper()
            for q in questions:
                q["_source_disease"] = disease
            all_questions.extend(questions)
            logger.info(f"  {cp.name}: {len(questions)} questions")
        except Exception as e:
            logger.warning(f"  Error loading {cp.name}: {e}")

    logger.info(f"Total questions loaded: {len(all_questions)}")
    return all_questions


def compute_metrics(questions):
    # Summary
    total_questions = len(questions)
    questions_with_edits = sum(1 for q in questions if get_real_errors(q))
    total_fields = 0
    total_corrections = 0
    for q in questions:
        fv = q.get("field_votes", {}) or {}
        total_fields += len(fv)
        total_corrections += len(get_real_errors(q))

    overall_accuracy = (total_fields - total_corrections) / total_fields * 100 if total_fields > 0 else 0

    summary = {
        "total_questions": total_questions,
        "questions_with_edits": questions_with_edits,
        "question_edit_rate": round(questions_with_edits / total_questions * 100, 1) if total_questions > 0 else 0,
        "total_fields": total_fields,
        "total_corrections": total_corrections,
        "overall_accuracy": round(overall_accuracy, 1),
        "generated_at": datetime.now().isoformat(),
    }

    # By Batch
    batch_stats = defaultdict(lambda: {"total_questions": 0, "questions_with_edits": 0, "total_fields": 0, "edited_fields": 0})
    for q in questions:
        batch = extract_batch(q.get("tagged_at"))
        real_errors = get_real_errors(q)
        fv = q.get("field_votes", {}) or {}
        batch_stats[batch]["total_questions"] += 1
        batch_stats[batch]["total_fields"] += len(fv)
        if real_errors:
            batch_stats[batch]["questions_with_edits"] += 1
            batch_stats[batch]["edited_fields"] += len(real_errors)

    by_batch = []
    for batch, s in sorted(batch_stats.items()):
        q_acc = (s["total_questions"] - s["questions_with_edits"]) / s["total_questions"] * 100 if s["total_questions"] > 0 else 0
        f_acc = (s["total_fields"] - s["edited_fields"]) / s["total_fields"] * 100 if s["total_fields"] > 0 else 0
        by_batch.append({"batch": batch, "total_questions": s["total_questions"], "questions_with_edits": s["questions_with_edits"],
                         "question_accuracy": round(q_acc, 1), "total_fields": s["total_fields"], "edited_fields": s["edited_fields"],
                         "field_accuracy": round(f_acc, 1)})

    # By Disease
    disease_stats = defaultdict(lambda: {"total_questions": 0, "questions_with_edits": 0, "total_fields": 0, "edited_fields": 0})
    for q in questions:
        disease = q.get("_source_disease", "Unknown")
        real_errors = get_real_errors(q)
        fv = q.get("field_votes", {}) or {}
        disease_stats[disease]["total_questions"] += 1
        disease_stats[disease]["total_fields"] += len(fv)
        if real_errors:
            disease_stats[disease]["questions_with_edits"] += 1
            disease_stats[disease]["edited_fields"] += len(real_errors)

    by_disease = []
    for disease, s in sorted(disease_stats.items()):
        q_acc = (s["total_questions"] - s["questions_with_edits"]) / s["total_questions"] * 100 if s["total_questions"] > 0 else 0
        f_acc = (s["total_fields"] - s["edited_fields"]) / s["total_fields"] * 100 if s["total_fields"] > 0 else 0
        by_disease.append({"disease": disease, "total_questions": s["total_questions"], "questions_with_edits": s["questions_with_edits"],
                           "question_accuracy": round(q_acc, 1), "total_fields": s["total_fields"], "edited_fields": s["edited_fields"],
                           "field_accuracy": round(f_acc, 1)})

    # By Model
    model_stats = {m: {"correct": 0, "total": 0, "null_to_needed": 0, "value_to_cleared": 0} for m in ["gpt", "claude", "gemini"]}
    for q in questions:
        fv = q.get("field_votes", {}) or {}
        ft = q.get("final_tags", {}) or {}
        for field, votes in fv.items():
            if not isinstance(votes, dict):
                continue
            human_value = normalize_value(ft.get(field))
            for model in ["gpt", "claude", "gemini"]:
                model_value = normalize_value(votes.get(f"{model}_value"))
                model_stats[model]["total"] += 1
                if model_value == human_value:
                    model_stats[model]["correct"] += 1
                elif model_value is None and human_value is not None:
                    model_stats[model]["null_to_needed"] += 1
                elif model_value is not None and human_value is None:
                    model_stats[model]["value_to_cleared"] += 1

    by_model = []
    for model, s in model_stats.items():
        acc = s["correct"] / s["total"] * 100 if s["total"] > 0 else 0
        by_model.append({"model": model.upper(), "accuracy": round(acc, 1), "correct": s["correct"],
                         "wrong": s["total"] - s["correct"] - s["null_to_needed"] - s["value_to_cleared"],
                         "null_to_needed": s["null_to_needed"], "value_to_cleared": s["value_to_cleared"]})

    # By Agreement Level
    agreement_stats = {level: {"total_fields": 0, "edited_fields": 0} for level in ["unanimous", "majority", "conflict"]}
    for q in questions:
        edited_fields = set(get_real_errors(q))
        fv = q.get("field_votes", {}) or {}
        for field, votes in fv.items():
            if not isinstance(votes, dict):
                continue
            agreement = votes.get("agreement", "unknown")
            if agreement in agreement_stats:
                agreement_stats[agreement]["total_fields"] += 1
                if field in edited_fields:
                    agreement_stats[agreement]["edited_fields"] += 1

    by_agreement = []
    for level, s in agreement_stats.items():
        acc = (s["total_fields"] - s["edited_fields"]) / s["total_fields"] * 100 if s["total_fields"] > 0 else 0
        err = s["edited_fields"] / s["total_fields"] * 100 if s["total_fields"] > 0 else 0
        by_agreement.append({"level": level, "total_fields": s["total_fields"], "edited_fields": s["edited_fields"],
                             "accuracy": round(acc, 1), "error_rate": round(err, 1)})

    # By Field Group
    group_stats = {group: {"total_fields": 0, "edited_fields": 0, "wrong_to_fixed": 0, "null_to_added": 0, "value_to_cleared": 0}
                   for group in list(FIELD_GROUPS.keys()) + ["Other"]}
    for q in questions:
        edited_fields = set(get_real_errors(q))
        fv = q.get("field_votes", {}) or {}
        ft = q.get("final_tags", {}) or {}
        for field, votes in fv.items():
            if not isinstance(votes, dict):
                continue
            group = get_field_group(field)
            group_stats[group]["total_fields"] += 1
            if field in edited_fields:
                group_stats[group]["edited_fields"] += 1
                llm_value = normalize_value(votes.get("final_value"))
                human_value = normalize_value(ft.get(field))
                ct = get_correction_type(llm_value, human_value)
                if ct != "no_change":
                    group_stats[group][ct] += 1

    by_field_group = []
    for group, s in group_stats.items():
        if s["total_fields"] == 0:
            continue
        acc = (s["total_fields"] - s["edited_fields"]) / s["total_fields"] * 100
        err = s["edited_fields"] / s["total_fields"] * 100
        by_field_group.append({"group": group, "total_fields": s["total_fields"], "edited_fields": s["edited_fields"],
                               "accuracy": round(acc, 1), "error_rate": round(err, 1),
                               "wrong_to_fixed": s["wrong_to_fixed"], "null_to_added": s["null_to_added"],
                               "value_to_cleared": s["value_to_cleared"]})
    by_field_group.sort(key=lambda x: x["error_rate"], reverse=True)

    # Top Problem Fields
    per_field = defaultdict(lambda: {"total": 0, "errors": 0, "corrections": defaultdict(int)})
    for q in questions:
        edited_fields = set(get_real_errors(q))
        fv = q.get("field_votes", {}) or {}
        ft = q.get("final_tags", {}) or {}
        for field, votes in fv.items():
            if not isinstance(votes, dict):
                continue
            per_field[field]["total"] += 1
            if field in edited_fields:
                per_field[field]["errors"] += 1
                llm_val = votes.get("final_value") or "(null)"
                human_val = ft.get(field) or "(cleared)"
                per_field[field]["corrections"][f"{llm_val} -> {human_val}"] += 1

    top_problem_fields = []
    for field, s in per_field.items():
        if s["total"] == 0:
            continue
        error_rate = s["errors"] / s["total"] * 100
        top_corrections = sorted(s["corrections"].items(), key=lambda x: -x[1])[:3]
        top_problem_fields.append({"field": field, "group": get_field_group(field), "total": s["total"],
                                   "errors": s["errors"], "error_rate": round(error_rate, 1),
                                   "top_corrections": [{"pattern": p, "count": c} for p, c in top_corrections]})
    top_problem_fields.sort(key=lambda x: x["error_rate"], reverse=True)
    top_problem_fields = top_problem_fields[:15]

    # Model Disagreement Analysis
    dissenter_stats = {m: {"times": 0, "dissenter_right": 0, "majority_right": 0} for m in ["gpt", "claude", "gemini"]}
    total_disagreements = 0
    for q in questions:
        fv = q.get("field_votes", {}) or {}
        ft = q.get("final_tags", {}) or {}
        for field, votes in fv.items():
            if not isinstance(votes, dict):
                continue
            gpt_val = normalize_value(votes.get("gpt_value"))
            claude_val = normalize_value(votes.get("claude_value"))
            gemini_val = normalize_value(votes.get("gemini_value"))
            human_val = normalize_value(ft.get(field))
            values = [gpt_val, claude_val, gemini_val]
            if len(set(values)) == 2:
                total_disagreements += 1
                for model, model_val in [("gpt", gpt_val), ("claude", claude_val), ("gemini", gemini_val)]:
                    other_vals = [v for m, v in [("gpt", gpt_val), ("claude", claude_val), ("gemini", gemini_val)] if m != model]
                    if other_vals[0] == other_vals[1] and model_val != other_vals[0]:
                        dissenter_stats[model]["times"] += 1
                        if model_val == human_val:
                            dissenter_stats[model]["dissenter_right"] += 1
                        if other_vals[0] == human_val:
                            dissenter_stats[model]["majority_right"] += 1

    model_disagreement_analysis = {"total_disagreements": total_disagreements, "by_dissenter": {}}
    for model, s in dissenter_stats.items():
        if s["times"] > 0:
            model_disagreement_analysis["by_dissenter"][model.upper()] = {
                "times_dissented": s["times"],
                "dissenter_correct": s["dissenter_right"],
                "dissenter_correct_pct": round(s["dissenter_right"] / s["times"] * 100, 1),
                "majority_correct": s["majority_right"],
                "majority_correct_pct": round(s["majority_right"] / s["times"] * 100, 1),
            }

    return {
        "summary": summary,
        "by_batch": by_batch,
        "by_disease": by_disease,
        "by_model": by_model,
        "by_agreement": by_agreement,
        "by_field_group": by_field_group,
        "top_problem_fields": top_problem_fields,
        "model_disagreement_analysis": model_disagreement_analysis,
    }


def upload_to_supabase(metrics, dry_run=False):
    from supabase import create_client

    url = os.getenv('SUPABASE_URL') or os.getenv('VITE_SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_KEY')

    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY are required")

    client = create_client(url, key)

    if dry_run:
        logger.info("[DRY RUN] Would upload metrics to eval_metrics table")
        logger.info(f"  Summary: {json.dumps(metrics['summary'], indent=2)}")
        return

    # Delete old metrics, insert new one
    try:
        client.table('eval_metrics').delete().gte('id', 0).execute()
    except Exception as e:
        logger.warning(f"Could not clear old metrics: {e}")

    result = client.table('eval_metrics').insert({
        'metrics': metrics,
        'generated_at': metrics['summary']['generated_at'],
    }).execute()

    if result.data:
        logger.info(f"Uploaded eval metrics (id={result.data[0]['id']})")
    else:
        logger.error("Failed to upload metrics")


def main():
    parser = argparse.ArgumentParser(description="Upload LLM Eval Metrics to Supabase")
    parser.add_argument("--dry-run", action="store_true", help="Preview without uploading")
    args = parser.parse_args()

    questions = load_checkpoints()
    metrics = compute_metrics(questions)

    logger.info(f"\nMetrics computed:")
    logger.info(f"  Questions: {metrics['summary']['total_questions']}")
    logger.info(f"  Fields: {metrics['summary']['total_fields']}")
    logger.info(f"  Accuracy: {metrics['summary']['overall_accuracy']}%")
    logger.info(f"  Diseases: {len(metrics['by_disease'])}")

    upload_to_supabase(metrics, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
