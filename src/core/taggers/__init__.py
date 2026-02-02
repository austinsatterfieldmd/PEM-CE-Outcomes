"""
V3 Tagging system - 3-model LLM voting.

This module provides the core tagging functionality using a 3-model voting system
(GPT-5.2, Claude Opus 4.5, Gemini 2.5 Pro) via OpenRouter.
"""

from .openrouter_client import OpenRouterClient, ModelConfig, RetryConfig
from .vote_aggregator import VoteAggregator, AggregatedVote, TagVote, AgreementLevel
from .multi_model_tagger import MultiModelTagger

__all__ = [
    "OpenRouterClient",
    "ModelConfig",
    "RetryConfig",
    "VoteAggregator",
    "AggregatedVote",
    "TagVote",
    "AgreementLevel",
    "MultiModelTagger",
]
