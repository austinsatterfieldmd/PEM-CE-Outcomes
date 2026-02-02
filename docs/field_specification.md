# Stage 2 Tagging Field Specification

> **Version:** 2.0
> **Last Updated:** 2026-01-25
> **Field Count:** 70 LLM-tagged + 2 computed = 72 total

## Overview

This document defines all 70 tag fields for the Stage 2 tagging system, serving as the source of truth for:
- LLM prompt engineering (disease-specific prompts)
- Dashboard UI components (input types, valid values)
- API schema definitions (Pydantic models)
- Review workflow (field grouping, vote comparison)

---

## Input Component Types

| Type | Behavior | Use For | Dashboard Component |
|------|----------|---------|---------------------|
| **Dropdown** | Fixed list, no custom input allowed | Closed fields with exhaustive values | `<DropdownField>` |
| **Dropdown+Other** | Fixed list + "Other" option for free text | Semi-closed fields | `<DropdownOtherField>` |
| **Autocomplete** | Suggestions from canonical list, accepts custom | Guided fields with common patterns | `<AutocompleteField>` |
| **Autocomplete+Free** | Suggestions + easy free text entry | Open fields with high variability | `<AutocompleteField allowFreeText>` |
| **Boolean** | Checkbox or Yes/No toggle | True/false flaw indicators | `<BooleanField>` |
| **Computed** | Read-only, derived from raw data | Auto-calculated fields | `<ReadOnlyField>` |

---

## Field Groups Summary

| Group | Name | Field Count | Description |
|-------|------|-------------|-------------|
| A | Core Fields | 20 | Primary classification & content |
| B | Patient Characteristics | 5 | Patient demographics & eligibility (NEW) |
| C | Treatment Metadata | 10 | Drug classes, targets, prior therapy |
| D | Clinical Context | 7 | Disease location, symptoms, PS |
| E | Safety/Toxicity | 7 | Adverse events & management |
| F | Efficacy/Outcomes | 5 | Endpoints & clinical benefit |
| G | Evidence/Guidelines | 3 | Source of recommendations |
| H | Question Quality | 13 | CME item analysis (internal) |
| - | Computed | 2 | Derived from raw data |

---

## Group A: Core Fields (20 fields)

| # | Field | Type | Input | Required | Valid Values |
|---|-------|------|-------|----------|--------------|
| 1 | `topic` | string | **Dropdown** | Yes | Treatment selection, AE management, Biomarker testing, Clinical efficacy, Diagnosis, Prognosis, Study design, Multidisciplinary care, Disparities in care, Barriers to care |
| 2 | `disease_stage` | string | **Dropdown+Other** | No | See disease-specific table below |
| 3 | `disease_type_1` | string | **Autocomplete** | No | See disease-specific table below |
| 4 | `disease_type_2` | string | **Autocomplete** | No | Same as disease_type_1 (for rare overlaps) |
| 5 | `treatment_line` | string | **Dropdown+Other** | No | 1L, 2L, 2L+, 3L+, Adjuvant, Neoadjuvant, Perioperative, Maintenance, Consolidation, R/R, Newly diagnosed |
| 6 | `treatment_1` | string | **Autocomplete+Free** | No | Open - drug/regimen names |
| 7 | `treatment_2` | string | **Autocomplete+Free** | No | Open |
| 8 | `treatment_3` | string | **Autocomplete+Free** | No | Open |
| 9 | `treatment_4` | string | **Autocomplete+Free** | No | Open |
| 10 | `treatment_5` | string | **Autocomplete+Free** | No | Open |
| 11 | `biomarker_1` | string | **Autocomplete+Free** | No | Open - tested markers |
| 12 | `biomarker_2` | string | **Autocomplete+Free** | No | Open |
| 13 | `biomarker_3` | string | **Autocomplete+Free** | No | Open |
| 14 | `biomarker_4` | string | **Autocomplete+Free** | No | Open |
| 15 | `biomarker_5` | string | **Autocomplete+Free** | No | Open |
| 16 | `trial_1` | string | **Autocomplete+Free** | No | Open - trial names |
| 17 | `trial_2` | string | **Autocomplete+Free** | No | Open |
| 18 | `trial_3` | string | **Autocomplete+Free** | No | Open |
| 19 | `trial_4` | string | **Autocomplete+Free** | No | Open |
| 20 | `trial_5` | string | **Autocomplete+Free** | No | Open |

### disease_stage Values by Disease

| Disease | Valid Values | Notes |
|---------|--------------|-------|
| **Solid Tumors** | Early-stage, Locally advanced, Metastatic, Oligometastatic | Standard staging |
| **Multiple Myeloma** | R-ISS I, R-ISS II, R-ISS III, ISS I, ISS II, ISS III | Only when explicitly stated |
| **Lymphoma** | Ann Arbor I, Ann Arbor II, Ann Arbor III, Ann Arbor IV | Only when explicitly stated |
| **CLL** | Rai 0-IV, Binet A/B/C | Only when explicitly stated |
| **SCLC** | Limited-stage, Extensive-stage | Disease-specific staging |

### disease_type Values by Disease

| Disease | disease_type_1 Values | Notes |
|---------|----------------------|-------|
| **Multiple Myeloma** | High-risk, Standard-risk, Plasma cell leukemia, Smoldering MM, MGUS, Light chain MM, Non-secretory MM | Cytogenetic risk is primary |
| **Breast Cancer** | HER2+, HER2-low, HR+/HER2-, Triple-negative, Inflammatory, Lobular, Ductal | Receptor status hierarchy |
| **NSCLC** | Adenocarcinoma, Squamous, Large cell, Adenosquamous, Sarcomatoid | Histology only (molecular → biomarker) |
| **CRC** | Left-sided, Right-sided, Rectal, MSI-H, Mucinous | Includes rectal |
| **SCLC** | N/A | Use disease_stage instead |

---

## Group B: Patient Characteristics (5 fields) - NEW

| # | Field | Type | Input | Required | Valid Values |
|---|-------|------|-------|----------|--------------|
| 21 | `treatment_eligibility` | string | **Dropdown+Other** | No | See disease-specific table below |
| 22 | `age_group` | string | **Dropdown** | No | Pediatric, AYA, Young (<65), Transitional (65-75), Elderly (>75) |
| 23 | `organ_dysfunction` | string | **Autocomplete** | No | Renal, Cardiac, Hepatic, Pulmonary |
| 24 | `fitness_status` | string | **Dropdown** | No | Fit, Frail |
| 25 | `disease_specific_factor` | string | **Autocomplete+Free** | No | See disease-specific table below |

### treatment_eligibility Values by Disease

| Disease | Valid Values |
|---------|--------------|
| **Multiple Myeloma** | Transplant-eligible, Transplant-ineligible |
| **Solid Tumors** | Surgery candidate, Not surgical candidate |
| **General** | Fit for intensive therapy, Unfit for intensive therapy |

### disease_specific_factor Values by Disease

| Disease | Valid Values | Notes |
|---------|--------------|-------|
| **Breast Cancer** | Premenopausal, Postmenopausal | Menopausal status affects treatment |
| **CML** | Chronic phase, Accelerated phase, Blast phase | Disease phase |
| **Others** | Reserved for future use | |

---

## Group C: Treatment Metadata (10 fields)

| # | Field | Type | Input | Required | Valid Values |
|---|-------|------|-------|----------|--------------|
| 26 | `drug_class_1` | string | **Autocomplete** | No | See canonical list |
| 27 | `drug_class_2` | string | **Autocomplete** | No | See canonical list |
| 28 | `drug_class_3` | string | **Autocomplete** | No | See canonical list |
| 29 | `drug_target_1` | string | **Autocomplete** | No | See canonical list |
| 30 | `drug_target_2` | string | **Autocomplete** | No | See canonical list |
| 31 | `drug_target_3` | string | **Autocomplete** | No | See canonical list |
| 32 | `prior_therapy_1` | string | **Autocomplete+Free** | No | Open - prior treatments |
| 33 | `prior_therapy_2` | string | **Autocomplete+Free** | No | Open |
| 34 | `prior_therapy_3` | string | **Autocomplete+Free** | No | Open |
| 35 | `resistance_mechanism` | string | **Autocomplete+Free** | No | T790M, C797S, MET amplification, etc. |

### drug_class Canonical Values

- EGFR TKI, ALK TKI, ROS1 TKI, KRAS G12C inhibitor, MET inhibitor, RET inhibitor, NTRK inhibitor
- Anti-PD-1, Anti-PD-L1, Anti-CTLA-4, Anti-HER2, Anti-CD38, Anti-BCMA
- ADC (Antibody-drug conjugate), Bispecific antibody, CAR-T
- CDK4/6 inhibitor, PARP inhibitor, PI3K inhibitor, mTOR inhibitor, BCL-2 inhibitor, BTK inhibitor
- Proteasome inhibitor, IMiD (Immunomodulatory drug)
- Chemotherapy, Hormone therapy, Radiation therapy

### drug_target Canonical Values

- EGFR, ALK, ROS1, KRAS G12C, MET, RET, NTRK, BRAF V600E
- HER2, PD-1, PD-L1, CTLA-4, CDK4/6, PARP, PI3K, mTOR
- CD19, CD20, CD38, BCMA, GPRC5D, FcRH5, BCL-2, BTK

---

## Group D: Clinical Context (7 fields)

| # | Field | Type | Input | Required | Valid Values |
|---|-------|------|-------|----------|--------------|
| 36 | `metastatic_site_1` | string | **Autocomplete** | No | Brain, Liver, Bone, Lung, Adrenal, Peritoneal, Lymph node, Skin, CNS involvement, Extramedullary plasmacytoma |
| 37 | `metastatic_site_2` | string | **Autocomplete** | No | Same as above |
| 38 | `metastatic_site_3` | string | **Autocomplete** | No | Same as above |
| 39 | `symptom_1` | string | **Autocomplete** | No | Pain, Dyspnea, Fatigue, Nausea, Neuropathy, Bone pain, Hypercalcemia, Anemia, Renal insufficiency |
| 40 | `symptom_2` | string | **Autocomplete** | No | Same as above |
| 41 | `symptom_3` | string | **Autocomplete** | No | Same as above |
| 42 | `performance_status` | string | **Dropdown+Other** | No | ECOG 0, ECOG 1, ECOG 2, ECOG 3, ECOG 4, KPS 100, KPS 90, KPS 80, KPS 70, KPS ≤60 |

---

## Group E: Safety/Toxicity (7 fields)

| # | Field | Type | Input | Required | Valid Values |
|---|-------|------|-------|----------|--------------|
| 43 | `toxicity_type_1` | string | **Autocomplete** | No | See canonical list |
| 44 | `toxicity_type_2` | string | **Autocomplete** | No | See canonical list |
| 45 | `toxicity_type_3` | string | **Autocomplete** | No | See canonical list |
| 46 | `toxicity_type_4` | string | **Autocomplete** | No | See canonical list |
| 47 | `toxicity_type_5` | string | **Autocomplete** | No | See canonical list |
| 48 | `toxicity_organ` | string | **Autocomplete** | No | Hematologic, GI, Dermatologic, Pulmonary, Hepatic, Renal, Cardiac, Neurologic, Endocrine, Musculoskeletal |
| 49 | `toxicity_grade` | string | **Dropdown** | No | Grade 1, Grade 2, Grade 3, Grade 4, Grade 5, Any grade, Grade ≥3 |

### toxicity_type Canonical Values

- Neutropenia, Febrile neutropenia, Thrombocytopenia, Anemia
- Diarrhea, Nausea, Vomiting, Mucositis
- Fatigue, Rash, Pruritus
- Pneumonitis, Colitis, Hepatitis, Nephrotoxicity, Cardiotoxicity
- Peripheral neuropathy, Infusion reaction
- CRS (Cytokine release syndrome), ICANS (Immune effector cell-associated neurotoxicity syndrome)
- Infections, Hypersensitivity

---

## Group F: Efficacy/Outcomes (5 fields)

| # | Field | Type | Input | Required | Valid Values |
|---|-------|------|-------|----------|--------------|
| 50 | `efficacy_endpoint_1` | string | **Autocomplete** | No | See canonical list |
| 51 | `efficacy_endpoint_2` | string | **Autocomplete** | No | See canonical list |
| 52 | `efficacy_endpoint_3` | string | **Autocomplete** | No | See canonical list |
| 53 | `outcome_context` | string | **Dropdown+Other** | No | Primary endpoint, Secondary endpoint, Exploratory endpoint, Subgroup analysis, Post-hoc analysis, Real-world data |
| 54 | `clinical_benefit` | string | **Dropdown+Other** | No | Statistically significant, Clinically meaningful, Superior, Non-inferior, Equivalent, No benefit, Detrimental |

### efficacy_endpoint Canonical Values

- OS (Overall survival), PFS (Progression-free survival), DFS (Disease-free survival)
- EFS (Event-free survival), RFS (Recurrence-free survival)
- ORR (Overall response rate), CR (Complete response), sCR (Stringent complete response)
- VGPR (Very good partial response), PR (Partial response)
- MRD negativity (Minimal residual disease negativity)
- DOR (Duration of response), DCR (Disease control rate), CBR (Clinical benefit rate)
- TTR (Time to response), TTP (Time to progression)
- pCR (Pathologic complete response)

---

## Group G: Evidence/Guidelines (3 fields)

| # | Field | Type | Input | Required | Valid Values |
|---|-------|------|-------|----------|--------------|
| 55 | `guideline_source_1` | string | **Dropdown+Other** | No | NCCN, ASCO, ESMO, IMWG, ASTCT, ASH, MASCC, FDA label, EMA label |
| 56 | `guideline_source_2` | string | **Dropdown+Other** | No | Same as above |
| 57 | `evidence_type` | string | **Dropdown** | No | Phase 3 RCT, Phase 2, Phase 1, Real-world evidence, Meta-analysis, Systematic review, Case series, Expert opinion, Guideline recommendation |

---

## Group H: Question Quality (13 fields)

> **Note:** These fields are for internal CME item analysis. Not shown to end users in standard views.

| # | Field | Type | Input | Required | Valid Values |
|---|-------|------|-------|----------|--------------|
| 58 | `cme_outcome_level` | string | **Dropdown** | No | 3 - Knowledge, 4 - Competence |
| 59 | `data_response_type` | string | **Dropdown** | No | Numeric, Qualitative, Comparative, Boolean |
| 60 | `stem_type` | string | **Dropdown** | No | Clinical vignette, Direct question, Incomplete statement, Case series |
| 61 | `lead_in_type` | string | **Dropdown** | No | Standard, Negative (EXCEPT/NOT), Best answer, Most likely, Most appropriate |
| 62 | `answer_format` | string | **Dropdown** | No | Single best, Compound (A+B), All of above, None of above, True/False |
| 63 | `answer_length_pattern` | string | **Dropdown** | No | Uniform, Variable, Correct longest, Correct shortest |
| 64 | `distractor_homogeneity` | string | **Dropdown** | No | Homogeneous, Heterogeneous |
| 65 | `flaw_absolute_terms` | boolean | **Boolean** | No | true/false |
| 66 | `flaw_grammatical_cue` | boolean | **Boolean** | No | true/false |
| 67 | `flaw_implausible_distractor` | boolean | **Boolean** | No | true/false |
| 68 | `flaw_clang_association` | boolean | **Boolean** | No | true/false |
| 69 | `flaw_convergence_vulnerability` | boolean | **Boolean** | No | true/false |
| 70 | `flaw_double_negative` | boolean | **Boolean** | No | true/false |

---

## Computed Fields (2 fields)

| # | Field | Type | Source | Valid Values |
|---|-------|------|--------|--------------|
| 71 | `answer_option_count` | integer | Count of answer options (A-E) | 2, 3, 4, 5 |
| 72 | `correct_answer_position` | string | Position of correct answer | A, B, C, D, E |

---

## API Schema (Pydantic Models)

```python
from pydantic import BaseModel
from typing import Optional, Literal, List

# Group B: Patient Characteristics (NEW)
class PatientCharacteristics(BaseModel):
    treatment_eligibility: Optional[str] = None
    age_group: Optional[Literal["Pediatric", "AYA", "Young", "Transitional", "Elderly"]] = None
    organ_dysfunction: Optional[str] = None
    fitness_status: Optional[Literal["Fit", "Frail"]] = None
    disease_specific_factor: Optional[str] = None

# Group A: Core Tags
class CoreTags(BaseModel):
    topic: Literal[
        "Treatment selection", "AE management", "Biomarker testing",
        "Clinical efficacy", "Diagnosis", "Prognosis", "Study design",
        "Multidisciplinary care", "Disparities in care", "Barriers to care"
    ]
    disease_stage: Optional[str] = None
    disease_type_1: Optional[str] = None
    disease_type_2: Optional[str] = None
    treatment_line: Optional[str] = None
    treatment_1: Optional[str] = None
    treatment_2: Optional[str] = None
    treatment_3: Optional[str] = None
    treatment_4: Optional[str] = None
    treatment_5: Optional[str] = None
    biomarker_1: Optional[str] = None
    biomarker_2: Optional[str] = None
    biomarker_3: Optional[str] = None
    biomarker_4: Optional[str] = None
    biomarker_5: Optional[str] = None
    trial_1: Optional[str] = None
    trial_2: Optional[str] = None
    trial_3: Optional[str] = None
    trial_4: Optional[str] = None
    trial_5: Optional[str] = None

# Group C: Treatment Metadata
class TreatmentMetadata(BaseModel):
    drug_class_1: Optional[str] = None
    drug_class_2: Optional[str] = None
    drug_class_3: Optional[str] = None
    drug_target_1: Optional[str] = None
    drug_target_2: Optional[str] = None
    drug_target_3: Optional[str] = None
    prior_therapy_1: Optional[str] = None
    prior_therapy_2: Optional[str] = None
    prior_therapy_3: Optional[str] = None
    resistance_mechanism: Optional[str] = None

# Group D: Clinical Context
class ClinicalContext(BaseModel):
    metastatic_site_1: Optional[str] = None
    metastatic_site_2: Optional[str] = None
    metastatic_site_3: Optional[str] = None
    symptom_1: Optional[str] = None
    symptom_2: Optional[str] = None
    symptom_3: Optional[str] = None
    performance_status: Optional[str] = None

# Group E: Safety/Toxicity
class SafetyToxicity(BaseModel):
    toxicity_type_1: Optional[str] = None
    toxicity_type_2: Optional[str] = None
    toxicity_type_3: Optional[str] = None
    toxicity_type_4: Optional[str] = None
    toxicity_type_5: Optional[str] = None
    toxicity_organ: Optional[str] = None
    toxicity_grade: Optional[str] = None

# Group F: Efficacy/Outcomes
class EfficacyOutcomes(BaseModel):
    efficacy_endpoint_1: Optional[str] = None
    efficacy_endpoint_2: Optional[str] = None
    efficacy_endpoint_3: Optional[str] = None
    outcome_context: Optional[str] = None
    clinical_benefit: Optional[str] = None

# Group G: Evidence/Guidelines
class EvidenceGuidelines(BaseModel):
    guideline_source_1: Optional[str] = None
    guideline_source_2: Optional[str] = None
    evidence_type: Optional[str] = None

# Group H: Question Quality
class QuestionQuality(BaseModel):
    cme_outcome_level: Optional[Literal["3 - Knowledge", "4 - Competence"]] = None
    data_response_type: Optional[str] = None
    stem_type: Optional[str] = None
    lead_in_type: Optional[str] = None
    answer_format: Optional[str] = None
    answer_length_pattern: Optional[str] = None
    distractor_homogeneity: Optional[str] = None
    flaw_absolute_terms: bool = False
    flaw_grammatical_cue: bool = False
    flaw_implausible_distractor: bool = False
    flaw_clang_association: bool = False
    flaw_convergence_vulnerability: bool = False
    flaw_double_negative: bool = False

# Computed Fields
class ComputedFields(BaseModel):
    answer_option_count: int
    correct_answer_position: Literal["A", "B", "C", "D", "E"]

# Vote Details for Review UI
class FieldVote(BaseModel):
    final_value: Optional[str] = None
    gpt_value: Optional[str] = None
    claude_value: Optional[str] = None
    gemini_value: Optional[str] = None
    agreement: Literal["unanimous", "majority", "conflict"]
    dissenting_model: Optional[str] = None
    web_search_used: bool = False

# Full Tag Response (Grouped)
class FullTagResponse(BaseModel):
    core: CoreTags
    patient_characteristics: PatientCharacteristics
    treatment_metadata: TreatmentMetadata
    clinical_context: ClinicalContext
    safety_toxicity: SafetyToxicity
    efficacy_outcomes: EfficacyOutcomes
    evidence_guidelines: EvidenceGuidelines
    question_quality: QuestionQuality
    computed: ComputedFields
    field_votes: Optional[dict[str, FieldVote]] = None
```

---

## Dashboard Review Panel Layout

```
┌─────────────────────────────────────────────────────────────────┐
│ Review Question #1234                    [Save] [Skip] [Reject] │
├─────────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ A 72-year-old man with R-ISS III multiple myeloma and...    │ │
│ │ A) VRd   B) DRd   C) KRd   D) Dara-VMP                      │ │
│ │ Correct: B                                                   │ │
│ └─────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│ ▼ Core Fields (20)                          [2 disagreements]   │
│   ┌──────────────────┬───────────────────────────────────────┐  │
│   │ topic            │ [Treatment selection           ▾]     │  │
│   │ disease_stage    │ [R-ISS III                      ] ⚠   │  │
│   │                  │   GPT: null | Claude: R-ISS III       │  │
│   │ disease_type_1   │ [High-risk                      ]     │  │
│   │ disease_type_2   │ [                               ]     │  │
│   │ treatment_line   │ [Newly diagnosed                ▾]    │  │
│   │ treatment_1      │ [daratumumab                    ]     │  │
│   │ ...              │                                       │  │
│   └──────────────────┴───────────────────────────────────────┘  │
│                                                                 │
│ ▼ Patient Characteristics (5)               [0 disagreements]   │
│   ┌──────────────────┬───────────────────────────────────────┐  │
│   │ treatment_elig.  │ [Transplant-ineligible         ▾]     │  │
│   │ age_group        │ [Elderly (65-74)               ▾]     │  │
│   │ organ_dysfunc.   │ [Renal                          ]     │  │
│   │ fitness_status   │ [                              ▾]     │  │
│   │ disease_specific │ [                               ]     │  │
│   └──────────────────┴───────────────────────────────────────┘  │
│                                                                 │
│ ▶ Treatment Metadata (10)                   [collapsed]         │
│ ▶ Clinical Context (7)                      [collapsed]         │
│ ▶ Safety/Toxicity (7)                       [collapsed]         │
│ ▶ Efficacy/Outcomes (5)                     [collapsed]         │
│ ▶ Evidence/Guidelines (3)                   [collapsed]         │
│ ▶ Question Quality (13)                     [collapsed]         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Migration Notes

### From 66 to 70 Fields

| Change | Migration Action |
|--------|------------------|
| Remove `special_population_1` | Map to treatment_eligibility, age_group, organ_dysfunction, or fitness_status |
| Remove `special_population_2` | Same as above |
| Add `treatment_eligibility` | Populate from disease_type or special_population where appropriate |
| Add `age_group` | Extract from vignettes where age is mentioned |
| Add `organ_dysfunction` | Extract from special_population or clinical context |
| Add `fitness_status` | Extract from special_population |
| Add `disease_specific_factor` | For menopausal status, disease phase, etc. |
| Split `disease_type` | Move existing value to disease_type_1, set disease_type_2 = null |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0 | 2026-01-25 | 70-field schema with patient characteristics group |
| 1.0 | 2026-01-15 | Original 66-field schema |
