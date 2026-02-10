"""
Migrate data from local SQLite database to Supabase PostgreSQL.

Reads all tables from dashboard/data/questions.db and writes them to Supabase
using the service role key (bypasses RLS).

Usage:
    # Dry run (read counts, don't write)
    python scripts/migrate_to_supabase.py --dry-run

    # Full migration
    python scripts/migrate_to_supabase.py

    # Migrate specific tables only
    python scripts/migrate_to_supabase.py --tables questions,tags,performance

Environment variables required:
    SUPABASE_URL         - Your Supabase project URL
    SUPABASE_SERVICE_KEY - Service role key (bypasses RLS)
"""

import sys
import os
import json
import sqlite3
import argparse
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Project root
PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "dashboard" / "data" / "questions.db"

# Batch size for inserts
BATCH_SIZE = 100

# Tables in dependency order (parents before children)
TABLE_ORDER = [
    "questions",
    "tags",
    "performance",
    "activities",
    "question_activities",
    "demographic_performance",
    "novel_entities",
    "novel_entity_occurrences",
    "user_defined_values",
    "data_error_questions",
    "duplicate_clusters",
    "cluster_members",
    "duplicate_decisions",
    "tag_proposals",
    "tag_proposal_candidates",
]


def get_sqlite_connection() -> sqlite3.Connection:
    """Open SQLite database with row factory."""
    if not DB_PATH.exists():
        logger.error(f"SQLite database not found: {DB_PATH}")
        sys.exit(1)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def get_supabase_client():
    """Create Supabase client with service role key."""
    try:
        from supabase import create_client
    except ImportError:
        logger.error("supabase-py not installed. Run: pip install supabase")
        sys.exit(1)

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")

    if not url or not key:
        logger.error(
            "Missing environment variables. Set SUPABASE_URL and SUPABASE_SERVICE_KEY.\n"
            "  SUPABASE_URL = https://your-project.supabase.co\n"
            "  SUPABASE_SERVICE_KEY = your service_role key (from Supabase dashboard > Settings > API)"
        )
        sys.exit(1)

    return create_client(url, key)


def get_table_columns(conn: sqlite3.Connection, table_name: str) -> list:
    """Get column names for a table."""
    cursor = conn.execute(f"PRAGMA table_info({table_name})")
    return [row["name"] for row in cursor.fetchall()]


def read_table(conn: sqlite3.Connection, table_name: str) -> list:
    """Read all rows from a SQLite table as dicts."""
    try:
        cursor = conn.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.OperationalError as e:
        logger.warning(f"Could not read table {table_name}: {e}")
        return []


def clean_row(row: dict, table_name: str) -> dict:
    """Clean a row for PostgreSQL insertion.

    - Remove 'id' for SERIAL tables (let Postgres auto-assign)
    - Convert SQLite booleans (0/1) to Python booleans
    - Handle None vs empty string
    """
    cleaned = {}
    # Tables where we want to preserve the original ID for FK references
    preserve_id_tables = {"questions"}

    for key, value in row.items():
        # Skip auto-increment id for most tables
        if key == "id" and table_name not in preserve_id_tables:
            continue

        # For questions table, keep id to maintain FK relationships
        # (tags.question_id, performance.question_id, etc. reference questions.id)

        # Convert SQLite integer booleans to Python booleans
        if key in ("needs_review", "edited_by_user", "is_canonical",
                    "flaw_absolute_terms", "flaw_grammatical_cue",
                    "flaw_implausible_distractor", "flaw_clang_association",
                    "flaw_convergence_vulnerability", "flaw_double_negative"):
            if value is not None:
                value = bool(value)

        cleaned[key] = value

    return cleaned


def migrate_table(supabase, conn: sqlite3.Connection, table_name: str, dry_run: bool = False):
    """Migrate a single table from SQLite to Supabase."""
    rows = read_table(conn, table_name)

    if not rows:
        logger.info(f"  {table_name}: 0 rows (skipping)")
        return 0

    logger.info(f"  {table_name}: {len(rows)} rows to migrate")

    if dry_run:
        return len(rows)

    # Clean rows for PostgreSQL
    cleaned_rows = [clean_row(row, table_name) for row in rows]

    # Batch insert
    inserted = 0
    for i in range(0, len(cleaned_rows), BATCH_SIZE):
        batch = cleaned_rows[i:i + BATCH_SIZE]
        try:
            result = supabase.table(table_name).upsert(batch).execute()
            inserted += len(batch)
            if (i + BATCH_SIZE) % 500 == 0 or i + BATCH_SIZE >= len(cleaned_rows):
                logger.info(f"    {table_name}: {inserted}/{len(cleaned_rows)} rows")
        except Exception as e:
            logger.error(f"    {table_name}: Error at batch {i//BATCH_SIZE}: {e}")
            # Log first row of failing batch for debugging
            if batch:
                logger.error(f"    First row keys: {list(batch[0].keys())}")
            raise

    return inserted


def verify_migration(supabase, conn: sqlite3.Connection, tables: list):
    """Verify row counts match between SQLite and Supabase."""
    logger.info("\n=== VERIFICATION ===")
    all_match = True

    for table_name in tables:
        # SQLite count
        try:
            sqlite_count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        except sqlite3.OperationalError:
            sqlite_count = 0

        # Supabase count
        try:
            result = supabase.table(table_name).select("*", count="exact").limit(0).execute()
            pg_count = result.count
        except Exception as e:
            logger.warning(f"  {table_name}: Could not verify Supabase count: {e}")
            pg_count = "ERROR"

        match = "OK" if sqlite_count == pg_count else "MISMATCH"
        if sqlite_count != pg_count:
            all_match = False

        logger.info(f"  {table_name}: SQLite={sqlite_count}, Supabase={pg_count} [{match}]")

    if all_match:
        logger.info("\nAll tables match!")
    else:
        logger.warning("\nSome tables have mismatched counts. Review above.")

    return all_match


def main():
    parser = argparse.ArgumentParser(description="Migrate SQLite data to Supabase")
    parser.add_argument("--dry-run", action="store_true", help="Read counts only, don't write")
    parser.add_argument("--tables", type=str, help="Comma-separated list of tables to migrate")
    parser.add_argument("--verify-only", action="store_true", help="Only verify existing migration")
    args = parser.parse_args()

    # Determine which tables to migrate
    if args.tables:
        tables = [t.strip() for t in args.tables.split(",")]
    else:
        tables = TABLE_ORDER

    # Connect to SQLite
    conn = get_sqlite_connection()
    logger.info(f"SQLite database: {DB_PATH}")

    # Connect to Supabase
    if args.dry_run:
        logger.info("DRY RUN — reading counts only, not writing to Supabase")
        supabase = None
    else:
        supabase = get_supabase_client()
        logger.info(f"Supabase URL: {os.environ.get('SUPABASE_URL')}")

    if args.verify_only:
        if not supabase:
            supabase = get_supabase_client()
        verify_migration(supabase, conn, tables)
        conn.close()
        return

    # Migrate each table
    logger.info(f"\n=== MIGRATING {len(tables)} TABLES ===")
    total_rows = 0

    for table_name in tables:
        try:
            count = migrate_table(supabase, conn, table_name, dry_run=args.dry_run)
            total_rows += count
        except Exception as e:
            logger.error(f"Failed to migrate {table_name}: {e}")
            if not args.dry_run:
                logger.error("Migration aborted. Fix the error and re-run.")
                conn.close()
                sys.exit(1)

    logger.info(f"\n=== MIGRATION {'PREVIEW' if args.dry_run else 'COMPLETE'} ===")
    logger.info(f"Total rows: {total_rows}")

    # Verify if not dry run
    if not args.dry_run and supabase:
        # Backfill FTS vectors for migrated questions
        logger.info("\nBackfilling FTS vectors...")
        try:
            supabase.rpc("backfill_fts_vectors", {}).execute()
            logger.info("  FTS vectors backfilled successfully")
        except Exception as e:
            logger.warning(f"  FTS backfill via RPC failed (may need manual run): {e}")
            logger.info("  Run this SQL manually in Supabase SQL Editor:")
            logger.info("  UPDATE questions SET fts_vector = to_tsvector('english', "
                        "coalesce(question_stem, '') || ' ' || coalesce(correct_answer, ''));")

        verify_migration(supabase, conn, tables)

    conn.close()


if __name__ == "__main__":
    main()
