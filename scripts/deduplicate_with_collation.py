"""
Deduplicate questions by QUESTIONGROUPDESIGNATION while collating activity metadata.

Takes the FullColumnsSample file and:
1. Groups by QUESTIONGROUPDESIGNATION (unique question identifier)
2. Keeps one row per unique question
3. Collates all unique COURSENAME values (semicolon-separated)
4. Collates all unique STARTDATE values (semicolon-separated)

Output: A deduplicated file ready for tagging with activity context preserved.

Usage:
    python scripts/deduplicate_with_collation.py --input data/raw/FullColumnsSample_v2_012026.xlsx
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def deduplicate_with_collation(input_file: str, output_file: str = None) -> str:
    """
    Deduplicate questions while collating activity metadata.

    Args:
        input_file: Path to input Excel file
        output_file: Path to output file (auto-generated if not provided)

    Returns:
        Path to output file
    """
    logger.info(f"Loading data from {input_file}...")
    df = pd.read_excel(input_file)
    logger.info(f"Loaded {len(df):,} rows with {len(df.columns)} columns")

    # Verify required columns exist
    required_cols = ['QUESTIONGROUPDESIGNATION', 'COURSENAME', 'STARTDATE']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    # Get unique count before deduplication
    unique_questions = df['QUESTIONGROUPDESIGNATION'].nunique()
    logger.info(f"Found {unique_questions:,} unique questions (by QUESTIONGROUPDESIGNATION)")

    # Define aggregation functions for each column
    # For most columns, keep the first value
    # For COURSENAME and STARTDATE, collate unique values

    def collate_unique(series):
        """Collate unique non-null values with semicolon separator."""
        unique_vals = series.dropna().unique()
        # Convert to string and join
        str_vals = [str(v).strip() for v in unique_vals if str(v).strip()]
        return '; '.join(sorted(set(str_vals)))

    def collate_dates(series):
        """Collate unique dates, formatted as YYYY-MM-DD."""
        unique_vals = series.dropna().unique()
        formatted_dates = []
        for v in unique_vals:
            if pd.notna(v):
                try:
                    # Try to parse and format consistently
                    if isinstance(v, str):
                        formatted_dates.append(v[:10])  # Take first 10 chars (YYYY-MM-DD)
                    else:
                        formatted_dates.append(pd.to_datetime(v).strftime('%Y-%m-%d'))
                except:
                    formatted_dates.append(str(v)[:10])
        return '; '.join(sorted(set(formatted_dates)))

    # Build aggregation dictionary
    agg_dict = {}

    # Columns to collate (unique values with semicolon separator)
    collate_cols = ['COURSENAME']
    date_cols = ['STARTDATE']

    # Columns to keep first value (most question content columns)
    first_cols = [col for col in df.columns
                  if col not in ['QUESTIONGROUPDESIGNATION'] + collate_cols + date_cols]

    for col in first_cols:
        agg_dict[col] = 'first'

    for col in collate_cols:
        if col in df.columns:
            agg_dict[col] = collate_unique

    for col in date_cols:
        if col in df.columns:
            agg_dict[col] = collate_dates

    logger.info("Grouping by QUESTIONGROUPDESIGNATION and collating metadata...")

    # Group by QUESTIONGROUPDESIGNATION and aggregate
    df_dedup = df.groupby('QUESTIONGROUPDESIGNATION', as_index=False).agg(agg_dict)

    # Rename collated columns for clarity
    df_dedup = df_dedup.rename(columns={
        'COURSENAME': 'ACTIVITY_NAMES',
        'STARTDATE': 'START_DATES'
    })

    # Add count of activities per question
    activity_counts = df.groupby('QUESTIONGROUPDESIGNATION').size().reset_index(name='ACTIVITY_COUNT')
    df_dedup = df_dedup.merge(activity_counts, on='QUESTIONGROUPDESIGNATION', how='left')

    # Reorder columns to put key columns first
    key_cols = ['QUESTIONGROUPDESIGNATION', 'ACTIVITY_COUNT', 'ACTIVITY_NAMES', 'START_DATES']
    other_cols = [col for col in df_dedup.columns if col not in key_cols]
    df_dedup = df_dedup[key_cols + other_cols]

    logger.info(f"Deduplicated: {len(df):,} → {len(df_dedup):,} rows")

    # Generate output filename if not provided
    if output_file is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = Path(input_file).parent
        output_file = output_dir / f"questions_deduplicated_collated_{timestamp}.xlsx"

    # Save to Excel
    logger.info(f"Saving to {output_file}...")
    df_dedup.to_excel(output_file, index=False)

    # Print summary statistics
    print("\n" + "=" * 60)
    print("DEDUPLICATION SUMMARY")
    print("=" * 60)
    print(f"Input rows: {len(df):,}")
    print(f"Output rows: {len(df_dedup):,}")
    print(f"Reduction: {(1 - len(df_dedup)/len(df))*100:.1f}%")
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
    parser = argparse.ArgumentParser(
        description='Deduplicate questions while collating activity metadata'
    )
    parser.add_argument(
        '--input', '-i',
        type=str,
        default='data/raw/FullColumnsSample_v2_012026.xlsx',
        help='Input Excel file path'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default=None,
        help='Output Excel file path (auto-generated if not provided)'
    )

    args = parser.parse_args()

    # Check input file exists
    if not Path(args.input).exists():
        print(f"ERROR: Input file not found: {args.input}")
        sys.exit(1)

    # Run deduplication
    output_file = deduplicate_with_collation(
        input_file=args.input,
        output_file=args.output
    )

    print(f"\nDone! Deduplicated file saved to: {output_file}")


if __name__ == "__main__":
    main()
