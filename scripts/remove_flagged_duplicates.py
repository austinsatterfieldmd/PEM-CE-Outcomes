"""
Remove flagged duplicate questions from stage 2 ready file.

This script:
1. Loads the duplicate review file
2. Extracts oncology question IDs that were flagged
3. Removes them from the stage2_ready_combined file
4. Saves a new cleaned file

Run: python scripts/remove_flagged_duplicates.py
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
import sys


def main():
    """Main function."""
    project_root = Path(__file__).parent.parent

    # Find the most recent duplicate review file
    eval_dir = project_root / "data/eval"
    review_files = list(eval_dir.glob("duplicate_review_fixed_*.xlsx"))

    if not review_files:
        print("No duplicate review file found in data/eval/")
        return

    # Sort by modification time and get most recent
    review_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    review_file = review_files[0]

    print(f"{'='*60}")
    print(f"REMOVING FLAGGED DUPLICATES FROM STAGE 2")
    print('='*60)
    print(f"\nUsing review file: {review_file.name}")

    # Load the duplicate review file
    review_df = pd.read_excel(review_file)
    print(f"Loaded {len(review_df)} rows from review file")
    print(f"Unique duplicate groups: {review_df['group_id'].nunique()}")

    # Get oncology question IDs from the review
    oncology_dupes = review_df[review_df['SOURCE'] == 'ONCOLOGY']['QUESTIONGROUPDESIGNATION'].astype(str).unique()
    print(f"\nOncology questions flagged as potential duplicates: {len(oncology_dupes)}")

    # Load stage2_ready_combined
    stage2_file = project_root / "data/checkpoints/stage2_ready_combined_20260123.xlsx"
    if not stage2_file.exists():
        print(f"Stage 2 file not found: {stage2_file}")
        return

    stage2_df = pd.read_excel(stage2_file)
    original_count = len(stage2_df)
    print(f"\nStage 2 ready file: {stage2_file.name}")
    print(f"  Original row count: {original_count}")

    # Convert IDs to string for comparison
    stage2_df['QUESTIONGROUPDESIGNATION'] = stage2_df['QUESTIONGROUPDESIGNATION'].astype(str)

    # Find which ones to remove
    to_remove = set(oncology_dupes)
    mask = stage2_df['QUESTIONGROUPDESIGNATION'].isin(to_remove)
    removed_count = mask.sum()

    print(f"  Questions to remove: {removed_count}")

    # Show sample of what's being removed
    if removed_count > 0:
        removed_df = stage2_df[mask]
        print(f"\n  Sample of questions being removed:")
        for _, row in removed_df.head(5).iterrows():
            question = str(row.get('OPTIMIZEDQUESTION', ''))[:60]
            print(f"    ID {row['QUESTIONGROUPDESIGNATION']}: {question}...")

    # Remove the flagged questions
    cleaned_df = stage2_df[~mask].copy()
    final_count = len(cleaned_df)

    print(f"\n  Final row count: {final_count}")
    print(f"  Removed: {original_count - final_count} questions")

    # Save the cleaned file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = project_root / f"data/checkpoints/stage2_ready_cleaned_{timestamp}.xlsx"
    cleaned_df.to_excel(output_file, index=False)

    print(f"\n{'='*60}")
    print("SUMMARY")
    print('='*60)
    print(f"Original questions: {original_count}")
    print(f"Removed (flagged duplicates): {removed_count}")
    print(f"Remaining questions: {final_count}")
    print(f"\nOutput file: {output_file.name}")

    # Also save the list of removed IDs for reference
    removed_ids_file = project_root / f"data/eval/removed_duplicate_ids_{timestamp}.txt"
    with open(removed_ids_file, 'w') as f:
        f.write(f"# Removed {removed_count} oncology questions flagged as potential duplicates\n")
        f.write(f"# Source: {review_file.name}\n")
        f.write(f"# Date: {timestamp}\n\n")
        for qid in sorted(to_remove):
            f.write(f"{qid}\n")

    print(f"Removed IDs list: {removed_ids_file.name}")


if __name__ == "__main__":
    main()
