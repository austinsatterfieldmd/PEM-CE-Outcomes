"""
Corrections service for capturing human edits for few-shot learning.
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Path to corrections directory (relative to project root)
CORRECTIONS_DIR = Path(__file__).parent.parent.parent.parent / "data" / "corrections"


def normalize_disease_name(disease_state: str) -> str:
    """Normalize disease name for file naming."""
    if not disease_state:
        return "unknown"
    return disease_state.lower().replace(" ", "_").replace("/", "_")


def get_corrections_file(disease_state: str) -> Path:
    """Get the corrections file path for a disease."""
    CORRECTIONS_DIR.mkdir(parents=True, exist_ok=True)
    disease_name = normalize_disease_name(disease_state)
    return CORRECTIONS_DIR / f"{disease_name}_corrections.jsonl"


def find_edited_fields(original_tags: Dict[str, Any], corrected_tags: Dict[str, Any]) -> List[str]:
    """
    Compare original and corrected tags to find which fields were edited.
    Returns list of field names that were changed.
    """
    edited_fields = []

    # All tag fields we care about (excluding metadata like confidence scores)
    tag_fields = [
        'topic', 'disease_state', 'disease_stage', 'disease_type_1', 'disease_type_2', 'treatment_line',
        'treatment_1', 'treatment_2', 'treatment_3', 'treatment_4', 'treatment_5',
        'biomarker_1', 'biomarker_2', 'biomarker_3', 'biomarker_4', 'biomarker_5',
        'trial_1', 'trial_2', 'trial_3', 'trial_4', 'trial_5',
        'treatment_eligibility', 'age_group', 'organ_dysfunction', 'fitness_status', 'disease_specific_factor',
        'comorbidity_1', 'comorbidity_2', 'comorbidity_3',
        'drug_class_1', 'drug_class_2', 'drug_class_3',
        'drug_target_1', 'drug_target_2', 'drug_target_3',
        'prior_therapy_1', 'prior_therapy_2', 'prior_therapy_3',
        'resistance_mechanism',
        'metastatic_site_1', 'metastatic_site_2', 'metastatic_site_3',
        'symptom_1', 'symptom_2', 'symptom_3',
        'performance_status',
        'toxicity_type_1', 'toxicity_type_2', 'toxicity_type_3', 'toxicity_type_4', 'toxicity_type_5',
        'toxicity_organ', 'toxicity_grade',
        'efficacy_endpoint_1', 'efficacy_endpoint_2', 'efficacy_endpoint_3',
        'outcome_context', 'clinical_benefit',
        'guideline_source_1', 'guideline_source_2', 'evidence_type',
        'cme_outcome_level', 'data_response_type', 'stem_type', 'lead_in_type',
        'answer_format', 'answer_length_pattern', 'distractor_homogeneity',
        'flaw_absolute_terms', 'flaw_grammatical_cue', 'flaw_implausible_distractor',
        'flaw_clang_association', 'flaw_convergence_vulnerability', 'flaw_double_negative',
    ]

    for field in tag_fields:
        original_value = original_tags.get(field)
        corrected_value = corrected_tags.get(field)

        # Normalize None and empty string
        if original_value == '':
            original_value = None
        if corrected_value == '':
            corrected_value = None

        # Check if values differ
        if original_value != corrected_value:
            edited_fields.append(field)

    return edited_fields


def save_correction(
    question_id: int,
    question_stem: str,
    correct_answer: Optional[str],
    incorrect_answers: Optional[List[str]],
    disease_state: str,
    original_tags: Dict[str, Any],
    corrected_tags: Dict[str, Any],
    source_question_id: Optional[int] = None,
    source_id: Optional[str] = None,
) -> Optional[str]:
    """
    Save a correction record to the disease-specific JSONL file.

    Args:
        question_id: Internal DB auto-increment ID
        source_question_id: DataFrame index from checkpoint (stable across re-imports)
        source_id: QUESTIONGROUPDESIGNATION (QGD) — the stable key linking to Excel

    Returns the path to the corrections file if successful, None otherwise.
    """
    try:
        # Find which fields were edited
        edited_fields = find_edited_fields(original_tags, corrected_tags)

        if not edited_fields:
            logger.info(f"No fields changed for question {question_id}, skipping correction save")
            return None

        # Create correction record
        correction = {
            "question_id": question_id,
            "source_question_id": source_question_id,
            "source_id": source_id,
            "question_stem": question_stem,
            "correct_answer": correct_answer,
            "incorrect_answers": incorrect_answers,
            "disease_state": disease_state,
            "original_tags": original_tags,
            "corrected_tags": corrected_tags,
            "edited_fields": edited_fields,
            "corrected_at": datetime.now().isoformat(),
        }

        # Get file path and append
        corrections_file = get_corrections_file(disease_state)

        with open(corrections_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(correction, ensure_ascii=False) + '\n')

        logger.info(f"Saved correction for question {question_id}: {len(edited_fields)} fields edited")
        logger.info(f"Edited fields: {edited_fields}")

        # Auto-learn normalization mappings from case/formatting corrections
        norm_mappings = learn_normalization_from_correction(original_tags, corrected_tags)
        if norm_mappings:
            added = update_normalization_rules(norm_mappings)
            if added > 0:
                logger.info(f"Auto-learned {added} normalization mappings from this correction")

        return str(corrections_file)

    except Exception as e:
        logger.error(f"Failed to save correction for question {question_id}: {e}")
        return None


def load_corrections(disease_state: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Load recent corrections for a disease state.

    Args:
        disease_state: The disease to load corrections for
        limit: Maximum number of corrections to return (most recent first)

    Returns:
        List of correction records, most recent first
    """
    corrections_file = get_corrections_file(disease_state)

    if not corrections_file.exists():
        return []

    try:
        corrections = []
        with open(corrections_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    corrections.append(json.loads(line))

        # Return most recent first
        return corrections[-limit:][::-1]

    except Exception as e:
        logger.error(f"Failed to load corrections for {disease_state}: {e}")
        return []


def is_normalization_correction(original: str, corrected: str) -> bool:
    """
    Check if a correction is a normalization-type change (case, punctuation, abbreviation).

    Returns True if the correction should be added to normalization_rules.yaml.
    """
    if not original or not corrected:
        return False

    original = str(original).strip()
    corrected = str(corrected).strip()

    # Same value after stripping
    if original == corrected:
        return False

    # Case-insensitive match = pure case normalization
    if original.lower() == corrected.lower():
        return True

    # Minor punctuation/spacing differences
    # e.g., "t(4;14)" vs "t4;14" or "infusion reaction" vs "Infusion reaction"
    original_norm = original.lower().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    corrected_norm = corrected.lower().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if original_norm == corrected_norm:
        return True

    return False


def learn_normalization_from_correction(original_tags: Dict[str, Any], corrected_tags: Dict[str, Any]) -> List[tuple]:
    """
    Extract normalization mappings from a correction.

    Returns list of (original_value, canonical_value) tuples that should be added to rules.
    """
    mappings = []

    for field in find_edited_fields(original_tags, corrected_tags):
        original = original_tags.get(field)
        corrected = corrected_tags.get(field)

        if original and corrected and is_normalization_correction(original, corrected):
            mappings.append((str(original).strip(), str(corrected).strip()))

    return mappings


def register_verified_canonical_values(tags: Dict[str, Any], db=None) -> int:
    """
    Register verified tag values as canonical for future normalization.

    When a user reviews a question and confirms tags, any non-null values
    become canonical. Future case variations will normalize to these values.

    This function:
    1. Adds to canonical_values.yaml (for backend normalization)
    2. Adds to user_values database table (for frontend dropdown display)

    Args:
        tags: Dict of field -> value from reviewed question
        db: Optional database instance (if None, will get from get_database)

    Returns:
        Number of new canonical values registered
    """
    import yaml
    from .database import get_database

    canonicals_file = Path(__file__).parent.parent.parent.parent / "config" / "canonical_values.yaml"

    # Fields that should be tracked for canonicalization
    trackable_fields = [
        "treatment_1", "treatment_2", "treatment_3", "treatment_4", "treatment_5",
        "biomarker_1", "biomarker_2", "biomarker_3", "biomarker_4", "biomarker_5",
        "trial_1", "trial_2", "trial_3", "trial_4", "trial_5",
        "drug_class_1", "drug_class_2", "drug_class_3",
        "toxicity_type_1", "toxicity_type_2", "toxicity_type_3", "toxicity_type_4", "toxicity_type_5",
        "toxicity_organ", "efficacy_endpoint_1", "efficacy_endpoint_2", "efficacy_endpoint_3",
        "disease_type_1", "disease_type_2", "symptom_1", "symptom_2", "symptom_3",
        "metastatic_site_1", "metastatic_site_2", "metastatic_site_3",
        "prior_therapy_1", "prior_therapy_2", "prior_therapy_3",
    ]

    try:
        if canonicals_file.exists():
            with open(canonicals_file, 'r', encoding='utf-8') as f:
                canonicals = yaml.safe_load(f) or {}
        else:
            canonicals = {}

        # Get or create verified_values section
        verified = canonicals.get("verified_values", {})

        # Get database for user_values table
        if db is None:
            db = get_database()

        added = 0
        for field in trackable_fields:
            value = tags.get(field)
            if not value or not isinstance(value, str):
                continue

            value = value.strip()
            if not value:
                continue

            # Get base field name (treatment, biomarker, etc.)
            base_field = field.rsplit('_', 1)[0] if field[-1].isdigit() else field

            # Initialize field list if needed
            if base_field not in verified:
                verified[base_field] = []

            # Check if value already exists (case-insensitive)
            existing_lower = [v.lower() for v in verified[base_field]]
            if value.lower() not in existing_lower:
                verified[base_field].append(value)
                logger.info(f"Registered new canonical value: {base_field} = '{value}'")
                added += 1

                # Also add to user_values database table (for frontend dropdown display)
                # Use the original field name (with number suffix) so it appears in the right dropdown
                try:
                    db.add_user_defined_value(field, value, created_by="auto_verified")
                except Exception as db_err:
                    logger.warning(f"Could not add to user_values table: {db_err}")

        if added > 0:
            canonicals["verified_values"] = verified

            with open(canonicals_file, 'w', encoding='utf-8') as f:
                yaml.dump(canonicals, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

            logger.info(f"Updated canonical values: added {added} new verified values")

        return added

    except Exception as e:
        logger.error(f"Failed to register canonical values: {e}")
        return 0


def update_normalization_rules(mappings: List[tuple]) -> int:
    """
    Add new normalization mappings to config/normalization_rules.yaml.

    Args:
        mappings: List of (alias, canonical) tuples

    Returns:
        Number of new mappings added
    """
    import yaml

    rules_file = Path(__file__).parent.parent.parent.parent / "config" / "normalization_rules.yaml"

    try:
        if rules_file.exists():
            with open(rules_file, 'r', encoding='utf-8') as f:
                rules = yaml.safe_load(f) or {}
        else:
            rules = {}

        # Get or create the normalization_aliases section
        norm_aliases = rules.get("normalization_aliases", {})

        added = 0
        for alias, canonical in mappings:
            if alias == canonical:
                continue

            # Add to aliases dict: canonical -> [list of aliases]
            if canonical not in norm_aliases:
                norm_aliases[canonical] = []

            if alias not in norm_aliases[canonical]:
                norm_aliases[canonical].append(alias)
                logger.info(f"Learned normalization: '{alias}' -> '{canonical}'")
                added += 1

        if added > 0:
            rules["normalization_aliases"] = norm_aliases

            # Update metadata
            from datetime import datetime
            rules.setdefault("_metadata", {})
            rules["_metadata"]["last_updated"] = datetime.now().isoformat()
            rules["_metadata"]["total_aliases"] = sum(len(v) for v in norm_aliases.values())

            with open(rules_file, 'w', encoding='utf-8') as f:
                yaml.dump(rules, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

            logger.info(f"Updated normalization rules: added {added} new aliases")

        return added

    except Exception as e:
        logger.error(f"Failed to update normalization rules: {e}")
        return 0


def format_correction_as_fewshot(correction: Dict[str, Any]) -> str:
    """
    Format a correction record as a few-shot example for LLM prompts.

    Returns a formatted string showing the question and corrected tags.
    """
    question_stem = correction.get('question_stem', '')
    correct_answer = correction.get('correct_answer', '')
    corrected_tags = correction.get('corrected_tags', {})
    edited_fields = correction.get('edited_fields', [])

    # Build the example
    example = f"""**Question:** {question_stem}

**Correct Answer:** {correct_answer}

**Human-Corrected Tags:**
```json
{json.dumps(corrected_tags, indent=2, ensure_ascii=False)}
```

**Note:** Human reviewer corrected the following fields: {', '.join(edited_fields)}
"""
    return example


def get_fewshot_examples(disease_state: str, count: int = 3) -> str:
    """
    Get formatted few-shot examples from recent corrections.

    Args:
        disease_state: The disease to get examples for
        count: Number of examples to include

    Returns:
        Formatted string with few-shot examples, or empty string if none available
    """
    corrections = load_corrections(disease_state, limit=count)

    if not corrections:
        return ""

    header = f"""
---

## Recent Human Corrections (Learn from these examples)

The following are recent questions where a human reviewer corrected the AI-generated tags.
Study these corrections carefully to understand the expected tagging patterns.

"""

    examples = []
    for i, correction in enumerate(corrections, 1):
        examples.append(f"### Correction Example {i}\n\n{format_correction_as_fewshot(correction)}")

    return header + "\n\n".join(examples) + "\n\n---\n"
