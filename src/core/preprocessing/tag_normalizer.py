"""
Tag Normalizer
==============
Normalizes tag values using rules from config/normalization_rules.yaml.

Applies alias mappings to ensure consistent terminology across all tagged questions.
This runs automatically before dashboard import to prevent conflicts like
"Infusion reaction" vs "infusion reaction".

Usage:
    from src.core.preprocessing.tag_normalizer import TagNormalizer

    normalizer = TagNormalizer()
    normalized_results = normalizer.normalize_results(results)
"""

import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

import yaml

logger = logging.getLogger(__name__)

# Project root for finding config files
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

# Tag containers to normalize
TAG_CONTAINERS = ["final_tags", "gpt_tags", "claude_tags", "gemini_tags"]

# Fields that should be normalized (multi-value fields with _1, _2, etc.)
NORMALIZABLE_FIELDS = [
    "treatment_1", "treatment_2", "treatment_3", "treatment_4", "treatment_5",
    "biomarker_1", "biomarker_2", "biomarker_3", "biomarker_4", "biomarker_5",
    "trial_1", "trial_2", "trial_3", "trial_4", "trial_5",
    "drug_class_1", "drug_class_2", "drug_class_3",
    "drug_target_1", "drug_target_2", "drug_target_3",
    "prior_therapy_1", "prior_therapy_2", "prior_therapy_3",
    "metastatic_site_1", "metastatic_site_2", "metastatic_site_3",
    "symptom_1", "symptom_2", "symptom_3",
    "toxicity_type_1", "toxicity_type_2", "toxicity_type_3",
    "toxicity_type_4", "toxicity_type_5", "toxicity_organ",
    "efficacy_endpoint_1", "efficacy_endpoint_2", "efficacy_endpoint_3",
    "disease_type", "disease_type_1", "disease_type_2",
    "resistance_mechanism", "special_population_1", "special_population_2",
    "disease_specific_factor", "treatment_line", "performance_status",
]

# Fields where first letter should always be capitalized (drug names, clinical terms)
PROPER_CASE_FIELDS = {
    "treatment_1", "treatment_2", "treatment_3", "treatment_4", "treatment_5",
    "prior_therapy_1", "prior_therapy_2", "prior_therapy_3",
    "drug_class_1", "drug_class_2", "drug_class_3",
    "toxicity_type_1", "toxicity_type_2", "toxicity_type_3",
    "toxicity_type_4", "toxicity_type_5",
    "symptom_1", "symptom_2", "symptom_3",
    "metastatic_site_1", "metastatic_site_2", "metastatic_site_3",
    "disease_specific_factor",
}


class TagNormalizer:
    """Normalizes tag values using alias mappings and canonical values."""

    def __init__(self, rules_path: Optional[Path] = None, canonicals_path: Optional[Path] = None):
        """Initialize normalizer with rules and canonical values files.

        Args:
            rules_path: Path to normalization_rules.yaml. Defaults to config/normalization_rules.yaml
            canonicals_path: Path to canonical_values.yaml. Defaults to config/canonical_values.yaml
        """
        if rules_path is None:
            rules_path = PROJECT_ROOT / "config" / "normalization_rules.yaml"
        if canonicals_path is None:
            canonicals_path = PROJECT_ROOT / "config" / "canonical_values.yaml"

        self.rules_path = rules_path
        self.canonicals_path = canonicals_path
        self.alias_lookup: Dict[str, str] = {}
        self.canonical_lookup: Dict[str, str] = {}  # lowercase -> canonical (for case-insensitive matching)
        self._load_rules()
        self._load_canonicals()

    def _load_rules(self) -> None:
        """Load normalization rules and build alias lookup."""
        if not self.rules_path.exists():
            logger.warning(f"Normalization rules not found: {self.rules_path}")
            return

        with open(self.rules_path, 'r', encoding='utf-8') as f:
            rules = yaml.safe_load(f) or {}

        # Build alias -> canonical lookup from all alias sections
        alias_sections = [
            "treatment_aliases",
            "biomarker_aliases",
            "trial_aliases",
            "drug_class_aliases",
            "disease_type_aliases",
            "efficacy_endpoint_aliases",
            "treatment_line_aliases",
            "performance_status_aliases",
        ]

        for section in alias_sections:
            section_data = rules.get(section, {})
            if isinstance(section_data, dict):
                for alias, canonical in section_data.items():
                    if alias and canonical and alias != canonical:
                        # Store both exact and lowercase for case-insensitive matching
                        self.alias_lookup[alias] = canonical
                        self.alias_lookup[alias.lower()] = canonical

        # Also load normalization_aliases (canonical -> [aliases] format)
        norm_aliases = rules.get("normalization_aliases", {})
        if isinstance(norm_aliases, dict):
            for canonical, aliases in norm_aliases.items():
                if isinstance(aliases, list):
                    for alias in aliases:
                        if alias and alias != canonical:
                            self.alias_lookup[alias] = canonical
                            self.alias_lookup[alias.lower()] = canonical

        logger.info(f"Loaded {len(self.alias_lookup)} normalization aliases")

    def _load_canonicals(self) -> None:
        """Load canonical values and build case-insensitive lookup."""
        if not self.canonicals_path.exists():
            logger.warning(f"Canonical values not found: {self.canonicals_path}")
            return

        with open(self.canonicals_path, 'r', encoding='utf-8') as f:
            canonicals = yaml.safe_load(f) or {}

        def extract_values(obj, prefix=""):
            """Recursively extract all string values from nested dict/list."""
            values = []
            if isinstance(obj, dict):
                for k, v in obj.items():
                    values.extend(extract_values(v, f"{prefix}.{k}" if prefix else k))
            elif isinstance(obj, list):
                for item in obj:
                    if isinstance(item, str):
                        values.append(item)
                    else:
                        values.extend(extract_values(item, prefix))
            return values

        # Extract all canonical values and build lowercase -> canonical lookup
        all_values = extract_values(canonicals)
        for val in all_values:
            if val:
                # Store lowercase -> canonical mapping
                self.canonical_lookup[val.lower()] = val

        logger.info(f"Loaded {len(self.canonical_lookup)} canonical values for case-insensitive matching")

    def normalize_value(self, value: Any) -> Any:
        """Normalize a single tag value.

        Priority:
        1. Exact alias match (from normalization_rules.yaml)
        2. Case-insensitive alias match
        3. Case-insensitive canonical match (from canonical_values.yaml)
        4. Return original value

        Args:
            value: Tag value to normalize

        Returns:
            Normalized value, or original if no mapping found
        """
        if not value or not isinstance(value, str):
            return value

        value_stripped = value.strip()

        # 1. Try exact alias match first
        if value_stripped in self.alias_lookup:
            return self.alias_lookup[value_stripped]

        # 2. Try case-insensitive alias match
        if value_stripped.lower() in self.alias_lookup:
            return self.alias_lookup[value_stripped.lower()]

        # 3. Try case-insensitive canonical match
        # This handles cases like "infusion reaction" -> "Infusion reaction"
        value_lower = value_stripped.lower()
        if value_lower in self.canonical_lookup:
            canonical = self.canonical_lookup[value_lower]
            # Only normalize if case differs (avoid redundant logging)
            if canonical != value_stripped:
                return canonical

        return value_stripped

    def is_known_value(self, value: Any) -> bool:
        """Check if a value is known (exists in canonical values or alias mappings).

        Args:
            value: Tag value to check

        Returns:
            True if value is known, False if it's a new/unknown value
        """
        if not value or not isinstance(value, str):
            return True  # Empty/null values are "known"

        value_stripped = value.strip()
        if not value_stripped:
            return True

        value_lower = value_stripped.lower()

        # Check alias mappings
        if value_stripped in self.alias_lookup or value_lower in self.alias_lookup:
            return True

        # Check canonical values
        if value_lower in self.canonical_lookup:
            return True

        return False

    def find_new_tag_values(self, tags: Dict[str, Any]) -> List[str]:
        """Find tag values that are not in known canonical values.

        Args:
            tags: Dict of field -> value

        Returns:
            List of field names with new/unknown values
        """
        new_value_fields = []

        for field in NORMALIZABLE_FIELDS:
            value = tags.get(field)
            if value and not self.is_known_value(value):
                new_value_fields.append(field)

        return new_value_fields

    @staticmethod
    def _ensure_proper_case(value: str) -> str:
        """Capitalize first letter of a value if it starts lowercase.

        Handles drug names (navtemadlin → Navtemadlin) while preserving:
        - Already capitalized values (Venetoclax → Venetoclax)
        - Abbreviations/special patterns (t(9;22), dMMR, PD-L1)
        - "Prior" prefixed values (Prior BTKi → Prior BTKi)
        """
        if not value or not value[0].islower():
            return value
        # Don't capitalize if starts with known lowercase patterns
        # like "t(9;22)", "del(17p)", etc.
        if value[0] == 't' and len(value) > 1 and value[1] == '(':
            return value
        if value.startswith("del(") or value.startswith("inv("):
            return value
        return value[0].upper() + value[1:]

    def normalize_tags(self, tags: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize all tag values in a tags dict.

        Args:
            tags: Dict of tag field -> value

        Returns:
            Dict with normalized values
        """
        if not tags:
            return tags

        normalized = dict(tags)
        for field in NORMALIZABLE_FIELDS:
            if field in normalized and normalized[field]:
                normalized[field] = self.normalize_value(normalized[field])
                # Apply proper-case fallback for drug names and clinical terms
                if field in PROPER_CASE_FIELDS and isinstance(normalized[field], str):
                    normalized[field] = self._ensure_proper_case(normalized[field])

        return normalized

    # Solid tumor disease states where treatment_line should be "1L" not "Newly diagnosed"
    _SOLID_TUMOR_DISEASES = {
        "breast cancer", "nsclc", "sclc", "crc", "colorectal cancer",
        "prostate cancer", "ovarian cancer", "bladder cancer", "urothelial carcinoma",
        "renal cell carcinoma", "hepatocellular carcinoma", "gastric cancer",
        "esophageal cancer", "head and neck cancer", "melanoma", "cervical cancer",
        "endometrial cancer", "pancreatic cancer", "cholangiocarcinoma",
        "thyroid cancer", "mesothelioma", "sarcoma", "glioma",
    }

    def _apply_cross_field_rules(self, tags: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Apply cross-field normalization rules that depend on multiple tag values.

        Modifies tags dict in place.

        Rules:
        - If answer_length_pattern is null/conflict AND distractor_homogeneity is
          "Homogeneous", default answer_length_pattern to "Uniform"
        - If treatment_line is "Newly diagnosed" AND disease is a solid tumor,
          normalize to "1L" (solid tumors use line-of-therapy, not diagnosis timing)
        """
        qid = result.get('question_id', '?')

        # Rule 1: Homogeneous distractors → Uniform answer length
        distractor = tags.get("distractor_homogeneity")
        answer_length = tags.get("answer_length_pattern")

        if distractor and distractor.strip().lower() == "homogeneous":
            if not answer_length or answer_length.strip() == "":
                tags["answer_length_pattern"] = "Uniform"
                logger.info(
                    f"Q{qid}: Normalized answer_length_pattern to 'Uniform' "
                    f"(conflict resolved by homogeneous distractor rule)"
                )

        # Rule 2: "Newly diagnosed" → "1L" for solid tumors
        treatment_line = tags.get("treatment_line")
        disease_state = (tags.get("disease_state") or "").strip().lower()

        if treatment_line and treatment_line.strip().lower() == "newly diagnosed":
            if disease_state in self._SOLID_TUMOR_DISEASES:
                tags["treatment_line"] = "1L"
                logger.info(
                    f"Q{qid}: Normalized treatment_line 'Newly diagnosed' -> '1L' "
                    f"(solid tumor: {tags.get('disease_state')})"
                )

    def normalize_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a single question result.

        Args:
            result: Question result dict with tag containers

        Returns:
            Result with normalized tags
        """
        normalized = dict(result)
        changes = []

        # Normalize each tag container
        for container_name in TAG_CONTAINERS:
            if container_name in normalized and isinstance(normalized[container_name], dict):
                original = normalized[container_name]
                normalized[container_name] = self.normalize_tags(original)

                # Track changes
                for field in NORMALIZABLE_FIELDS:
                    if field in original and original[field] != normalized[container_name].get(field):
                        changes.append(f"{container_name}.{field}: '{original[field]}' -> '{normalized[container_name][field]}'")

        # Also normalize field_votes
        if "field_votes" in normalized and isinstance(normalized["field_votes"], dict):
            for field, vote in normalized["field_votes"].items():
                if isinstance(vote, dict):
                    for vote_key in ["final_value", "gpt_value", "claude_value", "gemini_value"]:
                        if vote_key in vote and vote[vote_key]:
                            original_val = vote[vote_key]
                            vote[vote_key] = self.normalize_value(original_val)
                            if original_val != vote[vote_key]:
                                changes.append(f"field_votes.{field}.{vote_key}: '{original_val}' -> '{vote[vote_key]}'")

        if changes:
            qid = result.get("question_id", "?")
            logger.debug(f"Q{qid} normalized: {len(changes)} changes")

        # Cross-field normalization rules
        final_tags = normalized.get("final_tags", {})
        self._apply_cross_field_rules(final_tags, normalized)

        # Check for new tag values and flag for review
        new_value_fields = self.find_new_tag_values(final_tags)

        if new_value_fields:
            qid = result.get("question_id", "?")
            # Flag for review
            normalized["needs_review"] = True

            # Append to review_reason
            new_values_reason = f"new_tag_values:{','.join(new_value_fields)}"
            existing_reason = normalized.get("review_reason", "")
            if existing_reason:
                normalized["review_reason"] = f"{existing_reason}|{new_values_reason}"
            else:
                normalized["review_reason"] = new_values_reason

            # Log the new values for visibility
            new_vals = {f: final_tags.get(f) for f in new_value_fields}
            logger.info(f"Q{qid} flagged for review - new tag values: {new_vals}")

        return normalized

    def normalize_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize a list of question results.

        Args:
            results: List of question result dicts

        Returns:
            List of results with normalized tags
        """
        if not results:
            return results

        normalized = []
        total_questions_modified = 0

        for result in results:
            # Skip error results
            if "error" in result:
                normalized.append(result)
                continue

            original_json = str(result)
            norm_result = self.normalize_result(result)

            if str(norm_result) != original_json:
                total_questions_modified += 1

            normalized.append(norm_result)

        if total_questions_modified > 0:
            logger.info(f"Normalized {total_questions_modified}/{len(results)} questions")

        return normalized


def normalize_results(results: List[Dict[str, Any]], rules_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Convenience function to normalize results.

    Args:
        results: List of question result dicts
        rules_path: Optional path to normalization rules file

    Returns:
        List of normalized results
    """
    normalizer = TagNormalizer(rules_path)
    return normalizer.normalize_results(results)
