"""
Comprehensive Data Overhaul Script

Fixes three issues in one pass:
  1. Re-imports incomplete tags (Prostate + SCLC) from checkpoint files
  2. Rebuilds ALL performance data from corrected Excel scoring file
  3. Syncs everything to Supabase (only needed for --target sqlite)

Usage:
    python scripts/comprehensive_data_overhaul.py                         # Full run (SQLite)
    python scripts/comprehensive_data_overhaul.py --target supabase       # Write directly to Supabase
    python scripts/comprehensive_data_overhaul.py --dry-run               # Preview only
    python scripts/comprehensive_data_overhaul.py --phase 0,1,2           # Selective phases
    python scripts/comprehensive_data_overhaul.py --skip-supabase         # Skip Phase 3 sync
"""

import os
import sys
import json
import sqlite3
import shutil
import argparse
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# ============================================================
# Constants
# ============================================================

DB_PATH = PROJECT_ROOT / "dashboard" / "data" / "questions.db"
BACKUP_DIR = PROJECT_ROOT / "dashboard" / "data"
EXCEL_PATH = PROJECT_ROOT / "data" / "raw" / "FullColumnsSample_v2_012026_v3_ScoringUpdates_021226.xlsx"

CHECKPOINT_FILES = [
    PROJECT_ROOT / "data" / "checkpoints" / "stage2_prostate_cancer_checkpoint.json",
    PROJECT_ROOT / "data" / "checkpoints" / "stage2_sclc_checkpoint.json",
]

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

SUPABASE_SYNC_TABLES = ['tags', 'activities', 'performance', 'question_activities', 'demographic_performance']


# ============================================================
# Phase 0: Backup & Preflight
# ============================================================

def phase_0_backup(dry_run=False):
    """Create timestamped backup and verify all inputs."""
    logger.info("=" * 70)
    logger.info("PHASE 0: Backup & Preflight Checks")
    logger.info("=" * 70)

    # Verify database
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")
    logger.info(f"  Database: {DB_PATH} ({DB_PATH.stat().st_size / 1024 / 1024:.1f} MB)")

    # Verify checkpoint files
    for cp in CHECKPOINT_FILES:
        if not cp.exists():
            raise FileNotFoundError(f"Checkpoint not found: {cp}")
        with open(cp, 'r', encoding='utf-8') as f:
            data = json.load(f)
        count = len(data.get('results', []))
        logger.info(f"  Checkpoint: {cp.name} ({count} results)")

    # Verify Excel file
    if not EXCEL_PATH.exists():
        raise FileNotFoundError(f"Excel file not found: {EXCEL_PATH}")
    logger.info(f"  Excel: {EXCEL_PATH.name}")

    # Create backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"questions_backup_{timestamp}.db"
    if not dry_run:
        shutil.copy2(DB_PATH, backup_path)
        logger.info(f"  Backup created: {backup_path.name}")
    else:
        logger.info(f"  [DRY RUN] Would create backup: {backup_path.name}")

    # Print current state
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM questions")
    total_q = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tags")
    total_t = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM performance")
    total_p = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM question_activities")
    total_qa = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM demographic_performance")
    total_dp = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM activities")
    total_a = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tags WHERE agreement_level IS NULL")
    null_agreement = cursor.fetchone()[0]

    conn.close()

    logger.info(f"\n  Current database state:")
    logger.info(f"    Questions:                {total_q}")
    logger.info(f"    Tags:                     {total_t}")
    logger.info(f"    Tags w/ NULL agreement:   {null_agreement}")
    logger.info(f"    Performance rows:         {total_p}")
    logger.info(f"    Question-Activities:       {total_qa}")
    logger.info(f"    Demographic Performance:  {total_dp}")
    logger.info(f"    Activities:               {total_a}")

    return {"backup_path": str(backup_path) if not dry_run else "(dry run)"}


# ============================================================
# Phase 1: Re-import Tags from Checkpoints
# ============================================================

def phase_1_reimport_tags(dry_run=False, target='sqlite'):
    """Re-import incomplete tags from checkpoint files using the proper import script."""
    logger.info("")
    logger.info("=" * 70)
    logger.info(f"PHASE 1: Re-import Incomplete Tags from Checkpoints (target={target})")
    logger.info("=" * 70)

    from dashboard.scripts.import_stage2_results import import_stage2_upsert
    from dashboard.backend.services.import_service import get_import_db

    db = get_import_db(target)
    total_stats = {"inserted": 0, "updated": 0, "skipped_reviewed": 0, "skipped_excluded": 0, "errors": 0}

    for cp_path in CHECKPOINT_FILES:
        logger.info(f"\n  Processing: {cp_path.name}")

        with open(cp_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        results = data.get('results', [])
        logger.info(f"    Results to process: {len(results)}")

        if dry_run:
            # Count what would change
            conn = sqlite3.connect(str(DB_PATH))
            cursor = conn.cursor()
            would_update = 0
            would_insert = 0
            for r in results:
                sid = r.get('source_id') or r.get('qgd')
                if not sid:
                    continue
                cursor.execute("SELECT id FROM questions WHERE source_id = ?", (int(sid),))
                existing = cursor.fetchone()
                if existing:
                    # Check if edited
                    cursor.execute("SELECT edited_by_user FROM tags WHERE question_id = ?", (existing[0],))
                    tag_row = cursor.fetchone()
                    if tag_row and tag_row[0]:
                        continue
                    would_update += 1
                else:
                    would_insert += 1
            conn.close()
            logger.info(f"    [DRY RUN] Would update: {would_update}, Would insert: {would_insert}")
            total_stats["updated"] += would_update
            total_stats["inserted"] += would_insert
        else:
            stats = import_stage2_upsert(db, results, force_overwrite=False)
            for key in total_stats:
                if key in stats:
                    total_stats[key] += stats[key]
            logger.info(f"    Updated: {stats.get('updated', 0)}, "
                        f"Inserted: {stats.get('inserted', 0)}, "
                        f"Skipped (reviewed): {stats.get('skipped_reviewed', 0)}")

    logger.info(f"\n  Phase 1 totals: {total_stats}")

    # Verification
    if not dry_run:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM tags t
            JOIN questions q ON t.question_id = q.id
            WHERE t.disease_state IN ('Prostate cancer', 'SCLC')
            AND t.agreement_level IS NULL
        """)
        null_count = cursor.fetchone()[0]
        cursor.execute("""
            SELECT COUNT(*) FROM tags t
            JOIN questions q ON t.question_id = q.id
            WHERE t.disease_state IN ('Prostate cancer', 'SCLC')
            AND t.cme_outcome_level IS NOT NULL
        """)
        cme_count = cursor.fetchone()[0]
        conn.close()

        logger.info(f"\n  Verification:")
        logger.info(f"    Prostate/SCLC with NULL agreement_level: {null_count} (expect 0)")
        logger.info(f"    Prostate/SCLC with cme_outcome_level:    {cme_count} (expect 177)")

        if null_count > 0:
            logger.warning(f"    WARNING: {null_count} questions still have NULL agreement_level!")

    return total_stats


# ============================================================
# Phase 2: Rebuild Performance Data
# ============================================================

def phase_2_rebuild_performance(dry_run=False, verbose=False, target='sqlite'):
    """Clear and rebuild all performance data from the corrected Excel file."""
    logger.info("")
    logger.info("=" * 70)
    logger.info(f"PHASE 2: Rebuild All Performance Data from Corrected Excel (target={target})")
    logger.info("=" * 70)

    from dashboard.backend.services.import_service import get_import_db

    db = get_import_db(target)

    # Step 2a: Load Excel
    logger.info(f"\n  Loading Excel file...")
    df = pd.read_excel(EXCEL_PATH)
    logger.info(f"    Rows: {len(df):,}")
    logger.info(f"    Unique QGDs: {df['QUESTIONGROUPDESIGNATION'].nunique():,}")
    logger.info(f"    Scoring groups: {sorted(df['SCORINGGROUP'].unique())}")

    # Step 2b: Get QGD-to-question_id mapping
    if target == 'supabase':
        result = db.client.table('questions').select('id, source_id').not_.is_('source_id', 'null').execute()
        qgd_to_id = {r['source_id']: r['id'] for r in result.data}
    else:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, source_id FROM questions WHERE source_id IS NOT NULL")
        qgd_to_id = {row["source_id"]: row["id"] for row in cursor.fetchall()}
        conn.close()

    logger.info(f"    Questions in DB: {len(qgd_to_id)}")

    # Filter Excel to only our QGDs
    db_qgds = set(qgd_to_id.keys())
    df_ours = df[df['QUESTIONGROUPDESIGNATION'].isin(db_qgds)].copy()
    logger.info(f"    Excel rows matching our QGDs: {len(df_ours):,}")

    # Step 2c: Clear performance tables
    if not dry_run:
        logger.info(f"\n  Clearing performance tables...")
        if target == 'supabase':
            db.clear_performance_data()
        else:
            conn = sqlite3.connect(str(DB_PATH))
            cursor = conn.cursor()
            cursor.execute("DELETE FROM demographic_performance")
            cursor.execute("DELETE FROM question_activities")
            cursor.execute("DELETE FROM performance")
            cursor.execute("DELETE FROM activities")
            conn.commit()
            conn.close()
        logger.info(f"    Performance tables cleared")
    else:
        logger.info(f"\n  [DRY RUN] Would clear performance tables")

    # Step 2d: Aggregate performance per QGD x SCORINGGROUP
    logger.info(f"\n  Computing aggregated performance by segment...")
    perf_agg = df_ours.groupby(['QUESTIONGROUPDESIGNATION', 'SCORINGGROUP']).agg(
        pre_calc=('PRESCORECALC', 'sum'),
        pre_n=('PRESCOREN', 'sum'),
        post_calc=('POSTSCORECALC', 'sum'),
        post_n=('POSTSCOREN', 'sum'),
    ).reset_index()

    # Compute percentages
    perf_agg['pre_score'] = perf_agg.apply(
        lambda r: round(r['pre_calc'] / r['pre_n'] * 100, 2) if r['pre_n'] > 0 else None, axis=1
    )
    perf_agg['post_score'] = perf_agg.apply(
        lambda r: round(r['post_calc'] / r['post_n'] * 100, 2) if r['post_n'] > 0 else None, axis=1
    )

    # Build performance rows
    perf_rows = []
    perf_skipped = 0
    for _, row in perf_agg.iterrows():
        qgd = int(row['QUESTIONGROUPDESIGNATION'])
        question_id = qgd_to_id.get(qgd)
        if not question_id:
            continue
        segment = SEGMENT_MAP.get(row['SCORINGGROUP'])
        if not segment:
            perf_skipped += 1
            continue
        perf_rows.append({
            'question_id': question_id,
            'segment': segment,
            'pre_score': row['pre_score'],
            'post_score': row['post_score'],
            'pre_n': int(row['pre_n']),
            'post_n': int(row['post_n']),
        })

    # Insert performance rows
    if not dry_run:
        if target == 'supabase':
            db.insert_performance_batch(perf_rows)
        else:
            conn = sqlite3.connect(str(DB_PATH))
            cursor = conn.cursor()
            for pr in perf_rows:
                cursor.execute("""
                    INSERT OR REPLACE INTO performance
                    (question_id, segment, pre_score, post_score, pre_n, post_n)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (pr['question_id'], pr['segment'], pr['pre_score'],
                      pr['post_score'], pr['pre_n'], pr['post_n']))
            conn.commit()
            conn.close()

    logger.info(f"    Performance rows inserted: {len(perf_rows)} (skipped unmapped: {perf_skipped})")

    # Step 2e: Create activities from unique COURSENAMEs
    logger.info(f"\n  Creating activities...")
    activities_df = df_ours.groupby('COURSENAME').agg(
        start_date=('STARTDATE', 'first'),
        quarter=('USERQUARTERDATE', 'first'),
    ).reset_index()

    activity_name_to_id = {}
    act_count = 0
    for _, row in activities_df.iterrows():
        name = str(row['COURSENAME'])
        try:
            date_val = pd.to_datetime(row['start_date']).date() if pd.notna(row['start_date']) else None
        except Exception:
            date_val = None

        if not dry_run:
            activity_id = db.upsert_activity_metadata(
                activity_name=name,
                activity_date=date_val,
            )
            if activity_id:
                activity_name_to_id[name] = activity_id
        else:
            activity_name_to_id[name] = act_count + 1
        act_count += 1

    logger.info(f"    Activities created: {act_count}")

    # Step 2f: Per-activity aggregation
    logger.info(f"\n  Computing per-activity performance...")
    activity_agg = df_ours.groupby(['QUESTIONGROUPDESIGNATION', 'COURSENAME', 'SCORINGGROUP']).agg(
        pre_calc=('PRESCORECALC', 'sum'),
        pre_n=('PRESCOREN', 'sum'),
        post_calc=('POSTSCORECALC', 'sum'),
        post_n=('POSTSCOREN', 'sum'),
        start_date=('STARTDATE', 'first'),
        quarter=('USERQUARTERDATE', 'first'),
    ).reset_index()

    # Insert question_activities (Overall segment per QGD x COURSENAME)
    overall_act = activity_agg[activity_agg['SCORINGGROUP'] == 'Overall']
    qa_count = 0
    for _, row in overall_act.iterrows():
        qgd = int(row['QUESTIONGROUPDESIGNATION'])
        question_id = qgd_to_id.get(qgd)
        if not question_id:
            continue
        course_name = str(row['COURSENAME'])
        activity_id = activity_name_to_id.get(course_name)
        try:
            date_val = pd.to_datetime(row['start_date']).date() if pd.notna(row['start_date']) else None
        except Exception:
            date_val = None
        quarter_val = str(row['quarter']) if pd.notna(row['quarter']) else None
        pre_n = int(row['pre_n'])
        post_n = int(row['post_n'])
        pre_score = round(row['pre_calc'] / pre_n * 100, 2) if pre_n > 0 else None
        post_score = round(row['post_calc'] / post_n * 100, 2) if post_n > 0 else None

        if not dry_run:
            db.insert_question_activity(
                question_id=question_id,
                activity_name=course_name,
                activity_id=activity_id,
                activity_date=date_val,
                quarter=quarter_val,
                pre_score=pre_score,
                post_score=post_score,
                pre_n=pre_n,
                post_n=post_n,
            )
        qa_count += 1

    logger.info(f"    Question-Activity links created: {qa_count}")

    # Insert demographic_performance (non-Overall segments)
    non_overall = activity_agg[activity_agg['SCORINGGROUP'] != 'Overall']
    demo_rows = []
    for _, row in non_overall.iterrows():
        qgd = int(row['QUESTIONGROUPDESIGNATION'])
        question_id = qgd_to_id.get(qgd)
        if not question_id:
            continue
        course_name = str(row['COURSENAME'])
        activity_id = activity_name_to_id.get(course_name)
        pre_n = int(row['pre_n'])
        post_n = int(row['post_n'])
        pre_score = round(row['pre_calc'] / pre_n * 100, 2) if pre_n > 0 else None
        post_score = round(row['post_calc'] / post_n * 100, 2) if post_n > 0 else None
        n_respondents = pre_n + post_n

        demo_rows.append({
            'question_id': question_id,
            'activity_id': activity_id,
            'specialty': row['SCORINGGROUP'],
            'pre_score': pre_score,
            'post_score': post_score,
            'n_respondents': n_respondents,
            'pre_n': pre_n,
            'post_n': post_n,
        })

    if not dry_run:
        if target == 'supabase':
            db.insert_demographic_performance_batch(demo_rows)
        else:
            conn = sqlite3.connect(str(DB_PATH))
            cursor = conn.cursor()
            for dr in demo_rows:
                cursor.execute("""
                    INSERT INTO demographic_performance
                    (question_id, activity_id, specialty, pre_score, post_score,
                     n_respondents, pre_n, post_n)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (dr['question_id'], dr['activity_id'], dr['specialty'],
                      dr['pre_score'], dr['post_score'], dr['n_respondents'],
                      dr['pre_n'], dr['post_n']))
            conn.commit()
            conn.close()

    logger.info(f"    Demographic performance rows created: {len(demo_rows)}")

    # Verification
    logger.info(f"\n  Verification:")
    if not dry_run:
        if target == 'supabase':
            p_count = db.client.table('performance').select('id', count='exact').execute().count
            p_overall = db.client.table('performance').select('id', count='exact').eq('segment', 'overall').execute().count
            qa_total = db.client.table('question_activities').select('id', count='exact').execute().count
            logger.info(f"    Performance rows:            {p_count}")
            logger.info(f"    Overall segment rows:        {p_overall} (expect {len(qgd_to_id)})")
            logger.info(f"    Question-Activity links:     {qa_total}")
        else:
            conn = sqlite3.connect(str(DB_PATH))
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(DISTINCT question_id) FROM performance")
            q_with_perf = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM performance WHERE segment = 'overall'")
            overall_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(DISTINCT question_id) FROM question_activities")
            q_with_act = cursor.fetchone()[0]
            cursor.execute("""
                SELECT COUNT(*) FROM demographic_performance dp
                LEFT JOIN activities a ON dp.activity_id = a.id
                WHERE a.id IS NULL
            """)
            orphaned = cursor.fetchone()[0]

            logger.info(f"    Questions with performance data: {q_with_perf} (expect {len(qgd_to_id)})")
            logger.info(f"    Questions with 'overall' segment: {overall_count} (expect {len(qgd_to_id)})")
            logger.info(f"    Questions with activity links:    {q_with_act}")
            logger.info(f"    Orphaned demographic_perf FKs:    {orphaned} (expect 0)")
            conn.close()

    return {
        "performance_rows": len(perf_rows),
        "activities_created": act_count,
        "question_activity_links": qa_count,
        "demographic_performance_rows": len(demo_rows),
    }


# ============================================================
# Phase 3: Sync to Supabase
# ============================================================

def phase_3_sync_supabase(dry_run=False):
    """Sync corrected data to Supabase."""
    logger.info("")
    logger.info("=" * 70)
    logger.info("PHASE 3: Sync to Supabase")
    logger.info("=" * 70)

    import os
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")

    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_KEY')

    if not url or not key:
        logger.warning("  Supabase credentials not found. Skipping sync.")
        return {"skipped": True}

    from supabase import create_client
    client = create_client(url, key)

    # Import migration helpers
    from scripts.migrate_to_supabase import clean_row

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    # Step 3a: Clear performance-related tables in Supabase (children first)
    clear_order = ['demographic_performance', 'question_activities', 'performance', 'activities']
    for table in clear_order:
        if not dry_run:
            try:
                result = client.table(table).delete().gt('id', 0).execute()
                logger.info(f"  Cleared Supabase table: {table}")
            except Exception as e:
                logger.warning(f"  Could not clear {table}: {e}")
        else:
            logger.info(f"  [DRY RUN] Would clear Supabase table: {table}")

    # Step 3b: Sync each table
    BATCH_SIZE = 100
    total_synced = 0

    for table_name in SUPABASE_SYNC_TABLES:
        logger.info(f"\n  Syncing: {table_name}")

        cursor = conn.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()

        if not rows:
            logger.info(f"    0 rows (skipping)")
            continue

        # Clean rows for PostgreSQL
        cleaned_rows = []
        for row in rows:
            row_dict = dict(row)
            cleaned = clean_row(row_dict, table_name)
            cleaned_rows.append(cleaned)

        if dry_run:
            logger.info(f"    [DRY RUN] Would sync {len(cleaned_rows)} rows")
            total_synced += len(cleaned_rows)
            continue

        # Batch upsert
        synced = 0
        for i in range(0, len(cleaned_rows), BATCH_SIZE):
            batch = cleaned_rows[i:i + BATCH_SIZE]
            try:
                client.table(table_name).upsert(batch).execute()
                synced += len(batch)
            except Exception as e:
                logger.error(f"    Batch {i // BATCH_SIZE + 1} failed: {e}")
                # Log first row of failing batch for debugging
                if batch:
                    logger.error(f"    Sample row keys: {list(batch[0].keys())}")
                raise

        logger.info(f"    Synced: {synced} rows")
        total_synced += synced

    # Step 3c: Verify counts
    logger.info(f"\n  Verification (SQLite vs Supabase):")
    for table_name in SUPABASE_SYNC_TABLES:
        cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
        sqlite_count = cursor.fetchone()[0]

        if not dry_run:
            try:
                pk = 'question_id' if table_name == 'tags' else 'id'
                result = client.table(table_name).select(pk, count='exact').execute()
                sb_count = result.count
                match = "OK" if sqlite_count == sb_count else "MISMATCH"
                logger.info(f"    {table_name}: SQLite={sqlite_count}, Supabase={sb_count} [{match}]")
            except Exception as e:
                logger.warning(f"    {table_name}: SQLite={sqlite_count}, Supabase=ERROR ({e})")
        else:
            logger.info(f"    {table_name}: SQLite={sqlite_count}")

    conn.close()
    return {"total_synced": total_synced}


# ============================================================
# Phase 4: Final Validation Report
# ============================================================

def phase_4_validate(dry_run=False, target='sqlite'):
    """Produce comprehensive validation report."""
    logger.info("")
    logger.info("=" * 70)
    logger.info(f"PHASE 4: Final Validation Report (target={target})")
    logger.info("=" * 70)

    if target == 'supabase':
        _phase_4_validate_supabase()
    else:
        _phase_4_validate_sqlite()

    logger.info(f"\n{'=' * 70}")
    logger.info("OVERHAUL COMPLETE")
    logger.info(f"{'=' * 70}")


def _phase_4_validate_supabase():
    """Validation report against Supabase."""
    from dashboard.backend.services.import_service import get_import_db
    db = get_import_db('supabase')

    # Tag completeness by disease
    logger.info(f"\n  Tag completeness by disease:")
    result = db.client.table('tags').select(
        'disease_state, agreement_level, worst_case_agreement, cme_outcome_level'
    ).execute()
    from collections import Counter, defaultdict
    disease_stats = defaultdict(lambda: {'total': 0, 'agree': 0, 'worst': 0, 'cme': 0})
    for row in result.data:
        ds = row.get('disease_state') or 'Unknown'
        disease_stats[ds]['total'] += 1
        if row.get('agreement_level') is not None:
            disease_stats[ds]['agree'] += 1
        if row.get('worst_case_agreement') is not None:
            disease_stats[ds]['worst'] += 1
        if row.get('cme_outcome_level') is not None:
            disease_stats[ds]['cme'] += 1

    logger.info(f"    {'Disease':<25} {'Total':>5} {'Agree%':>7} {'Worst%':>7} {'CME%':>7}")
    logger.info(f"    {'-'*25} {'-'*5} {'-'*7} {'-'*7} {'-'*7}")
    for disease in sorted(disease_stats, key=lambda d: disease_stats[d]['total'], reverse=True):
        s = disease_stats[disease]
        total = s['total']
        logger.info(f"    {disease:<25} {total:>5} "
                     f"{s['agree'] * 100 // total:>6}% "
                     f"{s['worst'] * 100 // total:>6}% "
                     f"{s['cme'] * 100 // total:>6}%")

    # Performance coverage
    logger.info(f"\n  Performance coverage:")
    q_count = db.client.table('questions').select('id', count='exact').execute().count
    p_overall = db.client.table('performance').select('id', count='exact').eq('segment', 'overall').execute().count
    logger.info(f"    Total questions:          {q_count}")
    logger.info(f"    With performance (overall): {p_overall} ({p_overall * 100 // q_count if q_count else 0}%)")

    # Overall summary
    total_perf = db.client.table('performance').select('id', count='exact').execute().count
    total_qa = db.client.table('question_activities').select('id', count='exact').execute().count
    total_dp = db.client.table('demographic_performance').select('id', count='exact').execute().count
    total_act = db.client.table('activities').select('id', count='exact').execute().count
    total_tags = db.client.table('tags').select('question_id', count='exact').execute().count
    tags_with_agree = db.client.table('tags').select('question_id', count='exact').not_.is_('agreement_level', 'null').execute().count

    logger.info(f"\n  Final database state:")
    logger.info(f"    Performance rows:         {total_perf}")
    logger.info(f"    Question-Activities:       {total_qa}")
    logger.info(f"    Demographic Performance:  {total_dp}")
    logger.info(f"    Activities:               {total_act}")
    logger.info(f"    Tags with agreement:      {tags_with_agree}/{total_tags} ({tags_with_agree * 100 // total_tags if total_tags else 0}%)")


def _phase_4_validate_sqlite():
    """Validation report against SQLite."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # Tag completeness by disease
    logger.info(f"\n  Tag completeness by disease:")
    cursor.execute("""
        SELECT t.disease_state,
               COUNT(*) as total,
               SUM(CASE WHEN t.agreement_level IS NOT NULL THEN 1 ELSE 0 END) as has_agreement,
               SUM(CASE WHEN t.worst_case_agreement IS NOT NULL THEN 1 ELSE 0 END) as has_worst,
               SUM(CASE WHEN t.cme_outcome_level IS NOT NULL THEN 1 ELSE 0 END) as has_cme
        FROM tags t
        JOIN questions q ON t.question_id = q.id
        GROUP BY t.disease_state
        ORDER BY COUNT(*) DESC
    """)
    logger.info(f"    {'Disease':<25} {'Total':>5} {'Agree%':>7} {'Worst%':>7} {'CME%':>7}")
    logger.info(f"    {'-'*25} {'-'*5} {'-'*7} {'-'*7} {'-'*7}")
    for row in cursor.fetchall():
        disease, total, agree, worst, cme = row
        logger.info(f"    {disease:<25} {total:>5} "
                     f"{agree * 100 // total:>6}% "
                     f"{worst * 100 // total:>6}% "
                     f"{cme * 100 // total:>6}%")

    # Performance coverage
    logger.info(f"\n  Performance coverage:")
    cursor.execute("""
        SELECT COUNT(*) as total,
               SUM(CASE WHEN p.question_id IS NOT NULL THEN 1 ELSE 0 END) as has_perf
        FROM questions q
        LEFT JOIN performance p ON q.id = p.question_id AND p.segment = 'overall'
    """)
    total, has_perf = cursor.fetchone()
    logger.info(f"    Total questions:          {total}")
    logger.info(f"    With performance (overall): {has_perf} ({has_perf * 100 // total}%)")

    # FK integrity
    logger.info(f"\n  FK integrity:")
    cursor.execute("""
        SELECT COUNT(*) FROM demographic_performance dp
        LEFT JOIN activities a ON dp.activity_id = a.id
        WHERE a.id IS NULL AND dp.activity_id IS NOT NULL
    """)
    orphaned = cursor.fetchone()[0]
    logger.info(f"    Orphaned demographic_perf activity FKs: {orphaned}")

    # Review queue check
    logger.info(f"\n  Review queue:")
    cursor.execute("""
        SELECT t.disease_state, COUNT(*) FROM tags t
        JOIN questions q ON t.question_id = q.id
        WHERE t.needs_review = 1
        AND (t.edited_by_user IS NULL OR t.edited_by_user = 0)
        AND (q.is_oncology IS NULL OR q.is_oncology = 1)
        AND (q.canonical_source_id IS NULL OR q.canonical_source_id = CAST(q.source_id AS TEXT))
        AND q.id NOT IN (SELECT question_id FROM data_error_questions)
        GROUP BY t.disease_state
        ORDER BY COUNT(*) DESC
    """)
    for row in cursor.fetchall():
        logger.info(f"    {row[0]}: {row[1]} questions needing review")

    # Overall summary
    cursor.execute("SELECT COUNT(*) FROM performance")
    total_perf = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM question_activities")
    total_qa = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM demographic_performance")
    total_dp = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM activities")
    total_act = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tags WHERE agreement_level IS NOT NULL")
    total_agree = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tags")
    total_tags = cursor.fetchone()[0]

    logger.info(f"\n  Final database state:")
    logger.info(f"    Performance rows:         {total_perf}")
    logger.info(f"    Question-Activities:       {total_qa}")
    logger.info(f"    Demographic Performance:  {total_dp}")
    logger.info(f"    Activities:               {total_act}")
    logger.info(f"    Tags with agreement:      {total_agree}/{total_tags} ({total_agree * 100 // total_tags}%)")

    conn.close()


# ============================================================
# Main Entry Point
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Comprehensive Data Overhaul")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    parser.add_argument("--phase", type=str, default="0,1,2,3,4",
                        help="Comma-separated phases to run (default: 0,1,2,3,4)")
    parser.add_argument("--skip-supabase", action="store_true", help="Skip Phase 3 (Supabase sync)")
    parser.add_argument("--target", type=str, choices=["sqlite", "supabase"],
                        default=os.environ.get("IMPORT_TARGET", "supabase"),
                        help="Write target: supabase (default) or sqlite. Override with IMPORT_TARGET env var.")
    parser.add_argument("--verbose", action="store_true", help="Detailed logging")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    phases = [int(p.strip()) for p in args.phase.split(",")]

    # When target=supabase, Phase 3 (SQLite→Supabase sync) is unnecessary
    skip_supabase_sync = args.skip_supabase or args.target == 'supabase'

    logger.info("=" * 70)
    logger.info("COMPREHENSIVE DATA OVERHAUL")
    logger.info(f"  Target: {args.target}")
    logger.info(f"  Phases: {phases}")
    logger.info(f"  Dry run: {args.dry_run}")
    logger.info(f"  Skip Supabase sync: {skip_supabase_sync}")
    logger.info("=" * 70)

    try:
        if 0 in phases:
            phase_0_backup(dry_run=args.dry_run)

        if 1 in phases:
            phase_1_reimport_tags(dry_run=args.dry_run, target=args.target)

        if 2 in phases:
            phase_2_rebuild_performance(dry_run=args.dry_run, verbose=args.verbose, target=args.target)

        if 3 in phases and not skip_supabase_sync:
            phase_3_sync_supabase(dry_run=args.dry_run)

        if 4 in phases:
            phase_4_validate(dry_run=args.dry_run, target=args.target)

    except Exception as e:
        logger.error(f"\nFATAL ERROR: {e}")
        logger.error("The database backup from Phase 0 can be used to restore.")
        raise


if __name__ == "__main__":
    main()
