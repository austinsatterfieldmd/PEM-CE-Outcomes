"""
Verify tagging batch completion and track failed questions.

Run after each tagging batch to:
1. Check for missing questions (MASTER - DB - remaining)
2. Update failed_questions.json with any missing QGDs
3. Report summary

Usage:
    python scripts/verify_tagging_batch.py
    python scripts/verify_tagging_batch.py --fix  # Add missing to remaining file
"""

import argparse
import json
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime
from collections import defaultdict

PROJECT_ROOT = Path(__file__).parent.parent
CHECKPOINT_DIR = PROJECT_ROOT / "data" / "checkpoints"
DB_PATH = PROJECT_ROOT / "dashboard" / "data" / "questions.db"
MASTER_FILE = CHECKPOINT_DIR / "stage2_ready_MASTER.xlsx"
FAILED_FILE = CHECKPOINT_DIR / "failed_questions.json"

HEME_DISEASES = ['ALL', 'CLL', 'DLBCL', 'FL', 'MCL']


def load_failed_questions() -> dict:
    """Load existing failed questions tracker."""
    if FAILED_FILE.exists():
        with open(FAILED_FILE, encoding='utf-8') as f:
            return json.load(f)
    return {
        "failed": [],
        "recovered": [],
        "last_checked": None
    }


def save_failed_questions(data: dict):
    """Save failed questions tracker."""
    data["last_checked"] = datetime.now().isoformat()
    with open(FAILED_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def get_master_qgds() -> dict:
    """Get all QGDs from master file by disease."""
    df = pd.read_excel(MASTER_FILE)
    result = defaultdict(set)
    for _, row in df.iterrows():
        disease = row.get('STAGE1_disease_state', '')
        qgd = row.get('QUESTIONGROUPDESIGNATION')
        if disease in HEME_DISEASES and qgd:
            result[disease].add(int(qgd))
    return result


def get_db_qgds() -> dict:
    """Get all QGDs from database by disease."""
    if not DB_PATH.exists():
        return defaultdict(set)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT t.disease_state, q.source_id
        FROM tags t
        JOIN questions q ON t.question_id = q.id
        WHERE t.disease_state IN (?, ?, ?, ?, ?)
    ''', HEME_DISEASES)

    result = defaultdict(set)
    for disease, source_id in cursor.fetchall():
        if source_id:
            result[disease].add(int(source_id))
    conn.close()
    return result


def get_remaining_qgds() -> dict:
    """Get QGDs from remaining file by disease."""
    # Find the most recent remaining file
    remaining_files = list(CHECKPOINT_DIR.glob("stage2_remaining_*.xlsx"))
    if not remaining_files:
        return defaultdict(set)

    latest = max(remaining_files, key=lambda f: f.stat().st_mtime)
    df = pd.read_excel(latest)

    result = defaultdict(set)
    for _, row in df.iterrows():
        disease = row.get('STAGE1_disease_state', '')
        qgd = row.get('QUESTIONGROUPDESIGNATION')
        if disease in HEME_DISEASES and qgd:
            result[disease].add(int(qgd))
    return result


def find_missing_questions() -> dict:
    """Find questions that are in MASTER but not in DB or remaining."""
    master = get_master_qgds()
    db = get_db_qgds()
    remaining = get_remaining_qgds()

    missing = defaultdict(set)
    for disease in HEME_DISEASES:
        accounted = db[disease] | remaining[disease]
        missing[disease] = master[disease] - accounted

    return missing


def check_checkpoint_errors() -> dict:
    """Check checkpoint files for questions with errors."""
    errors = defaultdict(list)

    for disease in HEME_DISEASES:
        checkpoint_file = CHECKPOINT_DIR / f"stage2_tagged_{disease.lower()}.json"
        if not checkpoint_file.exists():
            continue

        with open(checkpoint_file, encoding='utf-8') as f:
            data = json.load(f)

        for q in data:
            if q.get('error'):
                errors[disease].append({
                    'qgd': q.get('source_id'),
                    'error': q.get('error'),
                    'tagged_at': q.get('tagged_at')
                })

    return errors


def add_to_remaining(qgds_by_disease: dict):
    """Add missing QGDs back to the remaining file."""
    remaining_files = list(CHECKPOINT_DIR.glob("stage2_remaining_*.xlsx"))
    if not remaining_files:
        print("No remaining file found!")
        return

    latest = max(remaining_files, key=lambda f: f.stat().st_mtime)
    remaining_df = pd.read_excel(latest)
    master_df = pd.read_excel(MASTER_FILE)

    rows_to_add = []
    for disease, qgds in qgds_by_disease.items():
        for qgd in qgds:
            row = master_df[master_df['QUESTIONGROUPDESIGNATION'] == qgd]
            if len(row) > 0:
                rows_to_add.append(row.iloc[0])

    if rows_to_add:
        new_df = pd.concat([remaining_df, pd.DataFrame(rows_to_add)], ignore_index=True)
        new_df.to_excel(latest, index=False)
        print(f"Added {len(rows_to_add)} questions to {latest.name}")


def main():
    parser = argparse.ArgumentParser(description="Verify tagging batch completion")
    parser.add_argument("--fix", action="store_true", help="Add missing questions to remaining file")
    args = parser.parse_args()

    print("=" * 60)
    print("TAGGING BATCH VERIFICATION")
    print("=" * 60)

    # Load existing tracker
    failed_data = load_failed_questions()

    # Find missing questions
    missing = find_missing_questions()
    total_missing = sum(len(qgds) for qgds in missing.values())

    # Check for checkpoint errors
    errors = check_checkpoint_errors()
    total_errors = sum(len(errs) for errs in errors.values())

    # Report
    print("\n--- Missing Questions (not in DB or remaining) ---")
    if total_missing == 0:
        print("None! All questions accounted for.")
    else:
        for disease in HEME_DISEASES:
            if missing[disease]:
                print(f"  {disease}: {sorted(missing[disease])}")
                # Add to failed tracker
                for qgd in missing[disease]:
                    if not any(f['qgd'] == qgd for f in failed_data['failed']):
                        failed_data['failed'].append({
                            'qgd': qgd,
                            'disease': disease,
                            'found_at': datetime.now().isoformat(),
                            'status': 'missing'
                        })

    print(f"\n--- Checkpoint Errors ---")
    if total_errors == 0:
        print("None!")
    else:
        for disease in HEME_DISEASES:
            if errors[disease]:
                print(f"  {disease}:")
                for err in errors[disease]:
                    print(f"    QGD {err['qgd']}: {err['error'][:50]}...")

    # Summary
    print(f"\n--- Summary ---")
    master = get_master_qgds()
    db = get_db_qgds()
    remaining = get_remaining_qgds()

    print(f"{'Disease':<8} {'Master':>8} {'DB':>8} {'Remaining':>10} {'Missing':>8}")
    print("-" * 50)
    for disease in HEME_DISEASES:
        m = len(master[disease])
        d = len(db[disease])
        r = len(remaining[disease])
        miss = len(missing[disease])
        print(f"{disease:<8} {m:>8} {d:>8} {r:>10} {miss:>8}")

    # Save tracker
    save_failed_questions(failed_data)
    print(f"\nTracker saved to: {FAILED_FILE}")

    # Fix if requested
    if args.fix and total_missing > 0:
        print(f"\n--- Fixing: Adding {total_missing} missing questions to remaining file ---")
        add_to_remaining(missing)
    elif total_missing > 0:
        print(f"\nRun with --fix to add missing questions to remaining file")


if __name__ == "__main__":
    main()
