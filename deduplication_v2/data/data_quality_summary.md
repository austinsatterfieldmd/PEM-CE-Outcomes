# Data Quality Analysis Summary

**Generated:** 2026-01-31 15:19

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
| Total QGDs | 6,802 |
| Singleton clusters (unique) | 5,824 |
| Multi-member clusters | 447 |

### Oncology Questions Only
| Category | Count | % of Oncology |
|----------|-------|---------------|
| Total Oncology QGDs | 3,634 | 100% |
| Singletons (unique) | 3,076 | 84.6% |
| Canonical (cluster representatives) | 261 | 7.2% |
| True Duplicates | 260 | 7.2% |
| Different Questions | 17 | 0.5% |
| **Data Errors** | **20** | **0.6%** |

### Unique Oncology Questions
**3,354** unique oncology questions (excluding duplicates and data errors)

## Data Errors Detail

20 oncology questions have been flagged as potential data errors. These are cases where:
- Two QGDs share nearly identical question stems (90%+ similarity)
- But have very different answer sets (<70% similarity)
- LLM determined the answer mismatch is likely a data join error, not intentional variation

**See:** `oncology_data_errors_for_review_v2.xlsx` for full details with question stems and both answer sets.

## Files Generated

| File | Description |
|------|-------------|
| `canonical_mapping.csv` | Maps every QGD to its canonical + status |
| `flagged_qgds_for_tagging.txt` | 20 QGDs to skip during tagging |
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
