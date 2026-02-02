"""
One-time script: Fix batch 3 (unreviewed) questions in the checkpoint.

For unreviewed questions only:
1. Re-aggregate comorbidity_1/2/3 from model votes (gpt_tags, claude_tags, gemini_tags)
   into final_tags — these were silently dropped because vote_aggregator.py was missing
   comorbidity fields in TAG_FIELDS.

Does NOT touch human_reviewed questions (batch 1 and batch 2).

Usage:
    python scripts/fix_batch3_comorbidity.py --dry-run
    python scripts/fix_batch3_comorbidity.py
"""

import json
import argparse
import logging
from pathlib import Path
from collections import Counter

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
CHECKPOINT_PATH = PROJECT_ROOT / "data" / "checkpoints" / "stage2_tagged_multiple_myeloma.json"

COMORBIDITY_FIELDS = ["comorbidity_1", "comorbidity_2", "comorbidity_3"]


def aggregate_field(gpt_val, claude_val, gemini_val):
    """Simple 3-model majority vote for a single field."""
    # Normalize
    def norm(v):
        if v is None:
            return None
        s = str(v).strip()
        return s if s else None

    vals = [norm(gpt_val), norm(claude_val), norm(gemini_val)]
    non_none = [v for v in vals if v is not None]

    if not non_none:
        return None  # All None → None

    counts = Counter(vals)
    most_common = counts.most_common()

    # Unanimous or majority
    if most_common[0][1] >= 2:
        return most_common[0][0]

    # 3-way conflict — return None (needs manual review)
    return None


def main():
    parser = argparse.ArgumentParser(description="Fix batch 3 comorbidity fields")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    args = parser.parse_args()

    logger.info(f"Loading checkpoint: {CHECKPOINT_PATH}")
    with open(CHECKPOINT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    logger.info(f"  {len(data)} total entries")

    reviewed = [e for e in data if e.get("human_reviewed", False)]
    unreviewed = [e for e in data if not e.get("human_reviewed", False)]
    logger.info(f"  {len(reviewed)} human-reviewed (WILL NOT TOUCH)")
    logger.info(f"  {len(unreviewed)} unreviewed (batch 3 — will fix)")

    fixed_count = 0
    fields_added = 0

    for entry in data:
        # Skip human-reviewed
        if entry.get("human_reviewed", False):
            continue

        qid = entry.get("question_id")
        gpt = entry.get("gpt_tags", {})
        claude = entry.get("claude_tags", {})
        gemini = entry.get("gemini_tags", {})
        final_tags = entry.get("final_tags", {})

        entry_changed = False

        # Re-aggregate comorbidity fields from model votes
        for field in COMORBIDITY_FIELDS:
            gpt_val = gpt.get(field)
            claude_val = claude.get(field)
            gemini_val = gemini.get(field)

            aggregated = aggregate_field(gpt_val, claude_val, gemini_val)

            current = final_tags.get(field)
            if aggregated is not None and current is None:
                final_tags[field] = aggregated
                entry_changed = True
                fields_added += 1
                logger.info(f"  QID {qid}: {field} = '{aggregated}' "
                           f"(GPT={gpt_val}, Claude={claude_val}, Gemini={gemini_val})")

        if entry_changed:
            entry["final_tags"] = final_tags
            fixed_count += 1

    logger.info(f"\n{'='*50}")
    logger.info(f"SUMMARY")
    logger.info(f"{'='*50}")
    logger.info(f"Questions fixed:  {fixed_count}")
    logger.info(f"Fields added:     {fields_added}")
    logger.info(f"Reviewed (safe):  {len(reviewed)}")
    logger.info(f"{'='*50}")

    if args.dry_run:
        logger.info("DRY RUN — no changes written")
    else:
        # Backup
        backup_path = CHECKPOINT_PATH.with_suffix(".json.pre_comorbidity_fix")
        if backup_path.exists():
            backup_path.unlink()
        import shutil
        shutil.copy2(CHECKPOINT_PATH, backup_path)
        logger.info(f"Backup saved: {backup_path.name}")

        with open(CHECKPOINT_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Checkpoint saved: {CHECKPOINT_PATH.name}")


if __name__ == "__main__":
    main()
