"""
Deduplicate Checkpoint Data Script

Runs deduplication on checkpoint JSON data (post-normalization).
Uses OpenAI embeddings to find semantically similar questions.

Output:
- Adds dedup metadata to checkpoint: is_duplicate, canonical_question_id, similarity_score, cluster_id
- Generates summary report

Usage:
    python scripts/dedup_checkpoint.py --dry-run  # Preview only
    python scripts/dedup_checkpoint.py            # Apply dedup
"""

import argparse
import json
import os
import sys
import shutil
from datetime import datetime
from pathlib import Path
import numpy as np
import requests
from dotenv import load_dotenv
from sklearn.metrics.pairwise import cosine_similarity

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================
SIMILARITY_THRESHOLD = 0.95
EMBEDDING_MODEL = "openai/text-embedding-3-small"
BATCH_SIZE = 100


def build_embedding_text(question: dict) -> str:
    """Build text for embedding from question + all answer options."""
    parts = []

    # Question stem
    stem = question.get('question_stem', '')
    if stem:
        parts.append(f"Question: {stem}")

    # Correct answer
    correct = question.get('correct_answer', '')
    if correct:
        parts.append(f"Correct: {correct}")

    # Incorrect answers
    incorrect = question.get('incorrect_answers', [])
    if incorrect:
        for i, ans in enumerate(incorrect):
            if ans:
                parts.append(f"Incorrect: {ans}")

    return " | ".join(parts)


def get_embeddings_batch(texts: list, api_key: str, batch_size: int = 100) -> list:
    """Get embeddings for a list of texts in batches using OpenRouter API."""
    import time

    all_embeddings = []

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/MJH-AI-Accelerator/CE-Outcomes-Dashboard",
        "X-Title": "CE Question Deduplication"
    }

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        print(f"  Embedding batch {i//batch_size + 1}/{(len(texts) + batch_size - 1)//batch_size} ({len(batch)} texts)...")

        for attempt in range(3):
            try:
                response = requests.post(
                    "https://openrouter.ai/api/v1/embeddings",
                    headers=headers,
                    json={
                        "input": batch,
                        "model": EMBEDDING_MODEL
                    },
                    timeout=60
                )

                if response.status_code == 429:
                    wait_time = 2 ** attempt * 5
                    print(f"    Rate limited, waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue

                if response.status_code != 200:
                    raise Exception(f"OpenRouter API error: {response.status_code} - {response.text}")

                data = response.json()
                batch_embeddings = [item["embedding"] for item in data["data"]]
                all_embeddings.extend(batch_embeddings)
                break

            except Exception as e:
                if attempt < 2:
                    print(f"    Error: {e}, retrying...")
                    time.sleep(2)
                else:
                    raise

    return all_embeddings


def find_duplicate_clusters(embeddings: np.ndarray, questions: list, threshold: float = 0.95) -> dict:
    """
    Find duplicate clusters based on cosine similarity.
    Returns dict mapping question_id to cluster info.
    """
    n = len(embeddings)
    print(f"  Computing similarity matrix for {n} questions...")
    similarity_matrix = cosine_similarity(embeddings)

    # Track assignments
    assigned = set()
    clusters = {}  # question_id -> (cluster_id, is_canonical, canonical_qid, max_similarity)
    cluster_id = 0

    # Create question_id to index mapping
    qid_to_idx = {q['question_id']: i for i, q in enumerate(questions)}
    idx_to_qid = {i: q['question_id'] for i, q in enumerate(questions)}

    for i in range(n):
        if i in assigned:
            continue

        # Find all rows similar to this one
        similar_indices = np.where(similarity_matrix[i] >= threshold)[0]

        if len(similar_indices) == 1:
            # Unique question
            qid = idx_to_qid[i]
            clusters[qid] = {
                'cluster_id': cluster_id,
                'is_duplicate': False,
                'canonical_question_id': qid,
                'similarity_score': 1.0,
                'duplicate_of': None
            }
            assigned.add(i)
        else:
            # Found duplicates
            cluster_members = [idx for idx in similar_indices if idx not in assigned]

            if cluster_members:
                # Select canonical: prefer lowest question_id (oldest/first)
                canonical_idx = min(cluster_members, key=lambda idx: questions[idx]['question_id'])
                canonical_qid = idx_to_qid[canonical_idx]

                for idx in cluster_members:
                    qid = idx_to_qid[idx]
                    is_canonical = (idx == canonical_idx)
                    sim_score = float(similarity_matrix[canonical_idx][idx])

                    clusters[qid] = {
                        'cluster_id': cluster_id,
                        'is_duplicate': not is_canonical,
                        'canonical_question_id': canonical_qid,
                        'similarity_score': sim_score,
                        'duplicate_of': None if is_canonical else canonical_qid
                    }
                    assigned.add(idx)

        cluster_id += 1

    return clusters


def main():
    parser = argparse.ArgumentParser(description='Deduplicate checkpoint data')
    parser.add_argument('--checkpoint', type=str,
                        default='data/checkpoints/stage2_tagged_multiple_myeloma.json',
                        help='Path to checkpoint file')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview changes without applying')
    parser.add_argument('--threshold', type=float, default=0.95,
                        help='Similarity threshold (default: 0.95)')
    args = parser.parse_args()

    checkpoint_path = Path(args.checkpoint)
    if not checkpoint_path.exists():
        print(f"Error: Checkpoint file not found: {checkpoint_path}")
        return 1

    # Check API key
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("Error: OPENROUTER_API_KEY not found in environment variables")
        return 1

    print("=" * 60)
    print("CHECKPOINT DEDUPLICATION")
    print("=" * 60)

    # Load data
    print(f"\n1. Loading checkpoint: {checkpoint_path}")
    with open(checkpoint_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"   Loaded {len(data)} questions")

    # Build embedding texts
    print("\n2. Building embedding texts...")
    embedding_texts = [build_embedding_text(q) for q in data]
    print(f"   Sample: {embedding_texts[0][:100]}...")

    # Get embeddings
    print("\n3. Generating embeddings via OpenRouter API...")
    embeddings = get_embeddings_batch(embedding_texts, api_key)
    embeddings_array = np.array(embeddings)
    print(f"   Generated {len(embeddings)} embeddings of dimension {len(embeddings[0])}")

    # Find duplicates
    print(f"\n4. Finding duplicates (threshold: {args.threshold})...")
    clusters = find_duplicate_clusters(embeddings_array, data, threshold=args.threshold)

    # Calculate statistics
    n_duplicates = sum(1 for c in clusters.values() if c['is_duplicate'])
    n_unique = len(clusters) - n_duplicates
    n_clusters = len(set(c['cluster_id'] for c in clusters.values()))

    print(f"\n{'=' * 60}")
    print("DEDUPLICATION RESULTS")
    print(f"{'=' * 60}")
    print(f"   Total questions:     {len(data)}")
    print(f"   Unique clusters:     {n_clusters}")
    print(f"   Canonical questions: {n_unique}")
    print(f"   Duplicates found:    {n_duplicates}")
    print(f"   Reduction:           {n_duplicates / len(data) * 100:.1f}%")

    # Show duplicate examples
    if n_duplicates > 0:
        print(f"\n   Sample duplicate clusters:")
        shown_clusters = set()
        for q in data:
            qid = q['question_id']
            cluster_info = clusters[qid]
            if cluster_info['is_duplicate'] and cluster_info['cluster_id'] not in shown_clusters:
                canonical_qid = cluster_info['canonical_question_id']
                canonical_q = next((x for x in data if x['question_id'] == canonical_qid), None)

                print(f"\n   Cluster {cluster_info['cluster_id']}:")
                if canonical_q:
                    stem_preview = canonical_q['question_stem'][:80] + "..." if len(canonical_q['question_stem']) > 80 else canonical_q['question_stem']
                    print(f"     CANONICAL Q{canonical_qid}: {stem_preview}")

                stem_preview = q['question_stem'][:80] + "..." if len(q['question_stem']) > 80 else q['question_stem']
                print(f"     DUPLICATE Q{qid}: {stem_preview}")
                print(f"     Similarity: {cluster_info['similarity_score']:.3f}")

                shown_clusters.add(cluster_info['cluster_id'])
                if len(shown_clusters) >= 3:
                    break

    if args.dry_run:
        print(f"\n{'=' * 60}")
        print("DRY RUN - No changes applied")
        print(f"{'=' * 60}")
        print(f"Would add dedup metadata to {len(data)} questions")
        print(f"Would mark {n_duplicates} as duplicates")
        return 0

    # Apply dedup metadata
    print(f"\n5. Applying dedup metadata to checkpoint...")
    for q in data:
        qid = q['question_id']
        cluster_info = clusters[qid]
        q['cluster_id'] = cluster_info['cluster_id']
        q['is_duplicate'] = cluster_info['is_duplicate']
        q['canonical_question_id'] = cluster_info['canonical_question_id']
        q['dedup_similarity_score'] = cluster_info['similarity_score']

    # Backup and save
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = checkpoint_path.with_suffix(f'.pre_dedup_{timestamp}.json')
    shutil.copy(checkpoint_path, backup_path)
    print(f"   Backup created: {backup_path}")

    with open(checkpoint_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"   Saved updated checkpoint: {checkpoint_path}")

    # Save dedup report
    report_path = checkpoint_path.parent / f'dedup_report_{timestamp}.json'
    report = {
        'timestamp': timestamp,
        'threshold': args.threshold,
        'total_questions': len(data),
        'unique_clusters': n_clusters,
        'canonical_questions': n_unique,
        'duplicates_found': n_duplicates,
        'reduction_percent': round(n_duplicates / len(data) * 100, 1),
        'clusters': {qid: info for qid, info in clusters.items() if info['is_duplicate']}
    }
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    print(f"   Saved dedup report: {report_path}")

    print(f"\nDone! Dedup metadata added to {len(data)} questions.")
    return 0


if __name__ == '__main__':
    exit(main())
