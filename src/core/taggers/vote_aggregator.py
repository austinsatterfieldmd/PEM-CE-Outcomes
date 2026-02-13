"""
Vote Aggregator for 3-Model LLM Voting System.

Aggregates votes from GPT, Claude, and Gemini to determine:
- Agreement level (unanimous, majority, conflict)
- Final tag values based on voting rules
- Confidence scores
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field
from collections import Counter

logger = logging.getLogger(__name__)


class AgreementLevel(str, Enum):
    """Agreement level among the 3 models."""
    UNANIMOUS = "unanimous"  # All 3 models agree
    MAJORITY = "majority"    # 2 of 3 models agree
    CONFLICT = "conflict"    # All 3 models disagree


@dataclass
class TagVote:
    """A single tag field's votes from all models."""
    field_name: str
    gpt_value: Optional[str]
    claude_value: Optional[str]
    gemini_value: Optional[str]
    final_value: Optional[str] = None
    agreement_level: AgreementLevel = AgreementLevel.CONFLICT
    confidence: float = 0.0
    dissenting_model: Optional[str] = None


@dataclass
class AggregatedVote:
    """Complete aggregated vote result for a question."""
    question_id: int
    tags: Dict[str, TagVote] = field(default_factory=dict)
    overall_agreement: AgreementLevel = AgreementLevel.CONFLICT
    overall_confidence: float = 0.0
    needs_review: bool = True
    review_reason: Optional[str] = None  # Why review is needed (for LLM eval)
    web_searches_used: List[Dict] = field(default_factory=list)

    # Individual model responses (preserved for LLM eval)
    gpt_tags: Dict[str, Any] = field(default_factory=dict)
    claude_tags: Dict[str, Any] = field(default_factory=dict)
    gemini_tags: Dict[str, Any] = field(default_factory=dict)

    # Final tags after aggregation
    final_tags: Dict[str, Any] = field(default_factory=dict)


class VoteAggregator:
    """
    Aggregates votes from 3 LLM models to determine final tags.

    Voting rules:
    - UNANIMOUS (3/3): Auto-accept with confidence 1.0
    - MAJORITY (2/3): Accept majority value with confidence 0.67, FLAG FOR REVIEW (for LLM eval)
    - CONFLICT (1/1/1): NO auto-assignment, flag for human review

    IMPORTANT: All individual model votes are preserved for LLM evaluation.
    Never auto-resolve conflicts - always capture all votes and flag for review.
    """

    # Tag fields that are voted on (73 total)
    TAG_FIELDS = [
        # === Group A: Core Classification (5 + 15 multi-value = 20) ===
        "topic",
        "disease_stage",
        "disease_type_1",
        "disease_type_2",
        "treatment_line",

        # === Multi-value Existing Fields (15) ===
        "treatment_1", "treatment_2", "treatment_3", "treatment_4", "treatment_5",
        "biomarker_1", "biomarker_2", "biomarker_3", "biomarker_4", "biomarker_5",
        "trial_1", "trial_2", "trial_3", "trial_4", "trial_5",

        # === Group B: Patient Characteristics (8) ===
        "treatment_eligibility",
        "age_group",
        "organ_dysfunction",
        "fitness_status",
        "disease_specific_factor",
        "comorbidity_1", "comorbidity_2", "comorbidity_3",

        # === Group C: Treatment Metadata (10) ===
        "drug_class_1", "drug_class_2", "drug_class_3",
        "drug_target_1", "drug_target_2", "drug_target_3",
        "prior_therapy_1", "prior_therapy_2", "prior_therapy_3",
        "resistance_mechanism",

        # === Group D: Clinical Context (7) ===
        "metastatic_site_1", "metastatic_site_2", "metastatic_site_3",
        "symptom_1", "symptom_2", "symptom_3",
        "performance_status",

        # === Group E: Safety/Toxicity (7) ===
        "toxicity_type_1", "toxicity_type_2", "toxicity_type_3", "toxicity_type_4", "toxicity_type_5",
        "toxicity_organ",
        "toxicity_grade",

        # === Group F: Efficacy/Outcomes (5) ===
        "efficacy_endpoint_1", "efficacy_endpoint_2", "efficacy_endpoint_3",
        "outcome_context",
        "clinical_benefit",

        # === Group G: Evidence/Guidelines (3) ===
        "guideline_source_1", "guideline_source_2",
        "evidence_type",

        # === Group H: Question Format/Quality (13) ===
        # Existing (2)
        "cme_outcome_level",      # 3=Knowledge, 4=Competence
        "data_response_type",     # Numeric/Qualitative/Comparative/Boolean
        # Question structure (5)
        "stem_type",              # Clinical vignette/Direct question/Incomplete statement
        "lead_in_type",           # Standard/Negative (EXCEPT/NOT)/Best answer/True statement
        "answer_format",          # Single best/Compound (A+B)/All of above/None of above/True-False
        "answer_length_pattern",  # Uniform/Correct longest/Correct shortest/Variable
        "distractor_homogeneity", # Homogeneous/Heterogeneous
        # Item writing flaws - 6 separate boolean fields
        "flaw_absolute_terms",         # true/false - "always", "never", "all", "none" in options
        "flaw_grammatical_cue",        # true/false - stem grammar reveals answer
        "flaw_implausible_distractor", # true/false - obviously wrong options
        "flaw_clang_association",      # true/false - answer shares words with stem
        "flaw_convergence_vulnerability", # true/false - multiple options share elements
        "flaw_double_negative",        # true/false - negative stem + negative option
    ]

    # Multi-value slot definitions (for validation and output formatting)
    MULTI_VALUE_SLOTS = {
        "treatment": 5,
        "biomarker": 5,
        "trial": 5,
        "disease_type": 2,
        "drug_class": 3,
        "drug_target": 3,
        "prior_therapy": 3,
        "comorbidity": 3,
        "metastatic_site": 3,
        "symptom": 3,
        "toxicity_type": 5,
        "efficacy_endpoint": 3,
        "guideline_source": 2,
    }

    # Computed fields (derived from raw data, not LLM-tagged)
    COMPUTED_FIELDS = ["answer_option_count", "correct_answer_position"]

    def __init__(
        self,
        auto_accept_unanimous: bool = True,
        spot_check_rate: float = 0.10,
        unanimous_confidence: float = 1.0,
        majority_confidence: float = 0.67,
        conflict_confidence: float = 0.0
    ):
        """
        Initialize vote aggregator.

        Args:
            auto_accept_unanimous: Whether to auto-accept unanimous votes
            spot_check_rate: Rate of unanimous votes to spot-check (0.0-1.0)
            unanimous_confidence: Confidence score for unanimous votes
            majority_confidence: Confidence score for majority votes
            conflict_confidence: Confidence score for conflicts
        """
        self.auto_accept_unanimous = auto_accept_unanimous
        self.spot_check_rate = spot_check_rate
        self.unanimous_confidence = unanimous_confidence
        self.majority_confidence = majority_confidence
        self.conflict_confidence = conflict_confidence

    # Fields that must remain boolean (not stringified)
    BOOLEAN_FIELDS = {
        "flaw_absolute_terms", "flaw_grammatical_cue", "flaw_implausible_distractor",
        "flaw_clang_association", "flaw_convergence_vulnerability", "flaw_double_negative",
    }

    def _normalize_value(self, value: Any) -> Optional[Any]:
        """Normalize a tag value for comparison.

        Booleans are converted to lowercase strings ("true"/"false") so that
        votes from different models compare correctly. The boolean type is
        restored in get_final_tags() for BOOLEAN_FIELDS.
        """
        if value is None:
            return None
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, str):
            # Strip whitespace and normalize case for comparison
            normalized = value.strip()
            return normalized if normalized else None
        return str(value).strip() or None

    def _aggregate_field(
        self,
        field_name: str,
        gpt_value: Any,
        claude_value: Any,
        gemini_value: Any
    ) -> TagVote:
        """
        Aggregate votes for a single tag field.

        IMPORTANT: Never auto-resolve conflicts. All 3 votes are preserved.
        - Unanimous: Auto-accept
        - Majority: Accept majority BUT flag for review (dissenting vote preserved)
        - Conflict: NO auto-assignment, flag for review (all votes preserved)

        Args:
            field_name: Name of the tag field
            gpt_value: GPT's value for this field
            claude_value: Claude's value for this field
            gemini_value: Gemini's value for this field

        Returns:
            TagVote with aggregated result
        """
        # Normalize values
        gpt_norm = self._normalize_value(gpt_value)
        claude_norm = self._normalize_value(claude_value)
        gemini_norm = self._normalize_value(gemini_value)

        vote = TagVote(
            field_name=field_name,
            gpt_value=gpt_norm,
            claude_value=claude_norm,
            gemini_value=gemini_norm
        )

        # Count votes (treating None as a distinct value)
        values = [gpt_norm, claude_norm, gemini_norm]
        non_none_values = [v for v in values if v is not None]

        # If all None, return as unanimous agreement on "no value"
        if not non_none_values:
            vote.agreement_level = AgreementLevel.UNANIMOUS
            vote.final_value = None
            vote.confidence = self.unanimous_confidence
            return vote

        # Count occurrences of each value
        value_counts = Counter(values)
        most_common = value_counts.most_common()

        # Check for unanimous (all same value)
        if len(most_common) == 1:
            vote.agreement_level = AgreementLevel.UNANIMOUS
            vote.final_value = most_common[0][0]
            vote.confidence = self.unanimous_confidence
            return vote

        # Check for majority (2 of 3)
        if most_common[0][1] >= 2:
            majority_value = most_common[0][0]
            vote.agreement_level = AgreementLevel.MAJORITY
            vote.final_value = majority_value
            vote.confidence = self.majority_confidence

            # Identify dissenting model (important for LLM eval)
            model_values = {"gpt": gpt_norm, "claude": claude_norm, "gemini": gemini_norm}
            for model, val in model_values.items():
                if val != majority_value:
                    vote.dissenting_model = model
                    break

            # Note: Majority votes are flagged for review in aggregate() method
            return vote

        # Conflict (all different) - DO NOT auto-assign any value
        vote.agreement_level = AgreementLevel.CONFLICT
        vote.final_value = None  # Explicitly null - requires manual review
        vote.confidence = self.conflict_confidence

        logger.info(
            f"Field '{field_name}' conflict: gpt={gpt_norm}, claude={claude_norm}, gemini={gemini_norm}"
        )

        return vote

    def aggregate(
        self,
        question_id: int,
        gpt_response: Dict[str, Any],
        claude_response: Dict[str, Any],
        gemini_response: Dict[str, Any],
        web_searches: Optional[List[Dict]] = None
    ) -> AggregatedVote:
        """
        Aggregate votes from all 3 models.

        IMPORTANT: All votes are preserved for LLM evaluation.
        - Unanimous: Auto-accept (unless spot-check selected)
        - Majority: Accept majority value BUT flag for review
        - Conflict: NO auto-assignment, flag for review

        Args:
            question_id: ID of the question being tagged
            gpt_response: GPT's tag assignments
            claude_response: Claude's tag assignments
            gemini_response: Gemini's tag assignments
            web_searches: Optional list of web searches performed

        Returns:
            AggregatedVote with final results and review flags
        """
        result = AggregatedVote(
            question_id=question_id,
            gpt_tags=gpt_response,
            claude_tags=claude_response,
            gemini_tags=gemini_response,
            web_searches_used=web_searches or []
        )

        # Aggregate each tag field
        agreement_levels = []
        conflict_fields = []
        majority_fields = []

        for field in self.TAG_FIELDS:
            tag_vote = self._aggregate_field(
                field_name=field,
                gpt_value=gpt_response.get(field),
                claude_value=claude_response.get(field),
                gemini_value=gemini_response.get(field)
            )
            result.tags[field] = tag_vote
            agreement_levels.append(tag_vote.agreement_level)

            # Track which fields have disagreements (for review_reason)
            if tag_vote.agreement_level == AgreementLevel.CONFLICT:
                conflict_fields.append(field)
            elif tag_vote.agreement_level == AgreementLevel.MAJORITY:
                majority_fields.append(field)

        # Build final_tags dict
        result.final_tags = self.get_final_tags(result)

        # Determine overall agreement level and review status
        if all(a == AgreementLevel.UNANIMOUS for a in agreement_levels):
            result.overall_agreement = AgreementLevel.UNANIMOUS
            result.overall_confidence = self.unanimous_confidence
            result.needs_review = not self.auto_accept_unanimous
            result.review_reason = None
        elif any(a == AgreementLevel.CONFLICT for a in agreement_levels):
            # Any conflict means review required
            result.overall_agreement = AgreementLevel.CONFLICT
            result.overall_confidence = self.conflict_confidence
            result.needs_review = True
            result.review_reason = f"conflict_in_fields:{','.join(conflict_fields)}"
            logger.warning(
                f"Question {question_id}: Conflict in fields {conflict_fields} - flagging for manual review"
            )
        else:
            # Majority agreement - accept but flag for review (for LLM eval)
            result.overall_agreement = AgreementLevel.MAJORITY
            result.overall_confidence = self.majority_confidence
            result.needs_review = True  # CHANGED: Always review majority votes for LLM eval
            result.review_reason = f"majority_in_fields:{','.join(majority_fields)}"
            logger.info(
                f"Question {question_id}: Majority agreement in fields {majority_fields} - flagging for review"
            )

        return result

    def get_final_tags(self, aggregated: AggregatedVote) -> Dict[str, Any]:
        """
        Extract final tag values from aggregated vote.

        Restores boolean types for BOOLEAN_FIELDS (flaw detectors) which were
        stringified during normalization for vote comparison.

        Args:
            aggregated: AggregatedVote result

        Returns:
            Dict of tag field -> final value
        """
        tags = {}
        for field, vote in aggregated.tags.items():
            val = vote.final_value
            if field in self.BOOLEAN_FIELDS:
                # Restore actual boolean from string representation
                if isinstance(val, str):
                    tags[field] = val.lower() in ('true', 'yes', '1', 't', 'y')
                elif isinstance(val, bool):
                    tags[field] = val
                else:
                    tags[field] = False  # Default for None/conflict
            else:
                tags[field] = val
        return tags

    def get_confidence_scores(self, aggregated: AggregatedVote) -> Dict[str, float]:
        """
        Extract confidence scores for each tag field.

        Args:
            aggregated: AggregatedVote result

        Returns:
            Dict of tag field -> confidence score
        """
        return {
            field: vote.confidence
            for field, vote in aggregated.tags.items()
        }

    def get_disagreements(self, aggregated: AggregatedVote) -> List[Dict[str, Any]]:
        """
        Get list of fields where models disagreed.

        Args:
            aggregated: AggregatedVote result

        Returns:
            List of disagreement dicts with field, values, and level
        """
        disagreements = []
        for field, vote in aggregated.tags.items():
            if vote.agreement_level != AgreementLevel.UNANIMOUS:
                disagreements.append({
                    "field": field,
                    "agreement_level": vote.agreement_level.value,
                    "gpt": vote.gpt_value,
                    "claude": vote.claude_value,
                    "gemini": vote.gemini_value,
                    "final": vote.final_value,
                    "dissenting_model": vote.dissenting_model
                })
        return disagreements

    def format_for_review(self, aggregated: AggregatedVote) -> Dict[str, Any]:
        """
        Format aggregated vote for human review interface.

        Includes all individual model votes for LLM evaluation purposes.

        Args:
            aggregated: AggregatedVote result

        Returns:
            Dict formatted for review UI
        """
        return {
            "question_id": aggregated.question_id,
            "overall_agreement": aggregated.overall_agreement.value,
            "overall_confidence": aggregated.overall_confidence,
            "needs_review": aggregated.needs_review,
            "review_reason": aggregated.review_reason,
            "tags": {
                field: {
                    "final": vote.final_value,
                    "agreement": vote.agreement_level.value,
                    "confidence": vote.confidence,
                    "votes": {
                        "gpt": vote.gpt_value,
                        "claude": vote.claude_value,
                        "gemini": vote.gemini_value
                    },
                    "dissenting_model": vote.dissenting_model
                }
                for field, vote in aggregated.tags.items()
            },
            # Preserve full model responses for LLM eval
            "model_responses": {
                "gpt": aggregated.gpt_tags,
                "claude": aggregated.claude_tags,
                "gemini": aggregated.gemini_tags
            },
            "web_searches": aggregated.web_searches_used
        }

    def to_database_format(self, aggregated: AggregatedVote) -> Dict[str, Any]:
        """
        Convert aggregated vote to database storage format.

        Preserves all individual model votes for LLM evaluation.

        Args:
            aggregated: AggregatedVote result

        Returns:
            Dict ready for database insertion
        """
        import json

        return {
            "question_id": aggregated.question_id,
            # Individual model responses (preserved for LLM eval)
            "gpt_tags": json.dumps(aggregated.gpt_tags),
            "claude_tags": json.dumps(aggregated.claude_tags),
            "gemini_tags": json.dumps(aggregated.gemini_tags),
            # Aggregated result
            "aggregated_tags": json.dumps(aggregated.final_tags or self.get_final_tags(aggregated)),
            "agreement_level": aggregated.overall_agreement.value,
            # Review tracking
            "needs_review": aggregated.needs_review,
            "review_reason": aggregated.review_reason,
            # Web search results
            "web_searches": json.dumps(aggregated.web_searches_used) if aggregated.web_searches_used else None
        }
