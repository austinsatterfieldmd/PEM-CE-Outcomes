"""
V3 Knowledge layer.

Domain knowledge for oncology CME tagging including:
- Disease states, topics, treatments, biomarkers, trials
- Synonym mappings and validation rules
- Knowledge enrichment for pre-LLM context
"""

from .enricher import KnowledgeEnricher

# Re-export constants for convenience
from .constants import (
    DISEASE_STATES,
    DISEASE_STAGES,
    DISEASE_TYPES,
    TREATMENT_LINES,
    BIOMARKERS,
)

from .topic_constants import TOPICS, TOPIC_KEYWORDS

__all__ = [
    "KnowledgeEnricher",
    "DISEASE_STATES",
    "DISEASE_STAGES",
    "DISEASE_TYPES",
    "TREATMENT_LINES",
    "BIOMARKERS",
    "TOPICS",
    "TOPIC_KEYWORDS",
]
