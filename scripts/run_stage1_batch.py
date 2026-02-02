"""
Run Stage 1 classification on all untagged questions with crash recovery.

Features:
- Incremental checkpointing: saves progress every N questions
- Crash recovery: automatically resumes from last checkpoint
- Skips already-tagged QGDs
- Progress tracking with ETA

Usage:
    python scripts/run_stage1_batch.py --input data/raw/untagged_questions_20260121_225129.xlsx
    python scripts/run_stage1_batch.py --resume  # Resume from last checkpoint
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv(Path(__file__).parent.parent / ".env")

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.taggers.disease_classifier import DiseaseClassifier
from core.taggers.openrouter_client import get_openrouter_client
from core.taggers.review_flagger import ReviewFlagger

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Checkpoint settings
CHECKPOINT_DIR = Path("data/checkpoints")
CHECKPOINT_INTERVAL = 50  # Save every N questions


def get_checkpoint_path(batch_id: str) -> Path:
    """Get checkpoint file path for a batch."""
    return CHECKPOINT_DIR / f"stage1_checkpoint_{batch_id}.json"


def get_results_path(batch_id: str) -> Path:
    """Get results file path for a batch."""
    return CHECKPOINT_DIR / f"stage1_results_{batch_id}.xlsx"


def save_checkpoint(batch_id: str, processed_qgds: set, results: list, start_time: datetime):
    """Save checkpoint with processed QGDs and results."""
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

    checkpoint = {
        'batch_id': batch_id,
        'processed_qgds': list(processed_qgds),
        'processed_count': len(processed_qgds),
        'start_time': start_time.isoformat(),
        'last_save': datetime.now().isoformat(),
    }

    checkpoint_path = get_checkpoint_path(batch_id)
    with open(checkpoint_path, 'w') as f:
        json.dump(checkpoint, f, indent=2)

    # Also save results to Excel
    if results:
        results_df = pd.DataFrame(results)
        results_path = get_results_path(batch_id)
        results_df.to_excel(results_path, index=False)

    logger.info(f"Checkpoint saved: {len(processed_qgds)} questions processed")


def load_checkpoint(batch_id: str) -> tuple:
    """Load checkpoint if exists. Returns (processed_qgds, results, start_time)."""
    checkpoint_path = get_checkpoint_path(batch_id)
    results_path = get_results_path(batch_id)

    if not checkpoint_path.exists():
        return set(), [], None

    try:
        with open(checkpoint_path, 'r') as f:
            checkpoint = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Failed to load checkpoint file: {e}")
        return set(), [], None

    processed_qgds = set(checkpoint.get('processed_qgds', []))
    start_time = datetime.fromisoformat(checkpoint['start_time']) if checkpoint.get('start_time') else None

    # Load existing results (with error handling for corrupted files)
    results = []
    if results_path.exists():
        try:
            # Check file size first
            if results_path.stat().st_size > 0:
                results_df = pd.read_excel(results_path)
                results = results_df.to_dict('records')
            else:
                logger.warning(f"Results file is empty, will regenerate")
        except Exception as e:
            logger.warning(f"Failed to load results file: {e}")

    logger.info(f"Resumed from checkpoint: {len(processed_qgds)} questions already processed")

    return processed_qgds, results, start_time


def find_latest_checkpoint() -> str:
    """Find the most recent checkpoint batch_id."""
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

    checkpoints = list(CHECKPOINT_DIR.glob("stage1_checkpoint_*.json"))
    if not checkpoints:
        return None

    # Sort by modification time, get latest
    latest = max(checkpoints, key=lambda p: p.stat().st_mtime)
    # Extract batch_id from filename
    batch_id = latest.stem.replace("stage1_checkpoint_", "")
    return batch_id


async def run_stage1_batch(
    input_file: str,
    batch_id: str = None,
    checkpoint_interval: int = CHECKPOINT_INTERVAL,
    dry_run: bool = False,
    limit: int = None
):
    """
    Run Stage 1 classification with checkpointing.

    Args:
        input_file: Path to input Excel file with untagged questions
        batch_id: Unique batch identifier (auto-generated if not provided)
        checkpoint_interval: Save checkpoint every N questions
        dry_run: If True, don't make API calls
        limit: If set, only process this many questions (for testing)
    """
    # Generate batch_id if not provided
    if batch_id is None:
        batch_id = datetime.now().strftime('%Y%m%d_%H%M%S')

    logger.info(f"Starting Stage 1 batch: {batch_id}")
    logger.info(f"Checkpoint interval: every {checkpoint_interval} questions")

    # Load checkpoint if exists
    processed_qgds, results, checkpoint_start_time = load_checkpoint(batch_id)

    # Load input data
    logger.info(f"Loading data from {input_file}...")
    df = pd.read_excel(input_file)
    total_questions = len(df)
    logger.info(f"Loaded {total_questions} questions")

    # Filter out already processed
    remaining_df = df[~df['QUESTIONGROUPDESIGNATION'].isin(processed_qgds)]
    remaining_count = len(remaining_df)

    if remaining_count == 0:
        logger.info("All questions already processed!")
        return get_results_path(batch_id)

    logger.info(f"Remaining to process: {remaining_count} questions")

    # Apply limit if specified
    if limit is not None and limit < remaining_count:
        remaining_df = remaining_df.head(limit)
        remaining_count = limit
        logger.info(f"Limiting to {limit} questions for this run")

    # Initialize client, classifier, and flagger
    client = get_openrouter_client()
    classifier = DiseaseClassifier(client=client)
    flagger = ReviewFlagger()

    # Track timing
    start_time = checkpoint_start_time or datetime.now()
    batch_start = datetime.now()
    questions_this_session = 0

    # Error rate monitoring - stop if too many failures
    error_count = 0
    partial_count = 0
    ERROR_RATE_THRESHOLD = 0.20  # Stop if >20% errors in first 50 questions
    ERROR_CHECK_WINDOW = 50

    # Process each question
    for idx, (row_idx, row) in enumerate(remaining_df.iterrows()):
        qgd = row['QUESTIONGROUPDESIGNATION']
        overall_progress = len(processed_qgds) + 1

        # Calculate ETA
        if questions_this_session > 0:
            elapsed = (datetime.now() - batch_start).total_seconds()
            if elapsed > 0:
                rate = questions_this_session / elapsed  # questions per second
                remaining = remaining_count - (idx + 1)
                eta_seconds = remaining / rate if rate > 0 else 0
                eta = timedelta(seconds=int(eta_seconds))
                eta_str = f" | ETA: {eta}"
            else:
                eta_str = ""
        else:
            eta_str = ""

        logger.info(f"Processing {overall_progress}/{total_questions} (QGD {qgd}){eta_str}")

        # Extract input data
        question_text = row.get('OPTIMIZEDQUESTION') or row.get('RAWQUESTION') or ''
        correct_answer = row.get('OPTIMIZEDCORRECTANSWER') or ''

        # Get activity names
        activity_names = []
        activity_col = row.get('ACTIVITY_NAMES') or row.get('COURSENAME')
        if pd.notna(activity_col):
            activity_names = [a.strip() for a in str(activity_col).split(';') if a.strip()]

        # Get start dates
        start_dates = []
        date_col = row.get('START_DATES') or row.get('STARTDATE')
        if pd.notna(date_col):
            start_dates = [d.strip()[:10] for d in str(date_col).split(';') if d.strip()]

        # Get incorrect answers
        incorrect_answers = []
        for i in range(1, 10):
            col = f'IANSWER{i}'
            if col in row.index and pd.notna(row[col]):
                incorrect_answers.append(str(row[col]))

        try:
            if dry_run:
                # Simulate result
                result = {'is_oncology': True, 'disease_state': 'Test', 'disease_state_secondary': None}
                voting = {'agreement': 'test', 'oncology_agreement': True, 'disease_agreement': True}
                gpt_vote = gemini_vote = {'is_oncology': True, 'disease_state': 'Test'}
                web_search = {}
            else:
                # Call classifier
                result = await classifier.classify(
                    question_text=question_text,
                    correct_answer=correct_answer,
                    activity_names=activity_names,
                    start_dates=start_dates,
                    incorrect_answers=incorrect_answers
                )

                # Result is returned directly (not nested under 'result' key)
                voting = result.get('voting_details', {})

                gpt_vote = voting.get('gpt', {})
                gemini_vote = voting.get('gemini', {})

            # Get review flags
            review_flags = flagger.flag_for_review(
                disease_state=result.get('disease_state'),
                disease_state_secondary=result.get('disease_state_secondary'),
                is_oncology=result.get('is_oncology'),
                agreement=voting.get('agreement', ''),
                activity_names=activity_names,
                question_text=question_text,
                correct_answer=correct_answer,
                voting_details=voting
            )
            review_record = flagger.to_review_record(review_flags)

            # Build result row
            result_row = {
                'QUESTIONGROUPDESIGNATION': qgd,
                'ACTIVITY_NAMES': row.get('ACTIVITY_NAMES') or row.get('COURSENAME'),
                'START_DATES': row.get('START_DATES') or row.get('STARTDATE'),
                'ACTIVITY_COUNT': row.get('ACTIVITY_COUNT', 1),
                'OPTIMIZEDQUESTION': row.get('OPTIMIZEDQUESTION'),
                'RAWQUESTION': row.get('RAWQUESTION'),
                'OPTIMIZEDCORRECTANSWER': row.get('OPTIMIZEDCORRECTANSWER'),

                # Model votes (2-model: GPT + Gemini)
                'GPT_is_oncology': gpt_vote.get('is_oncology'),
                'GPT_disease_state': gpt_vote.get('disease_state'),
                'GEMINI_is_oncology': gemini_vote.get('is_oncology'),
                'GEMINI_disease_state': gemini_vote.get('disease_state'),

                # Final result
                'FINAL_is_oncology': result.get('is_oncology'),
                'FINAL_disease_state': result.get('disease_state'),
                'FINAL_disease_state_secondary': result.get('disease_state_secondary'),
                'AGREEMENT': voting.get('agreement'),
                'ONCOLOGY_AGREEMENT': voting.get('oncology_agreement'),
                'DISEASE_AGREEMENT': voting.get('disease_agreement'),

                # Intelligent flagging
                'NEEDS_REVIEW': review_record.get('needs_review', False),
                'REVIEW_PRIORITY': review_record.get('priority', ''),
                'ERROR_LIKELIHOOD': review_record.get('error_likelihood', 0),
                'ROOT_CAUSES': '; '.join(review_record.get('root_causes', [])),
                'REVIEW_REASON': result.get('review_reason', ''),

                # Human review columns
                'CORRECT_is_oncology': '',
                'CORRECT_disease_state': '',
                'REVIEW_NOTES': '',
            }

            results.append(result_row)
            processed_qgds.add(qgd)
            questions_this_session += 1

            # Track error rates
            if voting.get('agreement') == 'partial_response':
                partial_count += 1

        except Exception as e:
            logger.error(f"Error processing QGD {qgd}: {e}")
            result_row = {
                'QUESTIONGROUPDESIGNATION': qgd,
                'OPTIMIZEDQUESTION': row.get('OPTIMIZEDQUESTION'),
                'ERROR': str(e),
            }
            results.append(result_row)
            processed_qgds.add(qgd)
            questions_this_session += 1
            error_count += 1

        # Check error rate after first window of questions
        if questions_this_session == ERROR_CHECK_WINDOW:
            error_rate = (error_count + partial_count) / ERROR_CHECK_WINDOW
            if error_rate > ERROR_RATE_THRESHOLD:
                logger.error(f"HIGH ERROR RATE DETECTED: {error_rate*100:.1f}% ({error_count} errors, {partial_count} partial) in first {ERROR_CHECK_WINDOW} questions")
                logger.error("STOPPING BATCH TO PREVENT WASTED API CALLS")
                save_checkpoint(batch_id, processed_qgds, results, start_time)
                print(f"\n*** BATCH STOPPED: Error rate {error_rate*100:.1f}% exceeds threshold {ERROR_RATE_THRESHOLD*100:.0f}% ***")
                print(f"Check logs and fix issues before resuming with --resume")
                return get_results_path(batch_id)
            else:
                logger.info(f"Error rate check passed: {error_rate*100:.1f}% ({error_count} errors, {partial_count} partial)")

        # Checkpoint
        if len(processed_qgds) % checkpoint_interval == 0:
            save_checkpoint(batch_id, processed_qgds, results, start_time)

            # Log cost so far
            if not dry_run and hasattr(client, 'get_total_cost'):
                cost = client.get_total_cost()
                logger.info(f"Cost so far: ${cost:.2f}")

    # Final save
    save_checkpoint(batch_id, processed_qgds, results, start_time)

    # Calculate final stats
    elapsed = datetime.now() - start_time

    print("\n" + "=" * 60)
    print("STAGE 1 BATCH COMPLETE")
    print("=" * 60)
    print(f"Batch ID: {batch_id}")
    print(f"Total processed: {len(processed_qgds)}")
    print(f"Total time: {elapsed}")
    print(f"Rate: {len(processed_qgds) / elapsed.total_seconds():.2f} questions/second")

    if not dry_run and hasattr(client, 'get_total_cost'):
        cost = client.get_total_cost()
        print(f"Total cost: ${cost:.2f}")

    results_path = get_results_path(batch_id)
    print(f"\nResults saved to: {results_path}")
    print("=" * 60)

    return results_path


def main():
    parser = argparse.ArgumentParser(description='Run Stage 1 batch classification with checkpointing')
    parser.add_argument(
        '--input', '-i',
        type=str,
        default='data/raw/untagged_questions_20260121_225129.xlsx',
        help='Input Excel file with untagged questions'
    )
    parser.add_argument(
        '--batch-id', '-b',
        type=str,
        default=None,
        help='Batch ID (auto-generated if not provided)'
    )
    parser.add_argument(
        '--resume', '-r',
        action='store_true',
        help='Resume from most recent checkpoint'
    )
    parser.add_argument(
        '--checkpoint-interval', '-c',
        type=int,
        default=CHECKPOINT_INTERVAL,
        help=f'Save checkpoint every N questions (default: {CHECKPOINT_INTERVAL})'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Test run without API calls'
    )
    parser.add_argument(
        '--limit', '-n',
        type=int,
        default=None,
        help='Limit number of questions to process (useful for testing)'
    )

    args = parser.parse_args()

    # Handle resume
    if args.resume:
        batch_id = find_latest_checkpoint()
        if batch_id is None:
            print("No checkpoint found to resume from.")
            return
        print(f"Resuming batch: {batch_id}")
    else:
        batch_id = args.batch_id

    # Check input file exists
    if not Path(args.input).exists():
        print(f"ERROR: Input file not found: {args.input}")
        return

    # CRITICAL: Validate API key is configured and working
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("=" * 60)
        print("ERROR: OPENROUTER_API_KEY environment variable not set!")
        print("=" * 60)
        print("\nPlease set your API key:")
        print("  set OPENROUTER_API_KEY=your_key_here")
        print("\nOr add it to your .env file in the project root.")
        return

    if not args.dry_run:
        print("Validating API key...")
        # Quick validation: try to instantiate the client and make a minimal call
        try:
            from core.taggers.openrouter_client import OpenRouterClient
            client = OpenRouterClient()
            # Test with a minimal prompt to verify API key works
            import httpx
            response = httpx.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "openai/gpt-4o-mini",
                    "messages": [{"role": "user", "content": "test"}],
                    "max_tokens": 1
                },
                timeout=10.0
            )
            if response.status_code == 401:
                print("=" * 60)
                print("ERROR: Invalid API key! Got 401 Unauthorized.")
                print("=" * 60)
                print("\nPlease check your OPENROUTER_API_KEY value.")
                return
            elif response.status_code != 200:
                print(f"WARNING: API test returned status {response.status_code}")
                print("Proceeding anyway, but watch for errors...")
            else:
                print("API key validated successfully!")
        except Exception as e:
            print(f"WARNING: Could not validate API key: {e}")
            print("Proceeding anyway, but watch for errors...")

    # Run
    asyncio.run(run_stage1_batch(
        input_file=args.input,
        batch_id=batch_id,
        checkpoint_interval=args.checkpoint_interval,
        dry_run=args.dry_run,
        limit=args.limit
    ))


if __name__ == "__main__":
    main()
