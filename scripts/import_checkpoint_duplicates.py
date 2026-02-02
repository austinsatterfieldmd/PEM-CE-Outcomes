"""
Import checkpoint duplicates into the dedup reviewer.

This script:
1. Reads the duplicate_review_fixed file (156 ONCOLOGY duplicates in 76 groups)
2. For each group, finds the canonical question in the database
3. Creates dedup clusters linking duplicates to canonicals
4. Outputs a JSON file for import via the /api/dedup/import endpoint

Note: Excluded questions (from config/excluded_questions.yaml) are filtered out.
"""

import pandas as pd
import sqlite3
import json
import yaml
from pathlib import Path
from difflib import SequenceMatcher
from datetime import datetime

# Paths
BASE_DIR = Path(__file__).parent.parent
DUPLICATE_REVIEW_FILE = BASE_DIR / "data/eval/duplicate_review_fixed_20260124_234304.xlsx"
DB_PATH = BASE_DIR / "dashboard/data/questions.db"
OUTPUT_PATH = BASE_DIR / "data/checkpoints/checkpoint_duplicates_import.json"
EXCLUSION_LIST_PATH = BASE_DIR / "config" / "excluded_questions.yaml"


def load_exclusion_list() -> set:
    """
    Load the set of excluded source_ids from config/excluded_questions.yaml.

    Returns:
        Set of source_id strings that should be excluded from import.
    """
    if not EXCLUSION_LIST_PATH.exists():
        print("No exclusion list found, no questions will be excluded")
        return set()

    try:
        with open(EXCLUSION_LIST_PATH, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        excluded = set()
        for item in data.get('excluded_questions', []):
            source_id = item.get('source_id')
            if source_id:
                excluded.add(str(source_id))

        if excluded:
            print(f"Loaded exclusion list: {len(excluded)} questions will be filtered out")
        return excluded

    except Exception as e:
        print(f"Warning: Failed to load exclusion list: {e}")
        return set()


def normalize_text(text: str) -> str:
    """Normalize question text for matching."""
    if pd.isna(text):
        return ""
    return str(text).lower().strip()


def find_canonical_in_db(duplicate_question: str, conn: sqlite3.Connection, threshold: float = 0.8):
    """Find the most similar question in the database."""
    cursor = conn.execute("""
        SELECT id, source_id, question_stem
        FROM questions
        WHERE question_stem IS NOT NULL
    """)

    best_match = None
    best_ratio = 0

    dup_norm = normalize_text(duplicate_question)[:200]

    for row in cursor:
        q_id, source_id, question_stem = row
        db_norm = normalize_text(question_stem)[:200]

        ratio = SequenceMatcher(None, dup_norm, db_norm).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = {
                "question_id": q_id,
                "source_id": source_id,
                "similarity": ratio
            }

    if best_match and best_match["similarity"] >= threshold:
        return best_match
    return None


def main():
    # Load exclusion list
    excluded_source_ids = load_exclusion_list()

    # Load duplicate review file
    print("Loading duplicate review file...")
    df = pd.read_excel(DUPLICATE_REVIEW_FILE)
    onc_df = df[df["SOURCE"] == "ONCOLOGY"]

    print(f"Found {len(onc_df)} ONCOLOGY duplicates in {onc_df['group_id'].nunique()} groups")

    # Connect to database
    conn = sqlite3.connect(DB_PATH)

    # Process each group
    clusters = []
    skipped_groups = []
    skipped_excluded = 0

    for group_id in onc_df["group_id"].unique():
        group = onc_df[onc_df["group_id"] == group_id]

        # Get representative question from group
        first_row = group.iloc[0]
        question_text = first_row.get("normalized_question") or first_row.get("original_question")

        if pd.isna(question_text):
            print(f"  Group {group_id}: No question text, skipping")
            skipped_groups.append(group_id)
            continue

        # Find canonical in database
        canonical = find_canonical_in_db(question_text, conn)

        if not canonical:
            print(f"  Group {group_id}: No canonical found (below threshold), skipping")
            skipped_groups.append(group_id)
            continue

        # Check if canonical is excluded
        if str(canonical["source_id"]) in excluded_source_ids:
            print(f"  Group {group_id}: Canonical {canonical['source_id']} is excluded, skipping group")
            skipped_groups.append(group_id)
            skipped_excluded += 1
            continue

        # Build cluster entry
        cluster = {
            "canonical_source_id": canonical["source_id"],
            "similarity": canonical["similarity"],
            "duplicates": []
        }

        for _, row in group.iterrows():
            dup_source_id = str(row["QUESTIONGROUPDESIGNATION"])

            # Skip excluded duplicates
            if dup_source_id in excluded_source_ids:
                print(f"    Skipping excluded duplicate QGD={dup_source_id}")
                skipped_excluded += 1
                continue

            cluster["duplicates"].append({
                "source_id": dup_source_id,
                "similarity": canonical["similarity"],  # Same as canonical match
                "question_preview": str(row.get("original_question", ""))[:200]
            })

        # Only add cluster if there are duplicates remaining
        if cluster["duplicates"]:
            clusters.append(cluster)
            print(f"  Group {group_id}: Found canonical {canonical['source_id']} ({canonical['similarity']:.1%}), {len(cluster['duplicates'])} duplicates")
        else:
            print(f"  Group {group_id}: All duplicates excluded, skipping group")
            skipped_groups.append(group_id)

    conn.close()

    # Build output for import
    output = {
        "generated_at": datetime.now().isoformat(),
        "source": "checkpoint_comparison",
        "description": "Duplicates from stage2_ready_final that were removed in stage2_ready_cleaned",
        "total_clusters": len(clusters),
        "skipped_groups": len(skipped_groups),
        "skipped_excluded": skipped_excluded,
        "duplicates": []
    }

    # Flatten to duplicate pairs for import endpoint
    for cluster in clusters:
        for dup in cluster["duplicates"]:
            output["duplicates"].append({
                "canonical_source_id": cluster["canonical_source_id"],
                "duplicate_source_id": dup["source_id"],
                "similarity": cluster["similarity"]
            })

    # Save output
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"\n=== Summary ===")
    print(f"Clusters created: {len(clusters)}")
    print(f"Skipped groups: {len(skipped_groups)}")
    print(f"Skipped excluded: {skipped_excluded}")
    print(f"Total duplicate pairs: {len(output['duplicates'])}")
    print(f"Output saved to: {OUTPUT_PATH}")

    return output


if __name__ == "__main__":
    main()
