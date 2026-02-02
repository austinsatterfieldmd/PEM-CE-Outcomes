#!/usr/bin/env python3
"""
Calculate QCore scores for all questions in the database.

This script:
1. Loads questions with quality tags from the database
2. Calculates QCore scores using the qcore_scorer
3. Stores scores back in the database

Usage:
    python scripts/calculate_qcore_scores.py
    python scripts/calculate_qcore_scores.py --dry-run
    python scripts/calculate_qcore_scores.py --question-id 4473
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.backend.services.database import DatabaseService


def main():
    parser = argparse.ArgumentParser(description="Calculate QCore scores for questions")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be scored without updating")
    parser.add_argument("--question-id", type=int, help="Score a specific question")
    parser.add_argument("--show-stats", action="store_true", help="Show scoring statistics only")
    args = parser.parse_args()

    db = DatabaseService()

    if args.show_stats:
        # Show current stats
        stats = db.get_qcore_stats()
        print("\n=== QCore Scoring Statistics ===")
        print(f"Total scored: {stats['total_scored']}")
        print(f"Total unscored: {stats['total_unscored']}")
        print(f"Average score: {stats['avg_score']}")
        print(f"Score range: {stats['min_score']} - {stats['max_score']}")
        print(f"Ready for deployment (>=80): {stats['ready_count']}")
        print("\nGrade Distribution:")
        for grade, data in sorted(stats['grade_distribution'].items()):
            print(f"  {grade}: {data['count']} questions (avg {data['avg_score']})")
        return

    if args.question_id:
        # Score a single question
        print(f"\nScoring question {args.question_id}...")
        result = db.calculate_qcore_for_question(args.question_id)
        if result:
            print(f"  Score: {result['score']} ({result['grade']})")
            print(f"  Ready for deployment: {result['ready_for_deployment']}")
            print(f"  Breakdown:")
            breakdown = result['breakdown']
            if 'flaws' in breakdown:
                flaw_penalties = sum(v for v in breakdown['flaws'].values() if v != 0)
                if flaw_penalties:
                    print(f"    Flaw deductions: {flaw_penalties}")
            if 'structure_deductions' in breakdown:
                struct_ded = sum(breakdown['structure_deductions'].values())
                if struct_ded:
                    print(f"    Structure deductions: -{struct_ded}")
            if 'structure_bonuses' in breakdown:
                struct_bonus = sum(breakdown['structure_bonuses'].values())
                if struct_bonus:
                    print(f"    Structure bonuses: +{struct_bonus}")
        else:
            print("  Question not found or has no tags")
        return

    if args.dry_run:
        # Show what would be scored
        print("\n=== DRY RUN - Showing questions to be scored ===")
        stats = db.get_qcore_stats()
        print(f"Questions with scores: {stats['total_scored']}")
        print(f"Questions without scores: {stats['total_unscored']}")
        print("\nRun without --dry-run to score all questions.")
        return

    # Score all questions
    print("\n=== Calculating QCore scores for all questions ===")
    result = db.calculate_qcore_for_all_questions()

    print(f"\nResults:")
    print(f"  Total questions: {result['total']}")
    print(f"  Scored: {result['scored']}")
    print(f"  Skipped (no quality tags): {result['skipped']}")
    print(f"  Failed: {result['failed']}")

    # Show updated stats
    print("\n=== Updated Statistics ===")
    stats = db.get_qcore_stats()
    print(f"Average score: {stats['avg_score']}")
    print(f"Ready for deployment (>=80): {stats['ready_count']}")
    print("\nGrade Distribution:")
    for grade, data in sorted(stats['grade_distribution'].items()):
        print(f"  {grade}: {data['count']} questions (avg {data['avg_score']})")


if __name__ == "__main__":
    main()
