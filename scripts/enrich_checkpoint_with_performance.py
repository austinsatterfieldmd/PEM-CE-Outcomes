#!/usr/bin/env python3
"""
Enrich checkpoint files with QCore scores and performance data.

This script adds:
1. QCore quality scores (calculated from quality tags)
2. Pre/post performance data by audience segment (from raw data files)

Usage:
    # Enrich a single checkpoint file
    python scripts/enrich_checkpoint_with_performance.py --checkpoint data/checkpoints/stage2_tagged_AML_20260211.json

    # Enrich all checkpoint files
    python scripts/enrich_checkpoint_with_performance.py --all

    # Specify raw performance data file
    python scripts/enrich_checkpoint_with_performance.py --checkpoint data/checkpoints/stage2_tagged_AML_20260211.json --raw-data data/raw/MyelomaDataTable_020526_proofing.xlsx
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import pandas as pd

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.preprocessing.qcore_scorer import calculate_qcore_score

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def calculate_qcore_for_tags(tags: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate QCore score from quality tags.

    Args:
        tags: Tag dictionary containing quality fields

    Returns:
        Dictionary with qcore_score, qcore_grade, qcore_breakdown
    """
    try:
        # Parse CME level (may be string like "4 - Competence")
        cme_level_raw = tags.get('cme_outcome_level', 4)
        if isinstance(cme_level_raw, str):
            # Extract number from "4 - Competence" format
            cme_level = int(cme_level_raw.split(' ')[0]) if ' ' in cme_level_raw else int(cme_level_raw)
        else:
            cme_level = int(cme_level_raw)

        result = calculate_qcore_score(tags, cme_level=cme_level)

        return {
            'qcore_score': result['total_score'],
            'qcore_grade': result['grade'],
            'qcore_breakdown': result['breakdown'],
            'qcore_ready_for_deployment': result['ready_for_deployment']
        }
    except Exception as e:
        logger.warning(f"Failed to calculate QCore: {e}")
        return {
            'qcore_score': None,
            'qcore_grade': None,
            'qcore_breakdown': {},
            'qcore_ready_for_deployment': False
        }


def load_performance_data(raw_data_file: Path) -> pd.DataFrame:
    """Load raw performance data from Excel file.

    Args:
        raw_data_file: Path to raw Excel file with performance data

    Returns:
        DataFrame with performance data
    """
    logger.info(f"Loading performance data from {raw_data_file}")

    # Required columns
    required_cols = [
        'QUESTIONGROUPDESIGNATION', 'SCORINGGROUP',
        'PRESCORECALC', 'PRESCOREN', 'POSTSCORECALC', 'POSTSCOREN'
    ]

    df = pd.read_excel(raw_data_file, usecols=lambda x: x in required_cols)
    logger.info(f"Loaded {len(df)} performance records")

    # Show unique scoring groups
    groups = df['SCORINGGROUP'].unique()
    logger.info(f"Audience segments: {', '.join(groups)}")

    return df


def match_performance_data(
    qgd: str,
    perf_data: pd.DataFrame
) -> Optional[Dict[str, Any]]:
    """Match performance data for a question by QGD.

    Args:
        qgd: Question Group Designation (source_id)
        perf_data: DataFrame with performance data

    Returns:
        Dictionary with performance data by audience segment, or None if no match
    """
    # Convert QGD to string for matching
    qgd_str = str(qgd)

    # Find all rows for this QGD
    matches = perf_data[perf_data['QUESTIONGROUPDESIGNATION'].astype(str) == qgd_str]

    if matches.empty:
        return None

    # Build performance data by audience segment
    performance_by_audience = {}

    for _, row in matches.iterrows():
        audience = row['SCORINGGROUP']

        # Calculate percentages
        pre_correct = row['PRESCORECALC']
        pre_total = row['PRESCOREN']
        post_correct = row['POSTSCORECALC']
        post_total = row['POSTSCOREN']

        pre_pct = (pre_correct / pre_total * 100) if pre_total > 0 else None
        post_pct = (post_correct / post_total * 100) if post_total > 0 else None
        change = (post_pct - pre_pct) if (pre_pct is not None and post_pct is not None) else None

        performance_by_audience[audience] = {
            'pre_score_correct': int(pre_correct) if pd.notna(pre_correct) else 0,
            'pre_score_total': int(pre_total) if pd.notna(pre_total) else 0,
            'pre_score_pct': round(pre_pct, 1) if pre_pct is not None else None,
            'post_score_correct': int(post_correct) if pd.notna(post_correct) else 0,
            'post_score_total': int(post_total) if pd.notna(post_total) else 0,
            'post_score_pct': round(post_pct, 1) if post_pct is not None else None,
            'change_pp': round(change, 1) if change is not None else None
        }

    return performance_by_audience


def enrich_checkpoint(
    checkpoint_file: Path,
    raw_data_file: Optional[Path] = None,
    output_file: Optional[Path] = None,
    dry_run: bool = False
) -> None:
    """Enrich a checkpoint file with QCore and performance data.

    Args:
        checkpoint_file: Path to checkpoint JSON file
        raw_data_file: Optional path to raw performance data Excel file
        output_file: Optional output path (defaults to overwriting input)
        dry_run: If True, show what would be done without saving
    """
    logger.info(f"\nEnriching {checkpoint_file.name}")

    # Load checkpoint
    with open(checkpoint_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Handle both old (list) and new (dict with 'results' key) checkpoint formats
    if isinstance(data, list):
        results = data
        logger.info(f"Found {len(results)} questions in checkpoint (old format)")
    else:
        results = data.get('results', [])
        logger.info(f"Found {len(results)} questions in checkpoint (new format)")

    # Load performance data if provided
    perf_data = None
    if raw_data_file and raw_data_file.exists():
        perf_data = load_performance_data(raw_data_file)
    else:
        logger.warning("No raw performance data provided - skipping performance matching")

    # Enrich each result
    enriched = 0
    qcore_added = 0
    perf_added = 0

    for result in results:
        # Skip if error result (check for truthy error value, not just key existence)
        if result.get('error'):
            continue

        # Calculate QCore from final_tags
        final_tags = result.get('final_tags', {})
        if final_tags:
            qcore_data = calculate_qcore_for_tags(final_tags)
            result.update(qcore_data)
            qcore_added += 1

        # Match performance data
        if perf_data is not None:
            qgd = result.get('source_id') or result.get('question_id')
            if qgd:
                perf_match = match_performance_data(qgd, perf_data)
                if perf_match:
                    result['performance_by_audience'] = perf_match
                    perf_added += 1

        enriched += 1

    logger.info(f"Enriched {enriched} questions:")
    logger.info(f"  QCore scores added: {qcore_added}")
    logger.info(f"  Performance data matched: {perf_added}")

    if dry_run:
        logger.info("DRY RUN - not saving changes")
        return

    # Save enriched checkpoint (preserve original structure)
    output_path = output_file or checkpoint_file
    with open(output_path, 'w', encoding='utf-8') as f:
        if isinstance(data, list):
            # Old format - save list directly
            json.dump(results, f, indent=2, ensure_ascii=False)
        else:
            # New format - save dict with updated results
            data['results'] = results
            json.dump(data, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved enriched checkpoint to {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Enrich checkpoint files with QCore and performance data"
    )
    parser.add_argument(
        '--checkpoint',
        type=Path,
        help='Checkpoint file to enrich'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Enrich all checkpoint files in data/checkpoints/'
    )
    parser.add_argument(
        '--raw-data',
        type=Path,
        help='Raw performance data Excel file'
    )
    parser.add_argument(
        '--output',
        type=Path,
        help='Output file (defaults to overwriting input)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without saving'
    )

    args = parser.parse_args()

    if not args.checkpoint and not args.all:
        parser.error("Must specify either --checkpoint or --all")

    if args.all:
        # Find all checkpoint files
        checkpoints_dir = PROJECT_ROOT / "data" / "checkpoints"
        checkpoint_files = list(checkpoints_dir.glob("stage2_tagged_*.json"))

        if not checkpoint_files:
            logger.error("No checkpoint files found")
            return

        logger.info(f"Found {len(checkpoint_files)} checkpoint files")

        for cp_file in checkpoint_files:
            enrich_checkpoint(cp_file, args.raw_data, dry_run=args.dry_run)

    else:
        # Single file
        if not args.checkpoint.exists():
            logger.error(f"Checkpoint file not found: {args.checkpoint}")
            return

        enrich_checkpoint(
            args.checkpoint,
            args.raw_data,
            args.output,
            args.dry_run
        )

    logger.info("\n✓ Enrichment complete")


if __name__ == '__main__':
    main()
