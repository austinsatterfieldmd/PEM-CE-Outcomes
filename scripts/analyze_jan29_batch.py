"""
Analyze errors from a specific batch of MM questions.
"""
import json
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

PROJECT_ROOT = Path(__file__).parent.parent
CHECKPOINT_FILE = PROJECT_ROOT / "data" / "checkpoints" / "stage2_tagged_multiple_myeloma.json"

# Core fields for focused analysis
CORE_FIELDS = [
    "topic", "disease_stage", "disease_type_1", "disease_type_2",
    "treatment_line", "treatment_1", "treatment_2", "treatment_3",
    "treatment_4", "treatment_5", "biomarker_1", "biomarker_2",
    "biomarker_3", "biomarker_4", "biomarker_5", "trial_1", "trial_2",
    "trial_3", "trial_4", "trial_5"
]


def normalize_value(v):
    """Normalize a value for comparison (case-insensitive)."""
    if v in (None, "", "null", "None", "none"):
        return None
    return str(v).strip().lower()


def extract_batch(tagged_at: str) -> str:
    """Extract batch identifier from tagged_at timestamp."""
    if not tagged_at:
        return "Unknown"
    try:
        dt = datetime.fromisoformat(tagged_at.replace("Z", "+00:00"))
        return f"Jan-{dt.day:02d}"
    except:
        return "Unknown"


def get_correction_type(llm_value, human_value):
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


def main():
    # Get batch from command line or default to Jan-28
    target_batch = sys.argv[1] if len(sys.argv) > 1 else "Jan-28"

    with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
        questions = json.load(f)

    print(f"Total questions: {len(questions)}")

    # Filter to target batch
    batch_questions = []
    for q in questions:
        batch = extract_batch(q.get("tagged_at"))
        if batch == target_batch:
            batch_questions.append(q)

    print(f"\n{target_batch} batch: {len(batch_questions)} questions")
    print("=" * 80)

    # Collect all errors first for summary
    all_errors = []
    questions_with_errors = []

    for q in batch_questions:
        qid = q.get("question_id")
        source_id = q.get("source_id")
        stem = q.get("question_stem", "")[:100] + "..."

        field_votes = q.get("field_votes", {}) or {}
        final_tags = q.get("final_tags", {}) or {}

        errors = []
        for field, fv in field_votes.items():
            if not isinstance(fv, dict):
                continue
            llm_value = normalize_value(fv.get("final_value"))
            human_value = normalize_value(final_tags.get(field))

            if llm_value != human_value:
                ct = get_correction_type(llm_value, human_value)
                errors.append({
                    "field": field,
                    "llm_value": fv.get("final_value"),
                    "human_value": final_tags.get(field),
                    "correction_type": ct,
                    "gpt_value": fv.get("gpt_value"),
                    "claude_value": fv.get("claude_value"),
                    "gemini_value": fv.get("gemini_value"),
                    "agreement": fv.get("agreement_level")
                })

        print(f"\nQ{qid} (QGD {source_id})")
        print(f"Stem: {stem}")
        print(f"Correct answer: {q.get('correct_answer', '')[:60]}...")

        if errors:
            print(f"\n  ERRORS ({len(errors)}):")
            for e in errors:
                print(f"    - {e['field']}: {e['correction_type']}")
                print(f"      LLM: {e['llm_value']} -> Human: {e['human_value']}")
                print(f"      Votes: GPT={e['gpt_value']}, Claude={e['claude_value']}, Gemini={e['gemini_value']}")
                print(f"      Agreement: {e['agreement']}")
        else:
            print("  NO ERRORS - Perfect tagging")

        print("-" * 80)

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    all_errors = []
    for q in jan29_questions:
        field_votes = q.get("field_votes", {}) or {}
        final_tags = q.get("final_tags", {}) or {}

        for field, fv in field_votes.items():
            if not isinstance(fv, dict):
                continue
            llm_value = normalize_value(fv.get("final_value"))
            human_value = normalize_value(final_tags.get(field))

            if llm_value != human_value:
                all_errors.append({
                    "qid": q.get("question_id"),
                    "field": field,
                    "llm": fv.get("final_value"),
                    "human": final_tags.get(field),
                    "type": get_correction_type(llm_value, human_value)
                })

    print(f"\nTotal errors in Jan-29 batch: {len(all_errors)}")

    if all_errors:
        print("\nBy correction type:")
        by_type = {}
        for e in all_errors:
            by_type[e["type"]] = by_type.get(e["type"], 0) + 1
        for t, c in sorted(by_type.items(), key=lambda x: -x[1]):
            print(f"  {t}: {c}")

        print("\nBy field:")
        by_field = {}
        for e in all_errors:
            by_field[e["field"]] = by_field.get(e["field"], 0) + 1
        for f, c in sorted(by_field.items(), key=lambda x: -x[1]):
            print(f"  {f}: {c}")

        print("\nDetailed error list:")
        for e in all_errors:
            print(f"  Q{e['qid']} | {e['field']}: '{e['llm']}' -> '{e['human']}' ({e['type']})")


if __name__ == "__main__":
    main()
