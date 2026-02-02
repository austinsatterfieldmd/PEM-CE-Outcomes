"""
Step 2: Cluster Questions by Stem Similarity

Clusters questions based on stem-only embeddings.
Uses 90% cosine similarity threshold (permissive to catch acronym-expanded versions).

Input: deduplication_v2/data/stem_embeddings.parquet
Output: deduplication_v2/data/stem_clusters.json
"""

import json
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# Configuration
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
INPUT_FILE = DATA_DIR / "stem_embeddings.parquet"
OUTPUT_FILE = DATA_DIR / "stem_clusters.json"

# 90% threshold - intentionally permissive to catch acronym variations
SIMILARITY_THRESHOLD = 0.90


def main():
    print("=" * 60)
    print("DEDUPLICATION V2 - STEP 2: CLUSTER BY STEM SIMILARITY")
    print("=" * 60)

    # Load embeddings
    print(f"\n1. Loading embeddings from {INPUT_FILE.name}...")
    if not INPUT_FILE.exists():
        print(f"ERROR: Input file not found: {INPUT_FILE}")
        print("Run generate_stem_embeddings.py first")
        return

    df = pd.read_parquet(INPUT_FILE)
    print(f"   Loaded {len(df)} rows")

    # Parse embeddings from JSON
    print("\n2. Parsing embeddings...")
    embeddings = np.array([json.loads(e) for e in df["embedding"]])
    print(f"   Embedding shape: {embeddings.shape}")

    # Compute similarity matrix
    print(f"\n3. Computing similarity matrix for {len(embeddings)} questions...")
    similarity_matrix = cosine_similarity(embeddings)
    print(f"   Matrix shape: {similarity_matrix.shape}")

    # Find clusters
    print(f"\n4. Finding clusters (threshold: {SIMILARITY_THRESHOLD})...")
    assigned = set()
    clusters = []
    cluster_id = 0

    qgds = df["qgd"].tolist()
    stems = df["stem"].tolist()

    for i in range(len(embeddings)):
        if i in assigned:
            continue

        # Find all similar questions
        similar_indices = np.where(similarity_matrix[i] >= SIMILARITY_THRESHOLD)[0]

        # Get unassigned similar questions
        cluster_members = [idx for idx in similar_indices if idx not in assigned]

        if not cluster_members:
            continue

        # Build cluster info
        cluster = {
            "cluster_id": cluster_id,
            "size": len(cluster_members),
            "members": []
        }

        for idx in cluster_members:
            sim_to_first = similarity_matrix[cluster_members[0]][idx]
            cluster["members"].append({
                "qgd": int(qgds[idx]) if pd.notna(qgds[idx]) else None,
                "row_index": int(idx),
                "stem_preview": stems[idx][:100] + "..." if len(stems[idx]) > 100 else stems[idx],
                "similarity_to_first": float(sim_to_first)
            })
            assigned.add(idx)

        clusters.append(cluster)
        cluster_id += 1

        if cluster_id % 500 == 0:
            print(f"   Processed {cluster_id} clusters...")

    # Separate singleton and multi-member clusters
    singletons = [c for c in clusters if c["size"] == 1]
    multi_member = [c for c in clusters if c["size"] > 1]

    # Sort multi-member clusters by size descending
    multi_member.sort(key=lambda x: -x["size"])

    # Build output
    output = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "input_file": INPUT_FILE.name,
            "total_questions": len(df),
            "similarity_threshold": SIMILARITY_THRESHOLD,
            "total_clusters": len(clusters),
            "singleton_clusters": len(singletons),
            "multi_member_clusters": len(multi_member)
        },
        "multi_member_clusters": multi_member,
        "singleton_count": len(singletons)
    }

    # Save
    print(f"\n5. Saving to {OUTPUT_FILE.name}...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"   Total questions: {len(df)}")
    print(f"   Total clusters: {len(clusters)}")
    print(f"   Singleton clusters (unique): {len(singletons)}")
    print(f"   Multi-member clusters: {len(multi_member)}")

    # Show top clusters
    if multi_member:
        print(f"\n   Top 5 largest clusters:")
        for c in multi_member[:5]:
            print(f"     Cluster {c['cluster_id']}: {c['size']} members")
            print(f"       Stem: {c['members'][0]['stem_preview'][:60]}...")

    # Questions in multi-member clusters
    questions_in_clusters = sum(c["size"] for c in multi_member)
    print(f"\n   Questions needing answer comparison: {questions_in_clusters}")
    print(f"   (These are in multi-member clusters)")

    print(f"\nDone! Proceed to Step 3: compare_answer_sets.py")


if __name__ == "__main__":
    main()
