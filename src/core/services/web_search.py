"""
Web Search Service for V3.

Uses Perplexity Sonar via OpenRouter for real-time web search
to look up novel trials, recent drug approvals, and emerging entities.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from ..taggers.openrouter_client import OpenRouterClient, get_openrouter_client

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A single web search result."""
    query: str
    content: str
    timestamp: datetime
    entity_type: Optional[str] = None
    entity_name: Optional[str] = None
    citations: List[str] = field(default_factory=list)


@dataclass
class SearchCache:
    """Simple in-memory cache for search results."""
    results: Dict[str, SearchResult] = field(default_factory=dict)
    ttl_minutes: int = 60  # Cache TTL

    def get(self, query: str) -> Optional[SearchResult]:
        """Get cached result if still valid."""
        key = query.lower().strip()
        if key in self.results:
            result = self.results[key]
            if datetime.utcnow() - result.timestamp < timedelta(minutes=self.ttl_minutes):
                return result
            else:
                del self.results[key]
        return None

    def set(self, query: str, result: SearchResult):
        """Cache a search result."""
        key = query.lower().strip()
        self.results[key] = result


class WebSearchService:
    """
    Web search service using Perplexity Sonar.

    Provides specialized search for:
    - Clinical trial information
    - Drug approvals and indications
    - Biomarker information
    - Treatment guidelines
    """

    # Search templates for different entity types
    SEARCH_TEMPLATES = {
        "trial": "clinical trial {entity} oncology results efficacy",
        "treatment": "FDA approval {entity} oncology indications mechanism",
        "biomarker": "biomarker {entity} cancer predictive prognostic testing",
        "disease": "{entity} cancer treatment guidelines NCCN",
        "general": "oncology {entity} clinical evidence"
    }

    def __init__(
        self,
        client: Optional[OpenRouterClient] = None,
        cache_ttl_minutes: int = 60,
        max_searches_per_question: int = 3
    ):
        """
        Initialize web search service.

        Args:
            client: OpenRouter client (creates default if None)
            cache_ttl_minutes: How long to cache search results
            max_searches_per_question: Maximum searches per question
        """
        self.client = client or get_openrouter_client()
        self.cache = SearchCache(ttl_minutes=cache_ttl_minutes)
        self.max_searches_per_question = max_searches_per_question
        self.search_count = 0

    def _build_query(self, entity: str, entity_type: Optional[str] = None) -> str:
        """Build search query from template."""
        template = self.SEARCH_TEMPLATES.get(entity_type, self.SEARCH_TEMPLATES["general"])
        return template.format(entity=entity)

    async def search(
        self,
        query: str,
        context: Optional[str] = None,
        use_cache: bool = True
    ) -> SearchResult:
        """
        Perform a web search.

        Args:
            query: Search query
            context: Optional context to include
            use_cache: Whether to use cached results

        Returns:
            SearchResult with content and metadata
        """
        # Check cache first
        if use_cache:
            cached = self.cache.get(query)
            if cached:
                logger.debug(f"Cache hit for query: {query[:50]}...")
                return cached

        try:
            response = await self.client.web_search(query=query, context=context)
            content = response.get("content", "")

            result = SearchResult(
                query=query,
                content=content,
                timestamp=datetime.utcnow()
            )

            # Cache the result
            self.cache.set(query, result)
            self.search_count += 1

            logger.info(f"Web search completed for: {query[:50]}...")
            return result

        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return SearchResult(
                query=query,
                content=f"Search failed: {str(e)}",
                timestamp=datetime.utcnow()
            )

    async def search_entity(
        self,
        entity_name: str,
        entity_type: Optional[str] = None,
        context: Optional[str] = None
    ) -> SearchResult:
        """
        Search for information about a specific entity.

        Args:
            entity_name: Name of the entity to search
            entity_type: Type of entity (trial, treatment, biomarker, disease)
            context: Optional context

        Returns:
            SearchResult with entity information
        """
        query = self._build_query(entity_name, entity_type)

        result = await self.search(query=query, context=context)
        result.entity_type = entity_type
        result.entity_name = entity_name

        return result

    async def search_multiple(
        self,
        entities: List[Dict[str, str]],
        context: Optional[str] = None
    ) -> List[SearchResult]:
        """
        Search for multiple entities.

        Args:
            entities: List of dicts with 'name' and optionally 'type'
            context: Optional shared context

        Returns:
            List of SearchResult objects
        """
        # Limit number of searches
        entities = entities[:self.max_searches_per_question]

        tasks = [
            self.search_entity(
                entity_name=e.get("name", ""),
                entity_type=e.get("type"),
                context=context
            )
            for e in entities
        ]

        return await asyncio.gather(*tasks)

    async def verify_trial(self, trial_name: str) -> Dict[str, Any]:
        """
        Verify a clinical trial name and get details.

        Args:
            trial_name: Name of the trial (e.g., "KEYNOTE-024")

        Returns:
            Dict with trial verification results
        """
        result = await self.search_entity(
            entity_name=trial_name,
            entity_type="trial",
            context="Verify this clinical trial name and provide key details: disease type, drugs studied, primary endpoints."
        )

        return {
            "trial_name": trial_name,
            "found": "not found" not in result.content.lower(),
            "details": result.content[:500],
            "search_timestamp": result.timestamp.isoformat()
        }

    async def lookup_drug(self, drug_name: str) -> Dict[str, Any]:
        """
        Look up drug information.

        Args:
            drug_name: Name of the drug

        Returns:
            Dict with drug information
        """
        result = await self.search_entity(
            entity_name=drug_name,
            entity_type="treatment",
            context="Provide FDA-approved indications, mechanism of action, and drug class."
        )

        return {
            "drug_name": drug_name,
            "info": result.content[:500],
            "search_timestamp": result.timestamp.isoformat()
        }

    async def check_recent_approvals(
        self,
        disease_state: str,
        months_back: int = 12
    ) -> Dict[str, Any]:
        """
        Check for recent drug approvals in a disease state.

        Args:
            disease_state: Disease to check
            months_back: How far back to look

        Returns:
            Dict with recent approval information
        """
        query = f"FDA drug approvals {disease_state} cancer {datetime.now().year}"

        result = await self.search(
            query=query,
            context=f"List FDA approvals for {disease_state} in the past {months_back} months."
        )

        return {
            "disease_state": disease_state,
            "recent_approvals": result.content[:1000],
            "search_timestamp": result.timestamp.isoformat()
        }

    def get_search_stats(self) -> Dict[str, Any]:
        """Get search service statistics."""
        return {
            "total_searches": self.search_count,
            "cached_results": len(self.cache.results),
            "cache_ttl_minutes": self.cache.ttl_minutes
        }

    def clear_cache(self):
        """Clear the search cache."""
        self.cache.results.clear()
        logger.info("Search cache cleared")


# Singleton instance
_service_instance: Optional[WebSearchService] = None


def get_web_search_service() -> WebSearchService:
    """Get or create web search service singleton."""
    global _service_instance
    if _service_instance is None:
        _service_instance = WebSearchService()
    return _service_instance
