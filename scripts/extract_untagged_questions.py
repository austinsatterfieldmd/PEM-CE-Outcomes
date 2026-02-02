"""
Extract untagged unique questions for Stage 1 classification.

This script:
1. Loads the tagged FullColumnsSample file
2. Identifies QUESTIONGROUPDESIGNATIONs that have NOT been tagged (ONCCLASS is null)
3. Deduplicates to one row per unique question
4. Collates activity metadata (COURSENAME, STARTDATE)
5. Outputs a file ready for Stage 1 tagging

Usage:
    python scripts/extract_untagged_questions.py
    python scripts/extract_untagged_questions.py --input data/raw/FullColumnsSample_v2_tagged_20260121_223915.xlsx
"""

import argparse
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def collate_unique(series):
    """Collate unique non-null values with semicolon separator."""
    unique_vals = series.dropna().unique()
    str_vals = [str(v).strip() for v in unique_vals if str(v).strip()]
    return '; '.join(sorted(set(str_vals)))


def collate_dates(series):
    """Collate unique dates, formatted as YYYY-MM-DD."""
    unique_vals = series.dropna().unique()
    formatted_dates = []
    for v in unique_vals:
        if pd.notna(v):
            try:
                if isinstance(v, str):
                    formatted_dates.append(v[:10])
                else:
                    formatted_dates.append(pd.to_datetime(v).strftime('%Y-%m-%d'))
            except:
                formatted_dates.append(str(v)[:10])
    return '; '.join(sorted(set(formatted_dates)))


def extract_untagged_questions(input_file: str, output_file: str = None) -> str:
    """
    Extract untagged unique questions from the tagged file.

    Args:
        input_file: Path to tagged FullColumnsSample file
        output_file: Path to output file (auto-generated if not provided)

    Returns:
        Path to output file
    """
    logger.info(f"Loading data from {input_file}...")
    df = pd.read_excel(input_file)
    logger.info(f"Loaded {len(df):,} rows")

    # Verify required columns
    required_cols = ['QUESTIONGROUPDESIGNATION', 'ONCCLASS']
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    # Get stats
    total_qgds = df['QUESTIONGROUPDESIGNATION'].nunique()
    tagged_rows = df['ONCCLASS'].notna()
    tagged_qgds = df[tagged_rows]['QUESTIONGROUPDESIGNATION'].nunique()

    logger.info(f"Total unique QGDs: {total_qgds:,}")
    logger.info(f"Already tagged QGDs: {tagged_qgds:,}")

    # Filter to only untagged rows (ONCCLASS is null)
    untagged_df = df[df['ONCCLASS'].isna()].copy()
    untagged_qgds = untagged_df['QUESTIONGROUPDESIGNATION'].nunique()
    logger.info(f"Untagged QGDs: {untagged_qgds:,}")

    # Build aggregation dictionary
    agg_dict = {}

    # Columns to collate
    collate_cols = ['COURSENAME']
    date_cols = ['STARTDATE']

    # Columns to keep first value
    first_cols = [col for col in untagged_df.columns
                  if col not in ['QUESTIONGROUPDESIGNATION'] + collate_cols + date_cols]

    for col in first_cols:
        agg_dict[col] = 'first'

    for col in collate_cols:
        if col in untagged_df.columns:
            agg_dict[col] = collate_unique

    for col in date_cols:
        if col in untagged_df.columns:
            agg_dict[col] = collate_dates

    logger.info("Deduplicating by QUESTIONGROUPDESIGNATION...")

    # Group by QUESTIONGROUPDESIGNATION and aggregate
    df_dedup = untagged_df.groupby('QUESTIONGROUPDESIGNATION', as_index=False).agg(agg_dict)

    # Rename collated columns for clarity
    df_dedup = df_dedup.rename(columns={
        'COURSENAME': 'ACTIVITY_NAMES',
        'STARTDATE': 'START_DATES'
    })

    # Add count of activities per question
    activity_counts = untagged_df.groupby('QUESTIONGROUPDESIGNATION').size().reset_index(name='ACTIVITY_COUNT')
    df_dedup = df_dedup.merge(activity_counts, on='QUESTIONGROUPDESIGNATION', how='left')

    # Reorder columns: key identifiers first, then question content, then answers
    key_cols = ['QUESTIONGROUPDESIGNATION', 'ACTIVITY_COUNT', 'ACTIVITY_NAMES', 'START_DATES']
    question_cols = ['OPTIMIZEDQUESTION', 'RAWQUESTION', 'OPTIMIZEDCORRECTANSWER']

    # Incorrect answer columns
    ianswer_cols = [col for col in df_dedup.columns if col.startswith('IANSWER')]

    # Tag columns (currently empty, will be filled by tagger)
    tag_cols = ['ONCCLASS', 'DISEASE_STATE1', 'DISEASE_STATE2', 'TOPIC', 'TREATMENT_1', 'TREATMENT_2', 'TREATMENT_3']
    tag_cols = [col for col in tag_cols if col in df_dedup.columns]

    # Other columns
    other_cols = [col for col in df_dedup.columns
                  if col not in key_cols + question_cols + ianswer_cols + tag_cols]

    # Reorder
    final_order = key_cols + question_cols + ianswer_cols + tag_cols + other_cols
    final_order = [col for col in final_order if col in df_dedup.columns]
    df_dedup = df_dedup[final_order]

    logger.info(f"Deduplicated: {len(untagged_df):,} rows → {len(df_dedup):,} unique questions")

    # Generate output filename if not provided
    if output_file is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = Path(input_file).parent
        output_file = output_dir / f"untagged_questions_{timestamp}.xlsx"

    # Save
    logger.info(f"Saving to {output_file}...")
    df_dedup.to_excel(output_file, index=False)

    # Print summary
    print("\n" + "=" * 60)
    print("EXTRACTION SUMMARY")
    print("=" * 60)
    print(f"Source file: {input_file}")
    print(f"Total rows in source: {len(df):,}")
    print(f"Total unique QGDs: {total_qgds:,}")
    print(f"Already tagged: {tagged_qgds:,}")
    print(f"Untagged unique questions: {len(df_dedup):,}")
    print(f"\nActivity count distribution:")
    activity_dist = df_dedup['ACTIVITY_COUNT'].describe()
    print(f"  Min: {activity_dist['min']:.0f}")
    print(f"  Max: {activity_dist['max']:.0f}")
    print(f"  Mean: {activity_dist['mean']:.1f}")
    print(f"  Median: {activity_dist['50%']:.0f}")
    print(f"\nOutput file: {output_file}")
    print("=" * 60)

    return str(output_file)


def main():
    parser = argparse.ArgumentParser(description='Extract untagged unique questions for Stage 1')
    parser.add_argument(
        '--input', '-i',
        type=str,
        default='data/raw/FullColumnsSample_v2_tagged_20260121_223915.xlsx',
        help='Input tagged file path'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default=None,
        help='Output file path (auto-generated if not provided)'
    )

    args = parser.parse_args()

    # Check input file exists
    if not Path(args.input).exists():
        print(f"ERROR: Input file not found: {args.input}")
        return

    # Extract untagged questions
    output_file = extract_untagged_questions(
        input_file=args.input,
        output_file=args.output
    )

    print(f"\nDone! Untagged questions saved to: {output_file}")
    print(f"\nNext step: Run Stage 1 tagging on this file:")
    print(f"  python scripts/run_stage1_eval.py --input \"{output_file}\" --n 100")


if __name__ == "__main__":
    main()
