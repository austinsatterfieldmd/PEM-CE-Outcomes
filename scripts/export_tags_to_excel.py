"""
Export finalized tags from checkpoint JSON back into the source Excel file by QGD.

Matches checkpoint entries to Excel rows by QUESTIONGROUPDESIGNATION.
Only writes to rows where human_reviewed=True (unless --include-unreviewed).
Preserves all existing Excel columns and adds new columns for extended schema fields.
Creates a new output file (never overwrites source).

Question stems edited in the dashboard are written back to OPTIMIZEDQUESTION.

Usage:
    # Export reviewed tags only (default)
    python scripts/export_tags_to_excel.py \
        --input data/raw/FullColumnsSample_v2_012026.xlsx \
        --checkpoint data/checkpoints/stage2_tagged_multiple_myeloma.json \
        --output data/raw/FullColumnsSample_v2_tagged.xlsx \
        --disease "Multiple myeloma"

    # Include all tagged questions (reviewed + unreviewed)
    python scripts/export_tags_to_excel.py \
        --input data/raw/FullColumnsSample_v2_012026.xlsx \
        --checkpoint data/checkpoints/stage2_tagged_multiple_myeloma.json \
        --output data/raw/FullColumnsSample_v2_tagged.xlsx \
        --disease "Multiple myeloma" \
        --include-unreviewed
"""

import argparse
import json
import logging
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────
# Column mapping: checkpoint final_tags field → Excel column name
# ──────────────────────────────────────────────────────────────────────

# Existing columns in the Excel file (already present, just need populating)
EXISTING_COLUMN_MAP = {
    'disease_state':    'DISEASE_STATE1',
    'topic':            'TOPIC',
    'treatment_1':      'TREATMENT_1',
    'treatment_2':      'TREATMENT_2',
    'treatment_3':      'TREATMENT_3',
    'treatment_4':      'TREATMENT_4',
    'treatment_5':      'TREATMENT_5',
    'disease_type_1':   'DISEASE_TYPE',
    'disease_stage':    'DISEASE_STAGE',
    'treatment_line':   'TREATMENT_LINE',
    'biomarker_1':      'BIOMARKER_1',
    'biomarker_2':      'BIOMARKER_2',
    'biomarker_3':      'BIOMARKER_3',
    'biomarker_4':      'BIOMARKER_4',
    'biomarker_5':      'BIOMARKER_5',
    'trial_1':          'TRIAL_1',
    'trial_2':          'TRIAL_2',
    'trial_3':          'TRIAL_3',
    'trial_4':          'TRIAL_4',
    'trial_5':          'TRIAL_5',
}

# New columns to add to the Excel file (extended schema)
NEW_COLUMN_MAP = {
    # Group B: Patient Characteristics
    'treatment_eligibility':    'TREATMENT_ELIGIBILITY',
    'age_group':                'AGE_GROUP',
    'organ_dysfunction':        'ORGAN_DYSFUNCTION',
    'fitness_status':           'FITNESS_STATUS',
    'disease_specific_factor':  'DISEASE_SPECIFIC_FACTOR',

    # Group B (continued): Comorbidities
    'comorbidity_1':            'COMORBIDITY_1',
    'comorbidity_2':            'COMORBIDITY_2',
    'comorbidity_3':            'COMORBIDITY_3',

    # Group C: Treatment Metadata
    'drug_class_1':             'DRUG_CLASS_1',
    'drug_class_2':             'DRUG_CLASS_2',
    'drug_class_3':             'DRUG_CLASS_3',
    'drug_target_1':            'DRUG_TARGET_1',
    'drug_target_2':            'DRUG_TARGET_2',
    'drug_target_3':            'DRUG_TARGET_3',
    'prior_therapy_1':          'PRIOR_THERAPY_1',
    'prior_therapy_2':          'PRIOR_THERAPY_2',
    'prior_therapy_3':          'PRIOR_THERAPY_3',
    'resistance_mechanism':     'RESISTANCE_MECHANISM',

    # Group D: Clinical Context
    'metastatic_site_1':        'METASTATIC_SITE_1',
    'metastatic_site_2':        'METASTATIC_SITE_2',
    'metastatic_site_3':        'METASTATIC_SITE_3',
    'symptom_1':                'SYMPTOM_1',
    'symptom_2':                'SYMPTOM_2',
    'symptom_3':                'SYMPTOM_3',
    'performance_status':       'PERFORMANCE_STATUS',

    # Group E: Safety/Toxicity
    'toxicity_type_1':          'TOXICITY_TYPE_1',
    'toxicity_type_2':          'TOXICITY_TYPE_2',
    'toxicity_type_3':          'TOXICITY_TYPE_3',
    'toxicity_type_4':          'TOXICITY_TYPE_4',
    'toxicity_type_5':          'TOXICITY_TYPE_5',
    'toxicity_organ':           'TOXICITY_ORGAN',
    'toxicity_grade':           'TOXICITY_GRADE',

    # Group F: Efficacy/Outcomes
    'efficacy_endpoint_1':      'EFFICACY_ENDPOINT_1',
    'efficacy_endpoint_2':      'EFFICACY_ENDPOINT_2',
    'efficacy_endpoint_3':      'EFFICACY_ENDPOINT_3',
    'outcome_context':          'OUTCOME_CONTEXT',
    'clinical_benefit':         'CLINICAL_BENEFIT',

    # Group G: Evidence/Guidelines
    'guideline_source_1':       'GUIDELINE_SOURCE_1',
    'guideline_source_2':       'GUIDELINE_SOURCE_2',
    'evidence_type':            'EVIDENCE_TYPE',

    # Group H: Question Format/Quality
    'cme_outcome_level':        'CME_OUTCOME_LEVEL',
    'data_response_type':       'DATA_RESPONSE_TYPE',
    'stem_type':                'STEM_TYPE',
    'lead_in_type':             'LEAD_IN_TYPE',
    'answer_format':            'ANSWER_FORMAT',
    'answer_length_pattern':    'ANSWER_LENGTH_PATTERN',
    'distractor_homogeneity':   'DISTRACTOR_HOMOGENEITY',
    'flaw_absolute_terms':      'FLAW_ABSOLUTE_TERMS',
    'flaw_grammatical_cue':     'FLAW_GRAMMATICAL_CUE',
    'flaw_implausible_distractor': 'FLAW_IMPLAUSIBLE_DISTRACTOR',
    'flaw_clang_association':   'FLAW_CLANG_ASSOCIATION',
    'flaw_convergence_vulnerability': 'FLAW_CONVERGENCE_VULNERABILITY',
    'flaw_double_negative':     'FLAW_DOUBLE_NEGATIVE',

    # Computed fields
    'answer_option_count':      'ANSWER_OPTION_COUNT',
    'correct_answer_position':  'CORRECT_ANSWER_POSITION',

    # Metadata columns
    'disease_type_2':           'DISEASE_TYPE_2',
}

# Metadata columns (from checkpoint entry, not final_tags)
METADATA_COLUMN_MAP = {
    'agreement':        'AGREEMENT_LEVEL',
    'confidence':       'OVERALL_CONFIDENCE',
    'review_reason':    'REVIEW_REASON',
    'human_reviewed':   'HUMAN_REVIEWED',
}

# Combine all maps for lookup
ALL_TAG_COLUMNS = {**EXISTING_COLUMN_MAP, **NEW_COLUMN_MAP}


def main():
    parser = argparse.ArgumentParser(
        description="Export finalized tags from checkpoint to Excel by QGD"
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to source Excel file (e.g., data/raw/FullColumnsSample_v2_012026.xlsx)"
    )
    parser.add_argument(
        "--checkpoint",
        required=True,
        help="Path to checkpoint JSON (e.g., data/checkpoints/stage2_tagged_multiple_myeloma.json)"
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to output Excel file (new file — source is never overwritten)"
    )
    parser.add_argument(
        "--disease",
        default=None,
        help="Filter checkpoint to specific disease (optional)"
    )
    parser.add_argument(
        "--include-unreviewed",
        action="store_true",
        help="Include unreviewed AI-tagged entries (default: only human-reviewed)"
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    checkpoint_path = Path(args.checkpoint)
    output_path = Path(args.output)

    # Safety: never overwrite the source file
    if input_path.resolve() == output_path.resolve():
        logger.error("Output path must be different from input path")
        sys.exit(1)

    # ── Load checkpoint ──────────────────────────────────────────────
    logger.info(f"Loading checkpoint: {checkpoint_path}")
    with open(checkpoint_path, "r", encoding="utf-8") as f:
        checkpoint_data = json.load(f)
    logger.info(f"  {len(checkpoint_data)} entries")

    # Filter by disease if specified
    if args.disease:
        checkpoint_data = [
            e for e in checkpoint_data
            if e.get('disease_state', '').lower() == args.disease.lower()
        ]
        logger.info(f"  Filtered to {len(checkpoint_data)} {args.disease} entries")

    # Filter to reviewed only (unless --include-unreviewed)
    if not args.include_unreviewed:
        checkpoint_data = [e for e in checkpoint_data if e.get('human_reviewed', False)]
        logger.info(f"  {len(checkpoint_data)} human-reviewed entries")
    else:
        logger.info(f"  Including all {len(checkpoint_data)} entries (reviewed + unreviewed)")

    if not checkpoint_data:
        logger.warning("No entries to export")
        sys.exit(0)

    # Build lookup: QGD (source_id) → checkpoint entry
    qgd_lookup = {}
    for entry in checkpoint_data:
        source_id = entry.get('source_id')
        if source_id is not None:
            qgd_lookup[str(source_id)] = entry
        else:
            logger.warning(f"Entry missing source_id: question_id={entry.get('question_id')}")
    logger.info(f"  {len(qgd_lookup)} entries with QGD for matching")

    # ── Load Excel ───────────────────────────────────────────────────
    logger.info(f"Loading Excel: {input_path}")
    df = pd.read_excel(input_path)
    logger.info(f"  {len(df)} rows, {len(df.columns)} columns")

    # Ensure QGD column exists and convert to string for matching
    if 'QUESTIONGROUPDESIGNATION' not in df.columns:
        logger.error("Excel file missing QUESTIONGROUPDESIGNATION column")
        sys.exit(1)

    df['_qgd_str'] = df['QUESTIONGROUPDESIGNATION'].astype(str)

    # ── Ensure tag columns have string dtype (avoid float64 FutureWarning) ──
    all_tag_excel_cols = list(EXISTING_COLUMN_MAP.values()) + list(NEW_COLUMN_MAP.values()) + list(METADATA_COLUMN_MAP.values())
    for col in all_tag_excel_cols:
        if col in df.columns:
            df[col] = df[col].astype(object)

    # ── Add new columns if they don't exist ─────────────────────────
    all_new_excel_cols = list(NEW_COLUMN_MAP.values()) + list(METADATA_COLUMN_MAP.values())
    for col in all_new_excel_cols:
        if col not in df.columns:
            df[col] = pd.Series(dtype='object')

    # ── Merge tags into Excel by QGD ─────────────────────────────────
    matched_rows = 0
    matched_qgds = set()
    stem_edits = 0

    for idx, row in df.iterrows():
        qgd = row['_qgd_str']
        if qgd not in qgd_lookup:
            continue

        entry = qgd_lookup[qgd]
        final_tags = entry.get('final_tags', {})
        matched_rows += 1
        matched_qgds.add(qgd)

        # Write tag fields → Excel columns (skip empty strings)
        for tag_field, excel_col in ALL_TAG_COLUMNS.items():
            value = final_tags.get(tag_field)
            if value is not None and value != '':
                df.at[idx, excel_col] = value

        # Write metadata columns
        for ckpt_field, excel_col in METADATA_COLUMN_MAP.items():
            value = entry.get(ckpt_field)
            if value is not None:
                df.at[idx, excel_col] = value

        # Write back edited question stem to OPTIMIZEDQUESTION
        if entry.get('question_stem_edited') and entry.get('question_stem'):
            df.at[idx, 'OPTIMIZEDQUESTION'] = entry['question_stem']
            stem_edits += 1

    # ── Clean up and save ────────────────────────────────────────────
    df.drop(columns=['_qgd_str'], inplace=True)

    logger.info(f"\nMatched {len(matched_qgds)}/{len(qgd_lookup)} unique QGDs ({matched_rows} Excel rows)")
    if stem_edits:
        logger.info(f"  Wrote back {stem_edits} edited question stems to OPTIMIZEDQUESTION")

    unmatched_qgds = set(qgd_lookup.keys()) - matched_qgds
    if unmatched_qgds:
        logger.warning(f"  {len(unmatched_qgds)} QGDs not found in Excel: {sorted(unmatched_qgds)[:10]}...")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info(f"Saving to: {output_path}")
    df.to_excel(output_path, index=False, engine='openpyxl')

    # ── Summary ──────────────────────────────────────────────────────
    print(f"\n{'='*50}")
    print("EXPORT SUMMARY")
    print(f"{'='*50}")
    print(f"Source:      {input_path.name}")
    print(f"Checkpoint:  {checkpoint_path.name}")
    print(f"Output:      {output_path.name}")
    print(f"QGDs matched: {len(matched_qgds)}/{len(qgd_lookup)}")
    print(f"Excel rows:   {matched_rows}")
    print(f"Stem edits:   {stem_edits}")
    if unmatched_qgds:
        print(f"Unmatched:    {len(unmatched_qgds)} QGDs not found in Excel")
    print(f"Total rows:  {len(df)}")
    print(f"Total cols:  {len(df.columns)}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
