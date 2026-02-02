"""
Analyze questions for:
1. Formatting issues (missing spaces after periods, concatenated words)
2. Potential duplicates with acronym/abbreviation differences

Run: python scripts/analyze_formatting_and_duplicates.py
"""

import pandas as pd
import re
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Common medical acronyms and their expanded forms
ACRONYM_MAP = {
    "NSCLC": "non-small cell lung cancer",
    "SCLC": "small cell lung cancer",
    "mCRPC": "metastatic castration-resistant prostate cancer",
    "CRPC": "castration-resistant prostate cancer",
    "CRC": "colorectal cancer",
    "mCRC": "metastatic colorectal cancer",
    "HCC": "hepatocellular carcinoma",
    "RCC": "renal cell carcinoma",
    "AML": "acute myeloid leukemia",
    "CML": "chronic myeloid leukemia",
    "CLL": "chronic lymphocytic leukemia",
    "ALL": "acute lymphoblastic leukemia",
    "NHL": "non-Hodgkin lymphoma",
    "DLBCL": "diffuse large B-cell lymphoma",
    "MM": "multiple myeloma",
    "MDS": "myelodysplastic syndrome",
    "TNBC": "triple-negative breast cancer",
    "HR+": "hormone receptor-positive",
    "HER2+": "HER2-positive",
    "HER2-": "HER2-negative",
    "EGFR": "epidermal growth factor receptor",
    "ALK": "anaplastic lymphoma kinase",
    "ROS1": "ROS proto-oncogene 1",
    "BRAF": "B-Raf proto-oncogene",
    "KRAS": "Kirsten rat sarcoma viral oncogene",
    "PD-1": "programmed cell death protein 1",
    "PD-L1": "programmed death-ligand 1",
    "CTLA-4": "cytotoxic T-lymphocyte-associated protein 4",
    "TKI": "tyrosine kinase inhibitor",
    "mAb": "monoclonal antibody",
    "ADC": "antibody-drug conjugate",
    "CAR-T": "chimeric antigen receptor T-cell",
    "ICI": "immune checkpoint inhibitor",
    "OS": "overall survival",
    "PFS": "progression-free survival",
    "ORR": "overall response rate",
    "DOR": "duration of response",
    "CR": "complete response",
    "PR": "partial response",
    "SD": "stable disease",
    "PD": "progressive disease",
    "AE": "adverse event",
    "SAE": "serious adverse event",
    "irAE": "immune-related adverse event",
    "QoL": "quality of life",
    "ECOG": "Eastern Cooperative Oncology Group",
    "PS": "performance status",
    "1L": "first-line",
    "2L": "second-line",
    "R/R": "relapsed/refractory",
    "CNS": "central nervous system",
    "GI": "gastrointestinal",
    "GIST": "gastrointestinal stromal tumor",
    "NET": "neuroendocrine tumor",
    "MET": "mesenchymal epithelial transition factor",
    "NRG1": "neuregulin 1",
    "NTRK": "neurotrophic tyrosine receptor kinase",
    "RET": "rearranged during transfection",
    "MSI-H": "microsatellite instability-high",
    "dMMR": "deficient mismatch repair",
    "TMB": "tumor mutational burden",
    "HRD": "homologous recombination deficiency",
    "BRCA": "breast cancer gene",
    "PARP": "poly ADP-ribose polymerase",
    "CDK4/6": "cyclin-dependent kinase 4/6",
    "PI3K": "phosphoinositide 3-kinase",
    "mTOR": "mammalian target of rapamycin",
    "VEGF": "vascular endothelial growth factor",
    "BTK": "Bruton's tyrosine kinase",
    "BCL-2": "B-cell lymphoma 2",
    "FLT3": "FMS-like tyrosine kinase 3",
    "IDH": "isocitrate dehydrogenase",
    "EZH2": "enhancer of zeste homolog 2",
}


def detect_formatting_issues(text: str) -> Dict[str, List[str]]:
    """
    Detect formatting issues in text.

    Returns dict with issue type -> list of examples found.
    """
    if not text or not isinstance(text, str):
        return {}

    issues = defaultdict(list)

    # 1. Missing space after period followed by capital letter
    # Matches: "treatment.The" but not "Dr.Smith" or "U.S.A."
    pattern_period_capital = r'(?<![A-Z])\.(?=[A-Z][a-z])'
    matches = re.findall(r'(\w+\.)[A-Z][a-z]+', text)
    for match in matches:
        # Exclude common abbreviations
        if match.lower() not in ['dr.', 'mr.', 'ms.', 'mrs.', 'vs.', 'etc.', 'e.g.', 'i.e.']:
            issues['missing_space_after_period'].append(match)

    # 2. Missing space after comma followed by letter
    pattern_comma = r',(?=[A-Za-z])'
    if re.search(pattern_comma, text):
        matches = re.findall(r'(\w+,)[A-Za-z]', text)
        issues['missing_space_after_comma'].extend(matches)

    # 3. Missing space after colon followed by letter (not in time like 10:30)
    pattern_colon = r'(?<!\d):(?=[A-Za-z])'
    if re.search(pattern_colon, text):
        matches = re.findall(r'(\w+:)[A-Za-z]', text)
        issues['missing_space_after_colon'].extend(matches)

    # 4. Missing space after semicolon
    pattern_semi = r';(?=[A-Za-z])'
    if re.search(pattern_semi, text):
        matches = re.findall(r'(\w+;)[A-Za-z]', text)
        issues['missing_space_after_semicolon'].extend(matches)

    # 5. Multiple consecutive spaces
    if '  ' in text:
        issues['multiple_spaces'].append('(found)')

    # 6. Concatenated words - lowercase followed immediately by uppercase mid-word
    # Matches: "cancerPatients" or "treatmentThe"
    pattern_concat = r'[a-z][A-Z]'
    concat_matches = re.findall(r'\b(\w+[a-z][A-Z]\w*)\b', text)
    # Filter out camelCase programming terms and known patterns
    for match in concat_matches:
        # Skip if it's a known acronym pattern (like HER2)
        if not any(acr in match for acr in ['HER2', 'PD-L', 'CDK4', 'BCL-2']):
            issues['possible_concatenated_words'].append(match)

    # 7. Missing space before parenthesis
    pattern_paren = r'[a-zA-Z]\('
    if re.search(pattern_paren, text):
        matches = re.findall(r'(\w+)\(', text)
        issues['missing_space_before_paren'].extend(matches)

    return dict(issues)


def normalize_for_comparison(text: str) -> str:
    """
    Normalize text for duplicate comparison:
    - Lowercase
    - Expand acronyms
    - Remove extra whitespace
    - Remove punctuation (except essential)
    """
    if not text or not isinstance(text, str):
        return ""

    normalized = text.lower()

    # Expand acronyms (case-insensitive replacement)
    for acronym, expanded in ACRONYM_MAP.items():
        # Match whole word only
        pattern = r'\b' + re.escape(acronym.lower()) + r'\b'
        normalized = re.sub(pattern, expanded.lower(), normalized)

    # Normalize whitespace
    normalized = re.sub(r'\s+', ' ', normalized)

    # Remove punctuation except essential (keep apostrophes, hyphens)
    normalized = re.sub(r'[^\w\s\'-]', '', normalized)

    return normalized.strip()


def find_potential_duplicates(df: pd.DataFrame, stem_col: str = 'OptimizedQuestion') -> List[Dict]:
    """
    Find potential duplicates by comparing normalized text.
    """
    # Build normalized stems
    stems = []
    for idx, row in df.iterrows():
        stem = row.get(stem_col, '')
        # Handle non-string values
        if pd.isna(stem) or not isinstance(stem, str):
            stem = ''
        normalized = normalize_for_comparison(stem)
        stems.append({
            'index': idx,
            'original': stem[:200],  # Truncate for display
            'normalized': normalized,
            'id': row.get('AnswerSetMerged', row.get('answer_set_merged', idx))
        })

    # Group by normalized stem
    groups = defaultdict(list)
    for item in stems:
        if item['normalized']:
            # Use first 100 chars of normalized as key (to catch near-matches)
            key = item['normalized'][:100]
            groups[key].append(item)

    # Find groups with multiple entries
    duplicates = []
    for key, items in groups.items():
        if len(items) > 1:
            duplicates.append({
                'normalized_key': key[:80],
                'count': len(items),
                'items': items
            })

    return duplicates


def find_near_duplicates_levenshtein(df: pd.DataFrame, stem_col: str = 'OptimizedQuestion',
                                      threshold: float = 0.9) -> List[Dict]:
    """
    Find near-duplicates using normalized text comparison.
    Uses simple ratio comparison for speed.
    """
    from difflib import SequenceMatcher

    stems = []
    for idx, row in df.iterrows():
        stem = row.get(stem_col, '') or ''
        normalized = normalize_for_comparison(stem)
        if len(normalized) > 20:  # Skip very short questions
            stems.append({
                'index': idx,
                'original': stem[:200],
                'normalized': normalized,
                'id': row.get('AnswerSetMerged', row.get('answer_set_merged', idx))
            })

    near_duplicates = []
    n = len(stems)

    # Compare all pairs (expensive but thorough)
    print(f"Comparing {n} questions for near-duplicates...")
    for i in range(n):
        for j in range(i + 1, n):
            # Quick length check first
            len_ratio = min(len(stems[i]['normalized']), len(stems[j]['normalized'])) / \
                       max(len(stems[i]['normalized']), len(stems[j]['normalized']))

            if len_ratio < threshold:
                continue

            # Detailed comparison
            ratio = SequenceMatcher(None,
                                   stems[i]['normalized'],
                                   stems[j]['normalized']).ratio()

            if ratio >= threshold:
                near_duplicates.append({
                    'similarity': ratio,
                    'item1': stems[i],
                    'item2': stems[j]
                })

        # Progress indicator
        if i % 500 == 0 and i > 0:
            print(f"  Processed {i}/{n} questions...")

    # Sort by similarity descending
    near_duplicates.sort(key=lambda x: -x['similarity'])

    return near_duplicates


def analyze_file(file_path: str):
    """Analyze a file for formatting issues and duplicates."""
    print(f"\n{'='*60}")
    print(f"Analyzing: {Path(file_path).name}")
    print('='*60)

    # Load data
    if file_path.endswith('.xlsx'):
        df = pd.read_excel(file_path)
    elif file_path.endswith('.csv'):
        df = pd.read_csv(file_path)
    else:
        print(f"Unsupported file format: {file_path}")
        return

    print(f"Loaded {len(df)} rows")
    print(f"Columns: {list(df.columns)[:10]}...")

    # Find question column - prefer OptimizedQuestion
    preferred_cols = ['OptimizedQuestion', 'OPTIMIZEDQUESTION', 'optimizedquestion',
                      'question_stem', 'stem', 'Question']
    question_col = None
    for col in preferred_cols:
        if col in df.columns:
            question_col = col
            break

    if not question_col:
        # Fallback to any column with 'question' in name (excluding IDs)
        question_cols = [c for c in df.columns
                        if 'question' in c.lower() and 'id' not in c.lower()
                        and 'designation' not in c.lower()]
        if question_cols:
            question_col = question_cols[0]

    if not question_col:
        print("No question column found!")
        print(f"Available columns: {list(df.columns)}")
        return
    print(f"Using column: {question_col}")

    # ========================================
    # PART 1: FORMATTING ISSUES
    # ========================================
    print(f"\n{'='*60}")
    print("PART 1: FORMATTING ISSUES")
    print('='*60)

    all_issues = defaultdict(list)
    questions_with_issues = 0

    for idx, row in df.iterrows():
        text = row.get(question_col, '')
        issues = detect_formatting_issues(text)

        if issues:
            questions_with_issues += 1
            for issue_type, examples in issues.items():
                all_issues[issue_type].append({
                    'row': idx,
                    'id': row.get('AnswerSetMerged', row.get('answer_set_merged', idx)),
                    'examples': examples,
                    'text_preview': str(text)[:150]
                })

    print(f"\nQuestions with formatting issues: {questions_with_issues}/{len(df)} "
          f"({questions_with_issues/len(df)*100:.1f}%)")

    print("\nIssue breakdown:")
    for issue_type, items in sorted(all_issues.items(), key=lambda x: -len(x[1])):
        print(f"  - {issue_type}: {len(items)} questions")

    # Show examples of each issue type
    print("\n--- Examples of each issue type ---")
    for issue_type, items in all_issues.items():
        print(f"\n{issue_type.upper()} ({len(items)} cases):")
        for item in items[:3]:  # Show first 3 examples
            print(f"  Row {item['row']} (ID: {item['id']}):")
            print(f"    Examples: {item['examples'][:3]}")
            print(f"    Text: {item['text_preview'][:100]}...")

    # ========================================
    # PART 2: POTENTIAL DUPLICATES
    # ========================================
    print(f"\n{'='*60}")
    print("PART 2: POTENTIAL DUPLICATES (after acronym normalization)")
    print('='*60)

    # Exact matches after normalization
    exact_dupes = find_potential_duplicates(df, question_col)
    print(f"\nExact matches after normalization: {len(exact_dupes)} groups")

    if exact_dupes:
        print("\n--- Top 10 exact duplicate groups ---")
        for group in exact_dupes[:10]:
            print(f"\nGroup ({group['count']} items):")
            print(f"  Normalized: {group['normalized_key'][:80]}...")
            for item in group['items'][:3]:
                print(f"    ID {item['id']}: {item['original'][:80]}...")

    # Near-duplicates (expensive - limit sample size)
    if len(df) <= 2000:
        print(f"\n--- Finding near-duplicates (90%+ similarity after normalization) ---")
        near_dupes = find_near_duplicates_levenshtein(df, question_col, threshold=0.90)
        print(f"Near-duplicates found: {len(near_dupes)}")

        if near_dupes:
            print("\n--- Top 20 near-duplicate pairs ---")
            for pair in near_dupes[:20]:
                print(f"\nSimilarity: {pair['similarity']:.1%}")
                print(f"  Q1 (ID {pair['item1']['id']}): {pair['item1']['original'][:80]}...")
                print(f"  Q2 (ID {pair['item2']['id']}): {pair['item2']['original'][:80]}...")
    else:
        print(f"\n[Skipping near-duplicate search for large file ({len(df)} rows)]")
        print("  To run on a subset, modify the script.")

    # ========================================
    # SUMMARY
    # ========================================
    print(f"\n{'='*60}")
    print("SUMMARY")
    print('='*60)
    print(f"Total questions analyzed: {len(df)}")
    print(f"Questions with formatting issues: {questions_with_issues}")
    print(f"Exact duplicate groups (after normalization): {len(exact_dupes)}")

    return {
        'formatting_issues': dict(all_issues),
        'exact_duplicates': exact_dupes,
        'total_questions': len(df),
        'questions_with_issues': questions_with_issues
    }


if __name__ == "__main__":
    # Default file to analyze
    default_file = "data/checkpoints/stage1_results_20260122_090849_corrected.xlsx"

    # Allow command line argument
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = default_file

    # Make path absolute
    project_root = Path(__file__).parent.parent
    file_path = project_root / file_path

    if not file_path.exists():
        print(f"File not found: {file_path}")
        print("\nAvailable files in data/checkpoints:")
        for f in (project_root / "data/checkpoints").glob("*.xlsx"):
            print(f"  {f.name}")
        sys.exit(1)

    analyze_file(str(file_path))
