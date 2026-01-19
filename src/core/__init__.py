"""
V3 Core module.

Provides the core business logic for the CME Outcomes Tagger including:
- 3-model LLM voting system (taggers)
- Domain knowledge and validation (knowledge)
- External service integrations (services)
- Data preprocessing (preprocessing)
"""

from .taggers import MultiModelTagger, VoteAggregator, OpenRouterClient
from .knowledge import KnowledgeEnricher
from .services import WebSearchService, PromptManager

__all__ = [
    "MultiModelTagger",
    "VoteAggregator",
    "OpenRouterClient",
    "KnowledgeEnricher",
    "WebSearchService",
    "PromptManager",
]
