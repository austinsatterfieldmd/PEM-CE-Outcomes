"""
LLM Evaluation API endpoints.

Provides accuracy metrics computed from the tagged checkpoint file:
- Summary statistics (overall accuracy, by model, by batch)
- Per-model comparison
- Agreement level analysis
- Field group breakdown
- Top problem fields
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import json
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/eval", tags=["evaluation"])

# Path to checkpoint file
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
CHECKPOINT_FILE = PROJECT_ROOT / "data" / "checkpoints" / "stage2_tagged_multiple_myeloma.json"

# Field groups for analysis
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


# ========== Pydantic Models ==========

class BatchStats(BaseModel):
    batch: str
    total_questions: int
    questions_with_edits: int
    question_accuracy: float
    total_fields: int
    edited_fields: int
    field_accuracy: float


class ModelStats(BaseModel):
    model: str
    accuracy: float
    correct: int
    wrong: int
    null_to_needed: int
    value_to_cleared: int


class AgreementStats(BaseModel):
    level: str
    total_fields: int
    edited_fields: int
    accuracy: float
    error_rate: float


class FieldGroupStats(BaseModel):
    group: str
    total_fields: int
    edited_fields: int
    accuracy: float
    error_rate: float
    wrong_to_fixed: int
    null_to_added: int
    value_to_cleared: int


class FieldStats(BaseModel):
    field: str
    group: str
    total: int
    errors: int
    error_rate: float
    top_corrections: List[Dict[str, Any]]


class EvalSummary(BaseModel):
    total_questions: int
    questions_with_edits: int
    question_edit_rate: float
    total_fields: int
    total_corrections: int
    overall_accuracy: float
    generated_at: str


class EvalMetrics(BaseModel):
    summary: EvalSummary
    by_batch: List[BatchStats]
    by_model: List[ModelStats]
    by_agreement: List[AgreementStats]
    by_field_group: List[FieldGroupStats]
    top_problem_fields: List[FieldStats]
    model_disagreement_analysis: Dict[str, Any]


# ========== Helper Functions ==========

def normalize_value(v) -> Optional[str]:
    """Normalize a value for comparison (case-insensitive)."""
    if v in (None, "", "null", "None", "none"):
        return None
    return str(v).strip().lower()


def get_correction_type(llm_value: Optional[str], human_value: Optional[str]) -> str:
    """Determine the type of correction made."""
    llm_is_null = llm_value is None
    human_is_null = human_value is None

    if llm_is_null and not human_is_null:
        return "null_to_added"
    elif not llm_is_null and human_is_null:
        return "value_to_cleared"
    elif not llm_is_null and not human_is_null:
        return "wrong_to_fixed"
    else:
        return "no_change"


def extract_batch(tagged_at: str) -> str:
    """Extract batch identifier from tagged_at timestamp."""
    if not tagged_at:
        return "Unknown"
    try:
        dt = datetime.fromisoformat(tagged_at.replace("Z", "+00:00"))
        return dt.strftime("%b-%d")
    except:
        return "Unknown"


def get_field_group(field_name: str) -> str:
    """Get the group a field belongs to."""
    for group, fields in FIELD_GROUPS.items():
        if field_name in fields:
            return group
    return "Other"


def get_real_errors(q: dict) -> list[str]:
    """Get list of fields with real errors (ignoring capitalization)."""
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


def load_checkpoint() -> list[dict]:
    """Load the tagged checkpoint data."""
    if not CHECKPOINT_FILE.exists():
        raise HTTPException(status_code=404, detail=f"Checkpoint file not found: {CHECKPOINT_FILE}")

    with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def compute_metrics(questions: list[dict]) -> EvalMetrics:
    """Compute all evaluation metrics from checkpoint data."""

    # ========== Summary Stats ==========
    total_questions = len(questions)
    questions_with_edits = sum(1 for q in questions if get_real_errors(q))

    total_fields = 0
    total_corrections = 0

    for q in questions:
        field_votes = q.get("field_votes", {}) or {}
        total_fields += len(field_votes)
        total_corrections += len(get_real_errors(q))

    overall_accuracy = (total_fields - total_corrections) / total_fields * 100 if total_fields > 0 else 0

    summary = EvalSummary(
        total_questions=total_questions,
        questions_with_edits=questions_with_edits,
        question_edit_rate=questions_with_edits / total_questions * 100 if total_questions > 0 else 0,
        total_fields=total_fields,
        total_corrections=total_corrections,
        overall_accuracy=round(overall_accuracy, 1),
        generated_at=datetime.now().isoformat()
    )

    # ========== By Batch ==========
    batch_stats = defaultdict(lambda: {
        "total_questions": 0,
        "questions_with_edits": 0,
        "total_fields": 0,
        "edited_fields": 0
    })

    for q in questions:
        batch = extract_batch(q.get("tagged_at"))
        real_errors = get_real_errors(q)
        field_votes = q.get("field_votes", {}) or {}

        batch_stats[batch]["total_questions"] += 1
        batch_stats[batch]["total_fields"] += len(field_votes)

        if real_errors:
            batch_stats[batch]["questions_with_edits"] += 1
            batch_stats[batch]["edited_fields"] += len(real_errors)

    by_batch = []
    for batch, stats in sorted(batch_stats.items()):
        q_acc = (stats["total_questions"] - stats["questions_with_edits"]) / stats["total_questions"] * 100 if stats["total_questions"] > 0 else 0
        f_acc = (stats["total_fields"] - stats["edited_fields"]) / stats["total_fields"] * 100 if stats["total_fields"] > 0 else 0
        by_batch.append(BatchStats(
            batch=batch,
            total_questions=stats["total_questions"],
            questions_with_edits=stats["questions_with_edits"],
            question_accuracy=round(q_acc, 1),
            total_fields=stats["total_fields"],
            edited_fields=stats["edited_fields"],
            field_accuracy=round(f_acc, 1)
        ))

    # ========== By Model ==========
    model_stats = {
        "gpt": {"correct": 0, "total": 0, "null_to_needed": 0, "value_to_cleared": 0},
        "claude": {"correct": 0, "total": 0, "null_to_needed": 0, "value_to_cleared": 0},
        "gemini": {"correct": 0, "total": 0, "null_to_needed": 0, "value_to_cleared": 0}
    }

    for q in questions:
        field_votes = q.get("field_votes", {}) or {}
        final_tags = q.get("final_tags", {}) or {}

        for field, fv in field_votes.items():
            if not isinstance(fv, dict):
                continue

            human_value = normalize_value(final_tags.get(field))

            for model in ["gpt", "claude", "gemini"]:
                model_value = normalize_value(fv.get(f"{model}_value"))
                model_stats[model]["total"] += 1

                if model_value == human_value:
                    model_stats[model]["correct"] += 1
                elif model_value is None and human_value is not None:
                    model_stats[model]["null_to_needed"] += 1
                elif model_value is not None and human_value is None:
                    model_stats[model]["value_to_cleared"] += 1

    by_model = []
    for model, stats in model_stats.items():
        acc = stats["correct"] / stats["total"] * 100 if stats["total"] > 0 else 0
        by_model.append(ModelStats(
            model=model.upper(),
            accuracy=round(acc, 1),
            correct=stats["correct"],
            wrong=stats["total"] - stats["correct"] - stats["null_to_needed"] - stats["value_to_cleared"],
            null_to_needed=stats["null_to_needed"],
            value_to_cleared=stats["value_to_cleared"]
        ))

    # ========== By Agreement Level ==========
    agreement_stats = {
        "unanimous": {"total_fields": 0, "edited_fields": 0},
        "majority": {"total_fields": 0, "edited_fields": 0},
        "conflict": {"total_fields": 0, "edited_fields": 0}
    }

    for q in questions:
        edited_fields = set(get_real_errors(q))
        field_votes = q.get("field_votes", {}) or {}

        for field, fv in field_votes.items():
            if not isinstance(fv, dict):
                continue

            agreement = fv.get("agreement", "unknown")
            if agreement in agreement_stats:
                agreement_stats[agreement]["total_fields"] += 1
                if field in edited_fields:
                    agreement_stats[agreement]["edited_fields"] += 1

    by_agreement = []
    for level, stats in agreement_stats.items():
        acc = (stats["total_fields"] - stats["edited_fields"]) / stats["total_fields"] * 100 if stats["total_fields"] > 0 else 0
        err = stats["edited_fields"] / stats["total_fields"] * 100 if stats["total_fields"] > 0 else 0
        by_agreement.append(AgreementStats(
            level=level,
            total_fields=stats["total_fields"],
            edited_fields=stats["edited_fields"],
            accuracy=round(acc, 1),
            error_rate=round(err, 1)
        ))

    # ========== By Field Group ==========
    group_stats = {group: {
        "total_fields": 0,
        "edited_fields": 0,
        "wrong_to_fixed": 0,
        "null_to_added": 0,
        "value_to_cleared": 0
    } for group in list(FIELD_GROUPS.keys()) + ["Other"]}

    for q in questions:
        edited_fields = set(get_real_errors(q))
        field_votes = q.get("field_votes", {}) or {}
        final_tags = q.get("final_tags", {}) or {}

        for field, fv in field_votes.items():
            if not isinstance(fv, dict):
                continue

            group = get_field_group(field)
            group_stats[group]["total_fields"] += 1

            if field in edited_fields:
                group_stats[group]["edited_fields"] += 1
                llm_value = normalize_value(fv.get("final_value"))
                human_value = normalize_value(final_tags.get(field))
                ct = get_correction_type(llm_value, human_value)
                if ct != "no_change":
                    group_stats[group][ct] += 1

    by_field_group = []
    for group, stats in group_stats.items():
        if stats["total_fields"] == 0:
            continue
        acc = (stats["total_fields"] - stats["edited_fields"]) / stats["total_fields"] * 100
        err = stats["edited_fields"] / stats["total_fields"] * 100
        by_field_group.append(FieldGroupStats(
            group=group,
            total_fields=stats["total_fields"],
            edited_fields=stats["edited_fields"],
            accuracy=round(acc, 1),
            error_rate=round(err, 1),
            wrong_to_fixed=stats["wrong_to_fixed"],
            null_to_added=stats["null_to_added"],
            value_to_cleared=stats["value_to_cleared"]
        ))

    # Sort by error rate descending
    by_field_group.sort(key=lambda x: x.error_rate, reverse=True)

    # ========== Top Problem Fields ==========
    per_field = defaultdict(lambda: {
        "total": 0,
        "errors": 0,
        "corrections": defaultdict(int)
    })

    for q in questions:
        edited_fields = set(get_real_errors(q))
        field_votes = q.get("field_votes", {}) or {}
        final_tags = q.get("final_tags", {}) or {}

        for field, fv in field_votes.items():
            if not isinstance(fv, dict):
                continue

            per_field[field]["total"] += 1

            if field in edited_fields:
                per_field[field]["errors"] += 1
                llm_val = fv.get("final_value") or "(null)"
                human_val = final_tags.get(field) or "(cleared)"
                correction_key = f"{llm_val} -> {human_val}"
                per_field[field]["corrections"][correction_key] += 1

    top_problem_fields = []
    for field, stats in per_field.items():
        if stats["total"] == 0:
            continue
        error_rate = stats["errors"] / stats["total"] * 100

        # Get top 3 correction patterns
        top_corrections = sorted(stats["corrections"].items(), key=lambda x: -x[1])[:3]
        top_corrections_list = [{"pattern": p, "count": c} for p, c in top_corrections]

        top_problem_fields.append(FieldStats(
            field=field,
            group=get_field_group(field),
            total=stats["total"],
            errors=stats["errors"],
            error_rate=round(error_rate, 1),
            top_corrections=top_corrections_list
        ))

    # Sort by error rate and take top 15
    top_problem_fields.sort(key=lambda x: x.error_rate, reverse=True)
    top_problem_fields = top_problem_fields[:15]

    # ========== Model Disagreement Analysis ==========
    dissenter_stats = {
        "gpt": {"times": 0, "dissenter_right": 0, "majority_right": 0},
        "claude": {"times": 0, "dissenter_right": 0, "majority_right": 0},
        "gemini": {"times": 0, "dissenter_right": 0, "majority_right": 0}
    }
    total_disagreements = 0

    for q in questions:
        field_votes = q.get("field_votes", {}) or {}
        final_tags = q.get("final_tags", {}) or {}

        for field, fv in field_votes.items():
            if not isinstance(fv, dict):
                continue

            gpt_val = normalize_value(fv.get("gpt_value"))
            claude_val = normalize_value(fv.get("claude_value"))
            gemini_val = normalize_value(fv.get("gemini_value"))
            human_val = normalize_value(final_tags.get(field))

            # Check for majority (2-1 split)
            values = [gpt_val, claude_val, gemini_val]
            if len(set(values)) == 2:  # 2-1 split
                total_disagreements += 1
                # Find the dissenter
                for model, model_val in [("gpt", gpt_val), ("claude", claude_val), ("gemini", gemini_val)]:
                    other_vals = [v for m, v in [("gpt", gpt_val), ("claude", claude_val), ("gemini", gemini_val)] if m != model]
                    if other_vals[0] == other_vals[1] and model_val != other_vals[0]:
                        # This model is the dissenter
                        dissenter_stats[model]["times"] += 1
                        if model_val == human_val:
                            dissenter_stats[model]["dissenter_right"] += 1
                        if other_vals[0] == human_val:
                            dissenter_stats[model]["majority_right"] += 1

    model_disagreement_analysis = {
        "total_disagreements": total_disagreements,
        "by_dissenter": {}
    }

    for model, stats in dissenter_stats.items():
        if stats["times"] > 0:
            model_disagreement_analysis["by_dissenter"][model.upper()] = {
                "times_dissented": stats["times"],
                "dissenter_correct": stats["dissenter_right"],
                "dissenter_correct_pct": round(stats["dissenter_right"] / stats["times"] * 100, 1),
                "majority_correct": stats["majority_right"],
                "majority_correct_pct": round(stats["majority_right"] / stats["times"] * 100, 1)
            }

    return EvalMetrics(
        summary=summary,
        by_batch=by_batch,
        by_model=by_model,
        by_agreement=by_agreement,
        by_field_group=by_field_group,
        top_problem_fields=top_problem_fields,
        model_disagreement_analysis=model_disagreement_analysis
    )


# ========== API Endpoints ==========

@router.get("/metrics", response_model=EvalMetrics)
async def get_eval_metrics():
    """Get comprehensive LLM evaluation metrics."""
    try:
        questions = load_checkpoint()
        return compute_metrics(questions)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error computing eval metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_eval_summary():
    """Get just the summary stats (faster endpoint)."""
    try:
        questions = load_checkpoint()
        metrics = compute_metrics(questions)
        return metrics.summary
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error computing eval summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))
