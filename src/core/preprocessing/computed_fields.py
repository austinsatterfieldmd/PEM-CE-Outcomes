"""
Extract computed fields from raw question data.

These fields are derived from the source data, not LLM-tagged:
- answer_option_count: Number of answer options (2-5)
- correct_answer_position: Position of correct answer (A-E)

Usage:
    from src.core.preprocessing.computed_fields import add_computed_fields
    df = add_computed_fields(df)
"""
from typing import Optional
import pandas as pd
import logging

logger = logging.getLogger(__name__)


def extract_answer_option_count(row: pd.Series) -> int:
    """
    Count non-null answer options (A through E).

    Args:
        row: DataFrame row containing answer columns

    Returns:
        Number of answer options (0-5)
    """
    # Common column name patterns for answer options
    answer_col_patterns = [
        ['Answer A', 'Answer B', 'Answer C', 'Answer D', 'Answer E'],
        ['answer_a', 'answer_b', 'answer_c', 'answer_d', 'answer_e'],
        ['AnswerA', 'AnswerB', 'AnswerC', 'AnswerD', 'AnswerE'],
        ['A', 'B', 'C', 'D', 'E'],
        ['Option A', 'Option B', 'Option C', 'Option D', 'Option E'],
    ]

    for pattern in answer_col_patterns:
        count = 0
        found_any = False
        for col in pattern:
            if col in row.index:
                found_any = True
                if pd.notna(row[col]) and str(row[col]).strip():
                    count += 1
        if found_any:
            return count

    # Fallback: look for any columns containing 'answer' and A-E
    answer_cols = [c for c in row.index if 'answer' in c.lower() or 'option' in c.lower()]
    count = sum(1 for col in answer_cols if pd.notna(row[col]) and str(row[col]).strip())

    return count


def extract_correct_answer_position(row: pd.Series) -> Optional[str]:
    """
    Extract the correct answer position from the Correct Answer column.

    Args:
        row: DataFrame row containing correct answer column

    Returns:
        Position string ("A", "B", "C", "D", or "E") or None
    """
    # Common column name patterns for correct answer
    correct_answer_cols = [
        'Correct Answer',
        'correct_answer',
        'CorrectAnswer',
        'Correct',
        'Answer',
        'Key',
    ]

    for col in correct_answer_cols:
        if col in row.index and pd.notna(row[col]):
            answer = str(row[col]).strip().upper()
            # Handle various formats: "A", "A.", "A)", "(A)", etc.
            answer = answer.replace('.', '').replace(')', '').replace('(', '').strip()
            if answer in ['A', 'B', 'C', 'D', 'E']:
                return answer
            # Handle full answer text by extracting first letter
            if len(answer) > 0 and answer[0] in ['A', 'B', 'C', 'D', 'E']:
                return answer[0]

    return None


def add_computed_fields(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add computed fields to dataframe.

    Args:
        df: DataFrame with question data

    Returns:
        DataFrame with answer_option_count and correct_answer_position columns added
    """
    logger.info(f"Adding computed fields to {len(df)} rows")

    df = df.copy()

    df['answer_option_count'] = df.apply(extract_answer_option_count, axis=1)
    df['correct_answer_position'] = df.apply(extract_correct_answer_position, axis=1)

    # Log statistics
    option_counts = df['answer_option_count'].value_counts().sort_index()
    logger.info(f"Answer option counts: {option_counts.to_dict()}")

    position_counts = df['correct_answer_position'].value_counts().sort_index()
    logger.info(f"Correct answer positions: {position_counts.to_dict()}")

    return df


def validate_computed_fields(df: pd.DataFrame) -> dict:
    """
    Validate computed fields and return quality metrics.

    Args:
        df: DataFrame with computed fields

    Returns:
        Dict with validation metrics
    """
    metrics = {
        'total_rows': len(df),
        'answer_count_missing': int((df['answer_option_count'] == 0).sum()),
        'correct_position_missing': int(df['correct_answer_position'].isna().sum()),
        'answer_count_distribution': df['answer_option_count'].value_counts().to_dict(),
        'position_distribution': df['correct_answer_position'].value_counts().to_dict(),
    }

    # Check for unusual patterns
    if metrics['answer_count_missing'] > 0:
        logger.warning(f"{metrics['answer_count_missing']} rows have no answer options detected")

    if metrics['correct_position_missing'] > 0:
        logger.warning(f"{metrics['correct_position_missing']} rows have no correct answer position detected")

    # Check for position bias (correct answer should be roughly evenly distributed)
    if 'position_distribution' in metrics and metrics['position_distribution']:
        positions = metrics['position_distribution']
        total = sum(positions.values())
        for pos, count in positions.items():
            proportion = count / total if total > 0 else 0
            if proportion > 0.35:  # More than 35% in one position
                logger.warning(f"Potential position bias: {pos} has {proportion:.1%} of correct answers")

    return metrics
