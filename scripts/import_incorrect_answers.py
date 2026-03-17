#!/usr/bin/env python3
"""
Backfill incorrect answers from Multispecialty Excel into Supabase.

Reads IANSWER1–IANSWER9 from the Multispecialty Excel, matches rows to
existing questions in Supabase by source_id (QUESTIONGROUPDESIGNATION),
and updates questions.incorrect_answers + tags.answer_option_count.

Usage:
    python scripts/import_incorrect_answers.py --dry-run
    python scripts/import_incorrect_answers.py --dry-run --limit 20
    python scripts/import_incorrect_answers.py --force
"""

import argparse
import io
import json
import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

# Force UTF-8 stdout on Windows to avoid cp1252 encoding errors
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Load environment
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

EXCEL_PATH = PROJECT_ROOT / "data" / "imports" / "multispecialty_questions.xlsx"
PREFERRED_SHEET = "Multispecialty_2026-03-11-1207"

IANSWER_COLS = [f"IANSWER{i}" for i in range(1, 10)]


def resolve_sheet_name(excel_path: Path) -> str:
    """Find the correct sheet: prefer the named sheet, fall back to first sheet."""
    import openpyxl
    wb = openpyxl.load_workbook(excel_path, read_only=True)
    sheets = wb.sheetnames
    wb.close()
    if PREFERRED_SHEET in sheets:
        return PREFERRED_SHEET
    if len(sheets) == 1:
        return sheets[0]
    for s in sheets:
        if "multispecialty" in s.lower():
            return s
    return sheets[0]


def parse_incorrect_answers(row: pd.Series) -> list[str]:
    """Collect IANSWER1-9 into a list, skipping empty/placeholder values."""
    answers = []
    for col in IANSWER_COLS:
        val = row.get(col)
        if pd.isna(val):
            continue
        text = str(val).strip()
        if text == "" or text == "0":
            continue
        answers.append(text)
    return answers


def fetch_all_questions(client) -> list[dict]:
    """Paginate through all questions in Supabase (max 1000 per request)."""
    all_questions = []
    offset = 0
    while True:
        batch = (
            client.table("questions")
            .select("id, source_id, correct_answer, incorrect_answers, question_stem")
            .range(offset, offset + 999)
            .execute()
        )
        all_questions.extend(batch.data)
        if len(batch.data) < 1000:
            break
        offset += 1000
    return all_questions


def main():
    parser = argparse.ArgumentParser(
        description="Backfill incorrect answers from Multispecialty Excel into Supabase"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show stats and sample without writing to Supabase",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process only first N unique QGDs (for testing)",
    )
    parser.add_argument(
        "--file",
        type=str,
        default=str(EXCEL_PATH),
        help=f"Path to Excel file (default: {EXCEL_PATH})",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing incorrect_answers (default: skip if already populated)",
    )
    args = parser.parse_args()

    # -----------------------------------------------------------------------
    # 1. EXCEL PARSING
    # -----------------------------------------------------------------------
    excel_path = Path(args.file)
    if not excel_path.exists():
        print(f"ERROR: Excel file not found: {excel_path}")
        sys.exit(1)

    sheet_name = resolve_sheet_name(excel_path)
    print(f"Reading {excel_path} (sheet: {sheet_name})...")
    df = pd.read_excel(excel_path, sheet_name=sheet_name)
    print(f"  Total rows in Excel: {len(df)}")

    present_ia_cols = [c for c in IANSWER_COLS if c in df.columns]
    if not present_ia_cols:
        print(f"ERROR: No IANSWER columns found in sheet '{sheet_name}'.")
        print(f"  Available columns: {list(df.columns)}")
        print(f"  Expected columns like: IANSWER1, IANSWER2, ... IANSWER9")
        print(f"\n  The Excel file may need to be replaced with the full multispecialty")
        print(f"  export that contains IANSWER1-IANSWER9 columns.")
        sys.exit(1)
    print(f"  IANSWER columns found: {present_ia_cols}")

    before_dedup = len(df)
    df = df.drop_duplicates(subset=["QUESTIONGROUPDESIGNATION"], keep="first")
    print(f"  Unique QGDs after dedup: {len(df)} (removed {before_dedup - len(df)} duplicate rows)")

    if args.limit:
        df = df.head(args.limit)
        print(f"  Limited to first {len(df)} QGDs")

    excel_data = {}
    no_incorrect = 0
    for _, row in df.iterrows():
        qgd = int(row["QUESTIONGROUPDESIGNATION"])
        ia_list = parse_incorrect_answers(row)
        if not ia_list:
            no_incorrect += 1
            continue
        excel_data[qgd] = ia_list

    print(f"  QGDs with incorrect answers: {len(excel_data)}")
    if no_incorrect:
        print(f"  QGDs with no incorrect answers (skipped): {no_incorrect}")

    # -----------------------------------------------------------------------
    # 2. SUPABASE MATCHING
    # -----------------------------------------------------------------------
    from supabase import create_client

    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")
        sys.exit(1)

    print("\nFetching existing questions from Supabase...")
    client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    all_questions = fetch_all_questions(client)
    print(f"  Total questions in Supabase: {len(all_questions)}")

    lookup = {}
    for q in all_questions:
        sid = q.get("source_id")
        if sid is not None:
            lookup[int(sid)] = q

    matched = 0
    already_populated = 0
    to_update = []
    unmatched = 0

    for qgd, ia_list in excel_data.items():
        q = lookup.get(qgd)
        if q is None:
            unmatched += 1
            continue
        matched += 1

        existing_ia = q.get("incorrect_answers")
        if existing_ia and not args.force:
            already_populated += 1
            continue

        to_update.append({
            "question_id": q["id"],
            "source_id": qgd,
            "stem_preview": (q.get("question_stem") or "")[:80],
            "incorrect_answers": ia_list,
        })

    print(f"\nMatching results:")
    print(f"  Total unique QGDs from Excel: {len(excel_data)}")
    print(f"  Matched to Supabase questions: {matched}")
    print(f"  Already populated (skip unless --force): {already_populated}")
    print(f"  To update: {len(to_update)}")
    print(f"  Unmatched (QGD not in Supabase): {unmatched}")

    # -----------------------------------------------------------------------
    # 3. DRY RUN OUTPUT
    # -----------------------------------------------------------------------
    if args.dry_run:
        print("\n--- DRY RUN (no changes written) ---")
        samples = to_update[:5]
        for i, item in enumerate(samples, 1):
            print(f"\n  [{i}] source_id={item['source_id']}")
            print(f"      Stem: {item['stem_preview']}...")
            print(f"      Incorrect answers ({len(item['incorrect_answers'])}):")
            for ans in item["incorrect_answers"]:
                print(f"        - {ans}")
        if len(to_update) > 5:
            print(f"\n  ... and {len(to_update) - 5} more")
        print(f"\nWould update {len(to_update)} questions.")
        return

    # -----------------------------------------------------------------------
    # 4. BATCH UPDATES
    # -----------------------------------------------------------------------
    if not to_update:
        print("\nNothing to update.")
        return

    print(f"\nUpdating {len(to_update)} questions in Supabase...")
    updated = 0
    errors = 0
    batch_size = 50

    for i in range(0, len(to_update), batch_size):
        batch = to_update[i : i + batch_size]
        for item in batch:
            qid = item["question_id"]
            ia_list = item["incorrect_answers"]
            try:
                client.table("questions").update(
                    {"incorrect_answers": json.dumps(ia_list)}
                ).eq("id", qid).execute()

                client.table("tags").update(
                    {"answer_option_count": len(ia_list) + 1}
                ).eq("question_id", qid).execute()

                updated += 1
            except Exception as e:
                errors += 1
                print(f"  ERROR updating question id={qid} (source_id={item['source_id']}): {e}")

        done = min(i + batch_size, len(to_update))
        print(f"  Progress: {done}/{len(to_update)}")

    # -----------------------------------------------------------------------
    # 5. SUMMARY
    # -----------------------------------------------------------------------
    print(f"\nBackfill complete:")
    print(f"  Total unique QGDs in Excel: {len(excel_data)}")
    print(f"  Matched to Supabase questions: {matched}")
    print(f"  Updated (incorrect_answers written): {updated}")
    print(f"  Skipped (already populated): {already_populated}")
    print(f"  Unmatched (QGD not in Supabase): {unmatched}")
    if errors:
        print(f"  Errors: {errors}")


if __name__ == "__main__":
    main()
