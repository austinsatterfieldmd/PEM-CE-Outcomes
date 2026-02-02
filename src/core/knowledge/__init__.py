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
    DISEASE_ABBREVIATIONS,
    DISEASE_SUBTYPES,
    VALID_DISEASE_STAGES,
    VALID_TREATMENT_LINES,
    PARANEOPLASTIC_SYNDROMES,
    MULTISPECIALTY_KEYWORDS,
)

from .topic_constants import TOPIC_TAGS, TOPIC_KEYWORDS

__all__ = [
    "KnowledgeEnricher",
    "DISEASE_STATES",
    "DISEASE_ABBREVIATIONS",
    "DISEASE_SUBTYPES",
    "VALID_DISEASE_STAGES",
    "VALID_TREATMENT_LINES",
    "PARANEOPLASTIC_SYNDROMES",
    "MULTISPECIALTY_KEYWORDS",
    "TOPIC_TAGS",
    "TOPIC_KEYWORDS",
]
