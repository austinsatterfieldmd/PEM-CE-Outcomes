"""
Clean existing stage 1 results and export potential duplicates for review.

This script:
1. Applies formatting fixes to question stems and answers
2. Identifies potential duplicates after acronym normalization
3. Exports both cleaned data and duplicate review file

Run: python scripts/clean_and_find_duplicates.py [input_file]
"""

import pandas as pd
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Tuple
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.deduplication.cleanup import (
    clean_text_full,
    detect_formatting_issues,
    detect_encoding_issues,
)

# Common medical acronyms and their expanded forms
ACRONYM_MAP = {
    # Cancer types
    "NSCLC": "non-small cell lung cancer",
    "SCLC": "small cell lung cancer",
    "mCRPC": "metastatic castration-resistant prostate cancer",
    "CRPC": "castration-resistant prostate cancer",
    "CRC": "colorectal cancer",
    "mCRC": "metastatic colorectal cancer",
    "HCC": "hepatocellular carcinoma",
    "RCC": "renal cell carcinoma",
    "mRCC": "metastatic renal cell carcinoma",
    "ccRCC": "clear cell renal cell carcinoma",
    "mccRCC": "metastatic clear cell renal cell carcinoma",
    "AML": "acute myeloid leukemia",
    "CML": "chronic myeloid leukemia",
    "CLL": "chronic lymphocytic leukemia",
    "ALL": "acute lymphoblastic leukemia",
    "NHL": "non-hodgkin lymphoma",
    "DLBCL": "diffuse large b-cell lymphoma",
    "FL": "follicular lymphoma",
    "MCL": "mantle cell lymphoma",
    "MM": "multiple myeloma",
    "MDS": "myelodysplastic syndrome",
    "TNBC": "triple-negative breast cancer",
    "MBC": "metastatic breast cancer",
    "GIST": "gastrointestinal stromal tumor",
    "NET": "neuroendocrine tumor",
    "GEP-NET": "gastroenteropancreatic neuroendocrine tumor",

    # Biomarkers/molecular
    "HR+": "hormone receptor-positive",
    "HR-": "hormone receptor-negative",
    "HER2+": "her2-positive",
    "HER2-": "her2-negative",
    "ER+": "estrogen receptor-positive",
    "ER-": "estrogen receptor-negative",
    "PR+": "progesterone receptor-positive",
    "PR-": "progesterone receptor-negative",
    "EGFR": "epidermal growth factor receptor",
    "ALK": "anaplastic lymphoma kinase",
    "ROS1": "ros proto-oncogene 1",
    "BRAF": "b-raf proto-oncogene",
    "KRAS": "kirsten rat sarcoma viral oncogene",
    "NRAS": "neuroblastoma ras viral oncogene",
    "MET": "mesenchymal epithelial transition factor",
    "RET": "rearranged during transfection",
    "NTRK": "neurotrophic tyrosine receptor kinase",
    "NRG1": "neuregulin 1",
    "PD-1": "programmed cell death protein 1",
    "PD-L1": "programmed death-ligand 1",
    "CTLA-4": "cytotoxic t-lymphocyte-associated protein 4",
    "MSI-H": "microsatellite instability-high",
    "MSI-L": "microsatellite instability-low",
    "MSS": "microsatellite stable",
    "dMMR": "deficient mismatch repair",
    "pMMR": "proficient mismatch repair",
    "TMB": "tumor mutational burden",
    "TMB-H": "tumor mutational burden-high",
    "HRD": "homologous recombination deficiency",
    "BRCA": "breast cancer gene",
    "BRCA1": "breast cancer gene 1",
    "BRCA2": "breast cancer gene 2",

    # Drug classes
    "TKI": "tyrosine kinase inhibitor",
    "mAb": "monoclonal antibody",
    "ADC": "antibody-drug conjugate",
    "CAR-T": "chimeric antigen receptor t-cell",
    "ICI": "immune checkpoint inhibitor",
    "PARP": "poly adp-ribose polymerase",
    "CDK4/6": "cyclin-dependent kinase 4/6",
    "PI3K": "phosphoinositide 3-kinase",
    "mTOR": "mammalian target of rapamycin",
    "VEGF": "vascular endothelial growth factor",
    "BTK": "brutons tyrosine kinase",
    "BCL-2": "b-cell lymphoma 2",
    "FLT3": "fms-like tyrosine kinase 3",
    "IDH": "isocitrate dehydrogenase",

    # Endpoints/outcomes
    "OS": "overall survival",
    "PFS": "progression-free survival",
    "DFS": "disease-free survival",
    "EFS": "event-free survival",
    "RFS": "recurrence-free survival",
    "ORR": "overall response rate",
    "DOR": "duration of response",
    "DCR": "disease control rate",
    "CBR": "clinical benefit rate",
    "CR": "complete response",
    "PR": "partial response",
    "SD": "stable disease",
    "PD": "progressive disease",
    "pCR": "pathologic complete response",

    # Safety
    "AE": "adverse event",
    "SAE": "serious adverse event",
    "irAE": "immune-related adverse event",
    "TRAE": "treatment-related adverse event",
    "DLT": "dose-limiting toxicity",
    "MTD": "maximum tolerated dose",

    # Clinical
    "QoL": "quality of life",
    "ECOG": "eastern cooperative oncology group",
    "PS": "performance status",
    "KPS": "karnofsky performance status",
    "1L": "first-line",
    "2L": "second-line",
    "3L": "third-line",
    "R/R": "relapsed/refractory",
    "CNS": "central nervous system",
    "GI": "gastrointestinal",
    "IV": "intravenous",
    "SC": "subcutaneous",
    "PO": "oral",
    "BID": "twice daily",
    "QD": "once daily",

    # Disease phases (CML specific)
    "CP": "chronic phase",
    "CML-CP": "chronic myeloid leukemia chronic phase",
    "AP": "accelerated phase",
    "BP": "blast phase",
}


def normalize_for_comparison(text: str) -> str:
    """
    Normalize text for duplicate comparison.
    """
    if not text or not isinstance(text, str):
        return ""

    normalized = text.lower()

    # Expand acronyms (longer ones first to avoid partial matches)
    sorted_acronyms = sorted(ACRONYM_MAP.items(), key=lambda x: -len(x[0]))
    for acronym, expanded in sorted_acronyms:
        pattern = r'\b' + re.escape(acronym.lower()) + r'\b'
        normalized = re.sub(pattern, expanded.lower(), normalized)

    # Normalize whitespace
    normalized = re.sub(r'\s+', ' ', normalized)

    # Remove punctuation except essential
    normalized = re.sub(r'[^\w\s\'-]', '', normalized)

    return normalized.strip()


def clean_dataframe(df: pd.DataFrame, question_col: str, answer_col: str = None) -> Tuple[pd.DataFrame, Dict]:
    """
    Clean all question text in a dataframe.

    Returns:
        Tuple of (cleaned_df, stats_dict)
    """
    cleaned_df = df.copy()
    stats = {
        'total_rows': len(df),
        'questions_cleaned': 0,
        'answers_cleaned': 0,
        'total_fixes': 0,
        'fix_types': defaultdict(int),
        'examples': []
    }

    # Clean question column
    for idx, row in df.iterrows():
        original = row.get(question_col, '')
        if pd.isna(original) or not isinstance(original, str):
            continue

        cleaned, fix_counts = clean_text_full(original)

        if fix_counts:
            cleaned_df.at[idx, question_col] = cleaned
            stats['questions_cleaned'] += 1
            stats['total_fixes'] += sum(fix_counts.values())

            for fix_type, count in fix_counts.items():
                stats['fix_types'][fix_type] += count

            # Save example
            if len(stats['examples']) < 20:
                stats['examples'].append({
                    'row': idx,
                    'original': original[:150],
                    'cleaned': cleaned[:150],
                    'fixes': fix_counts
                })

    # Clean answer column if provided
    if answer_col and answer_col in df.columns:
        for idx, row in df.iterrows():
            original = row.get(answer_col, '')
            if pd.isna(original) or not isinstance(original, str):
                continue

            cleaned, fix_counts = clean_text_full(original)

            if fix_counts:
                cleaned_df.at[idx, answer_col] = cleaned
                stats['answers_cleaned'] += 1

    return cleaned_df, stats


def find_duplicate_groups(df: pd.DataFrame, question_col: str) -> List[Dict]:
    """
    Find potential duplicates after acronym normalization.
    """
    # Build normalized stems
    items = []
    for idx, row in df.iterrows():
        stem = row.get(question_col, '')
        if pd.isna(stem) or not isinstance(stem, str):
            stem = ''

        normalized = normalize_for_comparison(stem)

        # Get ID column (try various names)
        id_val = None
        for id_col in ['AnswerSetMerged', 'ANSWERSETMERGED', 'answer_set_merged', 'id', 'ID']:
            if id_col in df.columns:
                id_val = row.get(id_col)
                break
        if id_val is None:
            id_val = idx

        items.append({
            'index': idx,
            'id': id_val,
            'original': stem[:300] if stem else '',
            'normalized': normalized[:300] if normalized else '',
            'answer': str(row.get('OPTIMIZEDCORRECTANSWER', row.get('correct_answer', '')))[:200]
        })

    # Group by normalized text (first 150 chars as key)
    groups = defaultdict(list)
    for item in items:
        if item['normalized'] and len(item['normalized']) > 20:
            key = item['normalized'][:150]
            groups[key].append(item)

    # Filter to groups with multiple entries
    duplicate_groups = []
    for key, group_items in groups.items():
        if len(group_items) > 1:
            duplicate_groups.append({
                'normalized_key': key[:100],
                'count': len(group_items),
                'items': group_items
            })

    # Sort by count descending
    duplicate_groups.sort(key=lambda x: -x['count'])

    return duplicate_groups


def export_duplicate_review(duplicate_groups: List[Dict], output_path: str):
    """
    Export duplicate groups to Excel for manual review.
    """
    rows = []

    for group_idx, group in enumerate(duplicate_groups):
        for item_idx, item in enumerate(group['items']):
            rows.append({
                'group_id': group_idx + 1,
                'group_size': group['count'],
                'item_in_group': item_idx + 1,
                'question_id': item['id'],
                'original_question': item['original'],
                'normalized_question': item['normalized'][:200],
                'correct_answer': item['answer'],
                'is_duplicate': '',  # For manual review
                'keep_this_one': '',  # For manual review
                'notes': ''  # For manual review
            })

    review_df = pd.DataFrame(rows)
    review_df.to_excel(output_path, index=False)

    print(f"Exported {len(duplicate_groups)} duplicate groups ({len(rows)} total rows) to {output_path}")
    return review_df


def main(input_file: str = None):
    """Main function."""
    project_root = Path(__file__).parent.parent

    # Default input file
    if input_file is None:
        input_file = "data/checkpoints/stage1_results_20260122_090849_corrected.xlsx"

    input_path = project_root / input_file

    if not input_path.exists():
        print(f"File not found: {input_path}")
        return

    print(f"\n{'='*60}")
    print(f"Processing: {input_path.name}")
    print('='*60)

    # Load data
    df = pd.read_excel(input_path)
    print(f"Loaded {len(df)} rows")

    # Find question and answer columns
    question_col = None
    for col in ['OptimizedQuestion', 'OPTIMIZEDQUESTION', 'optimizedquestion', 'Question', 'stem']:
        if col in df.columns:
            question_col = col
            break

    answer_col = None
    for col in ['OptimizedCorrectAnswer', 'OPTIMIZEDCORRECTANSWER', 'correct_answer', 'Answer']:
        if col in df.columns:
            answer_col = col
            break

    if not question_col:
        print(f"No question column found. Available columns: {list(df.columns)}")
        return

    print(f"Using columns: question={question_col}, answer={answer_col}")

    # ========================================
    # PART 1: CLEAN DATA
    # ========================================
    print(f"\n{'='*60}")
    print("PART 1: CLEANING DATA")
    print('='*60)

    cleaned_df, clean_stats = clean_dataframe(df, question_col, answer_col)

    print(f"\nCleaning Statistics:")
    print(f"  Total rows: {clean_stats['total_rows']}")
    print(f"  Questions cleaned: {clean_stats['questions_cleaned']}")
    print(f"  Answers cleaned: {clean_stats['answers_cleaned']}")
    print(f"  Total fixes: {clean_stats['total_fixes']}")
    print(f"  Fix types: {dict(clean_stats['fix_types'])}")

    if clean_stats['examples']:
        print(f"\nExample fixes:")
        for ex in clean_stats['examples'][:5]:
            print(f"  Row {ex['row']}:")
            print(f"    Before: {ex['original'][:80]}...")
            print(f"    After:  {ex['cleaned'][:80]}...")
            print(f"    Fixes:  {ex['fixes']}")

    # Save cleaned data
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    cleaned_output = project_root / f"data/checkpoints/stage1_results_cleaned_{timestamp}.xlsx"
    cleaned_df.to_excel(cleaned_output, index=False)
    print(f"\nSaved cleaned data to: {cleaned_output.name}")

    # ========================================
    # PART 2: FIND DUPLICATES
    # ========================================
    print(f"\n{'='*60}")
    print("PART 2: FINDING POTENTIAL DUPLICATES")
    print('='*60)

    duplicate_groups = find_duplicate_groups(cleaned_df, question_col)

    print(f"\nFound {len(duplicate_groups)} potential duplicate groups")

    if duplicate_groups:
        total_dupe_questions = sum(g['count'] for g in duplicate_groups)
        print(f"Total questions in duplicate groups: {total_dupe_questions}")

        # Show top groups
        print(f"\nTop 10 duplicate groups:")
        for i, group in enumerate(duplicate_groups[:10]):
            print(f"\nGroup {i+1} ({group['count']} items):")
            print(f"  Normalized: {group['normalized_key'][:80]}...")
            for item in group['items'][:2]:
                print(f"    ID {item['id']}: {item['original'][:70]}...")

        # Export for review
        review_output = project_root / f"data/eval/duplicate_review_{timestamp}.xlsx"
        export_duplicate_review(duplicate_groups, str(review_output))

    # ========================================
    # SUMMARY
    # ========================================
    print(f"\n{'='*60}")
    print("SUMMARY")
    print('='*60)
    print(f"Total questions: {len(df)}")
    print(f"Questions with formatting fixes: {clean_stats['questions_cleaned']}")
    print(f"Potential duplicate groups: {len(duplicate_groups)}")
    print(f"\nOutput files:")
    print(f"  1. Cleaned data: {cleaned_output.name}")
    if duplicate_groups:
        print(f"  2. Duplicate review: duplicate_review_{timestamp}.xlsx")


if __name__ == "__main__":
    input_file = sys.argv[1] if len(sys.argv) > 1 else None
    main(input_file)
