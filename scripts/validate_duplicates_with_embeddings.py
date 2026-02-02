"""
Validate the 156 removed "duplicates" against embedding-based similarity.

This script:
1. Loads the 156 QGDs that were removed based on text-matching
2. Cross-references with the embedding file to get actual similarity scores
3. Categorizes each as: CONFIRMED duplicate, FALSE POSITIVE, or NEEDS REVIEW
4. Generates a report and import file for manual review

Thresholds:
- >= 0.95: CONFIRMED duplicate (very high similarity)
- 0.85-0.95: NEEDS REVIEW (borderline)
- < 0.85: FALSE POSITIVE (should not have been removed)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import json
from collections import defaultdict

# Paths
BASE_DIR = Path(__file__).parent.parent
DUPLICATE_REVIEW_FILE = BASE_DIR / "data/eval/duplicate_review_fixed_20260124_234304.xlsx"
EMBED_FILE = BASE_DIR / "data/raw/questions_deduplicated_20260119_091825.xlsx"
COLLATED_FILE = BASE_DIR / "data/raw/questions_deduplicated_collated_20260121_221852.xlsx"
FINAL_FILE = BASE_DIR / "data/checkpoints/stage2_ready_final.xlsx"
OUTPUT_DIR = BASE_DIR / "data/eval"

# Thresholds
CONFIRMED_THRESHOLD = 0.95
REVIEW_THRESHOLD = 0.85


def normalize_text(text: str) -> str:
    """Normalize text for matching."""
    if pd.isna(text):
        return ""
    return str(text).lower().strip()[:200]


def load_embedding_clusters():
    """Load embedding file and build cluster lookup."""
    print("Loading embedding file...")
    embed_df = pd.read_excel(EMBED_FILE)
    print(f"  Loaded {len(embed_df)} rows")

    # Build cluster info
    clusters = defaultdict(list)
    for _, row in embed_df.iterrows():
        cluster_id = row['cluster_id']
        clusters[cluster_id].append({
            'row_id': row['row_id'],
            'question': row['QUESTION'],
            'is_canonical': row['is_canonical'],
            'canonical_row_id': row['canonical_row_id'],
            'similarity_score': row['similarity_score']
        })

    print(f"  Found {len(clusters)} clusters")
    return embed_df, clusters


def load_qgd_mapping():
    """Create mapping from question text to QGD."""
    print("Loading QGD mapping from collated file...")
    collated_df = pd.read_excel(COLLATED_FILE)

    # Create normalized text -> QGD mapping
    text_to_qgd = {}
    for _, row in collated_df.iterrows():
        norm = normalize_text(row['OPTIMIZEDQUESTION'])
        if norm:
            text_to_qgd[norm] = row['QUESTIONGROUPDESIGNATION']

    print(f"  Mapped {len(text_to_qgd)} unique questions to QGDs")
    return text_to_qgd, collated_df


def get_disease_state(qgd, final_df):
    """Get disease state for a QGD from the final file."""
    matches = final_df[final_df['QUESTIONGROUPDESIGNATION'] == qgd]
    if len(matches) > 0:
        return matches.iloc[0].get('FINAL_disease_state', 'Unknown')
    return 'Unknown'


def analyze_duplicate_groups():
    """Analyze each duplicate group against embeddings."""

    # Load all data
    embed_df, clusters = load_embedding_clusters()
    text_to_qgd, collated_df = load_qgd_mapping()

    print("\nLoading duplicate review file...")
    dup_df = pd.read_excel(DUPLICATE_REVIEW_FILE)
    onc_df = dup_df[dup_df['SOURCE'] == 'ONCOLOGY'].copy()
    print(f"  {len(onc_df)} ONCOLOGY questions in {onc_df['group_id'].nunique()} groups")

    print("\nLoading final file for disease states...")
    final_df = pd.read_excel(FINAL_FILE)

    # Create embed question -> row info mapping
    embed_df['norm_q'] = embed_df['QUESTION'].apply(normalize_text)
    embed_lookup = {}
    for _, row in embed_df.iterrows():
        norm = row['norm_q']
        if norm:
            embed_lookup[norm] = {
                'row_id': row['row_id'],
                'cluster_id': row['cluster_id'],
                'is_canonical': row['is_canonical'],
                'canonical_row_id': row['canonical_row_id'],
                'similarity_score': row['similarity_score']
            }

    # Analyze each group
    results = {
        'confirmed': [],      # >= 0.95 similarity
        'needs_review': [],   # 0.85-0.95 similarity
        'false_positive': [], # < 0.85 similarity
        'no_embedding': []    # couldn't find in embedding file
    }

    group_analysis = []

    for group_id in sorted(onc_df['group_id'].unique()):
        group = onc_df[onc_df['group_id'] == group_id]
        qgds = group['QUESTIONGROUPDESIGNATION'].tolist()

        group_info = {
            'group_id': group_id,
            'qgds': qgds,
            'size': len(qgds),
            'questions': [],
            'embed_clusters': set(),
            'similarities': [],
            'category': None,
            'disease_states': set()
        }

        # Get embedding info for each question in group
        for _, row in group.iterrows():
            qgd = row['QUESTIONGROUPDESIGNATION']
            question_text = row.get('original_question', '')
            norm_q = normalize_text(question_text)

            disease = get_disease_state(qgd, final_df)
            group_info['disease_states'].add(disease)

            q_info = {
                'qgd': qgd,
                'question': question_text[:100] if question_text else '',
                'disease_state': disease,
                'embed_info': None
            }

            # Look up in embedding file
            embed_info = embed_lookup.get(norm_q)
            if embed_info:
                q_info['embed_info'] = embed_info
                group_info['embed_clusters'].add(embed_info['cluster_id'])
                if embed_info['similarity_score'] < 1.0:  # Not the canonical itself
                    group_info['similarities'].append(embed_info['similarity_score'])

            group_info['questions'].append(q_info)

        # Determine category based on similarities
        if not group_info['similarities']:
            # All are canonicals or no embedding found
            has_embed = any(q['embed_info'] for q in group_info['questions'])
            if has_embed:
                # Multiple canonicals in same text-match group - likely false positive
                group_info['category'] = 'false_positive'
                group_info['reason'] = 'All questions are canonicals in different embedding clusters'
            else:
                group_info['category'] = 'no_embedding'
                group_info['reason'] = 'No embedding data found'
        else:
            min_sim = min(group_info['similarities'])
            avg_sim = sum(group_info['similarities']) / len(group_info['similarities'])
            group_info['min_similarity'] = min_sim
            group_info['avg_similarity'] = avg_sim

            if min_sim >= CONFIRMED_THRESHOLD:
                group_info['category'] = 'confirmed'
                group_info['reason'] = f'High similarity (min={min_sim:.3f})'
            elif min_sim >= REVIEW_THRESHOLD:
                group_info['category'] = 'needs_review'
                group_info['reason'] = f'Borderline similarity (min={min_sim:.3f})'
            else:
                group_info['category'] = 'false_positive'
                group_info['reason'] = f'Low similarity (min={min_sim:.3f})'

        # Convert sets to lists for JSON
        group_info['embed_clusters'] = list(group_info['embed_clusters'])
        group_info['disease_states'] = list(group_info['disease_states'])

        results[group_info['category']].append(group_info)
        group_analysis.append(group_info)

    return results, group_analysis


def generate_report(results, group_analysis):
    """Generate detailed report."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print("\n" + "=" * 70)
    print("DUPLICATE VALIDATION REPORT")
    print("=" * 70)

    # Summary
    total_groups = len(group_analysis)
    print(f"\nTotal text-matched groups analyzed: {total_groups}")
    print(f"\n  CONFIRMED duplicates (sim >= {CONFIRMED_THRESHOLD}): {len(results['confirmed'])} groups")
    print(f"  NEEDS REVIEW (sim {REVIEW_THRESHOLD}-{CONFIRMED_THRESHOLD}): {len(results['needs_review'])} groups")
    print(f"  FALSE POSITIVES (sim < {REVIEW_THRESHOLD}): {len(results['false_positive'])} groups")
    print(f"  NO EMBEDDING DATA: {len(results['no_embedding'])} groups")

    # Count questions in each category
    confirmed_qs = sum(g['size'] for g in results['confirmed'])
    review_qs = sum(g['size'] for g in results['needs_review'])
    false_pos_qs = sum(g['size'] for g in results['false_positive'])
    no_embed_qs = sum(g['size'] for g in results['no_embedding'])

    print(f"\nQuestion counts:")
    print(f"  CONFIRMED: {confirmed_qs} questions")
    print(f"  NEEDS REVIEW: {review_qs} questions")
    print(f"  FALSE POSITIVES: {false_pos_qs} questions (should NOT have been removed)")
    print(f"  NO EMBEDDING: {no_embed_qs} questions")

    # Disease breakdown
    print(f"\n{'=' * 70}")
    print("BREAKDOWN BY CATEGORY")
    print("=" * 70)

    for category in ['confirmed', 'needs_review', 'false_positive', 'no_embedding']:
        groups = results[category]
        if not groups:
            continue

        print(f"\n--- {category.upper()} ({len(groups)} groups) ---")

        # Disease distribution
        disease_counts = defaultdict(int)
        for g in groups:
            for d in g['disease_states']:
                disease_counts[d] += 1

        print(f"  Disease distribution:")
        for disease, count in sorted(disease_counts.items(), key=lambda x: -x[1]):
            print(f"    {disease}: {count}")

        # Show sample groups
        print(f"\n  Sample groups:")
        for g in groups[:3]:
            sim_info = ""
            if 'min_similarity' in g:
                sim_info = f" (sim={g['min_similarity']:.3f})"
            print(f"    Group {g['group_id']}: {g['size']} questions, {g['disease_states']}{sim_info}")
            print(f"      Reason: {g['reason']}")
            for q in g['questions'][:2]:
                print(f"      - QGD {q['qgd']}: {q['question'][:60]}...")

    # Save detailed JSON report
    report_path = OUTPUT_DIR / f"duplicate_validation_report_{timestamp}.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': timestamp,
            'thresholds': {
                'confirmed': CONFIRMED_THRESHOLD,
                'review': REVIEW_THRESHOLD
            },
            'summary': {
                'total_groups': total_groups,
                'confirmed_groups': len(results['confirmed']),
                'review_groups': len(results['needs_review']),
                'false_positive_groups': len(results['false_positive']),
                'no_embedding_groups': len(results['no_embedding']),
                'confirmed_questions': confirmed_qs,
                'review_questions': review_qs,
                'false_positive_questions': false_pos_qs,
                'no_embedding_questions': no_embed_qs
            },
            'results': {
                'confirmed': results['confirmed'],
                'needs_review': results['needs_review'],
                'false_positive': results['false_positive'],
                'no_embedding': results['no_embedding']
            }
        }, f, indent=2, default=to_json_serializable)

    print(f"\n{'=' * 70}")
    print(f"Detailed report saved to: {report_path.name}")

    return report_path


def to_json_serializable(obj):
    """Convert numpy types to Python native types for JSON serialization."""
    if isinstance(obj, (np.integer, np.int64)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj


def generate_restore_list(results):
    """Generate list of QGDs that should be restored (false positives)."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Collect QGDs that should NOT have been removed
    restore_qgds = []
    for group in results['false_positive']:
        for q in group['questions']:
            restore_qgds.append({
                'qgd': to_json_serializable(q['qgd']),
                'disease_state': q['disease_state'],
                'reason': group['reason'],
                'group_id': to_json_serializable(group['group_id'])
            })

    # Also include no_embedding as they weren't verified
    for group in results['no_embedding']:
        for q in group['questions']:
            restore_qgds.append({
                'qgd': to_json_serializable(q['qgd']),
                'disease_state': q['disease_state'],
                'reason': group['reason'],
                'group_id': to_json_serializable(group['group_id'])
            })

    if restore_qgds:
        restore_path = OUTPUT_DIR / f"questions_to_restore_{timestamp}.json"
        with open(restore_path, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': timestamp,
                'description': 'Questions that were incorrectly flagged as duplicates and should be restored',
                'count': len(restore_qgds),
                'questions': restore_qgds
            }, f, indent=2)

        print(f"Restore list saved to: {restore_path.name}")
        print(f"  {len(restore_qgds)} questions should be restored")

        return restore_path

    return None


def generate_review_import(results):
    """Generate import file for confirmed duplicates to review in dashboard."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Collect confirmed + needs_review for manual verification
    clusters_for_review = []

    for group in results['confirmed'] + results['needs_review']:
        # Find which question should be canonical (the one with is_canonical=True in embeddings)
        canonical_qgd = None
        duplicates = []

        for q in group['questions']:
            if q['embed_info'] and q['embed_info']['is_canonical']:
                canonical_qgd = q['qgd']
            else:
                duplicates.append(q)

        # If no canonical found, use first question
        if canonical_qgd is None and group['questions']:
            canonical_qgd = group['questions'][0]['qgd']
            duplicates = group['questions'][1:]

        if canonical_qgd and duplicates:
            cluster = {
                'group_id': to_json_serializable(group['group_id']),
                'category': group['category'],
                'canonical_qgd': to_json_serializable(canonical_qgd),
                'min_similarity': to_json_serializable(group.get('min_similarity', 0.95)),
                'disease_states': group['disease_states'],
                'duplicates': [
                    {
                        'qgd': to_json_serializable(d['qgd']),
                        'similarity': to_json_serializable(d['embed_info']['similarity_score']) if d.get('embed_info') else 0.95
                    }
                    for d in duplicates
                ]
            }
            clusters_for_review.append(cluster)

    if clusters_for_review:
        import_path = OUTPUT_DIR / f"validated_duplicates_for_review_{timestamp}.json"
        with open(import_path, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': timestamp,
                'description': 'Embedding-validated duplicates for manual review in dashboard',
                'thresholds': {
                    'confirmed': CONFIRMED_THRESHOLD,
                    'review': REVIEW_THRESHOLD
                },
                'cluster_count': len(clusters_for_review),
                'clusters': clusters_for_review
            }, f, indent=2)

        print(f"Review import file saved to: {import_path.name}")
        print(f"  {len(clusters_for_review)} clusters for review")

        return import_path

    return None


def main():
    print("=" * 70)
    print("VALIDATING 156 REMOVED QUESTIONS AGAINST EMBEDDINGS")
    print("=" * 70)

    results, group_analysis = analyze_duplicate_groups()

    report_path = generate_report(results, group_analysis)
    restore_path = generate_restore_list(results)
    review_path = generate_review_import(results)

    print("\n" + "=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    print("""
1. Review the FALSE POSITIVES - these questions should be restored
2. Import the validated duplicates into the dedup reviewer
3. Manually confirm/reject each cluster in the dashboard
4. Only after your review will any questions be hidden
""")


if __name__ == "__main__":
    main()
