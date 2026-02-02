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
"""

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Set

import pandas as pd

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent

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
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Import outcomes data from Excel file into dashboard database.

    Args:
        input_path: Path to Excel file with outcomes data
        db_path: Path to SQLite database
        dry_run: If True, don't write to database

    Returns:
        Dict with import statistics
    """
    print(f"\n=== Import Outcomes to Dashboard ===")
    print(f"Input:  {input_path}")
    print(f"DB:     {db_path}")
    print(f"Mode:   {'DRY RUN' if dry_run else 'WRITE'}")

    # Load Excel file
    print(f"\nLoading Excel file...")
    df = pd.read_excel(input_path)
    print(f"  Rows: {len(df)}")

    # Connect to database
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get existing questions by source_id (QGD)
    cursor.execute("SELECT id, source_id FROM questions WHERE source_id IS NOT NULL")
    db_questions = {row["source_id"]: row["id"] for row in cursor.fetchall()}
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
                activity_date = pd.to_datetime(start_date).strftime("%Y-%m-%d")
                quarter = get_quarter_from_date(start_date)
            except:
                pass

        # Create or get activity
        activity_key = f"{course_id}|{course_name}"
        if activity_key not in activities_seen:
            if not dry_run:
                # Check if activity exists
                cursor.execute(
                    "SELECT id FROM activities WHERE activity_name = ?",
                    (course_name,)
                )
                existing = cursor.fetchone()

                if existing:
                    activities_seen[activity_key] = existing["id"]
                    stats["activities_updated"] += 1
                else:
                    cursor.execute("""
                        INSERT INTO activities (activity_name, activity_date, quarter)
                        VALUES (?, ?, ?)
                    """, (course_name, activity_date, quarter))
                    activities_seen[activity_key] = cursor.lastrowid
                    stats["activities_created"] += 1
            else:
                # Dry run - just count
                if activity_key not in activities_seen:
                    activities_seen[activity_key] = len(activities_seen) + 1
                    stats["activities_created"] += 1

        activity_id = activities_seen.get(activity_key)

        # Create question-activity link if not exists
        qa_key = (question_id, course_name)
        if qa_key not in question_activities_seen:
            question_activities_seen.add(qa_key)

            # Get performance scores
            pre_score = row.get("PRESCORECALC")
            post_score = row.get("POSTSCORECALC")
            pre_n = row.get("PRESCOREN")
            post_n = row.get("POSTSCOREN")

            if not dry_run:
                # Check if link exists
                cursor.execute("""
                    SELECT id FROM question_activities
                    WHERE question_id = ? AND activity_name = ?
                """, (question_id, course_name))
                existing = cursor.fetchone()

                if not existing:
                    cursor.execute("""
                        INSERT INTO question_activities
                        (question_id, activity_id, activity_name, activity_date, quarter,
                         pre_score, post_score, pre_n, post_n)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        question_id, activity_id, course_name, activity_date, quarter,
                        pre_score if not pd.isna(pre_score) else None,
                        post_score if not pd.isna(post_score) else None,
                        int(pre_n) if not pd.isna(pre_n) else None,
                        int(post_n) if not pd.isna(post_n) else None
                    ))
                    stats["question_activities_created"] += 1

                    # Also create aggregate performance record
                    if not pd.isna(pre_score) or not pd.isna(post_score):
                        cursor.execute("""
                            INSERT OR REPLACE INTO performance
                            (question_id, segment, pre_score, post_score, pre_n, post_n)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            question_id,
                            course_name,  # Use activity name as segment
                            pre_score if not pd.isna(pre_score) else None,
                            post_score if not pd.isna(post_score) else None,
                            int(pre_n) if not pd.isna(pre_n) else None,
                            int(post_n) if not pd.isna(post_n) else None
                        ))
                        stats["performance_records_created"] += 1
            else:
                stats["question_activities_created"] += 1
                if not pd.isna(row.get("PRESCORECALC")) or not pd.isna(row.get("POSTSCORECALC")):
                    stats["performance_records_created"] += 1

        # Progress indicator
        if stats["rows_processed"] % 50000 == 0:
            print(f"  Processed {stats['rows_processed']:,} rows...")

    # Commit if not dry run
    if not dry_run:
        conn.commit()

    conn.close()

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
        print(f"\n[SUCCESS] Data imported to database")

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
        "--dry-run",
        action="store_true",
        help="Show what would be imported without writing to database"
    )

    args = parser.parse_args()

    # Validate paths
    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}")
        return 1

    if not args.db.exists():
        print(f"Error: Database not found: {args.db}")
        return 1

    # Run import
    stats = import_outcomes(
        input_path=args.input,
        db_path=args.db,
        dry_run=args.dry_run
    )

    return 0


if __name__ == "__main__":
    exit(main())
