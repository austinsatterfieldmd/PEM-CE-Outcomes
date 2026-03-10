#!/usr/bin/env python3
"""
Import eye care questions from multispecialty Excel into Supabase.

Reads data/imports/multispecialty_questions.xlsx, filters to eye-care-related
questions using keyword matching + ADC_OCULAR_TOXICITY flag, and imports
questions + activities into Supabase.

Usage:
    python scripts/import_eye_care_questions.py --dry-run
    python scripts/import_eye_care_questions.py --limit 10
    python scripts/import_eye_care_questions.py
"""

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load environment
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

EXCEL_PATH = PROJECT_ROOT / "data" / "imports" / "multispecialty_questions.xlsx"

# ---------------------------------------------------------------------------
# Eye care keyword filters
# ---------------------------------------------------------------------------
CONDITION_KEYWORDS = [
    r"\bAMD\b", r"macular", r"glaucoma", r"retina", r"cornea",
    r"dry eye", r"cataract", r"kerato", r"presbyopia",
    r"thyroid eye", r"\bTED\b", r"uveitis", r"blephar",
    r"neurotrophic", r"ocular surface", r"meibomian",
    r"\bIOL\b", r"\bMIGS\b",
]

TREATMENT_KEYWORDS = [
    r"VEGF", r"aflibercept", r"ranibizumab", r"faricimab",
    r"brolucizumab", r"pegcetacoplan", r"avacincaptad",
    r"teprotumumab", r"cenegermin", r"netarsudil",
    r"lifitegrast", r"cyclosporine ophthalmic", r"pilocarpine",
]

DIAGNOSTIC_KEYWORDS = [
    r"\bOCT\b", r"\bIOP\b", r"fundus", r"visual field",
    r"pachymetry", r"Schirmer", r"tonometry", r"gonioscopy",
    r"esthesiometry",
]

PROGRAM_KEYWORDS = [
    r"\bCOPE\b", r"\bAAO\b", r"\bARVO\b", r"\bASCRS\b",
    r"\bASRS\b", r"EyeCon", r"\bIKA\b",
    r"ophthalmol", r"optometr", r"eye care",
]

ALL_PATTERNS = (
    CONDITION_KEYWORDS
    + TREATMENT_KEYWORDS
    + DIAGNOSTIC_KEYWORDS
    + PROGRAM_KEYWORDS
)

# Compile a single regex for efficiency
EYE_CARE_REGEX = re.compile("|".join(ALL_PATTERNS), re.IGNORECASE)


def is_eye_care_row(row: pd.Series) -> bool:
    """Return True if the row matches eye care criteria."""
    # ADC_OCULAR_TOXICITY flag
    adc_val = row.get("ADC_OCULAR_TOXICITY")
    if pd.notna(adc_val) and int(adc_val) == 1:
        return True

    # Keyword match on question text
    question = str(row.get("OPTIMIZEDQUESTION", ""))
    if EYE_CARE_REGEX.search(question):
        return True

    # Keyword match on activity names
    activities = str(row.get("ACTIVITY_NAMES", ""))
    if EYE_CARE_REGEX.search(activities):
        return True

    # Keyword match on correct answer
    answer = str(row.get("OPTIMIZEDCORRECTANSWER", ""))
    if EYE_CARE_REGEX.search(answer):
        return True

    return False


def get_quarter_from_date(dt: datetime) -> str:
    """Convert a date to quarter string like '2024 Q3'."""
    q = (dt.month - 1) // 3 + 1
    return f"{dt.year} Q{q}"


def parse_activities(activity_names: str, start_dates: str):
    """Parse semicolon-delimited activity names and dates into list of dicts."""
    if pd.isna(activity_names) or not str(activity_names).strip():
        return []

    names = [n.strip() for n in str(activity_names).split(";") if n.strip()]
    dates_raw = [d.strip() for d in str(start_dates).split(";")] if pd.notna(start_dates) else []

    results = []
    for i, name in enumerate(names):
        activity = {"activity_name": name}
        if i < len(dates_raw) and dates_raw[i]:
            try:
                dt = pd.to_datetime(dates_raw[i])
                activity["activity_date"] = dt.strftime("%Y-%m-%d")
                activity["quarter"] = get_quarter_from_date(dt)
            except (ValueError, TypeError):
                pass
        results.append(activity)
    return results


def build_question_row(row: pd.Series, source_file: str) -> dict:
    """Map Excel row to questions table schema."""
    return {
        "source_id": int(row["QUESTIONGROUPDESIGNATION"]),
        "question_stem": str(row["OPTIMIZEDQUESTION"]).strip(),
        "correct_answer": str(row["OPTIMIZEDCORRECTANSWER"]).strip(),
        "source_file": source_file,
        "is_oncology": True,  # Repurposed as "is_eye_care" flag
    }


def import_to_supabase(questions: list, dry_run: bool = False):
    """Import filtered questions into Supabase."""
    from supabase import create_client

    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")
        sys.exit(1)

    client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    # Track stats
    questions_inserted = 0
    questions_skipped = 0
    activities_upserted = set()
    links_created = 0

    for q_data in questions:
        source_id = q_data["question"]["source_id"]

        # Check if question already exists
        existing = (
            client.table("questions")
            .select("id")
            .eq("source_id", source_id)
            .execute()
        )
        if existing.data:
            questions_skipped += 1
            continue

        if dry_run:
            questions_inserted += 1
            for act in q_data["activities"]:
                activities_upserted.add(act["activity_name"])
                links_created += 1
            continue

        # Insert question
        result = client.table("questions").insert(q_data["question"]).execute()
        if not result.data:
            print(f"  WARNING: Failed to insert source_id={source_id}")
            continue
        question_id = result.data[0]["id"]
        questions_inserted += 1

        # Upsert activities and create links
        for act in q_data["activities"]:
            # Upsert activity
            act_data = {"activity_name": act["activity_name"]}
            if "activity_date" in act:
                act_data["activity_date"] = act["activity_date"]
            if "quarter" in act:
                act_data["quarter"] = act["quarter"]

            act_result = (
                client.table("activities")
                .upsert(act_data, on_conflict="activity_name")
                .execute()
            )
            activity_id = act_result.data[0]["id"] if act_result.data else None
            activities_upserted.add(act["activity_name"])

            # Link question to activity
            link_data = {
                "question_id": question_id,
                "activity_name": act["activity_name"],
                "activity_id": activity_id,
            }
            if "activity_date" in act:
                link_data["activity_date"] = act["activity_date"]
            if "quarter" in act:
                link_data["quarter"] = act["quarter"]

            client.table("question_activities").upsert(
                link_data, on_conflict="question_id,activity_name"
            ).execute()
            links_created += 1

    return {
        "questions_inserted": questions_inserted,
        "questions_skipped": questions_skipped,
        "activities_upserted": len(activities_upserted),
        "links_created": links_created,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Import eye care questions from multispecialty Excel into Supabase"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be imported without actually importing",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit the number of questions to import (for testing)",
    )
    parser.add_argument(
        "--file",
        type=str,
        default=str(EXCEL_PATH),
        help=f"Path to Excel file (default: {EXCEL_PATH})",
    )
    args = parser.parse_args()

    # Read Excel
    excel_path = Path(args.file)
    if not excel_path.exists():
        print(f"ERROR: Excel file not found: {excel_path}")
        sys.exit(1)

    print(f"Reading {excel_path}...")
    df = pd.read_excel(excel_path)
    print(f"  Total rows in Excel: {len(df)}")

    # Filter: skip bad data (correct answer = "0")
    bad_answer_mask = df["OPTIMIZEDCORRECTANSWER"].astype(str).str.strip() == "0"
    bad_count = bad_answer_mask.sum()
    if bad_count > 0:
        print(f"  Skipping {bad_count} rows with OPTIMIZEDCORRECTANSWER = '0'")
        df = df[~bad_answer_mask]

    # Filter: eye care questions only
    eye_care_mask = df.apply(is_eye_care_row, axis=1)
    df_eye = df[eye_care_mask].copy()
    print(f"  Eye care matches: {len(df_eye)}")

    # Deduplicate by QUESTIONGROUPDESIGNATION (keep first occurrence)
    before_dedup = len(df_eye)
    df_eye = df_eye.drop_duplicates(subset=["QUESTIONGROUPDESIGNATION"], keep="first")
    if before_dedup != len(df_eye):
        print(f"  After dedup by QGD: {len(df_eye)} (removed {before_dedup - len(df_eye)} duplicates)")

    # Apply limit
    if args.limit:
        df_eye = df_eye.head(args.limit)
        print(f"  Limited to: {len(df_eye)} rows")

    # Build import data
    source_file = excel_path.name
    questions = []
    for _, row in df_eye.iterrows():
        q_row = build_question_row(row, source_file)
        activities = parse_activities(
            row.get("ACTIVITY_NAMES"), row.get("START_DATES")
        )
        questions.append({"question": q_row, "activities": activities})

    print(f"\nPrepared {len(questions)} questions for import")

    if args.dry_run:
        print("\n--- DRY RUN ---")
        # Show sample
        for i, q in enumerate(questions[:10]):
            qd = q["question"]
            stem_preview = qd["question_stem"][:80] + "..." if len(qd["question_stem"]) > 80 else qd["question_stem"]
            act_names = [a["activity_name"] for a in q["activities"]]
            print(f"  [{i+1}] QGD={qd['source_id']}  Activities={len(act_names)}")
            print(f"      Stem: {stem_preview}")
            if act_names:
                print(f"      Activities: {'; '.join(act_names[:3])}")
            print()

        if len(questions) > 10:
            print(f"  ... and {len(questions) - 10} more")

        # Run import in dry-run mode to get stats
        stats = import_to_supabase(questions, dry_run=True)
        print(f"\nDry run summary:")
        print(f"  Would insert: {stats['questions_inserted']} questions")
        print(f"  Would upsert: {stats['activities_upserted']} activities")
        print(f"  Would create: {stats['links_created']} question-activity links")
        return

    # Real import
    print("\nImporting to Supabase...")
    stats = import_to_supabase(questions, dry_run=False)

    print(f"\nImport complete:")
    print(f"  Questions inserted: {stats['questions_inserted']}")
    print(f"  Questions skipped (already exist): {stats['questions_skipped']}")
    print(f"  Activities upserted: {stats['activities_upserted']}")
    print(f"  Question-activity links: {stats['links_created']}")


if __name__ == "__main__":
    main()
