"""
Prompt Manager for V3.

Manages versioned prompt templates for the 3-model tagging system.
Supports iterative refinement based on human corrections.
"""

import json
import logging
import shutil
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
PROMPTS_DIR = PROJECT_ROOT / "prompts"
CORRECTIONS_DIR = PROJECT_ROOT / "data" / "corrections"


@dataclass
class PromptVersion:
    """A versioned prompt configuration."""
    version: str
    iteration: int
    system_prompt: str
    few_shot_examples: List[Dict] = field(default_factory=list)
    edge_cases: List[Dict] = field(default_factory=list)
    changelog: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    performance_metrics: Dict[str, float] = field(default_factory=dict)


class PromptManager:
    """
    Manages versioned prompts for the tagging system.

    Features:
    - Load/save prompt versions
    - Track performance metrics per version
    - Create new versions from corrections
    - Maintain changelog
    """

    def __init__(self, prompts_dir: Path = PROMPTS_DIR):
        """
        Initialize prompt manager.

        Args:
            prompts_dir: Directory containing prompt versions
        """
        self.prompts_dir = prompts_dir
        self.prompts_dir.mkdir(parents=True, exist_ok=True)

        self.current_version = self._detect_current_version()
        self._versions_cache: Dict[str, PromptVersion] = {}

        logger.info(f"Prompt manager initialized. Current version: {self.current_version}")

    def _detect_current_version(self) -> str:
        """Detect the current (latest) prompt version."""
        versions = self.list_versions()
        if versions:
            return versions[-1]  # Latest version
        return "v1.0"

    def list_versions(self) -> List[str]:
        """List all available prompt versions."""
        versions = []
        if self.prompts_dir.exists():
            for item in sorted(self.prompts_dir.iterdir()):
                if item.is_dir() and item.name.startswith("v"):
                    versions.append(item.name)
        return versions

    def load_version(self, version: str) -> PromptVersion:
        """
        Load a specific prompt version.

        Args:
            version: Version string (e.g., "v1.0")

        Returns:
            PromptVersion object
        """
        # Check cache first
        if version in self._versions_cache:
            return self._versions_cache[version]

        version_dir = self.prompts_dir / version

        if not version_dir.exists():
            raise ValueError(f"Prompt version not found: {version}")

        # Load system prompt
        system_prompt_path = version_dir / "system_prompt.txt"
        system_prompt = ""
        if system_prompt_path.exists():
            system_prompt = system_prompt_path.read_text(encoding="utf-8")

        # Load few-shot examples
        examples_path = version_dir / "few_shot_examples.json"
        few_shot_examples = []
        if examples_path.exists():
            few_shot_examples = json.loads(examples_path.read_text(encoding="utf-8"))

        # Load edge cases
        edge_cases_path = version_dir / "edge_cases.json"
        edge_cases = []
        if edge_cases_path.exists():
            edge_cases = json.loads(edge_cases_path.read_text(encoding="utf-8"))

        # Load changelog
        changelog_path = version_dir / "CHANGELOG.md"
        changelog = ""
        if changelog_path.exists():
            changelog = changelog_path.read_text(encoding="utf-8")

        # Load metadata
        metadata_path = version_dir / "metadata.json"
        metadata = {}
        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

        prompt_version = PromptVersion(
            version=version,
            iteration=metadata.get("iteration", 1),
            system_prompt=system_prompt,
            few_shot_examples=few_shot_examples,
            edge_cases=edge_cases,
            changelog=changelog,
            performance_metrics=metadata.get("performance_metrics", {})
        )

        # Cache it
        self._versions_cache[version] = prompt_version

        return prompt_version

    def get_current(self) -> PromptVersion:
        """Get the current (latest) prompt version."""
        return self.load_version(self.current_version)

    def save_version(self, prompt: PromptVersion):
        """
        Save a prompt version to disk.

        Args:
            prompt: PromptVersion to save
        """
        version_dir = self.prompts_dir / prompt.version
        version_dir.mkdir(parents=True, exist_ok=True)

        # Save system prompt
        (version_dir / "system_prompt.txt").write_text(
            prompt.system_prompt, encoding="utf-8"
        )

        # Save few-shot examples
        (version_dir / "few_shot_examples.json").write_text(
            json.dumps(prompt.few_shot_examples, indent=2), encoding="utf-8"
        )

        # Save edge cases
        (version_dir / "edge_cases.json").write_text(
            json.dumps(prompt.edge_cases, indent=2), encoding="utf-8"
        )

        # Save changelog
        (version_dir / "CHANGELOG.md").write_text(
            prompt.changelog, encoding="utf-8"
        )

        # Save metadata
        metadata = {
            "iteration": prompt.iteration,
            "created_at": prompt.created_at.isoformat(),
            "performance_metrics": prompt.performance_metrics
        }
        (version_dir / "metadata.json").write_text(
            json.dumps(metadata, indent=2), encoding="utf-8"
        )

        # Update cache
        self._versions_cache[prompt.version] = prompt

        logger.info(f"Saved prompt version: {prompt.version}")

    def create_new_version(
        self,
        base_version: Optional[str] = None,
        changes: Optional[str] = None
    ) -> PromptVersion:
        """
        Create a new prompt version based on an existing one.

        Args:
            base_version: Version to base on (defaults to current)
            changes: Description of changes for changelog

        Returns:
            New PromptVersion (not yet saved)
        """
        base = self.load_version(base_version or self.current_version)

        # Determine new version number
        versions = self.list_versions()
        if versions:
            last_version = versions[-1]
            # Parse version number (e.g., "v1.2" -> 1.2)
            try:
                major_minor = last_version[1:].split(".")
                major = int(major_minor[0])
                minor = int(major_minor[1]) if len(major_minor) > 1 else 0
                new_version = f"v{major}.{minor + 1}"
            except:
                new_version = f"v{len(versions) + 1}.0"
        else:
            new_version = "v1.0"

        # Create changelog entry
        changelog = base.changelog
        if changes:
            timestamp = datetime.utcnow().strftime("%Y-%m-%d")
            changelog = f"## {new_version} ({timestamp})\n\n{changes}\n\n{changelog}"

        return PromptVersion(
            version=new_version,
            iteration=base.iteration + 1,
            system_prompt=base.system_prompt,
            few_shot_examples=base.few_shot_examples.copy(),
            edge_cases=base.edge_cases.copy(),
            changelog=changelog,
            created_at=datetime.utcnow()
        )

    def add_example(
        self,
        question: str,
        tags: Dict[str, Any],
        version: Optional[str] = None
    ):
        """
        Add a few-shot example to a prompt version.

        Args:
            question: Example question text
            tags: Correct tags for the example
            version: Version to update (defaults to current)
        """
        prompt = self.load_version(version or self.current_version)

        # Check for duplicates
        for ex in prompt.few_shot_examples:
            if ex.get("question") == question:
                logger.warning("Example already exists, updating tags")
                ex["tags"] = tags
                self.save_version(prompt)
                return

        prompt.few_shot_examples.append({
            "question": question,
            "tags": tags,
            "added_at": datetime.utcnow().isoformat()
        })

        self.save_version(prompt)
        logger.info(f"Added example to {prompt.version}")

    def add_edge_case(
        self,
        description: str,
        question: str,
        expected_tags: Dict[str, Any],
        notes: Optional[str] = None,
        version: Optional[str] = None
    ):
        """
        Add an edge case to a prompt version.

        Args:
            description: Brief description of the edge case
            question: Example question
            expected_tags: Expected tag values
            notes: Additional notes
            version: Version to update (defaults to current)
        """
        prompt = self.load_version(version or self.current_version)

        prompt.edge_cases.append({
            "description": description,
            "question": question,
            "expected_tags": expected_tags,
            "notes": notes,
            "added_at": datetime.utcnow().isoformat()
        })

        self.save_version(prompt)
        logger.info(f"Added edge case to {prompt.version}")

    def update_metrics(
        self,
        version: str,
        metrics: Dict[str, float]
    ):
        """
        Update performance metrics for a prompt version.

        Args:
            version: Version to update
            metrics: Dict of metric name -> value
        """
        prompt = self.load_version(version)
        prompt.performance_metrics.update(metrics)
        self.save_version(prompt)

    def compare_versions(
        self,
        version1: str,
        version2: str
    ) -> Dict[str, Any]:
        """
        Compare two prompt versions.

        Args:
            version1: First version
            version2: Second version

        Returns:
            Dict with comparison results
        """
        v1 = self.load_version(version1)
        v2 = self.load_version(version2)

        return {
            "version1": version1,
            "version2": version2,
            "prompt_length_diff": len(v2.system_prompt) - len(v1.system_prompt),
            "examples_count": {
                version1: len(v1.few_shot_examples),
                version2: len(v2.few_shot_examples)
            },
            "edge_cases_count": {
                version1: len(v1.edge_cases),
                version2: len(v2.edge_cases)
            },
            "metrics": {
                version1: v1.performance_metrics,
                version2: v2.performance_metrics
            }
        }

    def set_current(self, version: str):
        """Set the current prompt version."""
        if version not in self.list_versions():
            raise ValueError(f"Version not found: {version}")

        self.current_version = version
        logger.info(f"Set current prompt version to: {version}")

    def get_disease_prompt(self, disease_state: str, version: str = "v2.0") -> Optional[str]:
        """
        Load disease-specific tagging prompt for Stage 2.

        Args:
            disease_state: Disease name (e.g., "Breast cancer", "NSCLC")
            version: Prompt version (default "v2.0")

        Returns:
            Disease-specific prompt string, or None if not found

        Example:
            >>> manager = PromptManager()
            >>> prompt = manager.get_disease_prompt("Breast cancer")
            >>> "HER2+" in prompt
            True
        """
        # Map disease_state to filename
        disease_filename = self._disease_to_filename(disease_state)

        # Try assembled prompt first (v2.0 modular system)
        assembled_path = self.prompts_dir / version / "disease_prompts" / f"{disease_filename}_prompt_v2.txt"
        if assembled_path.exists():
            logger.info(f"Loading assembled disease prompt for: {disease_state}")
            return assembled_path.read_text(encoding="utf-8")

        # Fallback to legacy disease_rules/*.md
        disease_rules_path = self.prompts_dir / version / "disease_rules" / f"{disease_filename}.md"
        if disease_rules_path.exists():
            logger.info(f"Loading disease-specific prompt for: {disease_state}")
            return disease_rules_path.read_text(encoding="utf-8")

        # Also try disease_prompts/*.txt (legacy naming)
        legacy_prompt_path = self.prompts_dir / version / "disease_prompts" / f"{disease_filename}_prompt.txt"
        if legacy_prompt_path.exists():
            logger.info(f"Loading legacy disease prompt for: {disease_state}")
            return legacy_prompt_path.read_text(encoding="utf-8")

        logger.warning(f"No disease-specific prompt found for: {disease_state}")
        return None

    def get_fallback_prompt(self, version: str = "v2.0") -> str:
        """
        Load fallback tagging prompt for diseases without specific rules.

        Args:
            version: Prompt version (default "v2.0")

        Returns:
            Fallback prompt string

        Example:
            >>> manager = PromptManager()
            >>> prompt = manager.get_fallback_prompt()
            >>> "KEYNOTE-756" in prompt
            True
        """
        fallback_path = self.prompts_dir / version / "fallback_prompt.txt"

        if fallback_path.exists():
            logger.info("Loading fallback prompt")
            return fallback_path.read_text(encoding="utf-8")
        else:
            raise FileNotFoundError(f"Fallback prompt not found at {fallback_path}")

    # Explicit mapping for diseases whose names don't convert cleanly to filenames.
    # Must stay in sync with DiseasePromptManager.DISEASE_TO_PROMPT_MAPPING.
    DISEASE_FILENAME_OVERRIDES = {
        "Hodgkin lymphoma": "hl",
        "HL": "hl",
        "cHL": "hl",
        "Waldenström": "waldenstrom",
        "Waldenstrom": "waldenstrom",
        "Waldenström macroglobulinemia": "waldenstrom",
        "Heme malignancies": "heme_malignancy_fallback",
        "MPN": "mpn_fallback",
        "NHL": "heme_malignancy_fallback",
        "PTCL": "ptcl",
        "Peripheral T-cell lymphoma": "ptcl",
        "BPDCN": "bpdcn",
        "MZL": "mzl",
        "Marginal zone lymphoma": "mzl",
        "CTCL": "ctcl",
        "Cutaneous T-cell lymphoma": "ctcl",
        "CMML": "cmml",
        "Myelofibrosis": "mf",
        "Polycythemia vera": "pv",
        "Essential thrombocythemia": "et",
    }

    def _disease_to_filename(self, disease_state: str) -> str:
        """
        Map disease_state to filename.

        Args:
            disease_state: Disease name (e.g., "Breast cancer", "NSCLC")

        Returns:
            Filename (e.g., "breast_cancer", "nsclc")

        Example:
            >>> manager = PromptManager()
            >>> manager._disease_to_filename("Breast cancer")
            "breast_cancer"
            >>> manager._disease_to_filename("NSCLC")
            "nsclc"
        """
        # Check explicit overrides first
        if disease_state in self.DISEASE_FILENAME_OVERRIDES:
            return self.DISEASE_FILENAME_OVERRIDES[disease_state]

        # Convert to lowercase and replace spaces/special chars with underscores
        filename = disease_state.lower()
        filename = filename.replace(" ", "_")
        filename = filename.replace("/", "_")
        filename = filename.replace("&", "and")
        filename = filename.strip("_")

        return filename

    def list_available_diseases(self, version: str = "v2.0") -> List[str]:
        """
        List all diseases with specific prompts available.

        Args:
            version: Prompt version (default "v2.0")

        Returns:
            List of disease names with available prompts

        Example:
            >>> manager = PromptManager()
            >>> diseases = manager.list_available_diseases()
            >>> "Breast cancer" in diseases
            True
        """
        diseases = set()

        # Check assembled prompts (v2.0 modular system)
        assembled_dir = self.prompts_dir / version / "disease_prompts"
        if assembled_dir.exists():
            for file_path in assembled_dir.glob("*_prompt_v2.txt"):
                # Convert filename back to disease name (remove _prompt_v2 suffix)
                disease_name = file_path.stem.replace("_prompt_v2", "").replace("_", " ").title()
                diseases.add(disease_name)

        # Also check legacy disease_rules/*.md
        disease_rules_dir = self.prompts_dir / version / "disease_rules"
        if disease_rules_dir.exists():
            for file_path in disease_rules_dir.glob("*.md"):
                disease_name = file_path.stem.replace("_", " ").title()
                diseases.add(disease_name)

        logger.debug(f"Found {len(diseases)} disease-specific prompts")
        return sorted(list(diseases))

    def _get_corrections_file(self, disease_state: str) -> Path:
        """Get the corrections file path for a disease."""
        disease_name = self._disease_to_filename(disease_state)
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
            if not k.endswith('_confidence') and k not in [
                'topic_method', 'needs_review', 'review_flags',
                'review_reason', 'flagged_at', 'agreement_level'
            ]
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

    def get_disease_prompt_with_fewshots(
        self,
        disease_state: str,
        version: str = "v2.0",
        num_fewshots: int = 3
    ) -> Optional[str]:
        """
        Get disease-specific prompt WITH dynamic few-shot examples from human corrections.

        This is the method to use for Stage 2 tagging to benefit from human corrections.

        Args:
            disease_state: Disease name
            version: Prompt version
            num_fewshots: Number of recent corrections to include as examples

        Returns:
            Complete prompt with disease rules + human corrections as examples
        """
        # Get base prompt
        base_prompt = self.get_disease_prompt(disease_state, version)

        if not base_prompt:
            return None

        # Get few-shot examples
        fewshot_section = self.get_fewshot_examples(disease_state, count=num_fewshots)

        if not fewshot_section:
            logger.debug(f"No corrections available for {disease_state}, using base prompt only")
            return base_prompt

        # Inject few-shots before the final "Now analyze" instruction
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
_manager_instance: Optional[PromptManager] = None


def get_prompt_manager() -> PromptManager:
    """Get or create prompt manager singleton."""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = PromptManager()
    return _manager_instance
