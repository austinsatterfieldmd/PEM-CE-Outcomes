"""Apply corrections from review file to main batch results."""

import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')

# Load both files
print('Loading files...')
batch_df = pd.read_excel('data/checkpoints/stage1_results_20260122_090849.xlsx')
review_df = pd.read_excel('data/eval/batch_review_20260123_125350_reviewed.xlsx')

print(f'Batch file: {len(batch_df)} rows')
print(f'Review file: {len(review_df)} rows')

# Get corrections from review file
corrections = review_df[review_df['CORRECT_is_oncology'].notna() | review_df['CORRECT_disease_state'].notna()]
print(f'Rows with corrections: {len(corrections)}')

# Apply corrections
updated_onc = 0
updated_disease = 0

for _, row in corrections.iterrows():
    qgd = row['QUESTIONGROUPDESIGNATION']
    mask = batch_df['QUESTIONGROUPDESIGNATION'] == qgd

    if not mask.any():
        print(f'  Warning: QGD {qgd} not found in batch file')
        continue

    # Update is_oncology if correction provided
    if pd.notna(row['CORRECT_is_oncology']):
        old_val = batch_df.loc[mask, 'FINAL_is_oncology'].iloc[0]
        new_val = int(row['CORRECT_is_oncology'])
        if old_val != new_val:
            batch_df.loc[mask, 'FINAL_is_oncology'] = new_val
            updated_onc += 1

    # Update disease_state if correction provided
    if pd.notna(row['CORRECT_disease_state']):
        old_val = batch_df.loc[mask, 'FINAL_disease_state'].iloc[0]
        new_val = row['CORRECT_disease_state']
        if str(old_val) != str(new_val):
            batch_df.loc[mask, 'FINAL_disease_state'] = new_val
            updated_disease += 1

print(f'\nUpdated is_oncology: {updated_onc} rows')
print(f'Updated disease_state: {updated_disease} rows')

# Save updated batch file
output_path = 'data/checkpoints/stage1_results_20260122_090849_corrected.xlsx'
batch_df.to_excel(output_path, index=False)
print(f'\nSaved corrected batch file to: {output_path}')
