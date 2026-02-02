"""
Clean up question stem typos and encoding artifacts.

Applies fixes from src/deduplication/cleanup.py:
- Encoding artifacts (smart quotes, em dashes, etc.)
- Missing spaces after periods/commas
- Concatenated words
- Multiple consecutive spaces

Usage:
    python scripts/clean_question_stems.py --dry-run  # Preview changes
    python scripts/clean_question_stems.py            # Apply changes
"""

import json
import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from deduplication.cleanup import clean_text_full, detect_encoding_issues, detect_formatting_issues


def clean_checkpoint_stems(data: list, dry_run: bool = True) -> tuple:
    """
    Clean question stems and answer text in checkpoint data.

    Returns:
        (data, changes_report)
    """
    changes = []

    for q in data:
        qid = q.get('question_id', 'unknown')
        source_id = q.get('source_id', '')

        # Clean question_stem
        stem = q.get('question_stem', '')
        if stem:
            cleaned_stem, stem_fixes = clean_text_full(stem)
            if stem_fixes:
                changes.append({
                    'question_id': qid,
                    'source_id': source_id,
                    'field': 'question_stem',
                    'original': stem[:200] + '...' if len(stem) > 200 else stem,
                    'cleaned': cleaned_stem[:200] + '...' if len(cleaned_stem) > 200 else cleaned_stem,
                    'fixes': stem_fixes
                })
                if not dry_run:
                    q['question_stem'] = cleaned_stem

        # Clean correct_answer
        correct = q.get('correct_answer', '')
        if correct:
            cleaned_correct, correct_fixes = clean_text_full(correct)
            if correct_fixes:
                changes.append({
                    'question_id': qid,
                    'source_id': source_id,
                    'field': 'correct_answer',
                    'original': correct[:200] + '...' if len(correct) > 200 else correct,
                    'cleaned': cleaned_correct[:200] + '...' if len(cleaned_correct) > 200 else cleaned_correct,
                    'fixes': correct_fixes
                })
                if not dry_run:
                    q['correct_answer'] = cleaned_correct

        # Clean incorrect_answers
        incorrect = q.get('incorrect_answers', [])
        if incorrect and isinstance(incorrect, list):
            cleaned_incorrect = []
            for i, ans in enumerate(incorrect):
                if ans:
                    cleaned_ans, ans_fixes = clean_text_full(ans)
                    if ans_fixes:
                        changes.append({
                            'question_id': qid,
                            'source_id': source_id,
                            'field': f'incorrect_answer_{i}',
                            'original': ans[:200] + '...' if len(ans) > 200 else ans,
                            'cleaned': cleaned_ans[:200] + '...' if len(cleaned_ans) > 200 else cleaned_ans,
                            'fixes': ans_fixes
                        })
                    cleaned_incorrect.append(cleaned_ans if not dry_run else ans)
                else:
                    cleaned_incorrect.append(ans)
            if not dry_run:
                q['incorrect_answers'] = [clean_text_full(a)[0] if a else a for a in incorrect]

    return data, changes


def summarize_changes(changes: list) -> dict:
    """Summarize changes by fix type."""
    summary = {
        'total_changes': len(changes),
        'questions_affected': len(set(c['question_id'] for c in changes)),
        'by_field': {},
        'by_fix_type': {}
    }

    for change in changes:
        # By field
        field = change['field']
        summary['by_field'][field] = summary['by_field'].get(field, 0) + 1

        # By fix type
        for fix_type, count in change['fixes'].items():
            if isinstance(count, dict):
                # Nested (like options)
                for sub_type, sub_count in count.items():
                    key = f"{fix_type}.{sub_type}"
                    summary['by_fix_type'][key] = summary['by_fix_type'].get(key, 0) + sub_count
            else:
                summary['by_fix_type'][fix_type] = summary['by_fix_type'].get(fix_type, 0) + count

    return summary


def main():
    parser = argparse.ArgumentParser(description='Clean question stem typos and encoding artifacts')
    parser.add_argument('--checkpoint', type=str,
                        default='data/checkpoints/stage2_tagged_multiple_myeloma.json',
                        help='Path to checkpoint file')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview changes without applying')
    parser.add_argument('--show-all', action='store_true',
                        help='Show all changes (default: first 20)')
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

    # Clean stems
    print("\nAnalyzing question stems for typos and encoding issues...")
    data, changes = clean_checkpoint_stems(data, dry_run=args.dry_run)

    # Report
    print(f"\n{'='*60}")
    print("QUESTION STEM CLEANUP REPORT")
    print(f"{'='*60}")

    if not changes:
        print("\nNo changes needed - all question stems are clean!")
        return 0

    summary = summarize_changes(changes)
    print(f"\nTotal changes needed: {summary['total_changes']}")
    print(f"Questions affected: {summary['questions_affected']}")

    print(f"\nChanges by field:")
    for field, count in sorted(summary['by_field'].items()):
        print(f"  {field}: {count}")

    print(f"\nChanges by fix type:")
    for fix_type, count in sorted(summary['by_fix_type'].items(), key=lambda x: -x[1]):
        print(f"  {fix_type}: {count}")

    # Show examples
    print(f"\n{'='*60}")
    print("EXAMPLE CHANGES")
    print(f"{'='*60}")

    show_count = len(changes) if args.show_all else min(20, len(changes))
    for i, change in enumerate(changes[:show_count]):
        print(f"\n[{i+1}] Q{change['question_id']} ({change['source_id']}) - {change['field']}")
        print(f"    Fixes: {change['fixes']}")
        print(f"    BEFORE: {change['original']}")
        print(f"    AFTER:  {change['cleaned']}")

    if len(changes) > show_count:
        print(f"\n... and {len(changes) - show_count} more changes")

    if args.dry_run:
        print(f"\n{'='*60}")
        print("DRY RUN - No changes applied")
        print(f"{'='*60}")
        print(f"Would apply {summary['total_changes']} fixes to {summary['questions_affected']} questions")
        return 0

    # Apply changes
    print(f"\n{'='*60}")
    print("APPLYING CHANGES")
    print(f"{'='*60}")

    # Re-run without dry-run to actually apply changes
    data, _ = clean_checkpoint_stems(data, dry_run=False)

    # Backup
    backup_path = checkpoint_path.with_suffix(f'.json.pre_stem_cleanup_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
    shutil.copy(checkpoint_path, backup_path)
    print(f"Backup created: {backup_path}")

    # Save
    with open(checkpoint_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Saved updated checkpoint: {checkpoint_path}")

    # Save changes log
    log_path = checkpoint_path.parent / f'stem_cleanup_changes_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump({
            'summary': summary,
            'changes': changes
        }, f, indent=2, ensure_ascii=False)
    print(f"Saved changes log: {log_path}")

    print(f"\nDone! Applied {summary['total_changes']} fixes to {summary['questions_affected']} questions")
    return 0


if __name__ == '__main__':
    exit(main())
