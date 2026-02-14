"""
Import performance data from raw Excel into SQLite and/or Supabase.

Reads the full Excel scoring file and imports performance data for questions
that exist in the target database. Does NOT delete existing data — uses
INSERT OR REPLACE (SQLite) or upsert (Supabase) for idempotent operation.

Usage:
    # Import to SQLite (default)
    python scripts/import_performance_data.py

    # Import to Supabase
    python scripts/import_performance_data.py --target supabase

    # Import to both
    python scripts/import_performance_data.py --target both

    # Only for a specific disease
    python scripts/import_performance_data.py --disease "NSCLC"

    # Preview only
    python scripts/import_performance_data.py --dry-run
"""

import os
import sys
import sqlite3
import argparse
import logging
import math
from pathlib import Path
from collections import defaultdict

import pandas as pd

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

DB_PATH = PROJECT_ROOT / "dashboard" / "data" / "questions.db"
EXCEL_PATH = PROJECT_ROOT / "data" / "raw" / "FullColumnsSample_v2_012026_v3_ScoringUpdates_021226.xlsx"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

SEGMENT_MAP = {
    'Overall': 'overall',
    'MedicalOncology': 'medical_oncologist',
    'AcademicOncology': 'academic',
    'CommunityOncology': 'community',
    'NP/PA': 'app',
    'NursingOncology': 'nursing',
    'SurgicalOncology': 'surgical_oncologist',
    'RadiationOncology': 'radiation_oncologist',
}


def safe_float(val):
    """Convert pandas value to float, NaN → None."""
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return None
    try:
        f = float(val)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


def safe_int(val):
    """Convert pandas value to int, NaN → 0."""
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return 0
    try:
        return int(val)
    except (TypeError, ValueError):
        return 0


def safe_pct(calc, n):
    """Calculate percentage safely, NaN-proof."""
    if calc is None or n is None:
        return None
    try:
        calc_f = float(calc)
        n_f = float(n)
        if math.isnan(calc_f) or math.isnan(n_f) or n_f <= 0:
            return None
        return round(calc_f / n_f * 100, 2)
    except (TypeError, ValueError):
        return None


def get_question_ids(target, disease_filter=None):
    """Get QGD → question_id mapping from the target database."""
    if target == 'supabase':
        from dashboard.backend.services.supabase_db import SupabaseDatabaseService
        db = SupabaseDatabaseService()

        # Paginate to get ALL questions (default limit is 1000)
        qgd_to_id = {}
        page_size = 1000
        offset = 0
        while True:
            result = (db.client.table('questions')
                      .select('id, source_id')
                      .not_.is_('source_id', 'null')
                      .range(offset, offset + page_size - 1)
                      .execute())
            if not result.data:
                break
            for r in result.data:
                qgd_to_id[r['source_id']] = r['id']
            if len(result.data) < page_size:
                break
            offset += page_size

        if disease_filter:
            # Filter by disease via tags table (also paginated)
            disease_qids = set()
            offset = 0
            while True:
                tag_result = (db.client.table('tags')
                              .select('question_id')
                              .eq('disease_state', disease_filter)
                              .range(offset, offset + page_size - 1)
                              .execute())
                if not tag_result.data:
                    break
                for r in tag_result.data:
                    disease_qids.add(r['question_id'])
                if len(tag_result.data) < page_size:
                    break
                offset += page_size
            qgd_to_id = {qgd: qid for qgd, qid in qgd_to_id.items() if qid in disease_qids}

        return qgd_to_id, db
    else:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row

        if disease_filter:
            rows = conn.execute(
                """SELECT q.id, q.source_id FROM questions q
                   JOIN tags t ON q.id = t.question_id
                   WHERE q.source_id IS NOT NULL AND t.disease_state = ?""",
                (disease_filter,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, source_id FROM questions WHERE source_id IS NOT NULL"
            ).fetchall()

        qgd_to_id = {row['source_id']: row['id'] for row in rows}
        return qgd_to_id, conn


def import_performance(target='sqlite', disease_filter=None, dry_run=False, excel_path=None):
    """Import performance data from Excel into the target database."""
    excel_file = excel_path or EXCEL_PATH

    logger.info("=" * 60)
    logger.info("IMPORT PERFORMANCE DATA")
    logger.info(f"  Target:  {target}")
    logger.info(f"  Disease: {disease_filter or 'all'}")
    logger.info(f"  Excel:   {excel_file.name}")
    logger.info(f"  Dry run: {dry_run}")
    logger.info("=" * 60)

    if not excel_file.exists():
        logger.error(f"Excel file not found: {excel_file}")
        return

    # Step 1: Load Excel
    logger.info("\nLoading Excel file...")
    df = pd.read_excel(excel_file)
    logger.info(f"  Total rows: {len(df):,}")
    logger.info(f"  Unique QGDs: {df['QUESTIONGROUPDESIGNATION'].nunique():,}")

    # Step 2: Get question mapping from target
    logger.info(f"\nGetting question mapping from {target}...")
    qgd_to_id, db_handle = get_question_ids(target, disease_filter)
    logger.info(f"  Questions to match: {len(qgd_to_id)}")

    if not qgd_to_id:
        logger.warning("No questions found in target database. Nothing to do.")
        return

    # Step 3: Filter Excel to our QGDs
    db_qgds = set(qgd_to_id.keys())
    df_ours = df[df['QUESTIONGROUPDESIGNATION'].isin(db_qgds)].copy()
    logger.info(f"  Excel rows matching: {len(df_ours):,}")

    if df_ours.empty:
        logger.warning("No matching rows in Excel. Check QGD values.")
        return

    # Step 4: Aggregate performance per QGD × SCORINGGROUP
    logger.info("\nAggregating performance data...")
    perf_agg = df_ours.groupby(['QUESTIONGROUPDESIGNATION', 'SCORINGGROUP']).agg(
        pre_calc=('PRESCORECALC', 'sum'),
        pre_n=('PRESCOREN', 'sum'),
        post_calc=('POSTSCORECALC', 'sum'),
        post_n=('POSTSCOREN', 'sum'),
    ).reset_index()

    # Compute percentages
    perf_agg['pre_score'] = perf_agg.apply(
        lambda r: safe_pct(r['pre_calc'], r['pre_n']), axis=1
    )
    perf_agg['post_score'] = perf_agg.apply(
        lambda r: safe_pct(r['post_calc'], r['post_n']), axis=1
    )

    # Build performance rows
    perf_rows = []
    skipped = 0
    for _, row in perf_agg.iterrows():
        qgd = int(row['QUESTIONGROUPDESIGNATION'])
        question_id = qgd_to_id.get(qgd)
        if not question_id:
            continue
        segment = SEGMENT_MAP.get(row['SCORINGGROUP'])
        if not segment:
            skipped += 1
            continue
        perf_rows.append({
            'question_id': question_id,
            'segment': segment,
            'pre_score': safe_float(row['pre_score']),
            'post_score': safe_float(row['post_score']),
            'pre_n': safe_int(row['pre_n']),
            'post_n': safe_int(row['post_n']),
        })

    logger.info(f"  Performance rows to insert: {len(perf_rows)} (skipped unmapped segments: {skipped})")

    # Step 5: Build activities and question-activity links
    logger.info("\nBuilding activities and demographic performance...")

    # Activities
    activities_df = df_ours.groupby('COURSENAME').agg(
        start_date=('STARTDATE', 'first'),
    ).reset_index()
    logger.info(f"  Unique activities: {len(activities_df)}")

    # Demographic performance (per QGD × COURSENAME × SCORINGGROUP)
    demo_agg = df_ours.groupby(
        ['QUESTIONGROUPDESIGNATION', 'COURSENAME', 'SCORINGGROUP']
    ).agg(
        pre_calc=('PRESCORECALC', 'sum'),
        pre_n=('PRESCOREN', 'sum'),
        post_calc=('POSTSCORECALC', 'sum'),
        post_n=('POSTSCOREN', 'sum'),
    ).reset_index()
    logger.info(f"  Demographic performance groups: {len(demo_agg):,}")

    if dry_run:
        # Report what would happen per disease
        logger.info("\n[DRY RUN] Summary of what would be imported:")
        logger.info(f"  Performance rows: {len(perf_rows)}")
        logger.info(f"  Activities: {len(activities_df)}")
        logger.info(f"  Demographic perf groups: {len(demo_agg):,}")

        # Count questions that would get performance data
        qids_with_perf = {r['question_id'] for r in perf_rows}
        logger.info(f"  Questions that would receive data: {len(qids_with_perf)}")
        return

    # Step 6: Insert into target
    if target == 'sqlite':
        _insert_sqlite(perf_rows, activities_df, demo_agg, qgd_to_id, db_handle)
    else:
        _insert_supabase(perf_rows, activities_df, demo_agg, qgd_to_id, db_handle)

    logger.info("\nDone.")


def _insert_sqlite(perf_rows, activities_df, demo_agg, qgd_to_id, conn):
    """Insert performance data into SQLite."""
    cursor = conn.cursor()

    # Performance rows (upsert)
    logger.info("\nInserting performance rows...")
    for pr in perf_rows:
        cursor.execute("""
            INSERT OR REPLACE INTO performance
            (question_id, segment, pre_score, post_score, pre_n, post_n)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (pr['question_id'], pr['segment'], pr['pre_score'],
              pr['post_score'], pr['pre_n'], pr['post_n']))
    conn.commit()
    logger.info(f"  Inserted/updated: {len(perf_rows)} performance rows")

    # Activities (upsert by name)
    logger.info("Creating activities...")
    activity_name_to_id = {}
    for _, row in activities_df.iterrows():
        name = str(row['COURSENAME'])
        try:
            date_val = pd.to_datetime(row['start_date']).strftime('%Y-%m-%d') if pd.notna(row['start_date']) else None
        except Exception:
            date_val = None

        # Check if exists
        existing = cursor.execute(
            "SELECT id FROM activities WHERE activity_name = ?", (name,)
        ).fetchone()
        if existing:
            activity_name_to_id[name] = existing[0]
        else:
            cursor.execute(
                "INSERT INTO activities (activity_name, activity_date) VALUES (?, ?)",
                (name, date_val)
            )
            activity_name_to_id[name] = cursor.lastrowid
    conn.commit()
    logger.info(f"  Activities: {len(activity_name_to_id)}")

    # Question-activities (skip existing)
    logger.info("Creating question-activity links...")
    qa_count = 0
    qa_existing = set()
    for row in cursor.execute("SELECT question_id, activity_id FROM question_activities").fetchall():
        qa_existing.add((row[0], row[1]))

    qa_pairs = set()
    for _, row in demo_agg.iterrows():
        qgd = int(row['QUESTIONGROUPDESIGNATION'])
        question_id = qgd_to_id.get(qgd)
        activity_id = activity_name_to_id.get(str(row['COURSENAME']))
        if question_id and activity_id:
            qa_pairs.add((question_id, activity_id))

    for q_id, a_id in qa_pairs:
        if (q_id, a_id) not in qa_existing:
            cursor.execute(
                "INSERT INTO question_activities (question_id, activity_id) VALUES (?, ?)",
                (q_id, a_id)
            )
            qa_count += 1
    conn.commit()
    logger.info(f"  New question-activity links: {qa_count}")

    # Demographic performance (upsert)
    logger.info("Inserting demographic performance...")
    dp_count = 0
    for _, row in demo_agg.iterrows():
        qgd = int(row['QUESTIONGROUPDESIGNATION'])
        question_id = qgd_to_id.get(qgd)
        course_name = str(row['COURSENAME'])
        activity_id = activity_name_to_id.get(course_name)
        if not question_id or not activity_id:
            continue

        pre_n = safe_int(row['pre_n'])
        post_n = safe_int(row['post_n'])
        pre_score = safe_pct(row['pre_calc'], row['pre_n'])
        post_score = safe_pct(row['post_calc'], row['post_n'])
        n_respondents = pre_n + post_n

        if pre_score is None and post_score is None:
            continue

        cursor.execute("""
            INSERT OR REPLACE INTO demographic_performance
            (question_id, activity_id, specialty, pre_score, post_score,
             n_respondents, pre_n, post_n)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (question_id, activity_id, row['SCORINGGROUP'],
              pre_score, post_score, n_respondents, pre_n, post_n))
        dp_count += 1
    conn.commit()
    logger.info(f"  Demographic perf rows: {dp_count}")

    # Verification
    logger.info("\nVerification:")
    cursor.execute("SELECT COUNT(DISTINCT question_id) FROM performance")
    q_with_perf = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM performance WHERE segment = 'overall'")
    overall = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM questions")
    total_q = cursor.fetchone()[0]
    logger.info(f"  Questions with performance: {q_with_perf}/{total_q}")
    logger.info(f"  Overall segment rows: {overall}")

    conn.close()


def _insert_supabase(perf_rows, activities_df, demo_agg, qgd_to_id, db):
    """Insert performance data into Supabase."""
    from dashboard.backend.services.supabase_db import SupabaseDatabaseService

    # Performance rows (batch upsert)
    logger.info("\nInserting performance rows to Supabase...")
    if perf_rows:
        count = db.insert_performance_batch(perf_rows)
        logger.info(f"  Inserted: {count} performance rows")

    # Activities (upsert)
    logger.info("Creating activities...")
    activity_name_to_id = {}
    for _, row in activities_df.iterrows():
        name = str(row['COURSENAME'])
        try:
            date_val = pd.to_datetime(row['start_date']).date() if pd.notna(row['start_date']) else None
        except Exception:
            date_val = None
        act_id = db.upsert_activity_metadata(activity_name=name, activity_date=date_val)
        if act_id:
            activity_name_to_id[name] = act_id
    logger.info(f"  Activities: {len(activity_name_to_id)}")

    # Question-activities
    logger.info("Creating question-activity links...")
    qa_count = 0
    qa_pairs = set()
    for _, row in demo_agg.iterrows():
        qgd = int(row['QUESTIONGROUPDESIGNATION'])
        question_id = qgd_to_id.get(qgd)
        activity_id = activity_name_to_id.get(str(row['COURSENAME']))
        if question_id and activity_id:
            qa_pairs.add((question_id, activity_id))

    for q_id, a_id in qa_pairs:
        try:
            db.insert_question_activity(question_id=q_id, activity_id=a_id)
            qa_count += 1
        except Exception:
            pass  # Already exists
    logger.info(f"  Question-activity links: {qa_count}")

    # Demographic performance
    logger.info("Inserting demographic performance...")
    dp_rows = []
    for _, row in demo_agg.iterrows():
        qgd = int(row['QUESTIONGROUPDESIGNATION'])
        question_id = qgd_to_id.get(qgd)
        course_name = str(row['COURSENAME'])
        activity_id = activity_name_to_id.get(course_name)
        if not question_id or not activity_id:
            continue

        pre_n = safe_int(row['pre_n'])
        post_n = safe_int(row['post_n'])
        pre_score = safe_pct(row['pre_calc'], row['pre_n'])
        post_score = safe_pct(row['post_calc'], row['post_n'])
        n_respondents = pre_n + post_n

        if pre_score is None and post_score is None:
            continue

        dp_rows.append({
            'question_id': question_id,
            'activity_id': activity_id,
            'specialty': row['SCORINGGROUP'],
            'pre_score': pre_score,
            'post_score': post_score,
            'n_respondents': n_respondents,
            'pre_n': pre_n,
            'post_n': post_n,
        })

    if dp_rows:
        count = db.insert_demographic_performance_batch(dp_rows)
        logger.info(f"  Demographic perf rows: {count}")

    # Verification
    logger.info("\nVerification:")
    p_count = db.client.table('performance').select('id', count='exact').limit(0).execute().count
    logger.info(f"  Performance rows in Supabase: {p_count}")


def main():
    parser = argparse.ArgumentParser(description="Import performance data from Excel")
    parser.add_argument("--target", choices=["sqlite", "supabase", "both"],
                        default="sqlite", help="Target database (default: sqlite)")
    parser.add_argument("--disease", type=str, help="Filter to specific disease state")
    parser.add_argument("--excel", type=Path, default=EXCEL_PATH,
                        help="Path to raw Excel file")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()

    targets = ['sqlite', 'supabase'] if args.target == 'both' else [args.target]

    for t in targets:
        import_performance(
            target=t,
            disease_filter=args.disease,
            dry_run=args.dry_run,
            excel_path=args.excel,
        )


if __name__ == "__main__":
    main()
