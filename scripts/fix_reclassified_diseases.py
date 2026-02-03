"""
Fix disease_state for questions that were incorrectly reclassified by Stage 1.

Based on manual review:
- Q7413: Heme malignancies (model correct - VOD/SOS is transplant-general)
- Q2250: ALL (model wrong - MRD question is from ALL activity)
- Q5959: CLL (model wrong - BTKi question from CLL/MCL activity, primary is CLL)
- Q6516: ALL (model wrong - ICANS question from ALL CAR-T activity)
- Q1579: FL (model wrong - CRS question from FL bispecific activity)
- Q7000: FL (model wrong - question stem mentions relapsed FL)

Updates both:
1. SQLite database (tags table)
2. Checkpoint JSON file
"""

import json
import sqlite3
from pathlib import Path

# Corrections based on manual review
DISEASE_CORRECTIONS = {
    "7413": "Heme malignancies",  # Model was correct
    "2250": "ALL",                # Model said MM, but activity is ALL
    "5959": "CLL",                # Model said Heme malignancies, but activity is CLL/MCL
    "6516": "ALL",                # Model said Heme malignancies, but activity is ALL
    "1579": "FL",                 # Model said Heme malignancies, but activity is FL
    "7000": "FL",                 # Model said Heme malignancies, question mentions FL
}


def fix_database(db_path: Path) -> dict:
    """Fix disease_state in the SQLite database."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    results = {"updated": [], "not_found": []}

    for source_id, correct_disease in DISEASE_CORRECTIONS.items():
        # Find question by source_id pattern
        cursor.execute(
            "SELECT id, source_id FROM questions WHERE source_id LIKE ?",
            (f"%{source_id}%",)
        )
        row = cursor.fetchone()

        if row:
            question_id = row["id"]
            full_source_id = row["source_id"]

            # Update tags table (both legacy disease_state AND disease_state_1)
            cursor.execute(
                "UPDATE tags SET disease_state = ?, disease_state_1 = ? WHERE question_id = ?",
                (correct_disease, correct_disease, question_id)
            )

            results["updated"].append({
                "source_id": full_source_id,
                "question_id": question_id,
                "disease_state": correct_disease
            })
        else:
            results["not_found"].append(source_id)

    conn.commit()
    conn.close()

    return results


def fix_checkpoint(checkpoint_path: Path) -> dict:
    """Fix disease_state in the checkpoint JSON file."""

    with open(checkpoint_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    results = {"updated": [], "not_found": []}

    # Handle nested {"results": [...]} format
    if isinstance(data, dict) and 'results' in data:
        questions = data['results']
    elif isinstance(data, list):
        questions = data
    else:
        questions = data.get("questions", [])

    for source_id, correct_disease in DISEASE_CORRECTIONS.items():
        found = False
        for question in questions:
            q_source_id = question.get("source_id", "")
            if source_id in q_source_id:
                # Update disease_state at question level
                question["disease_state"] = correct_disease

                # Update final_tags if present
                if "final_tags" in question:
                    question["final_tags"]["disease_state"] = correct_disease

                # Update field_votes if present
                if "field_votes" in question and "disease_state" in question["field_votes"]:
                    question["field_votes"]["disease_state"]["final_value"] = correct_disease

                results["updated"].append({
                    "source_id": q_source_id,
                    "disease_state": correct_disease
                })
                found = True
                break

        if not found:
            results["not_found"].append(source_id)

    # Write updated checkpoint
    with open(checkpoint_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    return results


def main():
    base_path = Path(__file__).parent.parent

    print("Fixing disease_state for reclassified questions")
    print("=" * 60)

    # Fix database
    db_path = base_path / "dashboard" / "data" / "questions.db"
    print(f"\nFixing database: {db_path}")
    db_results = fix_database(db_path)
    print(f"  Updated: {len(db_results['updated'])} questions")
    for update in db_results['updated']:
        sid = str(update['source_id'])
        print(f"    {sid[:30]}... -> {update['disease_state']}")
    if db_results['not_found']:
        print(f"  Not found: {db_results['not_found']}")

    # Fix checkpoint files
    checkpoint_dir = base_path / "data" / "checkpoints"
    heme_checkpoints = list(checkpoint_dir.glob("heme_tagged_*.json"))

    for checkpoint_path in heme_checkpoints:
        print(f"\nFixing checkpoint: {checkpoint_path.name}")
        cp_results = fix_checkpoint(checkpoint_path)
        print(f"  Updated: {len(cp_results['updated'])} questions")
        for update in cp_results['updated']:
            sid = str(update['source_id'])
            print(f"    {sid[:30]}... -> {update['disease_state']}")
        if cp_results['not_found']:
            print(f"  Not found: {cp_results['not_found']}")

    print("\n" + "=" * 60)
    print("Done! Disease states corrected.")


if __name__ == "__main__":
    main()
