"""
Import checkpoint duplicates into the dedup reviewer using pre-computed embeddings.

This script:
1. Reads the duplicate_review_fixed file (156 ONCOLOGY duplicates in 76 groups)
2. Matches questions to their embeddings via text matching
3. Uses embedding similarity scores for the import
4. For each group, selects the canonical (first is_canonical=True or first in group)
5. Creates dedup clusters for import via /api/dedup/import endpoint
6. SAFETY: Only creates cluster records, does NOT modify question data

Note: Excluded questions (from config/excluded_questions.yaml) are filtered out.

Output: JSON file for import via dashboard API
"""

import pandas as pd
import sqlite3
import json
import yaml
from pathlib import Path
from datetime import datetime
from difflib import SequenceMatcher

# Paths
BASE_DIR = Path(__file__).parent.parent
DUPLICATE_REVIEW_FILE = BASE_DIR / "data/eval/duplicate_review_fixed_20260124_234304.xlsx"
EMBED_FILE = BASE_DIR / "data/raw/questions_deduplicated_20260119_091825.xlsx"
COLLATED_FILE = BASE_DIR / "data/raw/questions_deduplicated_collated_20260121_221852.xlsx"
DB_PATH = BASE_DIR / "dashboard/data/questions.db"
OUTPUT_PATH = BASE_DIR / "data/checkpoints/checkpoint_duplicates_import_v2.json"
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
    return str(text).lower().strip()[:200]


def load_embedding_data():
    """Load and merge embedding data with QGDs."""
    print("Loading embedding and collated files...")
    embed_df = pd.read_excel(EMBED_FILE)
    collated_df = pd.read_excel(COLLATED_FILE)

    # Normalize for matching
    embed_df['norm_q'] = embed_df['QUESTION'].apply(normalize_text)
    collated_df['norm_q'] = collated_df['OPTIMIZEDQUESTION'].apply(normalize_text)

    # Merge to get QGD for each embedding row
    embed_with_qgd = embed_df.merge(
        collated_df[['norm_q', 'QUESTIONGROUPDESIGNATION']].drop_duplicates('norm_q'),
        on='norm_q',
        how='left'
    )

    # Create row_id -> QGD mapping for canonical lookup
    row_to_qgd = embed_with_qgd.set_index('row_id')['QUESTIONGROUPDESIGNATION'].to_dict()

    # Add canonical QGD
    embed_with_qgd['canonical_qgd'] = embed_with_qgd['canonical_row_id'].map(row_to_qgd)

    print(f"  Embedding rows: {len(embed_with_qgd)}")
    print(f"  With QGD: {embed_with_qgd['QUESTIONGROUPDESIGNATION'].notna().sum()}")

    return embed_with_qgd


def get_db_questions():
    """Get all questions currently in the database with their disease state from tags."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute("""
        SELECT q.id, q.source_id, q.question_stem, t.disease_state
        FROM questions q
        LEFT JOIN tags t ON q.id = t.question_id
        WHERE q.source_id IS NOT NULL
    """)

    questions = {}
    for row in cursor:
        q_id, source_id, stem, disease = row
        questions[str(source_id)] = {
            "question_id": q_id,
            "source_id": source_id,
            "stem": stem,
            "disease_state": disease
        }

    conn.close()
    print(f"Database questions: {len(questions)}")
    return questions


def main():
    print("=" * 60)
    print("Checkpoint Duplicates Import Script v2")
    print("=" * 60)

    # Load exclusion list
    excluded_source_ids = load_exclusion_list()

    # Load data
    embed_data = load_embedding_data()
    db_questions = get_db_questions()

    # Load duplicate review file
    print("\nLoading duplicate review file...")
    dup_df = pd.read_excel(DUPLICATE_REVIEW_FILE)
    onc_df = dup_df[dup_df['SOURCE'] == 'ONCOLOGY'].copy()

    print(f"ONCOLOGY duplicates: {len(onc_df)} in {onc_df['group_id'].nunique()} groups")

    # Create QGD -> embedding info lookup
    qgd_embed_info = {}
    for qgd in onc_df['QUESTIONGROUPDESIGNATION'].unique():
        matches = embed_data[embed_data['QUESTIONGROUPDESIGNATION'] == qgd]
        if len(matches) > 0:
            row = matches.iloc[0]
            qgd_embed_info[qgd] = {
                'cluster_id': row['cluster_id'],
                'is_canonical': row['is_canonical'],
                'canonical_qgd': row['canonical_qgd'],
                'similarity_score': row['similarity_score']
            }

    print(f"QGDs with embedding info: {len(qgd_embed_info)} / 156")

    # Process each group
    clusters_created = []
    skipped_no_db = []
    skipped_no_embed = []
    skipped_excluded = 0

    for group_id in sorted(onc_df['group_id'].unique()):
        group = onc_df[onc_df['group_id'] == group_id]
        qgds = group['QUESTIONGROUPDESIGNATION'].tolist()

        # Filter out excluded QGDs
        qgds_filtered = [qgd for qgd in qgds if str(int(qgd)) not in excluded_source_ids]
        excluded_count = len(qgds) - len(qgds_filtered)
        if excluded_count > 0:
            print(f"  Group {group_id}: Filtered out {excluded_count} excluded QGDs")
            skipped_excluded += excluded_count

        if len(qgds_filtered) == 0:
            print(f"  Group {group_id}: All QGDs excluded, skipping group")
            skipped_no_db.append({
                'group_id': group_id,
                'qgds': qgds,
                'reason': 'All questions excluded'
            })
            continue

        qgds = qgds_filtered  # Use filtered list

        # Check which QGDs are in the database
        in_db = [qgd for qgd in qgds if str(int(qgd)) in db_questions]
        not_in_db = [qgd for qgd in qgds if str(int(qgd)) not in db_questions]

        # If no questions in DB, skip entirely
        if len(in_db) == 0:
            skipped_no_db.append({
                'group_id': group_id,
                'qgds': qgds,
                'reason': 'No questions in current database'
            })
            continue

        # Get embedding info
        embed_info = {qgd: qgd_embed_info.get(qgd) for qgd in qgds}
        has_embed = [qgd for qgd in qgds if embed_info.get(qgd) is not None]

        if len(has_embed) == 0:
            skipped_no_embed.append({
                'group_id': group_id,
                'qgds': qgds,
                'reason': 'No embedding info found'
            })
            continue

        # Select canonical: prefer is_canonical=True from embedding, else first in DB
        canonical_qgd = None
        for qgd in qgds:
            info = embed_info.get(qgd)
            if info and info.get('is_canonical') and str(int(qgd)) in db_questions:
                canonical_qgd = qgd
                break

        if canonical_qgd is None:
            # Fall back to first question in DB
            canonical_qgd = in_db[0]

        # Build cluster entry
        canonical_source_id = str(int(canonical_qgd))
        canonical_db_info = db_questions.get(canonical_source_id)

        cluster = {
            'group_id': group_id,
            'canonical_source_id': canonical_source_id,
            'canonical_disease': canonical_db_info.get('disease_state') if canonical_db_info else None,
            'duplicates': []
        }

        # Add duplicates (excluding canonical)
        for qgd in qgds:
            if qgd == canonical_qgd:
                continue

            source_id = str(int(qgd))
            db_info = db_questions.get(source_id)
            embed = embed_info.get(qgd)

            dup_entry = {
                'source_id': source_id,
                'similarity': embed['similarity_score'] if embed else 0.95,  # Default if no embed
                'in_database': db_info is not None,
                'disease_state': db_info.get('disease_state') if db_info else None
            }
            cluster['duplicates'].append(dup_entry)

        clusters_created.append(cluster)

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Clusters created: {len(clusters_created)}")
    print(f"Skipped (not in DB): {len(skipped_no_db)}")
    print(f"Skipped (no embedding): {len(skipped_no_embed)}")
    print(f"Skipped (excluded): {skipped_excluded}")

    # Count by disease
    disease_counts = {}
    total_dups_in_db = 0
    for cluster in clusters_created:
        disease = cluster.get('canonical_disease', 'Unknown')
        disease_counts[disease] = disease_counts.get(disease, 0) + 1
        for dup in cluster['duplicates']:
            if dup['in_database']:
                total_dups_in_db += 1

    print(f"\nClusters by disease:")
    for disease, count in sorted(disease_counts.items()):
        print(f"  {disease}: {count}")

    print(f"\nTotal duplicates in database: {total_dups_in_db}")

    # Build output
    output = {
        'generated_at': datetime.now().isoformat(),
        'source': 'checkpoint_comparison_v2',
        'description': 'Duplicates from stage2_ready_final that were removed in stage2_ready_cleaned, with embedding similarity',
        'summary': {
            'total_groups_in_review_file': onc_df['group_id'].nunique(),
            'clusters_with_db_questions': len(clusters_created),
            'skipped_no_db_questions': len(skipped_no_db),
            'skipped_no_embedding': len(skipped_no_embed),
            'skipped_excluded': skipped_excluded,
            'duplicates_in_database': total_dups_in_db
        },
        'clusters': clusters_created,
        'skipped': {
            'no_db_questions': skipped_no_db[:10],  # First 10 for reference
            'no_embedding': skipped_no_embed
        }
    }

    # Generate flattened duplicate pairs for API import
    output['duplicate_pairs'] = []
    for cluster in clusters_created:
        for dup in cluster['duplicates']:
            if dup['in_database']:
                output['duplicate_pairs'].append({
                    'canonical_source_id': cluster['canonical_source_id'],
                    'duplicate_source_id': dup['source_id'],
                    'similarity': dup['similarity']
                })

    print(f"\nDuplicate pairs for import: {len(output['duplicate_pairs'])}")

    # Save output
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"\nOutput saved to: {OUTPUT_PATH}")

    # Show sample clusters
    print("\n" + "=" * 60)
    print("Sample Clusters (first 5 with DB questions)")
    print("=" * 60)
    for cluster in clusters_created[:5]:
        print(f"\nGroup {cluster['group_id']} - Canonical: {cluster['canonical_source_id']} ({cluster['canonical_disease']})")
        for dup in cluster['duplicates']:
            in_db = "✓ in DB" if dup['in_database'] else "✗ not in DB"
            print(f"  → Dup: {dup['source_id']} (sim={dup['similarity']:.3f}) {in_db}")

    return output


if __name__ == "__main__":
    main()
