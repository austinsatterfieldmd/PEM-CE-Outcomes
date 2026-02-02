"""
One-time script: Restore 50 human-reviewed entries from .bak into checkpoint and DB.

Problem:
  - Checkpoint JSON has 100 entries, 0 human_reviewed (WinError prevented saves)
  - .bak file has 50 entries, ALL human_reviewed with corrected final_tags
  - DB has 42/50 marked edited (incomplete fuzzy recovery)

This script:
  1. Merges .bak reviewed data into the current checkpoint by question_id
  2. Applies all 50 corrected final_tags to the DB by source_question_id
  3. Sets edited_by_user=True, needs_review=False for all 50 in DB

Note: Excluded questions (from config/excluded_questions.yaml) are skipped.

Run once, then verify.

Usage:
    python scripts/restore_reviewed_data.py
    python scripts/restore_reviewed_data.py --dry-run   # Preview without writing
"""

import json
import sqlite3
import sys
import logging
import yaml
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

CHECKPOINT_FILE = PROJECT_ROOT / "data" / "checkpoints" / "stage2_tagged_multiple_myeloma.json"
BAK_FILE = CHECKPOINT_FILE.with_suffix(".json.bak")
DB_PATH = PROJECT_ROOT / "dashboard" / "data" / "questions.db"
EXCLUSION_LIST_PATH = PROJECT_ROOT / "config" / "excluded_questions.yaml"


def load_exclusion_list() -> set:
    """
    Load the set of excluded source_ids from config/excluded_questions.yaml.

    Returns:
        Set of source_id strings that should be excluded from restore.
    """
    if not EXCLUSION_LIST_PATH.exists():
        logger.debug("No exclusion list found, no questions will be excluded")
        return set()

    try:
        with open(EXCLUSION_LIST_PATH, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        excluded = set()
        for item in data.get('excluded_questions', []):
            source_id = item.get('source_id')
            if source_id:
                excluded.add(str(source_id))

        if excluded:
            logger.info(f"Loaded exclusion list: {len(excluded)} questions will be skipped")
        return excluded

    except Exception as e:
        logger.warning(f"Failed to load exclusion list: {e}")
        return set()


def load_json(path: Path) -> list:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    dry_run = "--dry-run" in sys.argv

    if dry_run:
        logger.info("DRY RUN — no files will be modified")

    # Load exclusion list
    excluded_source_ids = load_exclusion_list()

    # ------------------------------------------------------------------
    # Step 1: Load current checkpoint and .bak
    # ------------------------------------------------------------------
    logger.info(f"Loading checkpoint: {CHECKPOINT_FILE}")
    current = load_json(CHECKPOINT_FILE)
    logger.info(f"  {len(current)} entries, {sum(1 for e in current if e.get('human_reviewed'))} reviewed")

    logger.info(f"Loading .bak: {BAK_FILE}")
    bak = load_json(BAK_FILE)
    bak_reviewed = sum(1 for e in bak if e.get("human_reviewed"))
    logger.info(f"  {len(bak)} entries, {bak_reviewed} reviewed")

    if bak_reviewed == 0:
        logger.error("No reviewed entries in .bak file — nothing to restore")
        return

    # Build lookup: question_id -> bak entry
    bak_lookup = {e["question_id"]: e for e in bak if e.get("human_reviewed")}
    logger.info(f"  {len(bak_lookup)} unique reviewed entries in .bak")

    # ------------------------------------------------------------------
    # Step 2: Merge .bak data into current checkpoint
    # ------------------------------------------------------------------
    merged_count = 0
    for entry in current:
        qid = entry["question_id"]
        if qid in bak_lookup:
            bak_entry = bak_lookup[qid]

            # Copy reviewed metadata
            entry["human_reviewed"] = True
            entry["human_reviewed_at"] = bak_entry.get("human_reviewed_at")
            entry["human_edited_fields"] = bak_entry.get("human_edited_fields", [])
            entry["needs_review"] = False

            # Copy corrected final_tags (the golden data)
            if "final_tags" in bak_entry:
                entry["final_tags"] = bak_entry["final_tags"]

            # Copy review_reason if updated
            if bak_entry.get("review_reason"):
                entry["review_reason"] = bak_entry["review_reason"]

            merged_count += 1

    logger.info(f"Merged {merged_count}/{len(bak_lookup)} reviewed entries into checkpoint")

    # Verify no mismatches
    if merged_count < len(bak_lookup):
        missing = set(bak_lookup.keys()) - {e["question_id"] for e in current}
        logger.warning(f"  {len(missing)} .bak entries not found in current checkpoint: {sorted(missing)}")

    # Save merged checkpoint
    if not dry_run:
        # Backup current before overwriting
        backup_path = CHECKPOINT_FILE.with_suffix(".json.pre_restore_bak")
        if backup_path.exists():
            backup_path.unlink()
        CHECKPOINT_FILE.rename(backup_path)
        logger.info(f"  Backed up current checkpoint to {backup_path.name}")

        with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2, ensure_ascii=False)
        logger.info(f"  Saved merged checkpoint ({len(current)} entries, {merged_count} reviewed)")

    # ------------------------------------------------------------------
    # Step 3: Apply all 50 reviews to DB
    # ------------------------------------------------------------------
    logger.info(f"\nApplying {len(bak_lookup)} reviews to database: {DB_PATH}")

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Build mapping: source_question_id -> DB id
    cursor.execute("SELECT id, source_question_id, source_id FROM questions")
    db_questions = {row["source_question_id"]: {"db_id": row["id"], "source_id": row["source_id"]}
                    for row in cursor.fetchall()}
    logger.info(f"  {len(db_questions)} questions in DB")

    # All valid tag columns in the DB tags table
    valid_tag_columns = {
        'topic', 'disease_state', 'disease_stage',
        'disease_type_1', 'disease_type_2',
        'treatment_line',
        'treatment_1', 'treatment_2', 'treatment_3', 'treatment_4', 'treatment_5',
        'biomarker_1', 'biomarker_2', 'biomarker_3', 'biomarker_4', 'biomarker_5',
        'trial_1', 'trial_2', 'trial_3', 'trial_4', 'trial_5',
        'treatment_eligibility', 'age_group', 'organ_dysfunction', 'fitness_status',
        'disease_specific_factor',
        'drug_class_1', 'drug_class_2', 'drug_class_3',
        'drug_target_1', 'drug_target_2', 'drug_target_3',
        'prior_therapy_1', 'prior_therapy_2', 'prior_therapy_3',
        'resistance_mechanism',
        'metastatic_site_1', 'metastatic_site_2', 'metastatic_site_3',
        'symptom_1', 'symptom_2', 'symptom_3',
        'performance_status',
        'toxicity_type_1', 'toxicity_type_2', 'toxicity_type_3',
        'toxicity_type_4', 'toxicity_type_5',
        'toxicity_organ', 'toxicity_grade',
        'efficacy_endpoint_1', 'efficacy_endpoint_2', 'efficacy_endpoint_3',
        'outcome_context', 'clinical_benefit',
        'guideline_source_1', 'guideline_source_2', 'evidence_type',
        'cme_outcome_level', 'data_response_type', 'stem_type', 'lead_in_type',
        'answer_format', 'answer_length_pattern', 'distractor_homogeneity',
        'flaw_absolute_terms', 'flaw_grammatical_cue', 'flaw_implausible_distractor',
        'flaw_clang_association', 'flaw_convergence_vulnerability', 'flaw_double_negative',
        'answer_option_count', 'correct_answer_position',
    }

    applied = 0
    not_found = 0
    skipped_excluded = 0
    for qid, bak_entry in bak_lookup.items():
        # Check exclusion list by source_id
        source_id = str(bak_entry.get('source_id', ''))
        if source_id in excluded_source_ids:
            logger.debug(f"  Skipping excluded question_id={qid} (source_id={source_id})")
            skipped_excluded += 1
            continue

        if qid not in db_questions:
            logger.warning(f"  question_id={qid} (source_id={bak_entry.get('source_id')}) not in DB")
            not_found += 1
            continue

        db_id = db_questions[qid]["db_id"]
        final_tags = bak_entry.get("final_tags", {})
        edited_fields = bak_entry.get("human_edited_fields", [])

        # Build SET clause for tag fields from final_tags
        updates = []
        values = []

        for field, value in final_tags.items():
            if field in valid_tag_columns and value is not None:
                updates.append(f"{field} = ?")
                values.append(value)

        # Mark as reviewed
        updates.append("needs_review = ?")
        values.append(0)
        updates.append("overall_confidence = ?")
        values.append(1.0)
        updates.append("edited_by_user = ?")
        values.append(1)
        updates.append("edited_at = ?")
        values.append(bak_entry.get("human_reviewed_at", datetime.now().isoformat()))
        updates.append("edited_fields = ?")
        values.append(json.dumps(edited_fields))
        updates.append("updated_at = CURRENT_TIMESTAMP")

        if updates:
            values.append(db_id)
            sql = f"UPDATE tags SET {', '.join(updates)} WHERE question_id = ?"
            if not dry_run:
                cursor.execute(sql, values)
            applied += 1

    if not dry_run:
        conn.commit()

    conn.close()

    logger.info(f"  Applied: {applied}")
    logger.info(f"  Skipped (excluded): {skipped_excluded}")
    logger.info(f"  Not found in DB: {not_found}")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print(f"\n{'='*50}")
    print("RESTORATION SUMMARY" + (" (DRY RUN)" if dry_run else ""))
    print(f"{'='*50}")
    print(f"Checkpoint: {merged_count}/{len(bak_lookup)} reviewed entries merged")
    print(f"Database:   {applied}/{len(bak_lookup)} reviews applied")
    if skipped_excluded:
        print(f"  Skipped (excluded): {skipped_excluded}")
    if not_found:
        print(f"  WARNING: {not_found} entries not found in DB")
    if not dry_run:
        print("\nVerify with:")
        print("  python -c \"import sqlite3; c=sqlite3.connect('dashboard/data/questions.db'); "
              "print('edited_by_user:', c.execute('SELECT COUNT(*) FROM tags WHERE edited_by_user=1').fetchone()[0]); "
              "print('needs_review:', c.execute('SELECT COUNT(*) FROM tags WHERE needs_review=1').fetchone()[0])\"")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
