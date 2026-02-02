"""
Analyze errors from a specific batch of MM questions.
Usage: python scripts/analyze_batch.py [batch_name]
Examples:
  python scripts/analyze_batch.py Jan-28
  python scripts/analyze_batch.py Jan-29
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

    print(f"Total questions in checkpoint: {len(questions)}")

    # Filter to target batch
    batch_questions = []
    for q in questions:
        batch = extract_batch(q.get("tagged_at"))
        if batch == target_batch:
            batch_questions.append(q)

    print(f"\n{'='*80}")
    print(f"{target_batch} BATCH ANALYSIS")
    print(f"{'='*80}")
    print(f"Questions in batch: {len(batch_questions)}")

    # Collect all errors
    all_errors = []
    questions_with_errors = 0

    for q in batch_questions:
        qid = q.get("question_id")
        source_id = q.get("source_id")
        field_votes = q.get("field_votes", {}) or {}
        final_tags = q.get("final_tags", {}) or {}

        q_errors = []
        for field, fv in field_votes.items():
            if not isinstance(fv, dict):
                continue
            llm_value = normalize_value(fv.get("final_value"))
            human_value = normalize_value(final_tags.get(field))

            if llm_value != human_value:
                ct = get_correction_type(llm_value, human_value)
                q_errors.append({
                    "qid": qid,
                    "source_id": source_id,
                    "field": field,
                    "is_core": field in CORE_FIELDS,
                    "llm_value": fv.get("final_value"),
                    "human_value": final_tags.get(field),
                    "correction_type": ct,
                    "gpt_value": fv.get("gpt_value"),
                    "claude_value": fv.get("claude_value"),
                    "gemini_value": fv.get("gemini_value"),
                    "agreement": fv.get("agreement_level"),
                    "stem": q.get("question_stem", "")[:80],
                    "correct_answer": q.get("correct_answer", "")[:60]
                })

        if q_errors:
            questions_with_errors += 1
            all_errors.extend(q_errors)

    total_fields = len(batch_questions) * len(CORE_FIELDS) if batch_questions else 0
    print(f"Questions with errors: {questions_with_errors} ({questions_with_errors/len(batch_questions)*100:.1f}%)")
    print(f"Total errors: {len(all_errors)}")

    # Separate core vs non-core errors
    core_errors = [e for e in all_errors if e["is_core"]]
    noncore_errors = [e for e in all_errors if not e["is_core"]]

    print(f"\n  Core field errors: {len(core_errors)}")
    print(f"  Non-core field errors: {len(noncore_errors)}")

    # Summary by correction type
    print(f"\n{'='*80}")
    print("ERRORS BY CORRECTION TYPE")
    print(f"{'='*80}")

    by_type = defaultdict(list)
    for e in all_errors:
        by_type[e["correction_type"]].append(e)

    for ct in ["wrong_to_fixed", "null_to_added", "value_to_cleared"]:
        errors = by_type.get(ct, [])
        core = [e for e in errors if e["is_core"]]
        print(f"\n{ct}: {len(errors)} total ({len(core)} core)")

    # Summary by field (sorted by count)
    print(f"\n{'='*80}")
    print("ERRORS BY FIELD (sorted by count)")
    print(f"{'='*80}")

    by_field = defaultdict(list)
    for e in all_errors:
        by_field[e["field"]].append(e)

    for field, errors in sorted(by_field.items(), key=lambda x: -len(x[1])):
        is_core = "CORE" if field in CORE_FIELDS else ""
        ct_breakdown = defaultdict(int)
        for e in errors:
            ct_breakdown[e["correction_type"]] += 1
        ct_str = ", ".join(f"{ct}:{c}" for ct, c in ct_breakdown.items())
        print(f"  {field}: {len(errors)} {is_core} [{ct_str}]")

    # Focus on CORE FIELD "wrong_to_fixed" errors (the real mistakes)
    core_wrong = [e for e in all_errors if e["is_core"] and e["correction_type"] == "wrong_to_fixed"]

    print(f"\n{'='*80}")
    print(f"CORE FIELD 'WRONG' ERRORS (LLM had wrong value): {len(core_wrong)}")
    print(f"{'='*80}")

    if core_wrong:
        # Group by field
        by_field_wrong = defaultdict(list)
        for e in core_wrong:
            by_field_wrong[e["field"]].append(e)

        for field, errors in sorted(by_field_wrong.items(), key=lambda x: -len(x[1])):
            print(f"\n### {field} ({len(errors)} errors)")
            for e in errors:
                print(f"  Q{e['qid']} (QGD {e['source_id']})")
                print(f"    LLM: '{e['llm_value']}' -> Human: '{e['human_value']}'")
                print(f"    Votes: GPT={e['gpt_value']}, Claude={e['claude_value']}, Gemini={e['gemini_value']}")
                print(f"    Stem: {e['stem']}...")
    else:
        print("  No core field 'wrong' errors!")

    # Also show Core Field null_to_added (LLM missed something)
    core_null = [e for e in all_errors if e["is_core"] and e["correction_type"] == "null_to_added"]

    print(f"\n{'='*80}")
    print(f"CORE FIELD 'NULL->ADDED' ERRORS (LLM missed value): {len(core_null)}")
    print(f"{'='*80}")

    if core_null:
        # Group by field
        by_field_null = defaultdict(list)
        for e in core_null:
            by_field_null[e["field"]].append(e)

        for field, errors in sorted(by_field_null.items(), key=lambda x: -len(x[1])):
            print(f"\n### {field} ({len(errors)} errors)")
            # Show top patterns
            patterns = defaultdict(int)
            for e in errors:
                patterns[e["human_value"]] += 1
            print(f"  Top values added:")
            for val, count in sorted(patterns.items(), key=lambda x: -x[1])[:5]:
                print(f"    [{count}x] {val}")
            # Show examples
            print(f"  Examples:")
            for e in errors[:3]:
                print(f"    Q{e['qid']}: Human added '{e['human_value']}'")
                print(f"      Stem: {e['stem']}...")

    # Core Field value_to_cleared (LLM over-tagged)
    core_cleared = [e for e in all_errors if e["is_core"] and e["correction_type"] == "value_to_cleared"]

    print(f"\n{'='*80}")
    print(f"CORE FIELD 'VALUE->CLEARED' ERRORS (LLM over-tagged): {len(core_cleared)}")
    print(f"{'='*80}")

    if core_cleared:
        by_field_cleared = defaultdict(list)
        for e in core_cleared:
            by_field_cleared[e["field"]].append(e)

        for field, errors in sorted(by_field_cleared.items(), key=lambda x: -len(x[1])):
            print(f"\n### {field} ({len(errors)} errors)")
            patterns = defaultdict(int)
            for e in errors:
                patterns[e["llm_value"]] += 1
            print(f"  Values incorrectly tagged (should be null):")
            for val, count in sorted(patterns.items(), key=lambda x: -x[1])[:5]:
                print(f"    [{count}x] {val}")


if __name__ == "__main__":
    main()
