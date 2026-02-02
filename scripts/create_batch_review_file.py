"""Create review file for Stage 1 classification review - BATCH ONLY.

Sources only from the new batch results (5,426 questions).
Layout matches stage1_eval template format.
"""

import pandas as pd
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

# Load ONLY the batch file
print("Loading batch file...")
batch_df = pd.read_excel('data/checkpoints/stage1_results_20260122_090849.xlsx')
print(f"Total questions in batch: {len(batch_df)}")

# Get unique questions
batch_unique = batch_df.drop_duplicates(subset='QUESTIONGROUPDESIGNATION')
print(f"Unique questions: {len(batch_unique)}")

def get_qgds_for_disease(disease):
    """Get QGDs matching a disease state from batch file."""
    return set(batch_unique[batch_unique['FINAL_disease_state'].astype(str).str.strip() == disease]['QUESTIONGROUPDESIGNATION'].tolist())

print("\nBuilding review categories...")

# Build category sets
pan_tumor = get_qgds_for_disease('Pan-tumor')
ones = get_qgds_for_disease('1')
heme = get_qgds_for_disease('Heme malignancies')
gepnet = get_qgds_for_disease('GEP-NET')
falses = get_qgds_for_disease('False')
ptcl = get_qgds_for_disease('PTCL')
cmv = get_qgds_for_disease('CMV')
gi = get_qgds_for_disease('GI cancers')
gyn = get_qgds_for_disease('Gyn cancers')
garbled = get_qgds_for_disease('FALSE (Blank)') | get_qgds_for_disease('Null') | get_qgds_for_disease('')

# Count disease states for "rare" threshold
disease_counts = batch_unique['FINAL_disease_state'].astype(str).str.strip().value_counts().to_dict()
rare_diseases = [ds for ds, count in disease_counts.items() if count < 10 and ds not in ['', 'nan', 'None']]
rare_qgds = set()
for ds in rare_diseases:
    rare_qgds.update(get_qgds_for_disease(ds))

# Disagreement and Gemini failed
disagreement = set(batch_unique[batch_unique['AGREEMENT'] != 'unanimous']['QUESTIONGROUPDESIGNATION'].tolist())
gemini_failed = set(batch_unique[batch_unique['GEMINI_is_oncology'].isna()]['QUESTIONGROUPDESIGNATION'].tolist())

# Print category counts
print(f"  Pan-tumor: {len(pan_tumor)}")
print(f"  Error '1': {len(ones)}")
print(f"  Heme malignancies: {len(heme)}")
print(f"  GEP-NET: {len(gepnet)}")
print(f"  Error 'False': {len(falses)}")
print(f"  PTCL: {len(ptcl)}")
print(f"  CMV: {len(cmv)}")
print(f"  GI cancers: {len(gi)}")
print(f"  Gyn cancers: {len(gyn)}")
print(f"  Error garbled: {len(garbled)}")
print(f"  Rare (<10): {len(rare_qgds)}")
print(f"  Disagreement: {len(disagreement)}")
print(f"  Gemini failed: {len(gemini_failed)}")

# All QGDs to review
all_review_qgds = (pan_tumor | ones | heme | gepnet | falses | ptcl | cmv |
                   gi | gyn | rare_qgds | disagreement | gemini_failed | garbled)

print(f"\nTotal unique questions to review: {len(all_review_qgds)}")

# Build review dataframe
print("Building review dataframe...")
review_rows = []

for qgd in all_review_qgds:
    batch_row = batch_unique[batch_unique['QUESTIONGROUPDESIGNATION'] == qgd]

    if len(batch_row) == 0:
        continue

    row = batch_row.iloc[0].to_dict()

    # Determine review categories
    categories = []
    if qgd in pan_tumor: categories.append('Pan-tumor')
    if qgd in ones: categories.append('Error: "1"')
    if qgd in heme: categories.append('Heme malignancies')
    if qgd in gepnet: categories.append('GEP-NET')
    if qgd in falses: categories.append('Error: "False"')
    if qgd in ptcl: categories.append('PTCL')
    if qgd in cmv: categories.append('CMV')
    if qgd in gi: categories.append('GI cancers')
    if qgd in gyn: categories.append('Gyn cancers')
    if qgd in garbled: categories.append('Error: Garbled')
    if qgd in rare_qgds and qgd not in (pan_tumor | ones | heme | gepnet | falses | ptcl | cmv | gi | gyn | garbled):
        categories.append('Rare (<10)')
    if qgd in disagreement: categories.append('GPT/Gemini disagree')
    if qgd in gemini_failed: categories.append('Gemini failed')

    row['REVIEW_CATEGORIES'] = '; '.join(categories)

    review_rows.append(row)

# Create dataframe
review_df = pd.DataFrame(review_rows)

# Reorder columns to match template format
column_order = [
    'QUESTIONGROUPDESIGNATION', 'REVIEW_CATEGORIES',
    'ACTIVITY_NAMES', 'START_DATES', 'ACTIVITY_COUNT',
    'OPTIMIZEDQUESTION', 'RAWQUESTION', 'OPTIMIZEDCORRECTANSWER',
    'GPT_is_oncology', 'GPT_disease_state',
    'GEMINI_is_oncology', 'GEMINI_disease_state',
    'FINAL_is_oncology', 'FINAL_disease_state', 'FINAL_disease_state_secondary',
    'AGREEMENT', 'ONCOLOGY_AGREEMENT', 'DISEASE_AGREEMENT',
    'NEEDS_REVIEW', 'REVIEW_PRIORITY', 'ERROR_LIKELIHOOD', 'ROOT_CAUSES', 'REVIEW_REASON',
    'CORRECT_is_oncology', 'CORRECT_disease_state', 'REVIEW_NOTES'
]
review_df = review_df[[c for c in column_order if c in review_df.columns]]

# Sort by review categories then QGD
review_df = review_df.sort_values(['REVIEW_CATEGORIES', 'QUESTIONGROUPDESIGNATION'])

# Save
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
output_path = f'data/eval/batch_review_{timestamp}.xlsx'
review_df.to_excel(output_path, index=False)

print(f"\nSaved to: {output_path}")
print(f"Total rows: {len(review_df)}")
print()
print("Category breakdown:")
for cat, count in review_df['REVIEW_CATEGORIES'].str.split('; ').explode().value_counts().items():
    print(f"  {cat}: {count}")
