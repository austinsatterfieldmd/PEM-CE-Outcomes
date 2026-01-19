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
    web_searches_used: List[Dict] = field(default_factory=list)

    # Individual model responses
    gpt_tags: Dict[str, Any] = field(default_factory=dict)
    claude_tags: Dict[str, Any] = field(default_factory=dict)
    gemini_tags: Dict[str, Any] = field(default_factory=dict)


class VoteAggregator:
    """
    Aggregates votes from 3 LLM models to determine final tags.

    Voting rules:
    - UNANIMOUS (3/3): Auto-accept with confidence 1.0
    - MAJORITY (2/3): Accept majority value with confidence 0.67, flag for spot-check
    - CONFLICT (1/1/1): Flag for human review, no auto-assignment

    Configurable thresholds for auto-acceptance.
    """

    # Tag fields that are voted on
    TAG_FIELDS = [
        "topic",
        "disease_state",
        "disease_stage",
        "disease_type",
        "treatment_line",
        "treatment",
        "biomarker",
        "trial"
    ]

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

    def _normalize_value(self, value: Any) -> Optional[str]:
        """Normalize a tag value for comparison."""
        if value is None:
            return None
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

        # If all None, return as conflict with no value
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

            # Identify dissenting model
            model_values = {"gpt": gpt_norm, "claude": claude_norm, "gemini": gemini_norm}
            for model, val in model_values.items():
                if val != majority_value:
                    vote.dissenting_model = model
                    break

            return vote

        # Conflict (all different)
        vote.agreement_level = AgreementLevel.CONFLICT
        vote.final_value = None  # No auto-assignment for conflicts
        vote.confidence = self.conflict_confidence

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

        Args:
            question_id: ID of the question being tagged
            gpt_response: GPT's tag assignments
            claude_response: Claude's tag assignments
            gemini_response: Gemini's tag assignments
            web_searches: Optional list of web searches performed

        Returns:
            AggregatedVote with final results
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
        for field in self.TAG_FIELDS:
            tag_vote = self._aggregate_field(
                field_name=field,
                gpt_value=gpt_response.get(field),
                claude_value=claude_response.get(field),
                gemini_value=gemini_response.get(field)
            )
            result.tags[field] = tag_vote
            agreement_levels.append(tag_vote.agreement_level)

        # Determine overall agreement level
        if all(a == AgreementLevel.UNANIMOUS for a in agreement_levels):
            result.overall_agreement = AgreementLevel.UNANIMOUS
            result.overall_confidence = self.unanimous_confidence
            result.needs_review = not self.auto_accept_unanimous
        elif any(a == AgreementLevel.CONFLICT for a in agreement_levels):
            result.overall_agreement = AgreementLevel.CONFLICT
            result.overall_confidence = self.conflict_confidence
            result.needs_review = True
        else:
            result.overall_agreement = AgreementLevel.MAJORITY
            result.overall_confidence = self.majority_confidence
            result.needs_review = True  # Majority votes go to review

        return result

    def get_final_tags(self, aggregated: AggregatedVote) -> Dict[str, Any]:
        """
        Extract final tag values from aggregated vote.

        Args:
            aggregated: AggregatedVote result

        Returns:
            Dict of tag field -> final value
        """
        return {
            field: vote.final_value
            for field, vote in aggregated.tags.items()
        }

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
            "web_searches": aggregated.web_searches_used
        }

    def to_database_format(self, aggregated: AggregatedVote) -> Dict[str, Any]:
        """
        Convert aggregated vote to database storage format.

        Args:
            aggregated: AggregatedVote result

        Returns:
            Dict ready for database insertion
        """
        import json

        return {
            "question_id": aggregated.question_id,
            "gpt_tags": json.dumps(aggregated.gpt_tags),
            "claude_tags": json.dumps(aggregated.claude_tags),
            "gemini_tags": json.dumps(aggregated.gemini_tags),
            "aggregated_tags": json.dumps(self.get_final_tags(aggregated)),
            "agreement_level": aggregated.overall_agreement.value,
            "needs_review": aggregated.needs_review,
            "web_searches": json.dumps(aggregated.web_searches_used) if aggregated.web_searches_used else None
        }
