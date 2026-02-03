"""
Run Stage 2 tagging for hematologic malignancies in batches with checkpoint support.

Tags questions from 5 disease states: CLL, DLBCL, FL, MCL, ALL
Uses disease-specific prompts with BTKi classification, prognostic scores, etc.

WORKFLOW:
    1. Run batch of 50 random questions from all 5 diseases
    2. Review accuracy in dashboard
    3. Run next batch (script auto-excludes already-tagged questions)

Usage:
    # First batch: 50 random questions from heme malignancies
    python scripts/run_heme_batch.py --batch-size 50

    # Smaller test batch
    python scripts/run_heme_batch.py --batch-size 10

    # Dry run (test with 5 questions, no API calls)
    python scripts/run_heme_batch.py --batch-size 5 --dry-run

    # Filter to specific disease(s)
    python scripts/run_heme_batch.py --diseases "CLL" "DLBCL" --batch-size 25

    # Continue from checkpoint (automatic)
    python scripts/run_heme_batch.py --batch-size 50

Cost estimate: ~$0.15 per question (Stage 1 ~$0.01 + Stage 2 ~$0.14)
50 questions = ~$7.50
"""

import argparse
import asyncio
import pandas as pd
import random
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
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

# Configure logging
LOG_DIR = PROJECT_ROOT / 'data' / 'checkpoints'
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / 'heme_batch.log')
    ]
)
logger = logging.getLogger(__name__)

# Target disease states for this batch script (using abbreviations as in Stage 1 data)
HEME_DISEASES = [
    "CLL",
    "DLBCL",
    "FL",
    "MCL",
    "ALL"
]

# Full names for reference/display
DISEASE_FULL_NAMES = {
    "CLL": "Chronic lymphocytic leukemia",
    "DLBCL": "Diffuse large B-cell lymphoma",
    "FL": "Follicular lymphoma",
    "MCL": "Mantle cell lymphoma",
    "ALL": "Acute lymphoblastic leukemia",
}

# Aliases for user input normalization
DISEASE_ALIASES = {
    "Chronic lymphocytic leukemia": "CLL",
    "Diffuse large B-cell lymphoma": "DLBCL",
    "Follicular lymphoma": "FL",
    "Mantle cell lymphoma": "MCL",
    "Acute lymphoblastic leukemia": "ALL",
    "B-ALL": "ALL",
    "T-ALL": "ALL",
}


def load_questions_from_excel(
    file_path: str,
    disease_filter: Optional[List[str]] = None
) -> List[Dict]:
    """
    Load questions from stage2_ready Excel file.

    Args:
        file_path: Path to Excel file
        disease_filter: Filter by STAGE1_disease_state (list of diseases)

    Returns:
        List of question dicts
    """
    logger.info(f"Loading questions from {file_path}")
    df = pd.read_excel(file_path)
    logger.info(f"Total rows in file: {len(df)}")

    # Filter by disease if specified
    if disease_filter:
        # Normalize filter to abbreviations (as used in Stage 1 data)
        normalized_filter = []
        for d in disease_filter:
            if d in DISEASE_ALIASES:
                # User passed full name, convert to abbreviation
                normalized_filter.append(DISEASE_ALIASES[d])
            else:
                # Already an abbreviation or as-is
                normalized_filter.append(d)

        df = df[df['STAGE1_disease_state'].isin(normalized_filter)]
        logger.info(f"Filtered to {len(df)} questions from {normalized_filter}")

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
            'id': int(idx),
            'source_id': str(row.get('QUESTIONGROUPDESIGNATION', '')),
            'question_stem': str(row['OPTIMIZEDQUESTION']),
            'correct_answer': str(row['OPTIMIZEDCORRECTANSWER']) if pd.notna(row.get('OPTIMIZEDCORRECTANSWER')) else None,
            'incorrect_answers': incorrect,
            'disease_state': str(row['STAGE1_disease_state']),
            'activities': str(row.get('ACTIVITY_NAMES', '')) if pd.notna(row.get('ACTIVITY_NAMES')) else '',
            'startdate': str(row.get('STARTDATE', '')) if pd.notna(row.get('STARTDATE')) else '',
        })

    return questions


def load_checkpoint(checkpoint_file: Path) -> Set[str]:
    """Load set of already-processed source_ids from checkpoint."""
    if not checkpoint_file.exists():
        return set()

    with open(checkpoint_file, encoding='utf-8') as f:
        checkpoint = json.load(f)
        return set(checkpoint.get('processed_source_ids', []))


def save_checkpoint(
    checkpoint_file: Path,
    processed_source_ids: Set[str],
    results: List[Dict]
):
    """Save checkpoint with processed IDs and results."""
    checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
    with open(checkpoint_file, 'w', encoding='utf-8') as f:
        json.dump({
            'processed_source_ids': list(processed_source_ids),
            'results': results,
            'timestamp': datetime.now().isoformat(),
            'diseases': HEME_DISEASES
        }, f, indent=2, ensure_ascii=False)


def aggregated_vote_to_dict(result: AggregatedVote, question: Dict) -> Dict[str, Any]:
    """Convert AggregatedVote to serializable dict for JSON output."""
    return {
        # Question data
        'question_id': result.question_id,
        'source_id': question['source_id'],
        'question_stem': question['question_stem'],
        'correct_answer': question['correct_answer'],
        'incorrect_answers': question['incorrect_answers'],
        'disease_state': question['disease_state'],
        'activities': question['activities'],
        'startdate': question.get('startdate', ''),

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


def sample_questions(
    questions: List[Dict],
    processed_ids: Set[str],
    batch_size: int,
    stratified: bool = True
) -> List[Dict]:
    """
    Sample untagged questions, optionally stratified by disease.

    Args:
        questions: All available questions
        processed_ids: Set of already-processed source_ids
        batch_size: Number of questions to sample
        stratified: If True, sample evenly from each disease

    Returns:
        List of sampled questions
    """
    # Filter to unprocessed
    unprocessed = [q for q in questions if q['source_id'] not in processed_ids]
    logger.info(f"Unprocessed questions available: {len(unprocessed)}")

    if len(unprocessed) == 0:
        logger.info("All questions have been processed!")
        return []

    if len(unprocessed) <= batch_size:
        logger.info(f"Returning all {len(unprocessed)} remaining questions")
        return unprocessed

    if stratified:
        # Group by disease
        by_disease = {}
        for q in unprocessed:
            disease = q['disease_state']
            if disease not in by_disease:
                by_disease[disease] = []
            by_disease[disease].append(q)

        logger.info("Questions by disease:")
        for disease, qs in by_disease.items():
            logger.info(f"  {disease}: {len(qs)}")

        # Sample evenly from each disease
        per_disease = batch_size // len(by_disease)
        remainder = batch_size % len(by_disease)

        sampled = []
        diseases = list(by_disease.keys())
        random.shuffle(diseases)  # Randomize which diseases get remainder

        for i, disease in enumerate(diseases):
            n = per_disease + (1 if i < remainder else 0)
            available = by_disease[disease]
            sample_n = min(n, len(available))
            sampled.extend(random.sample(available, sample_n))

        # If we couldn't get enough from stratified, fill from remaining
        if len(sampled) < batch_size:
            remaining = [q for q in unprocessed if q not in sampled]
            needed = batch_size - len(sampled)
            sampled.extend(random.sample(remaining, min(needed, len(remaining))))

        random.shuffle(sampled)  # Shuffle final order
        return sampled

    else:
        return random.sample(unprocessed, batch_size)


async def process_batch(
    questions: List[Dict],
    checkpoint_file: Path,
    processed_ids: Set[str],
    existing_results: List[Dict],
    checkpoint_interval: int = 5,
    dry_run: bool = False,
    use_web_search: bool = False
) -> List[Dict]:
    """
    Process questions with 3-model voting and checkpointing.

    Args:
        questions: List of question dicts to process
        checkpoint_file: Path to checkpoint file
        processed_ids: Set of already-processed source_ids (will be updated)
        existing_results: Existing results from checkpoint (will be extended)
        checkpoint_interval: Save checkpoint every N questions
        dry_run: If True, skip actual API calls
        use_web_search: If True, enable web search on disagreements

    Returns:
        List of all result dicts (existing + new)
    """
    if dry_run:
        logger.info("DRY RUN MODE - No API calls will be made")
        for q in questions:
            logger.info(f"  Would tag: {q['source_id'][:30]}... ({q['disease_state']})")
        return existing_results

    tagger = MultiModelTagger(prompt_version="v2.0", use_web_search=use_web_search)
    results = existing_results.copy()

    logger.info(f"Processing {len(questions)} questions...")
    batch_start = datetime.now()

    for i, question in enumerate(questions):
        try:
            logger.info(
                f"[{i+1}/{len(questions)}] Tagging {question['source_id'][:30]}... "
                f"({question['disease_state']})"
            )

            # Note: Stage 1 (disease classification) runs internally even though we already have it
            # This is by design - Stage 1 is cheap (~$0.01) and validates our classification
            result = await tagger.tag_question(
                question_id=question['id'],
                question_text=question['question_stem'],
                correct_answer=question.get('correct_answer'),
                incorrect_answers=question.get('incorrect_answers')
            )

            result_dict = aggregated_vote_to_dict(result, question)
            results.append(result_dict)
            processed_ids.add(question['source_id'])

            # Log agreement level
            logger.info(
                f"  -> {result.overall_agreement.value} agreement, "
                f"confidence: {result.overall_confidence:.2f}, "
                f"needs_review: {result.needs_review}"
            )

        except Exception as e:
            logger.error(f"Error processing question {question['source_id']}: {e}")
            # Save error result
            results.append({
                'question_id': question['id'],
                'source_id': question['source_id'],
                'disease_state': question['disease_state'],
                'error': str(e),
                'tagged_at': datetime.now().isoformat()
            })
            processed_ids.add(question['source_id'])

        # Save checkpoint periodically
        if (i + 1) % checkpoint_interval == 0:
            save_checkpoint(checkpoint_file, processed_ids, results)
            elapsed = (datetime.now() - batch_start).total_seconds()
            avg_time = elapsed / (i + 1)
            remaining = len(questions) - (i + 1)
            eta_seconds = remaining * avg_time
            logger.info(
                f"Checkpoint saved. Progress: {i+1}/{len(questions)} "
                f"(ETA: {eta_seconds/60:.1f} min)"
            )

    # Final checkpoint
    save_checkpoint(checkpoint_file, processed_ids, results)

    # Get cost estimate
    try:
        cost = tagger.client.get_total_cost()
        logger.info(f"Batch API cost: ${cost:.2f}")
    except Exception:
        pass

    batch_duration = (datetime.now() - batch_start).total_seconds()
    logger.info(f"Batch complete in {batch_duration/60:.1f} minutes")

    return results


def print_summary(results: List[Dict]):
    """Print summary of tagging results."""
    if not results:
        logger.info("No results to summarize")
        return

    # Exclude error results
    valid_results = [r for r in results if 'error' not in r]
    error_count = len(results) - len(valid_results)

    if not valid_results:
        logger.info(f"All {len(results)} results had errors")
        return

    # Agreement distribution
    agreement_counts = {}
    for r in valid_results:
        level = r.get('agreement', 'unknown')
        agreement_counts[level] = agreement_counts.get(level, 0) + 1

    # By disease
    disease_counts = {}
    for r in valid_results:
        disease = r.get('disease_state', 'unknown')
        disease_counts[disease] = disease_counts.get(disease, 0) + 1

    # Review needed
    needs_review = sum(1 for r in valid_results if r.get('needs_review', False))

    logger.info("\n" + "=" * 50)
    logger.info("TAGGING SUMMARY")
    logger.info("=" * 50)
    logger.info(f"Total tagged: {len(valid_results)} ({error_count} errors)")
    logger.info(f"Needs review: {needs_review} ({100*needs_review/len(valid_results):.1f}%)")
    logger.info("\nBy Agreement Level:")
    for level, count in sorted(agreement_counts.items()):
        logger.info(f"  {level}: {count} ({100*count/len(valid_results):.1f}%)")
    logger.info("\nBy Disease:")
    for disease, count in sorted(disease_counts.items()):
        logger.info(f"  {disease}: {count}")
    logger.info("=" * 50)


def main():
    parser = argparse.ArgumentParser(
        description="Run Stage 2 batch tagging for hematologic malignancies"
    )
    parser.add_argument(
        "--input",
        default="data/checkpoints/stage2_ready_fixed_lookup_20260129_214737.xlsx",
        help="Input Excel file with Stage 1 classified questions"
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output JSON file (default: data/checkpoints/heme_tagged_{timestamp}.json)"
    )
    parser.add_argument(
        "--checkpoint",
        default="data/checkpoints/heme_batch_checkpoint.json",
        help="Checkpoint file for resume support"
    )
    parser.add_argument(
        "--diseases",
        nargs="+",
        default=None,
        help="Filter to specific diseases (default: all 5 heme malignancies)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Number of questions to tag in this batch"
    )
    parser.add_argument(
        "--checkpoint-interval",
        type=int,
        default=5,
        help="Save checkpoint every N questions"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip API calls, just test sampling"
    )
    parser.add_argument(
        "--web-search",
        action="store_true",
        help="Enable web search on disagreements"
    )
    parser.add_argument(
        "--no-stratify",
        action="store_true",
        help="Disable stratified sampling (random instead of even per disease)"
    )

    args = parser.parse_args()

    # Resolve paths
    input_file = PROJECT_ROOT / args.input
    checkpoint_file = PROJECT_ROOT / args.checkpoint

    if not input_file.exists():
        logger.error(f"Input file not found: {input_file}")
        sys.exit(1)

    # Load questions
    disease_filter = args.diseases if args.diseases else HEME_DISEASES
    questions = load_questions_from_excel(str(input_file), disease_filter)

    if not questions:
        logger.error("No questions found for specified diseases")
        sys.exit(1)

    # Load checkpoint
    processed_ids = load_checkpoint(checkpoint_file)
    logger.info(f"Already processed: {len(processed_ids)} questions")

    # Load existing results if checkpoint exists
    existing_results = []
    if checkpoint_file.exists():
        with open(checkpoint_file, encoding='utf-8') as f:
            checkpoint = json.load(f)
            existing_results = checkpoint.get('results', [])

    # Sample questions for this batch
    sampled = sample_questions(
        questions,
        processed_ids,
        args.batch_size,
        stratified=not args.no_stratify
    )

    if not sampled:
        logger.info("No questions to process. All done!")
        print_summary(existing_results)
        return

    logger.info(f"Sampled {len(sampled)} questions for this batch:")
    disease_sample_counts = {}
    for q in sampled:
        d = q['disease_state']
        disease_sample_counts[d] = disease_sample_counts.get(d, 0) + 1
    for disease, count in sorted(disease_sample_counts.items()):
        logger.info(f"  {disease}: {count}")

    # Estimate cost (Stage 1 + Stage 2)
    est_cost = len(sampled) * 0.15
    logger.info(f"Estimated cost: ${est_cost:.2f}")

    if args.dry_run:
        logger.info("DRY RUN - would process above questions")
        return

    # Confirm before proceeding
    if not args.dry_run:
        response = input(f"\nProceed with tagging {len(sampled)} questions (~${est_cost:.2f})? [y/N]: ")
        if response.lower() != 'y':
            logger.info("Aborted by user")
            return

    # Process batch
    results = asyncio.run(process_batch(
        questions=sampled,
        checkpoint_file=checkpoint_file,
        processed_ids=processed_ids,
        existing_results=existing_results,
        checkpoint_interval=args.checkpoint_interval,
        dry_run=args.dry_run,
        use_web_search=args.web_search
    ))

    # Save final output
    if args.output:
        output_file = PROJECT_ROOT / args.output
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = PROJECT_ROOT / 'data' / 'checkpoints' / f'heme_tagged_{timestamp}.json'

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'results': results,
            'diseases': disease_filter,
            'timestamp': datetime.now().isoformat()
        }, f, indent=2, ensure_ascii=False)

    logger.info(f"Results saved to: {output_file}")

    # Print summary
    print_summary(results)


if __name__ == "__main__":
    main()
