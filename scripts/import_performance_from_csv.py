"""
Import performance data from Multispecialty CSV into Supabase performance table.

Reads a CSV performance export, aggregates by QGD + SCORINGGROUP (summing counts
across monthly rows), computes pre/post percentages, matches QGDs to existing
Supabase questions, and upserts into the performance table.

Reuses safe_pct, safe_float, safe_int, and SEGMENT_MAP from import_performance_data.py.

Usage:
    python scripts/import_performance_from_csv.py --dry-run --limit 50
    python scripts/import_performance_from_csv.py
    python scripts/import_performance_from_csv.py --file data/imports/other.csv
"""

import io
import sys
import argparse
import logging
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from import_performance_data import safe_pct, safe_float, safe_int, SEGMENT_MAP

DEFAULT_CSV = PROJECT_ROOT / "data" / "imports" / "Multispecialty_2026-03-17-1244.csv"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def get_supabase_question_map():
    """Paginate through all Supabase questions, return {source_id: question_id}."""
    from supabase import create_client
    import os

    client = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_KEY"],
    )

    qgd_to_id = {}
    page_size = 1000
    offset = 0
    while True:
        result = (client.table('questions')
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

    return qgd_to_id, client


def main():
    parser = argparse.ArgumentParser(
        description="Import performance data from Multispecialty CSV into Supabase"
    )
    parser.add_argument("--dry-run", action="store_true", help="Show stats without writing")
    parser.add_argument("--file", type=Path, default=DEFAULT_CSV, help="CSV file path")
    parser.add_argument("--limit", type=int, default=None, help="Process only first N unique QGDs")
    args = parser.parse_args()

    csv_path = args.file
    logger.info("=" * 60)
    logger.info("IMPORT PERFORMANCE FROM CSV")
    logger.info(f"  File:    {csv_path.name}")
    logger.info(f"  Limit:   {args.limit or 'all'}")
    logger.info(f"  Dry run: {args.dry_run}")
    logger.info("=" * 60)

    if not csv_path.exists():
        logger.error(f"CSV file not found: {csv_path}")
        sys.exit(1)

    # --- Step 1: Load CSV ---
    logger.info("\nLoading CSV...")
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    logger.info(f"  Total rows: {len(df):,}")

    required = ["QUESTIONGROUPDESIGNATION", "SCORINGGROUP",
                 "PRESCORECALC", "PRESCOREN", "POSTSCORECALC", "POSTSCOREN"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        logger.error(f"Missing required columns: {missing}")
        logger.info(f"  Available columns: {list(df.columns)}")
        sys.exit(1)

    unique_qgds = df["QUESTIONGROUPDESIGNATION"].nunique()
    logger.info(f"  Unique QGDs: {unique_qgds:,}")

    if args.limit:
        keep_qgds = df["QUESTIONGROUPDESIGNATION"].drop_duplicates().head(args.limit).tolist()
        df = df[df["QUESTIONGROUPDESIGNATION"].isin(keep_qgds)].copy()
        logger.info(f"  Limited to first {args.limit} QGDs ({len(df):,} rows)")

    # --- Step 2: Fetch Supabase question mapping ---
    logger.info("\nFetching Supabase question mapping...")
    qgd_to_id, client = get_supabase_question_map()
    logger.info(f"  Supabase questions with source_id: {len(qgd_to_id)}")

    # --- Step 3: Filter to matched QGDs ---
    db_qgds = set(qgd_to_id.keys())
    csv_qgds = set(df["QUESTIONGROUPDESIGNATION"].unique())
    matched_qgds = csv_qgds & db_qgds
    unmatched_qgds = csv_qgds - db_qgds

    df_matched = df[df["QUESTIONGROUPDESIGNATION"].isin(matched_qgds)].copy()
    logger.info(f"  Matched QGDs: {len(matched_qgds)}")
    logger.info(f"  Unmatched QGDs: {len(unmatched_qgds)} (non-eye-care, expected)")
    logger.info(f"  Matched CSV rows: {len(df_matched):,}")

    if df_matched.empty:
        logger.warning("No matching rows found. Nothing to import.")
        return

    # --- Step 4: Aggregate by QGD + SCORINGGROUP ---
    logger.info("\nAggregating performance data...")
    perf_agg = df_matched.groupby(["QUESTIONGROUPDESIGNATION", "SCORINGGROUP"]).agg(
        pre_calc=("PRESCORECALC", "sum"),
        pre_n=("PRESCOREN", "sum"),
        post_calc=("POSTSCORECALC", "sum"),
        post_n=("POSTSCOREN", "sum"),
    ).reset_index()

    perf_agg["pre_score"] = perf_agg.apply(
        lambda r: safe_pct(r["pre_calc"], r["pre_n"]), axis=1
    )
    perf_agg["post_score"] = perf_agg.apply(
        lambda r: safe_pct(r["post_calc"], r["post_n"]), axis=1
    )

    # --- Step 5: Build performance rows ---
    perf_rows = []
    skipped_segments = 0
    stats = {"with_pre_post": 0, "post_only": 0}

    for _, row in perf_agg.iterrows():
        qgd = int(row["QUESTIONGROUPDESIGNATION"])
        question_id = qgd_to_id.get(qgd)
        if not question_id:
            continue

        segment = SEGMENT_MAP.get(row["SCORINGGROUP"])
        if not segment:
            skipped_segments += 1
            continue

        pre = safe_float(row["pre_score"])
        post = safe_float(row["post_score"])

        if pre is not None and post is not None:
            stats["with_pre_post"] += 1
        elif post is not None:
            stats["post_only"] += 1

        perf_rows.append({
            "question_id": question_id,
            "segment": segment,
            "pre_score": pre,
            "post_score": post,
            "pre_n": safe_int(row["pre_n"]),
            "post_n": safe_int(row["post_n"]),
        })

    logger.info(f"  Aggregated groups: {len(perf_agg)}")
    logger.info(f"  Performance rows to upsert: {len(perf_rows)}")
    if skipped_segments:
        logger.info(f"  Skipped unmapped segments: {skipped_segments}")

    # --- Summary ---
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Total CSV rows:            {len(df):,}")
    print(f"  Unique QGDs (after limit): {len(csv_qgds)}")
    print(f"  Matched to Supabase:       {len(matched_qgds)}")
    print(f"  With both pre+post scores: {stats['with_pre_post']}")
    print(f"  With post-only (no pre):   {stats['post_only']}")
    print(f"  Unmatched (non-eye-care):  {len(unmatched_qgds)}")
    print(f"  Performance rows to write: {len(perf_rows)}")

    # Sample output
    if perf_rows:
        print(f"\n--- Sample (up to 5 matched questions) ---")
        for pr in perf_rows[:5]:
            delta = None
            if pr["pre_score"] is not None and pr["post_score"] is not None:
                delta = round(pr["post_score"] - pr["pre_score"], 2)
            delta_str = f"{delta:+.2f}pp" if delta is not None else "N/A"
            print(f"  qid={pr['question_id']:>5}  segment={pr['segment']:<10}"
                  f"  pre={pr['pre_score'] or 'N/A':>7}  post={pr['post_score'] or 'N/A':>7}"
                  f"  delta={delta_str:>10}  pre_n={pr['pre_n']:>5}  post_n={pr['post_n']:>5}")

    if args.dry_run:
        scored = [pr for pr in perf_rows
                  if pr["pre_score"] is not None and pr["post_score"] is not None]
        if scored:
            scored.sort(key=lambda r: r["post_score"] - r["pre_score"], reverse=True)
            print(f"\n--- Top 5 Improvers (by delta) ---")
            for pr in scored[:5]:
                d = round(pr["post_score"] - pr["pre_score"], 2)
                print(f"  qid={pr['question_id']:>5}  pre={pr['pre_score']:6.2f}%"
                      f"  post={pr['post_score']:6.2f}%  delta={d:+.2f}pp"
                      f"  (n_pre={pr['pre_n']}, n_post={pr['post_n']})")

            print(f"\n--- Top 5 Decliners (by delta) ---")
            for pr in scored[-5:]:
                d = round(pr["post_score"] - pr["pre_score"], 2)
                print(f"  qid={pr['question_id']:>5}  pre={pr['pre_score']:6.2f}%"
                      f"  post={pr['post_score']:6.2f}%  delta={d:+.2f}pp"
                      f"  (n_pre={pr['pre_n']}, n_post={pr['post_n']})")

        print("\n[DRY RUN] No data written.")
        return

    # --- Step 6: Upsert to Supabase ---
    logger.info("\nUpserting performance rows to Supabase...")
    BATCH_SIZE = 100
    total_upserted = 0
    for i in range(0, len(perf_rows), BATCH_SIZE):
        batch = perf_rows[i:i + BATCH_SIZE]
        for row in batch:
            if row.get("pre_score") is not None:
                row["pre_score"] = round(row["pre_score"], 2)
            if row.get("post_score") is not None:
                row["post_score"] = round(row["post_score"], 2)
        client.table("performance").upsert(
            batch, on_conflict="question_id,segment"
        ).execute()
        total_upserted += len(batch)
        if (i // BATCH_SIZE + 1) % 5 == 0:
            logger.info(f"  ... {total_upserted}/{len(perf_rows)} rows upserted")

    print(f"\n  Performance rows upserted: {total_upserted}")

    # Verification
    p_count = (client.table("performance")
               .select("id", count="exact").limit(0).execute().count)
    print(f"  Total performance rows in Supabase: {p_count}")
    print("\nDone.")


if __name__ == "__main__":
    main()
