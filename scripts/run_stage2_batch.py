"""
Run Stage 2 tagging in batches with checkpoint support.

Loads from stage2_ready Excel file, filters by disease, runs 3-model voting (GPT/Claude/Gemini).
Saves results with full model vote preservation for review.

RECOMMENDED WORKFLOW:
    1. Run first 25 questions to test
    2. Review accuracy in dashboard
    3. If good, continue with next 25
    4. Repeat until 100 done, evaluate overall

Usage:
    # Batch 1: First 25 MM questions (~$8.00 API cost)
    python scripts/run_stage2_batch.py --disease "Multiple myeloma" --start 0 --limit 25

    # Batch 2: Questions 25-50 (auto-resumes from checkpoint)
    python scripts/run_stage2_batch.py --disease "Multiple myeloma" --start 25 --limit 25

    # Batch 3-4: Continue to 100
    python scripts/run_stage2_batch.py --disease "Multiple myeloma" --start 50 --limit 25
    python scripts/run_stage2_batch.py --disease "Multiple myeloma" --start 75 --limit 25

    # Or run first 100 with resume support
    python scripts/run_stage2_batch.py --disease "Multiple myeloma" --limit 100

    # Dry run (test with first 3 questions, no API calls)
    python scripts/run_stage2_batch.py --disease "Multiple myeloma" --limit 3 --dry-run
"""

import argparse
import asyncio
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional
import json
from datetime import datetime
import sys
import logging

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from src.core.taggers.multi_model_tagger import MultiModelTagger
from src.core.taggers.vote_aggregator import AggregatedVote, AgreementLevel
from src.core.preprocessing.tag_normalizer import normalize_results
import sqlite3

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(PROJECT_ROOT / 'data' / 'checkpoints' / 'stage2_batch.log')
    ]
)
logger = logging.getLogger(__name__)


def get_existing_qgds_from_db() -> set:
    """
    Get QGDs (source_ids) already in dashboard database.

    This prevents re-tagging questions that already exist in the database,
    saving API costs and avoiding accidental overwrites.
    """
    db_path = PROJECT_ROOT / "dashboard" / "data" / "questions.db"
    if not db_path.exists():
        logger.warning(f"Dashboard database not found: {db_path}")
        return set()

    try:
        conn = sqlite3.connect(db_path)
        existing = {str(row[0]) for row in conn.execute('SELECT source_id FROM questions')}
        conn.close()
        logger.info(f"Found {len(existing)} existing questions in dashboard database")
        return existing
    except Exception as e:
        logger.error(f"Error reading dashboard database: {e}")
        return set()


def load_questions_from_excel(
    file_path: str,
    disease_filter: Optional[str] = None,
    start: int = 0,
    limit: Optional[int] = None,
    exclude_qgds: Optional[set] = None
) -> List[Dict]:
    """
    Load questions from stage2_ready Excel file.

    Args:
        file_path: Path to Excel file
        disease_filter: Filter by STAGE1_disease_state
        start: Starting index (after disease filter)
        limit: Maximum number of questions to load
        exclude_qgds: Set of QGDs (source_ids) to exclude (already in database)

    Returns:
        List of question dicts with: id, source_id, question_stem, correct_answer,
        incorrect_answers, disease_state, activities
    """
    logger.info(f"Loading questions from {file_path}")
    df = pd.read_excel(file_path)
    logger.info(f"Total rows in file: {len(df)}")

    # Filter by disease if specified
    if disease_filter:
        df = df[df['STAGE1_disease_state'] == disease_filter]
        logger.info(f"Filtered to {len(df)} {disease_filter} questions")

    # Exclude questions already in database
    if exclude_qgds:
        before_count = len(df)
        df = df[~df['QUESTIONGROUPDESIGNATION'].astype(str).isin(exclude_qgds)]
        excluded_count = before_count - len(df)
        if excluded_count > 0:
            logger.info(f"Excluding {excluded_count} questions that already exist in dashboard database")
        logger.info(f"Remaining: {len(df)} new questions to tag")

    # Apply start offset
    if start > 0:
        df = df.iloc[start:]
        logger.info(f"Starting from index {start}")

    # Apply limit if specified
    if limit:
        df = df.head(limit)
        logger.info(f"Limited to {len(df)} questions (indices {start} to {start + len(df) - 1})")

    questions = []
    for idx, row in df.iterrows():
        # Collect non-null incorrect answers
        incorrect = []
        for i in range(1, 10):
            col_name = f'IANSWER{i}'
            if col_name in row and pd.notna(row[col_name]):
                ans = str(row[col_name]).strip()
                if ans:
                    incorrect.append(ans)

        questions.append({
            'id': int(idx),  # Use DataFrame index as ID
            'source_id': str(row.get('QUESTIONGROUPDESIGNATION', '')),
            'question_stem': str(row['OPTIMIZEDQUESTION']),
            'correct_answer': str(row['OPTIMIZEDCORRECTANSWER']) if pd.notna(row.get('OPTIMIZEDCORRECTANSWER')) else None,
            'incorrect_answers': incorrect,
            'disease_state': str(row['STAGE1_disease_state']),
            'activities': str(row.get('ACTIVITY_NAMES', '')) if pd.notna(row.get('ACTIVITY_NAMES')) else '',
            # Activity dates (parallel to activity names, semicolon-separated)
            'activity_dates': str(row.get('START_DATES', row.get('STARTDATE', ''))) if pd.notna(row.get('START_DATES', row.get('STARTDATE'))) else '',
        })

    return questions


def aggregated_vote_to_dict(result: AggregatedVote, question: Dict) -> Dict[str, Any]:
    """
    Convert AggregatedVote to serializable dict for JSON output.

    Preserves all model votes for review interface.
    """
    return {
        # Question data
        'question_id': result.question_id,
        'source_id': question['source_id'],
        'question_stem': question['question_stem'],
        'correct_answer': question['correct_answer'],
        'incorrect_answers': question['incorrect_answers'],
        'disease_state': question['disease_state'],
        'activities': question['activities'],
        'activity_dates': question.get('activity_dates', ''),  # Parallel dates for each activity

        # Aggregation results
        'final_tags': result.final_tags,
        'agreement': result.overall_agreement.value,
        'confidence': result.overall_confidence,
        'needs_review': result.needs_review,
        'review_reason': result.review_reason,

        # Individual model votes (for review interface)
        'gpt_tags': result.gpt_tags,
        'claude_tags': result.claude_tags,
        'gemini_tags': result.gemini_tags,

        # Per-field vote details
        'field_votes': {
            field_name: {
                'final_value': vote.final_value,
                'gpt_value': vote.gpt_value,
                'claude_value': vote.claude_value,
                'gemini_value': vote.gemini_value,
                'agreement': vote.agreement_level.value,
                'confidence': vote.confidence,
                'dissenting_model': vote.dissenting_model
            }
            for field_name, vote in result.tags.items()
        },

        # Web search info
        'web_searches_used': result.web_searches_used,

        # Timestamp
        'tagged_at': datetime.now().isoformat()
    }


async def process_batch(
    questions: List[Dict],
    batch_size: int = 5,
    checkpoint_file: Optional[Path] = None,
    dry_run: bool = False,
    use_web_search: bool = False
) -> List[Dict]:
    """
    Process questions with 3-model voting and checkpointing.

    Args:
        questions: List of question dicts
        batch_size: Number of questions per checkpoint save
        checkpoint_file: Path to checkpoint file for resume support
        dry_run: If True, skip actual API calls
        use_web_search: If True, enable web search on disagreements

    Returns:
        List of result dicts
    """
    if dry_run:
        logger.info("DRY RUN MODE - No API calls will be made")
        # Return mock results for testing
        return [
            {
                'question_id': q['id'],
                'source_id': q['source_id'],
                'question_stem': q['question_stem'][:100] + '...',
                'disease_state': q['disease_state'],
                'dry_run': True
            }
            for q in questions
        ]

    tagger = MultiModelTagger(prompt_version="v2.0", use_web_search=use_web_search)
    results = []
    processed_ids = set()

    # Resume from checkpoint if exists
    # Track by source_id (QUESTIONGROUPDESIGNATION) for reliable resume across runs
    processed_source_ids = set()
    if checkpoint_file and checkpoint_file.exists():
        logger.info(f"Resuming from checkpoint: {checkpoint_file}")
        with open(checkpoint_file, encoding='utf-8') as f:
            checkpoint = json.load(f)
            results = checkpoint.get('results', [])
            # Extract source_ids from results for reliable tracking
            processed_source_ids = set(str(r.get('source_id', '')) for r in results if r.get('source_id'))
        logger.info(f"Loaded {len(results)} completed results, {len(processed_source_ids)} processed source IDs")

    # Filter to unprocessed questions by source_id
    to_process = [q for q in questions if q['source_id'] not in processed_source_ids]
    logger.info(f"Processing {len(to_process)} questions ({len(processed_ids)} already done)")

    if not to_process:
        logger.info("All questions already processed!")
        return results

    # Process in batches
    for i in range(0, len(to_process), batch_size):
        batch = to_process[i:i+batch_size]
        batch_start = datetime.now()

        for question in batch:
            try:
                logger.info(f"Tagging question {question['id']} ({question['source_id'][:20]}...)")

                # Build temporal context for LLM
                kb_context = {}
                if question.get('startdate'):
                    kb_context['activity_start_date'] = question['startdate']
                if question.get('activities'):
                    kb_context['activity_names'] = question['activities']

                result = await tagger.tag_question(
                    question_id=question['id'],
                    question_text=question['question_stem'],
                    correct_answer=question.get('correct_answer'),
                    incorrect_answers=question.get('incorrect_answers'),
                    kb_context=kb_context if kb_context else None
                )

                result_dict = aggregated_vote_to_dict(result, question)
                results.append(result_dict)
                processed_source_ids.add(question['source_id'])

                # Log agreement level
                logger.info(
                    f"  -> {result.overall_agreement.value} agreement, "
                    f"confidence: {result.overall_confidence:.2f}, "
                    f"needs_review: {result.needs_review}"
                )

            except Exception as e:
                logger.error(f"Error processing question {question['id']}: {e}")
                # Save error result
                results.append({
                    'question_id': question['id'],
                    'source_id': question['source_id'],
                    'disease_state': question['disease_state'],
                    'error': str(e),
                    'tagged_at': datetime.now().isoformat()
                })
                processed_source_ids.add(question['source_id'])

        # Save checkpoint after each batch
        if checkpoint_file:
            checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'processed_source_ids': list(processed_source_ids),
                    'results': results,
                    'timestamp': datetime.now().isoformat()
                }, f, indent=2, ensure_ascii=False)

        batch_duration = (datetime.now() - batch_start).total_seconds()
        logger.info(
            f"Progress: {len(processed_source_ids)}/{len(questions)} questions "
            f"({batch_duration:.1f}s for batch of {len(batch)})"
        )

    # Get cost estimate
    try:
        cost = tagger.client.get_total_cost()
        logger.info(f"Total API cost: ${cost:.2f}")
    except Exception:
        pass

    return results


def main():
    parser = argparse.ArgumentParser(description="Run Stage 2 batch tagging with 3-model voting")
    parser.add_argument(
        "--input",
        default="data/checkpoints/stage2_ready_MASTER.xlsx",
        help="Input Excel file with questions (default: MASTER file with 3,486 questions)"
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output JSON file (default: data/checkpoints/stage2_tagged_{disease}.json)"
    )
    parser.add_argument(
        "--disease",
        default="Multiple myeloma",
        help="Filter by disease state (exact match)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5,
        help="Questions per checkpoint save"
    )
    parser.add_argument(
        "--checkpoint",
        default=None,
        help="Checkpoint file path (default: data/checkpoints/stage2_{disease}_checkpoint.json)"
    )
    parser.add_argument(
        "--start",
        type=int,
        default=0,
        help="Starting index (0-based, after disease filter)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Number of questions to process"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip API calls, just test loading"
    )
    parser.add_argument(
        "--web-search",
        action="store_true",
        help="Enable web search on disagreements (disabled by default - adds cost without clear value)"
    )
    parser.add_argument(
        "--exclude-db",
        action="store_true",
        default=True,
        help="Exclude questions already in dashboard database (default: True)"
    )
    parser.add_argument(
        "--no-exclude-db",
        action="store_false",
        dest="exclude_db",
        help="Disable automatic exclusion of existing questions (DANGEROUS - will re-tag and waste money)"
    )
    args = parser.parse_args()

    # Set default paths based on disease
    disease_slug = args.disease.lower().replace(' ', '_')
    if args.output is None:
        args.output = f"data/checkpoints/stage2_tagged_{disease_slug}.json"
    if args.checkpoint is None:
        args.checkpoint = f"data/checkpoints/stage2_{disease_slug}_checkpoint.json"

    # Get existing QGDs to exclude (if enabled)
    exclude_qgds = set()
    if args.exclude_db:
        exclude_qgds = get_existing_qgds_from_db()
        if not exclude_qgds:
            logger.warning("No existing questions found in database - proceeding without exclusion")

    # Load questions
    input_path = PROJECT_ROOT / args.input
    questions = load_questions_from_excel(
        str(input_path),
        args.disease,
        args.start,
        args.limit,
        exclude_qgds=exclude_qgds
    )

    if not questions:
        logger.error(f"No questions found for disease: {args.disease}")
        return

    logger.info(f"Loaded {len(questions)} {args.disease} questions")

    # Estimate cost
    estimated_cost = len(questions) * 0.32  # ~$0.30-0.35 per question
    logger.info(f"Estimated API cost: ${estimated_cost:.2f}")

    # Run batch processing
    checkpoint_path = PROJECT_ROOT / args.checkpoint
    results = asyncio.run(process_batch(
        questions,
        batch_size=args.batch_size,
        checkpoint_file=checkpoint_path,
        dry_run=args.dry_run,
        use_web_search=args.web_search
    ))

    # Normalize tags before saving (applies alias mappings for consistency)
    if not args.dry_run and results:
        print("\nNormalizing tags...")
        results = normalize_results(results)

    # Save final results (preserving human-reviewed entries from previous runs)
    output_path = PROJECT_ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing output file if it exists to preserve human-reviewed entries
    existing_data = []
    if output_path.exists():
        try:
            with open(output_path, encoding='utf-8') as f:
                existing_data = json.load(f)
            logger.info(f"Loaded {len(existing_data)} existing results from {output_path}")
        except Exception as e:
            logger.warning(f"Could not load existing output file: {e}")

    # Create lookup of existing human-reviewed entries by source_id (QGD)
    # NOTE: We use source_id (not question_id) because question_id is just the DataFrame
    # index which can collide across different batch runs with different input data
    human_reviewed_lookup = {}
    for item in existing_data:
        if item.get('human_reviewed', False):
            human_reviewed_lookup[item['source_id']] = item

    # Also create lookup of ALL existing entries by source_id to detect duplicates
    existing_source_ids = {item['source_id'] for item in existing_data}

    # Merge: preserve human-reviewed entries, add/update non-reviewed
    merged_results = []

    # First, add all human-reviewed entries from existing data
    for item in existing_data:
        if item.get('human_reviewed', False):
            merged_results.append(item)

    # Then add new results (skip if already have human-reviewed version)
    for result in results:
        if result['source_id'] not in human_reviewed_lookup:
            merged_results.append(result)

    # Sort by source_id for consistency
    merged_results.sort(key=lambda x: x['source_id'])

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(merged_results, f, indent=2, ensure_ascii=False)

    preserved_count = len(human_reviewed_lookup)
    new_count = len(merged_results) - preserved_count
    logger.info(f"Saved {len(merged_results)} results to {output_path} ({preserved_count} human-reviewed preserved, {new_count} new/updated)")

    # Print summary
    if not args.dry_run and results:
        agreements = {'unanimous': 0, 'majority': 0, 'conflict': 0}
        needs_review = 0
        new_tag_values = 0
        errors = 0

        for r in results:
            if 'error' in r:
                errors += 1
            elif 'agreement' in r:
                agreements[r['agreement']] = agreements.get(r['agreement'], 0) + 1
                if r.get('needs_review'):
                    needs_review += 1
                # Count questions flagged for new tag values
                review_reason = r.get('review_reason') or ''
                if 'new_tag_values' in review_reason:
                    new_tag_values += 1

        print("\n" + "="*50)
        print("BATCH TAGGING SUMMARY")
        print("="*50)
        print(f"Total questions: {len(results)}")
        print(f"  Unanimous:     {agreements['unanimous']}")
        print(f"  Majority:      {agreements['majority']}")
        print(f"  Conflict:      {agreements['conflict']}")
        print(f"  Errors:        {errors}")
        print(f"Needs review:    {needs_review}")
        if new_tag_values > 0:
            print(f"  New tag values: {new_tag_values}")
        print("="*50)

    # Auto-import to dashboard database
    if not args.dry_run:
        import_script = PROJECT_ROOT / "dashboard" / "scripts" / "import_stage2_results.py"
        if import_script.exists():
            import subprocess
            print("\nImporting to dashboard database...")
            result = subprocess.run(
                ["python", str(import_script), "--file", str(output_path), "--upsert"],
                cwd=str(PROJECT_ROOT / "dashboard"),
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                # Extract key stats from output
                for line in result.stdout.split('\n'):
                    if 'Inserted' in line or 'Updated' in line or 'Total questions' in line:
                        print(line.split(' - ')[-1] if ' - ' in line else line)
            else:
                logger.warning(f"Dashboard import failed: {result.stderr}")

    # Auto-update remaining file (shrinking file approach)
    if not args.dry_run and results:
        update_remaining_file(results, args.input)


def update_remaining_file(results: List[Dict[str, Any]], input_file: str):
    """
    Update the remaining file by removing tagged questions.

    This implements the "shrinking file" approach:
    1. Read the tagging manifest to find current remaining file
    2. Remove newly tagged QGDs from remaining file
    3. Save new timestamped remaining file
    4. Update manifest with new entry
    """
    manifest_path = PROJECT_ROOT / "data" / "checkpoints" / "tagging_manifest.json"

    if not manifest_path.exists():
        logger.warning("No tagging_manifest.json found. Skipping remaining file update.")
        logger.info("To enable this feature, create the manifest with the initial remaining file.")
        return

    try:
        # Load manifest
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)

        current_remaining_file = manifest.get('current_remaining')
        if not current_remaining_file:
            logger.warning("No current_remaining file in manifest. Skipping update.")
            return

        remaining_path = PROJECT_ROOT / "data" / "checkpoints" / current_remaining_file
        if not remaining_path.exists():
            logger.warning(f"Remaining file not found: {remaining_path}")
            return

        # Get QGDs that were just tagged
        tagged_qgds = set()
        for r in results:
            if 'error' not in r:
                # Results store source_id (which is the QGD/QUESTIONGROUPDESIGNATION)
                qgd = r.get('source_id') or r.get('qgd') or r.get('question_id')
                if qgd:
                    tagged_qgds.add(str(qgd))

        if not tagged_qgds:
            logger.info("No successful tags to remove from remaining file.")
            return

        # Load current remaining file
        df_remaining = pd.read_excel(remaining_path)
        original_count = len(df_remaining)

        # Find QGD column (could be QGD or QUESTIONGROUPDESIGNATION or SOURCE_ID)
        qgd_col = None
        for col in ['QGD', 'qgd', 'QUESTIONGROUPDESIGNATION', 'questiongroupdesignation', 'SOURCE_ID', 'source_id']:
            if col in df_remaining.columns:
                qgd_col = col
                break

        if not qgd_col:
            logger.warning(f"Could not find QGD column in {remaining_path}")
            return

        # Remove tagged QGDs
        df_remaining[qgd_col] = df_remaining[qgd_col].astype(str)
        df_new_remaining = df_remaining[~df_remaining[qgd_col].isin(tagged_qgds)]
        new_count = len(df_new_remaining)
        removed_count = original_count - new_count

        if removed_count == 0:
            logger.info("No QGDs removed from remaining file (may have used different source).")
            return

        # Save new remaining file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_remaining_filename = f"stage2_remaining_{timestamp}.xlsx"
        new_remaining_path = PROJECT_ROOT / "data" / "checkpoints" / new_remaining_filename

        df_new_remaining.to_excel(new_remaining_path, index=False)

        # Update manifest
        manifest['current_remaining'] = new_remaining_filename
        manifest['current_remaining_count'] = new_count
        manifest['tagged_count'] = manifest.get('tagged_count', 0) + removed_count
        manifest['last_updated'] = datetime.now().isoformat()

        # Add to history
        if 'history' not in manifest:
            manifest['history'] = []

        manifest['history'].append({
            'file': new_remaining_filename,
            'created': datetime.now().isoformat(),
            'remaining_count': new_count,
            'tagged_in_batch': removed_count,
            'total_tagged': manifest['tagged_count'],
            'note': f"Removed {removed_count} QGDs after tagging batch"
        })

        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2)

        print(f"\n📊 Remaining file updated:")
        print(f"   Previous: {current_remaining_file} ({original_count} questions)")
        print(f"   New:      {new_remaining_filename} ({new_count} questions)")
        print(f"   Removed:  {removed_count} tagged QGDs")
        print(f"   Total tagged so far: {manifest['tagged_count']}")

        logger.info(f"Updated remaining file: {new_remaining_filename} ({new_count} remaining)")

    except Exception as e:
        logger.error(f"Failed to update remaining file: {e}")
        # Don't fail the whole batch for this


if __name__ == "__main__":
    main()
