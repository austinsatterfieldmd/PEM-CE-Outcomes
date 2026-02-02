# NSCLC Disease Module

This module contains NSCLC-specific tagging rules. Use in combination with base components (field_definitions.md, universal_rules.md, output_format.md).

---

## NSCLC-Specific Rules

### disease_type (Critical Difference from Other Diseases)

**NSCLC uses `null` for most cases.** Molecular alterations go in `biomarker`, NOT `disease_type`.

| disease_type Value | When to Use |
|-------------------|-------------|
| `null` | **DEFAULT** - Use for most NSCLC questions |
| `"Squamous"` | Only when squamous histology is explicitly stated AND relevant to treatment |
| `"Leptomeningeal"` | Only for leptomeningeal disease questions |

**Why this matters:**
- EGFR-mutated NSCLC → disease_type: `null`, biomarker_1: `"EGFR mutation"`
- ALK-positive NSCLC → disease_type: `null`, biomarker_1: `"ALK"`
- KRAS G12C NSCLC → disease_type: `null`, biomarker_1: `"KRAS G12C"`

This differs from breast cancer where HER2+ IS the disease_type.

---

### disease_stage

| Stage | disease_stage Value | Notes |
|-------|-------------------|-------|
| Stage I-II | `"Early-stage resectable"` | Surgical candidates |
| Stage III resectable | `"Early-stage resectable"` | Surgical candidates with nodal disease |
| Stage III unresectable | `"Early-stage unresectable"` | Locally advanced, concurrent CRT eligible |
| Stage IV / Metastatic | `"Metastatic"` | Distant metastases |

---

### treatment_line

**Early-Stage (Resectable):**
- `"Neoadjuvant"` - Before surgery (e.g., CheckMate-816)
- `"Adjuvant"` - After surgery (e.g., ADAURA, IMpower010)
- `"Perioperative"` - Before AND after surgery (e.g., KEYNOTE-671, CheckMate-77T)

**Unresectable Stage III:**
- `"Consolidation"` - After concurrent CRT (e.g., PACIFIC durvalumab)

**Metastatic:**
- `"1L"` - First-line metastatic
- `"2L+"` - Second-line or later
- `"Maintenance"` - Continuation after induction

---

### Biomarker Tagging Rules

**Actionable Genomic Alterations (AGAs):**
Tag the specific molecular alteration in `biomarker_1`:
- `"EGFR mutation"` (includes exon 19 del, L858R, exon 20 ins)
- `"ALK"` (ALK rearrangement/fusion)
- `"ROS1"` (ROS1 rearrangement)
- `"KRAS G12C"` (specific mutation)
- `"BRAF V600E"` (specific mutation)
- `"MET exon 14 skipping"`
- `"RET"` (RET fusion)
- `"NTRK"` (NTRK fusion)
- `"HER2"` (HER2 mutation, NOT amplification)

**"No AGA" Convention:**
When a question discusses immunotherapy eligibility for patients WITHOUT actionable alterations:
- biomarker_1: `"No AGA"` (No Actionable Genomic Alteration)
- This indicates the patient is immunotherapy-eligible

**PD-L1 Expression:**
Tag PD-L1 status when relevant to treatment selection:
- `"PD-L1 >=50%"` (high expression, pembrolizumab monotherapy eligible)
- `"PD-L1 1-49%"` (intermediate expression)
- `"PD-L1 <1%"` or `"PD-L1 negative"` (low/negative)

---

### Fundable NSCLC Treatments

**Tag ONLY these drugs. Do NOT tag chemotherapy (carboplatin, pemetrexed, etc.).**

| Category | Drugs |
|----------|-------|
| **EGFR TKIs** | osimertinib, erlotinib, gefitinib, afatinib, dacomitinib, amivantamab, lazertinib, mobocertinib |
| **ALK Inhibitors** | alectinib, brigatinib, lorlatinib, crizotinib, ceritinib, ensartinib |
| **ROS1 Inhibitors** | crizotinib, entrectinib, lorlatinib, repotrectinib, taletrectinib |
| **KRAS G12C Inhibitors** | sotorasib, adagrasib |
| **BRAF/MEK** | dabrafenib, trametinib |
| **MET Inhibitors** | capmatinib, tepotinib |
| **RET Inhibitors** | selpercatinib, pralsetinib |
| **NTRK Inhibitors** | larotrectinib, entrectinib |
| **Anti-PD-1** | pembrolizumab, nivolumab, cemiplimab |
| **Anti-PD-L1** | atezolizumab, durvalumab |
| **Anti-CTLA-4** | ipilimumab, tremelimumab |
| **HER2-Directed** | trastuzumab deruxtecan |
| **Anti-VEGF** | bevacizumab, ramucirumab |
| **ADCs** | trastuzumab deruxtecan, datopotamab deruxtecan |

---

### Trial Inference Table

**EGFR-Mutated:**
| Context | Trial(s) |
|---------|----------|
| 1L osimertinib | FLAURA, FLAURA2 |
| Adjuvant osimertinib | ADAURA |
| Amivantamab + lazertinib | MARIPOSA |
| Exon 20 insertion | PAPILLON, CHRYSALIS |
| T790M resistance | AURA3 |

**ALK-Positive:**
| Context | Trial(s) |
|---------|----------|
| 1L alectinib | ALEX |
| 1L brigatinib | ALTA-1L |
| 1L lorlatinib | CROWN |
| 2L+ lorlatinib | ALTA, ASCEND series |

**ROS1-Positive:**
| Context | Trial(s) |
|---------|----------|
| Repotrectinib | TRIDENT-1 |
| Entrectinib | STARTRK-2 |

**KRAS G12C:**
| Context | Trial(s) |
|---------|----------|
| Sotorasib monotherapy | CodeBreaK 100 |
| Sotorasib + chemo | CodeBreaK 200 |
| Adagrasib | KRYSTAL-1, KRYSTAL-7 |

**Immunotherapy (No AGA):**
| Context | Trial(s) |
|---------|----------|
| 1L pembrolizumab + chemo | KEYNOTE-189 (non-squamous), KEYNOTE-407 (squamous) |
| 1L pembrolizumab mono (PD-L1 >=50%) | KEYNOTE-024, KEYNOTE-042 |
| 1L nivolumab + ipilimumab + chemo | CheckMate-9LA |
| 1L nivolumab + ipilimumab | CheckMate-227 |
| 1L atezolizumab + bev + chemo | IMpower150 |
| Consolidation durvalumab (Stage III) | PACIFIC |
| Neoadjuvant nivolumab + chemo | CheckMate-816 |
| Perioperative pembrolizumab | KEYNOTE-671 |
| Adjuvant atezolizumab | IMpower010 |
| Perioperative nivolumab | CheckMate-77T |

**Other Targets:**
| Context | Trial(s) |
|---------|----------|
| MET exon 14 - capmatinib | GEOMETRY mono-1 |
| MET exon 14 - tepotinib | VISION |
| RET - selpercatinib | LIBRETTO-001, LIBRETTO-431 |
| BRAF V600E | BRF113928 |
| HER2 mutation - T-DXd | DESTINY-Lung01, DESTINY-Lung02 |

---

## NSCLC Examples (56 Fields)

### Example 1: EGFR-Mutated 1L Treatment Selection

**Question:** A 62-year-old woman with newly diagnosed metastatic NSCLC and an EGFR exon 19 deletion is evaluated. What is the preferred first-line systemic therapy?

**Correct Answer:** Osimertinib

```json
{
    "topic": "Treatment selection",
    "disease_stage": "Metastatic",
    "disease_type": null,
    "treatment_line": "1L",
    "treatment_1": "osimertinib",
    "treatment_2": null,
    "treatment_3": null,
    "treatment_4": null,
    "treatment_5": null,
    "biomarker_1": "EGFR mutation",
    "biomarker_2": null,
    "biomarker_3": null,
    "biomarker_4": null,
    "biomarker_5": null,
    "trial_1": null,
    "trial_2": null,
    "trial_3": null,
    "trial_4": null,
    "trial_5": null,
    "drug_class_1": "EGFR TKI",
    "drug_class_2": null,
    "drug_class_3": null,
    "drug_target_1": "EGFR",
    "drug_target_2": null,
    "drug_target_3": null,
    "prior_therapy_1": null,
    "prior_therapy_2": null,
    "prior_therapy_3": null,
    "resistance_mechanism": null,
    "metastatic_site_1": null,
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
    "evidence_type": null,
    "trial_phase": null,
    "cme_outcome_level": "4 - Competence",
    "data_response_type": "Comparative",
    "endpoint_type_1": null,
    "endpoint_type_2": null
}
```

**Rationale:**
- disease_type: `null` because EGFR mutation goes in biomarker, not disease_type
- biomarker_1: `"EGFR mutation"` - the actionable alteration
- trial_1: `null` - topic is "Treatment selection", trial not explicitly named in stem (inference not allowed)
- drug_class_1/drug_target_1: Captures the therapeutic class

---

### Example 2: ALK-Positive Clinical Efficacy

**Question:** In the CROWN trial, what was the progression-free survival benefit of lorlatinib compared to crizotinib in treatment-naive ALK-positive NSCLC?

**Correct Answer:** 3-year PFS rate was 64% vs 19%

```json
{
    "topic": "Clinical efficacy",
    "disease_stage": "Metastatic",
    "disease_type": null,
    "treatment_line": "1L",
    "treatment_1": "lorlatinib",
    "treatment_2": "crizotinib",
    "treatment_3": null,
    "treatment_4": null,
    "treatment_5": null,
    "biomarker_1": "ALK",
    "biomarker_2": null,
    "biomarker_3": null,
    "biomarker_4": null,
    "biomarker_5": null,
    "trial_1": "CROWN",
    "trial_2": null,
    "trial_3": null,
    "trial_4": null,
    "trial_5": null,
    "drug_class_1": "ALK inhibitor",
    "drug_class_2": "ALK inhibitor",
    "drug_class_3": null,
    "drug_target_1": "ALK",
    "drug_target_2": "ALK",
    "drug_target_3": null,
    "prior_therapy_1": null,
    "prior_therapy_2": null,
    "prior_therapy_3": null,
    "resistance_mechanism": null,
    "metastatic_site_1": null,
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
    "efficacy_endpoint_1": "Progression-free survival (PFS)",
    "efficacy_endpoint_2": null,
    "efficacy_endpoint_3": null,
    "outcome_context": "Primary endpoint met",
    "clinical_benefit": "Superior",
    "guideline_source_1": null,
    "guideline_source_2": null,
    "evidence_type": "Phase 3 RCT",
    "trial_phase": "Phase 3",
    "cme_outcome_level": "3 - Knowledge",
    "data_response_type": "Numeric",
    "endpoint_type_1": "Primary",
    "endpoint_type_2": null
}
```

**Rationale:**
- topic: `"Clinical efficacy"` - asks about trial results, not treatment choice
- Both lorlatinib and crizotinib tagged (comparator arms)
- efficacy_endpoint_1: `"Progression-free survival (PFS)"` - the outcome being asked
- cme_outcome_level: `"3 - Knowledge"` - tests recall of trial data, not clinical application

---

### Example 3: Neoadjuvant Immunotherapy (Stage III Resectable)

**Question:** A 58-year-old man with resectable stage IIIA NSCLC is being evaluated for neoadjuvant therapy. Based on CheckMate-816, what improvement in pathologic complete response was seen with neoadjuvant nivolumab plus chemotherapy compared to chemotherapy alone?

**Correct Answer:** pCR rate 24% vs 2.2%

```json
{
    "topic": "Clinical efficacy",
    "disease_stage": "Early-stage resectable",
    "disease_type": null,
    "treatment_line": "Neoadjuvant",
    "treatment_1": "nivolumab",
    "treatment_2": null,
    "treatment_3": null,
    "treatment_4": null,
    "treatment_5": null,
    "biomarker_1": "No AGA",
    "biomarker_2": null,
    "biomarker_3": null,
    "biomarker_4": null,
    "biomarker_5": null,
    "trial_1": "CheckMate-816",
    "trial_2": null,
    "trial_3": null,
    "trial_4": null,
    "trial_5": null,
    "drug_class_1": "Anti-PD-1",
    "drug_class_2": null,
    "drug_class_3": null,
    "drug_target_1": "PD-1",
    "drug_target_2": null,
    "drug_target_3": null,
    "prior_therapy_1": null,
    "prior_therapy_2": null,
    "prior_therapy_3": null,
    "resistance_mechanism": null,
    "metastatic_site_1": null,
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
    "efficacy_endpoint_1": "Pathologic complete response (pCR)",
    "efficacy_endpoint_2": null,
    "efficacy_endpoint_3": null,
    "outcome_context": "Primary endpoint met",
    "clinical_benefit": "Superior",
    "guideline_source_1": null,
    "guideline_source_2": null,
    "evidence_type": "Phase 3 RCT",
    "trial_phase": "Phase 3",
    "cme_outcome_level": "3 - Knowledge",
    "data_response_type": "Numeric",
    "endpoint_type_1": "Primary",
    "endpoint_type_2": null
}
```

**Rationale:**
- disease_stage: `"Early-stage resectable"` - Stage IIIA, surgical candidate
- treatment_line: `"Neoadjuvant"` - before surgery (curative intent)
- biomarker_1: `"No AGA"` - immunotherapy context implies no actionable alteration
- efficacy_endpoint_1: `"Pathologic complete response (pCR)"` - key surgical endpoint

---

### Example 4: Consolidation Durvalumab (Unresectable Stage III)

**Question:** Based on the PACIFIC trial, which patients with unresectable stage III NSCLC derive the most benefit from consolidation durvalumab after chemoradiation?

**Correct Answer:** Those with PD-L1 >=1%

```json
{
    "topic": "Treatment indication",
    "disease_stage": "Early-stage unresectable",
    "disease_type": null,
    "treatment_line": "Consolidation",
    "treatment_1": "durvalumab",
    "treatment_2": null,
    "treatment_3": null,
    "treatment_4": null,
    "treatment_5": null,
    "biomarker_1": "PD-L1 >=1%",
    "biomarker_2": null,
    "biomarker_3": null,
    "biomarker_4": null,
    "biomarker_5": null,
    "trial_1": "PACIFIC",
    "trial_2": null,
    "trial_3": null,
    "trial_4": null,
    "trial_5": null,
    "drug_class_1": "Anti-PD-L1",
    "drug_class_2": null,
    "drug_class_3": null,
    "drug_target_1": "PD-L1",
    "drug_target_2": null,
    "drug_target_3": null,
    "prior_therapy_1": "Prior chemoradiation",
    "prior_therapy_2": null,
    "prior_therapy_3": null,
    "resistance_mechanism": null,
    "metastatic_site_1": null,
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
    "outcome_context": "Subgroup analysis",
    "clinical_benefit": null,
    "guideline_source_1": null,
    "guideline_source_2": null,
    "evidence_type": "Phase 3 RCT",
    "trial_phase": "Phase 3",
    "cme_outcome_level": "3 - Knowledge",
    "data_response_type": "Qualitative",
    "endpoint_type_1": "Subgroup",
    "endpoint_type_2": null
}
```

**Rationale:**
- disease_stage: `"Early-stage unresectable"` - Stage III, locally advanced, not metastatic
- treatment_line: `"Consolidation"` - unique to unresectable Stage III NSCLC
- prior_therapy_1: `"Prior chemoradiation"` - the context for consolidation
- outcome_context: `"Subgroup analysis"` - question about which patients benefit most

---

### Example 5: KRAS G12C 2L Treatment with Brain Metastases

**Question:** A 67-year-old man with KRAS G12C-mutated metastatic NSCLC has progressed on pembrolizumab plus chemotherapy and has new brain metastases. Which targeted therapy has demonstrated intracranial activity in this setting?

**Correct Answer:** Adagrasib

```json
{
    "topic": "Treatment selection",
    "disease_stage": "Metastatic",
    "disease_type": null,
    "treatment_line": "2L+",
    "treatment_1": "adagrasib",
    "treatment_2": "sotorasib",
    "treatment_3": null,
    "treatment_4": null,
    "treatment_5": null,
    "biomarker_1": "KRAS G12C",
    "biomarker_2": null,
    "biomarker_3": null,
    "biomarker_4": null,
    "biomarker_5": null,
    "trial_1": null,
    "trial_2": null,
    "trial_3": null,
    "trial_4": null,
    "trial_5": null,
    "drug_class_1": "KRAS G12C inhibitor",
    "drug_class_2": "KRAS G12C inhibitor",
    "drug_class_3": null,
    "drug_target_1": "KRAS G12C",
    "drug_target_2": "KRAS G12C",
    "drug_target_3": null,
    "prior_therapy_1": "Prior immunotherapy",
    "prior_therapy_2": "Prior platinum",
    "prior_therapy_3": null,
    "resistance_mechanism": null,
    "metastatic_site_1": "Brain metastases",
    "metastatic_site_2": null,
    "metastatic_site_3": null,
    "symptom_1": null,
    "symptom_2": null,
    "symptom_3": null,
    "special_population_1": "CNS involvement",
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
    "evidence_type": null,
    "trial_phase": null,
    "cme_outcome_level": "4 - Competence",
    "data_response_type": "Comparative",
    "endpoint_type_1": null,
    "endpoint_type_2": null
}
```

**Rationale:**
- treatment_1/treatment_2: Both KRAS G12C inhibitors are relevant class options
- prior_therapy_1/2: Prior pembrolizumab + chemo captured
- metastatic_site_1: `"Brain metastases"` - explicitly mentioned, clinically relevant
- special_population_1: `"CNS involvement"` - affects treatment selection
- trial_1: `null` - topic is "Treatment selection", trial not explicitly named in stem (inference not allowed)

---

### Example 6: Immunotherapy Safety Profile

**Question:** What is the incidence of grade 3 or higher immune-related pneumonitis with pembrolizumab monotherapy in patients with advanced NSCLC?

**Correct Answer:** Approximately 3-5%

```json
{
    "topic": "Safety profile",
    "disease_stage": "Metastatic",
    "disease_type": null,
    "treatment_line": null,
    "treatment_1": "pembrolizumab",
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
    "drug_class_1": "Anti-PD-1",
    "drug_class_2": null,
    "drug_class_3": null,
    "drug_target_1": "PD-1",
    "drug_target_2": null,
    "drug_target_3": null,
    "prior_therapy_1": null,
    "prior_therapy_2": null,
    "prior_therapy_3": null,
    "resistance_mechanism": null,
    "metastatic_site_1": null,
    "metastatic_site_2": null,
    "metastatic_site_3": null,
    "symptom_1": null,
    "symptom_2": null,
    "symptom_3": null,
    "special_population_1": null,
    "special_population_2": null,
    "performance_status": null,
    "toxicity_type_1": "Immune-related pneumonitis",
    "toxicity_type_2": null,
    "toxicity_type_3": null,
    "toxicity_type_4": null,
    "toxicity_type_5": null,
    "toxicity_organ": "Pulmonary",
    "toxicity_grade": "Grade >=3",
    "efficacy_endpoint_1": null,
    "efficacy_endpoint_2": null,
    "efficacy_endpoint_3": null,
    "outcome_context": null,
    "clinical_benefit": null,
    "guideline_source_1": null,
    "guideline_source_2": null,
    "evidence_type": null,
    "trial_phase": null,
    "cme_outcome_level": "3 - Knowledge",
    "data_response_type": "Numeric",
    "endpoint_type_1": null,
    "endpoint_type_2": null
}
```

**Rationale:**
- topic: `"Safety profile"` - asking about adverse event rates
- toxicity_type_1: `"Immune-related pneumonitis"` - specific AE mentioned
- toxicity_organ: `"Pulmonary"` - organ system affected
- toxicity_grade: `"Grade >=3"` - severity level specified
- treatment_line: `null` - not specified in question (general safety data)

---

## NSCLC Edge Cases

### Edge Case 1: Squamous vs Non-Squamous
- Tag `disease_type: "Squamous"` ONLY when squamous histology affects treatment (e.g., bevacizumab contraindicated)
- For most questions, leave `disease_type: null` even if "squamous" is mentioned

### Edge Case 2: Resistance Mutations
- T790M after EGFR TKI → biomarker_1: `"T790M"`, prior_therapy_1: `"Prior EGFR TKI"`, resistance_mechanism: `"T790M mutation"`
- C797S after osimertinib → biomarker_1: `"C797S"`, prior_therapy_1: `"Prior osimertinib"`, resistance_mechanism: `"C797S mutation"`

### Edge Case 3: MET Amplification as Resistance
- MET amplification arising during EGFR TKI → resistance_mechanism: `"MET amplification"`, NOT biomarker_1

### Edge Case 4: Combination Immunotherapy
- Nivolumab + ipilimumab → treatment_1: `"nivolumab"`, treatment_2: `"ipilimumab"`, drug_class_1: `"Anti-PD-1"`, drug_class_2: `"Anti-CTLA-4"`
