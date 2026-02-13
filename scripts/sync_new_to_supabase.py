"""
Incremental sync of new questions from SQLite to Supabase.

Only inserts questions that exist in SQLite but are MISSING from Supabase.
NEVER deletes or overwrites existing Supabase data.

Usage:
    python scripts/sync_new_to_supabase.py --dry-run
    python scripts/sync_new_to_supabase.py --disease "SCLC" --dry-run
    python scripts/sync_new_to_supabase.py --disease "SCLC"
    python scripts/sync_new_to_supabase.py --verbose
"""

import sys
import os
import sqlite3
import argparse
import logging
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Set

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

DB_PATH = PROJECT_ROOT / "dashboard" / "data" / "questions.db"

logger = logging.getLogger(__name__)

# ============================================================
# Constants
# ============================================================

BOOLEAN_FIELDS = {
    "needs_review", "edited_by_user", "is_canonical",
    "flaw_absolute_terms", "flaw_grammatical_cue",
    "flaw_implausible_distractor", "flaw_clang_association",
    "flaw_convergence_vulnerability", "flaw_double_negative",
    "is_oncology",
}

SKIP_COLUMNS = {
    "questions": {"qcore_score", "qcore_grade", "qcore_breakdown", "qcore_scored_at"},
    "tags": {"qpulse_score", "qpulse_grade", "qpulse_breakdown", "qpulse_scored_at"},
}

# Tables where we preserve the SQLite id (for FK integrity)
PRESERVE_ID_TABLES = {"questions", "activities"}


# ============================================================
# Data structures
# ============================================================

@dataclass
class QuestionBundle:
    """All data for a single question to be synced."""
    source_id: int
    question_row: Dict[str, Any]
    tags_row: Optional[Dict[str, Any]] = None
    performance_rows: List[Dict[str, Any]] = field(default_factory=list)
    question_activity_rows: List[Dict[str, Any]] = field(default_factory=list)
    demographic_perf_rows: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class SyncStats:
    """Tracks sync operation results."""
    questions_added: int = 0
    tags_added: int = 0
    performance_rows_added: int = 0
    activities_upserted: int = 0
    question_activities_added: int = 0
    demographic_perf_added: int = 0
    qcore_scored: int = 0
    skipped_existing: int = 0
    errors: int = 0
    error_details: List[str] = field(default_factory=list)


# ============================================================
# Row cleaning (from migrate_to_supabase.py pattern)
# ============================================================

def clean_row(row: dict, table_name: str) -> dict:
    """Clean a SQLite row for Supabase insertion.

    - Preserve id for questions/activities (FK references)
    - Skip columns not in Supabase schema
    - Convert SQLite integer booleans to Python booleans
    """
    cleaned = {}
    table_skip = SKIP_COLUMNS.get(table_name, set())

    for key, value in row.items():
        # Skip auto-increment id for child tables
        if key == "id" and table_name not in PRESERVE_ID_TABLES:
            continue
        # Skip columns not in Supabase
        if key in table_skip:
            continue
        # Convert SQLite 0/1 to Python booleans
        if key in BOOLEAN_FIELDS and value is not None:
            value = bool(value)
        cleaned[key] = value

    return cleaned


# ============================================================
# Phase 0: Preflight Checks
# ============================================================

def preflight_checks(sqlite_conn, supabase_client, disease_filter=None) -> dict:
    """Verify both databases are accessible and report current state."""
    logger.info("=" * 60)
    logger.info("PHASE 0: Preflight Checks")
    logger.info("=" * 60)

    # SQLite checks
    if not DB_PATH.exists():
        logger.error(f"SQLite database not found: {DB_PATH}")
        sys.exit(1)

    sqlite_q = sqlite_conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
    sqlite_t = sqlite_conn.execute("SELECT COUNT(*) FROM tags").fetchone()[0]
    logger.info(f"  SQLite: {sqlite_q} questions, {sqlite_t} tags")

    if disease_filter:
        disease_count = sqlite_conn.execute(
            """SELECT COUNT(*) FROM tags t
               JOIN questions q ON t.question_id = q.id
               WHERE t.disease_state = ?""",
            (disease_filter,)
        ).fetchone()[0]
        if disease_count == 0:
            logger.error(f"  No questions found in SQLite for disease '{disease_filter}'")
            sys.exit(1)
        logger.info(f"  SQLite {disease_filter}: {disease_count} questions")

    # Supabase checks
    try:
        sb_q = supabase_client.table('questions').select('id', count='exact').limit(0).execute().count
        sb_t = supabase_client.table('tags').select('question_id', count='exact').limit(0).execute().count
        logger.info(f"  Supabase: {sb_q} questions, {sb_t} tags")
    except Exception as e:
        logger.error(f"  Supabase connection failed: {e}")
        sys.exit(1)

    return {
        'sqlite_questions': sqlite_q,
        'sqlite_tags': sqlite_t,
        'supabase_questions': sb_q,
        'supabase_tags': sb_t,
    }


# ============================================================
# Phase 1: Compute Delta
# ============================================================

def compute_delta(sqlite_conn, supabase_client, disease_filter=None) -> Set[int]:
    """Find source_ids in SQLite that are missing from Supabase."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("PHASE 1: Computing Delta")
    logger.info("=" * 60)

    # Get SQLite source_ids
    if disease_filter:
        rows = sqlite_conn.execute(
            """SELECT DISTINCT q.source_id
               FROM questions q
               JOIN tags t ON q.id = t.question_id
               WHERE t.disease_state = ?
               AND q.source_id IS NOT NULL""",
            (disease_filter,)
        ).fetchall()
    else:
        rows = sqlite_conn.execute(
            "SELECT source_id FROM questions WHERE source_id IS NOT NULL"
        ).fetchall()
    sqlite_ids = {row[0] for row in rows}
    logger.info(f"  SQLite source_ids: {len(sqlite_ids)}")

    # Get Supabase source_ids (paginated)
    supabase_ids = set()
    page_size = 1000
    offset = 0
    while True:
        result = (supabase_client.table('questions')
                  .select('source_id')
                  .not_.is_('source_id', 'null')
                  .range(offset, offset + page_size - 1)
                  .execute())
        if not result.data:
            break
        for r in result.data:
            supabase_ids.add(r['source_id'])
        if len(result.data) < page_size:
            break
        offset += page_size
    logger.info(f"  Supabase source_ids: {len(supabase_ids)}")

    new_ids = sqlite_ids - supabase_ids
    logger.info(f"  New questions to sync: {len(new_ids)}")

    return new_ids


# ============================================================
# Phase 2: Read Question Bundles from SQLite
# ============================================================

def read_question_bundles(sqlite_conn, source_ids: Set[int]) -> List[QuestionBundle]:
    """Read all data for each new question from SQLite."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("PHASE 2: Reading Question Bundles from SQLite")
    logger.info("=" * 60)

    bundles = []
    for source_id in sorted(source_ids):
        q_row = sqlite_conn.execute(
            "SELECT * FROM questions WHERE source_id = ?", (source_id,)
        ).fetchone()
        if not q_row:
            logger.warning(f"  source_id {source_id}: not found in questions table, skipping")
            continue

        question_id = q_row['id']
        bundle = QuestionBundle(source_id=source_id, question_row=dict(q_row))

        # Tags
        t_row = sqlite_conn.execute(
            "SELECT * FROM tags WHERE question_id = ?", (question_id,)
        ).fetchone()
        if t_row:
            bundle.tags_row = dict(t_row)

        # Performance
        p_rows = sqlite_conn.execute(
            "SELECT * FROM performance WHERE question_id = ?", (question_id,)
        ).fetchall()
        bundle.performance_rows = [dict(r) for r in p_rows]

        # Question-activities
        qa_rows = sqlite_conn.execute(
            "SELECT * FROM question_activities WHERE question_id = ?", (question_id,)
        ).fetchall()
        bundle.question_activity_rows = [dict(r) for r in qa_rows]

        # Demographic performance
        dp_rows = sqlite_conn.execute(
            "SELECT * FROM demographic_performance WHERE question_id = ?", (question_id,)
        ).fetchall()
        bundle.demographic_perf_rows = [dict(r) for r in dp_rows]

        bundles.append(bundle)

    logger.info(f"  Read {len(bundles)} bundles")
    total_perf = sum(len(b.performance_rows) for b in bundles)
    total_qa = sum(len(b.question_activity_rows) for b in bundles)
    total_dp = sum(len(b.demographic_perf_rows) for b in bundles)
    logger.info(f"  Performance rows: {total_perf}")
    logger.info(f"  Question-activity links: {total_qa}")
    logger.info(f"  Demographic perf rows: {total_dp}")

    return bundles


# ============================================================
# Phase 3: Insert into Supabase
# ============================================================

def sync_bundle(supabase_client, supa_db, bundle: QuestionBundle, stats: SyncStats):
    """Sync a single question bundle to Supabase."""
    source_id = bundle.source_id
    question_id = bundle.question_row['id']

    # Safety check: verify question doesn't already exist in Supabase
    existing = supa_db.get_question_by_source_id(str(source_id))
    if existing:
        logger.debug(f"  [{source_id}] Already exists in Supabase (id={existing['id']}), skipping")
        stats.skipped_existing += 1
        return

    # Step 1: Insert question (raw upsert to preserve id)
    q_cleaned = clean_row(bundle.question_row, 'questions')
    supabase_client.table('questions').upsert(q_cleaned).execute()
    stats.questions_added += 1

    # Step 2: Insert tags (raw upsert with all fields)
    if bundle.tags_row:
        t_cleaned = clean_row(bundle.tags_row, 'tags')
        # Ensure flagged_at is set for questions needing review (drives review queue sort)
        if t_cleaned.get('needs_review') and not t_cleaned.get('flagged_at'):
            t_cleaned['flagged_at'] = datetime.utcnow().isoformat()
        supabase_client.table('tags').upsert(t_cleaned, on_conflict='question_id').execute()
        stats.tags_added += 1

    # Step 3: Calculate QCore
    if bundle.tags_row:
        try:
            result = supa_db.calculate_qcore_for_question(question_id)
            if result:
                stats.qcore_scored += 1
        except Exception as e:
            logger.warning(f"  [{source_id}] QCore failed: {e}")

    # Step 4: Upsert performance rows
    if bundle.performance_rows:
        perf_cleaned = []
        for r in bundle.performance_rows:
            cleaned = clean_row(r, 'performance')
            # Ensure only the fields the batch method expects
            perf_cleaned.append({
                'question_id': cleaned['question_id'],
                'segment': cleaned['segment'],
                'pre_score': cleaned.get('pre_score'),
                'post_score': cleaned.get('post_score'),
                'pre_n': cleaned.get('pre_n'),
                'post_n': cleaned.get('post_n'),
            })
        count = supa_db.insert_performance_batch(perf_cleaned)
        stats.performance_rows_added += count

    # Step 5 & 6: Activities and question_activities
    # Build SQLite activity_id -> Supabase activity_id mapping for demographic_performance
    sqlite_to_supabase_activity_id = {}

    for qa_row in bundle.question_activity_rows:
        activity_name = qa_row.get('activity_name')
        if not activity_name:
            continue

        sqlite_activity_id = qa_row.get('activity_id')

        # Parse activity_date
        activity_date = None
        raw_date = qa_row.get('activity_date')
        if raw_date:
            if isinstance(raw_date, str):
                try:
                    activity_date = datetime.strptime(raw_date, '%Y-%m-%d').date()
                except ValueError:
                    try:
                        activity_date = datetime.fromisoformat(raw_date).date()
                    except (ValueError, TypeError):
                        pass
            elif isinstance(raw_date, date):
                activity_date = raw_date

        # Upsert activity metadata — returns Supabase-side activity_id
        supabase_activity_id = supa_db.upsert_activity_metadata(
            activity_name=activity_name,
            activity_date=activity_date,
        )
        stats.activities_upserted += 1

        # Record the mapping for demographic_performance remapping
        if sqlite_activity_id and supabase_activity_id:
            sqlite_to_supabase_activity_id[sqlite_activity_id] = supabase_activity_id

        # Insert question_activity link
        supa_db.insert_question_activity(
            question_id=question_id,
            activity_name=activity_name,
            activity_id=supabase_activity_id,
            activity_date=activity_date,
            quarter=qa_row.get('quarter'),
            pre_score=qa_row.get('pre_score'),
            post_score=qa_row.get('post_score'),
            pre_n=qa_row.get('pre_n'),
            post_n=qa_row.get('post_n'),
        )
        stats.question_activities_added += 1

    # Step 7: Insert demographic_performance rows (with activity_id remapping)
    if bundle.demographic_perf_rows:
        dp_cleaned = []
        skipped_dp = 0
        for r in bundle.demographic_perf_rows:
            cleaned = clean_row(r, 'demographic_performance')
            # Remap SQLite activity_id to Supabase activity_id
            sqlite_aid = cleaned.get('activity_id')
            if sqlite_aid in sqlite_to_supabase_activity_id:
                cleaned['activity_id'] = sqlite_to_supabase_activity_id[sqlite_aid]
            elif sqlite_aid is not None:
                logger.warning(f"  [{source_id}] No Supabase mapping for SQLite activity_id={sqlite_aid}, skipping demographic_performance row")
                skipped_dp += 1
                continue
            dp_cleaned.append(cleaned)
        if dp_cleaned:
            count = supa_db.insert_demographic_performance_batch(dp_cleaned)
            stats.demographic_perf_added += count
        if skipped_dp:
            logger.warning(f"  [{source_id}] Skipped {skipped_dp} demographic_performance rows (unmapped activity_ids)")


def sync_all_bundles(supabase_client, supa_db, bundles: List[QuestionBundle]) -> SyncStats:
    """Sync all bundles with per-question error isolation."""
    logger.info("")
    logger.info("=" * 60)
    logger.info(f"PHASE 3: Syncing {len(bundles)} Questions to Supabase")
    logger.info("=" * 60)

    stats = SyncStats()
    for i, bundle in enumerate(bundles, 1):
        try:
            sync_bundle(supabase_client, supa_db, bundle, stats)
            if i % 25 == 0 or i == len(bundles):
                logger.info(f"  Progress: {i}/{len(bundles)} ({stats.questions_added} added, {stats.errors} errors)")
        except Exception as e:
            stats.errors += 1
            error_msg = f"source_id={bundle.source_id}: {e}"
            stats.error_details.append(error_msg)
            logger.error(f"  [{i}/{len(bundles)}] ERROR {error_msg}")

    return stats


# ============================================================
# Phase 4: Post-flight Verification
# ============================================================

def postflight_checks(supabase_client, pre_counts: dict, stats: SyncStats, new_source_ids: Set[int]):
    """Verify sync results."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("PHASE 4: Post-flight Verification")
    logger.info("=" * 60)

    post_q = supabase_client.table('questions').select('id', count='exact').limit(0).execute().count
    post_t = supabase_client.table('tags').select('question_id', count='exact').limit(0).execute().count

    expected_q = pre_counts['supabase_questions'] + stats.questions_added
    expected_t = pre_counts['supabase_tags'] + stats.tags_added

    q_ok = post_q == expected_q
    t_ok = post_t == expected_t

    logger.info(f"  Questions: {post_q} (expected {expected_q}) {'OK' if q_ok else 'MISMATCH!'}")
    logger.info(f"  Tags:      {post_t} (expected {expected_t}) {'OK' if t_ok else 'MISMATCH!'}")

    # Spot-check new source_ids
    sample = sorted(list(new_source_ids))[:5]
    for sid in sample:
        try:
            result = (supabase_client.table('questions')
                      .select('id, source_id')
                      .eq('source_id', sid)
                      .execute())
            found = len(result.data) > 0
            status = "FOUND" if found else "MISSING!"
            logger.info(f"  Spot check source_id={sid}: {status}")
        except Exception as e:
            logger.warning(f"  Spot check source_id={sid}: query failed ({e})")

    # Backfill FTS vectors
    try:
        supabase_client.rpc("backfill_fts_vectors", {}).execute()
        logger.info("  FTS vectors backfilled")
    except Exception as e:
        logger.warning(f"  FTS backfill failed (non-critical): {e}")


# ============================================================
# Summary
# ============================================================

def print_summary(stats: SyncStats, bundles: List[QuestionBundle]):
    """Print human-readable summary."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("SYNC SUMMARY")
    logger.info("=" * 60)
    logger.info(f"  Questions added:         {stats.questions_added}")
    logger.info(f"  Tags added:              {stats.tags_added}")
    logger.info(f"  QCore scored:            {stats.qcore_scored}")
    logger.info(f"  Performance rows:        {stats.performance_rows_added}")
    logger.info(f"  Activities upserted:     {stats.activities_upserted}")
    logger.info(f"  Question-activity links: {stats.question_activities_added}")
    logger.info(f"  Demographic perf rows:   {stats.demographic_perf_added}")
    logger.info(f"  Skipped (already exist): {stats.skipped_existing}")
    logger.info(f"  Errors:                  {stats.errors}")

    if stats.error_details:
        logger.info("")
        logger.info("  Errors:")
        for err in stats.error_details:
            logger.info(f"    - {err}")

    # Per-disease breakdown
    disease_counts = {}
    for b in bundles:
        disease = b.tags_row.get('disease_state', 'Unknown') if b.tags_row else 'No tags'
        disease_counts[disease] = disease_counts.get(disease, 0) + 1
    if disease_counts:
        logger.info("")
        logger.info("  Per-disease breakdown:")
        for disease, count in sorted(disease_counts.items()):
            logger.info(f"    {disease}: {count}")

    logger.info("=" * 60)


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Sync new questions from SQLite to Supabase (incremental, non-destructive)"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview what would be synced, no writes")
    parser.add_argument("--disease", type=str, default=None,
                        help="Only sync questions for this disease state")
    parser.add_argument("--verbose", action="store_true",
                        help="Enable debug-level logging")
    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Suppress noisy HTTP debug logs even in verbose mode
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("hpack").setLevel(logging.WARNING)

    logger.info("=== Incremental Supabase Sync ===")
    logger.info(f"  Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    if args.disease:
        logger.info(f"  Disease filter: {args.disease}")

    # Connect SQLite
    sqlite_conn = sqlite3.connect(str(DB_PATH))
    sqlite_conn.row_factory = sqlite3.Row

    # Connect Supabase
    from supabase import create_client
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        logger.error("Set SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables")
        sys.exit(1)

    supabase_client = create_client(url, key)

    from dashboard.backend.services.supabase_db import SupabaseDatabaseService
    supa_db = SupabaseDatabaseService(url, key)

    # Phase 0: Preflight
    pre_counts = preflight_checks(sqlite_conn, supabase_client, args.disease)

    # Phase 1: Compute delta
    new_ids = compute_delta(sqlite_conn, supabase_client, args.disease)

    if not new_ids:
        logger.info("")
        logger.info("No new questions to sync. Databases are in sync.")
        sqlite_conn.close()
        return

    # Phase 2: Read bundles
    bundles = read_question_bundles(sqlite_conn, new_ids)
    sqlite_conn.close()

    if not bundles:
        logger.info("No bundles to sync after reading.")
        return

    # Dry-run report
    if args.dry_run:
        total_perf = sum(len(b.performance_rows) for b in bundles)
        total_qa = sum(len(b.question_activity_rows) for b in bundles)
        total_dp = sum(len(b.demographic_perf_rows) for b in bundles)

        logger.info("")
        logger.info("=== DRY RUN REPORT ===")
        logger.info(f"  Questions to add:        {len(bundles)}")
        logger.info(f"  Tags to add:             {sum(1 for b in bundles if b.tags_row)}")
        logger.info(f"  Performance rows:        {total_perf}")
        logger.info(f"  Question-activity links: {total_qa}")
        logger.info(f"  Demographic perf rows:   {total_dp}")

        disease_counts = {}
        for b in bundles:
            d = b.tags_row.get('disease_state', 'Unknown') if b.tags_row else 'No tags'
            disease_counts[d] = disease_counts.get(d, 0) + 1
        logger.info("")
        logger.info("  Per-disease breakdown:")
        for disease, count in sorted(disease_counts.items()):
            logger.info(f"    {disease}: {count}")

        logger.info("")
        logger.info("[DRY RUN] No data was written to Supabase.")
        return

    # Phase 3: Sync
    stats = sync_all_bundles(supabase_client, supa_db, bundles)

    # Phase 4: Post-flight
    postflight_checks(supabase_client, pre_counts, stats, new_ids)

    # Summary
    print_summary(stats, bundles)


if __name__ == "__main__":
    main()
