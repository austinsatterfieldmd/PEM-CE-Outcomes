"""
Generate deliverables from V2 deduplication analysis:
1. canonical_mapping.csv - Maps every QGD to its canonical
2. data_quality_summary.md - Report for colleague
3. flagged_qgds_for_tagging.txt - QGDs to skip
"""

import json
import yaml
import pandas as pd
from pathlib import Path
from datetime import datetime

# Paths
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
PROJECT_ROOT = SCRIPT_DIR.parent.parent

# Load data
print("Loading V2 analysis data...")

# Load oncology QGDs
with open(DATA_DIR / "oncology_qgds.txt", "r") as f:
    oncology_qgds = set(int(line.strip()) for line in f if line.strip())

# Load recommendations
with open(DATA_DIR / "final_recommendations.yaml", "r", encoding="utf-8") as f:
    recs = yaml.safe_load(f)

# Load stem clusters for singleton info
with open(DATA_DIR / "stem_clusters.json", "r", encoding="utf-8") as f:
    clusters_data = json.load(f)

# Load LLM triage results for reasoning
with open(DATA_DIR / "llm_triage_results.json", "r", encoding="utf-8") as f:
    triage_data = json.load(f)

print(f"  Oncology QGDs: {len(oncology_qgds)}")
print(f"  Multi-member clusters: {len(recs['stem_clusters'])}")

# ============================================================
# 1. Generate canonical_mapping.csv
# ============================================================
print("\n1. Generating canonical_mapping.csv...")

mapping_rows = []

# Track which QGDs are in clusters
qgds_in_clusters = set()

for cluster in recs["stem_clusters"]:
    cluster_id = cluster["cluster_id"]

    # Find the canonical in this cluster
    canonical_qgd = None
    for qgd_rec in cluster["qgds"]:
        if qgd_rec["status"] == "canonical":
            canonical_qgd = qgd_rec["qgd"]
            break

    for qgd_rec in cluster["qgds"]:
        qgd = qgd_rec["qgd"]
        qgds_in_clusters.add(qgd)

        mapping_rows.append({
            "qgd": qgd,
            "canonical_qgd": canonical_qgd if canonical_qgd else qgd,
            "status": qgd_rec["status"],
            "cluster_id": cluster_id,
            "is_oncology": "Yes" if qgd in oncology_qgds else "No",
            "recommendation": qgd_rec.get("recommendation", ""),
        })

# Add singletons (they are their own canonical)
all_qgds = set()
source_df = pd.read_excel(PROJECT_ROOT / "data/raw/questions_deduplicated_collated_20260121_221852.xlsx")
for _, row in source_df.iterrows():
    if pd.notna(row["QUESTIONGROUPDESIGNATION"]):
        qgd = int(row["QUESTIONGROUPDESIGNATION"])
        all_qgds.add(qgd)
        if qgd not in qgds_in_clusters:
            mapping_rows.append({
                "qgd": qgd,
                "canonical_qgd": qgd,
                "status": "singleton",
                "cluster_id": None,
                "is_oncology": "Yes" if qgd in oncology_qgds else "No",
                "recommendation": "unique_question",
            })

mapping_df = pd.DataFrame(mapping_rows)
mapping_df = mapping_df.sort_values("qgd")
mapping_df.to_csv(DATA_DIR / "canonical_mapping.csv", index=False)
print(f"  Saved {len(mapping_df)} rows to canonical_mapping.csv")

# ============================================================
# 2. Generate flagged_qgds_for_tagging.txt
# ============================================================
print("\n2. Generating flagged_qgds_for_tagging.txt...")

flagged_qgds = []
for row in mapping_rows:
    if row["status"] == "data_error" and row["is_oncology"] == "Yes":
        flagged_qgds.append(row["qgd"])

with open(DATA_DIR / "flagged_qgds_for_tagging.txt", "w") as f:
    f.write("# QGDs to skip during tagging (data quality issues)\n")
    f.write(f"# Generated: {datetime.now().isoformat()}\n")
    f.write(f"# Count: {len(flagged_qgds)}\n\n")
    for qgd in sorted(flagged_qgds):
        f.write(f"{qgd}\n")

print(f"  Saved {len(flagged_qgds)} flagged QGDs")

# ============================================================
# 3. Generate data_quality_summary.md
# ============================================================
print("\n3. Generating data_quality_summary.md...")

# Calculate stats
total_qgds = len(all_qgds)
oncology_count = len(oncology_qgds)
singleton_count = clusters_data["singleton_count"]
multi_member_count = len(recs["stem_clusters"])

# Count by status (oncology only)
status_counts = {"canonical": 0, "true_duplicate": 0, "different_question": 0, "data_error": 0, "singleton": 0}
for row in mapping_rows:
    if row["is_oncology"] == "Yes":
        status = row["status"]
        if status in status_counts:
            status_counts[status] += 1

summary_md = f"""# Data Quality Analysis Summary

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M")}

## Overview

This analysis used a hierarchical validation approach to identify duplicate questions and data quality issues in the CE question bank.

## Methodology

1. **Stem Clustering** (90% similarity threshold)
   - Grouped questions with similar stems regardless of answer sets
   - Permissive threshold to catch acronym expansions (e.g., "NSCLC" → "non-small cell lung cancer")

2. **Answer Set Comparison**
   - Compared answer embeddings within each stem cluster
   - Flagged pairs with <70% answer similarity for LLM review

3. **LLM Triage** (GPT-5.2)
   - Classified divergent pairs as:
     - SAME_QUESTION_DATA_ERROR: Wrong answers attached
     - SAME_QUESTION_MINOR_VARIATION: Valid answer variations
     - DIFFERENT_QUESTIONS: Legitimately different educational content

## Results Summary

### All Questions
| Metric | Count |
|--------|-------|
| Total QGDs | {total_qgds:,} |
| Singleton clusters (unique) | {singleton_count:,} |
| Multi-member clusters | {multi_member_count:,} |

### Oncology Questions Only
| Category | Count | % of Oncology |
|----------|-------|---------------|
| Total Oncology QGDs | {oncology_count:,} | 100% |
| Singletons (unique) | {status_counts['singleton']:,} | {100*status_counts['singleton']/oncology_count:.1f}% |
| Canonical (cluster representatives) | {status_counts['canonical']:,} | {100*status_counts['canonical']/oncology_count:.1f}% |
| True Duplicates | {status_counts['true_duplicate']:,} | {100*status_counts['true_duplicate']/oncology_count:.1f}% |
| Different Questions | {status_counts['different_question']:,} | {100*status_counts['different_question']/oncology_count:.1f}% |
| **Data Errors** | **{status_counts['data_error']:,}** | **{100*status_counts['data_error']/oncology_count:.1f}%** |

### Unique Oncology Questions
**{status_counts['singleton'] + status_counts['canonical'] + status_counts['different_question']:,}** unique oncology questions (excluding duplicates and data errors)

## Data Errors Detail

{status_counts['data_error']} oncology questions have been flagged as potential data errors. These are cases where:
- Two QGDs share nearly identical question stems (90%+ similarity)
- But have very different answer sets (<70% similarity)
- LLM determined the answer mismatch is likely a data join error, not intentional variation

**See:** `oncology_data_errors_for_review_v2.xlsx` for full details with question stems and both answer sets.

## Files Generated

| File | Description |
|------|-------------|
| `canonical_mapping.csv` | Maps every QGD to its canonical + status |
| `flagged_qgds_for_tagging.txt` | {len(flagged_qgds)} QGDs to skip during tagging |
| `oncology_data_errors_for_review_v2.xlsx` | Data errors with full question details |
| `final_recommendations.yaml` | Complete V2 analysis results |

## Recommended Actions

1. **Review data errors** in `oncology_data_errors_for_review_v2.xlsx`
   - Determine which answer set is correct for each pair
   - Consider fixing at the source (Snowflake) if possible

2. **Use canonical mapping** when joining tags with outcomes data
   - Duplicates should inherit tags from their canonical
   - This ensures consistent rollup of performance metrics

3. **Skip flagged QGDs** during tagging until data errors are resolved

## Technical Notes

- Stem embedding model: `openai/text-embedding-3-small` (1536 dimensions)
- Answer embedding model: `openai/text-embedding-3-small`
- LLM for triage: `openai/gpt-5.2`
- All source data: `questions_deduplicated_collated_20260121_221852.xlsx`
"""

with open(DATA_DIR / "data_quality_summary.md", "w", encoding="utf-8") as f:
    f.write(summary_md)

print("  Saved data_quality_summary.md")

# ============================================================
# Summary
# ============================================================
print("\n" + "=" * 60)
print("DELIVERABLES GENERATED")
print("=" * 60)
print(f"  1. canonical_mapping.csv ({len(mapping_df)} rows)")
print(f"  2. flagged_qgds_for_tagging.txt ({len(flagged_qgds)} QGDs)")
print(f"  3. data_quality_summary.md")
print(f"\nAll files saved to: {DATA_DIR}")
