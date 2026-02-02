"""
Comprehensive Accuracy Analysis V2 for LLM Tagging

Deep-dive analysis covering all 7 dimensions:
1. Performance by batch (improvement over iterations)
2. Per-model comparison (GPT vs Claude vs Gemini)
3. Agreement level analysis (unanimous vs majority vs conflict)
4. Tag group analysis (Core, Treatment, Clinical, Quality)
5. Per-field accuracy with trends
6. Correction type patterns
7. Dissenter analysis (when models disagreed, who was right?)

Data source: Checkpoint file with embedded human_edited_fields
- field_votes[field].final_value = LLM consensus BEFORE human review
- final_tags[field] = value AFTER human review
- human_edited_fields = list of fields changed by human

Usage:
    python scripts/comprehensive_accuracy_analysis_v2.py
"""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from datetime import datetime
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent
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


def load_checkpoint(checkpoint_file: Path) -> list[dict]:
    """Load the tagged checkpoint data."""
    with open(checkpoint_file, "r", encoding="utf-8") as f:
        return json.load(f)


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


def normalize_value(v) -> Optional[str]:
    """Normalize a value for comparison (case-insensitive)."""
    if v in (None, "", "null", "None", "none"):
        return None
    # Case-insensitive comparison - "daratumumab" == "Daratumumab"
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


def get_real_errors(q: dict) -> list[str]:
    """
    Get list of fields with REAL errors (ignoring capitalization differences).
    A real error is when normalized LLM value != normalized human value.
    """
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


def analyze_by_batch(questions: list[dict]) -> dict:
    """Analyze accuracy trends by batch (tagged_at date)."""
    batch_stats = defaultdict(lambda: {
        "total_questions": 0,
        "questions_with_edits": 0,
        "total_fields": 0,
        "edited_fields": 0,
        "correction_types": {"wrong_to_fixed": 0, "null_to_added": 0, "value_to_cleared": 0}
    })

    for q in questions:
        batch = extract_batch(q.get("tagged_at"))
        # Use real errors (ignoring capitalization) instead of human_edited_fields
        real_errors = get_real_errors(q)
        field_votes = q.get("field_votes", {}) or {}
        final_tags = q.get("final_tags", {}) or {}

        batch_stats[batch]["total_questions"] += 1
        batch_stats[batch]["total_fields"] += len(field_votes)

        if real_errors:
            batch_stats[batch]["questions_with_edits"] += 1
            batch_stats[batch]["edited_fields"] += len(real_errors)

            for field in real_errors:
                fv = field_votes.get(field, {})
                llm_value = normalize_value(fv.get("final_value"))
                human_value = normalize_value(final_tags.get(field))

                ct = get_correction_type(llm_value, human_value)
                if ct != "no_change":
                    batch_stats[batch]["correction_types"][ct] += 1

    # Calculate accuracy percentages
    for batch, stats in batch_stats.items():
        total_f = stats["total_fields"]
        edited_f = stats["edited_fields"]
        if total_f > 0:
            stats["field_accuracy_pct"] = round((total_f - edited_f) / total_f * 100, 2)

        total_q = stats["total_questions"]
        edited_q = stats["questions_with_edits"]
        if total_q > 0:
            stats["question_accuracy_pct"] = round((total_q - edited_q) / total_q * 100, 2)

    # Sort by batch date
    sorted_batches = sorted(batch_stats.items(), key=lambda x: x[0])
    return dict(sorted_batches)


def analyze_model_accuracy(questions: list[dict]) -> dict:
    """Analyze per-model accuracy by comparing to human-verified values."""
    model_stats = {
        "gpt": {"correct": 0, "wrong": 0, "null_when_needed": 0, "value_when_not_needed": 0, "total": 0},
        "claude": {"correct": 0, "wrong": 0, "null_when_needed": 0, "value_when_not_needed": 0, "total": 0},
        "gemini": {"correct": 0, "wrong": 0, "null_when_needed": 0, "value_when_not_needed": 0, "total": 0}
    }

    # Track who was right in disagreements
    disagreement_analysis = {
        "total_disagreements": 0,
        "gpt_was_right": 0,
        "claude_was_right": 0,
        "gemini_was_right": 0,
        "none_were_right": 0
    }

    for q in questions:
        field_votes = q.get("field_votes", {}) or {}
        final_tags = q.get("final_tags", {}) or {}

        for field, fv in field_votes.items():
            if not isinstance(fv, dict):
                continue

            human_value = normalize_value(final_tags.get(field))
            agreement = fv.get("agreement", "")

            for model in ["gpt", "claude", "gemini"]:
                model_value = normalize_value(fv.get(f"{model}_value"))
                model_stats[model]["total"] += 1

                if model_value == human_value:
                    model_stats[model]["correct"] += 1
                elif model_value is None and human_value is not None:
                    model_stats[model]["null_when_needed"] += 1
                    model_stats[model]["wrong"] += 1
                elif model_value is not None and human_value is None:
                    model_stats[model]["value_when_not_needed"] += 1
                    model_stats[model]["wrong"] += 1
                else:
                    model_stats[model]["wrong"] += 1

            # Track disagreements
            if agreement in ("majority", "conflict"):
                disagreement_analysis["total_disagreements"] += 1

                gpt_right = normalize_value(fv.get("gpt_value")) == human_value
                claude_right = normalize_value(fv.get("claude_value")) == human_value
                gemini_right = normalize_value(fv.get("gemini_value")) == human_value

                if gpt_right:
                    disagreement_analysis["gpt_was_right"] += 1
                if claude_right:
                    disagreement_analysis["claude_was_right"] += 1
                if gemini_right:
                    disagreement_analysis["gemini_was_right"] += 1
                if not (gpt_right or claude_right or gemini_right):
                    disagreement_analysis["none_were_right"] += 1

    # Calculate accuracy percentages
    for model in model_stats:
        total = model_stats[model]["total"]
        if total > 0:
            model_stats[model]["accuracy_pct"] = round(
                model_stats[model]["correct"] / total * 100, 2
            )

    return {
        "model_stats": model_stats,
        "disagreement_analysis": disagreement_analysis
    }


def analyze_by_agreement_level(questions: list[dict]) -> dict:
    """Analyze accuracy by agreement level (unanimous, majority, conflict)."""
    agreement_stats = {
        "unanimous": {"total_fields": 0, "edited_fields": 0, "questions": set()},
        "majority": {"total_fields": 0, "edited_fields": 0, "questions": set()},
        "conflict": {"total_fields": 0, "edited_fields": 0, "questions": set()}
    }

    for q in questions:
        qid = q.get("question_id")
        edited_fields = set(get_real_errors(q))
        field_votes = q.get("field_votes", {}) or {}
        overall_agreement = q.get("agreement", "")

        if overall_agreement in agreement_stats:
            agreement_stats[overall_agreement]["questions"].add(qid)

        for field, fv in field_votes.items():
            if not isinstance(fv, dict):
                continue

            field_agreement = fv.get("agreement", "")
            if field_agreement not in agreement_stats:
                continue

            agreement_stats[field_agreement]["total_fields"] += 1
            if field in edited_fields:
                agreement_stats[field_agreement]["edited_fields"] += 1

    # Calculate accuracy and convert sets to counts
    for level in agreement_stats:
        agreement_stats[level]["question_count"] = len(agreement_stats[level]["questions"])
        del agreement_stats[level]["questions"]

        total = agreement_stats[level]["total_fields"]
        edited = agreement_stats[level]["edited_fields"]
        if total > 0:
            agreement_stats[level]["accuracy_pct"] = round(
                (total - edited) / total * 100, 2
            )
            agreement_stats[level]["error_rate_pct"] = round(
                edited / total * 100, 2
            )

    return agreement_stats


def analyze_dissenting_model(questions: list[dict]) -> dict:
    """When a model dissented (majority vote), was the dissenter or majority right?"""
    dissenter_stats = {
        "gpt": {"times_dissented": 0, "dissenter_right": 0, "majority_right": 0},
        "claude": {"times_dissented": 0, "dissenter_right": 0, "majority_right": 0},
        "gemini": {"times_dissented": 0, "dissenter_right": 0, "majority_right": 0}
    }

    for q in questions:
        field_votes = q.get("field_votes", {}) or {}
        final_tags = q.get("final_tags", {}) or {}

        for field, fv in field_votes.items():
            if not isinstance(fv, dict):
                continue

            if fv.get("agreement") != "majority":
                continue

            dissenter = fv.get("dissenting_model")
            if not dissenter or dissenter not in dissenter_stats:
                continue

            human_value = normalize_value(final_tags.get(field))
            dissenter_value = normalize_value(fv.get(f"{dissenter}_value"))
            majority_value = normalize_value(fv.get("final_value"))

            dissenter_stats[dissenter]["times_dissented"] += 1

            if dissenter_value == human_value:
                dissenter_stats[dissenter]["dissenter_right"] += 1
            elif majority_value == human_value:
                dissenter_stats[dissenter]["majority_right"] += 1

    # Calculate percentages
    for model in dissenter_stats:
        times = dissenter_stats[model]["times_dissented"]
        if times > 0:
            dissenter_stats[model]["dissenter_right_pct"] = round(
                dissenter_stats[model]["dissenter_right"] / times * 100, 2
            )
            dissenter_stats[model]["majority_right_pct"] = round(
                dissenter_stats[model]["majority_right"] / times * 100, 2
            )

    return dissenter_stats


def analyze_by_field_group(questions: list[dict]) -> dict:
    """Analyze accuracy by field group."""
    group_stats = {group: {
        "total_fields": 0,
        "edited_fields": 0,
        "correction_types": {"wrong_to_fixed": 0, "null_to_added": 0, "value_to_cleared": 0}
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
                    group_stats[group]["correction_types"][ct] += 1

    # Calculate accuracy
    for group in group_stats:
        total = group_stats[group]["total_fields"]
        edited = group_stats[group]["edited_fields"]
        if total > 0:
            group_stats[group]["accuracy_pct"] = round(
                (total - edited) / total * 100, 2
            )
            group_stats[group]["error_rate_pct"] = round(
                edited / total * 100, 2
            )

    return group_stats


def analyze_per_field(questions: list[dict]) -> dict:
    """Detailed per-field accuracy analysis."""
    field_stats = defaultdict(lambda: {
        "total": 0,
        "edited": 0,
        "correction_types": {"wrong_to_fixed": 0, "null_to_added": 0, "value_to_cleared": 0},
        "by_agreement": {
            "unanimous": {"total": 0, "edited": 0},
            "majority": {"total": 0, "edited": 0},
            "conflict": {"total": 0, "edited": 0}
        },
        "by_batch": defaultdict(lambda: {"total": 0, "edited": 0}),
        "correction_patterns": Counter(),
        "model_accuracy": {
            "gpt": {"correct": 0, "total": 0},
            "claude": {"correct": 0, "total": 0},
            "gemini": {"correct": 0, "total": 0}
        }
    })

    for q in questions:
        batch = extract_batch(q.get("tagged_at"))
        edited_fields = set(get_real_errors(q))
        field_votes = q.get("field_votes", {}) or {}
        final_tags = q.get("final_tags", {}) or {}

        for field, fv in field_votes.items():
            if not isinstance(fv, dict):
                continue

            human_value = normalize_value(final_tags.get(field))
            llm_value = normalize_value(fv.get("final_value"))
            agreement = fv.get("agreement", "unknown")

            field_stats[field]["total"] += 1
            field_stats[field]["by_batch"][batch]["total"] += 1

            if agreement in field_stats[field]["by_agreement"]:
                field_stats[field]["by_agreement"][agreement]["total"] += 1

            # Per-model accuracy for this field
            for model in ["gpt", "claude", "gemini"]:
                model_value = normalize_value(fv.get(f"{model}_value"))
                field_stats[field]["model_accuracy"][model]["total"] += 1
                if model_value == human_value:
                    field_stats[field]["model_accuracy"][model]["correct"] += 1

            if field in edited_fields:
                field_stats[field]["edited"] += 1
                field_stats[field]["by_batch"][batch]["edited"] += 1

                if agreement in field_stats[field]["by_agreement"]:
                    field_stats[field]["by_agreement"][agreement]["edited"] += 1

                ct = get_correction_type(llm_value, human_value)
                if ct != "no_change":
                    field_stats[field]["correction_types"][ct] += 1

                # Track correction pattern
                llm_display = llm_value if llm_value else "(null)"
                human_display = human_value if human_value else "(cleared)"
                pattern = f"{llm_display} -> {human_display}"
                field_stats[field]["correction_patterns"][pattern] += 1

    # Calculate accuracy percentages
    for field in field_stats:
        total = field_stats[field]["total"]
        edited = field_stats[field]["edited"]
        if total > 0:
            field_stats[field]["accuracy_pct"] = round((total - edited) / total * 100, 2)
            field_stats[field]["error_rate_pct"] = round(edited / total * 100, 2)

        # Per-agreement accuracy
        for level in field_stats[field]["by_agreement"]:
            t = field_stats[field]["by_agreement"][level]["total"]
            e = field_stats[field]["by_agreement"][level]["edited"]
            if t > 0:
                field_stats[field]["by_agreement"][level]["accuracy_pct"] = round(
                    (t - e) / t * 100, 2
                )

        # Per-model accuracy for this field
        for model in field_stats[field]["model_accuracy"]:
            t = field_stats[field]["model_accuracy"][model]["total"]
            c = field_stats[field]["model_accuracy"][model]["correct"]
            if t > 0:
                field_stats[field]["model_accuracy"][model]["accuracy_pct"] = round(
                    c / t * 100, 2
                )

        # Convert defaultdict and Counter
        field_stats[field]["by_batch"] = dict(field_stats[field]["by_batch"])
        field_stats[field]["top_corrections"] = [
            {"pattern": p, "count": c}
            for p, c in field_stats[field]["correction_patterns"].most_common(5)
        ]
        del field_stats[field]["correction_patterns"]

    return dict(field_stats)


def generate_report(analysis: dict) -> str:
    """Generate comprehensive human-readable report."""
    lines = []

    # Header
    lines.append("=" * 100)
    lines.append("COMPREHENSIVE ACCURACY ANALYSIS REPORT V2")
    lines.append(f"Generated: {datetime.now().isoformat()}")
    lines.append("=" * 100)
    lines.append("")

    # Executive Summary
    lines.append("## EXECUTIVE SUMMARY")
    lines.append("-" * 50)
    s = analysis["summary"]
    lines.append(f"Total questions analyzed:     {s['total_questions']}")
    lines.append(f"Questions with human edits:   {s['questions_with_edits']} ({s['questions_with_edits']/s['total_questions']*100:.1f}%)")
    lines.append(f"Total fields analyzed:        {s['total_fields']}")
    lines.append(f"Total field corrections:      {s['total_corrections']}")
    lines.append(f"Overall field accuracy:       {s['overall_accuracy_pct']:.1f}%")
    lines.append("")

    # Section 1: Batch Analysis
    lines.append("=" * 100)
    lines.append("SECTION 1: ACCURACY BY BATCH (Improvement Over Time)")
    lines.append("=" * 100)
    lines.append("")
    lines.append(f"{'Batch':<12} {'Questions':>10} {'Q w/Edits':>10} {'Q Acc%':>10} {'Fields':>10} {'Edited':>8} {'F Acc%':>10}")
    lines.append("-" * 75)

    for batch, stats in analysis["by_batch"].items():
        q_acc = stats.get("question_accuracy_pct", 0)
        f_acc = stats.get("field_accuracy_pct", 0)
        lines.append(
            f"{batch:<12} {stats['total_questions']:>10} {stats['questions_with_edits']:>10} "
            f"{q_acc:>9.1f}% {stats['total_fields']:>10} {stats['edited_fields']:>8} {f_acc:>9.1f}%"
        )

    # Trend analysis
    batches = list(analysis["by_batch"].keys())
    if len(batches) >= 2:
        first_acc = analysis["by_batch"][batches[0]].get("field_accuracy_pct", 0)
        last_acc = analysis["by_batch"][batches[-1]].get("field_accuracy_pct", 0)
        lines.append("")
        lines.append(f"TREND: Field accuracy {first_acc:.1f}% -> {last_acc:.1f}% ({last_acc - first_acc:+.1f} pts)")
    lines.append("")

    # Section 2: Model Comparison
    lines.append("=" * 100)
    lines.append("SECTION 2: MODEL COMPARISON (GPT vs Claude vs Gemini)")
    lines.append("=" * 100)
    lines.append("")
    lines.append("Individual model accuracy (compared to human-verified values):")
    lines.append("")

    ms = analysis["model_accuracy"]["model_stats"]
    lines.append(f"{'Model':<10} {'Accuracy':>10} {'Correct':>10} {'Wrong':>10} {'Null→Needed':>12} {'Val→NotNeed':>12}")
    lines.append("-" * 70)

    for model in ["gpt", "claude", "gemini"]:
        stats = ms[model]
        acc = stats.get("accuracy_pct", 0)
        lines.append(
            f"{model.upper():<10} {acc:>9.1f}% {stats['correct']:>10} {stats['wrong']:>10} "
            f"{stats['null_when_needed']:>12} {stats['value_when_not_needed']:>12}"
        )

    lines.append("")
    lines.append("When models disagreed, who had the correct answer?")
    da = analysis["model_accuracy"]["disagreement_analysis"]
    total_dis = da["total_disagreements"]
    if total_dis > 0:
        lines.append(f"  Total disagreements: {total_dis}")
        for model in ["gpt", "claude", "gemini"]:
            count = da[f"{model}_was_right"]
            pct = count / total_dis * 100
            lines.append(f"  {model.upper()} was right: {count} ({pct:.1f}%)")
        lines.append(f"  None were right: {da['none_were_right']} ({da['none_were_right']/total_dis*100:.1f}%)")
    lines.append("")

    # Section 3: Agreement Level Analysis
    lines.append("=" * 100)
    lines.append("SECTION 3: ACCURACY BY AGREEMENT LEVEL")
    lines.append("=" * 100)
    lines.append("")
    lines.append("How well did unanimous, majority, and conflict votes perform?")
    lines.append("")

    ag = analysis["by_agreement"]
    lines.append(f"{'Agreement':<12} {'Questions':>10} {'Total Fields':>12} {'Edited':>10} {'Accuracy':>10} {'Error Rate':>12}")
    lines.append("-" * 70)

    for level in ["unanimous", "majority", "conflict"]:
        stats = ag[level]
        acc = stats.get("accuracy_pct", 0)
        err = stats.get("error_rate_pct", 0)
        lines.append(
            f"{level:<12} {stats['question_count']:>10} {stats['total_fields']:>12} "
            f"{stats['edited_fields']:>10} {acc:>9.1f}% {err:>11.1f}%"
        )

    lines.append("")
    lines.append("INSIGHT: Unanimous should have highest accuracy, conflict lowest.")
    lines.append("")

    # Section 4: Dissenting Model Analysis
    lines.append("=" * 100)
    lines.append("SECTION 4: DISSENTING MODEL ANALYSIS")
    lines.append("=" * 100)
    lines.append("")
    lines.append("When 2 models agreed and 1 dissented, who was right?")
    lines.append("")

    ds = analysis["dissenting_model"]
    lines.append(f"{'Dissenter':<12} {'Times':>8} {'Dissenter Right':>16} {'Majority Right':>15}")
    lines.append("-" * 55)

    for model in ["gpt", "claude", "gemini"]:
        stats = ds[model]
        dr_pct = stats.get("dissenter_right_pct", 0)
        mr_pct = stats.get("majority_right_pct", 0)
        lines.append(
            f"{model.upper():<12} {stats['times_dissented']:>8} "
            f"{stats['dissenter_right']:>8} ({dr_pct:>5.1f}%) "
            f"{stats['majority_right']:>7} ({mr_pct:>5.1f}%)"
        )
    lines.append("")

    # Section 5: Field Group Analysis
    lines.append("=" * 100)
    lines.append("SECTION 5: ACCURACY BY FIELD GROUP")
    lines.append("=" * 100)
    lines.append("")

    fg = analysis["by_field_group"]
    lines.append(f"{'Field Group':<25} {'Total':>8} {'Edited':>8} {'Accuracy':>10} {'Error Rate':>12}")
    lines.append("-" * 70)

    sorted_groups = sorted(
        [(g, s) for g, s in fg.items() if s["total_fields"] > 0],
        key=lambda x: x[1].get("error_rate_pct", 0),
        reverse=True
    )

    for group, stats in sorted_groups:
        acc = stats.get("accuracy_pct", 0)
        err = stats.get("error_rate_pct", 0)
        lines.append(
            f"{group:<25} {stats['total_fields']:>8} {stats['edited_fields']:>8} "
            f"{acc:>9.1f}% {err:>11.1f}%"
        )

    lines.append("")
    lines.append("Correction type breakdown by group:")
    lines.append(f"{'Group':<25} {'Wrong→Fixed':>12} {'Null→Added':>12} {'Val→Cleared':>12}")
    lines.append("-" * 65)

    for group, stats in sorted_groups:
        ct = stats["correction_types"]
        if sum(ct.values()) > 0:
            lines.append(
                f"{group:<25} {ct['wrong_to_fixed']:>12} {ct['null_to_added']:>12} {ct['value_to_cleared']:>12}"
            )
    lines.append("")

    # Section 6: Top Problem Fields
    lines.append("=" * 100)
    lines.append("SECTION 6: TOP 20 FIELDS WITH HIGHEST ERROR RATES")
    lines.append("=" * 100)
    lines.append("")

    pf = analysis["per_field"]
    sorted_fields = sorted(
        [(f, s) for f, s in pf.items() if s["edited"] > 0],
        key=lambda x: x[1]["error_rate_pct"],
        reverse=True
    )[:20]

    lines.append(f"{'Field':<30} {'Total':>6} {'Errors':>6} {'Rate':>8} {'Group':<20}")
    lines.append("-" * 75)

    for field, stats in sorted_fields:
        group = get_field_group(field)
        err_rate = stats.get("error_rate_pct", 0)
        lines.append(
            f"{field:<30} {stats['total']:>6} {stats['edited']:>6} {err_rate:>7.1f}% {group:<20}"
        )
    lines.append("")

    # Section 7: Detailed Field Analysis
    lines.append("=" * 100)
    lines.append("SECTION 7: DETAILED ANALYSIS OF TOP PROBLEM FIELDS")
    lines.append("=" * 100)

    for field, stats in sorted_fields[:10]:
        if stats["edited"] < 2:
            continue

        lines.append("")
        lines.append(f"### {field}")
        lines.append(f"    Error rate: {stats['error_rate_pct']:.1f}% ({stats['edited']}/{stats['total']})")

        # Correction types
        ct = stats["correction_types"]
        lines.append(f"    Correction types: Wrong→Fixed: {ct['wrong_to_fixed']}, Null→Added: {ct['null_to_added']}, Val→Cleared: {ct['value_to_cleared']}")

        # By agreement level
        lines.append("    By agreement level:")
        for level in ["unanimous", "majority", "conflict"]:
            ba = stats["by_agreement"][level]
            if ba["total"] > 0:
                acc = ba.get("accuracy_pct", 0)
                lines.append(f"      {level}: {acc:.1f}% accuracy ({ba['edited']}/{ba['total']} edited)")

        # Per-model accuracy for this field
        lines.append("    Per-model accuracy:")
        for model in ["gpt", "claude", "gemini"]:
            ma = stats["model_accuracy"][model]
            acc = ma.get("accuracy_pct", 0)
            lines.append(f"      {model.upper()}: {acc:.1f}%")

        # By batch trend
        if stats["by_batch"]:
            lines.append("    By batch:")
            for batch, bs in sorted(stats["by_batch"].items()):
                if bs["total"] > 0:
                    acc = (bs["total"] - bs["edited"]) / bs["total"] * 100
                    lines.append(f"      {batch}: {acc:.1f}% ({bs['edited']}/{bs['total']} edited)")

        # Top correction patterns
        if stats["top_corrections"]:
            lines.append("    Top correction patterns:")
            for p in stats["top_corrections"][:3]:
                lines.append(f"      [{p['count']}x] {p['pattern']}")

    lines.append("")

    # Summary Statistics
    lines.append("=" * 100)
    lines.append("SECTION 8: SUMMARY & KEY INSIGHTS")
    lines.append("=" * 100)
    lines.append("")

    # Overall correction breakdown
    ct_total = analysis["summary"]["correction_types"]
    total_ct = sum(ct_total.values())
    if total_ct > 0:
        lines.append("Overall Correction Type Breakdown:")
        lines.append(f"  LLM wrong, human fixed:   {ct_total['wrong_to_fixed']:>4} ({ct_total['wrong_to_fixed']/total_ct*100:.1f}%)")
        lines.append(f"  LLM null, human added:    {ct_total['null_to_added']:>4} ({ct_total['null_to_added']/total_ct*100:.1f}%)")
        lines.append(f"  LLM value, human cleared: {ct_total['value_to_cleared']:>4} ({ct_total['value_to_cleared']/total_ct*100:.1f}%)")
    lines.append("")

    # Key insights
    lines.append("KEY INSIGHTS:")
    lines.append("")

    # Best/worst model
    best_model = max(ms.keys(), key=lambda m: ms[m].get("accuracy_pct", 0))
    worst_model = min(ms.keys(), key=lambda m: ms[m].get("accuracy_pct", 0))
    lines.append(f"1. Best model: {best_model.upper()} ({ms[best_model].get('accuracy_pct', 0):.1f}% accuracy)")
    lines.append(f"   Worst model: {worst_model.upper()} ({ms[worst_model].get('accuracy_pct', 0):.1f}% accuracy)")

    # Agreement level insight
    unan_acc = ag["unanimous"].get("accuracy_pct", 0)
    conf_acc = ag["conflict"].get("accuracy_pct", 0)
    lines.append(f"2. Unanimous agreement: {unan_acc:.1f}% accurate")
    lines.append(f"   Conflict cases: {conf_acc:.1f}% accurate")
    lines.append(f"   Gap: {unan_acc - conf_acc:.1f} percentage points")

    # Best/worst field group
    if sorted_groups:
        worst_group = sorted_groups[0]
        best_group = sorted_groups[-1]
        lines.append(f"3. Worst field group: {worst_group[0]} ({worst_group[1].get('error_rate_pct', 0):.1f}% error rate)")
        lines.append(f"   Best field group: {best_group[0]} ({best_group[1].get('error_rate_pct', 0):.1f}% error rate)")

    # Top problematic fields
    if sorted_fields:
        lines.append(f"4. Most problematic fields:")
        for field, stats in sorted_fields[:3]:
            lines.append(f"   - {field}: {stats['error_rate_pct']:.1f}% error rate")

    lines.append("")
    lines.append("=" * 100)
    lines.append("END OF REPORT")
    lines.append("=" * 100)

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Comprehensive accuracy analysis V2")
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "accuracy_report_v2.txt",
        help="Output file for text report",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=PROJECT_ROOT / "data" / "accuracy_analysis_v2.json",
        help="Output file for JSON data",
    )
    args = parser.parse_args()

    print("Loading checkpoint data...")
    questions = load_checkpoint(CHECKPOINT_FILE)
    print(f"Loaded {len(questions)} questions")

    print("\nRunning comprehensive analysis...")

    print("  - Analyzing by batch...")
    by_batch = analyze_by_batch(questions)

    print("  - Analyzing model accuracy...")
    model_accuracy = analyze_model_accuracy(questions)

    print("  - Analyzing by agreement level...")
    by_agreement = analyze_by_agreement_level(questions)

    print("  - Analyzing dissenting models...")
    dissenting_model = analyze_dissenting_model(questions)

    print("  - Analyzing by field group...")
    by_field_group = analyze_by_field_group(questions)

    print("  - Analyzing per field...")
    per_field = analyze_per_field(questions)

    # Calculate summary stats
    questions_with_edits = sum(1 for q in questions if get_real_errors(q))
    total_fields = sum(s["total"] for s in per_field.values())
    total_corrections = sum(s["edited"] for s in per_field.values())

    ct_total = {"wrong_to_fixed": 0, "null_to_added": 0, "value_to_cleared": 0}
    for s in per_field.values():
        for ct_type in ct_total:
            ct_total[ct_type] += s["correction_types"][ct_type]

    analysis = {
        "summary": {
            "total_questions": len(questions),
            "questions_with_edits": questions_with_edits,
            "total_fields": total_fields,
            "total_corrections": total_corrections,
            "overall_accuracy_pct": round((total_fields - total_corrections) / total_fields * 100, 2) if total_fields > 0 else 0,
            "correction_types": ct_total
        },
        "by_batch": by_batch,
        "model_accuracy": model_accuracy,
        "by_agreement": by_agreement,
        "dissenting_model": dissenting_model,
        "by_field_group": by_field_group,
        "per_field": per_field
    }

    print("\nGenerating report...")
    report = generate_report(analysis)

    # Write outputs
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Wrote report to {args.output}")

    with open(args.json_output, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2, default=str)
    print(f"Wrote JSON data to {args.json_output}")

    # Print summary
    print("\n" + "=" * 60)
    print("QUICK SUMMARY")
    print("=" * 60)
    print(f"Total questions:          {len(questions)}")
    print(f"Questions with edits:     {questions_with_edits}")
    print(f"Total field corrections:  {total_corrections}")
    print(f"Overall field accuracy:   {analysis['summary']['overall_accuracy_pct']:.1f}%")

    return 0


if __name__ == "__main__":
    exit(main())
