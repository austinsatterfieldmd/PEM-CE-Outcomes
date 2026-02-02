"""
Unit tests for computed fields extraction.

Tests the extraction of:
- answer_option_count: Number of answer options (2-5)
- correct_answer_position: Position of correct answer (A-E)

These fields are derived from raw data, not LLM-tagged.
"""

import pytest
import pandas as pd
from src.core.preprocessing.computed_fields import (
    extract_answer_option_count,
    extract_correct_answer_position,
    add_computed_fields,
    validate_computed_fields,
)


class TestExtractAnswerOptionCount:
    """Tests for extract_answer_option_count function."""

    def test_five_options(self):
        """Test counting 5 answer options."""
        row = pd.Series({
            'Answer A': 'Option A text',
            'Answer B': 'Option B text',
            'Answer C': 'Option C text',
            'Answer D': 'Option D text',
            'Answer E': 'Option E text',
        })
        assert extract_answer_option_count(row) == 5

    def test_four_options(self):
        """Test counting 4 answer options (E is empty)."""
        row = pd.Series({
            'Answer A': 'Option A text',
            'Answer B': 'Option B text',
            'Answer C': 'Option C text',
            'Answer D': 'Option D text',
            'Answer E': None,
        })
        assert extract_answer_option_count(row) == 4

    def test_three_options(self):
        """Test counting 3 answer options."""
        row = pd.Series({
            'Answer A': 'Option A text',
            'Answer B': 'Option B text',
            'Answer C': 'Option C text',
            'Answer D': None,
            'Answer E': None,
        })
        assert extract_answer_option_count(row) == 3

    def test_two_options(self):
        """Test counting 2 answer options (True/False style)."""
        row = pd.Series({
            'Answer A': 'True',
            'Answer B': 'False',
            'Answer C': None,
            'Answer D': None,
            'Answer E': None,
        })
        assert extract_answer_option_count(row) == 2

    def test_empty_string_not_counted(self):
        """Test that empty strings are not counted as options."""
        row = pd.Series({
            'Answer A': 'Option A text',
            'Answer B': 'Option B text',
            'Answer C': '',
            'Answer D': '   ',  # Whitespace only
            'Answer E': None,
        })
        assert extract_answer_option_count(row) == 2

    def test_lowercase_column_names(self):
        """Test with lowercase column names."""
        row = pd.Series({
            'answer_a': 'Option A text',
            'answer_b': 'Option B text',
            'answer_c': 'Option C text',
            'answer_d': None,
            'answer_e': None,
        })
        assert extract_answer_option_count(row) == 3

    def test_simple_letter_columns(self):
        """Test with simple letter column names (A, B, C, D, E)."""
        row = pd.Series({
            'A': 'Option A text',
            'B': 'Option B text',
            'C': 'Option C text',
            'D': 'Option D text',
            'E': None,
        })
        assert extract_answer_option_count(row) == 4

    def test_no_answer_columns(self):
        """Test with no recognizable answer columns."""
        row = pd.Series({
            'question': 'What is the answer?',
            'topic': 'Treatment selection',
        })
        assert extract_answer_option_count(row) == 0


class TestExtractCorrectAnswerPosition:
    """Tests for extract_correct_answer_position function."""

    def test_simple_letter(self):
        """Test extracting simple letter answer (A, B, C, D, E)."""
        row = pd.Series({'Correct Answer': 'A'})
        assert extract_correct_answer_position(row) == 'A'

        row = pd.Series({'Correct Answer': 'B'})
        assert extract_correct_answer_position(row) == 'B'

        row = pd.Series({'Correct Answer': 'E'})
        assert extract_correct_answer_position(row) == 'E'

    def test_lowercase_letter(self):
        """Test extracting lowercase letter answer."""
        row = pd.Series({'Correct Answer': 'c'})
        assert extract_correct_answer_position(row) == 'C'

    def test_letter_with_period(self):
        """Test extracting letter with period (A., B., etc.)."""
        row = pd.Series({'Correct Answer': 'D.'})
        assert extract_correct_answer_position(row) == 'D'

    def test_letter_with_parenthesis(self):
        """Test extracting letter with parenthesis (A), (B), etc.)."""
        row = pd.Series({'Correct Answer': '(B)'})
        assert extract_correct_answer_position(row) == 'B'

        row = pd.Series({'Correct Answer': 'C)'})
        assert extract_correct_answer_position(row) == 'C'

    def test_full_answer_text(self):
        """Test extracting from full answer text starting with letter."""
        row = pd.Series({'Correct Answer': 'A. Pembrolizumab'})
        assert extract_correct_answer_position(row) == 'A'

    def test_alternative_column_names(self):
        """Test with alternative column names."""
        row = pd.Series({'correct_answer': 'B'})
        assert extract_correct_answer_position(row) == 'B'

        row = pd.Series({'Key': 'C'})
        assert extract_correct_answer_position(row) == 'C'

    def test_missing_correct_answer(self):
        """Test with missing correct answer column."""
        row = pd.Series({'question': 'What is the answer?'})
        assert extract_correct_answer_position(row) is None

    def test_null_correct_answer(self):
        """Test with null correct answer value."""
        row = pd.Series({'Correct Answer': None})
        assert extract_correct_answer_position(row) is None

    def test_invalid_answer_format(self):
        """Test with invalid answer format."""
        row = pd.Series({'Correct Answer': 'Invalid'})
        assert extract_correct_answer_position(row) is None

        row = pd.Series({'Correct Answer': '123'})
        assert extract_correct_answer_position(row) is None

    def test_whitespace_handling(self):
        """Test handling of whitespace."""
        row = pd.Series({'Correct Answer': '  A  '})
        assert extract_correct_answer_position(row) == 'A'


class TestAddComputedFields:
    """Tests for add_computed_fields function."""

    def test_adds_both_columns(self):
        """Test that both computed columns are added."""
        df = pd.DataFrame({
            'question': ['Q1', 'Q2'],
            'Answer A': ['A1', 'A2'],
            'Answer B': ['B1', 'B2'],
            'Answer C': ['C1', None],
            'Answer D': [None, None],
            'Answer E': [None, None],
            'Correct Answer': ['A', 'B'],
        })

        result = add_computed_fields(df)

        assert 'answer_option_count' in result.columns
        assert 'correct_answer_position' in result.columns

    def test_correct_values_assigned(self):
        """Test that correct values are assigned."""
        df = pd.DataFrame({
            'question': ['Q1', 'Q2'],
            'Answer A': ['A1', 'A2'],
            'Answer B': ['B1', 'B2'],
            'Answer C': ['C1', 'C2'],
            'Answer D': ['D1', None],
            'Answer E': [None, None],
            'Correct Answer': ['C', 'A'],
        })

        result = add_computed_fields(df)

        assert result.iloc[0]['answer_option_count'] == 4
        assert result.iloc[1]['answer_option_count'] == 3
        assert result.iloc[0]['correct_answer_position'] == 'C'
        assert result.iloc[1]['correct_answer_position'] == 'A'

    def test_original_dataframe_unchanged(self):
        """Test that original dataframe is not modified."""
        df = pd.DataFrame({
            'question': ['Q1'],
            'Answer A': ['A1'],
            'Answer B': ['B1'],
            'Correct Answer': ['A'],
        })
        original_cols = list(df.columns)

        add_computed_fields(df)

        assert list(df.columns) == original_cols


class TestValidateComputedFields:
    """Tests for validate_computed_fields function."""

    def test_returns_metrics_dict(self):
        """Test that validation returns metrics dictionary."""
        df = pd.DataFrame({
            'answer_option_count': [4, 4, 5, 3],
            'correct_answer_position': ['A', 'B', 'C', 'D'],
        })

        metrics = validate_computed_fields(df)

        assert 'total_rows' in metrics
        assert 'answer_count_missing' in metrics
        assert 'correct_position_missing' in metrics
        assert 'answer_count_distribution' in metrics
        assert 'position_distribution' in metrics

    def test_counts_missing_values(self):
        """Test counting of missing values."""
        df = pd.DataFrame({
            'answer_option_count': [4, 0, 5, 0],  # 2 missing (0 count)
            'correct_answer_position': ['A', None, 'C', None],  # 2 missing
        })

        metrics = validate_computed_fields(df)

        assert metrics['total_rows'] == 4
        assert metrics['answer_count_missing'] == 2
        assert metrics['correct_position_missing'] == 2

    def test_distribution_counts(self):
        """Test distribution counting."""
        df = pd.DataFrame({
            'answer_option_count': [4, 4, 5, 5, 5],
            'correct_answer_position': ['A', 'A', 'B', 'C', 'C'],
        })

        metrics = validate_computed_fields(df)

        assert metrics['answer_count_distribution'] == {4: 2, 5: 3}
        assert metrics['position_distribution'] == {'A': 2, 'B': 1, 'C': 2}


class TestComputedFieldsIntegration:
    """Integration tests for computed fields."""

    def test_typical_question_data(self):
        """Test with typical question data structure."""
        df = pd.DataFrame({
            'question_stem': [
                'A 65-year-old patient with NSCLC...',
                'Which treatment is preferred for HER2+ breast cancer?',
                'A patient presents with symptoms...',
            ],
            'Answer A': ['Pembrolizumab', 'Trastuzumab deruxtecan', 'True'],
            'Answer B': ['Osimertinib', 'Pertuzumab', 'False'],
            'Answer C': ['Carboplatin', 'Lapatinib', None],
            'Answer D': ['Docetaxel', 'Capecitabine', None],
            'Answer E': [None, None, None],
            'Correct Answer': ['B', 'A', 'A'],
        })

        result = add_computed_fields(df)

        # Verify counts
        assert list(result['answer_option_count']) == [4, 4, 2]
        assert list(result['correct_answer_position']) == ['B', 'A', 'A']

        # Validate
        metrics = validate_computed_fields(result)
        assert metrics['answer_count_missing'] == 0
        assert metrics['correct_position_missing'] == 0
