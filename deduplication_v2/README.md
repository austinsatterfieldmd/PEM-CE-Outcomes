# Deduplication V2 - Hierarchical Validation

## Background

The original deduplication pipeline (V1) used embeddings of `stem + correct_answer + incorrect_answers`.
However, we discovered that the source Snowflake data already had quality issues:

- 393 questions with conflicting IANSWER values in the original export
- Same question stem can legitimately have different answer sets (different educational questions)
- Stems, correct answers, and incorrect answers can all change between "versions" due to:
  - Copyeditor fixes (grammar, acronym expansion like "NSCLC" → "non-small cell lung cancer")
  - Faculty feedback (mid-activity or between activities)
  - Multiple deliverables (live, virtual, recording, written, journal versions)
  - Intentional improvements over 12-month activity lifecycle

## V2 Approach: Hierarchical Validation

This is a **read-only diagnostic layer** that preserves all existing QGDs and tags.

```
Current QGDs (preserved)
         ↓
Step 1: Stem-only embeddings → Find stem clusters
         ↓
Step 2: Within each stem cluster, compare answer set embeddings
         ↓
Step 3: Low answer similarity (<70%)? → LLM triage
         ↓
Output: Recommendations mapped to current QGDs
```

## Key Properties

| Requirement | How It's Handled |
|-------------|------------------|
| Keep MM tags | Read-only analysis, no changes to existing data |
| Keep QGD numbers | All output references existing QGDs |
| Colleague's work preserved | Recommendations only, no automatic changes |
| Mappable | Clear mapping from recommendations to QGDs |

## Folder Structure

```
deduplication_v2/
├── README.md                           # This file
├── scripts/
│   ├── generate_stem_embeddings.py     # Step 1: Stem-only embeddings
│   ├── cluster_by_stem.py              # Step 2: Find stem clusters
│   ├── compare_answer_sets.py          # Step 3: Compare answers within clusters
│   ├── llm_triage_divergent.py         # Step 4: LLM review of low-similarity pairs
│   └── generate_recommendations.py     # Step 5: Output final recommendations
├── data/
│   ├── stem_embeddings.parquet         # Stem-only embeddings (6,802 rows)
│   ├── stem_clusters.json              # Cluster assignments
│   ├── answer_comparisons.json         # Answer similarity within clusters
│   ├── llm_triage_results.json         # LLM verdicts
│   └── final_recommendations.yaml      # Actionable recommendations
└── prompts/
    └── answer_set_triage_prompt.txt    # LLM prompt for triage
```

## Usage

Run scripts in order:

```bash
# Step 1: Generate stem-only embeddings
python deduplication_v2/scripts/generate_stem_embeddings.py

# Step 2: Cluster by stem similarity (90% threshold)
python deduplication_v2/scripts/cluster_by_stem.py

# Step 3: Compare answer sets within clusters
python deduplication_v2/scripts/compare_answer_sets.py

# Step 4: LLM triage for divergent pairs (answer similarity < 70%)
python deduplication_v2/scripts/llm_triage_divergent.py

# Step 5: Generate final recommendations
python deduplication_v2/scripts/generate_recommendations.py
```

## Thresholds

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Stem similarity | 90% | Permissive to catch acronym-expanded versions |
| Answer similarity (flag) | <70% | Pairs with very different answers need review |
| Answer similarity (high) | >=90% | True duplicates with consistent answers |

## Output Categories

The final recommendations categorize each QGD as:

- **canonical**: The preferred version in a cluster
- **true_duplicate**: Same question, can merge tags from canonical
- **different_question**: Keep separate despite similar stem (legitimately different educational content)
- **data_error**: Wrong answer set attached - flag for manual review

## Estimated Costs

| Step | API Calls | Est. Cost |
|------|-----------|-----------|
| Stem embeddings | 6,802 | $0.02 |
| Answer embeddings | 6,802 | $0.02 |
| LLM triage | ~500-1000 | $5-10 |
| **Total** | | **~$10-15** |

## Data Lineage

```
Original Snowflake Export (12,907 rows)
    ↓ [Colleague's join - added QGD, activities, answers]
FullColumnsSample_v2_012026.xlsx (318,553 rows)
    ↓ [Our collation - one row per QGD]
questions_deduplicated_collated_20260121_221852.xlsx (6,802 rows)
    ↓ [This V2 validation layer]
final_recommendations.yaml
```

## Date Created

2026-01-31
