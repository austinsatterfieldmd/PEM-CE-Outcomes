"""
Analyze LLM model performance from Stage 1 evaluation results.
"""

import pandas as pd
import numpy as np


def normalize(val):
    """Normalize disease state for comparison."""
    if pd.isna(val) or val == '' or val is None:
        return None
    return str(val).strip().lower()


def get_truth_disease(row):
    """Get ground truth disease state."""
    corr = row['CORRECT_disease_state']
    if pd.notna(corr) and corr != '':
        return corr
    return row['FINAL_disease_state']


def get_truth_onc(row):
    """Get ground truth oncology status."""
    corr = row['CORRECT_is_oncology']
    if pd.notna(corr) and corr != '':
        return corr
    return row['FINAL_is_oncology']


def main():
    # Load the reviewed file
    df = pd.read_excel('data/eval/stage1_eval_20260121_145544_reviewed.xlsx')

    print('=== LLM PERFORMANCE ANALYSIS (700 Questions) ===')
    print(f'Total questions: {len(df)}')
    print()

    # Get ground truth
    df['TRUTH_disease_state'] = df.apply(get_truth_disease, axis=1)
    df['TRUTH_is_oncology'] = df.apply(get_truth_onc, axis=1)

    models = ['GPT', 'CLAUDE', 'GEMINI']
    results = {}

    for model in models:
        disease_col = f'{model}_disease_state'
        onc_col = f'{model}_is_oncology'

        # Count responses
        responded = df[disease_col].notna() | df[onc_col].notna()
        n_responded = responded.sum()

        # Disease state accuracy
        disease_correct = df.apply(
            lambda row, dc=disease_col: normalize(row[dc]) == normalize(row['TRUTH_disease_state']),
            axis=1
        )

        # is_oncology accuracy
        onc_correct = df.apply(
            lambda row, oc=onc_col: row[oc] == row['TRUTH_is_oncology'] if pd.notna(row[oc]) else False,
            axis=1
        )

        both_correct = disease_correct & onc_correct

        results[model] = {
            'responded': n_responded,
            'disease_correct': disease_correct.sum(),
            'onc_correct': onc_correct.sum(),
            'both_correct': both_correct.sum(),
        }

    print('=== ACCURACY BY MODEL ===')
    print(f'Model      Responded    Disease Correct    Oncology Correct   Both Correct')
    print('-' * 75)

    for model in models:
        r = results[model]
        d_pct = r['disease_correct'] / len(df) * 100
        o_pct = r['onc_correct'] / len(df) * 100
        b_pct = r['both_correct'] / len(df) * 100
        print(f'{model:<10} {r["responded"]:<12} {r["disease_correct"]:>4} ({d_pct:>5.1f}%)     {r["onc_correct"]:>4} ({o_pct:>5.1f}%)      {r["both_correct"]:>4} ({b_pct:>5.1f}%)')

    print()

    # SSL/API errors
    print('=== SSL/API ERRORS ===')
    error_models_col = df['ERROR_MODELS'].fillna('')
    for model in ['gpt', 'claude', 'gemini']:
        count = error_models_col.str.contains(model, case=False).sum()
        print(f'{model.upper()}: {count} SSL/API errors')

    print()

    # Disagreement analysis
    print('=== DISAGREEMENT ANALYSIS ===')
    disagreements = df[df['AGREEMENT'].isin(['majority', 'conflict'])]
    print(f'Total true disagreements (excluding partial_response): {len(disagreements)}')

    if len(disagreements) > 0:
        model_wins = {m: 0 for m in models}
        for idx, row in disagreements.iterrows():
            truth = normalize(row['TRUTH_disease_state'])
            for model in models:
                if normalize(row[f'{model}_disease_state']) == truth:
                    model_wins[model] += 1

        print(f'Model had correct answer in disagreements:')
        for model in models:
            pct = model_wins[model] / len(disagreements) * 100
            print(f'  {model}: {model_wins[model]} ({pct:.1f}%)')

    print()

    # Clean comparison (all 3 responded)
    print('=== ACCURACY (ROWS WITH ALL 3 MODELS RESPONDING) ===')
    clean_df = df[df['MODELS_RESPONDED'] == 3]
    print(f'Rows where all 3 models responded: {len(clean_df)}')

    for model in models:
        disease_col = f'{model}_disease_state'
        disease_correct = clean_df.apply(
            lambda row, dc=disease_col: normalize(row[dc]) == normalize(row['TRUTH_disease_state']),
            axis=1
        )
        pct = disease_correct.sum() / len(clean_df) * 100
        print(f'{model}: {disease_correct.sum()}/{len(clean_df)} correct ({pct:.1f}%)')

    # Show specific errors per model
    print()
    print('=== UNIQUE ERRORS BY MODEL ===')
    for model in models:
        disease_col = f'{model}_disease_state'
        errors = clean_df[clean_df.apply(
            lambda row, dc=disease_col: normalize(row[dc]) != normalize(row['TRUTH_disease_state']) and pd.notna(row[dc]),
            axis=1
        )]
        print(f'\n{model} errors ({len(errors)}):')
        for idx, row in errors.iterrows():
            print(f'  {model} said: "{row[disease_col]}" | Truth: "{row["TRUTH_disease_state"]}"')


if __name__ == "__main__":
    main()
