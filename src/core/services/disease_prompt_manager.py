"""
Disease-Specific Prompt Manager.

Loads and manages disease-specific tagging prompts for Stage 2 of the
two-stage tagging architecture.
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

# Path to corrections directory (relative to project root)
CORRECTIONS_DIR = Path("data/corrections")


class DiseasePromptManager:
    """Loads and caches disease-specific tagging prompts."""

    # Mapping from Stage 1 disease_state to prompt filename
    # Used when the disease_state doesn't directly match a prompt file
    DISEASE_TO_PROMPT_MAPPING = {
        # Pan-heme and category fallbacks
        "Heme malignancies": "heme_malignancy_fallback",
        "MPN": "mpn_fallback",
        "NHL": "heme_malignancy_fallback",  # Generic NHL goes to pan-heme

        # Rare heme diseases → specific prompts
        "Waldenström": "waldenstrom",
        "Waldenstrom": "waldenstrom",  # Without umlaut
        "Waldenström macroglobulinemia": "waldenstrom",
        "PTCL": "ptcl",
        "Peripheral T-cell lymphoma": "ptcl",
        "BPDCN": "bpdcn",
        "MZL": "mzl",
        "Marginal zone lymphoma": "mzl",
        "CTCL": "ctcl",
        "Cutaneous T-cell lymphoma": "ctcl",
        "CMML": "cmml",
        "PCNSL": "rare_lymphoma_fallback",  # Use lymphoma fallback

        # Rare solid tumors → specific prompts or fallback
        "NF1-associated plexiform neurofibroma": "nf1",
        "Neuroblastoma": "neuroblastoma",
        "Desmoid tumor": "rare_solid_tumor_fallback",
        "Tenosynovial giant cell tumor": "rare_solid_tumor_fallback",
        "TGCT": "rare_solid_tumor_fallback",
        "Basal cell carcinoma": "rare_solid_tumor_fallback",
        "GIST": "rare_solid_tumor_fallback",
        "Mesothelioma": "rare_solid_tumor_fallback",
        "Cholangiocarcinoma": "rare_solid_tumor_fallback",
        "Cutaneous squamous cell carcinoma": "rare_solid_tumor_fallback",
        "LCNEC": "rare_solid_tumor_fallback",

        # Other mappings
        "Myelofibrosis": "mf",  # Alias
        "Polycythemia vera": "pv",
        "Essential thrombocythemia": "et",
    }

    # Category-specific fallbacks based on disease patterns
    # NOTE: Specific diseases (DLBCL, FL, MCL, etc.) have their own prompts
    # These fallbacks catch generic/unspecified disease names
    CATEGORY_FALLBACKS = {
        # If disease contains these patterns, use specific fallback
        "lymphoma": "heme_malignancy_fallback",  # Generic lymphoma → pan-heme
        "leukemia": "heme_malignancy_fallback",
        "myeloma": "heme_malignancy_fallback",
    }

    def __init__(self, prompt_version: str = "v2.0"):
        """
        Initialize prompt manager.

        Args:
            prompt_version: Prompt version to use (default: "v2.0")
        """
        self.prompt_version = prompt_version
        self.base_path = Path(f"prompts/{prompt_version}/disease_prompts")
        self.fallback_path = Path(f"prompts/{prompt_version}/fallback_prompt.txt")

        # Cache for loaded prompts
        self.disease_prompts: Dict[str, str] = {}
        self.fallback_prompt: Optional[str] = None

        logger.debug(f"Initialized DiseasePromptManager with version {prompt_version}")

    def _disease_to_filename(self, disease_state: str) -> str:
        """
        Convert disease state to filename.

        Args:
            disease_state: Canonical disease name (e.g., "Breast cancer")

        Returns:
            Filename without extension (e.g., "breast_cancer")

        Examples:
            >>> manager = DiseasePromptManager()
            >>> manager._disease_to_filename("Breast cancer")
            'breast_cancer'
            >>> manager._disease_to_filename("NSCLC")
            'nsclc'
            >>> manager._disease_to_filename("Esophagogastric / GEJ cancer")
            'esophagogastric_gej_cancer'
        """
        if disease_state is None:
            return "fallback"

        # Convert to lowercase
        filename = disease_state.lower()

        # Replace spaces and slashes with underscores
        filename = filename.replace(" / ", "_").replace("/", "_").replace(" ", "_")

        # Remove special characters
        filename = "".join(c for c in filename if c.isalnum() or c == "_")

        return filename

    def _load_prompt_file(self, filepath: Path) -> Optional[str]:
        """
        Load prompt from file.

        Args:
            filepath: Path to prompt file

        Returns:
            Prompt text or None if file doesn't exist
        """
        if not filepath.exists():
            logger.warning(f"Prompt file not found: {filepath}")
            return None

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                prompt_text = f.read()

            logger.debug(f"Loaded prompt from {filepath}")
            return prompt_text

        except Exception as e:
            logger.error(f"Error loading prompt file {filepath}: {e}")
            return None

    def get_prompt_for_disease(self, disease_state: Optional[str]) -> str:
        """
        Get disease-specific prompt.

        Uses a three-tier lookup:
        1. Check explicit DISEASE_TO_PROMPT_MAPPING
        2. Try converting disease_state to filename directly
        3. Check CATEGORY_FALLBACKS based on disease name patterns
        4. Use generic fallback_prompt.txt

        Args:
            disease_state: Canonical disease name (e.g., "Breast cancer")

        Returns:
            Disease-specific prompt text, or fallback if not available

        Example:
            >>> manager = DiseasePromptManager()
            >>> prompt = manager.get_prompt_for_disease("Breast cancer")
            >>> "HR+/HER2-" in prompt
            True
        """
        # Handle None or empty disease state
        if not disease_state:
            logger.info("No disease state provided, using fallback prompt")
            return self.get_fallback_prompt()

        # Check cache first
        if disease_state in self.disease_prompts:
            logger.debug(f"Using cached prompt for {disease_state}")
            return self.disease_prompts[disease_state]

        # Tier 1: Check explicit mapping
        if disease_state in self.DISEASE_TO_PROMPT_MAPPING:
            mapped_filename = self.DISEASE_TO_PROMPT_MAPPING[disease_state]
            filepath = self.base_path / f"{mapped_filename}_prompt.txt"
            prompt_text = self._load_prompt_file(filepath)
            if prompt_text:
                self.disease_prompts[disease_state] = prompt_text
                logger.info(f"Loaded mapped prompt '{mapped_filename}' for {disease_state}")
                return prompt_text

        # Tier 2: Try direct filename conversion
        filename = self._disease_to_filename(disease_state)
        filepath = self.base_path / f"{filename}_prompt.txt"
        prompt_text = self._load_prompt_file(filepath)

        if prompt_text:
            # Cache the prompt
            self.disease_prompts[disease_state] = prompt_text
            logger.info(f"Loaded disease-specific prompt for {disease_state}")
            return prompt_text

        # Tier 3: Check category fallbacks based on name patterns
        disease_lower = disease_state.lower()
        for pattern, fallback_name in self.CATEGORY_FALLBACKS.items():
            if pattern in disease_lower:
                fallback_filepath = self.base_path / f"{fallback_name}_prompt.txt"
                fallback_text = self._load_prompt_file(fallback_filepath)
                if fallback_text:
                    self.disease_prompts[disease_state] = fallback_text
                    logger.info(f"Using category fallback '{fallback_name}' for {disease_state}")
                    return fallback_text

        # Tier 4: Use generic fallback
        logger.warning(
            f"No specific prompt found for {disease_state}, using generic fallback"
        )
        return self.get_fallback_prompt()

    def get_fallback_prompt(self) -> str:
        """
        Get fallback prompt for diseases without specific rules.

        Returns:
            Generic tagging prompt text

        Raises:
            FileNotFoundError: If fallback prompt doesn't exist
        """
        # Check cache
        if self.fallback_prompt:
            return self.fallback_prompt

        # Load from file
        prompt_text = self._load_prompt_file(self.fallback_path)

        if prompt_text:
            # Cache the fallback
            self.fallback_prompt = prompt_text
            logger.info("Loaded fallback prompt")
            return prompt_text
        else:
            # If no fallback file exists, create a basic one from v1.0
            logger.warning("No fallback prompt found, using v1.0 system prompt")
            fallback_path_v1 = Path("prompts/v1.0/system_prompt.txt")

            if fallback_path_v1.exists():
                prompt_text = self._load_prompt_file(fallback_path_v1)
                if prompt_text:
                    self.fallback_prompt = prompt_text
                    return prompt_text

            # Last resort: raise error
            raise FileNotFoundError(
                f"No fallback prompt found at {self.fallback_path} or "
                f"prompts/v1.0/system_prompt.txt"
            )

    def preload_disease(self, disease_state: str) -> bool:
        """
        Preload a disease prompt into cache.

        Args:
            disease_state: Canonical disease name

        Returns:
            True if loaded successfully, False otherwise
        """
        prompt = self.get_prompt_for_disease(disease_state)
        return bool(prompt)

    def preload_common_diseases(self) -> int:
        """
        Preload prompts for common diseases.

        Returns:
            Number of prompts successfully loaded
        """
        common_diseases = [
            "Breast cancer",
            "NSCLC",
            "SCLC",
            "CRC",
            "Prostate cancer",
            "Multiple myeloma",
            "Ovarian cancer",
            "Melanoma",
        ]

        loaded = 0
        for disease in common_diseases:
            if self.preload_disease(disease):
                loaded += 1

        logger.info(f"Preloaded {loaded}/{len(common_diseases)} common disease prompts")
        return loaded

    def clear_cache(self):
        """Clear the prompt cache."""
        self.disease_prompts.clear()
        self.fallback_prompt = None
        logger.debug("Cleared prompt cache")

    def _normalize_disease_name(self, disease_state: str) -> str:
        """Normalize disease name for file naming."""
        if not disease_state:
            return "unknown"
        return disease_state.lower().replace(" ", "_").replace("/", "_")

    def _get_corrections_file(self, disease_state: str) -> Path:
        """Get the corrections file path for a disease."""
        disease_name = self._normalize_disease_name(disease_state)
        return CORRECTIONS_DIR / f"{disease_name}_corrections.jsonl"

    def load_corrections(self, disease_state: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Load recent human corrections for a disease state.

        Args:
            disease_state: The disease to load corrections for
            limit: Maximum number of corrections to return (most recent first)

        Returns:
            List of correction records, most recent first
        """
        corrections_file = self._get_corrections_file(disease_state)

        if not corrections_file.exists():
            logger.debug(f"No corrections file found for {disease_state}")
            return []

        try:
            corrections = []
            with open(corrections_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        corrections.append(json.loads(line))

            # Return most recent first
            recent = corrections[-limit:][::-1]
            logger.info(f"Loaded {len(recent)} corrections for {disease_state}")
            return recent

        except Exception as e:
            logger.error(f"Failed to load corrections for {disease_state}: {e}")
            return []

    def format_correction_as_fewshot(self, correction: Dict[str, Any]) -> str:
        """
        Format a correction record as a few-shot example.

        Returns a formatted string showing the question and corrected tags.
        """
        question_stem = correction.get('question_stem', '')
        correct_answer = correction.get('correct_answer', '')
        corrected_tags = correction.get('corrected_tags', {})
        edited_fields = correction.get('edited_fields', [])

        # Only include the tag fields, not metadata like confidence scores
        tag_fields_only = {
            k: v for k, v in corrected_tags.items()
            if not k.endswith('_confidence') and k not in ['topic_method', 'needs_review', 'review_flags', 'review_reason', 'flagged_at', 'agreement_level']
        }

        example = f"""**Question:** {question_stem}

**Correct Answer:** {correct_answer}

**Human-Verified Tags:**
```json
{json.dumps(tag_fields_only, indent=2, ensure_ascii=False)}
```

**Reviewer corrected:** {', '.join(edited_fields)}
"""
        return example

    def get_fewshot_examples(self, disease_state: str, count: int = 3) -> str:
        """
        Get formatted few-shot examples from recent human corrections.

        Args:
            disease_state: The disease to get examples for
            count: Number of examples to include

        Returns:
            Formatted string with few-shot examples to inject into prompt
        """
        corrections = self.load_corrections(disease_state, limit=count)

        if not corrections:
            return ""

        header = """
---

## Learn From Recent Human Corrections

The following questions were recently reviewed by a human expert who corrected the AI-generated tags.
Study these corrections carefully to understand the expected tagging patterns for this disease.

"""

        examples = []
        for i, correction in enumerate(corrections, 1):
            examples.append(f"### Human Correction #{i}\n\n{self.format_correction_as_fewshot(correction)}")

        return header + "\n\n".join(examples) + "\n\n---\n"

    def get_prompt_with_fewshots(self, disease_state: Optional[str], num_fewshots: int = 3) -> str:
        """
        Get disease-specific prompt WITH dynamic few-shot examples from human corrections.

        This is the primary method to use when tagging new questions.

        Args:
            disease_state: Canonical disease name
            num_fewshots: Number of recent corrections to include

        Returns:
            Complete prompt with disease rules + human corrections as examples
        """
        # Get base prompt
        base_prompt = self.get_prompt_for_disease(disease_state)

        if not disease_state:
            return base_prompt

        # Get few-shot examples
        fewshot_section = self.get_fewshot_examples(disease_state, count=num_fewshots)

        if not fewshot_section:
            logger.debug(f"No corrections available for {disease_state}, using base prompt only")
            return base_prompt

        # Inject few-shots before the final "Now analyze" instruction
        # Look for the marker at the end of the prompt
        marker = "Now analyze the following"
        if marker in base_prompt:
            parts = base_prompt.rsplit(marker, 1)
            enhanced_prompt = parts[0] + fewshot_section + "\n" + marker + parts[1]
        else:
            # If no marker, append at the end
            enhanced_prompt = base_prompt + "\n\n" + fewshot_section

        logger.info(f"Enhanced prompt with {num_fewshots} few-shot examples for {disease_state}")
        return enhanced_prompt


# Singleton instance
_prompt_manager_instance: Optional[DiseasePromptManager] = None


def get_disease_prompt_manager(prompt_version: str = "v2.0") -> DiseasePromptManager:
    """
    Get singleton DiseasePromptManager instance.

    Args:
        prompt_version: Prompt version to use

    Returns:
        DiseasePromptManager instance
    """
    global _prompt_manager_instance

    if _prompt_manager_instance is None:
        _prompt_manager_instance = DiseasePromptManager(prompt_version=prompt_version)

    return _prompt_manager_instance
