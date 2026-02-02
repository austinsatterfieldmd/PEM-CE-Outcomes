"""
Fix encoding artifacts and formatting issues in question text.

Encoding issues from copy-paste and database migrations:
- â€™ → '
- â€œ → "
- â€ → "
- Ã© → é
- â€" → —

Formatting issues from OCR and data entry:
- Missing spaces after periods (treatment.The → treatment. The)
- Missing spaces after commas (cancer,which → cancer, which)
- Concatenated words (34-year-oldfemale → 34-year-old female)
- Multiple consecutive spaces
"""

import logging
import re
from typing import Dict, List, Tuple, Set

logger = logging.getLogger(__name__)


# Common encoding artifacts (sorted by frequency)
# These are UTF-8 bytes misinterpreted as Latin-1/Windows-1252
ENCODING_FIXES = {
    # Smart quotes and apostrophes (UTF-8 right single quote = E2 80 99)
    "\xe2\x80\x99": "'",      # ' (right single quote)
    "\xe2\x80\x98": "'",      # ' (left single quote)
    "\xe2\x80\x9c": '"',      # " (left double quote)
    "\xe2\x80\x9d": '"',      # " (right double quote)

    # Dashes and hyphens
    "\xe2\x80\x94": "\u2014",  # em dash
    "\xe2\x80\x93": "\u2013",  # en dash

    # Common accented characters (UTF-8 misread as Latin-1)
    "\xc3\xa9": "\u00e9",     # e with acute (e)
    "\xc3\xa8": "\u00e8",     # e with grave (e)
    "\xc3\xa0": "\u00e0",     # a with grave (a)
    "\xc3\xa1": "\u00e1",     # a with acute (a)
    "\xc3\xb3": "\u00f3",     # o with acute (o)
    "\xc3\xb1": "\u00f1",     # n with tilde (n)
    "\xc3\xbc": "\u00fc",     # u with umlaut (u)

    # Miscellaneous
    "\xe2\x80\xa6": "\u2026",  # ellipsis
    "\xc2": "",               # non-breaking space artifact
    "\xe2\x80\xa2": "\u2022",  # bullet point
}

# Common medical abbreviations to preserve (don't add space after period)
ABBREVIATIONS = {
    'dr.', 'mr.', 'ms.', 'mrs.', 'vs.', 'etc.', 'e.g.', 'i.e.',
    'approx.', 'avg.', 'est.', 'max.', 'min.', 'no.', 'vol.',
    'pt.', 'dx.', 'tx.', 'rx.', 'hx.', 'fx.', 'sx.',  # Medical
    'u.s.', 'u.k.', 'a.m.', 'p.m.',  # Common
    'ph.d.', 'm.d.', 'r.n.', 'n.p.', 'p.a.',  # Titles
    'inc.', 'ltd.', 'corp.',  # Business
}

# Common concatenated word patterns found in medical text
# Pattern: (word_ending, word_start) -> should have space between
CONCATENATION_PATTERNS = [
    # Age patterns: "34-year-oldfemale" -> "34-year-old female"
    (r'(\d+-year-old)([a-z])', r'\1 \2'),
    # Common medical concatenations
    (r'(female|male|patient|woman|man)(presents|with|who|has|is|was|diagnosed)', r'\1 \2'),
    (r'(metastatic|advanced|stage|grade)(breast|lung|colon|renal|prostate)', r'\1 \2'),
    (r'(breast|lung|colon|renal|prostate)(cancer|carcinoma|adenocarcinoma)', r'\1 \2'),
    # Question transitions: "mutations.How" -> "mutations. How"
    (r'(\w+)\.(How|What|Which|When|Where|Who|Why|Is|Are|Does|Do|Can|Should|Would|Could|Based|The|A|An|In|On|At|For|After|Before|During|Following|Given|This|These|Her|His|She|He|It|They)', r'\1. \2'),
    # Sentence endings into new sentences
    (r'(\w+)\.(She|He|It|They|The|A|An|This|These|Her|His|Patient|Treatment|Therapy|Based|Following|Given|After)', r'\1. \2'),
]

# Words that commonly appear concatenated (lowercase -> proper form)
KNOWN_CONCATENATIONS = {
    'totalurinary': 'total urinary',
    'hasigan': 'has IgAN',
    'hissystolic': 'his systolic',
    'hersystolic': 'her systolic',
    'adaactivity': 'ADA activity',
    'howmuch': 'How much',
    'gmg': 'gMG',  # Generalized myasthenia gravis
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


def fix_missing_spaces(text: str) -> Tuple[str, int]:
    """
    Fix missing spaces after punctuation marks.

    Handles:
    - Period followed by capital letter (not abbreviations)
    - Comma followed by letter
    - Colon followed by letter (not in time format)
    - Semicolon followed by letter

    Args:
        text: Text to fix

    Returns:
        Tuple of (fixed_text, num_fixes)

    Example:
        >>> fix_missing_spaces("treatment.The patient")
        ("treatment. The patient", 1)
    """
    if not text:
        return text, 0

    fixed = text
    num_fixes = 0

    # Fix period + capital (but not abbreviations or decimals)
    # Match: lowercase/digit + period + uppercase letter starting a word
    def fix_period(match):
        nonlocal num_fixes
        # Check if this is an abbreviation
        word_before = match.group(1).lower()
        if word_before + '.' in ABBREVIATIONS:
            return match.group(0)
        num_fixes += 1
        return match.group(1) + '. ' + match.group(2)

    # Pattern: word ending + period + capital letter
    fixed = re.sub(r'(\w)\.([A-Z][a-z])', fix_period, fixed)

    # Fix comma + letter (not in numbers like 1,000)
    def fix_comma(match):
        nonlocal num_fixes
        before = match.group(1)
        after = match.group(2)
        # Don't fix if it's a number pattern
        if before.isdigit() and after.isdigit():
            return match.group(0)
        num_fixes += 1
        return before + ', ' + after

    fixed = re.sub(r'(\w),([A-Za-z])', fix_comma, fixed)

    # Fix colon + letter (not in time like 10:30 or ratios)
    def fix_colon(match):
        nonlocal num_fixes
        before = match.group(1)
        after = match.group(2)
        # Don't fix time patterns or ratios
        if before.isdigit():
            return match.group(0)
        num_fixes += 1
        return before + ': ' + after

    fixed = re.sub(r'(\w):([A-Za-z])', fix_colon, fixed)

    # Fix semicolon + letter
    old_len = len(fixed)
    fixed = re.sub(r'(\w);([A-Za-z])', r'\1; \2', fixed)
    if len(fixed) > old_len:
        num_fixes += (len(fixed) - old_len) // 2

    return fixed, num_fixes


def fix_concatenated_words(text: str) -> Tuple[str, int]:
    """
    Fix concatenated words using pattern matching.

    Handles:
    - Age patterns: "34-year-oldfemale" -> "34-year-old female"
    - Medical patterns: "breastcancer" -> "breast cancer"
    - Known concatenations from KNOWN_CONCATENATIONS dict

    Args:
        text: Text to fix

    Returns:
        Tuple of (fixed_text, num_fixes)

    Example:
        >>> fix_concatenated_words("A 34-year-oldfemale presents")
        ("A 34-year-old female presents", 1)
    """
    if not text:
        return text, 0

    fixed = text
    num_fixes = 0

    # Apply known concatenation fixes (case-insensitive)
    text_lower = fixed.lower()
    for concat, replacement in KNOWN_CONCATENATIONS.items():
        if concat in text_lower:
            # Find all occurrences and replace preserving case of replacement
            pattern = re.compile(re.escape(concat), re.IGNORECASE)
            matches = pattern.findall(fixed)
            if matches:
                fixed = pattern.sub(replacement, fixed)
                num_fixes += len(matches)

    # Apply regex patterns for common concatenations
    for pattern, replacement in CONCATENATION_PATTERNS:
        old_fixed = fixed
        fixed = re.sub(pattern, replacement, fixed, flags=re.IGNORECASE)
        if fixed != old_fixed:
            num_fixes += 1

    return fixed, num_fixes


def normalize_whitespace(text: str) -> Tuple[str, int]:
    """
    Normalize whitespace: multiple spaces -> single space, trim.

    Args:
        text: Text to normalize

    Returns:
        Tuple of (normalized_text, num_fixes)

    Example:
        >>> normalize_whitespace("The  patient   has")
        ("The patient has", 2)
    """
    if not text:
        return text, 0

    # Count multiple space occurrences
    num_fixes = len(re.findall(r'  +', text))

    # Replace multiple spaces with single space
    normalized = re.sub(r'  +', ' ', text)

    # Trim leading/trailing whitespace
    normalized = normalized.strip()

    return normalized, num_fixes


def clean_formatting(text: str) -> Tuple[str, Dict[str, int]]:
    """
    Apply all formatting fixes to text.

    Applies in order:
    1. Fix missing spaces after punctuation
    2. Fix concatenated words
    3. Normalize whitespace

    Args:
        text: Text to clean

    Returns:
        Tuple of (cleaned_text, fix_counts_by_type)

    Example:
        >>> clean_formatting("A 34-year-oldfemale.She has  cancer")
        ("A 34-year-old female. She has cancer", {...})
    """
    if not text:
        return text, {}

    fix_counts = {}

    # Apply fixes in order
    text, count = fix_missing_spaces(text)
    if count > 0:
        fix_counts['missing_spaces'] = count

    text, count = fix_concatenated_words(text)
    if count > 0:
        fix_counts['concatenated_words'] = count

    text, count = normalize_whitespace(text)
    if count > 0:
        fix_counts['whitespace'] = count

    return text, fix_counts


def clean_text_full(text: str) -> Tuple[str, Dict[str, int]]:
    """
    Apply both encoding and formatting fixes to text.

    This is the comprehensive cleaning function that should be used
    for most text cleanup operations.

    Args:
        text: Text to clean

    Returns:
        Tuple of (cleaned_text, fix_counts_by_type)

    Example:
        >>> clean_text_full("Whatâ€™s the treatment.The patient")
        ("What's the treatment. The patient", {'encoding': 1, 'missing_spaces': 1})
    """
    if not text:
        return text, {}

    fix_counts = {}

    # First fix encoding issues
    text, encoding_fixes = clean_text(text)
    if encoding_fixes > 0:
        fix_counts['encoding'] = encoding_fixes

    # Then fix formatting issues
    text, formatting_fixes = clean_formatting(text)
    fix_counts.update(formatting_fixes)

    return text, fix_counts


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


def clean_question_full(question: Dict) -> Tuple[Dict, Dict[str, int]]:
    """
    Apply both encoding and formatting fixes to all text fields of a question.

    This is the comprehensive question cleaning function.

    Args:
        question: Question dict with stem, options, correct_answer, etc.

    Returns:
        Tuple of (cleaned_question, fix_counts_by_field)

    Example:
        >>> q = {"stem": "A 34-year-oldfemale.She has cancer"}
        >>> clean_q, fixes = clean_question_full(q)
        >>> clean_q["stem"]
        "A 34-year-old female. She has cancer"
    """
    cleaned = question.copy()
    fix_counts = {}

    # Clean question stem
    if "stem" in cleaned and cleaned["stem"]:
        cleaned["stem"], stem_fixes = clean_text_full(cleaned["stem"])
        if stem_fixes:
            fix_counts['stem'] = stem_fixes

    # Clean options (list or dict)
    if "options" in cleaned:
        options_fixes = {}
        if isinstance(cleaned["options"], list):
            cleaned_options = []
            for i, opt in enumerate(cleaned["options"]):
                if isinstance(opt, str):
                    cleaned_opt, opt_fixes = clean_text_full(opt)
                    cleaned_options.append(cleaned_opt)
                    if opt_fixes:
                        options_fixes[f'option_{i}'] = opt_fixes
                else:
                    cleaned_options.append(opt)
            cleaned["options"] = cleaned_options

        elif isinstance(cleaned["options"], dict):
            cleaned_options = {}
            for key, value in cleaned["options"].items():
                if isinstance(value, str):
                    cleaned_value, val_fixes = clean_text_full(value)
                    cleaned_options[key] = cleaned_value
                    if val_fixes:
                        options_fixes[f'option_{key}'] = val_fixes
                else:
                    cleaned_options[key] = value
            cleaned["options"] = cleaned_options

        if options_fixes:
            fix_counts['options'] = options_fixes

    # Clean correct answer
    if "correct_answer" in cleaned and isinstance(cleaned["correct_answer"], str):
        cleaned["correct_answer"], ans_fixes = clean_text_full(cleaned["correct_answer"])
        if ans_fixes:
            fix_counts['correct_answer'] = ans_fixes

    # Clean rationale/explanation (if present)
    if "rationale" in cleaned and isinstance(cleaned["rationale"], str):
        cleaned["rationale"], rat_fixes = clean_text_full(cleaned["rationale"])
        if rat_fixes:
            fix_counts['rationale'] = rat_fixes

    return cleaned, fix_counts


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


def detect_formatting_issues(text: str) -> Dict[str, List[str]]:
    """
    Detect formatting issues in text without fixing them.

    Useful for validation and reporting.

    Args:
        text: Text to check

    Returns:
        Dict of issue_type -> list of examples found

    Example:
        >>> detect_formatting_issues("treatment.The patient")
        {"missing_space_after_period": ["treatment."]}
    """
    if not text:
        return {}

    issues = {}

    # Missing space after period + capital
    matches = re.findall(r'(\w+)\.[A-Z][a-z]', text)
    valid_matches = [m for m in matches if m.lower() + '.' not in ABBREVIATIONS]
    if valid_matches:
        issues['missing_space_after_period'] = valid_matches

    # Missing space after comma + letter (not numbers)
    matches = re.findall(r'([a-zA-Z]+),([a-zA-Z])', text)
    if matches:
        issues['missing_space_after_comma'] = [f'{m[0]},' for m in matches]

    # Missing space after colon + letter (not time)
    matches = re.findall(r'([a-zA-Z]+):([a-zA-Z])', text)
    if matches:
        issues['missing_space_after_colon'] = [f'{m[0]}:' for m in matches]

    # Multiple spaces
    if '  ' in text:
        issues['multiple_spaces'] = ['(found)']

    # Potential concatenated words (lowercase followed by uppercase mid-word)
    concat_matches = re.findall(r'\b(\w*[a-z][A-Z]\w*)\b', text)
    # Filter out known patterns like HER2, PD-L1, etc.
    known_patterns = {'HER2', 'PD-L1', 'CDK4', 'BCL-2', 'mCRPC', 'mCRC', 'proBNP'}
    valid_concats = [m for m in concat_matches if not any(kp in m for kp in known_patterns)]
    if valid_concats:
        issues['possible_concatenated_words'] = valid_concats

    return issues


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


def get_formatting_quality_score(question: Dict) -> float:
    """
    Score question formatting quality (0.0 = many issues, 1.0 = clean).

    Considers:
    - Missing spaces after punctuation
    - Concatenated words
    - Multiple spaces

    Args:
        question: Question dict

    Returns:
        Quality score between 0.0 and 1.0

    Example:
        >>> q1 = {"stem": "What is the best treatment?"}
        >>> get_formatting_quality_score(q1)
        1.0
        >>> q2 = {"stem": "treatment.The patient has  cancer"}
        >>> get_formatting_quality_score(q2)
        0.8
    """
    # Combine all text fields
    text_parts = []

    if "stem" in question and question["stem"]:
        text_parts.append(str(question["stem"]))

    if "options" in question:
        if isinstance(question["options"], list):
            text_parts.extend([str(opt) for opt in question["options"]])
        elif isinstance(question["options"], dict):
            text_parts.extend([str(val) for val in question["options"].values()])

    if "correct_answer" in question and question["correct_answer"]:
        text_parts.append(str(question["correct_answer"]))

    combined_text = " ".join(text_parts)

    if not combined_text:
        return 1.0

    # Detect formatting issues
    issues = detect_formatting_issues(combined_text)

    # Count total issues
    total_issues = sum(len(v) for v in issues.values())

    if total_issues == 0:
        return 1.0

    # Penalize based on number of issues relative to text length
    # More lenient than encoding (formatting issues are less severe)
    penalty = min(0.5, total_issues * 0.05)  # Max 50% penalty
    score = 1.0 - penalty

    return max(0.0, score)


def get_overall_quality_score(question: Dict) -> float:
    """
    Get overall quality score combining encoding and formatting.

    Args:
        question: Question dict

    Returns:
        Combined quality score between 0.0 and 1.0

    Example:
        >>> q = {"stem": "What is the best treatment?"}
        >>> get_overall_quality_score(q)
        1.0
    """
    encoding_score = get_encoding_quality_score(question)
    formatting_score = get_formatting_quality_score(question)

    # Weight encoding slightly higher (encoding issues are more problematic)
    return encoding_score * 0.6 + formatting_score * 0.4


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
