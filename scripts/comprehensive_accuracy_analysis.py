"""
Comprehensive Accuracy Analysis for LLM Tagging

Analyzes correction data to generate:
1. Overall accuracy metrics
2. Per-field accuracy with error patterns
3. Correction type breakdown (wrong, null->added, cleared)
4. Top correction patterns for prompt improvement

Usage:
    python scripts/comprehensive_accuracy_analysis.py [--output report.txt]
"""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
CORRECTIONS_DIR = PROJECT_ROOT / "data" / "corrections"


def load_corrections(corrections_dir: Path) -> list[dict]:
    """Load all correction records from JSONL files."""
    corrections = []

    for jsonl_file in corrections_dir.glob("*.jsonl"):
        print(f"Loading {jsonl_file.name}...")
        with open(jsonl_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        corrections.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        print(f"  Warning: Could not parse line: {e}")

    return corrections


def analyze_corrections(corrections: list[dict]) -> dict:
    """Analyze all corrections and generate metrics."""

    # Overall stats
    total_questions = len(corrections)
    questions_with_edits = sum(1 for c in corrections if c.get("edited_fields"))

    # Per-field tracking
    field_stats = defaultdict(lambda: {
        "total_reviewed": 0,
        "total_edited": 0,
        "wrong_to_fixed": [],      # LLM had value, human changed it
        "null_to_added": [],       # LLM had null, human added value
        "value_to_cleared": [],    # LLM had value, human cleared it
        "original_values": Counter(),
        "corrected_values": Counter(),
        "correction_patterns": Counter(),  # "original -> corrected"
    })

    # Correction type counts
    correction_types = {
        "wrong_to_fixed": 0,
        "null_to_added": 0,
        "value_to_cleared": 0,
    }

    # Process each correction
    for correction in corrections:
        edited_fields = correction.get("edited_fields", []) or []
        original_tags = correction.get("original_tags", {}) or {}
        corrected_tags = correction.get("corrected_tags", {}) or {}
        question_id = correction.get("question_id")

        # Track all fields that were reviewed (even if not edited)
        for field in set(list(original_tags.keys()) + list(corrected_tags.keys())):
            field_stats[field]["total_reviewed"] += 1

        # Analyze edited fields
        for field in edited_fields:
            original_val = original_tags.get(field)
            corrected_val = corrected_tags.get(field)

            # Normalize empty values
            if original_val in (None, "", "null"):
                original_val = None
            if corrected_val in (None, "", "null"):
                corrected_val = None

            field_stats[field]["total_edited"] += 1

            entry = {
                "question_id": question_id,
                "original": original_val,
                "corrected": corrected_val,
            }

            # Categorize the correction type
            if original_val and corrected_val and str(original_val) != str(corrected_val):
                # LLM had a value, human changed it to something else
                correction_types["wrong_to_fixed"] += 1
                field_stats[field]["wrong_to_fixed"].append(entry)
                pattern = f"{original_val} -> {corrected_val}"
            elif not original_val and corrected_val:
                # LLM had null, human added a value
                correction_types["null_to_added"] += 1
                field_stats[field]["null_to_added"].append(entry)
                pattern = f"(null) -> {corrected_val}"
            elif original_val and not corrected_val:
                # LLM had a value, human cleared it
                correction_types["value_to_cleared"] += 1
                field_stats[field]["value_to_cleared"].append(entry)
                pattern = f"{original_val} -> (cleared)"
            else:
                pattern = None

            if pattern:
                field_stats[field]["correction_patterns"][pattern] += 1

            # Track value distributions
            if original_val:
                field_stats[field]["original_values"][str(original_val)] += 1
            if corrected_val:
                field_stats[field]["corrected_values"][str(corrected_val)] += 1

    return {
        "total_questions": total_questions,
        "questions_with_edits": questions_with_edits,
        "overall_accuracy": (total_questions - questions_with_edits) / total_questions * 100 if total_questions else 0,
        "correction_types": correction_types,
        "field_stats": dict(field_stats),
    }


def generate_report(analysis: dict) -> str:
    """Generate a human-readable report from the analysis."""
    lines = []

    # Header
    lines.append("=" * 80)
    lines.append("COMPREHENSIVE ACCURACY ANALYSIS REPORT")
    lines.append(f"Generated: {datetime.now().isoformat()}")
    lines.append("=" * 80)
    lines.append("")

    # Overall Summary
    lines.append("## OVERALL SUMMARY")
    lines.append("-" * 40)
    lines.append(f"Total questions reviewed:    {analysis['total_questions']}")
    lines.append(f"Questions with corrections:  {analysis['questions_with_edits']}")
    lines.append(f"Questions without changes:   {analysis['total_questions'] - analysis['questions_with_edits']}")
    lines.append(f"Overall accuracy rate:       {analysis['overall_accuracy']:.1f}%")
    lines.append("")

    # Correction Types
    ct = analysis["correction_types"]
    total_edits = sum(ct.values())
    lines.append("## CORRECTION TYPE BREAKDOWN")
    lines.append("-" * 40)
    lines.append(f"LLM wrong, human fixed:     {ct['wrong_to_fixed']:4d} ({ct['wrong_to_fixed']/total_edits*100:.1f}%)" if total_edits else "N/A")
    lines.append(f"LLM null, human added:      {ct['null_to_added']:4d} ({ct['null_to_added']/total_edits*100:.1f}%)" if total_edits else "N/A")
    lines.append(f"LLM value, human cleared:   {ct['value_to_cleared']:4d} ({ct['value_to_cleared']/total_edits*100:.1f}%)" if total_edits else "N/A")
    lines.append(f"TOTAL field edits:          {total_edits:4d}")
    lines.append("")

    # Per-field accuracy (sorted by error rate)
    lines.append("## PER-FIELD ACCURACY")
    lines.append("-" * 40)

    field_errors = []
    for field, stats in analysis["field_stats"].items():
        if stats["total_reviewed"] > 0:
            error_count = stats["total_edited"]
            error_rate = error_count / stats["total_reviewed"] * 100
            field_errors.append((field, error_count, error_rate, stats))

    # Sort by error count (descending)
    field_errors.sort(key=lambda x: x[1], reverse=True)

    # Show fields with errors
    lines.append("")
    lines.append("### Fields with Most Corrections")
    lines.append(f"{'Field':<35} {'Errors':>8} {'Rate':>8}")
    lines.append("-" * 55)

    for field, error_count, error_rate, stats in field_errors[:30]:
        if error_count > 0:
            lines.append(f"{field:<35} {error_count:>8} {error_rate:>7.1f}%")

    lines.append("")

    # Top correction patterns
    lines.append("## TOP CORRECTION PATTERNS")
    lines.append("-" * 40)
    lines.append("(Patterns that appear 3+ times)")
    lines.append("")

    all_patterns = Counter()
    for field, stats in analysis["field_stats"].items():
        for pattern, count in stats["correction_patterns"].items():
            all_patterns[f"{field}: {pattern}"] += count

    for pattern, count in all_patterns.most_common(50):
        if count >= 3:
            lines.append(f"  [{count:3d}x] {pattern}")

    lines.append("")

    # Detailed field analysis for problem fields
    lines.append("## DETAILED FIELD ANALYSIS")
    lines.append("-" * 40)

    for field, error_count, error_rate, stats in field_errors[:15]:
        if error_count < 3:
            continue

        lines.append("")
        lines.append(f"### {field}")
        lines.append(f"    Reviewed: {stats['total_reviewed']}, Edited: {error_count} ({error_rate:.1f}%)")
        lines.append(f"    - Wrong->Fixed: {len(stats['wrong_to_fixed'])}")
        lines.append(f"    - Null->Added:  {len(stats['null_to_added'])}")
        lines.append(f"    - Value->Cleared: {len(stats['value_to_cleared'])}")

        if stats["correction_patterns"]:
            lines.append("    Top patterns:")
            for pattern, count in stats["correction_patterns"].most_common(5):
                lines.append(f"      [{count}x] {pattern}")

    lines.append("")
    lines.append("=" * 80)
    lines.append("END OF REPORT")
    lines.append("=" * 80)

    return "\n".join(lines)


def generate_patterns_yaml(analysis: dict, output_path: Path):
    """Generate a YAML file with correction patterns for prompt improvement."""
    import yaml

    patterns = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_corrections_analyzed": analysis["total_questions"],
        },
        "correction_patterns": [],
        "field_normalization_rules": {},
    }

    # Extract patterns
    for field, stats in analysis["field_stats"].items():
        if stats["total_edited"] < 2:
            continue

        for pattern, count in stats["correction_patterns"].most_common(10):
            if count >= 2:
                patterns["correction_patterns"].append({
                    "field": field,
                    "pattern": pattern,
                    "count": count,
                    "action": "review",  # To be filled in manually
                })

    # Extract normalization rules (value mappings that appear multiple times)
    for field, stats in analysis["field_stats"].items():
        mappings = {}
        for entry in stats["wrong_to_fixed"]:
            orig = str(entry["original"]) if entry["original"] else None
            corr = str(entry["corrected"]) if entry["corrected"] else None
            if orig and corr:
                key = orig
                if key not in mappings:
                    mappings[key] = Counter()
                mappings[key][corr] += 1

        # Only include mappings with 2+ occurrences
        field_rules = {}
        for orig, targets in mappings.items():
            top_target, count = targets.most_common(1)[0]
            if count >= 2:
                field_rules[orig] = top_target

        if field_rules:
            patterns["field_normalization_rules"][field] = field_rules

    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(patterns, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    print(f"Wrote patterns to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Comprehensive accuracy analysis")
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "accuracy_report.txt",
        help="Output file for the report",
    )
    parser.add_argument(
        "--patterns-yaml",
        type=Path,
        default=PROJECT_ROOT / "config" / "correction_patterns.yaml",
        help="Output file for correction patterns YAML",
    )
    args = parser.parse_args()

    print("Loading corrections...")
    corrections = load_corrections(CORRECTIONS_DIR)
    print(f"Loaded {len(corrections)} correction records")

    if not corrections:
        print("No corrections found!")
        return 1

    print("\nAnalyzing corrections...")
    analysis = analyze_corrections(corrections)

    print("\nGenerating report...")
    report = generate_report(analysis)

    # Write report
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\nWrote report to {args.output}")

    # Print summary to console
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total questions:          {analysis['total_questions']}")
    print(f"Questions with edits:     {analysis['questions_with_edits']}")
    print(f"Overall accuracy:         {analysis['overall_accuracy']:.1f}%")
    print(f"Total field corrections:  {sum(analysis['correction_types'].values())}")

    # Generate patterns YAML
    print("\nGenerating correction patterns YAML...")
    generate_patterns_yaml(analysis, args.patterns_yaml)

    return 0


if __name__ == "__main__":
    exit(main())
