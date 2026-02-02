"""
Export human-reviewed corrections for Snowflake upload.

This script exports questions that have been reviewed/corrected by humans
from the checkpoint files. The output can be used to update MetaTags in Snowflake.

Usage:
    python scripts/export_corrections_for_snowflake.py --disease "Multiple myeloma"
    python scripts/export_corrections_for_snowflake.py --all
    python scripts/export_corrections_for_snowflake.py --all --format csv
"""

import argparse
import json
import csv
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.backend.services.checkpoint import (
    load_checkpoint,
    get_reviewed_questions,
    normalize_disease_name,
    CHECKPOINTS_DIR,
)


def list_available_diseases():
    """List diseases with checkpoint files available."""
    diseases = []
    for file in CHECKPOINTS_DIR.glob("stage2_tagged_*.json"):
        disease_name = file.stem.replace("stage2_tagged_", "").replace("_", " ").title()
        diseases.append(disease_name)
    return diseases


def export_disease(disease_state: str, output_format: str = "json") -> dict:
    """
    Export reviewed corrections for a disease.

    Returns:
        Dict with export stats
    """
    print(f"\n{'='*60}")
    print(f"Exporting corrections for: {disease_state}")
    print(f"{'='*60}")

    # Load checkpoint
    data = load_checkpoint(disease_state)
    if not data:
        print(f"No checkpoint data found for {disease_state}")
        return {'exported': 0, 'total': 0}

    # Find reviewed questions
    reviewed = [q for q in data if q.get('human_reviewed', False)]
    print(f"Total questions in checkpoint: {len(data)}")
    print(f"Human-reviewed questions: {len(reviewed)}")

    if not reviewed:
        print("No human-reviewed questions to export")
        return {'exported': 0, 'total': len(data)}

    # Prepare export data
    export_records = []
    for q in reviewed:
        final_tags = q.get('final_tags', {})

        record = {
            # Identifiers for Snowflake linkage
            'source_question_id': q.get('question_id'),
            'source_id': q.get('source_id'),

            # Metadata
            'disease_state': q.get('disease_state'),
            'reviewed_at': q.get('human_reviewed_at'),
            'edited_fields': q.get('human_edited_fields', []),

            # Core Tags (map to Snowflake METATAG columns)
            'METATAG1_disease_state': final_tags.get('disease_state') or q.get('disease_state'),
            'METATAG2_topic': final_tags.get('topic'),
            'METATAG3_treatment': final_tags.get('treatment_1'),
            'METATAG4_disease_type': final_tags.get('disease_type_1'),
            'METATAG5_disease_stage': final_tags.get('disease_stage'),
            'METATAG6_treatment_line': final_tags.get('treatment_line'),
            'METATAG7_biomarker': final_tags.get('biomarker_1'),
            'METATAG8_trial': final_tags.get('trial_1'),

            # Extended tags (for future Snowflake expansion)
            'treatment_2': final_tags.get('treatment_2'),
            'treatment_3': final_tags.get('treatment_3'),
            'biomarker_2': final_tags.get('biomarker_2'),
            'biomarker_3': final_tags.get('biomarker_3'),
            'trial_2': final_tags.get('trial_2'),
            'trial_3': final_tags.get('trial_3'),

            # All final_tags as JSON for reference
            'all_tags_json': json.dumps(final_tags, ensure_ascii=False),
        }
        export_records.append(record)

    # Create output directory
    exports_dir = PROJECT_ROOT / "data" / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename
    disease_filename = normalize_disease_name(disease_state)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if output_format == "json":
        output_file = exports_dir / f"snowflake_corrections_{disease_filename}_{timestamp}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_records, f, indent=2, ensure_ascii=False)
    elif output_format == "csv":
        output_file = exports_dir / f"snowflake_corrections_{disease_filename}_{timestamp}.csv"
        if export_records:
            fieldnames = export_records[0].keys()
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(export_records)

    print(f"\nExported {len(export_records)} corrections to:")
    print(f"  {output_file}")

    return {'exported': len(export_records), 'total': len(data), 'file': str(output_file)}


def main():
    parser = argparse.ArgumentParser(description="Export corrections for Snowflake upload")
    parser.add_argument("--disease", type=str, help="Disease state to export")
    parser.add_argument("--all", action="store_true", help="Export all available diseases")
    parser.add_argument("--format", choices=["json", "csv"], default="json", help="Output format")
    parser.add_argument("--list", action="store_true", help="List available diseases")

    args = parser.parse_args()

    if args.list:
        diseases = list_available_diseases()
        print("Available diseases with checkpoint files:")
        for d in diseases:
            print(f"  - {d}")
        return

    if args.all:
        diseases = list_available_diseases()
        total_exported = 0
        files = []

        for disease in diseases:
            result = export_disease(disease, output_format=args.format)
            total_exported += result['exported']
            if result.get('file'):
                files.append(result['file'])

        print(f"\n{'='*60}")
        print(f"TOTAL: Exported {total_exported} corrections across {len(diseases)} diseases")
        if files:
            print("\nExported files:")
            for f in files:
                print(f"  {f}")

    elif args.disease:
        export_disease(args.disease, output_format=args.format)

    else:
        parser.print_help()
        print("\nExamples:")
        print('  python scripts/export_corrections_for_snowflake.py --disease "Multiple myeloma"')
        print('  python scripts/export_corrections_for_snowflake.py --all --format csv')
        print('  python scripts/export_corrections_for_snowflake.py --list')


if __name__ == "__main__":
    main()
