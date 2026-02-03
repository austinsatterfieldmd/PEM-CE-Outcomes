"""
Script to retroactively fix drug_class and drug_target values for heme malignancies.

Changes:
1. Drug class fixes:
   - "Anti-CD20 antibody" -> "Monoclonal antibody" (drug_target should be "CD20")
   - "Anti-CD19 antibody" -> "Monoclonal antibody" (drug_target should be "CD19")
   - "Antibody-drug conjugate (ADC)" remains ADC (correct already)

2. Drug target additions for IMiDs:
   - If drug_class contains "IMiD" and drug_target doesn't have "Cereblon", add it
   - This applies when lenalidomide is in treatment fields

Updates both:
1. SQLite database (tags table)
2. Checkpoint JSON files (heme_tagged_*.json)

Usage:
    python scripts/fix_heme_drug_class.py --dry-run  # Preview changes
    python scripts/fix_heme_drug_class.py            # Apply changes
"""

import json
import sqlite3
import argparse
from pathlib import Path
from typing import Dict, List, Optional

# Mapping of old drug_class values to new standardized values
DRUG_CLASS_MAPPING = {
    "Anti-CD20 antibody": "Monoclonal antibody",
    "Anti-CD19 antibody": "Monoclonal antibody",
    "Anti-CD30 antibody": "Monoclonal antibody",
}

# IMiD drugs that should have Cereblon as target
IMID_DRUGS = ["lenalidomide", "pomalidomide", "thalidomide"]


def needs_cereblon_target(tags: dict) -> bool:
    """Check if this question needs Cereblon added to drug_target."""
    # Check if any drug_class is IMiD
    has_imid = False
    for i in range(1, 4):
        if tags.get(f"drug_class_{i}") == "IMiD":
            has_imid = True
            break

    if not has_imid:
        return False

    # Check if Cereblon is already in drug_target
    for i in range(1, 4):
        if tags.get(f"drug_target_{i}") == "Cereblon":
            return False  # Already has Cereblon

    return True


def find_empty_drug_target_slot(tags: dict) -> Optional[str]:
    """Find the first empty drug_target slot."""
    for i in range(1, 4):
        if not tags.get(f"drug_target_{i}"):
            return f"drug_target_{i}"
    return None


def fix_database(db_path: Path, dry_run: bool = False) -> dict:
    """Fix drug_class and drug_target values in the SQLite database."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    results = {
        "drug_class_updates": [],
        "cereblon_additions": [],
    }

    # 1. Fix drug_class values
    for field in ["drug_class_1", "drug_class_2", "drug_class_3"]:
        for old_value, new_value in DRUG_CLASS_MAPPING.items():
            cursor.execute(
                f"SELECT question_id, {field} FROM tags WHERE {field} = ?",
                (old_value,)
            )
            rows = cursor.fetchall()

            for row in rows:
                question_id = row["question_id"]
                if not dry_run:
                    cursor.execute(
                        f"UPDATE tags SET {field} = ? WHERE question_id = ?",
                        (new_value, question_id)
                    )
                results["drug_class_updates"].append({
                    "question_id": question_id,
                    "field": field,
                    "old_value": old_value,
                    "new_value": new_value
                })

    # 2. Add Cereblon to drug_target for IMiD questions
    # First, find all questions with IMiD drug_class
    cursor.execute("""
        SELECT question_id,
               drug_class_1, drug_class_2, drug_class_3,
               drug_target_1, drug_target_2, drug_target_3,
               treatment_1, treatment_2, treatment_3, treatment_4, treatment_5
        FROM tags
        WHERE drug_class_1 = 'IMiD' OR drug_class_2 = 'IMiD' OR drug_class_3 = 'IMiD'
    """)
    imid_rows = cursor.fetchall()

    for row in imid_rows:
        tags = dict(row)
        question_id = tags["question_id"]

        # Check if already has Cereblon
        has_cereblon = any(
            tags.get(f"drug_target_{i}") == "Cereblon"
            for i in range(1, 4)
        )

        if has_cereblon:
            continue

        # Find empty slot for Cereblon
        slot = None
        for i in range(1, 4):
            if not tags.get(f"drug_target_{i}"):
                slot = f"drug_target_{i}"
                break

        if slot:
            if not dry_run:
                cursor.execute(
                    f"UPDATE tags SET {slot} = ? WHERE question_id = ?",
                    ("Cereblon", question_id)
                )
            results["cereblon_additions"].append({
                "question_id": question_id,
                "field": slot,
                "new_value": "Cereblon"
            })

    if not dry_run:
        conn.commit()
    conn.close()

    return results


def fix_checkpoint(checkpoint_path: Path, dry_run: bool = False) -> dict:
    """Fix drug_class and drug_target values in the checkpoint JSON file."""

    with open(checkpoint_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    results = {
        "drug_class_updates": [],
        "cereblon_additions": [],
        "questions_modified": 0
    }

    # Handle nested {"results": [...]} format
    if isinstance(data, dict) and 'results' in data:
        questions = data['results']
    elif isinstance(data, list):
        questions = data
    else:
        questions = data.get("questions", [])

    for question in questions:
        modified = False
        question_id = question.get("source_id") or question.get("question_id")

        # 1. Fix drug_class in final_tags
        final_tags = question.get("final_tags", {})
        if final_tags:
            for field in ["drug_class_1", "drug_class_2", "drug_class_3"]:
                current_value = final_tags.get(field)
                if current_value in DRUG_CLASS_MAPPING:
                    new_value = DRUG_CLASS_MAPPING[current_value]
                    final_tags[field] = new_value
                    modified = True
                    results["drug_class_updates"].append({
                        "question_id": question_id,
                        "section": "final_tags",
                        "field": field,
                        "old_value": current_value,
                        "new_value": new_value
                    })

            # 2. Add Cereblon if IMiD present and missing Cereblon
            if needs_cereblon_target(final_tags):
                slot = find_empty_drug_target_slot(final_tags)
                if slot:
                    final_tags[slot] = "Cereblon"
                    modified = True
                    results["cereblon_additions"].append({
                        "question_id": question_id,
                        "section": "final_tags",
                        "field": slot,
                        "new_value": "Cereblon"
                    })

        # 3. Fix per-model tags
        for model in ["gpt_tags", "claude_tags", "gemini_tags"]:
            tags = question.get(model, {})
            if tags:
                for field in ["drug_class_1", "drug_class_2", "drug_class_3"]:
                    current_value = tags.get(field)
                    if current_value in DRUG_CLASS_MAPPING:
                        new_value = DRUG_CLASS_MAPPING[current_value]
                        tags[field] = new_value
                        modified = True
                        results["drug_class_updates"].append({
                            "question_id": question_id,
                            "section": model,
                            "field": field,
                            "old_value": current_value,
                            "new_value": new_value
                        })

                # Add Cereblon for IMiD
                if needs_cereblon_target(tags):
                    slot = find_empty_drug_target_slot(tags)
                    if slot:
                        tags[slot] = "Cereblon"
                        modified = True
                        results["cereblon_additions"].append({
                            "question_id": question_id,
                            "section": model,
                            "field": slot,
                            "new_value": "Cereblon"
                        })

        # 4. Fix field_votes
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
                        results["drug_class_updates"].append({
                            "question_id": question_id,
                            "section": "field_votes",
                            "field": f"{field}.final_value",
                            "old_value": current_value,
                            "new_value": new_value
                        })
                    # Fix per-model values
                    for model_key in ["gpt_value", "claude_value", "gemini_value"]:
                        current_value = vote_data.get(model_key)
                        if current_value in DRUG_CLASS_MAPPING:
                            new_value = DRUG_CLASS_MAPPING[current_value]
                            vote_data[model_key] = new_value
                            modified = True
                            results["drug_class_updates"].append({
                                "question_id": question_id,
                                "section": "field_votes",
                                "field": f"{field}.{model_key}",
                                "old_value": current_value,
                                "new_value": new_value
                            })

        if modified:
            results["questions_modified"] += 1

    # Write updated checkpoint (unless dry run)
    if not dry_run:
        with open(checkpoint_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Fix drug_class and drug_target values for heme malignancies"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without applying them"
    )
    args = parser.parse_args()

    base_path = Path(__file__).parent.parent

    if args.dry_run:
        print("=" * 60)
        print("DRY RUN - No changes will be made")
        print("=" * 60)

    # Fix database
    db_path = base_path / "dashboard" / "data" / "questions.db"
    print(f"\nFixing database: {db_path}")
    db_results = fix_database(db_path, dry_run=args.dry_run)

    print(f"  Drug class updates: {len(db_results['drug_class_updates'])}")
    print(f"  Cereblon additions: {len(db_results['cereblon_additions'])}")

    # Show drug class changes by old value
    if db_results['drug_class_updates']:
        by_old_value = {}
        for update in db_results['drug_class_updates']:
            old = update['old_value']
            if old not in by_old_value:
                by_old_value[old] = 0
            by_old_value[old] += 1

        print("\n  Drug class changes:")
        for old_value, count in sorted(by_old_value.items()):
            print(f"    '{old_value}' -> 'Monoclonal antibody': {count}")

    if db_results['cereblon_additions']:
        print(f"\n  Added Cereblon to {len(db_results['cereblon_additions'])} questions")

    # Fix checkpoint files
    checkpoint_dir = base_path / "data" / "checkpoints"
    heme_checkpoints = list(checkpoint_dir.glob("heme_tagged_*.json"))

    for checkpoint_path in heme_checkpoints:
        print(f"\nFixing checkpoint: {checkpoint_path.name}")
        cp_results = fix_checkpoint(checkpoint_path, dry_run=args.dry_run)
        print(f"  Questions modified: {cp_results['questions_modified']}")
        print(f"  Drug class updates: {len(cp_results['drug_class_updates'])}")
        print(f"  Cereblon additions: {len(cp_results['cereblon_additions'])}")

        if cp_results['drug_class_updates']:
            by_old_value = {}
            for update in cp_results['drug_class_updates']:
                old = update['old_value']
                if old not in by_old_value:
                    by_old_value[old] = 0
                by_old_value[old] += 1

            print("\n  Drug class changes:")
            for old_value, count in sorted(by_old_value.items()):
                print(f"    '{old_value}' -> 'Monoclonal antibody': {count}")

    if args.dry_run:
        print("\n" + "=" * 60)
        print("DRY RUN complete - run without --dry-run to apply changes")
        print("=" * 60)
    else:
        print("\nDone! Changes applied.")


if __name__ == "__main__":
    main()
