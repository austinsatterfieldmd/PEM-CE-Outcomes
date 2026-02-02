# Output Format

Respond with ONLY a JSON object containing all 66 fields. Use `null` for fields that are not applicable or cannot be determined with confidence.

```json
{
    "topic": "Treatment selection",
    "disease_stage": "Metastatic",
    "disease_type": "HER2+",
    "treatment_line": "2L+",
    "treatment_1": "trastuzumab deruxtecan",
    "treatment_2": null,
    "treatment_3": null,
    "treatment_4": null,
    "treatment_5": null,
    "biomarker_1": null,
    "biomarker_2": null,
    "biomarker_3": null,
    "biomarker_4": null,
    "biomarker_5": null,
    "trial_1": null,
    "trial_2": null,
    "trial_3": null,
    "trial_4": null,
    "trial_5": null,
    "drug_class_1": "HER2-directed ADC",
    "drug_class_2": null,
    "drug_class_3": null,
    "drug_target_1": "HER2",
    "drug_target_2": null,
    "drug_target_3": null,
    "prior_therapy_1": "Prior trastuzumab",
    "prior_therapy_2": null,
    "prior_therapy_3": null,
    "resistance_mechanism": null,
    "metastatic_site_1": "Brain metastases",
    "metastatic_site_2": null,
    "metastatic_site_3": null,
    "symptom_1": null,
    "symptom_2": null,
    "symptom_3": null,
    "special_population_1": null,
    "special_population_2": null,
    "performance_status": null,
    "toxicity_type_1": null,
    "toxicity_type_2": null,
    "toxicity_type_3": null,
    "toxicity_type_4": null,
    "toxicity_type_5": null,
    "toxicity_organ": null,
    "toxicity_grade": null,
    "efficacy_endpoint_1": null,
    "efficacy_endpoint_2": null,
    "efficacy_endpoint_3": null,
    "outcome_context": null,
    "clinical_benefit": null,
    "guideline_source_1": null,
    "guideline_source_2": null,
    "evidence_type": "Phase 3 RCT",
    "cme_outcome_level": "4 - Competence",
    "data_response_type": "Comparative",
    "stem_type": "Clinical vignette",
    "lead_in_type": "Best answer",
    "answer_format": "Single best",
    "answer_length_pattern": "Variable",
    "distractor_homogeneity": "Homogeneous",
    "flaw_absolute_terms": false,
    "flaw_grammatical_cue": false,
    "flaw_implausible_distractor": false,
    "flaw_clang_association": false,
    "flaw_convergence_vulnerability": false,
    "flaw_double_negative": false
}
```

## Key Rules for Output

1. **All 66 fields must be present** - Never omit a field; use `null` for inapplicable fields
2. **Exact canonical values** - Use values exactly as specified in field definitions
3. **No extra fields** - Only include the 66 defined fields
4. **Valid JSON** - Ensure proper JSON formatting (double quotes, no trailing commas)
5. **One topic only** - Topic is the only required field; never null
6. **Boolean flaw fields** - Use `true` or `false` (not strings, not null) for the 6 flaw_ fields
