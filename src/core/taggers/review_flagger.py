"""
Review Flagger - Simplified flagging for Stage 1 classification review.

With 99.74% unanimous accuracy, only flags model disagreement and API errors.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class ReviewPriority(Enum):
    """Review priority levels."""
    CRITICAL = 1    # Model conflict - needs human review
    MEDIUM = 2      # Partial response - API error


@dataclass
class ReviewFlag:
    """A flag indicating a question needs review."""
    priority: ReviewPriority
    root_cause: str           # Short category (e.g., "Model Conflict")
    reason: str               # Detailed explanation


class ReviewFlagger:
    """
    Simplified review flagging - only flags disagreement and API errors.

    With 99.74% unanimous accuracy across 392 questions, the extra pattern-based
    flags (Business Rule, Multi-Disease, Broad Category, etc.) produced too many
    false positives with no errors caught. Simplified to only flag:

    1. Model Conflict - GPT and Gemini disagree (rare but worth reviewing)
    2. Partial Response - One model had an API error
    """

    def flag_for_review(
        self,
        disease_state: Optional[str] = None,
        disease_state_secondary: Optional[str] = None,
        is_oncology: Optional[bool] = None,
        agreement: str = "",
        activity_names: Optional[List[str]] = None,
        question_text: Optional[str] = None,
        correct_answer: Optional[str] = None,
        voting_details: Optional[Dict] = None
    ) -> List[ReviewFlag]:
        """
        Analyze a classification result and return review flags.

        Only flags:
        - Model conflict (GPT vs Gemini disagreement)
        - Partial response (API errors)

        Returns list of flags. Empty list means no review needed.
        """
        flags = []

        # 1. Model Conflict (CRITICAL - models disagree)
        if agreement == "conflict":
            flags.append(ReviewFlag(
                priority=ReviewPriority.CRITICAL,
                root_cause="Model Conflict",
                reason="GPT and Gemini disagree - needs human review"
            ))

        # 2. Partial Response / API Error (MEDIUM - one model failed)
        if agreement == "partial_response":
            flags.append(ReviewFlag(
                priority=ReviewPriority.MEDIUM,
                root_cause="Partial Response",
                reason="One model had an API error - single model result"
            ))

        # Also check voting_details for error info
        if voting_details and voting_details.get("models_with_errors", 0) > 0:
            error_models = voting_details.get("error_models", [])
            if error_models and not any(f.root_cause == "Partial Response" for f in flags):
                flags.append(ReviewFlag(
                    priority=ReviewPriority.MEDIUM,
                    root_cause="Partial Response",
                    reason=f"Model error: {', '.join(error_models)}"
                ))

        return flags

    def get_priority_label(self, flags: List[ReviewFlag]) -> str:
        """Get the highest priority label for display."""
        if not flags:
            return "Auto-Accept"

        highest = min(f.priority.value for f in flags)
        return {
            ReviewPriority.CRITICAL.value: "Critical Review",
            ReviewPriority.MEDIUM.value: "Medium Priority",
        }.get(highest, "Review")

    def get_root_causes(self, flags: List[ReviewFlag]) -> List[str]:
        """Get unique root cause labels for display."""
        seen = set()
        causes = []
        for flag in flags:
            if flag.root_cause not in seen:
                seen.add(flag.root_cause)
                causes.append(flag.root_cause)
        return causes

    def to_review_record(
        self,
        flags: List[ReviewFlag],
        include_details: bool = True
    ) -> Dict:
        """
        Convert flags to a record suitable for review queue.

        Returns dict with fields for dashboard display.
        """
        if not flags:
            return {
                "needs_review": False,
                "priority": "Auto-Accept",
                "error_likelihood": 0.003,  # 0.3% baseline (1/392 unanimous errors)
                "root_causes": [],
                "flag_count": 0,
                "details": []
            }

        # Simple error likelihood based on flag type
        error_likelihood = 0.003  # baseline
        for flag in flags:
            if flag.root_cause == "Model Conflict":
                error_likelihood = 0.15  # ~15% when models disagree
            elif flag.root_cause == "Partial Response":
                error_likelihood = max(error_likelihood, 0.05)  # ~5% with API error

        record = {
            "needs_review": True,
            "priority": self.get_priority_label(flags),
            "error_likelihood": round(error_likelihood, 3),
            "root_causes": self.get_root_causes(flags),
            "flag_count": len(flags),
        }

        if include_details:
            record["details"] = [
                {
                    "priority": flag.priority.name,
                    "root_cause": flag.root_cause,
                    "reason": flag.reason
                }
                for flag in flags
            ]

        return record


# Convenience function for quick flagging
def flag_classification(
    disease_state: Optional[str] = None,
    is_oncology: Optional[bool] = None,
    agreement: str = "",
    activity_names: Optional[List[str]] = None,
    question_text: Optional[str] = None,
    correct_answer: Optional[str] = None,
    disease_state_secondary: Optional[str] = None,
    voting_details: Optional[Dict] = None
) -> Dict:
    """
    Quick function to flag a classification for review.

    Returns a review record dict suitable for dashboard display.
    """
    flagger = ReviewFlagger()
    flags = flagger.flag_for_review(
        disease_state=disease_state,
        disease_state_secondary=disease_state_secondary,
        is_oncology=is_oncology,
        agreement=agreement,
        activity_names=activity_names,
        question_text=question_text,
        correct_answer=correct_answer,
        voting_details=voting_details
    )
    return flagger.to_review_record(flags)
