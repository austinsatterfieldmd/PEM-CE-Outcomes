"""
QCore Score Calculator - Question Quality Assessment (0-100)

Part of the Q-Suite:
- QCore: Quality scoring (QC + score = QCore) - flaw deductions, structure penalties
- QScan: Similar question finder
- QBoost: LLM accuracy + LO alignment + suggestions

Calculates a quality score based on:
1. Item writing flaw deductions (data-driven, calibrated from historical performance)
2. Structure-based deductions (heterogeneous distractors, answer length patterns)

Two grading scales:
- Level 3 (Knowledge): More lenient thresholds
- Level 4 (Competence): Stricter thresholds

Usage:
    from src.core.preprocessing.qcore_scorer import calculate_qcore_score
    result = calculate_qcore_score(tags, cme_level=4)
    print(f"Score: {result['total_score']}, Grade: {result['grade']}")
"""
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class CMELevel(Enum):
    """CME outcome levels (Moore's framework)."""
    LEVEL_3_KNOWLEDGE = 3
    LEVEL_4_COMPETENCE = 4


@dataclass
class QCoreConfig:
    """Configuration for QCore scoring weights.

    Expert default penalties based on psychometric research (Haladyna et al., Case & Swanson).
    These will be refined as performance data accumulates.
    """

    # Flaw penalties (L3 / L4)
    # Tier 2: -12 L4 / -8 L3
    # Tier 3: -10 L4 / -6 L3
    # Tier 4: -8 L4 / -5 L3
    FLAW_PENALTIES = {
        'flaw_grammatical_cue': {'L3': 8, 'L4': 12},           # Tier 2: Strong test-wiseness cue
        'flaw_implausible_distractor': {'L3': 6, 'L4': 10},    # Tier 3: Reduces effective options (less severe if 4+ options)
        'flaw_clang_association': {'L3': 6, 'L4': 10},         # Tier 3: Word matching enables cueing
        'flaw_convergence_vulnerability': {'L3': 6, 'L4': 10}, # Tier 3: Elimination strategy bypass
        'flaw_absolute_terms': {'L3': 5, 'L4': 8},             # Tier 4: "Always/never" heuristic
        'flaw_double_negative': {'L3': 5, 'L4': 8},            # Tier 4: Cognitive load, not knowledge
    }

    # Structure-based deductions (L3 / L4)
    # Tier 1 (worst): -15 L4 / -10 L3 - Fundamentally flawed question formats
    # Tier 2: -12 L4 / -8 L3
    # Tier 3: -10 L4 / -6 L3
    # Tier 4: -8 L4 / -5 L3
    STRUCTURE_DEDUCTIONS = {
        'distractor_homogeneity': {
            'Heterogeneous': {'L3': 5, 'L4': 8},  # Tier 4: Mixed distractor types
        },
        'answer_length_pattern': {
            'Variable': {'L3': 2, 'L4': 4},               # Minor cue
            'Correct longest': {'L3': 8, 'L4': 12},       # Tier 2: Major test-wiseness vulnerability
            'Correct shortest': {'L3': 8, 'L4': 12},      # Tier 2: Major test-wiseness vulnerability
        },
        'answer_option_count': {
            2: {'L3': 10, 'L4': 15},  # Tier 1: Too few options (50% guess rate) - only if not True-False
            3: {'L3': 6, 'L4': 10},   # Tier 3: Few options (33% guess rate)
        },
        'data_response_type': {
            'Numeric': {'L3': 10, 'L4': 15},  # Tier 1: Numeric questions inappropriate for competence assessment
        },
        'answer_format': {
            'All of above': {'L3': 10, 'L4': 15},     # Tier 1: Test-wiseness vulnerability (pattern recognition)
            'None of above': {'L3': 10, 'L4': 15},    # Tier 1: Test-wiseness vulnerability (elimination strategy)
            'True-False': {'L3': 10, 'L4': 15},       # Tier 1: Binary format, high guess rate
            'Compound (A+B)': {'L3': 8, 'L4': 12},    # Tier 2: Reduces discrimination, complex scoring
        },
        'lead_in_type': {
            'Negative (EXCEPT/NOT)': {'L3': 10, 'L4': 15},  # Tier 1: Confusing, tests recall not application
        },
        'stem_type': {
            'Incomplete statement': {'L3': 4, 'L4': 6},  # "The mechanism of X is..." format - tests recall
        },
    }

    # Structure-based bonuses (L3 / L4)
    # NOTE: Bonuses removed - starting from 100 means 100 is the ideal baseline
    # Good structure is expected, not rewarded above baseline
    STRUCTURE_BONUSES = {
        # Empty - no bonuses, only deductions from 100
    }

    # Grade thresholds - unified scale for both L3 and L4 (traditional grading)
    # No F grade - D is the floor
    GRADE_THRESHOLDS = {
        'L3': {  # Level 3 (Knowledge) - same scale as L4
            'A': 90,
            'B': 80,
            'C': 70,
            'D': 0,  # D is the floor (no F grade)
        },
        'L4': {  # Level 4 (Competence) - same scale as L3
            'A': 90,
            'B': 80,
            'C': 70,
            'D': 0,  # D is the floor (no F grade)
        },
    }


# Backward compatibility alias
QBoostConfig = QCoreConfig


def _get_level_key(cme_level: int) -> str:
    """Convert CME level to config key."""
    return 'L4' if cme_level == 4 else 'L3'


def _normalize_bool(value: Any) -> bool:
    """Normalize various boolean representations to actual bool."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ('true', 'yes', '1', 't', 'y')
    if isinstance(value, (int, float)):
        return bool(value)
    return False


def _calculate_flaw_deductions(tags: Dict[str, Any], level_key: str, config: QCoreConfig) -> Dict[str, Any]:
    """Calculate deductions from item writing flaws."""
    total_deduction = 0
    breakdown = {}
    flaw_count = 0

    for flaw_field, penalties in config.FLAW_PENALTIES.items():
        flaw_value = tags.get(flaw_field)
        is_flawed = _normalize_bool(flaw_value)

        if is_flawed:
            penalty = penalties[level_key]
            total_deduction += penalty
            breakdown[flaw_field] = -penalty
            flaw_count += 1
            logger.debug(f"Flaw detected: {flaw_field} = {flaw_value} -> -{penalty}")
        else:
            breakdown[flaw_field] = 0

    return {
        'total': total_deduction,
        'breakdown': breakdown,
        'flaw_count': flaw_count,
    }


def _calculate_structure_deductions(tags: Dict[str, Any], level_key: str, config: QCoreConfig) -> Dict[str, Any]:
    """Calculate deductions from structural issues."""
    total_deduction = 0
    breakdown = {}

    for field, value_penalties in config.STRUCTURE_DEDUCTIONS.items():
        field_value = tags.get(field)

        # Handle answer_option_count as integer
        if field == 'answer_option_count':
            try:
                field_value = int(field_value) if field_value is not None else None
            except (ValueError, TypeError):
                field_value = None

        if field_value in value_penalties:
            penalty = value_penalties[field_value][level_key]
            total_deduction += penalty
            breakdown[f"{field}:{field_value}"] = -penalty
            logger.debug(f"Structure deduction: {field}={field_value} -> -{penalty}")

    return {
        'total': total_deduction,
        'breakdown': breakdown,
    }


def _calculate_structure_bonuses(tags: Dict[str, Any], level_key: str, config: QCoreConfig) -> Dict[str, Any]:
    """Calculate bonuses from good structural choices."""
    total_bonus = 0
    breakdown = {}

    for field, value_bonuses in config.STRUCTURE_BONUSES.items():
        field_value = tags.get(field)

        if field_value in value_bonuses:
            bonus = value_bonuses[field_value][level_key]
            total_bonus += bonus
            breakdown[f"{field}:{field_value}"] = bonus
            logger.debug(f"Structure bonus: {field}={field_value} -> +{bonus}")

    return {
        'total': total_bonus,
        'breakdown': breakdown,
    }


def _determine_grade(score: float, level_key: str, config: QCoreConfig) -> str:
    """Determine letter grade based on score and level. D is the floor (no F grade)."""
    thresholds = config.GRADE_THRESHOLDS[level_key]

    for grade in ['A', 'B', 'C']:
        if score >= thresholds[grade]:
            return grade
    # D is the floor - any score below C threshold is D (no F grade)
    return 'D'


def _get_grade_interpretation(grade: str, level_key: str) -> str:
    """Get human-readable interpretation of grade."""
    interpretations = {
        'A': 'Excellent - ready for deployment',
        'B': 'Good - minor improvements suggested',
        'C': 'Fair - review recommended',
        'D': 'Needs work - revision required',  # D is now the floor
    }
    return interpretations.get(grade, 'Unknown')


def calculate_qcore_score(
    tags: Dict[str, Any],
    cme_level: int = 4,
    config: Optional[QCoreConfig] = None
) -> Dict[str, Any]:
    """
    Calculate QCore quality score for a question.

    Args:
        tags: Dictionary of tag values (from database or LLM output)
        cme_level: CME outcome level (3=Knowledge, 4=Competence). Default 4.
        config: Optional custom configuration. Uses defaults if not provided.

    Returns:
        Dict with:
        - total_score: Final score (0-100)
        - base_score: Starting score (100)
        - flaw_deductions: Total points lost from flaws
        - structure_deductions: Total points lost from structure issues
        - structure_bonuses: Total points gained from good structure
        - flaw_count: Number of flaws detected
        - grade: Letter grade (A-F)
        - grade_interpretation: Human-readable grade meaning
        - cme_level: The CME level used for grading
        - breakdown: Detailed breakdown of all adjustments
        - ready_for_deployment: True if grade is A or B

    Example:
        >>> tags = {
        ...     'flaw_implausible_distractor': True,
        ...     'flaw_absolute_terms': False,
        ...     'stem_type': 'Clinical vignette',
        ...     'answer_length_pattern': 'Uniform',
        ...     'distractor_homogeneity': 'Homogeneous',
        ... }
        >>> result = calculate_qcore_score(tags, cme_level=4)
        >>> print(f"Score: {result['total_score']}, Grade: {result['grade']}")
        Score: 78, Grade: B
    """
    if config is None:
        config = QCoreConfig()

    # Determine level key for config lookups
    level_key = _get_level_key(cme_level)

    # Start with base score
    base_score = 100

    # Calculate components
    flaw_result = _calculate_flaw_deductions(tags, level_key, config)
    structure_ded_result = _calculate_structure_deductions(tags, level_key, config)
    structure_bon_result = _calculate_structure_bonuses(tags, level_key, config)

    # Calculate total score
    total_score = base_score - flaw_result['total'] - structure_ded_result['total'] + structure_bon_result['total']

    # Clamp to 0-100 range
    total_score = max(0, min(100, total_score))

    # Determine grade
    grade = _determine_grade(total_score, level_key, config)

    # Combine all breakdowns
    combined_breakdown = {
        'flaws': flaw_result['breakdown'],
        'structure_deductions': structure_ded_result['breakdown'],
        'structure_bonuses': structure_bon_result['breakdown'],
    }

    return {
        'total_score': round(total_score, 1),
        'base_score': base_score,
        'flaw_deductions': -flaw_result['total'],
        'structure_deductions': -structure_ded_result['total'],
        'structure_bonuses': structure_bon_result['total'],
        'flaw_count': flaw_result['flaw_count'],
        'grade': grade,
        'grade_interpretation': _get_grade_interpretation(grade, level_key),
        'cme_level': cme_level,
        'level_description': 'Competence' if cme_level == 4 else 'Knowledge',
        'breakdown': combined_breakdown,
        'ready_for_deployment': grade in ('A', 'B'),
    }


# Backward compatibility alias
calculate_qboost_score = calculate_qcore_score


def calculate_batch_qcore_scores(
    questions: list[Dict[str, Any]],
    tags_key: str = 'tags',
    cme_level_key: str = 'cme_outcome_level',
    default_cme_level: int = 4,
) -> list[Dict[str, Any]]:
    """
    Calculate QCore scores for a batch of questions.

    Args:
        questions: List of question dicts
        tags_key: Key in question dict containing tags
        cme_level_key: Key in tags containing CME level
        default_cme_level: Default CME level if not specified

    Returns:
        List of QCore result dicts
    """
    results = []

    for q in questions:
        tags = q.get(tags_key, q)  # Use q directly if no tags_key

        # Extract CME level from tags
        cme_level = default_cme_level
        cme_value = tags.get(cme_level_key, '')
        if cme_value:
            if '4' in str(cme_value) or 'competence' in str(cme_value).lower():
                cme_level = 4
            elif '3' in str(cme_value) or 'knowledge' in str(cme_value).lower():
                cme_level = 3

        result = calculate_qcore_score(tags, cme_level=cme_level)
        result['question_id'] = q.get('id') or q.get('question_id') or q.get('source_id')
        results.append(result)

    return results


# Backward compatibility alias
calculate_batch_qboost_scores = calculate_batch_qcore_scores


def get_score_distribution(scores: list[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate distribution statistics for a batch of QCore scores.

    Args:
        scores: List of QCore result dicts

    Returns:
        Dict with distribution statistics
    """
    if not scores:
        return {'count': 0}

    total_scores = [s['total_score'] for s in scores]
    grades = [s['grade'] for s in scores]
    flaw_counts = [s['flaw_count'] for s in scores]

    grade_dist = {}
    for g in ['A', 'B', 'C', 'D']:  # No F grade
        grade_dist[g] = sum(1 for x in grades if x == g)

    return {
        'count': len(scores),
        'mean_score': round(sum(total_scores) / len(total_scores), 1),
        'min_score': min(total_scores),
        'max_score': max(total_scores),
        'grade_distribution': grade_dist,
        'mean_flaw_count': round(sum(flaw_counts) / len(flaw_counts), 2),
        'ready_for_deployment_count': sum(1 for s in scores if s['ready_for_deployment']),
        'ready_for_deployment_pct': round(sum(1 for s in scores if s['ready_for_deployment']) / len(scores) * 100, 1),
    }
