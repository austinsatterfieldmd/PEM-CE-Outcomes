"""
Stage 1 Disease Classification Script

Runs the disease classifier (Stage 1 of two-stage tagging) on CE questions
to determine disease_state distribution.

This helps inform the architecture decision:
- Which diseases need disease-specific prompts?
- What percentage falls into "other solid tumor" or "other heme"?

Output:
1. Disease frequency statistics (console + CSV)
2. Full results Excel file with classification for each question
"""

import os
import sys
import asyncio
from pathlib import Path
from datetime import datetime
from collections import Counter
import argparse

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
from dotenv import load_dotenv
from tqdm import tqdm

from src.core.taggers.disease_classifier import DiseaseClassifier
from src.core.taggers.openrouter_client import OpenRouterClient

load_dotenv()


def aggregate_questions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate questions by QUESTIONGROUPDESIGNATION.

    Each unique question may appear multiple times (once per scoring group per activity).
    We aggregate to get:
    - One row per unique question
    - All activities that question appeared in
    - All start dates for those activities

    Returns:
        DataFrame with unique questions and aggregated activities/dates
    """
    # Column mappings
    group_col = 'QUESTIONGROUPDESIGNATION'
    question_col = 'OPTIMIZEDQUESTION'
    answer_col = 'OPTIMIZEDCORRECTANSWER'
    activity_col = 'COURSENAME'
    date_col = 'STARTDATE'

    # Incorrect answer columns
    incorrect_cols = [f'IANSWER{i}' for i in range(1, 10) if f'IANSWER{i}' in df.columns]

    if group_col not in df.columns:
        raise ValueError(f"Column '{group_col}' not found. Available: {list(df.columns)}")

    print(f"   Aggregating {len(df)} rows by {group_col}...")

    # Group by question and aggregate
    def aggregate_group(group):
        """Aggregate a group of rows for the same question."""
        first_row = group.iloc[0]

        # Get unique activities and their dates
        activities = group[[activity_col, date_col]].drop_duplicates()
        activity_list = activities[activity_col].dropna().unique().tolist()

        # Get dates, formatted
        date_list = []
        for date_val in activities[date_col].dropna().unique():
            try:
                if isinstance(date_val, str):
                    date_list.append(date_val[:10])
                elif hasattr(date_val, 'strftime'):
                    date_list.append(date_val.strftime('%Y-%m-%d'))
            except:
                pass

        # Collect incorrect answers (take first non-null for each position)
        incorrect_answers = []
        for col in incorrect_cols:
            vals = group[col].dropna().unique()
            if len(vals) > 0:
                incorrect_answers.append(str(vals[0]))

        return pd.Series({
            group_col: first_row[group_col],
            question_col: first_row[question_col],
            answer_col: first_row[answer_col],
            'activities': activity_list,
            'start_dates': date_list,
            'incorrect_answers': incorrect_answers,
            'row_count': len(group)
        })

    # Perform aggregation
    aggregated = df.groupby(group_col, as_index=False).apply(aggregate_group, include_groups=False)

    print(f"   Aggregated to {len(aggregated)} unique questions")
    print(f"   Average rows per question: {len(df) / len(aggregated):.1f}")

    # Show activity distribution
    activity_counts = aggregated['activities'].apply(len)
    print(f"   Questions with 1 activity: {(activity_counts == 1).sum()}")
    print(f"   Questions with 2+ activities: {(activity_counts >= 2).sum()}")
    print(f"   Questions with 5+ activities: {(activity_counts >= 5).sum()}")

    return aggregated


async def classify_questions(
    df: pd.DataFrame,
    client: OpenRouterClient,
    use_voting: bool = True,
    sample_size: int = None,
    batch_size: int = 5
) -> pd.DataFrame:
    """
    Run Stage 1 classification on aggregated questions using 3-model voting.

    Args:
        df: Aggregated DataFrame with unique questions (from aggregate_questions)
        client: OpenRouter client
        use_voting: If True, use 3-model voting (GPT-5.2, Claude, Gemini). If False, single model.
        sample_size: If set, only classify this many questions (for testing)
        batch_size: Number of concurrent requests (lower for 3-model voting due to 3x API calls)

    Returns:
        DataFrame with classification results added
    """
    classifier = DiseaseClassifier(client=client, use_voting=use_voting)

    # Sample if requested
    if sample_size and sample_size < len(df):
        df = df.sample(n=sample_size, random_state=42).reset_index(drop=True)
        print(f"   Sampled {sample_size} questions for classification")

    # Prepare results columns
    df['is_oncology'] = None
    df['disease_state'] = None
    df['agreement'] = None  # unanimous, majority, conflict
    df['gpt_disease'] = None
    df['claude_disease'] = None
    df['gemini_disease'] = None
    df['classification_error'] = None

    # Column mappings for aggregated data
    question_col = 'OPTIMIZEDQUESTION'
    answer_col = 'OPTIMIZEDCORRECTANSWER'

    # Process in batches
    total = len(df)
    errors = 0

    print(f"\n   Classifying {total} unique questions...")

    for i in tqdm(range(0, total, batch_size), desc="   Classifying"):
        batch_end = min(i + batch_size, total)
        batch_indices = range(i, batch_end)

        # Create tasks for batch
        tasks = []
        for idx in batch_indices:
            row = df.iloc[idx]

            question_text = str(row[question_col]) if pd.notna(row[question_col]) else ""
            correct_answer = str(row[answer_col]) if pd.notna(row[answer_col]) else None

            # Get aggregated activities and dates
            activities = row.get('activities', [])
            start_dates = row.get('start_dates', [])
            incorrect_answers = row.get('incorrect_answers', [])

            tasks.append(
                classifier.classify(
                    question_text=question_text,
                    correct_answer=correct_answer,
                    activity_names=activities,
                    start_dates=start_dates,
                    incorrect_answers=incorrect_answers
                )
            )

        # Run batch
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for j, result in enumerate(results):
                idx = i + j
                if isinstance(result, Exception):
                    df.at[idx, 'classification_error'] = str(result)
                    errors += 1
                else:
                    df.at[idx, 'is_oncology'] = result.get('is_oncology')
                    df.at[idx, 'disease_state'] = result.get('disease_state')

                    # Extract voting details if present
                    voting_details = result.get('voting_details', {})
                    if voting_details:
                        df.at[idx, 'agreement'] = voting_details.get('agreement')
                        # Individual model responses
                        gpt_result = voting_details.get('gpt', {})
                        claude_result = voting_details.get('claude', {})
                        gemini_result = voting_details.get('gemini', {})
                        df.at[idx, 'gpt_disease'] = gpt_result.get('disease_state')
                        df.at[idx, 'claude_disease'] = claude_result.get('disease_state')
                        df.at[idx, 'gemini_disease'] = gemini_result.get('disease_state')

        except Exception as e:
            print(f"\n   Batch error at {i}: {e}")
            errors += batch_size

    print(f"\n   Classification complete. Errors: {errors}/{total}")

    return df


def print_frequency_report(df: pd.DataFrame):
    """Print disease frequency statistics."""
    print("\n" + "=" * 70)
    print("DISEASE FREQUENCY REPORT")
    print("=" * 70)

    # Oncology vs Non-oncology
    oncology_counts = df['is_oncology'].value_counts()
    total = len(df)

    print(f"\n1. ONCOLOGY VS NON-ONCOLOGY")
    print("-" * 40)

    onc_count = oncology_counts.get(True, 0)
    non_onc_count = oncology_counts.get(False, 0)
    unknown_count = df['is_oncology'].isna().sum()

    print(f"   Oncology:     {onc_count:>6} ({onc_count/total*100:>5.1f}%)")
    print(f"   Non-Oncology: {non_onc_count:>6} ({non_onc_count/total*100:>5.1f}%)")
    if unknown_count > 0:
        print(f"   Unknown:      {unknown_count:>6} ({unknown_count/total*100:>5.1f}%)")

    # Disease state distribution (oncology only)
    oncology_df = df[df['is_oncology'] == True]

    if len(oncology_df) > 0:
        print(f"\n2. DISEASE STATE DISTRIBUTION (Oncology: {len(oncology_df)} questions)")
        print("-" * 70)

        disease_counts = oncology_df['disease_state'].value_counts()

        # Categorize diseases
        solid_tumors_specific = [
            'Breast cancer', 'NSCLC', 'SCLC', 'CRC', 'Prostate cancer'
        ]
        heme_specific = ['Multiple Myeloma']

        # Group results
        results = []
        for disease, count in disease_counts.items():
            pct = count / len(oncology_df) * 100

            # Determine category
            if disease in solid_tumors_specific:
                category = "Solid (Specific)"
            elif disease in heme_specific:
                category = "Heme (Specific)"
            elif disease in ['Pan-tumor', 'GI Cancers', 'Gyn Cancers', 'Heme Malignancies']:
                category = "Umbrella"
            elif disease in ['DLBCL', 'FL', 'MCL', 'NHL', 'Hodgkin lymphoma', 'CLL', 'AML', 'ALL', 'CML', 'MDS', 'GVHD', 'CMV']:
                category = "Heme (Other)"
            elif pd.isna(disease):
                category = "Unknown"
            else:
                category = "Solid (Other)"

            results.append({
                'disease': disease if pd.notna(disease) else '(Not determined)',
                'count': count,
                'pct': pct,
                'category': category
            })

        # Sort by count
        results.sort(key=lambda x: x['count'], reverse=True)

        # Print table
        print(f"\n   {'Disease State':<35} {'Count':>8} {'Pct':>8}   Category")
        print(f"   {'-'*35} {'-'*8} {'-'*8}   {'-'*15}")

        for r in results:
            print(f"   {r['disease']:<35} {r['count']:>8} {r['pct']:>7.1f}%   {r['category']}")

        # Summary by category
        print(f"\n3. SUMMARY BY CATEGORY")
        print("-" * 40)

        category_counts = Counter()
        for r in results:
            category_counts[r['category']] += r['count']

        for category in ['Solid (Specific)', 'Solid (Other)', 'Heme (Specific)', 'Heme (Other)', 'Umbrella', 'Unknown']:
            if category in category_counts:
                count = category_counts[category]
                pct = count / len(oncology_df) * 100
                print(f"   {category:<20} {count:>8} ({pct:>5.1f}%)")

        # Coverage analysis
        print(f"\n4. COVERAGE ANALYSIS")
        print("-" * 40)

        specific_diseases = solid_tumors_specific + heme_specific
        specific_count = sum(
            disease_counts.get(d, 0) for d in specific_diseases
        )
        specific_pct = specific_count / len(oncology_df) * 100

        print(f"   Disease-specific prompts cover: {specific_count:>6} ({specific_pct:>5.1f}%)")
        print(f"   Remaining (need fallback):      {len(oncology_df) - specific_count:>6} ({100-specific_pct:>5.1f}%)")

        # Top diseases not covered
        print(f"\n   Top diseases NOT covered by specific prompts:")
        uncovered = [r for r in results if r['disease'] not in specific_diseases]
        for r in uncovered[:10]:
            print(f"     - {r['disease']}: {r['count']} ({r['pct']:.1f}%)")

    # Voting agreement statistics (if voting was used)
    if 'agreement' in df.columns and df['agreement'].notna().any():
        print(f"\n5. VOTING AGREEMENT STATISTICS")
        print("-" * 40)

        agreement_counts = df['agreement'].value_counts()
        for agreement, count in agreement_counts.items():
            if agreement:
                pct = count / len(df) * 100
                print(f"   {agreement:<20} {count:>8} ({pct:>5.1f}%)")

        # Show conflicts if any
        conflicts = df[df['agreement'] == 'conflict']
        if len(conflicts) > 0:
            print(f"\n   Sample conflicts (showing model disagreements):")
            for _, row in conflicts.head(5).iterrows():
                q_preview = str(row.get('QUESTION', row.get('question', '')))[:60] + "..."
                print(f"     Q: {q_preview}")
                print(f"        GPT: {row.get('gpt_disease', 'N/A')}, Claude: {row.get('claude_disease', 'N/A')}, Gemini: {row.get('gemini_disease', 'N/A')}")
                print(f"        Final: {row.get('disease_state', 'N/A')}")

    return df


async def main():
    parser = argparse.ArgumentParser(description='Run Stage 1 disease classification on CE questions')
    parser.add_argument('--input', '-i', type=str, help='Input Excel file path')
    parser.add_argument('--output', '-o', type=str, help='Output Excel file path')
    parser.add_argument('--sample', '-s', type=int, default=None, help='Sample size (for testing, applies to unique questions)')
    parser.add_argument('--no-voting', action='store_true', help='Use single model instead of 3-model voting')
    parser.add_argument('--batch', '-b', type=int, default=5, help='Batch size for concurrent requests (default 5 for 3-model voting)')
    parser.add_argument('--columns', '-c', type=str, nargs='+',
                        default=['QUESTIONGROUPDESIGNATION', 'OPTIMIZEDQUESTION', 'OPTIMIZEDCORRECTANSWER',
                                 'COURSENAME', 'STARTDATE', 'IANSWER1', 'IANSWER2', 'IANSWER3',
                                 'IANSWER4', 'IANSWER5', 'IANSWER6', 'IANSWER7', 'IANSWER8', 'IANSWER9'],
                        help='Columns to load from Excel (to reduce memory)')

    args = parser.parse_args()

    # Default paths
    if not args.input:
        # Look for FullColumnsSample file first, then deduplicated
        raw_dir = project_root / "data" / "raw"
        full_cols_files = list(raw_dir.glob("FullColumnsSample*.xlsx"))
        if full_cols_files:
            args.input = str(max(full_cols_files, key=lambda p: p.stat().st_mtime))
            print(f"Using most recent FullColumnsSample file: {args.input}")
        else:
            dedup_files = list(raw_dir.glob("questions_deduplicated_*.xlsx"))
            if dedup_files:
                args.input = str(max(dedup_files, key=lambda p: p.stat().st_mtime))
                print(f"Using most recent deduplicated file: {args.input}")
            else:
                args.input = str(raw_dir / "FulLQuestionsAnswers_NoPrevDesignations_011626_V2.xlsx")

    if not args.output:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        args.output = str(project_root / "data" / "raw" / f"questions_stage1_classified_{timestamp}.xlsx")

    use_voting = not args.no_voting

    print("=" * 70)
    print("STAGE 1 DISEASE CLASSIFICATION")
    print("=" * 70)
    print(f"   Input:  {args.input}")
    print(f"   Output: {args.output}")
    print(f"   Mode:   {'3-Model Voting (GPT-5.2, Claude, Gemini)' if use_voting else 'Single Model (Claude)'}")
    print(f"   Sample: {args.sample or 'All unique questions'}")
    print(f"   Batch:  {args.batch}")

    # Check API key
    if not os.getenv("OPENROUTER_API_KEY"):
        print("\nERROR: OPENROUTER_API_KEY not found in environment")
        sys.exit(1)

    # Load data - only required columns to reduce memory
    print(f"\n1. Loading data from {args.input}...")
    print(f"   Loading only columns: {args.columns}")

    try:
        df = pd.read_excel(args.input, usecols=args.columns)
    except ValueError as e:
        # Some columns may not exist, load all and filter
        print(f"   Warning: Some columns not found, loading all columns...")
        df = pd.read_excel(args.input)
        # Filter to only columns that exist
        existing_cols = [c for c in args.columns if c in df.columns]
        df = df[existing_cols]

    print(f"   Loaded {len(df)} rows with {len(df.columns)} columns")

    # Aggregate by QUESTIONGROUPDESIGNATION
    print(f"\n2. Aggregating to unique questions...")
    aggregated_df = aggregate_questions(df)

    # Free memory from original df
    del df

    # Initialize client
    print(f"\n3. Initializing OpenRouter client...")
    client = OpenRouterClient()

    # Run classification on aggregated questions
    print(f"\n4. Running Stage 1 classification...")
    classified_df = await classify_questions(
        df=aggregated_df,
        client=client,
        use_voting=use_voting,
        sample_size=args.sample,
        batch_size=args.batch
    )

    # Print frequency report
    print_frequency_report(classified_df)

    # Save aggregated results (unique questions with classifications)
    print(f"\n6. Saving results...")

    # Save unique questions file
    unique_output = args.output.replace('.xlsx', '_unique.xlsx')
    classified_df.to_excel(unique_output, index=False)
    print(f"   Saved {len(classified_df)} unique questions to {unique_output}")

    # Also save CSV frequency summary
    csv_path = args.output.replace('.xlsx', '_frequency.csv')
    freq_df = classified_df.groupby(['is_oncology', 'disease_state']).size().reset_index(name='count')
    freq_df = freq_df.sort_values(['is_oncology', 'count'], ascending=[False, False])
    freq_df.to_csv(csv_path, index=False)
    print(f"   Saved frequency summary to {csv_path}")

    # Print cost summary
    print(f"\n7. COST SUMMARY")
    print("-" * 40)
    usage = client.get_usage_summary()
    print(f"   Total API calls: {usage['total_calls']}")
    print(f"   Total cost:      ${usage['total_cost']:.4f}")

    if usage['by_model']:
        print(f"\n   By model:")
        for model, stats in usage['by_model'].items():
            print(f"     {model}: {stats['calls']} calls, ${stats['cost']:.4f}")

    # Cleanup
    await client.close()

    print(f"\n" + "=" * 70)
    print("DONE!")
    print("=" * 70)
    print(f"\nNext step: Merge classifications back to full dataset using QUESTIONGROUPDESIGNATION")


if __name__ == "__main__":
    asyncio.run(main())
