"""
Import Outcomes Data into Dashboard

This script imports activity-level performance data from the Excel file into
the dashboard database, linking questions to activities with their pre/post scores.

It imports:
- Activities (COURSEID, COURSENAME, STARTDATE)
- Question-Activity links with performance data (pre/post scores)
- Performance segments (by specialty, region, etc.)

Usage:
    python scripts/import_outcomes_to_dashboard.py [--input INPUT_FILE] [--dry-run]
    python scripts/import_outcomes_to_dashboard.py --target supabase       # Write directly to Supabase

Note: For full performance data rebuild with demographic breakdowns, prefer
      comprehensive_data_overhaul.py --phase 2 --target supabase
"""

import os
import sys
import argparse
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Set

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

# Default paths
DEFAULT_INPUT = PROJECT_ROOT / "data" / "raw" / "FullColumnsSample_v2_012026.xlsx"
DEFAULT_DB = PROJECT_ROOT / "dashboard" / "data" / "questions.db"


def get_quarter_from_date(date_str: str) -> Optional[str]:
    """Convert date to quarter string (e.g., '2024 Q3')."""
    if not date_str or pd.isna(date_str):
        return None
    try:
        if isinstance(date_str, str):
            dt = pd.to_datetime(date_str)
        else:
            dt = date_str
        quarter = (dt.month - 1) // 3 + 1
        return f"{dt.year} Q{quarter}"
    except:
        return None


def import_outcomes(
    input_path: Path,
    db_path: Path,
    dry_run: bool = False,
    target: str = 'sqlite'
) -> Dict[str, Any]:
    """
    Import outcomes data from Excel file into dashboard database.

    Args:
        input_path: Path to Excel file with outcomes data
        db_path: Path to SQLite database (only used when target='sqlite')
        dry_run: If True, don't write to database
        target: 'sqlite' or 'supabase'

    Returns:
        Dict with import statistics
    """
    from dashboard.backend.services.import_service import get_import_db

    print(f"\n=== Import Outcomes to Dashboard ===")
    print(f"Input:  {input_path}")
    print(f"Target: {target}")
    print(f"Mode:   {'DRY RUN' if dry_run else 'WRITE'}")

    # Load Excel file
    print(f"\nLoading Excel file...")
    df = pd.read_excel(input_path)
    print(f"  Rows: {len(df)}")

    # Get QGD-to-question_id mapping
    db = get_import_db(target)
    if target == 'supabase':
        result = db.client.table('questions').select('id, source_id').not_.is_('source_id', 'null').execute()
        db_questions = {r['source_id']: r['id'] for r in result.data}
    else:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, source_id FROM questions WHERE source_id IS NOT NULL")
        db_questions = {row["source_id"]: row["id"] for row in cursor.fetchall()}
        conn.close()  # Read-only; writes go through service layer

    print(f"  Questions in DB: {len(db_questions)}")

    # Track statistics
    stats = {
        "rows_processed": 0,
        "rows_skipped_no_qgd": 0,
        "rows_skipped_not_in_db": 0,
        "activities_created": 0,
        "activities_updated": 0,
        "question_activities_created": 0,
        "performance_records_created": 0,
    }

    # Track activities we've seen
    activities_seen: Dict[str, int] = {}
    question_activities_seen: Set[tuple] = set()

    print(f"\nProcessing rows...")

    for idx, row in df.iterrows():
        stats["rows_processed"] += 1

        # Get QGD
        qgd = row.get("QUESTIONGROUPDESIGNATION")
        if pd.isna(qgd):
            stats["rows_skipped_no_qgd"] += 1
            continue

        qgd = int(qgd)

        # Check if question exists in database
        if qgd not in db_questions:
            stats["rows_skipped_not_in_db"] += 1
            continue

        question_id = db_questions[qgd]

        # Get activity info
        course_id = row.get("COURSEID")
        course_name = row.get("COURSENAME", "")
        start_date = row.get("STARTDATE")

        if pd.isna(course_id) or pd.isna(course_name):
            continue

        course_id = str(course_id)
        course_name = str(course_name)

        # Parse date
        activity_date = None
        quarter = None
        if not pd.isna(start_date):
            try:
                dt = pd.to_datetime(start_date)
                activity_date = dt.date() if target == 'supabase' else dt.strftime("%Y-%m-%d")
                quarter = get_quarter_from_date(start_date)
            except:
                pass

        # Create or get activity
        activity_key = f"{course_id}|{course_name}"
        if activity_key not in activities_seen:
            if not dry_run:
                activity_id = db.upsert_activity_metadata(
                    activity_name=course_name,
                    activity_date=activity_date if target == 'supabase' else None,
                )
                if activity_id:
                    activities_seen[activity_key] = activity_id
                    stats["activities_created"] += 1
                # For SQLite upsert_activity_metadata with date string
                if target == 'sqlite' and activity_date and activity_id:
                    pass  # upsert_activity_metadata handles date
            else:
                activities_seen[activity_key] = len(activities_seen) + 1
                stats["activities_created"] += 1

        activity_id = activities_seen.get(activity_key)

        # Create question-activity link if not exists
        qa_key = (question_id, course_name)
        if qa_key not in question_activities_seen:
            question_activities_seen.add(qa_key)

            # Get performance scores
            pre_score_raw = row.get("PRESCORECALC")
            post_score_raw = row.get("POSTSCORECALC")
            pre_n = row.get("PRESCOREN")
            post_n = row.get("POSTSCOREN")

            pre_score = float(pre_score_raw) if not pd.isna(pre_score_raw) else None
            post_score = float(post_score_raw) if not pd.isna(post_score_raw) else None
            pre_n_val = int(pre_n) if not pd.isna(pre_n) else None
            post_n_val = int(post_n) if not pd.isna(post_n) else None

            if not dry_run:
                db.insert_question_activity(
                    question_id=question_id,
                    activity_name=course_name,
                    activity_id=activity_id,
                    activity_date=activity_date,
                    quarter=quarter,
                    pre_score=pre_score,
                    post_score=post_score,
                    pre_n=pre_n_val,
                    post_n=post_n_val,
                )
                stats["question_activities_created"] += 1

                # Also create aggregate performance record
                if pre_score is not None or post_score is not None:
                    db.insert_performance(
                        question_id=question_id,
                        segment=course_name,
                        pre_score=pre_score,
                        post_score=post_score,
                        pre_n=pre_n_val,
                        post_n=post_n_val,
                    )
                    stats["performance_records_created"] += 1
            else:
                stats["question_activities_created"] += 1
                if pre_score is not None or post_score is not None:
                    stats["performance_records_created"] += 1

        # Progress indicator
        if stats["rows_processed"] % 50000 == 0:
            print(f"  Processed {stats['rows_processed']:,} rows...")

    # Print summary
    print(f"\n=== Import Summary ===")
    print(f"  Rows processed: {stats['rows_processed']:,}")
    print(f"  Rows skipped (no QGD): {stats['rows_skipped_no_qgd']:,}")
    print(f"  Rows skipped (QGD not in DB): {stats['rows_skipped_not_in_db']:,}")
    print(f"  Activities created: {stats['activities_created']}")
    print(f"  Activities updated: {stats['activities_updated']}")
    print(f"  Question-Activity links: {stats['question_activities_created']}")
    print(f"  Performance records: {stats['performance_records_created']}")

    if dry_run:
        print(f"\n[DRY RUN] No changes written to database")
    else:
        print(f"\n[SUCCESS] Data imported to {target}")

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Import outcomes data from Excel into dashboard database"
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
        "--target",
        type=str,
        choices=["sqlite", "supabase"],
        default=os.environ.get("IMPORT_TARGET", "supabase"),
        help="Write target: supabase (default) or sqlite. Override with IMPORT_TARGET env var."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be imported without writing to database"
    )

    args = parser.parse_args()

    # Validate paths
    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}")
        return 1

    if args.target == 'sqlite' and not args.db.exists():
        print(f"Error: Database not found: {args.db}")
        return 1

    # Run import
    stats = import_outcomes(
        input_path=args.input,
        db_path=args.db,
        dry_run=args.dry_run,
        target=args.target
    )

    return 0


if __name__ == "__main__":
    exit(main())
