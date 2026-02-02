"""
Step 3: Compare Answer Sets Within Clusters

For each multi-member stem cluster, compares answer set embeddings
to identify divergent pairs that need LLM triage.

Input:
  - deduplication_v2/data/stem_clusters.json
  - data/raw/questions_deduplicated_collated_20260121_221852.xlsx
Output: deduplication_v2/data/answer_comparisons.json
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np
import requests
from dotenv import load_dotenv
from sklearn.metrics.pairwise import cosine_similarity

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

# Configuration
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
CLUSTERS_FILE = DATA_DIR / "stem_clusters.json"
SOURCE_FILE = PROJECT_ROOT / "data/raw/questions_deduplicated_collated_20260121_221852.xlsx"
OUTPUT_FILE = DATA_DIR / "answer_comparisons.json"

EMBEDDING_MODEL = "openai/text-embedding-3-small"
BATCH_SIZE = 100

# Thresholds
HIGH_SIMILARITY = 0.90  # True duplicates
LOW_SIMILARITY = 0.70   # Need LLM triage


def build_answer_text(row: pd.Series) -> str:
    """Build text for embedding from all answer options."""
    parts = []

    # Correct answer
    if pd.notna(row.get("OPTIMIZEDCORRECTANSWER")):
        parts.append(f"Correct: {row['OPTIMIZEDCORRECTANSWER']}")

    # Incorrect answers
    for i in range(1, 10):
        col = f"IANSWER{i}"
        if col in row and pd.notna(row[col]):
            parts.append(f"Incorrect: {row[col]}")

    return " | ".join(parts)


def get_embeddings_batch(texts: list, api_key: str, batch_size: int = 100) -> list:
    """Get embeddings for a list of texts in batches."""
    import time

    all_embeddings = []

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        print(f"    Embedding batch {i//batch_size + 1}/{(len(texts) + batch_size - 1)//batch_size}...")

        for attempt in range(3):
            try:
                response = requests.post(
                    "https://openrouter.ai/api/v1/embeddings",
                    headers=headers,
                    json={"input": batch, "model": EMBEDDING_MODEL},
                    timeout=60
                )

                if response.status_code == 429:
                    time.sleep(2 ** attempt * 5)
                    continue

                if response.status_code != 200:
                    raise Exception(f"API error: {response.status_code}")

                data = response.json()
                batch_embeddings = [item["embedding"] for item in data["data"]]
                all_embeddings.extend(batch_embeddings)
                break

            except requests.exceptions.Timeout:
                if attempt < 2:
                    time.sleep(2)
                else:
                    raise

    return all_embeddings


def main():
    print("=" * 60)
    print("DEDUPLICATION V2 - STEP 3: COMPARE ANSWER SETS")
    print("=" * 60)

    # Check API key
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY not found")
        sys.exit(1)

    # Load clusters
    print(f"\n1. Loading clusters from {CLUSTERS_FILE.name}...")
    if not CLUSTERS_FILE.exists():
        print("ERROR: Clusters file not found. Run cluster_by_stem.py first")
        sys.exit(1)

    with open(CLUSTERS_FILE, "r", encoding="utf-8") as f:
        clusters_data = json.load(f)

    multi_member_clusters = clusters_data["multi_member_clusters"]
    print(f"   Found {len(multi_member_clusters)} multi-member clusters")

    # Load source data
    print(f"\n2. Loading source data from {SOURCE_FILE.name}...")
    source_df = pd.read_excel(SOURCE_FILE)
    print(f"   Loaded {len(source_df)} rows")

    # Build QGD -> row mapping
    qgd_to_row = {
        int(row["QUESTIONGROUPDESIGNATION"]): row
        for _, row in source_df.iterrows()
        if pd.notna(row["QUESTIONGROUPDESIGNATION"])
    }
    print(f"   Mapped {len(qgd_to_row)} QGDs")

    # Collect all QGDs that need answer embeddings
    print("\n3. Collecting QGDs from multi-member clusters...")
    qgds_to_embed = set()
    for cluster in multi_member_clusters:
        for member in cluster["members"]:
            if member["qgd"] is not None:
                qgds_to_embed.add(member["qgd"])

    print(f"   {len(qgds_to_embed)} unique QGDs need answer embeddings")

    # Build answer texts
    print("\n4. Building answer texts...")
    qgd_list = list(qgds_to_embed)
    answer_texts = []
    valid_qgds = []

    for qgd in qgd_list:
        if qgd in qgd_to_row:
            row = qgd_to_row[qgd]
            text = build_answer_text(row)
            if text.strip():
                answer_texts.append(text)
                valid_qgds.append(qgd)

    print(f"   Built {len(answer_texts)} answer texts")

    # Generate answer embeddings
    print("\n5. Generating answer embeddings...")
    answer_embeddings = get_embeddings_batch(answer_texts, api_key, BATCH_SIZE)
    print(f"   Generated {len(answer_embeddings)} embeddings")

    # Build QGD -> embedding mapping
    qgd_to_embedding = {
        qgd: emb for qgd, emb in zip(valid_qgds, answer_embeddings)
    }

    # Compare answer sets within each cluster
    print("\n6. Comparing answer sets within clusters...")
    results = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_clusters_analyzed": len(multi_member_clusters),
            "high_similarity_threshold": HIGH_SIMILARITY,
            "low_similarity_threshold": LOW_SIMILARITY
        },
        "cluster_comparisons": [],
        "divergent_pairs": [],  # Pairs needing LLM triage
        "summary": {
            "total_pairs_compared": 0,
            "high_similarity_pairs": 0,
            "medium_similarity_pairs": 0,
            "low_similarity_pairs": 0
        }
    }

    for cluster in multi_member_clusters:
        cluster_id = cluster["cluster_id"]
        members = cluster["members"]

        # Get embeddings for cluster members
        member_qgds = [m["qgd"] for m in members if m["qgd"] in qgd_to_embedding]

        if len(member_qgds) < 2:
            continue

        # Compute pairwise similarities
        embeddings_matrix = np.array([qgd_to_embedding[qgd] for qgd in member_qgds])
        sim_matrix = cosine_similarity(embeddings_matrix)

        cluster_result = {
            "cluster_id": cluster_id,
            "stem_preview": members[0]["stem_preview"] if members else "",
            "member_count": len(member_qgds),
            "pairs": []
        }

        # Compare all pairs
        for i in range(len(member_qgds)):
            for j in range(i + 1, len(member_qgds)):
                qgd_i = member_qgds[i]
                qgd_j = member_qgds[j]
                sim = float(sim_matrix[i][j])

                results["summary"]["total_pairs_compared"] += 1

                pair_info = {
                    "qgd_1": qgd_i,
                    "qgd_2": qgd_j,
                    "answer_similarity": round(sim, 4)
                }

                if sim >= HIGH_SIMILARITY:
                    pair_info["category"] = "high"
                    results["summary"]["high_similarity_pairs"] += 1
                elif sim >= LOW_SIMILARITY:
                    pair_info["category"] = "medium"
                    results["summary"]["medium_similarity_pairs"] += 1
                else:
                    pair_info["category"] = "low"
                    results["summary"]["low_similarity_pairs"] += 1

                    # Add to divergent pairs for LLM triage
                    results["divergent_pairs"].append({
                        "cluster_id": cluster_id,
                        "stem_preview": members[0]["stem_preview"][:100] if members else "",
                        "qgd_1": qgd_i,
                        "qgd_2": qgd_j,
                        "answer_similarity": round(sim, 4)
                    })

                cluster_result["pairs"].append(pair_info)

        results["cluster_comparisons"].append(cluster_result)

    # Save results
    print(f"\n7. Saving to {OUTPUT_FILE.name}...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"   Clusters analyzed: {len(results['cluster_comparisons'])}")
    print(f"   Total pairs compared: {results['summary']['total_pairs_compared']}")
    print(f"   High similarity (>={HIGH_SIMILARITY}): {results['summary']['high_similarity_pairs']}")
    print(f"   Medium similarity ({LOW_SIMILARITY}-{HIGH_SIMILARITY}): {results['summary']['medium_similarity_pairs']}")
    print(f"   Low similarity (<{LOW_SIMILARITY}): {results['summary']['low_similarity_pairs']}")
    print(f"\n   Divergent pairs needing LLM triage: {len(results['divergent_pairs'])}")

    if results["divergent_pairs"]:
        print(f"\n   Sample divergent pairs:")
        for pair in results["divergent_pairs"][:3]:
            print(f"     Cluster {pair['cluster_id']}: QGD {pair['qgd_1']} vs {pair['qgd_2']} (sim={pair['answer_similarity']})")

    print(f"\nDone! Proceed to Step 4: llm_triage_divergent.py")


if __name__ == "__main__":
    main()
