"""
Fix Demographic Performance Data Import

This script fixes the demographic_performance table by:
1. Adding separate pre_n and post_n columns
2. Recalculating percentages from counts: (correct_count / n) * 100
3. Properly aggregating data per question × activity × segment

Usage:
    python scripts/fix_demographic_performance.py [--dry-run]
"""

import argparse
import sqlite3
from pathlib import Path
from collections import defaultdict

import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent
DEFAULT_INPUT = PROJECT_ROOT / "data" / "raw" / "FullColumnsSample_v2_012026.xlsx"
DEFAULT_DB = PROJECT_ROOT / "dashboard" / "data" / "questions.db"


def fix_demographic_performance(
    input_path: Path,
    db_path: Path,
    dry_run: bool = False
):
    """
    Fix demographic performance data with proper percentage calculations.
    """
    print(f"\n=== Fix Demographic Performance Data ===")
    print(f"Input:  {input_path}")
    print(f"DB:     {db_path}")
    print(f"Mode:   {'DRY RUN' if dry_run else 'WRITE'}")

    # Load Excel file
    print(f"\nLoading Excel file...")
    df = pd.read_excel(input_path)
    print(f"  Total rows: {len(df):,}")

    # Connect to database
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get question_id mapping (source_id -> question_id)
    cursor.execute("SELECT id, source_id FROM questions WHERE source_id IS NOT NULL")
    qgd_to_question_id = {int(row["source_id"]): row["id"] for row in cursor.fetchall()}
    print(f"  Questions in DB: {len(qgd_to_question_id)}")

    # Get activity_id mapping (activity_name -> activity_id)
    cursor.execute("SELECT id, activity_name FROM activities")
    activity_name_to_id = {row["activity_name"]: row["id"] for row in cursor.fetchall()}
    print(f"  Activities in DB: {len(activity_name_to_id)}")

    if not dry_run:
        # Update schema: Add pre_n and post_n columns if they don't exist
        print(f"\nUpdating schema...")
        try:
            cursor.execute("ALTER TABLE demographic_performance ADD COLUMN pre_n INTEGER")
            print("  Added pre_n column")
        except sqlite3.OperationalError:
            print("  pre_n column already exists")

        try:
            cursor.execute("ALTER TABLE demographic_performance ADD COLUMN post_n INTEGER")
            print("  Added post_n column")
        except sqlite3.OperationalError:
            print("  post_n column already exists")

        # Clear existing demographic_performance data
        print(f"\nClearing existing demographic_performance data...")
        cursor.execute("DELETE FROM demographic_performance")
        print(f"  Cleared all rows")
        conn.commit()

    # Aggregate data by question × activity × segment
    # Structure: {(question_id, activity_id, segment): {pre_correct, pre_n, post_correct, post_n}}
    aggregated = defaultdict(lambda: {
        "pre_correct": 0, "pre_n": 0,
        "post_correct": 0, "post_n": 0
    })

    print(f"\nProcessing rows...")
    rows_processed = 0
    rows_skipped_no_qgd = 0
    rows_skipped_not_in_db = 0
    rows_skipped_no_activity = 0

    for idx, row in df.iterrows():
        rows_processed += 1

        # Get QGD
        qgd = row.get("QUESTIONGROUPDESIGNATION")
        if pd.isna(qgd):
            rows_skipped_no_qgd += 1
            continue

        qgd = int(qgd)
        if qgd not in qgd_to_question_id:
            rows_skipped_not_in_db += 1
            continue

        question_id = qgd_to_question_id[qgd]

        # Get activity
        course_name = row.get("COURSENAME")
        if pd.isna(course_name):
            rows_skipped_no_activity += 1
            continue

        course_name = str(course_name)
        activity_id = activity_name_to_id.get(course_name)
        if activity_id is None:
            rows_skipped_no_activity += 1
            continue

        # Get segment
        segment = row.get("SCORINGGROUP")
        if pd.isna(segment):
            segment = "Overall"
        segment = str(segment)

        # Skip "Overall" segment - we'll calculate our own
        if segment == "Overall":
            continue

        # Aggregate pre-test data
        pre_correct = row.get("PRESCORECALC")
        pre_n = row.get("PRESCOREN")
        if pd.notna(pre_correct) and pd.notna(pre_n) and pre_n > 0:
            key = (question_id, activity_id, segment)
            aggregated[key]["pre_correct"] += int(pre_correct)
            aggregated[key]["pre_n"] += int(pre_n)

        # Aggregate post-test data
        post_correct = row.get("POSTSCORECALC")
        post_n = row.get("POSTSCOREN")
        if pd.notna(post_correct) and pd.notna(post_n) and post_n > 0:
            key = (question_id, activity_id, segment)
            aggregated[key]["post_correct"] += int(post_correct)
            aggregated[key]["post_n"] += int(post_n)

        if rows_processed % 50000 == 0:
            print(f"  Processed {rows_processed:,} rows...")

    print(f"\n=== Processing Summary ===")
    print(f"  Rows processed: {rows_processed:,}")
    print(f"  Rows skipped (no QGD): {rows_skipped_no_qgd:,}")
    print(f"  Rows skipped (QGD not in DB): {rows_skipped_not_in_db:,}")
    print(f"  Rows skipped (no activity): {rows_skipped_no_activity:,}")
    print(f"  Unique combinations: {len(aggregated):,}")

    # Insert aggregated data
    print(f"\nInserting aggregated data...")
    inserted = 0

    for (question_id, activity_id, segment), data in aggregated.items():
        pre_n = data["pre_n"]
        post_n = data["post_n"]
        pre_correct = data["pre_correct"]
        post_correct = data["post_correct"]

        # Calculate percentages
        pre_score = (pre_correct / pre_n * 100) if pre_n > 0 else None
        post_score = (post_correct / post_n * 100) if post_n > 0 else None

        # Only insert if we have at least some data
        if pre_score is None and post_score is None:
            continue

        if not dry_run:
            cursor.execute("""
                INSERT INTO demographic_performance
                (question_id, activity_id, specialty, pre_score, post_score, pre_n, post_n)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                question_id, activity_id, segment,
                pre_score, post_score,
                pre_n if pre_n > 0 else None,
                post_n if post_n > 0 else None
            ))

        inserted += 1

    if not dry_run:
        conn.commit()

    print(f"  Inserted {inserted:,} demographic performance records")

    # Verify some data
    if not dry_run:
        print(f"\n=== Verification ===")
        # Check Q4500 (QGD 6376) for ASCO ISS MedicalOncology
        cursor.execute("""
            SELECT dp.*, a.activity_name
            FROM demographic_performance dp
            JOIN activities a ON dp.activity_id = a.id
            JOIN questions q ON dp.question_id = q.id
            WHERE q.source_id = 6376
            AND a.activity_name LIKE '%ASCO ISS%'
            AND dp.specialty = 'MedicalOncology'
        """)
        rows = cursor.fetchall()
        print(f"  Q4500 ASCO ISS MedicalOncology data:")
        for r in rows:
            name = r["activity_name"][:40]
            print(f"    {name}...")
            print(f"      pre: {r['pre_score']:.1f}% (n={r['pre_n']})" if r['pre_score'] else f"      pre: None")
            print(f"      post: {r['post_score']:.1f}% (n={r['post_n']})" if r['post_score'] else f"      post: None")

    conn.close()

    if dry_run:
        print(f"\n[DRY RUN] No changes made to database")
    else:
        print(f"\n[SUCCESS] Demographic performance data fixed")

    return {"inserted": inserted}


def main():
    parser = argparse.ArgumentParser(
        description="Fix demographic performance data with proper calculations"
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Input Excel file (default: {DEFAULT_INPUT})"
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB,
        help=f"SQLite database path (default: {DEFAULT_DB})"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )

    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}")
        return 1

    if not args.db.exists():
        print(f"Error: Database not found: {args.db}")
        return 1

    fix_demographic_performance(
        input_path=args.input,
        db_path=args.db,
        dry_run=args.dry_run
    )

    return 0


if __name__ == "__main__":
    exit(main())
