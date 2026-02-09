# Breast Cancer Disease Module

This question has been classified as **Breast cancer**. Apply the following disease-specific rules in addition to the universal rules.

---

## disease_type: Subtyping Hierarchy

**CRITICAL PRIORITY:** Always try very hard to determine the molecular subtype. Subtype determination is the #1 priority for breast cancer.

### Step 1: Determine HER2 Status First
```
HER2 IHC 3+ OR IHC 2+/ISH+ → HER2-positive (HER2+)
HER2 IHC 1+ OR IHC 2+/ISH- → HER2-low
HER2 IHC 0 with membrane staining → HER2-ultralow
HER2 IHC 0 OR negative → HER2-negative
```

### Step 2: Determine Final Subtype

| Scenario | disease_type Value |
|----------|-------------------|
| HER2+ and HR+ both explicit | `"HR+/HER2+"` |
| HER2+ (HR- or not specified) | `"HER2+"` |
| HER2-low (any HR status) | `"HER2-low"` |
| HER2-ultralow | `"HER2-ultralow"` |
| HR+ and HER2-negative | `"HR+/HER2-"` |
| ER-, PR-, HER2- | `"Triple-negative"` |
| Ductal carcinoma in situ | `"DCIS"` |
| Invasive lobular carcinoma focus | `"ILC"` |

### Edge Case: HR+/HER2-low Classification
**Critical decision for Treatment selection questions:**
- If answer involves **T-DXd** (trastuzumab deruxtecan) → Use `"HER2-low"` or `"HER2-ultralow"`
- Otherwise → Use `"HR+/HER2-"` (CDK4/6i, endocrine therapy drive treatment)
- *Rationale:* T-DXd is the only drug specifically approved for HER2-low. When T-DXd is the treatment, HER2-low status is clinically actionable.

---

## disease_stage: Breast Cancer Staging

| Value | Triggers |
|-------|----------|
| `"Early-stage"` | Stage I, II, III, "non-metastatic", "resectable", "operable", "adjuvant", "neoadjuvant" |
| `"Metastatic"` | Stage IV, "mBC", "MBC", "metastatic", "advanced breast cancer" |

**IMPORTANT:** Stage III is "Early-stage" (non-metastatic, curative intent)

---

## treatment_line: Breast Cancer Conventions

**Early-Stage:**
- `"Adjuvant"` - After surgery
- `"Neoadjuvant"` - Before surgery
- `"Perioperative"` - Before and after surgery

**Metastatic:**
- `"1L"` - First-line, treatment-naive metastatic
- `"2L+"` - Second-line or later, after progression
- `"Maintenance"` - Continuation after response

---

## Fundable Breast Cancer Treatments

### HER2+ Disease
`"trastuzumab"`, `"pertuzumab"`, `"trastuzumab deruxtecan"`, `"trastuzumab emtansine"`, `"tucatinib"`, `"neratinib"`, `"lapatinib"`, `"margetuximab"`

### HR+/HER2- Disease
**CDK4/6 Inhibitors:** `"palbociclib"`, `"ribociclib"`, `"abemaciclib"`
**Other:** `"everolimus"`, `"alpelisib"`, `"elacestrant"`, `"capivasertib"`, `"inavolisib"`

### Triple-Negative Disease
**Immunotherapy:** `"pembrolizumab"`, `"atezolizumab"`
**ADCs:** `"sacituzumab govitecan"`, `"datopotamab deruxtecan"`
**PARP Inhibitors:** `"olaparib"`, `"talazoparib"`

### Drug Class Expansion (Use STARTDATE for temporal context)

| Drug Class | Setting | Expand To |
|------------|---------|-----------|
| CDK4/6 inhibitor | 1L mBC | palbociclib, ribociclib, abemaciclib |
| CDK4/6 inhibitor | Adjuvant | abemaciclib, ribociclib (post-2024) |
| Antibody-drug conjugate (ADC) | HER2 | trastuzumab deruxtecan, trastuzumab emtansine |
| PARP inhibitor | gBRCA+ mBC | olaparib, talazoparib |

---

## Biomarker Redundancy (Breast Cancer Specific)

| If disease_type is... | DO NOT tag biomarker: |
|----------------------|----------------------|
| `"HER2+"` | `"HER2"` |
| `"HR+/HER2-"` | `"HER2"` |
| `"Triple-negative"` | `"HER2"` |

**Non-redundant biomarkers to tag when relevant:**
- `"PD-L1"` - for immunotherapy eligibility (TNBC)
- `"PIK3CA"` - for alpelisib/inavolisib
- `"ESR1"` - for elacestrant
- `"BRCA1/2"` - for PARP inhibitors
- `"Oncotype DX"`, `"MammaPrint"` - prognostic assays

---

## Trial Inference Table (Breast Cancer)

### HER2+ Disease
| Drug + Context | Trial |
|----------------|-------|
| Trastuzumab + pertuzumab + chemo in 1L HER2+ mBC | `"CLEOPATRA"` |
| T-DXd vs T-DM1 in HER2+ mBC | `"DESTINY-Breast03"` |
| T-DXd in HER2+ 2L+ mBC | `"DESTINY-Breast01"` |
| Tucatinib + trastuzumab in HER2+ brain mets | `"HER2CLIMB"` |
| T-DM1 adjuvant in HER2+ residual disease | `"KATHERINE"` |
| Pertuzumab adjuvant in HER2+ early BC | `"APHINITY"` |

### HER2-low Disease
| Drug + Context | Trial |
|----------------|-------|
| T-DXd in HER2-low mBC | `"DESTINY-Breast04"` |
| T-DXd in HER2-ultralow | `"DESTINY-Breast06"` |

### HR+/HER2- Disease
| Drug + Context | Trial |
|----------------|-------|
| Ribociclib + letrozole in 1L HR+/HER2- mBC | `"MONALEESA-2"` |
| Ribociclib + fulvestrant in 2L+ HR+/HER2- mBC | `"MONALEESA-3"` |
| Ribociclib in premenopausal HR+/HER2- | `"MONALEESA-7"` |
| Abemaciclib + fulvestrant in 2L+ HR+/HER2- mBC | `"MONARCH-2"` |
| Abemaciclib + AI in 1L HR+/HER2- mBC | `"MONARCH-3"` |
| Abemaciclib adjuvant in high-risk HR+/HER2- | `"monarchE"` |
| Ribociclib adjuvant in HR+/HER2- | `"NATALEE"` |
| Palbociclib + letrozole in 1L HR+/HER2- mBC | `"PALOMA-2"` |
| Palbociclib + fulvestrant in 2L+ HR+/HER2- mBC | `"PALOMA-3"` |
| Elacestrant in ESR1-mutated HR+/HER2- | `"EMERALD"` |
| Alpelisib + fulvestrant in PIK3CA-mutated | `"SOLAR-1"` |
| Capivasertib + fulvestrant in HR+/HER2- | `"CAPItello-291"` |
| Inavolisib + palbociclib + fulvestrant in PIK3CA-mutated | `"INAVO120"` |

### Triple-Negative Disease
| Drug + Context | Trial |
|----------------|-------|
| Pembrolizumab + chemo in 1L mTNBC (PD-L1+) | `"KEYNOTE-355"` |
| Pembrolizumab neoadjuvant in early TNBC | `"KEYNOTE-522"` |
| SG + pembrolizumab in 1L mTNBC | `"ASCENT-04"` |
| Atezolizumab + nab-paclitaxel in 1L mTNBC | `"IMpassion130"` |
| Sacituzumab govitecan in 2L+ mTNBC | `"ASCENT"` |
| Datopotamab deruxtecan in mTNBC | `"TROPION-Breast02"` |
| Olaparib in BRCA-mutated mBC | `"OlympiAD"` |
| Talazoparib in BRCA-mutated mBC | `"EMBRACA"` |

---

## Contextual Inference from Trials

| Trial | Inferred disease_type | Inferred treatment_line | Inferred disease_stage |
|-------|----------------------|------------------------|----------------------|
| DESTINY-Breast04 | HER2-low | 2L+ | Metastatic |
| DESTINY-Breast03 | HER2+ | 2L+ | Metastatic |
| CLEOPATRA | HER2+ | 1L | Metastatic |
| monarchE | HR+/HER2- | Adjuvant | Early-stage |
| NATALEE | HR+/HER2- | Adjuvant | Early-stage |
| KEYNOTE-522 | Triple-negative | Neoadjuvant | Early-stage |
| KEYNOTE-355 | Triple-negative | 1L | Metastatic |
| ASCENT-04 | Triple-negative | 1L | Metastatic |
| CAPItello-291 | HR+/HER2- | 2L+ | Metastatic |
| SOLAR-1 | HR+/HER2- | 2L+ | Metastatic |
| EMERALD | HR+/HER2- | 2L+ | Metastatic |

---

## Special Cases

### BIA-ALCL (Breast Implant-Associated ALCL)
- Classified under "Breast cancer" for disease_state
- For tagging: topic = "AE management" (complication of breast reconstruction)
- disease_type = `null`

### DCIS
- disease_type = `"DCIS"`
- disease_stage = `"Early-stage"` (always - stage 0)

---

## Examples

### Example 1: HER2+ Metastatic First-Line
**Q:** "What is the preferred first-line treatment for HER2-positive metastatic breast cancer based on the CLEOPATRA trial?"
**A:** "Trastuzumab + pertuzumab + docetaxel"

```json
{
    "topic": "Treatment indication",
    "disease_stage": "Metastatic",
    "disease_type": "HER2+",
    "treatment_line": "1L",
    "treatment_1": "trastuzumab",
    "treatment_2": "pertuzumab",
    "treatment_3": null,
    "treatment_4": null,
    "treatment_5": null,
    "biomarker_1": null,
    "biomarker_2": null,
    "biomarker_3": null,
    "biomarker_4": null,
    "biomarker_5": null,
    "trial_1": "CLEOPATRA",
    "trial_2": null,
    "trial_3": null,
    "trial_4": null,
    "trial_5": null,
    "drug_class_1": "Monoclonal antibody",
    "drug_class_2": null,
    "drug_class_3": null,
    "drug_target_1": "HER2",
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
    "evidence_type": "Phase 3 RCT",
    "trial_phase": "Phase 3",
    "cme_outcome_level": "3 - Knowledge",
    "data_response_type": "Qualitative",
    "endpoint_type_1": null,
    "endpoint_type_2": null
}
```
**Rationale:** Treatment indication (not selection) - asking about preferred/approved treatment. HER2+ → don't tag HER2 as biomarker. CLEOPATRA explicitly mentioned. Docetaxel not tagged (chemo).

---

### Example 2: HER2-low with Trial Inference
**Q:** "What is the clinical benefit of T-DXd in HER2-low metastatic breast cancer after prior chemotherapy?"
**A:** "Significant improvement in PFS and OS compared to chemotherapy"

```json
{
    "topic": "Clinical efficacy",
    "disease_stage": "Metastatic",
    "disease_type": "HER2-low",
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
    "trial_1": "DESTINY-Breast04",
    "trial_2": null,
    "trial_3": null,
    "trial_4": null,
    "trial_5": null,
    "drug_class_1": "Antibody-drug conjugate (ADC)",
    "drug_class_2": null,
    "drug_class_3": null,
    "drug_target_1": "HER2",
    "drug_target_2": null,
    "drug_target_3": null,
    "prior_therapy_1": "Prior chemotherapy",
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
    "efficacy_endpoint_2": "Overall survival (OS)",
    "efficacy_endpoint_3": null,
    "outcome_context": null,
    "clinical_benefit": "Statistically significant",
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
**Rationale:** Clinical efficacy topic → trial inference allowed. T-DXd + HER2-low + mBC = DESTINY-Breast04. "After prior chemotherapy" → 2L+, prior_therapy_1 tagged.

---

### Example 3: HR+/HER2- with CDK4/6 Inhibitor Patient Vignette
**Q:** "A 62-year-old postmenopausal woman with newly diagnosed HR+/HER2- metastatic breast cancer. Which regimen is most appropriate as initial therapy?"
**A:** "Ribociclib + letrozole"

```json
{
    "topic": "Treatment selection",
    "disease_stage": "Metastatic",
    "disease_type": "HR+/HER2-",
    "treatment_line": "1L",
    "treatment_1": "ribociclib",
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
    "drug_class_1": "CDK4/6 inhibitor",
    "drug_class_2": null,
    "drug_class_3": null,
    "drug_target_1": "CDK4/6",
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
    "special_population_1": "Elderly (>=65 years)",
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
**Rationale:** Patient vignette → Treatment selection (Level 4 Competence). "Newly diagnosed metastatic" → 1L. Letrozole not tagged. 62-year-old → special_population. No trial inference (not Clinical efficacy topic).

---

### Example 4: TNBC Neoadjuvant Immunotherapy
**Q:** "Based on KEYNOTE-522, what is the role of pembrolizumab in early-stage triple-negative breast cancer?"
**A:** "Pembrolizumab + chemotherapy in the neoadjuvant and adjuvant setting improves pCR and EFS"

```json
{
    "topic": "Clinical efficacy",
    "disease_stage": "Early-stage",
    "disease_type": "Triple-negative",
    "treatment_line": "Neoadjuvant",
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
    "trial_1": "KEYNOTE-522",
    "trial_2": null,
    "trial_3": null,
    "trial_4": null,
    "trial_5": null,
    "drug_class_1": "Immune checkpoint inhibitor",
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
    "efficacy_endpoint_2": "Event-free survival (EFS)",
    "efficacy_endpoint_3": null,
    "outcome_context": null,
    "clinical_benefit": null,
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
**Rationale:** Early-stage TNBC, neoadjuvant setting. Endpoints pCR and EFS tagged from answer. Trial explicitly mentioned.

---

### Example 5: PIK3CA-mutated with Targeted Therapy
**Q:** "What targeted therapy is approved for PIK3CA-mutated HR+/HER2- mBC after progression on CDK4/6i?"
**A:** "Alpelisib + fulvestrant"

```json
{
    "topic": "Treatment indication",
    "disease_stage": "Metastatic",
    "disease_type": "HR+/HER2-",
    "treatment_line": "2L+",
    "treatment_1": "alpelisib",
    "treatment_2": null,
    "treatment_3": null,
    "treatment_4": null,
    "treatment_5": null,
    "biomarker_1": "PIK3CA",
    "biomarker_2": null,
    "biomarker_3": null,
    "biomarker_4": null,
    "biomarker_5": null,
    "trial_1": null,
    "trial_2": null,
    "trial_3": null,
    "trial_4": null,
    "trial_5": null,
    "drug_class_1": "PI3K inhibitor",
    "drug_class_2": null,
    "drug_class_3": null,
    "drug_target_1": "PIK3CA",
    "drug_target_2": null,
    "drug_target_3": null,
    "prior_therapy_1": "Prior CDK4/6 inhibitor",
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
    "cme_outcome_level": "3 - Knowledge",
    "data_response_type": "Qualitative",
    "endpoint_type_1": null,
    "endpoint_type_2": null
}
```
**Rationale:** PIK3CA is NOT in disease_type → tag as biomarker. "After progression on CDK4/6i" → prior_therapy, 2L+. Fulvestrant not tagged (hormonal backbone).

---

### Example 6: Biomarker Testing (HER2 Exception)
**Q:** "Which biomarkers should be tested in all newly diagnosed breast cancer?"
**A:** "ER, PR, HER2"

```json
{
    "topic": "Biomarker testing",
    "disease_stage": null,
    "disease_type": null,
    "treatment_line": null,
    "treatment_1": null,
    "treatment_2": null,
    "treatment_3": null,
    "treatment_4": null,
    "treatment_5": null,
    "biomarker_1": "HER2",
    "biomarker_2": null,
    "biomarker_3": null,
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
    "evidence_type": null,
    "trial_phase": null,
    "cme_outcome_level": "3 - Knowledge",
    "data_response_type": "Qualitative",
    "endpoint_type_1": null,
    "endpoint_type_2": null
}
```
**Rationale:** Exception to redundancy rule - topic is "Biomarker testing" so HER2 can be tagged as biomarker. No specific subtype → disease_type null.
