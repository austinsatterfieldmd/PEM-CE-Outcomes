"""
Fix the 10 error rows in the latest eval batch by re-running them through the classifier.
"""
import asyncio
import pandas as pd
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

from src.core.taggers.disease_classifier import DiseaseClassifier
from src.core.taggers.openrouter_client import get_openrouter_client
from src.core.taggers.review_flagger import ReviewFlagger


async def rerun_error_rows():
    # Load the eval file
    eval_file = 'data/eval/stage1_eval_20260122_023148.xlsx'
    df = pd.read_excel(eval_file)

    # Find error rows (agreement='partial' with no classification data, or missing AGREEMENT)
    error_indices = df[
        (df['AGREEMENT'].isna()) |
        ((df['AGREEMENT'] == 'partial') & (df['FINAL_is_oncology'].isna()))
    ].index.tolist()
    print(f'Re-running {len(error_indices)} error rows: {error_indices}')

    if len(error_indices) == 0:
        print('No error rows to fix!')
        return

    # Initialize
    client = get_openrouter_client()
    classifier = DiseaseClassifier(client=client)
    flagger = ReviewFlagger()

    # Re-run each error row
    for idx in error_indices:
        row = df.loc[idx]
        print(f'\nProcessing row {idx}...')

        # Get input data - ensure strings
        question_text = str(row.get('OPTIMIZEDQUESTION') or row.get('RAWQUESTION') or '')
        correct_answer = str(row.get('OPTIMIZEDCORRECTANSWER') or '')

        # Get activity names
        activity_names = []
        activity_col = row.get('ACTIVITY_NAMES')
        if pd.notna(activity_col):
            activity_names = [a.strip() for a in str(activity_col).split(';') if a.strip()]

        # Get start dates
        start_dates = []
        date_col = row.get('START_DATES')
        if pd.notna(date_col):
            start_dates = [d.strip()[:10] for d in str(date_col).split(';') if d.strip()]

        # Get incorrect answers
        incorrect_answers = []
        for i in range(1, 10):
            col = f'IANSWER{i}'
            if col in row.index and pd.notna(row[col]):
                incorrect_answers.append(str(row[col]))

        try:
            # Call classifier
            result = await classifier.classify(
                question_text=question_text,
                correct_answer=correct_answer,
                activity_names=activity_names,
                start_dates=start_dates,
                incorrect_answers=incorrect_answers
            )

            voting = result.get('voting_details', {})
            gpt_vote = voting.get('gpt', {})
            gemini_vote = voting.get('gemini', {})

            # Get review flags (now with fixed str conversion)
            review_flags = flagger.flag_for_review(
                disease_state=result.get('disease_state'),
                disease_state_secondary=result.get('disease_state_secondary'),
                is_oncology=result.get('is_oncology'),
                agreement=voting.get('agreement', ''),
                activity_names=activity_names,
                question_text=question_text,
                correct_answer=correct_answer,
                voting_details=voting
            )
            review_record = flagger.to_review_record(review_flags)

            # Update the dataframe
            df.at[idx, 'GPT_is_oncology'] = gpt_vote.get('is_oncology')
            df.at[idx, 'GPT_disease_state'] = gpt_vote.get('disease_state')
            df.at[idx, 'GEMINI_is_oncology'] = gemini_vote.get('is_oncology')
            df.at[idx, 'GEMINI_disease_state'] = gemini_vote.get('disease_state')
            df.at[idx, 'FINAL_is_oncology'] = result.get('is_oncology')
            df.at[idx, 'FINAL_disease_state'] = result.get('disease_state')
            df.at[idx, 'FINAL_disease_state_secondary'] = result.get('disease_state_secondary')
            df.at[idx, 'AGREEMENT'] = voting.get('agreement')
            df.at[idx, 'ONCOLOGY_AGREEMENT'] = voting.get('oncology_agreement')
            df.at[idx, 'DISEASE_AGREEMENT'] = voting.get('disease_agreement')
            df.at[idx, 'NEEDS_REVIEW'] = result.get('needs_review')
            df.at[idx, 'REVIEW_REASON'] = result.get('review_reason')
            df.at[idx, 'FLAG_NEEDS_REVIEW'] = review_record.get('needs_review', False)
            df.at[idx, 'FLAG_PRIORITY'] = review_record.get('priority', '')
            df.at[idx, 'FLAG_ERROR_LIKELIHOOD'] = review_record.get('error_likelihood', 0)
            df.at[idx, 'FLAG_ROOT_CAUSES'] = '; '.join(review_record.get('root_causes', []))
            df.at[idx, 'FLAG_COUNT'] = review_record.get('flag_count', 0)
            df.at[idx, 'RAW_VOTING_DETAILS'] = json.dumps(voting, default=str)

            # Clear the error column if it exists
            if 'ERROR' in df.columns:
                df.at[idx, 'ERROR'] = None

            print(f'  is_oncology: {result.get("is_oncology")}, disease: {result.get("disease_state")}, agreement: {voting.get("agreement")}')

        except Exception as e:
            print(f'  ERROR: {e}')

    # Save back
    print('\nSaving updated file...')
    df.to_excel(eval_file, index=False)
    print(f'Saved to {eval_file}')

    # Print final stats
    remaining_errors = df['AGREEMENT'].isna().sum()
    print(f'\nRemaining errors: {remaining_errors}')

    # Show summary
    print('\n=== UPDATED AGREEMENT LEVELS ===')
    print(df['AGREEMENT'].value_counts(dropna=False))


if __name__ == "__main__":
    asyncio.run(rerun_error_rows())
