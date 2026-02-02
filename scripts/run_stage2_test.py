"""
Run Stage 2 tagging test on a sample of questions.

This script tests the 66-field tagging system with disease-specific prompts.
It bypasses Stage 1 (disease classification) since we already know the disease state.

Usage:
    python scripts/run_stage2_test.py --disease "Breast cancer" --limit 25
    python scripts/run_stage2_test.py --disease NSCLC --limit 25
    python scripts/run_stage2_test.py --disease CRC --limit 25
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv(Path(__file__).parent.parent / ".env")

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.taggers.openrouter_client import get_openrouter_client
from core.taggers.vote_aggregator import VoteAggregator, AgreementLevel
from core.services.prompt_manager import get_prompt_manager

# Get TAG_FIELDS from the VoteAggregator class
TAG_FIELDS = VoteAggregator.TAG_FIELDS

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Output directory
OUTPUT_DIR = Path("data/eval")


def parse_response(content: str, model_name: str = "unknown") -> dict:
    """
    Parse LLM response to extract JSON tags.

    Uses multiple strategies to handle:
    - JSON in markdown code blocks
    - Truncated responses (repair incomplete JSON)
    - Explanatory text around JSON
    """
    import re

    if not content:
        logger.warning(f"{model_name}: Empty response")
        return {}

    content = content.strip()

    # Strategy 1: Extract JSON from markdown code block anywhere in response
    json_block_pattern = r'```(?:json)?\s*(\{[\s\S]*?\})\s*```'
    json_match = re.search(json_block_pattern, content)

    if json_match:
        json_str = json_match.group(1).strip()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # Try to repair truncated JSON
            repaired = repair_truncated_json(json_str)
            if repaired:
                try:
                    return json.loads(repaired)
                except json.JSONDecodeError:
                    pass

    # Strategy 2: Find raw JSON object starting with { and containing "topic"
    # (topic is required, so it should be in any valid response)
    json_object_pattern = r'\{[^{}]*"topic"[\s\S]*'
    json_obj_match = re.search(json_object_pattern, content)

    if json_obj_match:
        json_str = json_obj_match.group(0)
        # Try to find the end of the JSON object
        brace_count = 0
        end_pos = 0
        for i, char in enumerate(json_str):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_pos = i + 1
                    break

        if end_pos > 0:
            json_str = json_str[:end_pos]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                repaired = repair_truncated_json(json_str)
                if repaired:
                    try:
                        return json.loads(repaired)
                    except json.JSONDecodeError:
                        pass
        else:
            # No closing brace found - truncated response
            repaired = repair_truncated_json(json_str)
            if repaired:
                try:
                    return json.loads(repaired)
                except json.JSONDecodeError:
                    pass

    # Strategy 3: Strip markdown and try direct parse
    if content.startswith("```json"):
        content = content[7:]
    elif content.startswith("```"):
        content = content[3:]

    if content.endswith("```"):
        content = content[:-3]

    content = content.strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Final attempt: repair truncated JSON
        repaired = repair_truncated_json(content)
        if repaired:
            try:
                result = json.loads(repaired)
                logger.info(f"{model_name}: Repaired truncated JSON successfully")
                return result
            except json.JSONDecodeError as e:
                logger.warning(f"{model_name}: Failed to parse even after repair: {e}")
        else:
            logger.warning(f"{model_name}: Failed to parse JSON, no repair possible")

        return {}


def repair_truncated_json(json_str: str) -> str:
    """
    Attempt to repair a truncated JSON object.

    Common issues:
    - Missing closing braces
    - Truncated string values
    - Missing null values
    """
    if not json_str:
        return None

    json_str = json_str.strip()

    # If it doesn't start with {, not repairable
    if not json_str.startswith('{'):
        return None

    # Count braces
    open_braces = json_str.count('{')
    close_braces = json_str.count('}')

    # If already balanced, return as-is
    if open_braces == close_braces:
        return json_str

    # Check for truncated string (unmatched quote at end)
    # Find the last complete key-value pair
    lines = json_str.split('\n')
    repaired_lines = []

    for line in lines:
        stripped = line.strip()

        # Skip empty lines
        if not stripped:
            continue

        # Check if line ends with incomplete value
        if stripped.endswith(':'):
            # Missing value, add null
            repaired_lines.append(line + ' null,')
        elif '"' in stripped and stripped.count('"') % 2 != 0:
            # Unmatched quote - truncated string
            # Try to close the string
            if stripped.endswith(','):
                stripped = stripped[:-1]
            repaired_lines.append(stripped + '",')
        else:
            repaired_lines.append(line)

    repaired = '\n'.join(repaired_lines)

    # Remove trailing comma before closing brace
    repaired = repaired.rstrip()
    if repaired.endswith(','):
        repaired = repaired[:-1]

    # Add missing closing braces
    missing_braces = open_braces - repaired.count('}')
    if missing_braces > 0:
        repaired += '\n' + '}' * missing_braces

    return repaired


async def run_stage2_test(
    disease: str,
    limit: int = 25,
    input_file: str = "data/checkpoints/stage2_ready_final.xlsx",
    dry_run: bool = False
):
    """
    Run Stage 2 tagging test on disease-specific questions.

    This directly calls 3 models with the disease-specific prompt,
    bypassing Stage 1 since we already know the disease state.

    Args:
        disease: Disease state to filter (e.g., "Breast cancer")
        limit: Number of questions to tag
        input_file: Path to Stage 2 ready file
        dry_run: If True, skip API calls
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Load data
    logger.info(f"Loading data from {input_file}...")
    df = pd.read_excel(input_file)

    # Filter by disease
    disease_df = df[df['FINAL_disease_state'] == disease]
    logger.info(f"Found {len(disease_df)} {disease} questions")

    if len(disease_df) == 0:
        print(f"No questions found for disease: {disease}")
        print("Available diseases:")
        print(df['FINAL_disease_state'].value_counts().head(15))
        return

    # Take sample
    sample_df = disease_df.head(limit)
    logger.info(f"Testing with {len(sample_df)} questions")

    # Initialize client and components
    client = get_openrouter_client()
    prompt_manager = get_prompt_manager()
    aggregator = VoteAggregator()

    # Load disease-specific prompt
    disease_prompt = prompt_manager.get_disease_prompt(disease, version="v2.0")
    if not disease_prompt:
        logger.warning(f"No disease prompt for {disease}, using fallback")
        disease_prompt = prompt_manager.get_fallback_prompt(version="v2.0")

    logger.info(f"Loaded disease prompt: {len(disease_prompt)} characters")

    # Results storage
    results = []

    # Process each question
    for idx, (row_idx, row) in enumerate(sample_df.iterrows()):
        qgd = row['QUESTIONGROUPDESIGNATION']
        question_text = row.get('OPTIMIZEDQUESTION') or row.get('RAWQUESTION') or ''
        correct_answer = row.get('OPTIMIZEDCORRECTANSWER') or ''
        activity_name = row.get('ACTIVITY_NAMES') or ''
        start_date = row.get('START_DATES') or ''

        logger.info(f"Processing {idx+1}/{len(sample_df)}: QGD {qgd}")

        try:
            if dry_run:
                # Simulate response
                result_row = {
                    'QUESTIONGROUPDESIGNATION': qgd,
                    'OPTIMIZEDQUESTION': question_text[:200],
                    'OPTIMIZEDCORRECTANSWER': correct_answer[:200],
                    'ACTIVITY_NAMES': activity_name,
                    'DISEASE_STATE': disease,
                    'AGREEMENT': 'dry_run',
                    'NEEDS_REVIEW': False,
                }
                for field in TAG_FIELDS:
                    result_row[f'FINAL_{field}'] = None
                    result_row[f'GPT_{field}'] = None
                    result_row[f'CLAUDE_{field}'] = None
                    result_row[f'GEMINI_{field}'] = None
            else:
                # Build messages
                user_content = f"STARTDATE: {start_date}\n\nQuestion: {question_text}\n\nCorrect Answer: {correct_answer}"
                messages = [
                    {"role": "system", "content": disease_prompt},
                    {"role": "user", "content": user_content}
                ]

                # Call 3 models in parallel
                # Use higher max_tokens for 66-field JSON output (default 1000 is too small)
                responses = await client.generate_parallel(
                    messages=messages,
                    models=["gpt", "claude", "gemini"],
                    max_tokens=4000,  # 66-field JSON needs ~2500+ output tokens
                    response_format={"type": "json_object"}
                )

                # Parse responses with model-specific logging
                gpt_content = responses.get("gpt", {}).get("content", "")
                claude_content = responses.get("claude", {}).get("content", "")
                gemini_content = responses.get("gemini", {}).get("content", "")

                # Debug: Log first 200 chars of each response to diagnose issues
                if gemini_content and not gemini_content.strip().startswith('{') and not '```' in gemini_content[:50]:
                    logger.debug(f"Gemini raw response start: {gemini_content[:300]}")

                gpt_tags = parse_response(gpt_content, "GPT")
                claude_tags = parse_response(claude_content, "Claude")
                gemini_tags = parse_response(gemini_content, "Gemini")

                # Aggregate votes
                aggregated = aggregator.aggregate(
                    question_id=idx,
                    gpt_response=gpt_tags,
                    claude_response=claude_tags,
                    gemini_response=gemini_tags
                )

                # Build result row
                result_row = {
                    'QUESTIONGROUPDESIGNATION': qgd,
                    'OPTIMIZEDQUESTION': question_text,
                    'OPTIMIZEDCORRECTANSWER': correct_answer,
                    'ACTIVITY_NAMES': activity_name,
                    'START_DATES': start_date,
                    'DISEASE_STATE': disease,
                    'AGREEMENT': aggregated.overall_agreement.value,
                    'CONFIDENCE': aggregated.overall_confidence,
                    'NEEDS_REVIEW': aggregated.needs_review,
                    'REVIEW_REASON': aggregated.review_reason or '',
                }

                # Add final tags
                for field in TAG_FIELDS:
                    if aggregated.final_tags:
                        result_row[f'FINAL_{field}'] = aggregated.final_tags.get(field)
                    else:
                        result_row[f'FINAL_{field}'] = None

                # Add per-model votes
                for field in TAG_FIELDS:
                    if field in aggregated.tags:
                        tag_vote = aggregated.tags[field]
                        result_row[f'GPT_{field}'] = tag_vote.gpt_value
                        result_row[f'CLAUDE_{field}'] = tag_vote.claude_value
                        result_row[f'GEMINI_{field}'] = tag_vote.gemini_value
                    else:
                        result_row[f'GPT_{field}'] = None
                        result_row[f'CLAUDE_{field}'] = None
                        result_row[f'GEMINI_{field}'] = None

            results.append(result_row)

        except Exception as e:
            logger.error(f"Error processing QGD {qgd}: {e}")
            import traceback
            traceback.print_exc()
            result_row = {
                'QUESTIONGROUPDESIGNATION': qgd,
                'OPTIMIZEDQUESTION': question_text[:200],
                'OPTIMIZEDCORRECTANSWER': correct_answer[:200],
                'ERROR': str(e),
            }
            results.append(result_row)

    # Save results
    results_df = pd.DataFrame(results)

    # Create filename
    disease_slug = disease.lower().replace(" ", "_")
    results_path = OUTPUT_DIR / f"stage2_test_{disease_slug}_{timestamp}.xlsx"

    results_df.to_excel(results_path, index=False)

    # Print summary
    print("\n" + "=" * 60)
    print("STAGE 2 TEST COMPLETE")
    print("=" * 60)
    print(f"Disease: {disease}")
    print(f"Questions tagged: {len(results)}")

    if not dry_run:
        # Agreement stats
        if 'AGREEMENT' in results_df.columns:
            agreement_counts = results_df['AGREEMENT'].value_counts()
            print(f"\nAgreement breakdown:")
            for agreement, count in agreement_counts.items():
                print(f"  {agreement}: {count}")

        # Review needed
        needs_review = results_df['NEEDS_REVIEW'].sum() if 'NEEDS_REVIEW' in results_df.columns else 0
        print(f"\nNeeds review: {needs_review}")

        # Cost
        if hasattr(client, 'get_total_cost'):
            cost = client.get_total_cost()
            print(f"Total cost: ${cost:.2f}")

    print(f"\nResults saved to: {results_path}")
    print("=" * 60)

    # Create review file
    review_path = create_review_file(results_df, disease_slug, timestamp)
    print(f"Review file saved to: {review_path}")

    return results_path


def create_review_file(results_df: pd.DataFrame, disease_slug: str, timestamp: str) -> Path:
    """Create a human-readable review file for the tagging results."""

    review_rows = []

    for _, row in results_df.iterrows():
        review_row = {
            'QGD': row.get('QUESTIONGROUPDESIGNATION'),
            'QUESTION': row.get('OPTIMIZEDQUESTION', '')[:500] if pd.notna(row.get('OPTIMIZEDQUESTION')) else '',
            'ANSWER': row.get('OPTIMIZEDCORRECTANSWER', '')[:300] if pd.notna(row.get('OPTIMIZEDCORRECTANSWER')) else '',
            'ACTIVITY': row.get('ACTIVITY_NAMES', '')[:100] if pd.notna(row.get('ACTIVITY_NAMES')) else '',
            'AGREEMENT': row.get('AGREEMENT', ''),
            'NEEDS_REVIEW': row.get('NEEDS_REVIEW', False),
            'REVIEW_REASON': row.get('REVIEW_REASON', ''),
        }

        # Core fields
        core_fields = ['topic', 'disease_stage', 'disease_type', 'treatment_line']
        for field in core_fields:
            review_row[f'FINAL_{field}'] = row.get(f'FINAL_{field}', '')
            review_row[f'GPT_{field}'] = row.get(f'GPT_{field}', '')
            review_row[f'CLAUDE_{field}'] = row.get(f'CLAUDE_{field}', '')
            review_row[f'GEMINI_{field}'] = row.get(f'GEMINI_{field}', '')

        # Multi-value fields (show up to 3)
        for base in ['treatment', 'biomarker', 'trial']:
            for i in range(1, 4):
                field = f'{base}_{i}'
                review_row[f'FINAL_{field}'] = row.get(f'FINAL_{field}', '')

        # Group A-F key fields (including new Group F question quality fields)
        key_fields = [
            'drug_class_1', 'drug_target_1', 'prior_therapy_1',
            'metastatic_site_1', 'special_population_1', 'performance_status',
            'toxicity_type_1', 'toxicity_organ', 'toxicity_grade',
            'efficacy_endpoint_1', 'outcome_context', 'clinical_benefit',
            'guideline_source_1', 'evidence_type',
            'cme_outcome_level', 'data_response_type',
            # New Group F question structure and flaw fields
            'stem_type', 'lead_in_type', 'answer_format',
            'flaw_absolute_terms', 'flaw_implausible_distractor'
        ]
        for field in key_fields:
            review_row[f'FINAL_{field}'] = row.get(f'FINAL_{field}', '')

        # Add correction columns
        review_row['CORRECT_topic'] = ''
        review_row['CORRECT_disease_type'] = ''
        review_row['CORRECT_treatment_1'] = ''
        review_row['REVIEWER_NOTES'] = ''

        review_rows.append(review_row)

    review_df = pd.DataFrame(review_rows)

    # Save review file
    review_path = OUTPUT_DIR / f"stage2_review_{disease_slug}_{timestamp}.xlsx"
    review_df.to_excel(review_path, index=False)

    return review_path


def main():
    parser = argparse.ArgumentParser(description='Run Stage 2 tagging test')
    parser.add_argument(
        '--disease', '-d',
        type=str,
        default='Breast cancer',
        help='Disease state to test (default: "Breast cancer")'
    )
    parser.add_argument(
        '--limit', '-n',
        type=int,
        default=25,
        help='Number of questions to tag (default: 25)'
    )
    parser.add_argument(
        '--input', '-i',
        type=str,
        default='data/checkpoints/stage2_ready_final.xlsx',
        help='Input file with Stage 2 ready questions'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Test run without API calls'
    )

    args = parser.parse_args()

    # Validate API key
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key and not args.dry_run:
        print("ERROR: OPENROUTER_API_KEY environment variable not set!")
        print("Set it with: set OPENROUTER_API_KEY=your_key_here")
        return

    # Run test
    asyncio.run(run_stage2_test(
        disease=args.disease,
        limit=args.limit,
        input_file=args.input,
        dry_run=args.dry_run
    ))


if __name__ == "__main__":
    main()
