"""
Recover risk stratification data from model votes.

The first batch of MM questions had LLM-tagged risk levels (low/standard/high-risk in disease_type_1)
but they weren't always captured in final_tags. This script extracts risk values from model votes
and populates disease_type_1.

Usage:
    python scripts/recover_risk_stratification.py --dry-run  # Preview changes
    python scripts/recover_risk_stratification.py            # Apply changes
"""

import json
import argparse
import shutil
from datetime import datetime
from pathlib import Path
from collections import Counter


RISK_KEYWORDS = [
    'high-risk', 'high risk', 'standard-risk', 'standard risk',
    'low-risk', 'low risk', 'High-risk', 'Standard-risk', 'Low-risk'
]


def normalize_risk_value(value: str) -> str:
    """Normalize risk stratification values to canonical form."""
    if not value:
        return None
    value_lower = value.lower().strip()
    if 'high' in value_lower and 'risk' in value_lower:
        return 'High-risk'
    elif 'standard' in value_lower and 'risk' in value_lower:
        return 'Standard-risk'
    elif 'low' in value_lower and 'risk' in value_lower:
        return 'Low-risk'
    return value  # Return as-is for other values like "Smoldering MM", "MGUS"


def has_risk_keyword(value: str) -> bool:
    """Check if value contains risk stratification keywords."""
    if not value:
        return False
    return any(kw.lower() in str(value).lower() for kw in RISK_KEYWORDS)


def get_model_risk_votes(question: dict) -> dict:
    """Extract risk stratification votes from model tags."""
    votes = {}
    for model in ['gpt_tags', 'claude_tags', 'gemini_tags']:
        model_tags = question.get(model)
        if model_tags:
            dt1 = model_tags.get('disease_type_1')
            if has_risk_keyword(dt1):
                votes[model] = normalize_risk_value(dt1)
    return votes


def determine_final_value(votes: dict) -> tuple:
    """
    Determine final risk value based on voting logic.

    Returns:
        (final_value, agreement_level, should_apply)
        - agreement_level: 'unanimous', 'majority', 'single'
        - should_apply: True for unanimous/majority, False for single
    """
    if not votes:
        return None, None, False

    vote_values = list(votes.values())
    vote_counts = Counter(vote_values)
    most_common_value, most_common_count = vote_counts.most_common(1)[0]

    if len(votes) == 3 and most_common_count == 3:
        return most_common_value, 'unanimous', True
    elif len(votes) >= 2 and most_common_count >= 2:
        return most_common_value, 'majority', True
    else:
        return most_common_value, 'single', False  # Don't auto-apply single model votes


def find_recoverable_questions(data: list) -> list:
    """Find questions with null disease_type_1 but risk in model votes."""
    recoverable = []

    for q in data:
        final_dt = q.get('final_tags', {}).get('disease_type_1')
        if final_dt and str(final_dt).strip():
            continue  # Already has a value

        votes = get_model_risk_votes(q)
        if votes:
            final_value, agreement, should_apply = determine_final_value(votes)
            recoverable.append({
                'question_id': q['question_id'],
                'source_id': q.get('source_id'),
                'model_votes': votes,
                'final_value': final_value,
                'agreement': agreement,
                'should_apply': should_apply,
                'question_stem': q.get('question_stem', '')[:100] + '...'
            })

    return recoverable


def apply_recoveries(data: list, recoveries: list) -> int:
    """Apply risk stratification recoveries to data. Returns count of applied."""
    recovery_map = {r['question_id']: r for r in recoveries if r['should_apply']}
    applied = 0

    for q in data:
        qid = q['question_id']
        if qid in recovery_map:
            recovery = recovery_map[qid]
            # Update final_tags
            if 'final_tags' not in q:
                q['final_tags'] = {}
            q['final_tags']['disease_type_1'] = recovery['final_value']

            # Also update field_votes if present
            if 'field_votes' in q and 'disease_type_1' in q['field_votes']:
                q['field_votes']['disease_type_1']['final_value'] = recovery['final_value']

            applied += 1

    return applied


def main():
    parser = argparse.ArgumentParser(description='Recover risk stratification from model votes')
    parser.add_argument('--checkpoint', type=str,
                        default='data/checkpoints/stage2_tagged_multiple_myeloma.json',
                        help='Path to checkpoint file')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview changes without applying')
    args = parser.parse_args()

    checkpoint_path = Path(args.checkpoint)
    if not checkpoint_path.exists():
        print(f"Error: Checkpoint file not found: {checkpoint_path}")
        return 1

    # Load data
    print(f"Loading checkpoint: {checkpoint_path}")
    with open(checkpoint_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"Total questions: {len(data)}")

    # Find recoverable questions
    recoveries = find_recoverable_questions(data)

    print(f"\n{'='*60}")
    print("RISK STRATIFICATION RECOVERY REPORT")
    print(f"{'='*60}")

    # Summary by agreement level
    unanimous = [r for r in recoveries if r['agreement'] == 'unanimous']
    majority = [r for r in recoveries if r['agreement'] == 'majority']
    single = [r for r in recoveries if r['agreement'] == 'single']

    print(f"\nRecoverable questions: {len(recoveries)}")
    print(f"  Unanimous (3/3) - will apply: {len(unanimous)}")
    print(f"  Majority (2/3) - will apply: {len(majority)}")
    print(f"  Single model (1/3) - needs review: {len(single)}")

    # Value distribution
    will_apply = [r for r in recoveries if r['should_apply']]
    value_counts = Counter(r['final_value'] for r in will_apply)
    print(f"\nValues to be applied:")
    for value, count in value_counts.most_common():
        print(f"  {value}: {count}")

    # Show examples
    print(f"\n{'='*60}")
    print("EXAMPLES - TO BE APPLIED (unanimous/majority)")
    print(f"{'='*60}")
    for r in will_apply[:5]:
        print(f"\nQ{r['question_id']} ({r['source_id']}):")
        print(f"  Votes: {r['model_votes']}")
        print(f"  Final: {r['final_value']} ({r['agreement']})")

    if single:
        print(f"\n{'='*60}")
        print("EXAMPLES - NEEDS REVIEW (single model only)")
        print(f"{'='*60}")
        for r in single[:5]:
            print(f"\nQ{r['question_id']} ({r['source_id']}):")
            print(f"  Votes: {r['model_votes']}")
            print(f"  Suggested: {r['final_value']} (single model - not auto-applied)")

    if args.dry_run:
        print(f"\n{'='*60}")
        print("DRY RUN - No changes applied")
        print(f"{'='*60}")
        print(f"Would apply {len(will_apply)} risk stratification values")
        print(f"Would flag {len(single)} questions for manual review")
        return 0

    # Apply changes
    print(f"\n{'='*60}")
    print("APPLYING CHANGES")
    print(f"{'='*60}")

    # Backup
    backup_path = checkpoint_path.with_suffix(f'.json.pre_risk_recovery_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
    shutil.copy(checkpoint_path, backup_path)
    print(f"Backup created: {backup_path}")

    # Apply
    applied_count = apply_recoveries(data, recoveries)
    print(f"Applied {applied_count} risk stratification values")

    # Save
    with open(checkpoint_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Saved updated checkpoint: {checkpoint_path}")

    # Save review list for single-model cases
    if single:
        review_path = checkpoint_path.parent / 'risk_stratification_needs_review.json'
        with open(review_path, 'w', encoding='utf-8') as f:
            json.dump(single, f, indent=2, ensure_ascii=False)
        print(f"Saved review list ({len(single)} items): {review_path}")

    print(f"\nDone!")
    return 0


if __name__ == '__main__':
    exit(main())
