"""
Script to retroactively fix drug_class values for immunotherapies.

Changes:
- "Anti-CD38 mAb" -> "Monoclonal antibody" (drug_target should be "CD38")
- "Anti-SLAMF7" -> "Monoclonal antibody" (drug_target should be "SLAMF7")
- "BCMA bispecific" -> "Bispecific antibody" (drug_target should be "BCMA")
- "GPRC5D bispecific" -> "Bispecific antibody" (drug_target should be "GPRC5D")
- "BCMA CAR-T" -> "CAR-T therapy" (drug_target should be "BCMA")

Updates both:
1. SQLite database (tags table)
2. Checkpoint JSON files
"""

import json
import sqlite3
from pathlib import Path

# Mapping of old values to new standardized values
DRUG_CLASS_MAPPING = {
    "Anti-CD38 mAb": "Monoclonal antibody",
    "Anti-SLAMF7": "Monoclonal antibody",
    "BCMA bispecific": "Bispecific antibody",
    "GPRC5D bispecific": "Bispecific antibody",
    "BCMA CAR-T": "CAR-T therapy",
}


def fix_database(db_path: Path) -> dict:
    """Fix drug_class values in the SQLite database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    results = {
        "database_updates": [],
        "fields_checked": ["drug_class_1", "drug_class_2", "drug_class_3"]
    }

    # Find and fix all mapped values
    for field in ["drug_class_1", "drug_class_2", "drug_class_3"]:
        for old_value, new_value in DRUG_CLASS_MAPPING.items():
            cursor.execute(
                f"SELECT question_id, {field} FROM tags WHERE {field} = ?",
                (old_value,)
            )
            rows = cursor.fetchall()

            for question_id, current_value in rows:
                cursor.execute(
                    f"UPDATE tags SET {field} = ? WHERE question_id = ?",
                    (new_value, question_id)
                )
                results["database_updates"].append({
                    "question_id": question_id,
                    "field": field,
                    "old_value": current_value,
                    "new_value": new_value
                })

    conn.commit()
    conn.close()

    return results


def fix_checkpoint(checkpoint_path: Path) -> dict:
    """Fix drug_class values in the checkpoint JSON file."""

    with open(checkpoint_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    results = {
        "checkpoint_updates": [],
        "questions_modified": 0
    }

    # Checkpoint can be either a list of questions or a dict with "questions" key
    if isinstance(data, list):
        questions = data
    else:
        questions = data.get("questions", [])

    # Iterate through all questions in checkpoint
    for question in questions:
        modified = False
        question_id = question.get("source_question_id") or question.get("question_id")

        # Check and fix aggregated tags
        for tags_field in ["aggregated_tags", "final_tags"]:
            tags = question.get(tags_field, {})
            if tags:
                for field in ["drug_class_1", "drug_class_2", "drug_class_3"]:
                    current_value = tags.get(field)
                    if current_value in DRUG_CLASS_MAPPING:
                        new_value = DRUG_CLASS_MAPPING[current_value]
                        tags[field] = new_value
                        modified = True
                        results["checkpoint_updates"].append({
                            "question_id": question_id,
                            "section": tags_field,
                            "field": field,
                            "old_value": current_value,
                            "new_value": new_value
                        })

        # Check and fix per-model tags (gpt_tags, claude_tags, gemini_tags)
        for model in ["gpt_tags", "claude_tags", "gemini_tags"]:
            tags = question.get(model, {})
            if tags:
                for field in ["drug_class_1", "drug_class_2", "drug_class_3"]:
                    current_value = tags.get(field)
                    if current_value in DRUG_CLASS_MAPPING:
                        new_value = DRUG_CLASS_MAPPING[current_value]
                        tags[field] = new_value
                        modified = True
                        results["checkpoint_updates"].append({
                            "question_id": question_id,
                            "section": model,
                            "field": field,
                            "old_value": current_value,
                            "new_value": new_value
                        })

        # Check and fix field_votes (contains per-field voting details)
        field_votes = question.get("field_votes", {})
        if field_votes:
            for field in ["drug_class_1", "drug_class_2", "drug_class_3"]:
                vote_data = field_votes.get(field, {})
                if vote_data:
                    # Fix final_value
                    current_value = vote_data.get("final_value")
                    if current_value in DRUG_CLASS_MAPPING:
                        new_value = DRUG_CLASS_MAPPING[current_value]
                        vote_data["final_value"] = new_value
                        modified = True
                        results["checkpoint_updates"].append({
                            "question_id": question_id,
                            "section": "field_votes",
                            "field": f"{field}.final_value",
                            "old_value": current_value,
                            "new_value": new_value
                        })
                    # Fix per-model values in field_votes
                    for model_key in ["gpt_value", "claude_value", "gemini_value"]:
                        current_value = vote_data.get(model_key)
                        if current_value in DRUG_CLASS_MAPPING:
                            new_value = DRUG_CLASS_MAPPING[current_value]
                            vote_data[model_key] = new_value
                            modified = True
                            results["checkpoint_updates"].append({
                                "question_id": question_id,
                                "section": "field_votes",
                                "field": f"{field}.{model_key}",
                                "old_value": current_value,
                                "new_value": new_value
                            })

        if modified:
            results["questions_modified"] += 1

    # Write updated checkpoint
    with open(checkpoint_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    return results


def main():
    """Main function to run retroactive fix."""
    base_path = Path(__file__).parent.parent

    # Fix database
    db_path = base_path / "dashboard" / "data" / "questions.db"
    print(f"Fixing database: {db_path}")
    db_results = fix_database(db_path)
    print(f"  Database updates: {len(db_results['database_updates'])}")

    # Group by question_id for cleaner output
    if db_results['database_updates']:
        by_question = {}
        for update in db_results['database_updates']:
            qid = update['question_id']
            if qid not in by_question:
                by_question[qid] = []
            by_question[qid].append(f"{update['field']}: {update['old_value']} -> {update['new_value']}")

        print("\n  Database changes by question:")
        for qid, changes in by_question.items():
            print(f"    Q{qid}: {', '.join(changes)}")

    # Fix checkpoint files
    checkpoint_dir = base_path / "data" / "checkpoints"
    mm_checkpoint = checkpoint_dir / "stage2_tagged_multiple_myeloma.json"

    if mm_checkpoint.exists():
        print(f"\nFixing checkpoint: {mm_checkpoint}")
        cp_results = fix_checkpoint(mm_checkpoint)
        print(f"  Questions modified: {cp_results['questions_modified']}")
        print(f"  Total field updates: {len(cp_results['checkpoint_updates'])}")

        if cp_results['checkpoint_updates']:
            # Summarize by old_value
            by_old_value = {}
            for update in cp_results['checkpoint_updates']:
                old = update['old_value']
                if old not in by_old_value:
                    by_old_value[old] = 0
                by_old_value[old] += 1

            print("\n  Checkpoint changes by old value:")
            for old_value, count in by_old_value.items():
                print(f"    '{old_value}' -> 'Monoclonal antibody': {count} fields")

    print("\nDone!")


if __name__ == "__main__":
    main()
