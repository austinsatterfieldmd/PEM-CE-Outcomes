"""
Sync Tags from SQLite Database to Excel File

This script reads tagged question data from the SQLite database and merges it
into the raw Excel file, joining on QGD (QuestionGroupDesignation).

Usage:
    python scripts/sync_tags_to_excel.py [--input INPUT_FILE] [--output OUTPUT_FILE] [--dry-run]

Arguments:
    --input     Path to input Excel file (default: data/raw/FullColumnsSample_v2_012026.xlsx)
    --output    Path to output Excel file (default: data/output/tagged_outcomes_{timestamp}.xlsx)
    --dry-run   Show what would be updated without writing file

Output:
    Creates a new Excel file with tags from the database merged in.
    Only updates rows where QGD exists in the database.
"""

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

import pandas as pd

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent

# Default paths
DEFAULT_INPUT = PROJECT_ROOT / "data" / "raw" / "FullColumnsSample_v2_012026.xlsx"
DEFAULT_DB = PROJECT_ROOT / "dashboard" / "data" / "questions.db"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "output"

# Column mapping: database column -> Excel column
TAG_COLUMN_MAPPING = {
    # Core fields
    "disease_state": "DISEASE_STATE1",
    "disease_state_2": "DISEASE_STATE2",
    "topic": "TOPIC",
    "disease_type": "DISEASE_TYPE",
    "disease_stage": "DISEASE_STAGE",
    "treatment_line": "TREATMENT_LINE",

    # Treatment slots (1-5)
    "treatment_1": "TREATMENT_1",
    "treatment_2": "TREATMENT_2",
    "treatment_3": "TREATMENT_3",
    "treatment_4": "TREATMENT_4",
    "treatment_5": "TREATMENT_5",

    # Biomarker slots (1-5)
    "biomarker_1": "BIOMARKER_1",
    "biomarker_2": "BIOMARKER_2",
    "biomarker_3": "BIOMARKER_3",
    "biomarker_4": "BIOMARKER_4",
    "biomarker_5": "BIOMARKER_5",

    # Trial slots (1-5)
    "trial_1": "TRIAL_1",
    "trial_2": "TRIAL_2",
    "trial_3": "TRIAL_3",
    "trial_4": "TRIAL_4",
    "trial_5": "TRIAL_5",
}

# Additional fields that exist in database but not in original Excel
# These will be added as new columns if --include-extended is passed
EXTENDED_COLUMN_MAPPING = {
    # Patient characteristics
    "treatment_eligibility": "TREATMENT_ELIGIBILITY",
    "age_group": "AGE_GROUP",
    "fitness_status": "FITNESS_STATUS",
    "disease_specific_factor": "DISEASE_SPECIFIC_FACTOR",
    "comorbidity_1": "COMORBIDITY_1",
    "comorbidity_2": "COMORBIDITY_2",
    "comorbidity_3": "COMORBIDITY_3",

    # Treatment metadata
    "drug_class_1": "DRUG_CLASS_1",
    "drug_class_2": "DRUG_CLASS_2",
    "drug_class_3": "DRUG_CLASS_3",
    "drug_target_1": "DRUG_TARGET_1",
    "prior_therapy_1": "PRIOR_THERAPY_1",

    # Clinical context
    "performance_status": "PERFORMANCE_STATUS",

    # Safety/toxicity
    "toxicity_type_1": "TOXICITY_TYPE_1",
    "toxicity_organ": "TOXICITY_ORGAN",

    # Efficacy/outcomes
    "efficacy_endpoint_1": "EFFICACY_ENDPOINT_1",
    "outcome_context": "OUTCOME_CONTEXT",
    "clinical_benefit": "CLINICAL_BENEFIT",

    # Evidence/guidelines
    "guideline_source_1": "GUIDELINE_SOURCE_1",
    "evidence_type": "EVIDENCE_TYPE",
}


def get_tags_from_database(db_path: Path) -> Dict[int, Dict[str, Any]]:
    """
    Query all tags from the database, keyed by source_id (QGD).

    Returns:
        Dict mapping source_id (QGD) -> tag values
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Get all columns from tags table
    db_columns = list(TAG_COLUMN_MAPPING.keys()) + list(EXTENDED_COLUMN_MAPPING.keys())

    # Build query - need to handle columns that might not exist
    query = """
        SELECT
            q.source_id,
            q.canonical_source_id,
            t.*
        FROM questions q
        JOIN tags t ON q.id = t.question_id
        WHERE q.source_id IS NOT NULL
    """

    cursor = conn.cursor()
    cursor.execute(query)

    tags_by_qgd = {}
    for row in cursor.fetchall():
        source_id = row["source_id"]
        canonical_source_id = row["canonical_source_id"]

        # Skip duplicates (questions that point to a different canonical)
        if canonical_source_id and str(canonical_source_id) != str(source_id):
            continue

        # Extract tag values
        tag_values = {}
        for db_col in TAG_COLUMN_MAPPING.keys():
            try:
                val = row[db_col]
                # Normalize None/''/null to empty string
                tag_values[db_col] = val if val else ""
            except IndexError:
                tag_values[db_col] = ""

        # Also get extended columns if available
        for db_col in EXTENDED_COLUMN_MAPPING.keys():
            try:
                val = row[db_col]
                tag_values[db_col] = val if val else ""
            except (IndexError, KeyError):
                tag_values[db_col] = ""

        tags_by_qgd[source_id] = tag_values

    conn.close()
    return tags_by_qgd


def sync_tags_to_excel(
    input_path: Path,
    output_path: Path,
    db_path: Path,
    include_extended: bool = False,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Sync tags from database to Excel file.

    Args:
        input_path: Path to input Excel file
        output_path: Path to output Excel file
        db_path: Path to SQLite database
        include_extended: Include extended tag columns (not in original Excel)
        dry_run: If True, don't write output file

    Returns:
        Dict with sync statistics
    """
    print(f"\n=== Tag Sync to Excel ===")
    print(f"Input:  {input_path}")
    print(f"Output: {output_path}")
    print(f"DB:     {db_path}")
    print(f"Mode:   {'DRY RUN' if dry_run else 'WRITE'}")

    # Load Excel file
    print(f"\nLoading Excel file...")
    df = pd.read_excel(input_path)
    print(f"  Rows: {len(df)}")
    print(f"  Columns: {len(df.columns)}")

    # Get tags from database
    print(f"\nLoading tags from database...")
    tags_by_qgd = get_tags_from_database(db_path)
    print(f"  Tagged questions: {len(tags_by_qgd)}")

    # Find matching QGDs
    excel_qgds = set(df["QUESTIONGROUPDESIGNATION"].dropna().astype(int))
    db_qgds = set(tags_by_qgd.keys())
    matching_qgds = excel_qgds & db_qgds

    print(f"\n  QGDs in Excel: {len(excel_qgds)}")
    print(f"  QGDs in DB: {len(db_qgds)}")
    print(f"  Matching: {len(matching_qgds)}")

    # Determine which columns to update
    column_mapping = TAG_COLUMN_MAPPING.copy()
    if include_extended:
        column_mapping.update(EXTENDED_COLUMN_MAPPING)

    # Track statistics
    stats = {
        "rows_total": len(df),
        "rows_updated": 0,
        "rows_skipped": 0,
        "qgds_matched": len(matching_qgds),
        "qgds_not_in_db": len(excel_qgds - db_qgds),
        "fields_updated": {col: 0 for col in column_mapping.values()},
    }

    # Ensure all target columns exist and are string type
    for excel_col in column_mapping.values():
        if excel_col not in df.columns:
            df[excel_col] = ""
        # Convert column to string type to avoid dtype warnings
        df[excel_col] = df[excel_col].fillna("").astype(str)

    # Update rows
    print(f"\nUpdating rows...")
    for idx, row in df.iterrows():
        qgd = row["QUESTIONGROUPDESIGNATION"]

        # Skip if no QGD or not in database
        if pd.isna(qgd):
            stats["rows_skipped"] += 1
            continue

        qgd = int(qgd)
        if qgd not in tags_by_qgd:
            stats["rows_skipped"] += 1
            continue

        # Get tags for this QGD
        tags = tags_by_qgd[qgd]

        # Update each tag column
        for db_col, excel_col in column_mapping.items():
            new_val = tags.get(db_col, "")
            old_val = row.get(excel_col, "")

            # Normalize for comparison
            old_str = str(old_val) if pd.notna(old_val) else ""
            new_str = str(new_val) if new_val else ""

            if new_str != old_str:
                df.at[idx, excel_col] = new_str
                stats["fields_updated"][excel_col] += 1

        stats["rows_updated"] += 1

    # Print summary
    print(f"\n=== Sync Summary ===")
    print(f"  Rows updated: {stats['rows_updated']}")
    print(f"  Rows skipped: {stats['rows_skipped']}")
    print(f"  QGDs not in DB: {stats['qgds_not_in_db']}")

    print(f"\n  Fields updated:")
    for col, count in stats["fields_updated"].items():
        if count > 0:
            print(f"    {col}: {count} values")

    # Write output
    if not dry_run:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_excel(output_path, index=False)
        print(f"\n[SUCCESS] Output written to: {output_path}")
    else:
        print(f"\n[DRY RUN] Would write to: {output_path}")

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Sync tags from SQLite database to Excel file"
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Input Excel file (default: {DEFAULT_INPUT})"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output Excel file (default: auto-generated with timestamp)"
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB,
        help=f"SQLite database path (default: {DEFAULT_DB})"
    )
    parser.add_argument(
        "--include-extended",
        action="store_true",
        help="Include extended tag columns (not in original Excel)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without writing file"
    )

    args = parser.parse_args()

    # Generate output path if not provided
    if args.output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output = DEFAULT_OUTPUT_DIR / f"tagged_outcomes_{timestamp}.xlsx"

    # Validate paths
    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}")
        return 1

    if not args.db.exists():
        print(f"Error: Database not found: {args.db}")
        return 1

    # Run sync
    stats = sync_tags_to_excel(
        input_path=args.input,
        output_path=args.output,
        db_path=args.db,
        include_extended=args.include_extended,
        dry_run=args.dry_run
    )

    return 0


if __name__ == "__main__":
    exit(main())
