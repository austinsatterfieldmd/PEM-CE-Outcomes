"""
Step 5: Generate Final Recommendations

Compiles results from all previous steps into actionable recommendations
mapped to existing QGDs.

Input:
  - deduplication_v2/data/stem_clusters.json
  - deduplication_v2/data/answer_comparisons.json
  - deduplication_v2/data/llm_triage_results.json
Output: deduplication_v2/data/final_recommendations.yaml
"""

import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

import yaml

# Configuration
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
CLUSTERS_FILE = DATA_DIR / "stem_clusters.json"
COMPARISONS_FILE = DATA_DIR / "answer_comparisons.json"
TRIAGE_FILE = DATA_DIR / "llm_triage_results.json"
OUTPUT_FILE = DATA_DIR / "final_recommendations.yaml"

# Thresholds (must match compare_answer_sets.py)
HIGH_SIMILARITY = 0.90
LOW_SIMILARITY = 0.70


def load_json(filepath: Path) -> dict:
    """Load JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def select_canonical(qgds: list, qgd_quality: dict) -> int:
    """
    Select the canonical QGD from a list.

    Priority:
    1. Highest answer quality score (if available)
    2. Lowest QGD number (oldest/original)
    """
    # If we have quality scores, use them
    if qgd_quality:
        scored = [(qgd, qgd_quality.get(qgd, 0)) for qgd in qgds]
        scored.sort(key=lambda x: (-x[1], x[0]))  # Highest quality, then lowest QGD
        return scored[0][0]

    # Otherwise, use lowest QGD (oldest)
    return min(qgds)


def main():
    print("=" * 60)
    print("DEDUPLICATION V2 - STEP 5: GENERATE RECOMMENDATIONS")
    print("=" * 60)

    # Load clusters
    print(f"\n1. Loading clusters from {CLUSTERS_FILE.name}...")
    if not CLUSTERS_FILE.exists():
        print("ERROR: Clusters file not found. Run cluster_by_stem.py first")
        return

    clusters_data = load_json(CLUSTERS_FILE)
    multi_member_clusters = clusters_data["multi_member_clusters"]
    total_questions = clusters_data["metadata"]["total_questions"]
    singleton_count = clusters_data["singleton_count"]
    print(f"   {len(multi_member_clusters)} multi-member clusters")
    print(f"   {singleton_count} singleton clusters")

    # Load answer comparisons
    print(f"\n2. Loading answer comparisons from {COMPARISONS_FILE.name}...")
    if not COMPARISONS_FILE.exists():
        print("ERROR: Comparisons file not found. Run compare_answer_sets.py first")
        return

    comparisons_data = load_json(COMPARISONS_FILE)
    cluster_comparisons = comparisons_data["cluster_comparisons"]
    divergent_pairs = comparisons_data["divergent_pairs"]
    print(f"   {len(cluster_comparisons)} clusters with comparisons")
    print(f"   {len(divergent_pairs)} divergent pairs")

    # Load LLM triage results (optional - may not have run yet)
    print(f"\n3. Loading LLM triage results...")
    triage_results = {}
    if TRIAGE_FILE.exists():
        triage_data = load_json(TRIAGE_FILE)
        # Index by (qgd_1, qgd_2) for quick lookup
        for result in triage_data.get("triage_results", []):
            key = (result["qgd_1"], result["qgd_2"])
            triage_results[key] = result
        print(f"   Loaded {len(triage_results)} triage results")
    else:
        print("   No triage results found (Step 4 not run yet)")
        print("   Will use answer similarity only for recommendations")

    # Build cluster-level comparison index
    cluster_pairs = defaultdict(list)
    for comparison in cluster_comparisons:
        cluster_id = comparison["cluster_id"]
        for pair in comparison.get("pairs", []):
            cluster_pairs[cluster_id].append(pair)

    # Generate recommendations
    print("\n4. Generating recommendations...")

    recommendations = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "source_clusters": CLUSTERS_FILE.name,
            "source_comparisons": COMPARISONS_FILE.name,
            "source_triage": TRIAGE_FILE.name if TRIAGE_FILE.exists() else None,
            "total_qgds": total_questions,
            "stem_clusters_found": len(multi_member_clusters) + singleton_count,
            "multi_member_clusters": len(multi_member_clusters),
            "divergent_pairs_triaged": len(triage_results)
        },
        "stem_clusters": [],
        "summary": {
            "canonical_qgds": 0,
            "true_duplicates": 0,
            "different_questions": 0,
            "data_errors": 0,
            "pending_triage": 0,
            "singletons": singleton_count
        }
    }

    # Process each multi-member cluster
    for cluster in multi_member_clusters:
        cluster_id = cluster["cluster_id"]
        members = cluster["members"]

        # Get all QGDs in cluster
        qgds = [m["qgd"] for m in members if m["qgd"] is not None]

        if len(qgds) < 2:
            continue

        # Get pairs for this cluster
        pairs = cluster_pairs.get(cluster_id, [])

        # Analyze pairs to determine relationships
        qgd_relationships = {}  # qgd -> {"status", "related_to", "similarity", "llm_verdict"}

        # Initialize all QGDs as potential canonicals
        for qgd in qgds:
            qgd_relationships[qgd] = {
                "status": "canonical_candidate",
                "high_sim_to": [],
                "low_sim_to": [],
                "llm_verdicts": {}
            }

        # Process each pair
        for pair in pairs:
            qgd_1 = pair["qgd_1"]
            qgd_2 = pair["qgd_2"]
            similarity = pair["answer_similarity"]
            category = pair.get("category", "unknown")

            if category == "high":
                # High similarity = true duplicates
                qgd_relationships[qgd_1]["high_sim_to"].append({
                    "qgd": qgd_2, "similarity": similarity
                })
                qgd_relationships[qgd_2]["high_sim_to"].append({
                    "qgd": qgd_1, "similarity": similarity
                })

            elif category == "low":
                # Low similarity = need LLM triage or flagged
                triage_key = (qgd_1, qgd_2)
                triage_key_rev = (qgd_2, qgd_1)

                llm_result = triage_results.get(triage_key) or triage_results.get(triage_key_rev)

                if llm_result:
                    verdict = llm_result.get("llm_response", {}).get("verdict", "UNKNOWN")
                    reason = llm_result.get("llm_response", {}).get("reasoning", "")

                    qgd_relationships[qgd_1]["llm_verdicts"][qgd_2] = {
                        "verdict": verdict, "reason": reason
                    }
                    qgd_relationships[qgd_2]["llm_verdicts"][qgd_1] = {
                        "verdict": verdict, "reason": reason
                    }
                else:
                    # No triage yet - flag as pending
                    qgd_relationships[qgd_1]["low_sim_to"].append({
                        "qgd": qgd_2, "similarity": similarity, "triaged": False
                    })
                    qgd_relationships[qgd_2]["low_sim_to"].append({
                        "qgd": qgd_1, "similarity": similarity, "triaged": False
                    })

        # Determine final status for each QGD
        cluster_rec = {
            "cluster_id": cluster_id,
            "stem_preview": members[0]["stem_preview"] if members else "",
            "member_count": len(qgds),
            "qgds": []
        }

        # Select canonical (lowest QGD for now)
        canonical_qgd = select_canonical(qgds, {})

        for qgd in qgds:
            rel = qgd_relationships[qgd]

            qgd_rec = {
                "qgd": qgd,
                "status": None,
                "recommendation": None
            }

            if qgd == canonical_qgd:
                # This is the canonical
                qgd_rec["status"] = "canonical"
                qgd_rec["recommendation"] = "keep_as_canonical"
                recommendations["summary"]["canonical_qgds"] += 1

            elif rel["high_sim_to"]:
                # High similarity to another QGD = true duplicate
                closest = max(rel["high_sim_to"], key=lambda x: x["similarity"])
                qgd_rec["status"] = "true_duplicate"
                qgd_rec["answer_sim_to_canonical"] = closest["similarity"]
                qgd_rec["recommendation"] = f"merge_tags_from_{canonical_qgd}"
                recommendations["summary"]["true_duplicates"] += 1

            elif rel["llm_verdicts"]:
                # Have LLM verdict
                # Check if any verdict is DIFFERENT_QUESTIONS
                has_different = any(
                    v["verdict"] == "DIFFERENT_QUESTIONS"
                    for v in rel["llm_verdicts"].values()
                )
                has_data_error = any(
                    v["verdict"] == "SAME_QUESTION_DATA_ERROR"
                    for v in rel["llm_verdicts"].values()
                )

                if has_different:
                    qgd_rec["status"] = "different_question"
                    verdicts = [v for v in rel["llm_verdicts"].values() if v["verdict"] == "DIFFERENT_QUESTIONS"]
                    qgd_rec["llm_reason"] = verdicts[0]["reason"] if verdicts else ""
                    qgd_rec["recommendation"] = "keep_separate"
                    recommendations["summary"]["different_questions"] += 1
                elif has_data_error:
                    qgd_rec["status"] = "data_error"
                    verdicts = [v for v in rel["llm_verdicts"].values() if v["verdict"] == "SAME_QUESTION_DATA_ERROR"]
                    qgd_rec["llm_reason"] = verdicts[0]["reason"] if verdicts else ""
                    qgd_rec["recommendation"] = "flag_for_manual_review"
                    recommendations["summary"]["data_errors"] += 1
                else:
                    # SAME_QUESTION_MINOR_VARIATION or other
                    qgd_rec["status"] = "true_duplicate"
                    qgd_rec["recommendation"] = f"merge_tags_from_{canonical_qgd}"
                    recommendations["summary"]["true_duplicates"] += 1

            elif rel["low_sim_to"]:
                # Low similarity but no triage yet
                qgd_rec["status"] = "pending_triage"
                qgd_rec["low_similarity_pairs"] = [
                    {"qgd": p["qgd"], "similarity": p["similarity"]}
                    for p in rel["low_sim_to"]
                ]
                qgd_rec["recommendation"] = "run_llm_triage"
                recommendations["summary"]["pending_triage"] += 1

            else:
                # Medium similarity - treat as true duplicate
                qgd_rec["status"] = "true_duplicate"
                qgd_rec["recommendation"] = f"merge_tags_from_{canonical_qgd}"
                recommendations["summary"]["true_duplicates"] += 1

            cluster_rec["qgds"].append(qgd_rec)

        recommendations["stem_clusters"].append(cluster_rec)

    # Save as YAML
    print(f"\n5. Saving to {OUTPUT_FILE.name}...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        yaml.dump(recommendations, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"   Total QGDs analyzed: {total_questions}")
    print(f"   Singleton clusters (unique): {recommendations['summary']['singletons']}")
    print(f"   Multi-member clusters: {len(recommendations['stem_clusters'])}")
    print(f"\n   Recommendations:")
    print(f"     Canonical QGDs: {recommendations['summary']['canonical_qgds']}")
    print(f"     True duplicates: {recommendations['summary']['true_duplicates']}")
    print(f"     Different questions: {recommendations['summary']['different_questions']}")
    print(f"     Data errors (manual review): {recommendations['summary']['data_errors']}")
    print(f"     Pending LLM triage: {recommendations['summary']['pending_triage']}")

    print(f"\nDone! Recommendations saved to {OUTPUT_FILE}")
    print("\nNext steps:")
    if recommendations['summary']['pending_triage'] > 0:
        print("  1. Run Step 4 (llm_triage_divergent.py) to triage pending pairs")
        print("  2. Re-run this script to update recommendations")
    else:
        print("  1. Review recommendations in final_recommendations.yaml")
        print("  2. Apply recommendations to your tagging workflow")


if __name__ == "__main__":
    main()
