# CRC (Colorectal Cancer) Disease Module

This module contains CRC-specific tagging rules. Use in combination with base components (field_definitions.md, universal_rules.md, output_format.md).

---

## CRC-Specific Rules

### CRITICAL: Chemotherapy IS Tagged in CRC

**Unlike other diseases, CRC questions SHOULD tag chemotherapy regimens.**

Why: In CRC, the chemotherapy backbone (FOLFOX vs FOLFIRI vs FOLFOXIRI) directly impacts targeted therapy selection and is clinically meaningful.

| Regimen | Tag As |
|---------|--------|
| FOLFOX | `"FOLFOX"` |
| FOLFIRI | `"FOLFIRI"` |
| FOLFOXIRI | `"FOLFOXIRI"` |
| CAPOX/XELOX | `"CAPOX"` |
| Capecitabine | `"capecitabine"` |

**Combination tagging:**
- FOLFOX + bevacizumab → treatment_1: `"FOLFOX"`, treatment_2: `"bevacizumab"`
- FOLFIRI + cetuximab → treatment_1: `"FOLFIRI"`, treatment_2: `"cetuximab"`

---

### disease_type

| disease_type Value | When to Use |
|-------------------|-------------|
| `null` | **DEFAULT** - Most CRC questions |
| `"Rectal"` | Only when rectal-specific treatment applies (TNT, organ preservation, sphincter-sparing) |
| `"MSI-H/dMMR"` | When MSI-H/dMMR status is the defining characteristic for treatment |

**Note:** Biomarkers like BRAF V600E, RAS status, HER2 go in `biomarker` fields, NOT disease_type.

---

### disease_stage

| Stage | disease_stage Value | Notes |
|-------|-------------------|-------|
| Stage I-III | `"Early-stage"` | Resectable, adjuvant setting |
| Stage II-III rectal | `"Early-stage"` | TNT/neoadjuvant setting |
| Stage IV resectable | `"Metastatic"` | Oligometastatic, conversion therapy |
| Stage IV unresectable | `"Metastatic"` | Palliative systemic therapy |

---

### treatment_line

**Early-Stage:**
- `"Adjuvant"` - Post-surgical chemotherapy (Stage III, high-risk Stage II)
- `"Neoadjuvant"` - Before surgery (rectal cancer CRT)
- `"Perioperative"` - Before and after surgery (FOLFOX perioperative for rectal)

**Metastatic:**
- `"1L"` - First-line metastatic
- `"2L+"` - Second-line or later
- `"Maintenance"` - Continuation/maintenance after induction

---

### Biomarker Tagging Rules

**Key CRC Biomarkers:**

| Biomarker | When to Tag | Notes |
|-----------|-------------|-------|
| `"MSI-H/dMMR"` | When MSI status affects treatment | Tag in biomarker if NOT in disease_type |
| `"MSS"` | When microsatellite stable status is relevant | Indicates immunotherapy unlikely to work |
| `"RAS wild-type"` | Anti-EGFR eligibility | KRAS/NRAS wild-type = eligible |
| `"RAS mutated"` | Anti-EGFR NOT eligible | KRAS or NRAS mutation |
| `"BRAF V600E"` | BRAF-mutated CRC | Worse prognosis, specific therapy |
| `"BRAF wild-type"` | When BRAF status explicitly relevant | |
| `"HER2"` | HER2-amplified CRC | Rare but targetable |
| `"Left-sided"` | Tumor sidedness | Better anti-EGFR response |
| `"Right-sided"` | Tumor sidedness | Worse prognosis, less anti-EGFR benefit |
| `"NTRK fusion"` | NTRK-rearranged CRC | Rare, larotrectinib/entrectinib eligible |

**Sidedness as Biomarker:**
Tumor sidedness is clinically relevant in CRC and should be tagged as a biomarker when it influences treatment selection (especially anti-EGFR decisions).

---

### Fundable CRC Treatments

| Category | Drugs |
|----------|-------|
| **Chemotherapy (TAG in CRC)** | FOLFOX, FOLFIRI, FOLFOXIRI, CAPOX, capecitabine |
| **Anti-VEGF** | bevacizumab, aflibercept, ramucirumab |
| **Anti-EGFR** | cetuximab, panitumumab |
| **BRAF + MEK** | encorafenib (+cetuximab), dabrafenib, trametinib |
| **HER2-Directed** | trastuzumab, pertuzumab, trastuzumab deruxtecan, tucatinib |
| **Checkpoint Inhibitors** | pembrolizumab, nivolumab, ipilimumab |
| **Multi-kinase Inhibitors** | regorafenib |
| **NTRK Inhibitors** | larotrectinib, entrectinib |
| **Other Targeted** | fruquintinib (VEGFR), trifluridine/tipiracil (TAS-102) |

---

### Trial Inference Table

**MSI-H/dMMR CRC:**
| Context | Trial(s) |
|---------|----------|
| 1L pembrolizumab (MSI-H mCRC) | KEYNOTE-177 |
| Nivolumab + ipilimumab (MSI-H) | CheckMate-142 |
| Neoadjuvant pembrolizumab (dMMR rectal) | Multiple single-arm studies |

**BRAF V600E CRC:**
| Context | Trial(s) |
|---------|----------|
| Encorafenib + cetuximab | BEACON |
| Encorafenib + cetuximab + FOLFOX 1L | BREAKWATER |

**HER2-Amplified CRC:**
| Context | Trial(s) |
|---------|----------|
| Trastuzumab + tucatinib | MOUNTAINEER |
| Trastuzumab + pertuzumab | MyPathway |
| Trastuzumab deruxtecan | DESTINY-CRC01, DESTINY-CRC02 |

**Anti-EGFR (RAS/BRAF Wild-Type):**
| Context | Trial(s) |
|---------|----------|
| 1L FOLFOX/FOLFIRI + cetuximab | CRYSTAL, FIRE-3, CALGB/SWOG 80405 |
| 1L FOLFOX + panitumumab | PRIME, PARADIGM |
| Left-sided benefit | PARADIGM (subgroup) |

**Anti-VEGF:**
| Context | Trial(s) |
|---------|----------|
| 1L FOLFOX + bevacizumab | Multiple trials |
| 2L aflibercept | VELOUR |
| 2L ramucirumab | RAISE |

**Adjuvant:**
| Context | Trial(s) |
|---------|----------|
| 3 vs 6 months adjuvant oxaliplatin | IDEA collaboration |
| Stage III adjuvant FOLFOX/CAPOX | MOSAIC |

**Later Lines:**
| Context | Trial(s) |
|---------|----------|
| Regorafenib | CORRECT |
| TAS-102 (trifluridine/tipiracil) | RECOURSE |
| Fruquintinib | FRESCO |

---

## CRC Examples (56 Fields)

### Example 1: MSI-H mCRC 1L Treatment Selection

**Question:** A 58-year-old patient with newly diagnosed metastatic colorectal cancer is found to have MSI-H/dMMR status on molecular testing. What is the preferred first-line systemic therapy?

**Correct Answer:** Pembrolizumab monotherapy

```json
{
    "topic": "Treatment selection",
    "disease_stage": "Metastatic",
    "disease_type": "MSI-H/dMMR",
    "treatment_line": "1L",
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
- disease_type: `"MSI-H/dMMR"` - the defining characteristic for this treatment decision
- biomarker_1: `null` - MSI-H already captured in disease_type (redundancy rule)
- trial_1: `null` - topic is "Treatment selection", trial not explicitly named in stem (inference not allowed)
- cme_outcome_level: `"4 - Competence"` - patient vignette with treatment decision

---

### Example 2: BRAF V600E Second-Line Treatment

**Question:** A 62-year-old patient with BRAF V600E-mutated metastatic CRC has progressed on first-line FOLFOX plus bevacizumab. Based on the BEACON trial, what is the preferred second-line regimen?

**Correct Answer:** Encorafenib plus cetuximab

```json
{
    "topic": "Treatment selection",
    "disease_stage": "Metastatic",
    "disease_type": null,
    "treatment_line": "2L+",
    "treatment_1": "encorafenib",
    "treatment_2": "cetuximab",
    "treatment_3": null,
    "treatment_4": null,
    "treatment_5": null,
    "biomarker_1": "BRAF V600E",
    "biomarker_2": null,
    "biomarker_3": null,
    "biomarker_4": null,
    "biomarker_5": null,
    "trial_1": "BEACON",
    "trial_2": null,
    "trial_3": null,
    "trial_4": null,
    "trial_5": null,
    "drug_class_1": "BRAF inhibitor",
    "drug_class_2": "Anti-EGFR",
    "drug_class_3": null,
    "drug_target_1": "BRAF V600E",
    "drug_target_2": "EGFR",
    "drug_target_3": null,
    "prior_therapy_1": "Prior FOLFOX",
    "prior_therapy_2": "Prior bevacizumab",
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
    "evidence_type": "Phase 3 RCT",
    "trial_phase": "Phase 3",
    "cme_outcome_level": "4 - Competence",
    "data_response_type": "Comparative",
    "endpoint_type_1": null,
    "endpoint_type_2": null
}
```

**Rationale:**
- disease_type: `null` - BRAF V600E goes in biomarker, not disease_type for CRC
- biomarker_1: `"BRAF V600E"` - the actionable mutation
- prior_therapy_1/2: Captures the prior treatment context (progressed on FOLFOX + bev)
- Both targeted drugs (encorafenib + cetuximab) are tagged

---

### Example 3: Left-Sided RAS Wild-Type 1L Anti-EGFR

**Question:** A 55-year-old patient with left-sided, RAS wild-type, BRAF wild-type metastatic CRC is evaluated for first-line therapy. Which regimen is associated with improved overall survival in this population?

**Correct Answer:** FOLFOX plus panitumumab (based on PARADIGM)

```json
{
    "topic": "Treatment selection",
    "disease_stage": "Metastatic",
    "disease_type": null,
    "treatment_line": "1L",
    "treatment_1": "FOLFOX",
    "treatment_2": "panitumumab",
    "treatment_3": null,
    "treatment_4": null,
    "treatment_5": null,
    "biomarker_1": "RAS wild-type",
    "biomarker_2": "BRAF wild-type",
    "biomarker_3": "Left-sided",
    "biomarker_4": null,
    "biomarker_5": null,
    "trial_1": "PARADIGM",
    "trial_2": null,
    "trial_3": null,
    "trial_4": null,
    "trial_5": null,
    "drug_class_1": "Anti-EGFR",
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
    "efficacy_endpoint_1": "Overall survival (OS)",
    "efficacy_endpoint_2": null,
    "efficacy_endpoint_3": null,
    "outcome_context": null,
    "clinical_benefit": null,
    "guideline_source_1": null,
    "guideline_source_2": null,
    "evidence_type": "Phase 3 RCT",
    "trial_phase": "Phase 3",
    "cme_outcome_level": "4 - Competence",
    "data_response_type": "Comparative",
    "endpoint_type_1": null,
    "endpoint_type_2": null
}
```

**Rationale:**
- treatment_1: `"FOLFOX"` - chemotherapy IS tagged in CRC
- biomarker_3: `"Left-sided"` - sidedness is a biomarker in CRC affecting anti-EGFR benefit
- trial_1: `"PARADIGM"` - definitive trial for 1L anti-EGFR in left-sided RAS WT
- efficacy_endpoint_1: `"Overall survival (OS)"` - the question asks about OS benefit

---

### Example 4: HER2-Amplified CRC Clinical Efficacy

**Question:** In the MOUNTAINEER trial, what was the overall response rate with trastuzumab plus tucatinib in patients with HER2-positive metastatic CRC refractory to standard therapies?

**Correct Answer:** 38.1%

```json
{
    "topic": "Clinical efficacy",
    "disease_stage": "Metastatic",
    "disease_type": null,
    "treatment_line": "2L+",
    "treatment_1": "trastuzumab",
    "treatment_2": "tucatinib",
    "treatment_3": null,
    "treatment_4": null,
    "treatment_5": null,
    "biomarker_1": "HER2",
    "biomarker_2": null,
    "biomarker_3": null,
    "biomarker_4": null,
    "biomarker_5": null,
    "trial_1": "MOUNTAINEER",
    "trial_2": null,
    "trial_3": null,
    "trial_4": null,
    "trial_5": null,
    "drug_class_1": "Anti-HER2 mAb",
    "drug_class_2": "HER2 TKI",
    "drug_class_3": null,
    "drug_target_1": "HER2",
    "drug_target_2": "HER2",
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
    "efficacy_endpoint_1": "Overall response rate (ORR)",
    "efficacy_endpoint_2": null,
    "efficacy_endpoint_3": null,
    "outcome_context": "Primary endpoint met",
    "clinical_benefit": "Clinically meaningful",
    "guideline_source_1": null,
    "guideline_source_2": null,
    "evidence_type": "Phase 2 RCT",
    "trial_phase": "Phase 2",
    "cme_outcome_level": "3 - Knowledge",
    "data_response_type": "Numeric",
    "endpoint_type_1": "Primary",
    "endpoint_type_2": null
}
```

**Rationale:**
- topic: `"Clinical efficacy"` - asking about trial results (ORR)
- treatment_line: `"2L+"` - refractory to standard therapies
- biomarker_1: `"HER2"` - the biomarker defining eligibility
- cme_outcome_level: `"3 - Knowledge"` - tests recall of trial data
- data_response_type: `"Numeric"` - answer is a percentage

---

### Example 5: Adjuvant Duration (IDEA Collaboration)

**Question:** Based on the IDEA collaboration, what is the recommended duration of adjuvant oxaliplatin-based chemotherapy for patients with low-risk stage III colon cancer?

**Correct Answer:** 3 months of CAPOX

```json
{
    "topic": "Treatment indication",
    "disease_stage": "Early-stage",
    "disease_type": null,
    "treatment_line": "Adjuvant",
    "treatment_1": "CAPOX",
    "treatment_2": null,
    "treatment_3": null,
    "treatment_4": null,
    "treatment_5": null,
    "biomarker_1": null,
    "biomarker_2": null,
    "biomarker_3": null,
    "biomarker_4": null,
    "biomarker_5": null,
    "trial_1": "IDEA",
    "trial_2": null,
    "trial_3": null,
    "trial_4": null,
    "trial_5": null,
    "drug_class_1": null,
    "drug_class_2": null,
    "drug_class_3": null,
    "drug_target_1": null,
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
    "efficacy_endpoint_1": "Disease-free survival (DFS)",
    "efficacy_endpoint_2": null,
    "efficacy_endpoint_3": null,
    "outcome_context": "Subgroup analysis",
    "clinical_benefit": "Non-inferior",
    "guideline_source_1": null,
    "guideline_source_2": null,
    "evidence_type": "Phase 3 RCT",
    "trial_phase": "Phase 3",
    "cme_outcome_level": "3 - Knowledge",
    "data_response_type": "Qualitative",
    "endpoint_type_1": null,
    "endpoint_type_2": null
}
```

**Rationale:**
- topic: `"Treatment indication"` - asking about recommended regimen, not patient-specific
- treatment_line: `"Adjuvant"` - post-surgical therapy (curative intent)
- outcome_context: `"Subgroup analysis"` - low-risk vs high-risk subgroups
- clinical_benefit: `"Non-inferior"` - 3 months non-inferior to 6 months in low-risk

---

### Example 6: Biomarker Testing in CRC

**Question:** Which molecular testing is essential before selecting first-line therapy for metastatic colorectal cancer?

**Correct Answer:** RAS, BRAF, and MSI/MMR status

```json
{
    "topic": "Biomarker testing",
    "disease_stage": "Metastatic",
    "disease_type": null,
    "treatment_line": "1L",
    "treatment_1": null,
    "treatment_2": null,
    "treatment_3": null,
    "treatment_4": null,
    "treatment_5": null,
    "biomarker_1": "RAS wild-type",
    "biomarker_2": "BRAF V600E",
    "biomarker_3": "MSI-H/dMMR",
    "biomarker_4": null,
    "biomarker_5": null,
    "trial_1": null,
    "trial_2": null,
    "trial_3": null,
    "trial_4": null,
    "trial_5": null,
    "drug_class_1": null,
    "drug_class_2": null,
    "drug_class_3": null,
    "drug_target_1": null,
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
    "evidence_type": "Guideline recommendation",
    "trial_phase": null,
    "cme_outcome_level": "3 - Knowledge",
    "data_response_type": "Qualitative",
    "endpoint_type_1": null,
    "endpoint_type_2": null
}
```

**Rationale:**
- topic: `"Biomarker testing"` - question is specifically about testing
- biomarker_1-3: Lists the key biomarkers being tested (exception to redundancy rule for testing topic)
- treatment fields: `null` - no specific treatment is the focus
- guideline_source_1: `null` - no guideline body explicitly named in stem (do not infer from standard of care)
- evidence_type: `"Guideline recommendation"` - based on practice guidelines

---

## CRC Edge Cases

### Edge Case 1: Rectal Cancer TNT
- Tag `disease_type: "Rectal"` when discussing total neoadjuvant therapy (TNT), organ preservation, or sphincter-sparing approaches
- Otherwise, use `disease_type: null` for general CRC questions

### Edge Case 2: Oligometastatic Disease
- Still tag `disease_stage: "Metastatic"` even if potentially resectable
- Add `metastatic_site_1: "Oligometastatic disease"` if specifically mentioned
- Note: Conversion surgery may be curative intent (reflected via disease_stage context)

### Edge Case 3: Right-Sided BRAF V600E
- Tag both `biomarker: "BRAF V600E"` AND `biomarker: "Right-sided"` if both mentioned
- These often co-occur and both impact prognosis/treatment

### Edge Case 4: MSI Testing Question
- If topic is `"Biomarker testing"` about MSI testing, you CAN tag `biomarker: "MSI-H/dMMR"` even if that's also the disease_type for treatment questions

### Edge Case 5: Lynch Syndrome
- Tag `biomarker: "MSI-H/dMMR"` for Lynch syndrome (germline MMR deficiency)
- May also tag `special_population_1` if relevant (hereditary cancer syndrome)
