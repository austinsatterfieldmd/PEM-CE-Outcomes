"""
Stage 1 Evaluation Script - Few-Shot Iteration

Runs Stage 1 (Disease Classification) on a sample of questions and outputs
an Excel file with all input data + model votes for human review.

This is used to build few-shot examples for prompt improvement.

Usage:
    # Dry run (mock API calls) to test pipeline:
    python scripts/run_stage1_eval.py --input data/raw/FullColumnsSample_v2_012026.xlsx --n 5 --dry-run

    # Live run with real API calls:
    python scripts/run_stage1_eval.py --input data/raw/FullColumnsSample_v2_012026.xlsx --n 100

Output:
    data/eval/stage1_eval_YYYYMMDD_HHMMSS.xlsx
"""

import asyncio
import argparse
import json
import logging
import os
import random
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

from src.core.taggers.review_flagger import ReviewFlagger

# Mock disease states for dry-run testing
MOCK_DISEASE_STATES = [
    "Breast cancer", "NSCLC", "SCLC", "CRC", "Multiple Myeloma",
    "Prostate cancer", "Melanoma", "AML", "CLL", "DLBCL",
    "Ovarian cancer", "RCC", "HCC", "Pancreatic cancer", None
]


def generate_mock_classification(question_text: str, correct_answer: str) -> dict:
    """
    Generate mock classification results for dry-run testing.
    Simulates realistic voting patterns including unanimous, majority, and conflict.
    """
    # Determine mock oncology status based on keywords
    text_lower = (str(question_text or "") + " " + str(correct_answer or "")).lower()
    oncology_keywords = ["cancer", "tumor", "carcinoma", "lymphoma", "leukemia", "myeloma", "melanoma", "nsclc", "sclc"]
    is_oncology = any(kw in text_lower for kw in oncology_keywords)

    # Generate random agreement pattern
    pattern = random.choices(
        ["unanimous", "majority", "conflict"],
        weights=[0.6, 0.3, 0.1]  # 60% unanimous, 30% majority, 10% conflict
    )[0]

    if pattern == "unanimous":
        disease = random.choice(MOCK_DISEASE_STATES[:10]) if is_oncology else None
        gpt_disease = claude_disease = gemini_disease = disease
        gpt_onc = claude_onc = gemini_onc = is_oncology
        agreement = "unanimous"
    elif pattern == "majority":
        disease = random.choice(MOCK_DISEASE_STATES[:10]) if is_oncology else None
        dissenter = random.choice(["gpt", "claude", "gemini"])
        alt_disease = random.choice([d for d in MOCK_DISEASE_STATES[:10] if d != disease])

        gpt_disease = alt_disease if dissenter == "gpt" else disease
        claude_disease = alt_disease if dissenter == "claude" else disease
        gemini_disease = alt_disease if dissenter == "gemini" else disease
        gpt_onc = claude_onc = gemini_onc = is_oncology
        agreement = "majority"
    else:  # conflict
        diseases = random.sample(MOCK_DISEASE_STATES[:10], 3)
        gpt_disease, claude_disease, gemini_disease = diseases
        gpt_onc = claude_onc = gemini_onc = is_oncology
        agreement = "conflict"
        disease = None  # No consensus

    # Determine review status
    needs_review = agreement != "unanimous"
    review_reason = None
    if agreement == "majority":
        review_reason = "disease_majority"
    elif agreement == "conflict":
        review_reason = "disease_conflict"

    return {
        "is_oncology": is_oncology if agreement != "conflict" else None,
        "disease_state": disease,
        "needs_review": needs_review,
        "review_reason": review_reason,
        "voting_details": {
            "gpt": {"is_oncology": gpt_onc, "disease_state": gpt_disease},
            "claude": {"is_oncology": claude_onc, "disease_state": claude_disease},
            "gemini": {"is_oncology": gemini_onc, "disease_state": gemini_disease},
            "agreement": agreement,
            "oncology_agreement": "unanimous",
            "disease_agreement": agreement
        }
    }

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run_stage1_evaluation(
    input_file: str,
    n_questions: int = 100,
    output_dir: str = "data/eval",
    random_seed: int = 42,
    dry_run: bool = False
):
    """
    Run Stage 1 classification on a sample of questions.

    Args:
        input_file: Path to input Excel file with full question data
        n_questions: Number of questions to evaluate
        output_dir: Directory for output files
        random_seed: Random seed for reproducible sampling
        dry_run: If True, use mock responses instead of real API calls
    """
    random.seed(random_seed)

    # Only import real classifier if not dry run
    classifier = None
    client = None
    if not dry_run:
        from src.core.taggers.openrouter_client import get_openrouter_client
        from src.core.taggers.disease_classifier import DiseaseClassifier
        client = get_openrouter_client()
        classifier = DiseaseClassifier(client=client, use_voting=True)
    else:
        logger.info("DRY RUN MODE: Using mock API responses")

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Load data
    logger.info(f"Loading data from {input_file}...")
    df = pd.read_excel(input_file)
    logger.info(f"Loaded {len(df)} rows with {len(df.columns)} columns")

    # Deduplicate by QUESTIONGROUPDESIGNATION to avoid wasting API calls on identical questions
    # QUESTIONGROUPDESIGNATION identifies unique question content across different activities
    if 'QUESTIONGROUPDESIGNATION' in df.columns:
        original_count = len(df)
        # Keep first occurrence of each unique question (by QUESTIONGROUPDESIGNATION)
        df_unique = df.drop_duplicates(subset=['QUESTIONGROUPDESIGNATION'], keep='first')
        dedup_count = len(df_unique)
        if original_count != dedup_count:
            logger.info(f"Deduplicated: {original_count} → {dedup_count} unique questions "
                       f"(removed {original_count - dedup_count} duplicates by QUESTIONGROUPDESIGNATION)")
    else:
        df_unique = df
        logger.warning("QUESTIONGROUPDESIGNATION column not found - cannot deduplicate")

    # Sample questions (use canonical/unique questions if available)
    # Prefer questions with ONCCLASS not set (need classification)
    if 'ONCCLASS' in df_unique.columns:
        unclassified = df_unique[df_unique['ONCCLASS'].isna()]
        if len(unclassified) >= n_questions:
            sample_df = unclassified.sample(n=n_questions, random_state=random_seed)
        else:
            sample_df = df_unique.sample(n=min(n_questions, len(df_unique)), random_state=random_seed)
    else:
        sample_df = df_unique.sample(n=min(n_questions, len(df_unique)), random_state=random_seed)

    logger.info(f"Sampled {len(sample_df)} unique questions for evaluation")

    # Prepare results list
    results = []

    # Initialize review flagger
    flagger = ReviewFlagger()

    # Process each question
    for idx, (row_idx, row) in enumerate(sample_df.iterrows()):
        logger.info(f"Processing question {idx + 1}/{len(sample_df)}...")

        # Extract input data
        question_text = row.get('OPTIMIZEDQUESTION') or row.get('RAWQUESTION') or row.get('QUESTION', '')
        correct_answer = row.get('OPTIMIZEDCORRECTANSWER') or row.get('CANSWER1', '')

        # Get activity names (may be collated with semicolons or single)
        activity_names = []
        activity_col = row.get('ACTIVITY_NAMES') or row.get('COURSENAME')
        if pd.notna(activity_col):
            # Split by semicolon if collated, otherwise use as single value
            activity_names = [a.strip() for a in str(activity_col).split(';') if a.strip()]

        # Get start dates (may be collated with semicolons or single)
        start_dates = []
        date_col = row.get('START_DATES') or row.get('STARTDATE')
        if pd.notna(date_col):
            # Split by semicolon if collated, otherwise use as single value
            start_dates = [d.strip()[:10] for d in str(date_col).split(';') if d.strip()]

        # Get incorrect answers
        incorrect_answers = []
        for i in range(1, 10):
            col = f'IANSWER{i}'
            if col in row and pd.notna(row[col]):
                incorrect_answers.append(str(row[col]))

        try:
            # Run classification (mock or real)
            if dry_run:
                result = generate_mock_classification(question_text, correct_answer)
            else:
                result = await classifier.classify(
                    question_text=question_text,
                    correct_answer=correct_answer,
                    activity_names=activity_names if activity_names else None,
                    start_dates=start_dates if start_dates else None,
                    incorrect_answers=incorrect_answers if incorrect_answers else None
                )

            # Extract voting details
            voting = result.get('voting_details', {})
            gpt_vote = voting.get('gpt', {})
            claude_vote = voting.get('claude', {})
            gemini_vote = voting.get('gemini', {})
            web_search = voting.get('web_search', {})

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

            # Build result row with all input data + model outputs
            result_row = {
                # === IDENTIFIERS ===
                'row_index': row_idx,
                'ANSWERSETMERGED': row.get('ANSWERSETMERGED'),
                'QUESTIONID': row.get('QUESTIONID'),

                # === INPUT: Question Context ===
                'ACTIVITY_NAMES': row.get('ACTIVITY_NAMES') or row.get('COURSENAME'),
                'START_DATES': row.get('START_DATES') or row.get('STARTDATE'),
                'ACTIVITY_COUNT': row.get('ACTIVITY_COUNT', 1),
                'QUESTIONGROUPDESIGNATION': row.get('QUESTIONGROUPDESIGNATION'),
                'SCORINGGROUP': row.get('SCORINGGROUP'),
                'SOURCETYPE': row.get('SOURCETYPE'),

                # === INPUT: Question Text ===
                'OPTIMIZEDQUESTION': row.get('OPTIMIZEDQUESTION'),
                'RAWQUESTION': row.get('RAWQUESTION'),

                # === INPUT: Answers ===
                'OPTIMIZEDCORRECTANSWER': row.get('OPTIMIZEDCORRECTANSWER'),
                'IANSWER1': row.get('IANSWER1'),
                'IANSWER2': row.get('IANSWER2'),
                'IANSWER3': row.get('IANSWER3'),
                'IANSWER4': row.get('IANSWER4'),
                'IANSWER5': row.get('IANSWER5'),
                'IANSWER6': row.get('IANSWER6'),
                'IANSWER7': row.get('IANSWER7'),
                'IANSWER8': row.get('IANSWER8'),
                'IANSWER9': row.get('IANSWER9'),

                # === EXISTING TAGS (if any) ===
                'EXISTING_ONCCLASS': row.get('ONCCLASS'),
                'EXISTING_DISEASE_STATE': row.get('DISEASE_STATE'),

                # === MODEL VOTES ===
                'GPT_is_oncology': gpt_vote.get('is_oncology'),
                'GPT_disease_state': gpt_vote.get('disease_state'),
                'CLAUDE_is_oncology': claude_vote.get('is_oncology'),
                'CLAUDE_disease_state': claude_vote.get('disease_state'),
                'GEMINI_is_oncology': gemini_vote.get('is_oncology'),
                'GEMINI_disease_state': gemini_vote.get('disease_state'),

                # === WEB SEARCH (if used) ===
                'WEB_SEARCH_disease_state': web_search.get('disease_state'),
                'WEB_SEARCH_trial_name': web_search.get('trial_name'),

                # === AGGREGATED RESULT ===
                'FINAL_is_oncology': result.get('is_oncology'),
                'FINAL_disease_state': result.get('disease_state'),
                'FINAL_disease_state_secondary': result.get('disease_state_secondary'),
                'AGREEMENT': voting.get('agreement'),
                'ONCOLOGY_AGREEMENT': voting.get('oncology_agreement'),
                'DISEASE_AGREEMENT': voting.get('disease_agreement'),
                'MODELS_RESPONDED': voting.get('models_responded', 3),
                'MODELS_WITH_ERRORS': voting.get('models_with_errors', 0),
                'ERROR_MODELS': ','.join(voting.get('error_models', [])),
                'NEEDS_REVIEW': result.get('needs_review'),
                'REVIEW_REASON': result.get('review_reason'),

                # === INTELLIGENT FLAGGING ===
                'FLAG_NEEDS_REVIEW': review_record.get('needs_review', False),
                'FLAG_PRIORITY': review_record.get('priority', ''),
                'FLAG_ERROR_LIKELIHOOD': review_record.get('error_likelihood', 0),
                'FLAG_ROOT_CAUSES': '; '.join(review_record.get('root_causes', [])),
                'FLAG_COUNT': review_record.get('flag_count', 0),

                # === HUMAN REVIEW COLUMNS (to be filled) ===
                'CORRECT_is_oncology': '',  # Human fills this
                'CORRECT_disease_state': '',  # Human fills this
                'REVIEW_NOTES': '',  # Human fills this

                # === RAW JSON (for debugging) ===
                'RAW_VOTING_DETAILS': json.dumps(voting, default=str),
            }

            results.append(result_row)

        except Exception as e:
            logger.error(f"Error processing question {idx + 1}: {e}")
            # Add error row
            result_row = {
                'row_index': row_idx,
                'ANSWERSETMERGED': row.get('ANSWERSETMERGED'),
                'QUESTIONID': row.get('QUESTIONID'),
                'OPTIMIZEDQUESTION': row.get('OPTIMIZEDQUESTION'),
                'ERROR': str(e),
            }
            results.append(result_row)

    # Create output DataFrame
    results_df = pd.DataFrame(results)

    # Generate output filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = output_path / f"stage1_eval_{timestamp}.xlsx"

    # Save to Excel with formatting
    logger.info(f"Saving results to {output_file}...")

    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        results_df.to_excel(writer, sheet_name='Stage1_Eval', index=False)

        # Get workbook and worksheet for formatting
        workbook = writer.book
        worksheet = writer.sheets['Stage1_Eval']

        # Auto-adjust column widths (approximate)
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)  # Cap at 50
            worksheet.column_dimensions[column_letter].width = adjusted_width

    logger.info(f"Saved {len(results_df)} results to {output_file}")

    # Print summary statistics
    print("\n" + "=" * 60)
    print("STAGE 1 EVALUATION SUMMARY")
    print("=" * 60)
    print(f"Total questions processed: {len(results_df)}")

    if 'AGREEMENT' in results_df.columns:
        agreement_counts = results_df['AGREEMENT'].value_counts()
        print(f"\nAgreement levels:")
        for level, count in agreement_counts.items():
            print(f"  {level}: {count} ({count/len(results_df)*100:.1f}%)")

    if 'FINAL_is_oncology' in results_df.columns:
        oncology_counts = results_df['FINAL_is_oncology'].value_counts()
        print(f"\nOncology classification:")
        for val, count in oncology_counts.items():
            print(f"  {val}: {count} ({count/len(results_df)*100:.1f}%)")

    if 'NEEDS_REVIEW' in results_df.columns:
        review_count = results_df['NEEDS_REVIEW'].sum()
        print(f"\nNeeds review: {review_count} ({review_count/len(results_df)*100:.1f}%)")

    print(f"\nOutput file: {output_file}")
    print("=" * 60)

    # Return API cost estimate
    if dry_run:
        print(f"\nDRY RUN: No API costs incurred")
    else:
        cost = client.get_total_cost() if client and hasattr(client, 'get_total_cost') else 0
        print(f"\nEstimated API cost: ${cost:.4f}")

    return output_file


def main():
    parser = argparse.ArgumentParser(description='Run Stage 1 evaluation for few-shot iteration')
    parser.add_argument(
        '--input', '-i',
        type=str,
        default='data/raw/questions_deduplicated_collated_20260121_221852.xlsx',
        help='Input Excel file path (use deduplicated file with collated activity names)'
    )
    parser.add_argument(
        '--n', '-n',
        type=int,
        default=100,
        help='Number of questions to evaluate'
    )
    parser.add_argument(
        '--output-dir', '-o',
        type=str,
        default='data/eval',
        help='Output directory for results'
    )
    parser.add_argument(
        '--seed', '-s',
        type=int,
        default=42,
        help='Random seed for reproducible sampling'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Use mock API responses instead of real calls (for testing)'
    )

    args = parser.parse_args()

    # Check for API key (not needed for dry-run)
    if not args.dry_run and not os.getenv('OPENROUTER_API_KEY'):
        print("ERROR: OPENROUTER_API_KEY not found in environment variables")
        print("Please add it to your .env file")
        sys.exit(1)

    # Run evaluation
    output_file = asyncio.run(run_stage1_evaluation(
        input_file=args.input,
        n_questions=args.n,
        output_dir=args.output_dir,
        random_seed=args.seed,
        dry_run=args.dry_run
    ))

    print(f"\nDone! Review the output file and fill in the CORRECT_* columns.")
    print(f"Then run the analysis script to generate few-shot examples.")


if __name__ == "__main__":
    main()
