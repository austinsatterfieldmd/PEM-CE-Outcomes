"""
Merge verified Stage 1 tags from reviewed evaluation files into FullColumnsSample_v2.

This script:
1. Extracts verified tags from all reviewed evaluation files
2. Applies manual corrections from REVIEW_NOTES
3. Merges tags into FullColumnsSample_v2 via QUESTIONGROUPDESIGNATION
4. Updates columns: ONCCLASS (B), and disease state columns (O, P)

Usage:
    python scripts/merge_verified_tags.py
"""

import argparse
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Manual corrections based on REVIEW_NOTES
# Format: QUESTIONGROUPDESIGNATION -> {corrected_is_oncology, corrected_disease_state, corrected_disease_state_secondary}
MANUAL_CORRECTIONS = {
    # 100-batch corrections
    5966: {"is_oncology": True, "disease_state": "LEMS", "disease_state_secondary": "SCLC"},  # LEMS, SCLC as secondary
    6327: {"is_oncology": False, "disease_state": None, "disease_state_secondary": None},  # IDA = multispecialty
    1587: {"is_oncology": False, "disease_state": None, "disease_state_secondary": None},  # Psychiatry program
    2383: {"is_oncology": True, "disease_state": "NF1-associated plexiform neurofibroma", "disease_state_secondary": None},

    # 200-batch corrections
    4850: {"is_oncology": True, "disease_state": "NSCLC", "disease_state_secondary": None},  # Lung meeting context
    5808: {"is_oncology": False, "disease_state": None, "disease_state_secondary": None},  # Myocarditis = multispecialty
    4513: {"is_oncology": True, "disease_state": "GU Cancers", "disease_state_secondary": None},  # GU malignancies broadly
    6122: {"is_oncology": False, "disease_state": None, "disease_state_secondary": None},  # TA-TMA = multispecialty
    7302: {"is_oncology": True, "disease_state": "Sarcoma", "disease_state_secondary": None},  # GIST -> Sarcoma
    4996: {"is_oncology": False, "disease_state": None, "disease_state_secondary": None},  # Prostate screening = multispecialty
    3664: {"is_oncology": False, "disease_state": None, "disease_state_secondary": None},  # CAS = multispecialty
    5044: {"is_oncology": True, "disease_state": "Breast cancer", "disease_state_secondary": None},  # SOBO = breast
    1116: {"is_oncology": True, "disease_state": "Hepatobiliary cancer", "disease_state_secondary": None},  # CCA -> HBC
    6335: {"is_oncology": False, "disease_state": None, "disease_state_secondary": None},  # IDA = multispecialty
    2525: {"is_oncology": False, "disease_state": None, "disease_state_secondary": None},  # Prostate screening = multispecialty

    # 700-batch corrections
    2718: {"is_oncology": True, "disease_state": "Gyn Cancers", "disease_state_secondary": None},  # Pan-tumor at Gyn meeting
    3681: {"is_oncology": True, "disease_state": "Waldenström", "disease_state_secondary": "MZL"},  # Dual disease
    4932: {"is_oncology": False, "disease_state": None, "disease_state_secondary": None},  # COPE/Eye = multispecialty
    2860: {"is_oncology": True, "disease_state": "Pan-tumor", "disease_state_secondary": None},  # "All of the above" = pan-tumor
    5902: {"is_oncology": True, "disease_state": "MPN", "disease_state_secondary": None},  # MPN umbrella
    6525: {"is_oncology": True, "disease_state": "MPN", "disease_state_secondary": None},  # MPN umbrella
    2817: {"is_oncology": True, "disease_state": "AML", "disease_state_secondary": "MDS"},  # AML with MDS secondary

    # 200-batch-2 corrections (stage1_eval_20260121_233650_reviewed.xlsx)
    2278: {"is_oncology": False, "disease_state": None, "disease_state_secondary": None},  # Sickle cell = non-oncology (activity name red herring)
    6029: {"is_oncology": True, "disease_state": "Multiple Myeloma", "disease_state_secondary": "NHL"},  # Dual disease, not Heme Malignancies umbrella

    # 200-batch-3 corrections (stage1_eval_20260122_012256_reviewed.xlsx)
    2582: {"is_oncology": True, "disease_state": "Gyn Cancers", "disease_state_secondary": None},  # COPE ocular toxicity with mirvetuximab (ovarian) + tisotumab (cervical) = Gyn Cancers, not Pan-tumor
    857: {"is_oncology": True, "disease_state": "NSCLC", "disease_state_secondary": None},  # EGFR NSCLC - GPT was right, disease conflict resulted in null
}


def load_reviewed_files():
    """Load all reviewed evaluation files and extract verified tags."""
    reviewed_files = [
        'data/eval/stage1_eval_20260121_094325_reviewed.xlsx',
        'data/eval/stage1_eval_20260121_121136_reviewed.xlsx',
        'data/eval/stage1_eval_20260121_145544_reviewed.xlsx',
        'data/eval/stage1_eval_20260121_233650_reviewed.xlsx',
        'data/eval/stage1_eval_20260122_012256_reviewed.xlsx',
    ]

    all_tags = []

    for filepath in reviewed_files:
        if not Path(filepath).exists():
            logger.warning(f"File not found: {filepath}")
            continue

        logger.info(f"Loading {filepath}...")
        df = pd.read_excel(filepath)

        # Extract rows where model was correct (blank or True, not False)
        not_wrong_onc = ~(df['CORRECT_is_oncology'] == False)
        not_wrong_dis = ~(df['CORRECT_disease_state'] == False)
        has_result = df['FINAL_is_oncology'].notna()

        correct_rows = df[not_wrong_onc & not_wrong_dis & has_result].copy()

        # Extract only needed columns (handle missing secondary column)
        cols_to_extract = ['QUESTIONGROUPDESIGNATION', 'FINAL_is_oncology', 'FINAL_disease_state']
        if 'FINAL_disease_state_secondary' in correct_rows.columns:
            cols_to_extract.append('FINAL_disease_state_secondary')

        tags = correct_rows[cols_to_extract].copy()
        tags = tags.rename(columns={
            'FINAL_is_oncology': 'is_oncology',
            'FINAL_disease_state': 'disease_state',
        })

        # Add secondary column if it exists, otherwise create empty
        if 'FINAL_disease_state_secondary' in tags.columns:
            tags = tags.rename(columns={'FINAL_disease_state_secondary': 'disease_state_secondary'})
        else:
            tags['disease_state_secondary'] = None

        all_tags.append(tags)
        logger.info(f"  Extracted {len(tags)} verified tags")

    # Combine all
    combined = pd.concat(all_tags, ignore_index=True)

    # Deduplicate by QUESTIONGROUPDESIGNATION (keep first)
    combined = combined.drop_duplicates(subset=['QUESTIONGROUPDESIGNATION'], keep='first')

    logger.info(f"Total unique verified tags: {len(combined)}")

    return combined


def apply_manual_corrections(tags_df):
    """Apply manual corrections from REVIEW_NOTES."""
    corrections_applied = 0

    for qgd, correction in MANUAL_CORRECTIONS.items():
        # Check if this question is in our tags
        mask = tags_df['QUESTIONGROUPDESIGNATION'] == qgd

        if mask.any():
            # Update existing row
            tags_df.loc[mask, 'is_oncology'] = correction['is_oncology']
            tags_df.loc[mask, 'disease_state'] = correction['disease_state']
            tags_df.loc[mask, 'disease_state_secondary'] = correction['disease_state_secondary']
            corrections_applied += 1
        else:
            # Add new row for corrected question
            new_row = {
                'QUESTIONGROUPDESIGNATION': qgd,
                'is_oncology': correction['is_oncology'],
                'disease_state': correction['disease_state'],
                'disease_state_secondary': correction['disease_state_secondary']
            }
            tags_df = pd.concat([tags_df, pd.DataFrame([new_row])], ignore_index=True)
            corrections_applied += 1

    logger.info(f"Applied {corrections_applied} manual corrections")

    return tags_df


def merge_into_source(tags_df, source_file, output_file=None):
    """Merge verified tags into source FullColumnsSample file."""
    logger.info(f"Loading source file: {source_file}")
    source_df = pd.read_excel(source_file)
    logger.info(f"  Loaded {len(source_df)} rows")

    # Check column names for disease state columns
    logger.info(f"  Columns: {list(source_df.columns[:20])}...")

    # Create lookup dict from tags
    tags_lookup = {}
    for _, row in tags_df.iterrows():
        qgd = row['QUESTIONGROUPDESIGNATION']
        tags_lookup[qgd] = {
            'is_oncology': row['is_oncology'],
            'disease_state': row['disease_state'],
            'disease_state_secondary': row['disease_state_secondary']
        }

    # Track updates
    updated_oncclass = 0
    updated_disease1 = 0
    updated_disease2 = 0

    # Identify target columns (based on FullColumnsSample_v2 structure)
    oncclass_col = 'ONCCLASS'  # Column 1
    disease1_col = 'DISEASE_STATE1'  # Column 14
    disease2_col = 'DISEASE_STATE2'  # Column 15

    # Verify columns exist
    for col in [oncclass_col, disease1_col, disease2_col]:
        if col not in source_df.columns:
            logger.error(f"Required column not found: {col}")
            return None

    logger.info(f"  Target columns: {oncclass_col}, {disease1_col}, {disease2_col}")

    # Apply tags row by row
    for idx, row in source_df.iterrows():
        qgd = row.get('QUESTIONGROUPDESIGNATION')
        if pd.isna(qgd) or qgd not in tags_lookup:
            continue

        tags = tags_lookup[qgd]

        # Update ONCCLASS
        if oncclass_col:
            oncclass_value = "Oncology" if tags['is_oncology'] else "Multispecialty"
            if pd.isna(source_df.at[idx, oncclass_col]) or source_df.at[idx, oncclass_col] != oncclass_value:
                source_df.at[idx, oncclass_col] = oncclass_value
                updated_oncclass += 1

        # Update disease_state (only for oncology questions)
        if tags['is_oncology'] and disease1_col and tags['disease_state']:
            if pd.isna(source_df.at[idx, disease1_col]) or source_df.at[idx, disease1_col] != tags['disease_state']:
                source_df.at[idx, disease1_col] = tags['disease_state']
                updated_disease1 += 1

        # Update disease_state_secondary
        if tags['is_oncology'] and disease2_col and tags['disease_state_secondary']:
            if pd.isna(source_df.at[idx, disease2_col]) or source_df.at[idx, disease2_col] != tags['disease_state_secondary']:
                source_df.at[idx, disease2_col] = tags['disease_state_secondary']
                updated_disease2 += 1

    logger.info(f"Updates applied:")
    logger.info(f"  ONCCLASS: {updated_oncclass} rows")
    logger.info(f"  Disease State 1: {updated_disease1} rows")
    logger.info(f"  Disease State 2: {updated_disease2} rows")

    # Generate output filename
    if output_file is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"data/raw/FullColumnsSample_v2_tagged_{timestamp}.xlsx"

    # Save
    logger.info(f"Saving to {output_file}...")
    source_df.to_excel(output_file, index=False)

    return output_file


def main():
    parser = argparse.ArgumentParser(description='Merge verified Stage 1 tags into source file')
    parser.add_argument(
        '--source', '-s',
        type=str,
        default='data/raw/FullColumnsSample_v2_012026.xlsx',
        help='Source file to update'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default=None,
        help='Output file path (auto-generated if not provided)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without saving'
    )

    args = parser.parse_args()

    # Load verified tags
    logger.info("=== Loading verified tags from reviewed files ===")
    tags_df = load_reviewed_files()

    # Apply manual corrections
    logger.info("\n=== Applying manual corrections ===")
    tags_df = apply_manual_corrections(tags_df)

    logger.info(f"\nFinal tag count: {len(tags_df)} unique questions")

    # Show distribution
    oncology_count = (tags_df['is_oncology'] == True).sum()
    multispec_count = (tags_df['is_oncology'] == False).sum()
    logger.info(f"  Oncology: {oncology_count}")
    logger.info(f"  Multispecialty: {multispec_count}")

    if args.dry_run:
        logger.info("\n=== DRY RUN - Not saving ===")
        logger.info(f"Would update source file: {args.source}")
        return

    # Merge into source
    logger.info(f"\n=== Merging into source file ===")
    output_file = merge_into_source(tags_df, args.source, args.output)

    print(f"\nDone! Tagged file saved to: {output_file}")


if __name__ == "__main__":
    main()
