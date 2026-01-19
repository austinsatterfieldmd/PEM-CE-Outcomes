"""
Disease-Specific Prompt Manager.

Loads and manages disease-specific tagging prompts for Stage 2 of the
two-stage tagging architecture.
"""

import logging
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class DiseasePromptManager:
    """Loads and caches disease-specific tagging prompts."""

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

        # Load from file
        filename = self._disease_to_filename(disease_state)
        filepath = self.base_path / f"{filename}_prompt.txt"

        prompt_text = self._load_prompt_file(filepath)

        if prompt_text:
            # Cache the prompt
            self.disease_prompts[disease_state] = prompt_text
            logger.info(f"Loaded disease-specific prompt for {disease_state}")
            return prompt_text
        else:
            # Fall back to generic prompt
            logger.warning(
                f"No specific prompt found for {disease_state}, using fallback"
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
            "Multiple Myeloma",
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
