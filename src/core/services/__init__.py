"""
V3 Services layer.

Provides external service integrations and utilities for the tagging system.
"""

from .web_search import WebSearchService, SearchResult
from .prompt_manager import PromptManager, PromptVersion

__all__ = [
    "WebSearchService",
    "SearchResult",
    "PromptManager",
    "PromptVersion",
]
