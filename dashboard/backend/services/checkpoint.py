"""
Checkpoint service for updating stage2_tagged_*.json files with human corrections.

This ensures the checkpoint files (source of truth) are updated when:
1. User edits tags in the dashboard
2. User marks a question as reviewed

The checkpoint files can then be exported back to Snowflake.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

# Path to checkpoints directory (relative to project root)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
CHECKPOINTS_DIR = PROJECT_ROOT / "data" / "checkpoints"


def normalize_disease_name(disease_state: str) -> str:
    """Normalize disease name for filename matching."""
    if not disease_state:
        return "unknown"
    return disease_state.lower().replace(" ", "_").replace("/", "_")


def get_checkpoint_file(disease_state: str) -> Path:
    """Get the checkpoint file path for a disease."""
    disease_name = normalize_disease_name(disease_state)
    return CHECKPOINTS_DIR / f"stage2_tagged_{disease_name}.json"


def load_checkpoint(disease_state: str) -> List[Dict[str, Any]]:
    """Load checkpoint file for a disease."""
    checkpoint_file = get_checkpoint_file(disease_state)

    if not checkpoint_file.exists():
        logger.warning(f"Checkpoint file not found: {checkpoint_file}")
        return []

    try:
        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load checkpoint {checkpoint_file}: {e}")
        return []


def save_checkpoint(disease_state: str, data: List[Dict[str, Any]]) -> bool:
    """Save checkpoint file for a disease."""
    checkpoint_file = get_checkpoint_file(disease_state)

    try:
        # Create backup before overwriting (delete old backup first on Windows)
        if checkpoint_file.exists():
            backup_file = checkpoint_file.with_suffix('.json.bak')
            if backup_file.exists():
                backup_file.unlink()  # Delete existing backup
            checkpoint_file.rename(backup_file)

        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved checkpoint file: {checkpoint_file}")
        return True

    except Exception as e:
        logger.error(f"Failed to save checkpoint {checkpoint_file}: {e}")
        return False


def update_question_in_checkpoint(
    source_question_id: int,
    disease_state: str,
    corrected_tags: Dict[str, Any],
    edited_fields: List[str],
) -> bool:
    """
    Update a question's tags in the checkpoint file.

    Args:
        source_question_id: The original question_id from the checkpoint
        disease_state: Disease state to find the correct checkpoint file
        corrected_tags: The human-corrected tags
        edited_fields: List of field names that were edited

    Returns:
        True if updated successfully, False otherwise
    """
    # Load checkpoint
    data = load_checkpoint(disease_state)
    if not data:
        logger.warning(f"No checkpoint data for {disease_state}")
        return False

    # Find the question by source_question_id
    question_found = False
    for question in data:
        if question.get('question_id') == source_question_id:
            # Update final_tags with corrected values
            if 'final_tags' not in question:
                question['final_tags'] = {}

            for field, value in corrected_tags.items():
                # Skip metadata fields
                if field in ['needs_review', 'review_reason', 'agreement_level',
                             'overall_confidence', 'flagged_at']:
                    continue
                question['final_tags'][field] = value

            # Mark as human-reviewed
            question['needs_review'] = False
            question['human_reviewed'] = True
            question['human_reviewed_at'] = datetime.now().isoformat()
            question['human_edited_fields'] = edited_fields

            # Update review_reason to indicate human review
            original_reason = question.get('review_reason', '')
            if original_reason:
                question['review_reason'] = f"{original_reason}|human_reviewed"
            else:
                question['review_reason'] = "human_reviewed"

            question_found = True
            logger.info(f"Updated question {source_question_id} in checkpoint: {len(edited_fields)} fields edited")
            break

    if not question_found:
        logger.warning(f"Question {source_question_id} not found in checkpoint for {disease_state}")
        return False

    # Save updated checkpoint
    return save_checkpoint(disease_state, data)


def update_question_stem_in_checkpoint(
    source_question_id: int,
    disease_state: str,
    new_question_stem: str,
) -> bool:
    """
    Update a question's stem in the checkpoint file and flag it for Excel write-back.

    Sets question_stem_edited=True so the export script knows to write
    the new stem back to OPTIMIZEDQUESTION in Excel.

    Args:
        source_question_id: The original question_id from the checkpoint
        disease_state: Disease state to find the correct checkpoint file
        new_question_stem: The edited question stem text

    Returns:
        True if updated successfully, False otherwise
    """
    data = load_checkpoint(disease_state)
    if not data:
        logger.warning(f"No checkpoint data for {disease_state}")
        return False

    for question in data:
        if question.get('question_id') == source_question_id:
            question['question_stem'] = new_question_stem
            question['question_stem_edited'] = True
            logger.info(f"Updated question_stem for {source_question_id} in checkpoint")
            return save_checkpoint(disease_state, data)

    logger.warning(f"Question {source_question_id} not found in checkpoint for {disease_state}")
    return False


def update_question_oncology_status_in_checkpoint(
    source_question_id: int,
    disease_state: str,
    is_oncology: bool,
) -> bool:
    """
    Update a question's oncology status in the checkpoint file.

    Args:
        source_question_id: The original question_id from the checkpoint
        disease_state: Disease state to find the correct checkpoint file
        is_oncology: Whether the question is oncology-related

    Returns:
        True if updated successfully, False otherwise
    """
    data = load_checkpoint(disease_state)
    if not data:
        logger.warning(f"No checkpoint data for {disease_state}")
        return False

    for question in data:
        if question.get('question_id') == source_question_id:
            question['is_oncology'] = is_oncology
            question['human_reviewed'] = True
            question['human_reviewed_at'] = datetime.now().isoformat()
            logger.info(f"Updated is_oncology={is_oncology} for question {source_question_id} in checkpoint")
            return save_checkpoint(disease_state, data)

    logger.warning(f"Question {source_question_id} not found in checkpoint for {disease_state}")
    return False


def get_reviewed_questions(disease_state: str) -> List[Dict[str, Any]]:
    """
    Get all human-reviewed questions from a checkpoint.

    Returns questions with human_reviewed=True, suitable for export to Snowflake.
    """
    data = load_checkpoint(disease_state)
    return [q for q in data if q.get('human_reviewed', False)]


def export_corrections_for_snowflake(disease_state: str, output_file: Optional[Path] = None) -> Path:
    """
    Export human-reviewed corrections in a format suitable for Snowflake upload.

    Creates a JSON file with:
    - source_id (for linking to Snowflake QUESTIONID)
    - source_question_id
    - corrected final_tags
    - human_edited_fields

    Args:
        disease_state: Disease to export corrections for
        output_file: Optional output path (default: data/exports/corrections_{disease}.json)

    Returns:
        Path to the exported file
    """
    reviewed = get_reviewed_questions(disease_state)

    if not reviewed:
        logger.warning(f"No reviewed questions found for {disease_state}")
        return None

    # Prepare export data
    export_data = []
    for q in reviewed:
        export_record = {
            'source_question_id': q.get('question_id'),
            'source_id': q.get('source_id'),
            'disease_state': q.get('disease_state'),
            'corrected_tags': q.get('final_tags', {}),
            'edited_fields': q.get('human_edited_fields', []),
            'reviewed_at': q.get('human_reviewed_at'),
        }
        export_data.append(export_record)

    # Determine output path
    if output_file is None:
        exports_dir = PROJECT_ROOT / "data" / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)
        disease_name = normalize_disease_name(disease_state)
        output_file = exports_dir / f"corrections_{disease_name}.json"

    # Write export file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)

    logger.info(f"Exported {len(export_data)} corrections to {output_file}")
    return output_file


def export_to_multispecialty(
    source_id: str,
    question_stem: str,
    correct_answer: str,
    activities: str = "",
    disease_state: str = "Non-oncology",
    source: str = "Dashboard review",
) -> bool:
    """
    Append a non-oncology question to the multispecialty_questions.xlsx file.

    Args:
        source_id: QUESTIONGROUPDESIGNATION (QGD)
        question_stem: The question text
        correct_answer: The correct answer
        activities: Comma-separated activity names
        disease_state: The assigned disease state (e.g., "Secondary immunodeficiency")
        source: Source identifier for tracking

    Returns:
        True if exported successfully, False otherwise
    """
    try:
        import pandas as pd

        multispecialty_file = CHECKPOINTS_DIR / "multispecialty_questions.xlsx"

        # Load existing file or create new
        if multispecialty_file.exists():
            df = pd.read_excel(multispecialty_file)
        else:
            df = pd.DataFrame(columns=[
                'QUESTIONGROUPDESIGNATION', 'OPTIMIZEDQUESTION', 'OPTIMIZEDCORRECTANSWER',
                'ACTIVITY_NAMES', 'START_DATES', 'FINAL_disease_state', 'SOURCE', 'ADC_OCULAR_TOXICITY'
            ])

        # Check if already exists
        source_id_int = int(source_id) if source_id else 0
        if source_id_int in df['QUESTIONGROUPDESIGNATION'].values:
            logger.info(f"Question {source_id} already exists in multispecialty file, skipping")
            return True

        # Create new row
        new_row = {
            'QUESTIONGROUPDESIGNATION': source_id_int,
            'OPTIMIZEDQUESTION': question_stem,
            'OPTIMIZEDCORRECTANSWER': correct_answer,
            'ACTIVITY_NAMES': activities or '',
            'START_DATES': '',
            'FINAL_disease_state': disease_state,
            'SOURCE': source,
            'ADC_OCULAR_TOXICITY': False
        }

        # Append and save
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.to_excel(multispecialty_file, index=False)

        logger.info(f"Exported question {source_id} to multispecialty_questions.xlsx")
        return True

    except Exception as e:
        logger.error(f"Failed to export to multispecialty file: {e}")
        return False
