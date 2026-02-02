"""Create FL (Follicular Lymphoma) outcomes file for grant writer view - rolled up by question."""

import pandas as pd
import numpy as np
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

# Load both files
print("Loading data files...")
main_df = pd.read_excel('data/raw/FullColumnsSample_v2_tagged_20260121_223915.xlsx')
batch_df = pd.read_excel('data/checkpoints/stage1_results_20260122_090849.xlsx')

# Filter for FL questions from both files
print("Filtering for FL questions...")
main_fl = main_df[main_df['STAGE1_disease_state'].astype(str).str.strip() == 'FL']
batch_fl = batch_df[batch_df['FINAL_disease_state'].astype(str).str.strip() == 'FL']

# Get all unique FL QGDs
main_fl_qgds = set(main_fl['QUESTIONGROUPDESIGNATION'].tolist())
batch_fl_qgds = set(batch_fl['QUESTIONGROUPDESIGNATION'].tolist())
all_fl_qgds = main_fl_qgds | batch_fl_qgds
print(f"Combined unique FL questions: {len(all_fl_qgds)}")

# Build rolled-up dataframe - one row per question
rows = []

for qgd in all_fl_qgds:
    # Get all rows for this QGD from main file
    qgd_rows = main_df[main_df['QUESTIONGROUPDESIGNATION'] == qgd]

    if len(qgd_rows) == 0:
        # Fall back to batch file if not in main
        qgd_rows = batch_df[batch_df['QUESTIONGROUPDESIGNATION'] == qgd]
        if len(qgd_rows) == 0:
            continue

    # Get question/answer (same across all rows)
    first_row = qgd_rows.iloc[0]

    row_data = {
        'Question': first_row['OPTIMIZEDQUESTION'] if pd.notna(first_row.get('OPTIMIZEDQUESTION')) else first_row.get('RAWQUESTION', ''),
        'Correct Answer': first_row.get('OPTIMIZEDCORRECTANSWER', ''),
    }

    # Combine incorrect answers into one field
    incorrect = []
    for i in range(1, 10):
        col = f'IANSWER{i}'
        if col in qgd_rows.columns and pd.notna(first_row.get(col)) and str(first_row.get(col)).strip():
            incorrect.append(str(first_row[col]).strip())
    row_data['Incorrect Answers'] = ' | '.join(incorrect) if incorrect else ''

    # Aggregate activity info
    activity_col = 'COURSENAME' if 'COURSENAME' in qgd_rows.columns else 'ACTIVITY_NAMES'
    activities = qgd_rows[activity_col].dropna().unique().tolist() if activity_col in qgd_rows.columns else []
    row_data['# Activities'] = len(activities)
    row_data['Activity Names'] = '; '.join(sorted(set(str(a) for a in activities)))

    # Date range
    if 'STARTDATE' in qgd_rows.columns:
        dates = pd.to_datetime(qgd_rows['STARTDATE'], errors='coerce').dropna()
        if len(dates) > 0:
            row_data['Earliest Activity'] = dates.min().strftime('%Y-%m-%d')
            row_data['Latest Activity'] = dates.max().strftime('%Y-%m-%d')
        else:
            row_data['Earliest Activity'] = ''
            row_data['Latest Activity'] = ''
    else:
        row_data['Earliest Activity'] = ''
        row_data['Latest Activity'] = ''

    # Aggregate scoring data
    # PRESCORECALC = number correct, PRESCOREN = total responses
    # Percentage = sum(correct) / sum(total) across all activities

    total_pre_correct = 0
    total_pre_n = 0
    total_post_correct = 0
    total_post_n = 0

    if 'PRESCORECALC' in qgd_rows.columns and 'PRESCOREN' in qgd_rows.columns:
        valid = qgd_rows[['PRESCORECALC', 'PRESCOREN']].dropna()
        total_pre_correct = int(valid['PRESCORECALC'].sum())
        total_pre_n = int(valid['PRESCOREN'].sum())

    if 'POSTSCORECALC' in qgd_rows.columns and 'POSTSCOREN' in qgd_rows.columns:
        valid = qgd_rows[['POSTSCORECALC', 'POSTSCOREN']].dropna()
        total_post_correct = int(valid['POSTSCORECALC'].sum())
        total_post_n = int(valid['POSTSCOREN'].sum())

    row_data['Total Pre N'] = total_pre_n
    row_data['Total Post N'] = total_post_n

    # Calculate percentages: correct / total
    if total_pre_n > 0:
        row_data['Avg Pre Score %'] = round((total_pre_correct / total_pre_n) * 100, 1)
    else:
        row_data['Avg Pre Score %'] = ''

    if total_post_n > 0:
        row_data['Avg Post Score %'] = round((total_post_correct / total_post_n) * 100, 1)
    else:
        row_data['Avg Post Score %'] = ''

    # Calculate improvement
    if row_data['Avg Pre Score %'] != '' and row_data['Avg Post Score %'] != '':
        row_data['Score Change'] = round(row_data['Avg Post Score %'] - row_data['Avg Pre Score %'], 1)
    else:
        row_data['Score Change'] = ''

    rows.append(row_data)

# Create dataframe
output_df = pd.DataFrame(rows)

# Reorder columns
column_order = [
    'Question', 'Correct Answer', 'Incorrect Answers',
    '# Activities', 'Activity Names', 'Earliest Activity', 'Latest Activity',
    'Total Pre N', 'Total Post N', 'Avg Pre Score %', 'Avg Post Score %', 'Score Change'
]
output_df = output_df[[c for c in column_order if c in output_df.columns]]

# Sort by number of activities (most used first), then by Total Pre N
output_df = output_df.sort_values(['# Activities', 'Total Pre N'], ascending=[False, False])

# Save to Outcomes folder
output_path = 'Outcomes/FL_Questions_GrantWriter.xlsx'
output_df.to_excel(output_path, index=False)

print(f"\nSaved to: {output_path}")
print(f"Total questions: {len(output_df)}")
print(f"\nSummary:")
print(f"  Total learners (Pre N): {output_df['Total Pre N'].sum():,}")
print(f"  Total learners (Post N): {output_df['Total Post N'].sum():,}")
print(f"  Activities per question: {output_df['# Activities'].min()} - {output_df['# Activities'].max()}")
