"""
Import Stage 2 tagging results (JSON) into the dashboard database.

Uses QUESTIONGROUPDESIGNATION (QGD = source_id) as the stable key for upsert.
Human-reviewed questions are protected from overwrite by default.

Usage:
    # Upsert (safe default): update existing, insert new, protect human-reviewed
    python dashboard/scripts/import_stage2_results.py --upsert --file data/checkpoints/stage2_tagged_multiple_myeloma.json

    # Upsert all checkpoint files
    python dashboard/scripts/import_stage2_results.py --upsert --all

    # Clear and re-import (DESTRUCTIVE — requires --force)
    python dashboard/scripts/import_stage2_results.py --clear --force --file data/checkpoints/stage2_tagged_multiple_myeloma.json
"""

import sys
from pathlib import Path
import json
import argparse
import logging
import yaml

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dashboard.backend.services.database import DatabaseService
from src.core.preprocessing.tag_normalizer import TagNormalizer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Path to exclusion list
EXCLUSION_LIST_PATH = project_root / "config" / "excluded_questions.yaml"


def load_exclusion_list() -> set:
    """
    Load the set of excluded source_ids from config/excluded_questions.yaml.

    Returns:
        Set of source_id strings that should be excluded from import.
    """
    if not EXCLUSION_LIST_PATH.exists():
        logger.debug("No exclusion list found, no questions will be excluded")
        return set()

    try:
        with open(EXCLUSION_LIST_PATH, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        excluded = set()
        for item in data.get('excluded_questions', []):
            source_id = item.get('source_id')
            if source_id:
                excluded.add(str(source_id))

        if excluded:
            logger.info(f"Loaded exclusion list: {len(excluded)} questions will be filtered out")
        return excluded

    except Exception as e:
        logger.warning(f"Failed to load exclusion list: {e}")
        return set()

# 8 core tags used to compute tag_status
CORE_TAGS = [
    'topic', 'disease_state', 'disease_stage', 'disease_type_1',
    'treatment_line', 'treatment_1', 'biomarker_1', 'trial_1'
]


def compute_worst_case_agreement(result: dict) -> str:
    """
    Compute worst-case agreement across ALL field_votes.

    Used for Questions Needing Review page - shows worst disagreement.

    Returns:
        'verified' - Human-reviewed
        'unanimous' - ALL fields unanimous
        'majority' - Worst disagreement = majority (no conflicts)
        'conflict' - ANY field has conflict
    """
    # If human-reviewed, always return 'verified'
    if result.get('human_reviewed', False):
        return 'verified'

    field_votes = result.get('field_votes', {})
    if not field_votes:
        # No field_votes data - use agreement from checkpoint, or default to conflict
        return result.get('agreement', 'conflict')

    has_conflict = False
    has_majority = False

    for tag_name, vote in field_votes.items():
        agreement = vote.get('agreement', 'unanimous')

        if agreement == 'conflict':
            has_conflict = True
            break  # Can return early - conflict is the worst case
        elif agreement == 'majority':
            has_majority = True

    # Return worst level found
    if has_conflict:
        return 'conflict'
    elif has_majority:
        return 'majority'
    else:
        return 'unanimous'


def compute_tag_status(result: dict) -> str:
    """
    Compute tag_status from field_votes of 8 core tags.

    Returns:
        'verified' - Human-reviewed
        'unanimous' - ALL 8 core tags unanimous
        'majority' - Worst disagreement = majority (no conflicts)
        'conflict' - ANY of 8 core tags has conflict
    """
    # If human-reviewed, always return 'verified'
    if result.get('human_reviewed', False):
        return 'verified'

    field_votes = result.get('field_votes', {})
    if not field_votes:
        # No field_votes data - treat as conflict (unknown)
        return 'conflict'

    has_conflict = False
    has_majority = False

    for tag_name in CORE_TAGS:
        vote = field_votes.get(tag_name, {})
        agreement = vote.get('agreement', 'unanimous')

        if agreement == 'conflict':
            has_conflict = True
        elif agreement == 'majority':
            has_majority = True

    # Return worst level found
    if has_conflict:
        return 'conflict'
    elif has_majority:
        return 'majority'
    else:
        return 'unanimous'


def build_tag_update(result: dict) -> dict:
    """Build the tag update dict from a checkpoint result entry."""
    final_tags = result.get('final_tags', {})

    tag_update = {
        # Core fields
        'topic': final_tags.get('topic'),
        'disease_state': result.get('disease_state') or final_tags.get('disease_state'),
        'disease_state_1': final_tags.get('disease_state_1'),  # Primary disease state (rare cases with 2)
        'disease_state_2': final_tags.get('disease_state_2'),  # Secondary disease state (e.g., MM + NHL)
        'disease_stage': final_tags.get('disease_stage'),
        'disease_type_1': final_tags.get('disease_type_1'),
        'disease_type_2': final_tags.get('disease_type_2'),
        'treatment_line': final_tags.get('treatment_line'),

        # Multi-value treatment fields
        'treatment_1': final_tags.get('treatment_1'),
        'treatment_2': final_tags.get('treatment_2'),
        'treatment_3': final_tags.get('treatment_3'),
        'treatment_4': final_tags.get('treatment_4'),
        'treatment_5': final_tags.get('treatment_5'),

        # Multi-value biomarker fields
        'biomarker_1': final_tags.get('biomarker_1'),
        'biomarker_2': final_tags.get('biomarker_2'),
        'biomarker_3': final_tags.get('biomarker_3'),
        'biomarker_4': final_tags.get('biomarker_4'),
        'biomarker_5': final_tags.get('biomarker_5'),

        # Multi-value trial fields
        'trial_1': final_tags.get('trial_1'),
        'trial_2': final_tags.get('trial_2'),
        'trial_3': final_tags.get('trial_3'),
        'trial_4': final_tags.get('trial_4'),
        'trial_5': final_tags.get('trial_5'),

        # Group B: Patient Characteristics
        'treatment_eligibility': final_tags.get('treatment_eligibility'),
        'age_group': final_tags.get('age_group'),
        'organ_dysfunction': final_tags.get('organ_dysfunction'),
        'fitness_status': final_tags.get('fitness_status'),
        'disease_specific_factor': final_tags.get('disease_specific_factor'),
        'comorbidity_1': final_tags.get('comorbidity_1'),
        'comorbidity_2': final_tags.get('comorbidity_2'),
        'comorbidity_3': final_tags.get('comorbidity_3'),

        # Group C: Treatment Metadata
        'drug_class_1': final_tags.get('drug_class_1'),
        'drug_class_2': final_tags.get('drug_class_2'),
        'drug_class_3': final_tags.get('drug_class_3'),
        'drug_target_1': final_tags.get('drug_target_1'),
        'drug_target_2': final_tags.get('drug_target_2'),
        'drug_target_3': final_tags.get('drug_target_3'),
        'prior_therapy_1': final_tags.get('prior_therapy_1'),
        'prior_therapy_2': final_tags.get('prior_therapy_2'),
        'prior_therapy_3': final_tags.get('prior_therapy_3'),
        'resistance_mechanism': final_tags.get('resistance_mechanism'),

        # Group D: Clinical Context
        'metastatic_site_1': final_tags.get('metastatic_site_1'),
        'metastatic_site_2': final_tags.get('metastatic_site_2'),
        'metastatic_site_3': final_tags.get('metastatic_site_3'),
        'symptom_1': final_tags.get('symptom_1'),
        'symptom_2': final_tags.get('symptom_2'),
        'symptom_3': final_tags.get('symptom_3'),
        'performance_status': final_tags.get('performance_status'),

        # Group E: Safety/Toxicity
        'toxicity_type_1': final_tags.get('toxicity_type_1'),
        'toxicity_type_2': final_tags.get('toxicity_type_2'),
        'toxicity_type_3': final_tags.get('toxicity_type_3'),
        'toxicity_type_4': final_tags.get('toxicity_type_4'),
        'toxicity_type_5': final_tags.get('toxicity_type_5'),
        'toxicity_organ': final_tags.get('toxicity_organ'),
        'toxicity_grade': final_tags.get('toxicity_grade'),

        # Group F: Efficacy/Outcomes
        'efficacy_endpoint_1': final_tags.get('efficacy_endpoint_1'),
        'efficacy_endpoint_2': final_tags.get('efficacy_endpoint_2'),
        'efficacy_endpoint_3': final_tags.get('efficacy_endpoint_3'),
        'outcome_context': final_tags.get('outcome_context'),
        'clinical_benefit': final_tags.get('clinical_benefit'),

        # Group G: Evidence/Guidelines
        'guideline_source_1': final_tags.get('guideline_source_1'),
        'guideline_source_2': final_tags.get('guideline_source_2'),
        'evidence_type': final_tags.get('evidence_type'),

        # Group H: Question Format/Quality
        'cme_outcome_level': final_tags.get('cme_outcome_level'),
        'data_response_type': final_tags.get('data_response_type'),
        'stem_type': final_tags.get('stem_type'),
        'lead_in_type': final_tags.get('lead_in_type'),
        'answer_format': final_tags.get('answer_format'),
        'answer_length_pattern': final_tags.get('answer_length_pattern'),
        'distractor_homogeneity': final_tags.get('distractor_homogeneity'),
        'flaw_absolute_terms': final_tags.get('flaw_absolute_terms'),
        'flaw_grammatical_cue': final_tags.get('flaw_grammatical_cue'),
        'flaw_implausible_distractor': final_tags.get('flaw_implausible_distractor'),
        'flaw_clang_association': final_tags.get('flaw_clang_association'),
        'flaw_convergence_vulnerability': final_tags.get('flaw_convergence_vulnerability'),
        'flaw_double_negative': final_tags.get('flaw_double_negative'),

        # Computed fields
        'answer_option_count': final_tags.get('answer_option_count'),
        'correct_answer_position': final_tags.get('correct_answer_position'),

        # Review metadata
        'needs_review': result.get('needs_review', False),
        'review_reason': result.get('review_reason'),
        'agreement_level': result.get('agreement'),
        'overall_confidence': result.get('confidence'),

        # Computed tag agreement status (based on 8 core tags)
        'tag_status': compute_tag_status(result),

        # Worst-case agreement across ALL fields (for Review page)
        'worst_case_agreement': compute_worst_case_agreement(result),
    }

    # Filter out None values
    return {k: v for k, v in tag_update.items() if v is not None}


def import_stage2_upsert(db: DatabaseService, results: list, force_overwrite: bool = False) -> dict:
    """
    Upsert Stage 2 tagging results by QGD (source_id).

    - If QGD is in exclusion list: SKIP (permanently excluded)
    - If QGD exists in DB and is human-reviewed: SKIP (unless force_overwrite)
    - If QGD exists in DB and not reviewed: UPDATE tags
    - If QGD not in DB: INSERT new question + tags

    Args:
        db: Database service instance
        results: List of result dicts from stage2_tagged_*.json
        force_overwrite: If True, overwrite even human-reviewed questions

    Returns:
        Stats dict with counts
    """
    stats = {'inserted': 0, 'updated': 0, 'skipped_reviewed': 0, 'skipped_error': 0, 'skipped_excluded': 0, 'errors': 0}

    # Initialize normalizer for tag normalization
    try:
        normalizer = TagNormalizer()
        logger.info("TagNormalizer initialized for import normalization")
    except Exception as e:
        logger.warning(f"Failed to initialize TagNormalizer: {e}. Proceeding without normalization.")
        normalizer = None

    # Load exclusion list
    excluded_source_ids = load_exclusion_list()

    for result in results:
        # Normalize tags before import (belt-and-suspenders with tagging script normalization)
        if normalizer:
            try:
                result = normalizer.normalize_result(result)
            except Exception as e:
                logger.warning(f"Normalization failed for result: {e}")

        try:
            # Handle error results — skip if no question data
            if 'error' in result:
                if not result.get('question_stem'):
                    logger.warning(f"Skipping error result for question {result.get('question_id')}: {result['error']}")
                    stats['skipped_error'] += 1
                    continue

            source_id = result.get('source_id')
            if source_id is None:
                logger.warning(f"Result missing source_id (QGD), skipping: question_id={result.get('question_id')}")
                stats['errors'] += 1
                continue

            source_id_str = str(source_id)

            # Check exclusion list
            if source_id_str in excluded_source_ids:
                logger.debug(f"Skipping excluded QGD={source_id_str} (question_id={result.get('question_id')})")
                stats['skipped_excluded'] += 1
                continue
            source_question_id = result.get('question_id')
            question_stem = result.get('question_stem', '')
            correct_answer = result.get('correct_answer')
            incorrect_answers = result.get('incorrect_answers', [])
            source_file = f"stage2_batch_{result.get('disease_state', 'unknown')}"

            # Look up by QGD
            existing = db.get_question_by_source_id(source_id_str)

            if existing:
                # Question already in DB
                # Check BOTH DB flag (edited_by_user) AND checkpoint flag (human_reviewed)
                is_human_reviewed = existing['edited_by_user'] or result.get('human_reviewed', False)
                if is_human_reviewed and not force_overwrite:
                    logger.debug(f"Skipping human-reviewed QGD={source_id_str} (DB id={existing['id']})")
                    stats['skipped_reviewed'] += 1
                    continue

                # Use the checkpoint stem, but prefer DB stem if it was user-edited
                # (question_stem_edited flag in checkpoint means user edited via dashboard)
                stem_to_use = question_stem
                if result.get('question_stem_edited'):
                    # Checkpoint already has the edited stem — use it
                    stem_to_use = question_stem
                elif existing.get('question_stem') and existing['question_stem'] != question_stem:
                    # DB stem differs from checkpoint but no edit flag — preserve DB version
                    # (user may have edited via dashboard without checkpoint write-back)
                    logger.info(f"Preserving DB question_stem for QGD={source_id_str} (differs from checkpoint)")
                    stem_to_use = existing['question_stem']

                # Update question data
                db.update_question(
                    question_id=existing['id'],
                    question_stem=stem_to_use,
                    correct_answer=correct_answer,
                    incorrect_answers=incorrect_answers if incorrect_answers else None,
                    source_file=source_file,
                )

                # Update tags
                tag_update = build_tag_update(result)
                db.update_tags(existing['id'], tag_update)

                # Calculate QCore score for the updated question
                try:
                    db.calculate_qcore_for_question(existing['id'])
                except Exception as e:
                    logger.warning(f"QCore scoring failed for QGD={source_id_str}: {e}")

                stats['updated'] += 1
            else:
                # Insert new question
                db_question_id = db.insert_question(
                    question_stem=question_stem,
                    correct_answer=correct_answer,
                    incorrect_answers=incorrect_answers if incorrect_answers else None,
                    source_file=source_file,
                    source_question_id=source_question_id,
                    source_id=source_id,
                )

                # Insert minimal tag record then update with all fields
                db.insert_tags(
                    db_question_id,
                    topic=result.get('final_tags', {}).get('topic'),
                    disease_state=result.get('disease_state') or result.get('final_tags', {}).get('disease_state'),
                    needs_review=result.get('needs_review', False),
                    overall_confidence=result.get('confidence'),
                )

                tag_update = build_tag_update(result)
                db.update_tags(db_question_id, tag_update)

                # Calculate QCore score for the new question
                try:
                    db.calculate_qcore_for_question(db_question_id)
                except Exception as e:
                    logger.warning(f"QCore scoring failed for new question (QGD={source_id}): {e}")

                # Insert activities if present (with dates when available)
                activities = result.get('activities', '')
                activity_dates = result.get('activity_dates', '')
                if activities:
                    activity_list = [a.strip() for a in activities.split('; ') if a.strip()]
                    date_list = [d.strip() for d in activity_dates.split('; ')] if activity_dates else []

                    for i, activity_name in enumerate(activity_list):
                        # Get corresponding date if available (parallel lists)
                        activity_date = None
                        if i < len(date_list) and date_list[i]:
                            try:
                                from datetime import datetime
                                activity_date = datetime.strptime(date_list[i], '%Y-%m-%d').date()
                            except (ValueError, TypeError):
                                pass  # Skip invalid dates

                        if activity_date:
                            db.insert_activity_with_date(db_question_id, activity_name, activity_date)
                        else:
                            db.insert_activity(db_question_id, activity_name)

                stats['inserted'] += 1

        except Exception as e:
            logger.error(f"Error importing result (QGD={result.get('source_id')}): {e}")
            stats['errors'] += 1

    return stats


def import_stage2_clear(db: DatabaseService, results: list) -> dict:
    """
    Clear database and insert all results fresh.
    Only used with --clear --force.
    """
    db.clear_database()
    logger.info("Database cleared")

    stats = {'inserted': 0, 'skipped_error': 0, 'skipped_excluded': 0, 'errors': 0}

    # Load exclusion list
    excluded_source_ids = load_exclusion_list()

    for result in results:
        try:
            if 'error' in result:
                if not result.get('question_stem'):
                    stats['skipped_error'] += 1
                    continue

            source_question_id = result.get('question_id')
            source_id = result.get('source_id')

            # Check exclusion list
            if source_id and str(source_id) in excluded_source_ids:
                logger.debug(f"Skipping excluded QGD={source_id} (question_id={source_question_id})")
                stats['skipped_excluded'] += 1
                continue
            question_stem = result.get('question_stem', '')
            correct_answer = result.get('correct_answer')
            incorrect_answers = result.get('incorrect_answers', [])

            db_question_id = db.insert_question(
                question_stem=question_stem,
                correct_answer=correct_answer,
                incorrect_answers=incorrect_answers if incorrect_answers else None,
                source_file=f"stage2_batch_{result.get('disease_state', 'unknown')}",
                source_question_id=source_question_id,
                source_id=source_id,
            )

            db.insert_tags(
                db_question_id,
                topic=result.get('final_tags', {}).get('topic'),
                disease_state=result.get('disease_state') or result.get('final_tags', {}).get('disease_state'),
                needs_review=result.get('needs_review', False),
                overall_confidence=result.get('confidence'),
            )

            tag_update = build_tag_update(result)
            db.update_tags(db_question_id, tag_update)

            # Calculate QCore score for the new question
            try:
                db.calculate_qcore_for_question(db_question_id)
            except Exception as e:
                logger.warning(f"QCore scoring failed for question (QGD={source_id}): {e}")

            activities = result.get('activities', '')
            if activities:
                for activity_name in activities.split(', '):
                    if activity_name.strip():
                        db.insert_activity(db_question_id, activity_name.strip())

            stats['inserted'] += 1

        except Exception as e:
            logger.error(f"Error importing result: {e}")
            stats['errors'] += 1

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Import Stage 2 tagging results into dashboard database",
        epilog="You must specify either --upsert or --clear (with --force)."
    )
    parser.add_argument(
        "--file",
        type=str,
        help="Path to stage2_tagged_*.json file"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Import all stage2_tagged_*.json files from data/checkpoints"
    )

    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--upsert",
        action="store_true",
        help="Upsert by QGD: update existing, insert new, protect human-reviewed"
    )
    mode_group.add_argument(
        "--clear",
        action="store_true",
        help="Clear database and re-import from scratch (DESTRUCTIVE — requires --force)"
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Required with --clear. With --upsert, also overwrites human-reviewed questions."
    )
    args = parser.parse_args()

    # Validate arguments
    if not args.file and not args.all:
        parser.error("Must specify --file or --all")

    if not args.upsert and not args.clear:
        parser.error(
            "Must specify an import mode:\n"
            "  --upsert  (safe: update existing, insert new, protect human-reviewed)\n"
            "  --clear   (destructive: wipe DB and re-import, requires --force)"
        )

    if args.clear and not args.force:
        parser.error("--clear requires --force to confirm destructive operation")

    # Database path
    db_path = Path(__file__).parent.parent / "data" / "questions.db"
    logger.info(f"Database path: {db_path}")
    logger.info(f"Mode: {'upsert' if args.upsert else 'clear+reimport'}")

    # Initialize database
    db = DatabaseService(db_path)

    # Collect files to import
    files_to_import = []
    if args.file:
        files_to_import.append(Path(args.file))
    elif args.all:
        checkpoint_dir = project_root / "data" / "checkpoints"
        files_to_import = list(checkpoint_dir.glob("stage2_tagged_*.json"))

    logger.info(f"Found {len(files_to_import)} files to import")

    # Aggregate all results (for --clear, we need all data before clearing)
    all_results = []
    for file_path in files_to_import:
        logger.info(f"Loading {file_path.name}...")
        with open(file_path, encoding='utf-8') as f:
            data = json.load(f)
        # Handle both flat list and nested {"results": [...]} format
        if isinstance(data, dict) and 'results' in data:
            results = data['results']
        else:
            results = data
        logger.info(f"  {len(results)} results")
        all_results.extend(results)

    logger.info(f"Total results to import: {len(all_results)}")

    # Import
    if args.clear:
        stats = import_stage2_clear(db, all_results)
        logger.info(f"\n{'='*50}")
        logger.info("CLEAR + IMPORT complete")
        logger.info(f"  Inserted:            {stats['inserted']}")
        logger.info(f"  Skipped (excluded):  {stats['skipped_excluded']}")
        logger.info(f"  Skipped (errors):    {stats['skipped_error']}")
        logger.info(f"  Errors:              {stats['errors']}")
    else:
        stats = import_stage2_upsert(db, all_results, force_overwrite=args.force)
        logger.info(f"\n{'='*50}")
        logger.info("UPSERT complete")
        logger.info(f"  Inserted (new):       {stats['inserted']}")
        logger.info(f"  Updated (existing):   {stats['updated']}")
        logger.info(f"  Skipped (excluded):   {stats['skipped_excluded']}")
        logger.info(f"  Skipped (reviewed):   {stats['skipped_reviewed']}")
        logger.info(f"  Skipped (errors):     {stats['skipped_error']}")
        logger.info(f"  Errors:               {stats['errors']}")

    # Get database stats
    db_stats = db.get_stats()
    logger.info(f"\nDatabase stats:")
    logger.info(f"  Total questions: {db_stats['total_questions']}")
    logger.info(f"  Tagged questions: {db_stats['tagged_questions']}")
    logger.info(f"{'='*50}")


if __name__ == "__main__":
    main()
