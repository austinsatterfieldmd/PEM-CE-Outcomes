"""Create review file for Stage 1 classification review."""

import pandas as pd
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

# Load both files
print("Loading data files...")
main_df = pd.read_excel('data/raw/FullColumnsSample_v2_tagged_20260121_223915.xlsx')
batch_df = pd.read_excel('data/checkpoints/stage1_results_20260122_090849.xlsx')

main_unique = main_df.drop_duplicates(subset='QUESTIONGROUPDESIGNATION')
batch_unique = batch_df.drop_duplicates(subset='QUESTIONGROUPDESIGNATION')

def get_qgds_for_disease(disease):
    main_qgds = set(main_unique[main_unique['STAGE1_disease_state'].astype(str).str.strip() == disease]['QUESTIONGROUPDESIGNATION'].tolist())
    batch_qgds = set(batch_unique[batch_unique['FINAL_disease_state'].astype(str).str.strip() == disease]['QUESTIONGROUPDESIGNATION'].tolist())
    return main_qgds | batch_qgds

print("Building review categories...")

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
garbled = get_qgds_for_disease('FALSE (Blank)') | get_qgds_for_disease('Null')

# Rare diseases (<10)
combined_counts = {}
for ds in main_unique['STAGE1_disease_state'].dropna().unique():
    ds_str = str(ds).strip()
    combined_counts[ds_str] = combined_counts.get(ds_str, 0) + len(main_unique[main_unique['STAGE1_disease_state'].astype(str).str.strip() == ds_str])
for ds in batch_unique['FINAL_disease_state'].dropna().unique():
    ds_str = str(ds).strip()
    combined_counts[ds_str] = combined_counts.get(ds_str, 0) + len(batch_unique[batch_unique['FINAL_disease_state'].astype(str).str.strip() == ds_str])

rare_diseases = [ds for ds, count in combined_counts.items() if count < 10]
rare_qgds = set()
for ds in rare_diseases:
    rare_qgds.update(get_qgds_for_disease(ds))

# Disagreement and Gemini failed
disagreement = set(batch_unique[batch_unique['AGREEMENT'] != 'unanimous']['QUESTIONGROUPDESIGNATION'].tolist())
gemini_failed = set(batch_unique[batch_unique['GEMINI_is_oncology'].isna()]['QUESTIONGROUPDESIGNATION'].tolist())

# All QGDs to review
all_review_qgds = pan_tumor | ones | heme | gepnet | falses | ptcl | cmv | gi | gyn | rare_qgds | disagreement | gemini_failed | garbled

print(f"Total questions to review: {len(all_review_qgds)}")

# Build review dataframe
print("Building review dataframe...")
review_rows = []

for qgd in all_review_qgds:
    row = {'QGD': qgd}

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

    # Get data from main file or batch file
    main_row = main_unique[main_unique['QUESTIONGROUPDESIGNATION'] == qgd]
    batch_row = batch_unique[batch_unique['QUESTIONGROUPDESIGNATION'] == qgd]

    if len(main_row) > 0:
        row['SOURCE'] = 'Audited'
        row['QUESTION'] = main_row['OPTIMIZEDQUESTION'].values[0] if pd.notna(main_row['OPTIMIZEDQUESTION'].values[0]) else main_row['RAWQUESTION'].values[0]
        row['ANSWER'] = main_row['OPTIMIZEDCORRECTANSWER'].values[0]
        row['ACTIVITY_NAMES'] = main_unique[main_unique['QUESTIONGROUPDESIGNATION'] == qgd]['COURSENAME'].iloc[0] if 'COURSENAME' in main_unique.columns else ''
        row['CURRENT_is_oncology'] = main_row['STAGE1_is_oncology'].values[0]
        row['CURRENT_disease_state'] = main_row['STAGE1_disease_state'].values[0]
        row['CURRENT_disease_state_secondary'] = main_row['STAGE1_disease_state_secondary'].values[0] if 'STAGE1_disease_state_secondary' in main_row.columns else ''
        row['GPT_is_oncology'] = ''
        row['GPT_disease_state'] = ''
        row['GEMINI_is_oncology'] = ''
        row['GEMINI_disease_state'] = ''
        row['AGREEMENT'] = 'audited'
    elif len(batch_row) > 0:
        row['SOURCE'] = 'Batch'
        row['QUESTION'] = batch_row['OPTIMIZEDQUESTION'].values[0] if pd.notna(batch_row['OPTIMIZEDQUESTION'].values[0]) else batch_row['RAWQUESTION'].values[0]
        row['ANSWER'] = batch_row['OPTIMIZEDCORRECTANSWER'].values[0]
        row['ACTIVITY_NAMES'] = batch_row['ACTIVITY_NAMES'].values[0]
        row['CURRENT_is_oncology'] = batch_row['FINAL_is_oncology'].values[0]
        row['CURRENT_disease_state'] = batch_row['FINAL_disease_state'].values[0]
        row['CURRENT_disease_state_secondary'] = batch_row['FINAL_disease_state_secondary'].values[0] if 'FINAL_disease_state_secondary' in batch_row.columns else ''
        row['GPT_is_oncology'] = batch_row['GPT_is_oncology'].values[0]
        row['GPT_disease_state'] = batch_row['GPT_disease_state'].values[0]
        row['GEMINI_is_oncology'] = batch_row['GEMINI_is_oncology'].values[0]
        row['GEMINI_disease_state'] = batch_row['GEMINI_disease_state'].values[0]
        row['AGREEMENT'] = batch_row['AGREEMENT'].values[0]
    else:
        continue

    # Add correction columns
    row['CORRECT_is_oncology'] = ''
    row['CORRECT_disease_state'] = ''
    row['CORRECT_disease_state_secondary'] = ''
    row['REVIEW_NOTES'] = ''

    review_rows.append(row)

# Create dataframe
review_df = pd.DataFrame(review_rows)

# Sort by review categories then QGD
review_df = review_df.sort_values(['REVIEW_CATEGORIES', 'QGD'])

# Reorder columns
column_order = [
    'QGD', 'REVIEW_CATEGORIES', 'SOURCE', 'AGREEMENT',
    'CURRENT_is_oncology', 'CURRENT_disease_state', 'CURRENT_disease_state_secondary',
    'GPT_is_oncology', 'GPT_disease_state', 'GEMINI_is_oncology', 'GEMINI_disease_state',
    'CORRECT_is_oncology', 'CORRECT_disease_state', 'CORRECT_disease_state_secondary', 'REVIEW_NOTES',
    'QUESTION', 'ANSWER', 'ACTIVITY_NAMES'
]
review_df = review_df[column_order]

# Save
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
output_path = f'data/eval/stage1_review_{timestamp}.xlsx'
review_df.to_excel(output_path, index=False)

print(f"\nSaved to: {output_path}")
print(f"Total rows: {len(review_df)}")
print()
print("Category breakdown:")
for cat, count in review_df['REVIEW_CATEGORIES'].str.split('; ').explode().value_counts().items():
    print(f"  {cat}: {count}")
