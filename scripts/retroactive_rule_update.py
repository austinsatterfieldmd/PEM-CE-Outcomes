"""
Retroactive Rule Update Script
================================
Applies Changes 1-5 from the tagging rule refinement plan to existing
checkpoint data (stage2_tagged_*.json files).

Changes applied:
  Change 4 (Drug Class): Fully automated string replacement
    - "BCMA CAR-T" -> "CAR-T therapy"
    - "BCMA bispecific" -> "Bispecific antibody"
    - "BCMA ADC" -> "Antibody-drug conjugate (ADC)"
    - "GPRC5D bispecific" -> "Bispecific antibody"
    - "FcRH5 bispecific" -> "Bispecific antibody"
    - "BCMA-targeted bispecific" -> "Bispecific antibody"
    - "GPRC5D-targeted bispecific" -> "Bispecific antibody"
    - "FcRH5-targeted bispecific" -> "Bispecific antibody"
    Applied to ALL questions including human-reviewed (terminology rename).

  Changes 1, 2, 5 (Efficacy, Guidelines, Trials): Semi-automated
    - Generates a review CSV listing questions with non-null values in
      affected fields for non-qualifying topics
    - User reviews CSV, marks "keep" or "null" for each
    - Script reads reviewed CSV and applies nullifications

Usage:
  # Preview all changes (dry run):
  python scripts/retroactive_rule_update.py --dry-run

  # Apply Change 4 (drug class rename) automatically:
  python scripts/retroactive_rule_update.py --apply-change4

  # Generate review CSV for Changes 1, 2, 5:
  python scripts/retroactive_rule_update.py --generate-review

  # Apply reviewed CSV for Changes 1, 2, 5:
  python scripts/retroactive_rule_update.py --apply-review --review-csv path/to/reviewed.csv

  # Apply all automated changes + reviewed CSV together:
  python scripts/retroactive_rule_update.py --apply-change4 --apply-review --review-csv path/to/reviewed.csv

  # Specify a different checkpoint file:
  python scripts/retroactive_rule_update.py --checkpoint data/checkpoints/stage2_tagged_multiple_myeloma.json --apply-change4
"""

import argparse
import csv
import json
import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Change 4: Drug class string replacements
DRUG_CLASS_REPLACEMENTS = {
    "BCMA CAR-T": "CAR-T therapy",
    "BCMA bispecific": "Bispecific antibody",
    "BCMA ADC": "Antibody-drug conjugate (ADC)",
    "GPRC5D bispecific": "Bispecific antibody",
    "FcRH5 bispecific": "Bispecific antibody",
    "BCMA-targeted bispecific": "Bispecific antibody",
    "GPRC5D-targeted bispecific": "Bispecific antibody",
    "FcRH5-targeted bispecific": "Bispecific antibody",
}

# Fields affected by drug class renaming
DRUG_CLASS_FIELDS = ["drug_class_1", "drug_class_2", "drug_class_3"]

# Tag containers that hold tag dictionaries
TAG_CONTAINERS = ["final_tags", "gpt_tags", "claude_tags", "gemini_tags"]

# Topics that qualify for trial inference
TRIAL_QUALIFYING_TOPICS = {"Clinical efficacy", "Study design"}

# Topics that qualify for efficacy endpoint tagging
EFFICACY_QUALIFYING_TOPICS = {"Clinical efficacy"}

# Fields to check for each change type
EFFICACY_FIELDS = ["efficacy_endpoint_1", "efficacy_endpoint_2", "efficacy_endpoint_3",
                   "outcome_context", "clinical_benefit"]
GUIDELINE_FIELDS = ["guideline_source_1", "guideline_source_2"]
TRIAL_FIELDS = ["trial_1", "trial_2", "trial_3", "trial_4", "trial_5"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_checkpoint(path: Path) -> list:
    """Load checkpoint JSON file."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_checkpoint(data: list, path: Path) -> None:
    """Save checkpoint JSON file."""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved checkpoint: {path}")


def create_backup(path: Path) -> Path:
    """Create a timestamped backup of the checkpoint file."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = path.with_suffix(f'.pre_retroactive_update_{timestamp}.json')
    shutil.copy2(path, backup_path)
    logger.info(f"Backup created: {backup_path}")
    return backup_path


def get_topic(question: dict) -> str:
    """Get the topic from a question's final_tags."""
    final_tags = question.get("final_tags", {})
    return final_tags.get("topic", "") or ""


def has_value(val) -> bool:
    """Check if a tag value is non-null and non-empty."""
    return val is not None and val != "" and val != "null"


def is_human_edited_field(question: dict, field: str) -> bool:
    """Check if a specific field was manually edited by a human reviewer."""
    edited_fields = question.get("human_edited_fields", []) or []
    return field in edited_fields


# ---------------------------------------------------------------------------
# Change 4: Drug Class Renaming (Fully Automated)
# ---------------------------------------------------------------------------

def apply_change4_to_question(question: dict, dry_run: bool = False) -> dict:
    """Apply drug class renaming to a single question.

    Returns dict of changes made: {location: {field: (old, new)}}
    """
    changes = {}

    for container_name in TAG_CONTAINERS:
        container = question.get(container_name)
        if not container or not isinstance(container, dict):
            continue

        for field in DRUG_CLASS_FIELDS:
            old_val = container.get(field)
            if old_val and old_val in DRUG_CLASS_REPLACEMENTS:
                new_val = DRUG_CLASS_REPLACEMENTS[old_val]
                if not dry_run:
                    container[field] = new_val
                changes.setdefault(container_name, {})[field] = (old_val, new_val)

    # Also update field_votes
    field_votes = question.get("field_votes", {})
    if field_votes:
        for field in DRUG_CLASS_FIELDS:
            vote = field_votes.get(field)
            if not vote or not isinstance(vote, dict):
                continue
            for vote_key in ["final_value", "gpt_value", "claude_value", "gemini_value"]:
                old_val = vote.get(vote_key)
                if old_val and old_val in DRUG_CLASS_REPLACEMENTS:
                    new_val = DRUG_CLASS_REPLACEMENTS[old_val]
                    if not dry_run:
                        vote[vote_key] = new_val
                    changes.setdefault("field_votes." + field, {})[vote_key] = (old_val, new_val)

    # Check web_searches_used for drug class mentions (just for awareness, don't modify)

    return changes


def apply_change4(data: list, dry_run: bool = False) -> int:
    """Apply Change 4 (drug class renaming) to all questions.

    Returns count of questions modified.
    """
    modified_count = 0

    for q in data:
        changes = apply_change4_to_question(q, dry_run=dry_run)
        if changes:
            modified_count += 1
            qid = q.get("question_id", "?")
            if dry_run:
                logger.info(f"  [DRY RUN] Q{qid}: Would rename drug classes:")
                for loc, fields in changes.items():
                    for field, (old, new) in fields.items():
                        logger.info(f"    {loc}.{field}: \"{old}\" -> \"{new}\"")

    return modified_count


# ---------------------------------------------------------------------------
# Changes 1, 2, 5: Semi-Automated Review CSV Generation
# ---------------------------------------------------------------------------

def generate_review_csv(data: list, output_path: Path, include_reviewed: bool = False) -> int:
    """Generate a review CSV for Changes 1, 2, 5.

    For each question, checks if non-null values exist in efficacy_endpoint,
    guideline_source, or trial fields when the topic doesn't qualify.

    Args:
        data: List of question dicts
        output_path: Where to write the CSV
        include_reviewed: If True, include human-reviewed questions

    Returns:
        Number of rows written
    """
    rows = []

    for q in data:
        qid = q.get("question_id", "?")
        source_id = q.get("source_id", "?")
        topic = get_topic(q)
        stem = q.get("question_stem", "")
        human_reviewed = q.get("human_reviewed", False)

        if not include_reviewed and human_reviewed:
            continue

        final_tags = q.get("final_tags", {})

        # Change 1: Efficacy endpoints (only for non-Clinical efficacy topics)
        efficacy_values = {}
        if topic not in EFFICACY_QUALIFYING_TOPICS:
            for field in EFFICACY_FIELDS:
                val = final_tags.get(field)
                if has_value(val):
                    efficacy_values[field] = val

        # Change 2: Guideline sources (always flag — must be explicitly named)
        guideline_values = {}
        for field in GUIDELINE_FIELDS:
            val = final_tags.get(field)
            if has_value(val):
                guideline_values[field] = val

        # Change 5: Trial inference (only for non-qualifying topics)
        trial_values = {}
        if topic not in TRIAL_QUALIFYING_TOPICS:
            for field in TRIAL_FIELDS:
                val = final_tags.get(field)
                if has_value(val):
                    trial_values[field] = val

        # Only add row if there's something to review
        if efficacy_values or guideline_values or trial_values:
            row = {
                "question_id": qid,
                "source_id": source_id,
                "topic": topic,
                "human_reviewed": human_reviewed,
                "question_stem": stem,
                # Efficacy fields
                "efficacy_endpoint_1": final_tags.get("efficacy_endpoint_1", ""),
                "efficacy_endpoint_2": final_tags.get("efficacy_endpoint_2", ""),
                "efficacy_endpoint_3": final_tags.get("efficacy_endpoint_3", ""),
                "outcome_context": final_tags.get("outcome_context", ""),
                "clinical_benefit": final_tags.get("clinical_benefit", ""),
                "action_efficacy": "null" if efficacy_values else "",
                # Guideline fields
                "guideline_source_1": final_tags.get("guideline_source_1", ""),
                "guideline_source_2": final_tags.get("guideline_source_2", ""),
                "action_guideline": "null" if guideline_values else "",
                # Trial fields
                "trial_1": final_tags.get("trial_1", ""),
                "trial_2": final_tags.get("trial_2", ""),
                "trial_3": final_tags.get("trial_3", ""),
                "action_trial": "null" if trial_values else "",
            }
            rows.append(row)

    if rows:
        fieldnames = [
            "question_id", "source_id", "topic", "human_reviewed", "question_stem",
            "efficacy_endpoint_1", "efficacy_endpoint_2", "efficacy_endpoint_3",
            "outcome_context", "clinical_benefit", "action_efficacy",
            "guideline_source_1", "guideline_source_2", "action_guideline",
            "trial_1", "trial_2", "trial_3", "action_trial",
        ]
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        logger.info(f"Review CSV written: {output_path} ({len(rows)} rows)")
    else:
        logger.info("No questions flagged for review — all values already correct.")

    return len(rows)


# ---------------------------------------------------------------------------
# Changes 1, 2, 5: Apply Reviewed CSV
# ---------------------------------------------------------------------------

def apply_review_csv(data: list, csv_path: Path, dry_run: bool = False) -> int:
    """Apply nullifications from a reviewed CSV to the checkpoint data.

    The CSV should have columns:
      - question_id
      - action_efficacy: "null" to clear efficacy fields, "keep" to preserve
      - action_guideline: "null" to clear guideline fields, "keep" to preserve
      - action_trial: "null" to clear trial fields, "keep" to preserve

    Returns count of questions modified.
    """
    # Build lookup by question_id
    q_lookup = {q["question_id"]: q for q in data}

    # Read reviewed CSV
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        review_rows = list(reader)

    modified_count = 0

    for row in review_rows:
        qid = int(row["question_id"])
        q = q_lookup.get(qid)
        if not q:
            logger.warning(f"  Q{qid} not found in checkpoint, skipping")
            continue

        changes_made = False
        final_tags = q.get("final_tags", {})

        # Apply efficacy nullification
        action_efficacy = (row.get("action_efficacy") or "").strip().lower()
        if action_efficacy == "null":
            for field in EFFICACY_FIELDS:
                if has_value(final_tags.get(field)):
                    if is_human_edited_field(q, field):
                        logger.info(f"  Q{qid}: Skipping {field} (human-edited)")
                        continue
                    old_val = final_tags[field]
                    if not dry_run:
                        final_tags[field] = None
                    logger.info(f"  {'[DRY RUN] ' if dry_run else ''}Q{qid}: {field}: \"{old_val}\" -> null (efficacy rule)")
                    changes_made = True

        # Apply guideline nullification
        action_guideline = (row.get("action_guideline") or "").strip().lower()
        if action_guideline == "null":
            for field in GUIDELINE_FIELDS:
                if has_value(final_tags.get(field)):
                    if is_human_edited_field(q, field):
                        logger.info(f"  Q{qid}: Skipping {field} (human-edited)")
                        continue
                    old_val = final_tags[field]
                    if not dry_run:
                        final_tags[field] = None
                    logger.info(f"  {'[DRY RUN] ' if dry_run else ''}Q{qid}: {field}: \"{old_val}\" -> null (guideline rule)")
                    changes_made = True

        # Apply trial nullification
        action_trial = (row.get("action_trial") or "").strip().lower()
        if action_trial == "null":
            for field in TRIAL_FIELDS:
                if has_value(final_tags.get(field)):
                    if is_human_edited_field(q, field):
                        logger.info(f"  Q{qid}: Skipping {field} (human-edited)")
                        continue
                    old_val = final_tags[field]
                    if not dry_run:
                        final_tags[field] = None
                    logger.info(f"  {'[DRY RUN] ' if dry_run else ''}Q{qid}: {field}: \"{old_val}\" -> null (trial rule)")
                    changes_made = True

        if changes_made:
            modified_count += 1
            # Append retroactive update to review_reason
            if not dry_run:
                review_reason = q.get("review_reason", "") or ""
                if "retroactive_rule_v2" not in review_reason:
                    sep = "|" if review_reason else ""
                    q["review_reason"] = review_reason + sep + "retroactive_rule_v2"

    return modified_count


# ---------------------------------------------------------------------------
# Summary / Dry Run
# ---------------------------------------------------------------------------

def print_summary(data: list) -> None:
    """Print a summary of what would be changed across all questions."""
    total_questions = len(data)
    human_reviewed = sum(1 for q in data if q.get("human_reviewed", False))

    # Change 4 stats
    c4_count = 0
    c4_values = {}
    for q in data:
        for container_name in TAG_CONTAINERS:
            container = q.get(container_name, {}) or {}
            for field in DRUG_CLASS_FIELDS:
                val = container.get(field)
                if val and val in DRUG_CLASS_REPLACEMENTS:
                    c4_count += 1
                    c4_values[val] = c4_values.get(val, 0) + 1

    # Changes 1, 2, 5 stats
    c1_count = 0  # efficacy
    c2_count = 0  # guideline
    c5_count = 0  # trial
    for q in data:
        topic = get_topic(q)
        final_tags = q.get("final_tags", {})

        if topic not in EFFICACY_QUALIFYING_TOPICS:
            for field in EFFICACY_FIELDS:
                if has_value(final_tags.get(field)):
                    c1_count += 1

        for field in GUIDELINE_FIELDS:
            if has_value(final_tags.get(field)):
                c2_count += 1

        if topic not in TRIAL_QUALIFYING_TOPICS:
            for field in TRIAL_FIELDS:
                if has_value(final_tags.get(field)):
                    c5_count += 1

    logger.info("=" * 60)
    logger.info("RETROACTIVE RULE UPDATE SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total questions: {total_questions}")
    logger.info(f"Human-reviewed: {human_reviewed}")
    logger.info("")
    logger.info(f"Change 4 (Drug Class Rename):")
    logger.info(f"  Total field values to rename: {c4_count}")
    for val, count in sorted(c4_values.items(), key=lambda x: -x[1]):
        logger.info(f"    \"{val}\" -> \"{DRUG_CLASS_REPLACEMENTS[val]}\": {count} occurrences")
    logger.info("")
    logger.info(f"Change 1 (Efficacy Endpoints):")
    logger.info(f"  Fields with values in non-qualifying topics: {c1_count}")
    logger.info(f"  (These need manual review via --generate-review)")
    logger.info("")
    logger.info(f"Change 2 (Guideline Sources):")
    logger.info(f"  Fields with values needing review: {c2_count}")
    logger.info(f"  (These need manual review via --generate-review)")
    logger.info("")
    logger.info(f"Change 5 (Trial Inference):")
    logger.info(f"  Fields with values in non-qualifying topics: {c5_count}")
    logger.info(f"  (These need manual review via --generate-review)")
    logger.info("=" * 60)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Apply retroactive rule updates to tagged checkpoint data."
    )
    parser.add_argument(
        "--checkpoint",
        type=str,
        default=str(PROJECT_ROOT / "data" / "checkpoints" / "stage2_tagged_multiple_myeloma.json"),
        help="Path to checkpoint JSON file"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing to disk"
    )
    parser.add_argument(
        "--apply-change4",
        action="store_true",
        help="Apply Change 4 (drug class renaming) automatically"
    )
    parser.add_argument(
        "--generate-review",
        action="store_true",
        help="Generate review CSV for Changes 1, 2, 5"
    )
    parser.add_argument(
        "--apply-review",
        action="store_true",
        help="Apply nullifications from a reviewed CSV"
    )
    parser.add_argument(
        "--review-csv",
        type=str,
        help="Path to the reviewed CSV file (required with --apply-review)"
    )
    parser.add_argument(
        "--include-reviewed",
        action="store_true",
        help="Include human-reviewed questions in the review CSV (default: skip)"
    )
    parser.add_argument(
        "--review-output",
        type=str,
        default=None,
        help="Output path for review CSV (default: data/checkpoints/retroactive_review.csv)"
    )

    args = parser.parse_args()

    checkpoint_path = Path(args.checkpoint)
    if not checkpoint_path.exists():
        logger.error(f"Checkpoint file not found: {checkpoint_path}")
        sys.exit(1)

    # Load data
    logger.info(f"Loading checkpoint: {checkpoint_path}")
    data = load_checkpoint(checkpoint_path)
    logger.info(f"Loaded {len(data)} questions")

    # If no action specified, show summary
    if not any([args.apply_change4, args.generate_review, args.apply_review]):
        print_summary(data)
        logger.info("\nTo apply changes, use --apply-change4, --generate-review, or --apply-review")
        return

    modified = False

    # Apply Change 4
    if args.apply_change4:
        logger.info("\n--- Change 4: Drug Class Renaming ---")
        count = apply_change4(data, dry_run=args.dry_run)
        logger.info(f"Change 4: {count} questions {'would be' if args.dry_run else ''} modified")
        if count > 0 and not args.dry_run:
            modified = True

    # Generate review CSV
    if args.generate_review:
        review_output = Path(args.review_output) if args.review_output else (
            checkpoint_path.parent / "retroactive_review.csv"
        )
        logger.info(f"\n--- Generating Review CSV ---")
        row_count = generate_review_csv(
            data, review_output,
            include_reviewed=args.include_reviewed
        )
        if row_count > 0:
            logger.info(f"Review CSV: {review_output}")
            logger.info("Edit the action_efficacy, action_guideline, action_trial columns:")
            logger.info("  'null'  = clear the value (was inferred, not explicit)")
            logger.info("  'keep'  = preserve the value (was explicitly mentioned)")
            logger.info("  ''      = no action needed (already correct)")
            logger.info(f"\nThen run: python scripts/retroactive_rule_update.py --apply-review --review-csv \"{review_output}\"")

    # Apply reviewed CSV
    if args.apply_review:
        if not args.review_csv:
            logger.error("--review-csv is required with --apply-review")
            sys.exit(1)

        csv_path = Path(args.review_csv)
        if not csv_path.exists():
            logger.error(f"Review CSV not found: {csv_path}")
            sys.exit(1)

        logger.info(f"\n--- Applying Reviewed CSV: {csv_path} ---")
        count = apply_review_csv(data, csv_path, dry_run=args.dry_run)
        logger.info(f"Changes 1/2/5: {count} questions {'would be' if args.dry_run else ''} modified")
        if count > 0 and not args.dry_run:
            modified = True

    # Save if changes were made
    if modified:
        create_backup(checkpoint_path)
        save_checkpoint(data, checkpoint_path)
        logger.info("\nDone! Changes saved to checkpoint.")
    elif args.dry_run:
        logger.info("\n[DRY RUN] No changes written to disk.")
    else:
        logger.info("\nNo changes needed.")


if __name__ == "__main__":
    main()
