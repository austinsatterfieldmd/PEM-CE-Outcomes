"""
Backfill corrections from already-reviewed questions.

Compares the original LLM tags (from stage2_tagged JSON files) with
the current database values (which include human corrections) to
create correction records for few-shot learning.

Usage:
    python scripts/backfill_corrections.py --disease "Multiple myeloma"
    python scripts/backfill_corrections.py --all
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.backend.services.database import DatabaseService
from dashboard.backend.services.corrections import (
    save_correction,
    find_edited_fields,
    get_corrections_file,
    normalize_disease_name,
)


def load_batch_file(disease_state: str) -> dict:
    """Load the stage2 batch file for a disease."""
    disease_filename = normalize_disease_name(disease_state)
    batch_file = PROJECT_ROOT / "data" / "checkpoints" / f"stage2_tagged_{disease_filename}.json"

    if not batch_file.exists():
        print(f"Batch file not found: {batch_file}")
        return {}

    with open(batch_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Index by question_id for fast lookup
    return {q['question_id']: q for q in data}


def get_reviewed_questions(db: DatabaseService, disease_state: str) -> list:
    """Get questions that have been reviewed (needs_review=False) for a disease."""
    # Query the database for reviewed questions with this disease
    questions, total = db.search_questions(
        disease_states=[disease_state],
        needs_review=False,
        page=1,
        page_size=10000,  # Get all
    )
    return questions


def backfill_disease(disease_state: str, dry_run: bool = False):
    """Backfill corrections for a single disease."""
    print(f"\n{'='*60}")
    print(f"Backfilling corrections for: {disease_state}")
    print(f"{'='*60}")

    # Load original tags from batch file
    batch_data = load_batch_file(disease_state)
    if not batch_data:
        print(f"No batch data found for {disease_state}")
        return 0

    print(f"Loaded {len(batch_data)} questions from batch file")

    # Get reviewed questions from database
    db = DatabaseService()
    reviewed = get_reviewed_questions(db, disease_state)
    print(f"Found {len(reviewed)} reviewed questions in database")

    corrections_created = 0

    for question in reviewed:
        question_id = question['id']

        # Skip if not in batch file
        if question_id not in batch_data:
            continue

        batch_question = batch_data[question_id]
        original_tags = batch_question.get('final_tags', {})

        # Get current tags from database
        detail = db.get_question_detail(question_id)
        if not detail:
            continue

        corrected_tags = detail['tags']

        # Find edited fields
        edited_fields = find_edited_fields(original_tags, corrected_tags)

        if not edited_fields:
            # No changes made, skip
            continue

        print(f"\nQuestion {question_id}: {len(edited_fields)} fields edited")
        print(f"  Edited: {', '.join(edited_fields[:5])}{'...' if len(edited_fields) > 5 else ''}")

        if dry_run:
            print(f"  [DRY RUN] Would create correction record")
            corrections_created += 1
            continue

        # Create correction record
        result = save_correction(
            question_id=question_id,
            question_stem=batch_question.get('question_stem', ''),
            correct_answer=batch_question.get('correct_answer'),
            incorrect_answers=batch_question.get('incorrect_answers'),
            disease_state=disease_state,
            original_tags=original_tags,
            corrected_tags=corrected_tags,
        )

        if result:
            corrections_created += 1

    print(f"\n{'='*60}")
    print(f"Created {corrections_created} correction records for {disease_state}")

    # Show file location
    corrections_file = get_corrections_file(disease_state)
    if corrections_file.exists():
        print(f"Corrections file: {corrections_file}")
        # Count lines
        with open(corrections_file, 'r') as f:
            line_count = sum(1 for _ in f)
        print(f"Total corrections in file: {line_count}")

    return corrections_created


def list_available_diseases():
    """List diseases with batch files available."""
    checkpoints_dir = PROJECT_ROOT / "data" / "checkpoints"
    diseases = []

    for file in checkpoints_dir.glob("stage2_tagged_*.json"):
        # Extract disease name from filename
        disease_name = file.stem.replace("stage2_tagged_", "").replace("_", " ").title()
        diseases.append(disease_name)

    return diseases


def main():
    parser = argparse.ArgumentParser(description="Backfill corrections from reviewed questions")
    parser.add_argument("--disease", type=str, help="Disease state to backfill (e.g., 'Multiple myeloma')")
    parser.add_argument("--all", action="store_true", help="Backfill all available diseases")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--list", action="store_true", help="List available diseases")

    args = parser.parse_args()

    if args.list:
        diseases = list_available_diseases()
        print("Available diseases with batch files:")
        for d in diseases:
            print(f"  - {d}")
        return

    if args.all:
        diseases = list_available_diseases()
        total = 0
        for disease in diseases:
            total += backfill_disease(disease, dry_run=args.dry_run)
        print(f"\n{'='*60}")
        print(f"TOTAL: Created {total} correction records across {len(diseases)} diseases")
    elif args.disease:
        backfill_disease(args.disease, dry_run=args.dry_run)
    else:
        parser.print_help()
        print("\nExample:")
        print('  python scripts/backfill_corrections.py --disease "Multiple myeloma"')
        print('  python scripts/backfill_corrections.py --all --dry-run')


if __name__ == "__main__":
    main()
