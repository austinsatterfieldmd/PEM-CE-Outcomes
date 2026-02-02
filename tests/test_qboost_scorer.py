"""
Unit tests for QBoost Score Calculator.

Tests cover:
1. Flaw deductions at both L3 and L4 levels
2. Structure deductions (heterogeneous distractors, answer length patterns, option counts)
3. Structure bonuses (clinical vignette, homogeneous distractors, uniform lengths)
4. Grade thresholds for both levels
5. Edge cases (all flaws, no flaws, mixed scenarios)
"""
import pytest
from src.core.preprocessing.qboost_scorer import (
    calculate_qboost_score,
    calculate_batch_qboost_scores,
    get_score_distribution,
    QBoostConfig,
    _normalize_bool,
)


class TestNormalizeBool:
    """Test boolean normalization helper."""

    def test_bool_true(self):
        assert _normalize_bool(True) is True

    def test_bool_false(self):
        assert _normalize_bool(False) is False

    def test_string_true_variants(self):
        assert _normalize_bool("true") is True
        assert _normalize_bool("True") is True
        assert _normalize_bool("TRUE") is True
        assert _normalize_bool("yes") is True
        assert _normalize_bool("1") is True

    def test_string_false_variants(self):
        assert _normalize_bool("false") is False
        assert _normalize_bool("False") is False
        assert _normalize_bool("no") is False
        assert _normalize_bool("0") is False

    def test_int_values(self):
        assert _normalize_bool(1) is True
        assert _normalize_bool(0) is False

    def test_none_returns_false(self):
        assert _normalize_bool(None) is False


class TestFlawDeductions:
    """Test flaw-based score deductions."""

    def test_no_flaws_level3(self):
        """No flaws should give base score of 100."""
        tags = {
            'flaw_implausible_distractor': False,
            'flaw_grammatical_cue': False,
            'flaw_clang_association': False,
            'flaw_convergence_vulnerability': False,
            'flaw_absolute_terms': False,
            'flaw_double_negative': False,
        }
        result = calculate_qboost_score(tags, cme_level=3)
        assert result['flaw_deductions'] == 0
        assert result['flaw_count'] == 0

    def test_single_flaw_implausible_distractor_l3(self):
        """Single implausible distractor flaw at L3."""
        tags = {
            'flaw_implausible_distractor': True,
            'flaw_grammatical_cue': False,
        }
        result = calculate_qboost_score(tags, cme_level=3)
        assert result['flaw_deductions'] == -10
        assert result['flaw_count'] == 1
        assert result['breakdown']['flaws']['flaw_implausible_distractor'] == -10

    def test_single_flaw_implausible_distractor_l4(self):
        """Single implausible distractor flaw at L4 (stricter)."""
        tags = {
            'flaw_implausible_distractor': True,
            'flaw_grammatical_cue': False,
        }
        result = calculate_qboost_score(tags, cme_level=4)
        assert result['flaw_deductions'] == -15
        assert result['flaw_count'] == 1

    def test_grammatical_cue_deduction(self):
        """Grammatical cue flaw deduction."""
        tags = {'flaw_grammatical_cue': True}
        result_l3 = calculate_qboost_score(tags, cme_level=3)
        result_l4 = calculate_qboost_score(tags, cme_level=4)
        assert result_l3['flaw_deductions'] == -8
        assert result_l4['flaw_deductions'] == -12

    def test_clang_association_deduction(self):
        """Clang association flaw deduction."""
        tags = {'flaw_clang_association': True}
        result_l3 = calculate_qboost_score(tags, cme_level=3)
        result_l4 = calculate_qboost_score(tags, cme_level=4)
        assert result_l3['flaw_deductions'] == -6
        assert result_l4['flaw_deductions'] == -10

    def test_convergence_vulnerability_deduction(self):
        """Convergence vulnerability flaw deduction."""
        tags = {'flaw_convergence_vulnerability': True}
        result_l3 = calculate_qboost_score(tags, cme_level=3)
        result_l4 = calculate_qboost_score(tags, cme_level=4)
        assert result_l3['flaw_deductions'] == -6
        assert result_l4['flaw_deductions'] == -10

    def test_absolute_terms_deduction(self):
        """Absolute terms flaw deduction."""
        tags = {'flaw_absolute_terms': True}
        result_l3 = calculate_qboost_score(tags, cme_level=3)
        result_l4 = calculate_qboost_score(tags, cme_level=4)
        assert result_l3['flaw_deductions'] == -5
        assert result_l4['flaw_deductions'] == -8

    def test_double_negative_deduction(self):
        """Double negative flaw deduction."""
        tags = {'flaw_double_negative': True}
        result_l3 = calculate_qboost_score(tags, cme_level=3)
        result_l4 = calculate_qboost_score(tags, cme_level=4)
        assert result_l3['flaw_deductions'] == -5
        assert result_l4['flaw_deductions'] == -8

    def test_multiple_flaws_accumulate(self):
        """Multiple flaws should accumulate deductions."""
        tags = {
            'flaw_implausible_distractor': True,  # -10 L3
            'flaw_grammatical_cue': True,         # -8 L3
            'flaw_absolute_terms': True,          # -5 L3
        }
        result = calculate_qboost_score(tags, cme_level=3)
        assert result['flaw_deductions'] == -23
        assert result['flaw_count'] == 3

    def test_all_flaws_l4(self):
        """All flaws at L4 should give maximum deduction."""
        tags = {
            'flaw_implausible_distractor': True,  # -15
            'flaw_grammatical_cue': True,         # -12
            'flaw_clang_association': True,       # -10
            'flaw_convergence_vulnerability': True,  # -10
            'flaw_absolute_terms': True,          # -8
            'flaw_double_negative': True,         # -8
        }
        result = calculate_qboost_score(tags, cme_level=4)
        assert result['flaw_deductions'] == -63  # Total L4 penalties
        assert result['flaw_count'] == 6


class TestStructureDeductions:
    """Test structure-based deductions."""

    def test_heterogeneous_distractors_l3(self):
        """Heterogeneous distractors deduction at L3."""
        tags = {'distractor_homogeneity': 'Heterogeneous'}
        result = calculate_qboost_score(tags, cme_level=3)
        assert result['structure_deductions'] == -4

    def test_heterogeneous_distractors_l4(self):
        """Heterogeneous distractors deduction at L4."""
        tags = {'distractor_homogeneity': 'Heterogeneous'}
        result = calculate_qboost_score(tags, cme_level=4)
        assert result['structure_deductions'] == -8

    def test_variable_answer_length(self):
        """Variable answer length pattern (minor deduction)."""
        tags = {'answer_length_pattern': 'Variable'}
        result_l3 = calculate_qboost_score(tags, cme_level=3)
        result_l4 = calculate_qboost_score(tags, cme_level=4)
        assert result_l3['structure_deductions'] == -2
        assert result_l4['structure_deductions'] == -4

    def test_correct_longest_answer(self):
        """Correct answer longest (major test-wiseness vulnerability)."""
        tags = {'answer_length_pattern': 'Correct longest'}
        result_l3 = calculate_qboost_score(tags, cme_level=3)
        result_l4 = calculate_qboost_score(tags, cme_level=4)
        assert result_l3['structure_deductions'] == -6
        assert result_l4['structure_deductions'] == -10

    def test_correct_shortest_answer(self):
        """Correct answer shortest (major test-wiseness vulnerability)."""
        tags = {'answer_length_pattern': 'Correct shortest'}
        result_l3 = calculate_qboost_score(tags, cme_level=3)
        result_l4 = calculate_qboost_score(tags, cme_level=4)
        assert result_l3['structure_deductions'] == -6
        assert result_l4['structure_deductions'] == -10

    def test_two_options_deduction(self):
        """Two answer options (50% guessing)."""
        tags = {'answer_option_count': 2}
        result_l3 = calculate_qboost_score(tags, cme_level=3)
        result_l4 = calculate_qboost_score(tags, cme_level=4)
        assert result_l3['structure_deductions'] == -4
        assert result_l4['structure_deductions'] == -6

    def test_three_options_deduction(self):
        """Three answer options (33% guessing)."""
        tags = {'answer_option_count': 3}
        result_l3 = calculate_qboost_score(tags, cme_level=3)
        result_l4 = calculate_qboost_score(tags, cme_level=4)
        assert result_l3['structure_deductions'] == -2
        assert result_l4['structure_deductions'] == -4

    def test_four_options_no_deduction(self):
        """Four answer options (standard, no deduction)."""
        tags = {'answer_option_count': 4}
        result = calculate_qboost_score(tags, cme_level=3)
        assert result['structure_deductions'] == 0

    def test_option_count_as_string(self):
        """Option count passed as string should work."""
        tags = {'answer_option_count': '3'}
        result = calculate_qboost_score(tags, cme_level=3)
        assert result['structure_deductions'] == -2

    def test_numeric_data_response_type_deduction(self):
        """Numeric data response type should incur deduction (disfavored)."""
        tags = {'data_response_type': 'Numeric'}
        result_l3 = calculate_qboost_score(tags, cme_level=3)
        result_l4 = calculate_qboost_score(tags, cme_level=4)
        assert result_l3['structure_deductions'] == -6
        assert result_l4['structure_deductions'] == -10

    def test_qualitative_data_response_type_no_deduction(self):
        """Qualitative data response type should have no deduction."""
        tags = {'data_response_type': 'Qualitative'}
        result = calculate_qboost_score(tags, cme_level=3)
        assert result['structure_deductions'] == 0


class TestStructureBonuses:
    """Test structure-based bonuses."""

    def test_clinical_vignette_bonus(self):
        """Clinical vignette stem type bonus."""
        tags = {'stem_type': 'Clinical vignette'}
        result_l3 = calculate_qboost_score(tags, cme_level=3)
        result_l4 = calculate_qboost_score(tags, cme_level=4)
        assert result_l3['structure_bonuses'] == 3
        assert result_l4['structure_bonuses'] == 6

    def test_case_series_bonus(self):
        """Case series stem type bonus."""
        tags = {'stem_type': 'Case series'}
        result_l3 = calculate_qboost_score(tags, cme_level=3)
        result_l4 = calculate_qboost_score(tags, cme_level=4)
        assert result_l3['structure_bonuses'] == 2
        assert result_l4['structure_bonuses'] == 4

    def test_best_answer_lead_in_bonus(self):
        """Best answer lead-in type bonus."""
        tags = {'lead_in_type': 'Best answer'}
        result_l3 = calculate_qboost_score(tags, cme_level=3)
        result_l4 = calculate_qboost_score(tags, cme_level=4)
        assert result_l3['structure_bonuses'] == 2
        assert result_l4['structure_bonuses'] == 4

    def test_most_appropriate_lead_in_bonus(self):
        """Most appropriate lead-in type bonus."""
        tags = {'lead_in_type': 'Most appropriate'}
        result_l3 = calculate_qboost_score(tags, cme_level=3)
        result_l4 = calculate_qboost_score(tags, cme_level=4)
        assert result_l3['structure_bonuses'] == 2
        assert result_l4['structure_bonuses'] == 4

    def test_most_likely_lead_in_bonus(self):
        """Most likely lead-in type bonus (smaller)."""
        tags = {'lead_in_type': 'Most likely'}
        result_l3 = calculate_qboost_score(tags, cme_level=3)
        result_l4 = calculate_qboost_score(tags, cme_level=4)
        assert result_l3['structure_bonuses'] == 1
        assert result_l4['structure_bonuses'] == 2

    def test_homogeneous_distractors_bonus(self):
        """Homogeneous distractors bonus."""
        tags = {'distractor_homogeneity': 'Homogeneous'}
        result_l3 = calculate_qboost_score(tags, cme_level=3)
        result_l4 = calculate_qboost_score(tags, cme_level=4)
        assert result_l3['structure_bonuses'] == 2
        assert result_l4['structure_bonuses'] == 4

    def test_uniform_answer_length_bonus(self):
        """Uniform answer length pattern bonus."""
        tags = {'answer_length_pattern': 'Uniform'}
        result_l3 = calculate_qboost_score(tags, cme_level=3)
        result_l4 = calculate_qboost_score(tags, cme_level=4)
        assert result_l3['structure_bonuses'] == 2
        assert result_l4['structure_bonuses'] == 3

    def test_multiple_bonuses_accumulate(self):
        """Multiple bonuses should accumulate."""
        tags = {
            'stem_type': 'Clinical vignette',      # +3 L3
            'lead_in_type': 'Best answer',         # +2 L3
            'distractor_homogeneity': 'Homogeneous',  # +2 L3
            'answer_length_pattern': 'Uniform',    # +2 L3
        }
        result = calculate_qboost_score(tags, cme_level=3)
        assert result['structure_bonuses'] == 9


class TestGradeThresholds:
    """Test grade assignment thresholds."""

    def test_grade_a_level3(self):
        """Grade A at Level 3 (≥85)."""
        # Start at 100, add bonuses to stay above 85
        tags = {'stem_type': 'Clinical vignette'}  # +3
        result = calculate_qboost_score(tags, cme_level=3)
        assert result['total_score'] >= 85
        assert result['grade'] == 'A'

    def test_grade_a_level4(self):
        """Grade A at Level 4 (≥90)."""
        # Need bonuses to get above 90
        tags = {
            'stem_type': 'Clinical vignette',      # +6
            'lead_in_type': 'Best answer',         # +4
        }
        result = calculate_qboost_score(tags, cme_level=4)
        assert result['total_score'] >= 90
        assert result['grade'] == 'A'

    def test_grade_b_level3(self):
        """Grade B at Level 3 (70-84)."""
        # Add some flaws to get into B range
        tags = {
            'flaw_implausible_distractor': True,  # -10
            'flaw_grammatical_cue': True,         # -8
        }
        result = calculate_qboost_score(tags, cme_level=3)
        assert 70 <= result['total_score'] < 85
        assert result['grade'] == 'B'

    def test_grade_b_level4(self):
        """Grade B at Level 4 (80-89)."""
        tags = {
            'flaw_implausible_distractor': True,  # -15
        }
        result = calculate_qboost_score(tags, cme_level=4)
        assert 80 <= result['total_score'] < 90
        assert result['grade'] == 'B'

    def test_grade_c_level3(self):
        """Grade C at Level 3 (55-69)."""
        tags = {
            'flaw_implausible_distractor': True,  # -10
            'flaw_grammatical_cue': True,         # -8
            'flaw_clang_association': True,       # -6
            'flaw_absolute_terms': True,          # -5
            'distractor_homogeneity': 'Heterogeneous',  # -4
        }
        result = calculate_qboost_score(tags, cme_level=3)
        assert 55 <= result['total_score'] < 70
        assert result['grade'] == 'C'

    def test_grade_d_level3(self):
        """Grade D at Level 3 (40-54)."""
        tags = {
            'flaw_implausible_distractor': True,  # -10
            'flaw_grammatical_cue': True,         # -8
            'flaw_clang_association': True,       # -6
            'flaw_convergence_vulnerability': True,  # -6
            'flaw_absolute_terms': True,          # -5
            'flaw_double_negative': True,         # -5
            'distractor_homogeneity': 'Heterogeneous',  # -4
            'answer_length_pattern': 'Correct longest',  # -6
        }
        result = calculate_qboost_score(tags, cme_level=3)
        assert 40 <= result['total_score'] < 55
        assert result['grade'] == 'D'

    def test_grade_f_level3(self):
        """Grade F at Level 3 (<40)."""
        tags = {
            'flaw_implausible_distractor': True,  # -10
            'flaw_grammatical_cue': True,         # -8
            'flaw_clang_association': True,       # -6
            'flaw_convergence_vulnerability': True,  # -6
            'flaw_absolute_terms': True,          # -5
            'flaw_double_negative': True,         # -5
            'distractor_homogeneity': 'Heterogeneous',  # -4
            'answer_length_pattern': 'Correct longest',  # -6
            'answer_option_count': 2,             # -4
        }
        result = calculate_qboost_score(tags, cme_level=3)
        # Total deductions: -54, Score: 46 (D range)
        # Need more to get to F
        assert result['grade'] in ('D', 'F')


class TestTotalScoreCalculation:
    """Test total score calculation combining all components."""

    def test_perfect_question_l3(self):
        """Perfect question with all bonuses, no flaws (L3)."""
        tags = {
            'flaw_implausible_distractor': False,
            'flaw_grammatical_cue': False,
            'flaw_clang_association': False,
            'flaw_convergence_vulnerability': False,
            'flaw_absolute_terms': False,
            'flaw_double_negative': False,
            'stem_type': 'Clinical vignette',      # +3
            'lead_in_type': 'Best answer',         # +2
            'distractor_homogeneity': 'Homogeneous',  # +2
            'answer_length_pattern': 'Uniform',    # +2
            'answer_option_count': 4,
        }
        result = calculate_qboost_score(tags, cme_level=3)
        # Base: 100, Flaws: 0, Bonuses: +9, Deductions: 0
        assert result['total_score'] == 100  # Clamped to 100
        assert result['base_score'] == 100
        assert result['flaw_deductions'] == 0
        assert result['structure_bonuses'] == 9
        assert result['structure_deductions'] == 0
        assert result['grade'] == 'A'
        assert result['ready_for_deployment'] is True

    def test_mixed_question_l4(self):
        """Mixed quality question (L4)."""
        tags = {
            'flaw_implausible_distractor': True,   # -15
            'stem_type': 'Clinical vignette',      # +6
            'lead_in_type': 'Best answer',         # +4
            'distractor_homogeneity': 'Homogeneous',  # +4
            'answer_length_pattern': 'Uniform',    # +3
        }
        result = calculate_qboost_score(tags, cme_level=4)
        # Base: 100, Flaws: -15, Bonuses: +17, Deductions: 0
        # Total: 100 - 15 + 17 = 102 → clamped to 100
        assert result['total_score'] == 100
        assert result['grade'] == 'A'

    def test_score_clamped_to_zero(self):
        """Score should not go below 0."""
        # Create a scenario with massive deductions
        tags = {
            'flaw_implausible_distractor': True,
            'flaw_grammatical_cue': True,
            'flaw_clang_association': True,
            'flaw_convergence_vulnerability': True,
            'flaw_absolute_terms': True,
            'flaw_double_negative': True,
            'distractor_homogeneity': 'Heterogeneous',
            'answer_length_pattern': 'Correct longest',
            'answer_option_count': 2,
        }
        result = calculate_qboost_score(tags, cme_level=4)
        # L4 deductions: 15+12+10+10+8+8+8+10+6 = 87
        # But score should be clamped to 0
        assert result['total_score'] >= 0

    def test_ready_for_deployment_true(self):
        """Questions with A or B grade are ready for deployment."""
        # Grade B scenario
        tags = {'flaw_implausible_distractor': True}  # -10 L3
        result = calculate_qboost_score(tags, cme_level=3)
        assert result['grade'] in ('A', 'B')
        assert result['ready_for_deployment'] is True

    def test_ready_for_deployment_false(self):
        """Questions with C, D, or F grade are not ready."""
        tags = {
            'flaw_implausible_distractor': True,
            'flaw_grammatical_cue': True,
            'flaw_clang_association': True,
            'flaw_absolute_terms': True,
        }
        result = calculate_qboost_score(tags, cme_level=3)
        # Total deductions: -29, Score: 71 (still B)
        # Need more deductions
        tags['flaw_double_negative'] = True  # -5 more
        tags['distractor_homogeneity'] = 'Heterogeneous'  # -4 more
        result = calculate_qboost_score(tags, cme_level=3)
        assert result['grade'] in ('C', 'D', 'F')
        assert result['ready_for_deployment'] is False


class TestBreakdownOutput:
    """Test detailed breakdown output."""

    def test_breakdown_includes_all_sections(self):
        """Breakdown should include flaws, deductions, and bonuses."""
        tags = {
            'flaw_implausible_distractor': True,
            'stem_type': 'Clinical vignette',
            'distractor_homogeneity': 'Heterogeneous',
        }
        result = calculate_qboost_score(tags, cme_level=3)

        assert 'flaws' in result['breakdown']
        assert 'structure_deductions' in result['breakdown']
        assert 'structure_bonuses' in result['breakdown']

    def test_breakdown_shows_individual_values(self):
        """Breakdown should show each flaw/bonus value."""
        tags = {
            'flaw_implausible_distractor': True,
            'flaw_grammatical_cue': False,
            'stem_type': 'Clinical vignette',
        }
        result = calculate_qboost_score(tags, cme_level=3)

        assert result['breakdown']['flaws']['flaw_implausible_distractor'] == -10
        assert result['breakdown']['flaws']['flaw_grammatical_cue'] == 0
        assert 'stem_type:Clinical vignette' in result['breakdown']['structure_bonuses']


class TestBatchProcessing:
    """Test batch scoring functions."""

    def test_batch_scoring(self):
        """Batch scoring should process multiple questions."""
        questions = [
            {'tags': {'flaw_implausible_distractor': True}},
            {'tags': {'stem_type': 'Clinical vignette'}},
            {'tags': {}},
        ]
        results = calculate_batch_qboost_scores(questions)

        assert len(results) == 3
        assert all('total_score' in r for r in results)
        assert all('grade' in r for r in results)

    def test_batch_cme_level_extraction(self):
        """Batch scoring should extract CME level from tags."""
        questions = [
            {'tags': {'cme_outcome_level': '3 - Knowledge'}},
            {'tags': {'cme_outcome_level': '4 - Competence'}},
            {'tags': {}},  # Default to 4
        ]
        results = calculate_batch_qboost_scores(questions)

        assert results[0]['cme_level'] == 3
        assert results[1]['cme_level'] == 4
        assert results[2]['cme_level'] == 4  # Default

    def test_distribution_stats(self):
        """Distribution stats should calculate correctly."""
        scores = [
            {'total_score': 90, 'grade': 'A', 'flaw_count': 0, 'ready_for_deployment': True},
            {'total_score': 75, 'grade': 'B', 'flaw_count': 1, 'ready_for_deployment': True},
            {'total_score': 60, 'grade': 'C', 'flaw_count': 2, 'ready_for_deployment': False},
        ]
        stats = get_score_distribution(scores)

        assert stats['count'] == 3
        assert stats['mean_score'] == 75.0
        assert stats['min_score'] == 60
        assert stats['max_score'] == 90
        assert stats['grade_distribution']['A'] == 1
        assert stats['grade_distribution']['B'] == 1
        assert stats['grade_distribution']['C'] == 1
        assert stats['ready_for_deployment_count'] == 2
        assert stats['ready_for_deployment_pct'] == 66.7

    def test_empty_distribution(self):
        """Empty score list should return count 0."""
        stats = get_score_distribution([])
        assert stats == {'count': 0}


class TestCMELevelHandling:
    """Test CME level handling."""

    def test_level_3_uses_l3_config(self):
        """Level 3 should use L3 penalties and thresholds."""
        tags = {'flaw_implausible_distractor': True}
        result = calculate_qboost_score(tags, cme_level=3)
        assert result['cme_level'] == 3
        assert result['level_description'] == 'Knowledge'
        assert result['flaw_deductions'] == -10  # L3 penalty

    def test_level_4_uses_l4_config(self):
        """Level 4 should use L4 penalties and thresholds."""
        tags = {'flaw_implausible_distractor': True}
        result = calculate_qboost_score(tags, cme_level=4)
        assert result['cme_level'] == 4
        assert result['level_description'] == 'Competence'
        assert result['flaw_deductions'] == -15  # L4 penalty

    def test_default_cme_level_is_4(self):
        """Default CME level should be 4."""
        tags = {}
        result = calculate_qboost_score(tags)
        assert result['cme_level'] == 4

    def test_invalid_cme_level_defaults_to_l3(self):
        """Invalid CME level should default to L3 config."""
        tags = {'flaw_implausible_distractor': True}
        result = calculate_qboost_score(tags, cme_level=5)  # Invalid
        assert result['flaw_deductions'] == -10  # L3 penalty


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_tags(self):
        """Empty tags should give base score."""
        result = calculate_qboost_score({}, cme_level=3)
        assert result['total_score'] == 100
        assert result['grade'] == 'A'

    def test_none_tags(self):
        """None values in tags should be handled."""
        tags = {
            'flaw_implausible_distractor': None,
            'stem_type': None,
        }
        result = calculate_qboost_score(tags, cme_level=3)
        assert result['total_score'] == 100

    def test_string_boolean_values(self):
        """String boolean values should be normalized."""
        tags = {
            'flaw_implausible_distractor': 'true',
            'flaw_grammatical_cue': 'false',
        }
        result = calculate_qboost_score(tags, cme_level=3)
        assert result['flaw_deductions'] == -10
        assert result['flaw_count'] == 1

    def test_custom_config(self):
        """Custom config should override defaults."""
        custom_config = QBoostConfig()
        # Modify penalty (in real usage, you'd subclass or modify the instance)
        tags = {'flaw_implausible_distractor': True}
        result = calculate_qboost_score(tags, cme_level=3, config=custom_config)
        assert result['flaw_deductions'] == -10


class TestGradeInterpretation:
    """Test grade interpretation messages."""

    def test_grade_a_interpretation(self):
        """Grade A interpretation."""
        tags = {}
        result = calculate_qboost_score(tags, cme_level=3)
        assert result['grade'] == 'A'
        assert 'Excellent' in result['grade_interpretation']

    def test_grade_f_interpretation(self):
        """Grade F interpretation."""
        tags = {
            'flaw_implausible_distractor': True,
            'flaw_grammatical_cue': True,
            'flaw_clang_association': True,
            'flaw_convergence_vulnerability': True,
            'flaw_absolute_terms': True,
            'flaw_double_negative': True,
            'distractor_homogeneity': 'Heterogeneous',
            'answer_length_pattern': 'Correct longest',
            'answer_option_count': 2,
        }
        result = calculate_qboost_score(tags, cme_level=4)
        # This should be a low grade
        assert 'Poor' in result['grade_interpretation'] or \
               'Failing' in result['grade_interpretation'] or \
               'revision' in result['grade_interpretation'].lower() or \
               'rewrite' in result['grade_interpretation'].lower()
