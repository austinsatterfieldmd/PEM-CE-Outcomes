"""
Unit tests for VoteAggregator.

Tests the 3-model voting logic:
- Unanimous agreement (3/3)
- Majority agreement (2/3)
- Conflict (1/1/1)
"""

import pytest
from src.core.taggers.vote_aggregator import (
    VoteAggregator,
    AgreementLevel,
    TagVote,
    AggregatedVote
)


class TestVoteAggregator:
    """Tests for VoteAggregator class."""

    @pytest.fixture
    def aggregator(self):
        """Create a default VoteAggregator instance."""
        return VoteAggregator()

    # ============== Unanimous Tests ==============

    def test_unanimous_all_same(
        self,
        aggregator,
        sample_gpt_response,
        sample_claude_response,
        sample_gemini_response
    ):
        """Test unanimous agreement when all 3 models return identical tags."""
        result = aggregator.aggregate(
            question_id=1,
            gpt_response=sample_gpt_response,
            claude_response=sample_claude_response,
            gemini_response=sample_gemini_response
        )

        assert result.overall_agreement == AgreementLevel.UNANIMOUS
        assert result.overall_confidence == 1.0
        assert result.needs_review is False  # Auto-accept unanimous

        # Check each tag field
        for field, tag_vote in result.tags.items():
            assert tag_vote.agreement_level == AgreementLevel.UNANIMOUS
            assert tag_vote.confidence == 1.0
            assert tag_vote.dissenting_model is None

    def test_unanimous_all_none(self, aggregator):
        """Test unanimous when all models return None for a field."""
        gpt = {"topic": None, "disease_state": "NSCLC"}
        claude = {"topic": None, "disease_state": "NSCLC"}
        gemini = {"topic": None, "disease_state": "NSCLC"}

        result = aggregator.aggregate(
            question_id=1,
            gpt_response=gpt,
            claude_response=claude,
            gemini_response=gemini
        )

        # topic should be unanimous (all None)
        assert result.tags["topic"].agreement_level == AgreementLevel.UNANIMOUS
        assert result.tags["topic"].final_value is None

    # ============== Majority Tests ==============

    def test_majority_agreement(self, aggregator, sample_disagreement_responses):
        """Test majority agreement (2/3 models agree)."""
        gpt, claude, gemini = sample_disagreement_responses

        result = aggregator.aggregate(
            question_id=1,
            gpt_response=gpt,
            claude_response=claude,
            gemini_response=gemini
        )

        # Only topic differs (gemini)
        assert result.tags["topic"].agreement_level == AgreementLevel.MAJORITY
        assert result.tags["topic"].final_value == "Treatment selection"  # GPT & Claude
        assert result.tags["topic"].confidence == 0.67
        assert result.tags["topic"].dissenting_model == "gemini"

        # Overall should be majority since one field has majority
        assert result.overall_agreement == AgreementLevel.MAJORITY
        assert result.needs_review is True

    def test_majority_identifies_dissenting_model_gpt(self, aggregator):
        """Test that GPT is correctly identified as dissenting."""
        gpt = {"topic": "Different topic"}
        claude = {"topic": "Same topic"}
        gemini = {"topic": "Same topic"}

        result = aggregator.aggregate(
            question_id=1,
            gpt_response=gpt,
            claude_response=claude,
            gemini_response=gemini
        )

        assert result.tags["topic"].dissenting_model == "gpt"
        assert result.tags["topic"].final_value == "Same topic"

    def test_majority_identifies_dissenting_model_claude(self, aggregator):
        """Test that Claude is correctly identified as dissenting."""
        gpt = {"topic": "Same topic"}
        claude = {"topic": "Different topic"}
        gemini = {"topic": "Same topic"}

        result = aggregator.aggregate(
            question_id=1,
            gpt_response=gpt,
            claude_response=claude,
            gemini_response=gemini
        )

        assert result.tags["topic"].dissenting_model == "claude"

    # ============== Conflict Tests ==============

    def test_conflict_all_different(self, aggregator, sample_conflict_responses):
        """Test conflict when all 3 models disagree."""
        gpt, claude, gemini = sample_conflict_responses

        result = aggregator.aggregate(
            question_id=1,
            gpt_response=gpt,
            claude_response=claude,
            gemini_response=gemini
        )

        # Topic has 3 different values
        assert result.tags["topic"].agreement_level == AgreementLevel.CONFLICT
        assert result.tags["topic"].final_value is None  # No auto-assignment
        assert result.tags["topic"].confidence == 0.0

        # Overall should be conflict
        assert result.overall_agreement == AgreementLevel.CONFLICT
        assert result.needs_review is True

    def test_conflict_no_final_value_assigned(self, aggregator):
        """Ensure conflicts don't auto-assign final values."""
        gpt = {"treatment": "Drug A"}
        claude = {"treatment": "Drug B"}
        gemini = {"treatment": "Drug C"}

        result = aggregator.aggregate(
            question_id=1,
            gpt_response=gpt,
            claude_response=claude,
            gemini_response=gemini
        )

        assert result.tags["treatment"].final_value is None

    # ============== Value Normalization Tests ==============

    def test_normalize_whitespace(self, aggregator):
        """Test that whitespace is normalized for comparison."""
        gpt = {"topic": "Treatment selection"}
        claude = {"topic": "  Treatment selection  "}
        gemini = {"topic": "Treatment selection "}

        result = aggregator.aggregate(
            question_id=1,
            gpt_response=gpt,
            claude_response=claude,
            gemini_response=gemini
        )

        assert result.tags["topic"].agreement_level == AgreementLevel.UNANIMOUS

    def test_empty_string_treated_as_none(self, aggregator):
        """Test that empty strings are normalized to None."""
        gpt = {"topic": ""}
        claude = {"topic": None}
        gemini = {"topic": "   "}

        result = aggregator.aggregate(
            question_id=1,
            gpt_response=gpt,
            claude_response=claude,
            gemini_response=gemini
        )

        # All should be treated as None -> unanimous
        assert result.tags["topic"].agreement_level == AgreementLevel.UNANIMOUS
        assert result.tags["topic"].final_value is None

    # ============== Helper Method Tests ==============

    def test_get_final_tags(self, aggregator, sample_gpt_response):
        """Test extracting final tags from aggregated result."""
        result = aggregator.aggregate(
            question_id=1,
            gpt_response=sample_gpt_response,
            claude_response=sample_gpt_response,
            gemini_response=sample_gpt_response
        )

        final_tags = aggregator.get_final_tags(result)

        assert final_tags["topic"] == "Treatment selection"
        assert final_tags["disease_state"] == "NSCLC"
        assert final_tags["treatment"] == "osimertinib"

    def test_get_confidence_scores(self, aggregator, sample_disagreement_responses):
        """Test extracting confidence scores."""
        gpt, claude, gemini = sample_disagreement_responses

        result = aggregator.aggregate(
            question_id=1,
            gpt_response=gpt,
            claude_response=claude,
            gemini_response=gemini
        )

        scores = aggregator.get_confidence_scores(result)

        assert scores["topic"] == 0.67  # Majority
        assert scores["disease_state"] == 1.0  # Unanimous

    def test_get_disagreements(self, aggregator, sample_disagreement_responses):
        """Test extracting disagreement details."""
        gpt, claude, gemini = sample_disagreement_responses

        result = aggregator.aggregate(
            question_id=1,
            gpt_response=gpt,
            claude_response=claude,
            gemini_response=gemini
        )

        disagreements = aggregator.get_disagreements(result)

        # Should have one disagreement (topic)
        assert len(disagreements) == 1
        assert disagreements[0]["field"] == "topic"
        assert disagreements[0]["dissenting_model"] == "gemini"

    def test_format_for_review(self, aggregator, sample_gpt_response):
        """Test formatting for review UI."""
        result = aggregator.aggregate(
            question_id=1,
            gpt_response=sample_gpt_response,
            claude_response=sample_gpt_response,
            gemini_response=sample_gpt_response
        )

        review_format = aggregator.format_for_review(result)

        assert "question_id" in review_format
        assert "overall_agreement" in review_format
        assert "tags" in review_format
        assert review_format["overall_agreement"] == "unanimous"

    def test_to_database_format(self, aggregator, sample_gpt_response):
        """Test conversion to database storage format."""
        result = aggregator.aggregate(
            question_id=1,
            gpt_response=sample_gpt_response,
            claude_response=sample_gpt_response,
            gemini_response=sample_gpt_response
        )

        db_format = aggregator.to_database_format(result)

        assert db_format["question_id"] == 1
        assert db_format["agreement_level"] == "unanimous"
        assert db_format["needs_review"] is False
        # JSON fields should be strings
        assert isinstance(db_format["gpt_tags"], str)
        assert isinstance(db_format["aggregated_tags"], str)

    # ============== Configuration Tests ==============

    def test_custom_confidence_thresholds(self):
        """Test custom confidence thresholds."""
        aggregator = VoteAggregator(
            unanimous_confidence=0.95,
            majority_confidence=0.60,
            conflict_confidence=0.1
        )

        gpt = {"topic": "A"}
        claude = {"topic": "A"}
        gemini = {"topic": "B"}

        result = aggregator.aggregate(
            question_id=1,
            gpt_response=gpt,
            claude_response=claude,
            gemini_response=gemini
        )

        assert result.tags["topic"].confidence == 0.60  # Custom majority

    def test_auto_accept_disabled(self):
        """Test disabling auto-accept for unanimous votes."""
        aggregator = VoteAggregator(auto_accept_unanimous=False)

        gpt = {"topic": "Same"}
        claude = {"topic": "Same"}
        gemini = {"topic": "Same"}

        result = aggregator.aggregate(
            question_id=1,
            gpt_response=gpt,
            claude_response=claude,
            gemini_response=gemini
        )

        # Even unanimous needs review when auto-accept is disabled
        assert result.needs_review is True

    # ============== Edge Case Tests ==============

    def test_missing_fields_handled(self, aggregator):
        """Test that missing fields in responses are handled gracefully."""
        gpt = {"topic": "A"}  # Missing other fields
        claude = {"topic": "A", "disease_state": "B"}
        gemini = {}  # Empty

        # Should not raise an error
        result = aggregator.aggregate(
            question_id=1,
            gpt_response=gpt,
            claude_response=claude,
            gemini_response=gemini
        )

        assert result is not None
        assert "topic" in result.tags

    def test_web_searches_stored(self, aggregator, sample_gpt_response):
        """Test that web searches are stored in result."""
        web_searches = [
            {"entity": "novel-drug", "query": "novel-drug oncology", "result": "Info..."}
        ]

        result = aggregator.aggregate(
            question_id=1,
            gpt_response=sample_gpt_response,
            claude_response=sample_gpt_response,
            gemini_response=sample_gpt_response,
            web_searches=web_searches
        )

        assert result.web_searches_used == web_searches

    def test_all_tag_fields_processed(self, aggregator, sample_gpt_response):
        """Test that all 66 tag fields are processed."""
        result = aggregator.aggregate(
            question_id=1,
            gpt_response=sample_gpt_response,
            claude_response=sample_gpt_response,
            gemini_response=sample_gpt_response
        )

        # Verify all 66 TAG_FIELDS are processed
        assert len(result.tags) == 66

        # Check core classification fields
        core_fields = ["topic", "disease_stage", "disease_type", "treatment_line"]
        for field in core_fields:
            assert field in result.tags

        # Check multi-value fields
        for i in range(1, 6):
            assert f"treatment_{i}" in result.tags
            assert f"biomarker_{i}" in result.tags
            assert f"trial_{i}" in result.tags

        # Check Group A: Treatment Metadata
        for i in range(1, 4):
            assert f"drug_class_{i}" in result.tags
            assert f"drug_target_{i}" in result.tags
            assert f"prior_therapy_{i}" in result.tags
        assert "resistance_mechanism" in result.tags

        # Check Group B: Clinical Context
        for i in range(1, 4):
            assert f"metastatic_site_{i}" in result.tags
            assert f"symptom_{i}" in result.tags
        assert "special_population_1" in result.tags
        assert "special_population_2" in result.tags
        assert "performance_status" in result.tags

        # Check Group C: Safety/Toxicity
        for i in range(1, 6):
            assert f"toxicity_type_{i}" in result.tags
        assert "toxicity_organ" in result.tags
        assert "toxicity_grade" in result.tags

        # Check Group D: Efficacy/Outcomes
        for i in range(1, 4):
            assert f"efficacy_endpoint_{i}" in result.tags
        assert "outcome_context" in result.tags
        assert "clinical_benefit" in result.tags

        # Check Group E: Evidence/Guidelines
        assert "guideline_source_1" in result.tags
        assert "guideline_source_2" in result.tags
        assert "evidence_type" in result.tags

        # Check Group F: Question Format/Quality (13 fields)
        group_f_fields = [
            "cme_outcome_level", "data_response_type",
            "stem_type", "lead_in_type", "answer_format",
            "answer_length_pattern", "distractor_homogeneity",
            "flaw_absolute_terms", "flaw_grammatical_cue",
            "flaw_implausible_distractor", "flaw_clang_association",
            "flaw_convergence_vulnerability", "flaw_double_negative"
        ]
        for field in group_f_fields:
            assert field in result.tags

    # ============== 66-Field Schema Tests ==============

    def test_all_66_fields_processed(self, aggregator, sample_66_field_response):
        """Test that all 66 TAG_FIELDS are processed correctly."""
        result = aggregator.aggregate(
            question_id=1,
            gpt_response=sample_66_field_response,
            claude_response=sample_66_field_response,
            gemini_response=sample_66_field_response
        )

        # Verify exact count
        assert len(result.tags) == 66
        assert result.overall_agreement == AgreementLevel.UNANIMOUS

    def test_group_f_question_format_fields(self, aggregator, sample_66_field_response):
        """Test Group F question format/quality fields are processed."""
        result = aggregator.aggregate(
            question_id=1,
            gpt_response=sample_66_field_response,
            claude_response=sample_66_field_response,
            gemini_response=sample_66_field_response
        )

        # Check question structure fields
        assert result.tags["cme_outcome_level"].final_value == "4 - Competence"
        assert result.tags["data_response_type"].final_value == "Comparative"
        assert result.tags["stem_type"].final_value == "Clinical vignette"
        assert result.tags["lead_in_type"].final_value == "Best answer"
        assert result.tags["answer_format"].final_value == "Single best"
        assert result.tags["answer_length_pattern"].final_value == "Variable"
        assert result.tags["distractor_homogeneity"].final_value == "Homogeneous"

    def test_boolean_flaw_fields(self, aggregator, sample_66_field_response):
        """Test that boolean flaw fields return true/false correctly."""
        result = aggregator.aggregate(
            question_id=1,
            gpt_response=sample_66_field_response,
            claude_response=sample_66_field_response,
            gemini_response=sample_66_field_response
        )

        # Check boolean flaw fields (sample_66_field_response has flaw_implausible_distractor=True)
        assert result.tags["flaw_absolute_terms"].final_value is False
        assert result.tags["flaw_grammatical_cue"].final_value is False
        assert result.tags["flaw_implausible_distractor"].final_value is True  # This one is True
        assert result.tags["flaw_clang_association"].final_value is False
        assert result.tags["flaw_convergence_vulnerability"].final_value is False
        assert result.tags["flaw_double_negative"].final_value is False

    def test_boolean_flaw_fields_majority_vote(self, aggregator, sample_66_field_response):
        """Test that boolean flaw fields vote correctly on disagreement."""
        gpt = sample_66_field_response.copy()
        claude = sample_66_field_response.copy()
        gemini = sample_66_field_response.copy()

        # 2 models say True, 1 says False
        gpt["flaw_absolute_terms"] = True
        claude["flaw_absolute_terms"] = True
        gemini["flaw_absolute_terms"] = False

        result = aggregator.aggregate(
            question_id=1,
            gpt_response=gpt,
            claude_response=claude,
            gemini_response=gemini
        )

        # Majority should win (True)
        assert result.tags["flaw_absolute_terms"].final_value is True
        assert result.tags["flaw_absolute_terms"].agreement_level == AgreementLevel.MAJORITY

    def test_multi_value_treatment_fields(self, aggregator, sample_66_field_response):
        """Test that multi-value treatment fields are processed."""
        response = sample_66_field_response.copy()
        response["treatment_1"] = "Drug A"
        response["treatment_2"] = "Drug B"
        response["treatment_3"] = "Drug C"
        response["treatment_4"] = None
        response["treatment_5"] = None

        result = aggregator.aggregate(
            question_id=1,
            gpt_response=response,
            claude_response=response,
            gemini_response=response
        )

        assert result.tags["treatment_1"].final_value == "Drug A"
        assert result.tags["treatment_2"].final_value == "Drug B"
        assert result.tags["treatment_3"].final_value == "Drug C"
        assert result.tags["treatment_4"].final_value is None
        assert result.tags["treatment_5"].final_value is None

    def test_multi_value_toxicity_fields(self, aggregator, sample_66_field_response):
        """Test that multi-value toxicity fields are processed."""
        response = sample_66_field_response.copy()
        response["toxicity_type_1"] = "Pneumonitis"
        response["toxicity_type_2"] = "Diarrhea"
        response["toxicity_organ"] = "Pulmonary"
        response["toxicity_grade"] = "Grade 3"

        result = aggregator.aggregate(
            question_id=1,
            gpt_response=response,
            claude_response=response,
            gemini_response=response
        )

        assert result.tags["toxicity_type_1"].final_value == "Pneumonitis"
        assert result.tags["toxicity_type_2"].final_value == "Diarrhea"
        assert result.tags["toxicity_organ"].final_value == "Pulmonary"
        assert result.tags["toxicity_grade"].final_value == "Grade 3"

    def test_tag_fields_count_constant(self, aggregator):
        """Verify TAG_FIELDS has exactly 66 fields."""
        assert len(aggregator.TAG_FIELDS) == 66

    def test_computed_fields_not_in_tag_fields(self, aggregator):
        """Verify computed fields are separate from TAG_FIELDS."""
        assert "answer_option_count" not in aggregator.TAG_FIELDS
        assert "correct_answer_position" not in aggregator.TAG_FIELDS
        assert "answer_option_count" in aggregator.COMPUTED_FIELDS
        assert "correct_answer_position" in aggregator.COMPUTED_FIELDS
