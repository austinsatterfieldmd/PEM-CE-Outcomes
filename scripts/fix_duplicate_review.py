"""
Fix duplicate review file with correct question IDs and add SOURCE column.

This script:
1. Loads the cleaned stage 1 results
2. Finds potential duplicates after acronym normalization
3. Uses QUESTIONGROUPDESIGNATION as the unique question identifier
4. Adds SOURCE column (ONCOLOGY vs MULTISPECIALTY)
5. Exports corrected duplicate review file

Run: python scripts/fix_duplicate_review.py
"""

import pandas as pd
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Set, Tuple
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Common medical acronyms and their expanded forms (same as clean_and_find_duplicates.py)
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


def load_source_mapping(project_root: Path) -> set:
    """
    Load mapping of question IDs to source (ONCOLOGY vs MULTISPECIALTY).

    Logic: Questions in stage2_ready_combined are ONCOLOGY (they passed stage 1
    classification). All other questions are MULTISPECIALTY.
    """
    oncology_ids = set()

    # Load oncology questions from stage2_ready_combined
    oncology_file = project_root / "data/checkpoints/stage2_ready_combined_20260123.xlsx"
    if oncology_file.exists():
        try:
            onc_df = pd.read_excel(oncology_file)
            for _, row in onc_df.iterrows():
                qid = str(row.get('QUESTIONGROUPDESIGNATION', ''))
                if qid:
                    oncology_ids.add(qid)
            print(f"Loaded {len(oncology_ids)} oncology question IDs from stage2_ready_combined")
        except Exception as e:
            print(f"Warning: Could not load oncology file: {e}")
    else:
        print(f"Warning: Oncology file not found: {oncology_file}")

    # Return the set - we'll determine MULTISPECIALTY by exclusion
    return oncology_ids


def find_duplicate_groups(df: pd.DataFrame, question_col: str, id_col: str, oncology_ids: set) -> List[Dict]:
    """
    Find potential duplicates after acronym normalization.
    Uses specified ID column for unique question identification.
    """
    # Build normalized stems
    items = []
    for idx, row in df.iterrows():
        stem = row.get(question_col, '')
        if pd.isna(stem) or not isinstance(stem, str):
            stem = ''

        normalized = normalize_for_comparison(stem)

        # Get the unique ID
        id_val = row.get(id_col)
        if pd.isna(id_val):
            id_val = f"row_{idx}"

        # Determine source: ONCOLOGY if in oncology_ids, else MULTISPECIALTY
        source = "ONCOLOGY" if str(id_val) in oncology_ids else "MULTISPECIALTY"

        # Get activity names for context
        activity_names = row.get('ACTIVITY_NAMES', row.get('Activity_Names', ''))
        if pd.isna(activity_names):
            activity_names = ''

        # Get incorrect answers (IANSWER1-9)
        incorrect_answers = []
        for i in range(1, 10):
            ans = row.get(f'IANSWER{i}', row.get(f'ianswer{i}', ''))
            if pd.notna(ans) and str(ans).strip():
                incorrect_answers.append(str(ans).strip())

        items.append({
            'index': idx,
            'id': str(id_val),
            'original': stem[:300] if stem else '',
            'normalized': normalized[:300] if normalized else '',
            'answer': str(row.get('OPTIMIZEDCORRECTANSWER', row.get('OptimizedCorrectAnswer', row.get('correct_answer', ''))))[:200],
            'incorrect_answers': incorrect_answers,
            'source': source,
            'activity_names': str(activity_names)[:300] if activity_names else ''
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
            # Format incorrect answers as pipe-separated string
            incorrect_ans = item.get('incorrect_answers', [])
            incorrect_ans_str = ' | '.join(incorrect_ans) if incorrect_ans else ''

            rows.append({
                'group_id': group_idx + 1,
                'group_size': group['count'],
                'item_in_group': item_idx + 1,
                'QUESTIONGROUPDESIGNATION': item['id'],
                'SOURCE': item['source'],
                'ACTIVITY_NAMES': item.get('activity_names', ''),
                'original_question': item['original'],
                'normalized_question': item['normalized'][:200],
                'correct_answer': item['answer'],
                'incorrect_answers': incorrect_ans_str,
                'is_duplicate': '',  # For manual review
                'keep_this_one': '',  # For manual review
                'notes': ''  # For manual review
            })

    review_df = pd.DataFrame(rows)
    review_df.to_excel(output_path, index=False)

    print(f"Exported {len(duplicate_groups)} duplicate groups ({len(rows)} total rows) to {output_path}")
    return review_df


def main():
    """Main function."""
    project_root = Path(__file__).parent.parent

    # Find the most recent cleaned file
    checkpoint_dir = project_root / "data/checkpoints"
    cleaned_files = list(checkpoint_dir.glob("stage1_results_cleaned_*.xlsx"))

    if not cleaned_files:
        print("No cleaned stage1 results found in data/checkpoints/")
        return

    # Sort by modification time and get most recent
    cleaned_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    input_path = cleaned_files[0]

    print(f"\n{'='*60}")
    print(f"Processing: {input_path.name}")
    print('='*60)

    # Load data
    df = pd.read_excel(input_path)
    print(f"Loaded {len(df)} rows")
    print(f"Columns: {list(df.columns)[:15]}...")

    # Find question column
    question_col = None
    for col in ['OptimizedQuestion', 'OPTIMIZEDQUESTION', 'optimizedquestion', 'Question', 'stem']:
        if col in df.columns:
            question_col = col
            break

    if not question_col:
        print(f"No question column found. Available columns: {list(df.columns)}")
        return

    # Find ID column - use QUESTIONGROUPDESIGNATION
    id_col = None
    for col in ['QUESTIONGROUPDESIGNATION', 'QuestionGroupDesignation', 'questiongroupdesignation']:
        if col in df.columns:
            id_col = col
            break

    if not id_col:
        print(f"No QUESTIONGROUPDESIGNATION column found. Available columns: {list(df.columns)}")
        return

    print(f"Using columns: question={question_col}, id={id_col}")

    # Verify IDs are unique
    id_counts = df[id_col].value_counts()
    duplicate_ids = id_counts[id_counts > 1]
    if len(duplicate_ids) > 0:
        print(f"\nWARNING: Found {len(duplicate_ids)} duplicate IDs in {id_col}:")
        print(duplicate_ids.head(10))
    else:
        print(f"Verified: All {len(df)} IDs in {id_col} are unique")

    # Load oncology IDs from stage2_ready_combined
    print(f"\n{'='*60}")
    print("LOADING SOURCE MAPPING")
    print('='*60)
    oncology_ids = load_source_mapping(project_root)

    # Find duplicates
    print(f"\n{'='*60}")
    print("FINDING POTENTIAL DUPLICATES")
    print('='*60)

    duplicate_groups = find_duplicate_groups(df, question_col, id_col, oncology_ids)

    print(f"\nFound {len(duplicate_groups)} potential duplicate groups")

    if duplicate_groups:
        total_dupe_questions = sum(g['count'] for g in duplicate_groups)
        print(f"Total questions in duplicate groups: {total_dupe_questions}")

        # Count by source
        source_counts = defaultdict(int)
        for group in duplicate_groups:
            for item in group['items']:
                source_counts[item['source']] += 1
        print(f"By source: {dict(source_counts)}")

        # Show top groups
        print(f"\nTop 5 duplicate groups:")
        for i, group in enumerate(duplicate_groups[:5]):
            print(f"\nGroup {i+1} ({group['count']} items):")
            print(f"  Normalized: {group['normalized_key'][:60]}...")
            for item in group['items'][:3]:
                print(f"    [{item['source']}] ID {item['id']}: {item['original'][:50]}...")

        # Export for review
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        review_output = project_root / f"data/eval/duplicate_review_fixed_{timestamp}.xlsx"
        export_duplicate_review(duplicate_groups, str(review_output))

        print(f"\n{'='*60}")
        print("SUMMARY")
        print('='*60)
        print(f"Total questions: {len(df)}")
        print(f"Potential duplicate groups: {len(duplicate_groups)}")
        print(f"Questions in duplicate groups: {total_dupe_questions}")
        print(f"\nOutput file: {review_output.name}")
        print(f"\nColumns in output:")
        print(f"  - group_id: Duplicate group number")
        print(f"  - group_size: Number of questions in this group")
        print(f"  - item_in_group: Position within the group")
        print(f"  - QUESTIONGROUPDESIGNATION: Unique question ID")
        print(f"  - SOURCE: ONCOLOGY or MULTISPECIALTY")
        print(f"  - ACTIVITY_NAMES: CE activity titles (for context)")
        print(f"  - original_question: Cleaned question text")
        print(f"  - normalized_question: After acronym expansion")
        print(f"  - correct_answer: The correct answer")
        print(f"  - incorrect_answers: All incorrect options (pipe-separated)")
        print(f"  - is_duplicate: (for manual review)")
        print(f"  - keep_this_one: (for manual review)")
        print(f"  - notes: (for manual review)")
    else:
        print("No duplicate groups found!")


if __name__ == "__main__":
    main()
