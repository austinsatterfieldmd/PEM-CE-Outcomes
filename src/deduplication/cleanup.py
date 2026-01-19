"""
Fix encoding artifacts in question text.

Common issues from copy-paste and database migrations:
- â€™ → '
- â€œ → "
- â€ → "
- Ã© → é
- â€" → —
"""

import logging
import re
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


# Common encoding artifacts (sorted by frequency)
ENCODING_FIXES = {
    # Smart quotes and apostrophes
    "â€™": "'",
    "â€˜": "'",
    "â€œ": '"',
    "â€": '"',

    # Dashes and hyphens
    "â€"": "—",  # em dash
    "â€"": "–",  # en dash

    # Common accented characters
    "Ã©": "é",
    "Ã¨": "è",
    "Ã ": "à",
    "Ã¡": "á",
    "Ã³": "ó",
    "Ã±": "ñ",
    "Ã¼": "ü",

    # Miscellaneous
    "â€¦": "…",  # ellipsis
    "Â": "",     # non-breaking space artifact
    "â€¢": "•",  # bullet point
}


def clean_text(text: str) -> Tuple[str, int]:
    """
    Fix encoding artifacts in text.

    Args:
        text: Original text with potential encoding issues

    Returns:
        Tuple of (cleaned_text, num_fixes_applied)

    Example:
        >>> clean_text("Whatâ€™s the best treatment?")
        ("What's the best treatment?", 1)
    """
    if not text:
        return text, 0

    cleaned = text
    num_fixes = 0

    for artifact, replacement in ENCODING_FIXES.items():
        if artifact in cleaned:
            count = cleaned.count(artifact)
            cleaned = cleaned.replace(artifact, replacement)
            num_fixes += count

    return cleaned, num_fixes


def clean_question(question: Dict) -> Tuple[Dict, int]:
    """
    Clean encoding artifacts in all text fields of a question.

    Args:
        question: Question dict with stem, options, correct_answer, etc.

    Returns:
        Tuple of (cleaned_question, total_fixes)

    Example:
        >>> q = {"stem": "Whatâ€™s best?", "options": ["Aâ€"B", "C"]}
        >>> clean_q, fixes = clean_question(q)
        >>> clean_q["stem"]
        "What's best?"
        >>> fixes
        2
    """
    cleaned = question.copy()
    total_fixes = 0

    # Clean question stem
    if "stem" in cleaned and cleaned["stem"]:
        cleaned["stem"], stem_fixes = clean_text(cleaned["stem"])
        total_fixes += stem_fixes

    # Clean options (list or dict)
    if "options" in cleaned:
        if isinstance(cleaned["options"], list):
            cleaned_options = []
            for opt in cleaned["options"]:
                if isinstance(opt, str):
                    cleaned_opt, opt_fixes = clean_text(opt)
                    cleaned_options.append(cleaned_opt)
                    total_fixes += opt_fixes
                else:
                    cleaned_options.append(opt)
            cleaned["options"] = cleaned_options

        elif isinstance(cleaned["options"], dict):
            cleaned_options = {}
            for key, value in cleaned["options"].items():
                if isinstance(value, str):
                    cleaned_value, val_fixes = clean_text(value)
                    cleaned_options[key] = cleaned_value
                    total_fixes += val_fixes
                else:
                    cleaned_options[key] = value
            cleaned["options"] = cleaned_options

    # Clean correct answer
    if "correct_answer" in cleaned and isinstance(cleaned["correct_answer"], str):
        cleaned["correct_answer"], ans_fixes = clean_text(cleaned["correct_answer"])
        total_fixes += ans_fixes

    # Clean rationale/explanation (if present)
    if "rationale" in cleaned and isinstance(cleaned["rationale"], str):
        cleaned["rationale"], rat_fixes = clean_text(cleaned["rationale"])
        total_fixes += rat_fixes

    return cleaned, total_fixes


def clean_all_questions(questions: List[Dict], show_stats: bool = True) -> Tuple[List[Dict], Dict]:
    """
    Clean encoding artifacts in all questions.

    Args:
        questions: List of question dicts
        show_stats: Whether to log statistics

    Returns:
        Tuple of (cleaned_questions, stats_dict)

    Example:
        >>> questions = [{"stem": "Whatâ€™s A?"}, {"stem": "Whatâ€™s B?"}]
        >>> cleaned, stats = clean_all_questions(questions)
        >>> stats["questions_with_issues"]
        2
        >>> stats["total_fixes"]
        2
    """
    cleaned_questions = []
    questions_with_issues = 0
    total_fixes = 0
    artifact_counts = {artifact: 0 for artifact in ENCODING_FIXES.keys()}

    for question in questions:
        cleaned, num_fixes = clean_question(question)
        cleaned_questions.append(cleaned)

        if num_fixes > 0:
            questions_with_issues += 1
            total_fixes += num_fixes

            # Count each artifact type
            for artifact in ENCODING_FIXES.keys():
                original_text = str(question)
                artifact_counts[artifact] += original_text.count(artifact)

    stats = {
        "total_questions": len(questions),
        "questions_with_issues": questions_with_issues,
        "questions_clean": len(questions) - questions_with_issues,
        "total_fixes": total_fixes,
        "artifact_counts": {
            artifact: count
            for artifact, count in artifact_counts.items()
            if count > 0
        }
    }

    if show_stats:
        logger.info(
            f"Cleaned {stats['total_questions']} questions: "
            f"{stats['questions_with_issues']} had issues, "
            f"{stats['total_fixes']} fixes applied"
        )
        if stats["artifact_counts"]:
            logger.info(f"Most common artifacts: {stats['artifact_counts']}")

    return cleaned_questions, stats


def detect_encoding_issues(text: str) -> List[str]:
    """
    Detect encoding artifacts in text without fixing them.

    Useful for validation and reporting.

    Args:
        text: Text to check

    Returns:
        List of detected artifacts

    Example:
        >>> detect_encoding_issues("Whatâ€™s the â€œbestâ€ treatment?")
        ["â€™", "â€œ", "â€"]
    """
    if not text:
        return []

    detected = []
    for artifact in ENCODING_FIXES.keys():
        if artifact in text:
            detected.append(artifact)

    return detected


def get_encoding_quality_score(question: Dict) -> float:
    """
    Score question encoding quality (0.0 = many issues, 1.0 = clean).

    Used in canonicalization to prefer clean versions.

    Args:
        question: Question dict

    Returns:
        Quality score between 0.0 and 1.0

    Example:
        >>> q1 = {"stem": "What's the best treatment?"}
        >>> get_encoding_quality_score(q1)
        1.0
        >>> q2 = {"stem": "Whatâ€™s the â€œbestâ€ treatment?"}
        >>> get_encoding_quality_score(q2)
        0.85
    """
    # Combine all text fields
    text_parts = []

    if "stem" in question and question["stem"]:
        text_parts.append(question["stem"])

    if "options" in question:
        if isinstance(question["options"], list):
            text_parts.extend([str(opt) for opt in question["options"]])
        elif isinstance(question["options"], dict):
            text_parts.extend([str(val) for val in question["options"].values()])

    if "correct_answer" in question and question["correct_answer"]:
        text_parts.append(str(question["correct_answer"]))

    combined_text = " ".join(text_parts)

    # Count artifacts
    total_chars = len(combined_text)
    if total_chars == 0:
        return 1.0

    artifact_chars = 0
    for artifact in ENCODING_FIXES.keys():
        artifact_chars += combined_text.count(artifact) * len(artifact)

    # Score: 1.0 - (artifact_proportion)
    # Penalize artifacts more heavily (multiply by 10 to make impact visible)
    penalty = min(1.0, (artifact_chars / total_chars) * 10)
    score = 1.0 - penalty

    return max(0.0, score)  # Ensure non-negative


def generate_cleanup_report(questions: List[Dict]) -> Dict:
    """
    Generate detailed report of encoding issues across questions.

    Args:
        questions: List of question dicts

    Returns:
        Report dict with statistics and examples

    Example:
        >>> questions = [{"stem": "Whatâ€™s A?"}, {"stem": "Clean question"}]
        >>> report = generate_cleanup_report(questions)
        >>> report["questions_with_issues"]
        1
        >>> "â€™" in report["artifacts_found"]
        True
    """
    questions_with_issues = []
    artifact_examples = {}
    artifact_counts = {artifact: 0 for artifact in ENCODING_FIXES.keys()}

    for i, question in enumerate(questions):
        qid = question.get("id", f"index_{i}")
        issues = detect_encoding_issues(str(question))

        if issues:
            questions_with_issues.append({
                "id": qid,
                "issues": issues,
                "stem_preview": question.get("stem", "")[:100]
            })

            for artifact in issues:
                artifact_counts[artifact] += 1

                # Save first 3 examples of each artifact type
                if artifact not in artifact_examples:
                    artifact_examples[artifact] = []

                if len(artifact_examples[artifact]) < 3:
                    artifact_examples[artifact].append({
                        "question_id": qid,
                        "preview": question.get("stem", "")[:100]
                    })

    return {
        "total_questions": len(questions),
        "questions_with_issues": len(questions_with_issues),
        "questions_clean": len(questions) - len(questions_with_issues),
        "artifact_counts": {k: v for k, v in artifact_counts.items() if v > 0},
        "artifacts_found": list(artifact_examples.keys()),
        "artifact_examples": artifact_examples,
        "sample_issues": questions_with_issues[:10]  # First 10 examples
    }
