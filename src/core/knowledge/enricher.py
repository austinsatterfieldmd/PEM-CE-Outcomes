"""
Knowledge Enricher for V3.

Pre-processes questions to extract context from the static knowledge base
before sending to LLMs. This helps the models by:
1. Providing canonical entity names
2. Suggesting possible values for ambiguous cases
3. Extracting known entities mentioned in the question
"""

import json
import logging
import re
from typing import Dict, Any, List, Optional, Set, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
KB_PATH = PROJECT_ROOT / "knowledge_base" / "oncology_entities.json"


class KnowledgeEnricher:
    """
    Enriches questions with knowledge base context before LLM tagging.

    Extracts mentions of known entities and provides context to help
    models make better tagging decisions.
    """

    def __init__(self, kb_path: Path = KB_PATH):
        """
        Initialize knowledge enricher.

        Args:
            kb_path: Path to knowledge base JSON file
        """
        self.kb_path = kb_path
        self.kb_data = self._load_kb()

        # Build lookup structures
        self.diseases = self._build_disease_lookup()
        self.treatments = self._build_treatment_lookup()
        self.trials = self._build_trial_lookup()
        self.biomarkers = self._build_biomarker_lookup()

        logger.info(
            f"Knowledge enricher initialized: {len(self.diseases)} diseases, "
            f"{len(self.treatments)} treatments, {len(self.trials)} trials, "
            f"{len(self.biomarkers)} biomarkers"
        )

    def _load_kb(self) -> Dict[str, Any]:
        """Load knowledge base from JSON file."""
        if not self.kb_path.exists():
            logger.warning(f"Knowledge base not found at {self.kb_path}")
            return {}

        try:
            with open(self.kb_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load knowledge base: {e}")
            return {}

    def _build_disease_lookup(self) -> Dict[str, str]:
        """Build disease name -> canonical name lookup."""
        lookup = {}

        # Add diseases from KB
        for disease in self.kb_data.get("diseases", []):
            name = disease.get("name", "")
            if name:
                lookup[name.lower()] = name

            # Add synonyms
            for syn in disease.get("synonyms", []):
                lookup[syn.lower()] = name

        # Add disease types
        for dtype in self.kb_data.get("disease_types", []):
            name = dtype.get("name", "")
            if name:
                lookup[name.lower()] = name

        return lookup

    def _build_treatment_lookup(self) -> Dict[str, Dict[str, Any]]:
        """Build treatment name -> info lookup."""
        lookup = {}

        for treatment in self.kb_data.get("treatments", []):
            name = treatment.get("name", "")
            if name:
                info = {
                    "canonical_name": name,
                    "drug_class": treatment.get("drug_class"),
                    "mechanism": treatment.get("mechanism")
                }
                lookup[name.lower()] = info

                # Add synonyms
                for syn in treatment.get("synonyms", []):
                    lookup[syn.lower()] = info

        return lookup

    def _build_trial_lookup(self) -> Dict[str, Dict[str, Any]]:
        """Build trial name -> info lookup."""
        lookup = {}

        for trial in self.kb_data.get("trials", []):
            name = trial.get("name", "")
            if name:
                info = {
                    "canonical_name": name,
                    "disease": trial.get("disease"),
                    "drugs": trial.get("drugs", [])
                }
                lookup[name.lower()] = info

        return lookup

    def _build_biomarker_lookup(self) -> Dict[str, str]:
        """Build biomarker name -> canonical name lookup."""
        lookup = {}

        for biomarker in self.kb_data.get("biomarkers", []):
            name = biomarker.get("name", "")
            if name:
                lookup[name.lower()] = name

                # Add synonyms
                for syn in biomarker.get("synonyms", []):
                    lookup[syn.lower()] = name

        return lookup

    def _extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extract known entities from text.

        Args:
            text: Text to search for entities

        Returns:
            Dict mapping entity type to list of found entities
        """
        text_lower = text.lower()
        found = {
            "diseases": [],
            "treatments": [],
            "trials": [],
            "biomarkers": []
        }

        # Search for diseases
        for pattern, canonical in self.diseases.items():
            if pattern in text_lower and canonical not in found["diseases"]:
                found["diseases"].append(canonical)

        # Search for treatments
        for pattern, info in self.treatments.items():
            if pattern in text_lower:
                canonical = info["canonical_name"]
                if canonical not in found["treatments"]:
                    found["treatments"].append(canonical)

        # Search for trials (case-sensitive for trial names like KEYNOTE-024)
        for pattern, info in self.trials.items():
            # Also check original case
            canonical = info["canonical_name"]
            if canonical in text or pattern in text_lower:
                if canonical not in found["trials"]:
                    found["trials"].append(canonical)

        # Search for biomarkers
        for pattern, canonical in self.biomarkers.items():
            if pattern in text_lower and canonical not in found["biomarkers"]:
                found["biomarkers"].append(canonical)

        return found

    def _get_disease_context(self, diseases: List[str]) -> List[Dict[str, Any]]:
        """Get detailed context for found diseases."""
        context = []
        for disease in diseases[:3]:  # Limit to top 3
            for d in self.kb_data.get("diseases", []):
                if d.get("name") == disease:
                    context.append({
                        "name": disease,
                        "category": d.get("category"),
                        "common_stages": d.get("stages", []),
                        "common_biomarkers": d.get("biomarkers", [])[:5]
                    })
                    break
        return context

    def _get_treatment_context(self, treatments: List[str]) -> List[Dict[str, Any]]:
        """Get detailed context for found treatments."""
        context = []
        for treatment in treatments[:5]:  # Limit to top 5
            info = self.treatments.get(treatment.lower())
            if info:
                context.append({
                    "name": info["canonical_name"],
                    "drug_class": info.get("drug_class"),
                    "mechanism": info.get("mechanism")
                })
        return context

    def _get_trial_context(self, trials: List[str]) -> List[Dict[str, Any]]:
        """Get detailed context for found trials."""
        context = []
        for trial in trials[:3]:  # Limit to top 3
            info = self.trials.get(trial.lower())
            if info:
                context.append({
                    "name": info["canonical_name"],
                    "disease": info.get("disease"),
                    "drugs": info.get("drugs", [])[:3]
                })
        return context

    def enrich(
        self,
        question_text: str,
        correct_answer: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Enrich a question with knowledge base context.

        Args:
            question_text: The question stem text
            correct_answer: Optional correct answer text

        Returns:
            Dict with extracted entities and context
        """
        # Combine question and answer for entity extraction
        full_text = question_text
        if correct_answer:
            full_text += " " + correct_answer

        # Extract entities
        found = self._extract_entities(full_text)

        # Build context
        context = {
            "extracted_entities": found,
            "disease_context": self._get_disease_context(found["diseases"]),
            "treatment_context": self._get_treatment_context(found["treatments"]),
            "trial_context": self._get_trial_context(found["trials"]),
            "has_known_entities": any(found.values())
        }

        # Add suggestions if certain fields are missing
        if not found["diseases"] and found["treatments"]:
            # Try to infer disease from treatment
            for treatment in found["treatments"]:
                info = self.treatments.get(treatment.lower(), {})
                # Could add disease inference logic here

        return context

    def get_canonical_name(
        self,
        entity_name: str,
        entity_type: str
    ) -> Optional[str]:
        """
        Get canonical name for an entity.

        Args:
            entity_name: Entity name to look up
            entity_type: Type of entity (disease, treatment, trial, biomarker)

        Returns:
            Canonical name if found, None otherwise
        """
        name_lower = entity_name.lower()

        if entity_type == "disease":
            return self.diseases.get(name_lower)
        elif entity_type == "treatment":
            info = self.treatments.get(name_lower)
            return info["canonical_name"] if info else None
        elif entity_type == "trial":
            info = self.trials.get(name_lower)
            return info["canonical_name"] if info else None
        elif entity_type == "biomarker":
            return self.biomarkers.get(name_lower)

        return None

    def is_known_entity(self, entity_name: str) -> Tuple[bool, Optional[str]]:
        """
        Check if an entity is in the knowledge base.

        Args:
            entity_name: Entity name to check

        Returns:
            Tuple of (is_known, entity_type)
        """
        name_lower = entity_name.lower()

        if name_lower in self.diseases:
            return True, "disease"
        if name_lower in self.treatments:
            return True, "treatment"
        if name_lower in self.trials:
            return True, "trial"
        if name_lower in self.biomarkers:
            return True, "biomarker"

        return False, None

    def get_stats(self) -> Dict[str, int]:
        """Get knowledge base statistics."""
        return {
            "diseases": len(self.diseases),
            "treatments": len(self.treatments),
            "trials": len(self.trials),
            "biomarkers": len(self.biomarkers)
        }


# Singleton instance
_enricher_instance: Optional[KnowledgeEnricher] = None


def get_knowledge_enricher() -> KnowledgeEnricher:
    """Get or create knowledge enricher singleton."""
    global _enricher_instance
    if _enricher_instance is None:
        _enricher_instance = KnowledgeEnricher()
    return _enricher_instance
