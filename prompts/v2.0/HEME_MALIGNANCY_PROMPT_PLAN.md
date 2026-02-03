# Hematologic Malignancy Prompt Development Plan

## Overview

Create disease-specific 70-field tagging prompts for 5 hematologic malignancies:
1. **DLBCL** (Diffuse Large B-Cell Lymphoma)
2. **FL** (Follicular Lymphoma)
3. **MCL** (Mantle Cell Lymphoma)
4. **CLL** (Chronic Lymphocytic Leukemia)
5. **ALL** (Acute Lymphoblastic Leukemia)

**Template:** Use `multiple_myeloma_prompt.txt` as the structural template since it's also a hematologic malignancy with similar patterns (no solid tumor staging, R/R vs newly diagnosed, similar drug classes).

---

## Prompt Structure (from MM template)

Each prompt follows this structure:

1. **Header** - Role definition + context
2. **Non-oncology detection** - SID/infection questions that mention the disease but aren't oncology
3. **Group A: Core Fields (20)** - topic, disease_stage, disease_type, treatment_line, treatments, biomarkers, trials
4. **Group B: Patient Characteristics (8)** - treatment_eligibility, age_group, fitness_status, etc.
5. **Group C: Treatment Metadata (10)** - drug_class, drug_target, prior_therapy, resistance
6. **Group D: Clinical Context (9)** - symptoms, metastatic sites, performance status
7. **Group E: Safety/Toxicity (7)** - toxicity types, grades, organs
8. **Group F: Efficacy/Outcomes (5)** - endpoints, clinical benefit
9. **Group G: Evidence/Guidelines (3)** - guideline sources, evidence type
10. **Group H: Question Format (13)** - CME outcome level, stem type, flaws
11. **Few-shot examples** - 3-5 complete examples with rationale
12. **Output format** - JSON schema

---

## Disease-Specific Content to Research

### For Each Disease, Define:

#### 1. Disease Classification
- [ ] Canonical disease_state value
- [ ] Trigger terms/synonyms
- [ ] Subtypes that should map here vs. separate diseases

#### 2. Staging System (disease_stage)
- [ ] Staging system used (Ann Arbor, Lugano, Rai, Binet, etc.)
- [ ] Valid stage values
- [ ] When to tag vs. when null

#### 3. Subtypes (disease_type_1, disease_type_2)
- [ ] Molecular/genetic subtypes (e.g., GCB vs ABC for DLBCL)
- [ ] Risk categories (high-risk, standard-risk)
- [ ] Histologic subtypes
- [ ] Hierarchy for conflicting subtypes

#### 4. Treatment Lines (treatment_line)
- [ ] First-line/Newly diagnosed triggers
- [ ] R/R triggers
- [ ] Maintenance/Consolidation patterns
- [ ] Disease-specific terminology

#### 5. Key Treatments (treatment_1-5)
- [ ] Frontline regimens
- [ ] R/R therapies
- [ ] Novel agents (CAR-T, bispecifics, ADCs)
- [ ] Backbone agents to EXCLUDE (not fundable)

#### 6. Biomarkers (biomarker_1-5)
- [ ] Diagnostic markers
- [ ] Prognostic markers
- [ ] Predictive markers
- [ ] MRD testing
- [ ] Redundancy rules (when biomarker is in disease_type)

#### 7. Key Trials (trial_1-5)
- [ ] Frontline trials
- [ ] R/R trials
- [ ] CAR-T/bispecific trials

#### 8. Drug Classes & Targets
- [ ] Common drug classes (e.g., BTK inhibitors, anti-CD20, PI3K inhibitors)
- [ ] Molecular targets

#### 9. Topic Disambiguation
- [ ] Disease-specific topic rules
- [ ] Safety profile vs AE management vs Prophylaxis patterns
- [ ] Treatment selection vs Treatment indication patterns

---

## Disease-Specific Research Sections

### 1. DLBCL (Diffuse Large B-Cell Lymphoma)

**Staging:** Ann Arbor/Lugano (Limited vs Advanced)
**Subtypes:**
- Cell of origin: GCB vs ABC (non-GCB)
- Double/Triple hit lymphoma
- Primary mediastinal, CNS, testicular
- High-grade B-cell lymphoma

**Key Treatments:**
- Frontline: R-CHOP, Pola-R-CHP
- R/R: CAR-T (axi-cel, liso-cel, tisa-cel), polatuzumab, loncastuximab, glofitamab, epcoritamab
- Salvage: R-ICE, R-DHAP, R-GDP

**Key Trials:**
- POLARIX (Pola-R-CHP)
- ZUMA-7 (axi-cel vs SOC)
- TRANSFORM (liso-cel)
- ELARA (tisa-cel FL)

**Biomarkers:** MYC, BCL2, BCL6 rearrangements, cell of origin, IPI score

---

### 2. FL (Follicular Lymphoma)

**Staging:** Ann Arbor/Lugano (often indolent, watch-and-wait)
**Subtypes:**
- Grade 1, 2, 3a, 3b
- Transformed FL (→ DLBCL)

**Key Treatments:**
- Frontline: BR, R-CHOP, R2 (lenalidomide + rituximab), obinutuzumab-chemo
- R/R: CAR-T (axi-cel, tisa-cel), mosunetuzumab, PI3K inhibitors (copanlisib, duvelisib), EZH2 inhibitor (tazemetostat)
- Maintenance: Rituximab maintenance

**Key Trials:**
- GALLIUM (obinutuzumab vs rituximab)
- ZUMA-5 (axi-cel for FL)
- ELARA (tisa-cel)
- RELEVANCE (R2 vs chemo-R)

**Biomarkers:** FLIPI score, EZH2 mutation, POD24 (progression within 24 months)

---

### 3. MCL (Mantle Cell Lymphoma)

**Staging:** Ann Arbor
**Subtypes:**
- Classical vs blastoid vs pleomorphic
- Indolent (leukemic non-nodal)
- TP53 mutated (high-risk)

**Key Treatments:**
- Frontline: BR, R-CHOP/R-DHAP + ASCT, VR-CAP
- R/R: BTK inhibitors (ibrutinib, acalabrutinib, zanubrutinib), CAR-T (brexu-cel), venetoclax, lenalidomide, pirtobrutinib
- Maintenance: Rituximab maintenance

**Key Trials:**
- TRIANGLE (ibrutinib + chemo)
- SHINE (ibrutinib + BR in elderly)
- ZUMA-2 (brexu-cel)
- BRUIN (pirtobrutinib)

**Biomarkers:** TP53 mutation, Ki-67, MIPI score, SOX11

---

### 4. CLL (Chronic Lymphocytic Leukemia)

**Staging:** Rai (US) or Binet (Europe)
**Subtypes:**
- IGHV mutated vs unmutated
- del(17p)/TP53 mutated (high-risk)
- del(11q), trisomy 12, del(13q)

**Key Treatments:**
- Frontline: BTK inhibitors (ibrutinib, acalabrutinib, zanubrutinib), venetoclax + obinutuzumab (fixed duration)
- R/R: BTK inhibitors, venetoclax-based, pirtobrutinib (post-BTKi), CAR-T (liso-cel)
- Historical: FCR, BR (now less common)

**Key Trials:**
- CLL14 (venetoclax + obinutuzumab)
- ELEVATE-TN (acalabrutinib)
- ALPINE (zanubrutinib vs ibrutinib)
- BRUIN (pirtobrutinib)
- TRANSCEND CLL 004 (liso-cel)

**Biomarkers:** IGHV mutation status, del(17p), TP53 mutation, del(11q), complex karyotype

---

### 5. ALL (Acute Lymphoblastic Leukemia)

**Classification:** B-ALL vs T-ALL
**Subtypes:**
- Ph+ (BCR-ABL positive)
- Ph-like
- MLL-rearranged
- Hypodiploid
- ETP T-ALL

**Key Treatments:**
- Frontline: Hyper-CVAD, pediatric-inspired regimens, + TKI for Ph+
- R/R: Blinatumomab, inotuzumab, CAR-T (tisa-cel for B-ALL), nelarabine (T-ALL)
- Ph+: TKIs (dasatinib, ponatinib)

**Key Trials:**
- ELIANA (tisa-cel pediatric)
- TOWER (blinatumomab vs chemo)
- INO-VATE (inotuzumab)

**Biomarkers:** BCR-ABL (Ph+), MRD status, CD19/CD22 expression

---

## Implementation Plan

### Phase 1: Research & Content Gathering (Per Disease)
1. Review existing CME questions for each disease
2. Identify common treatments, trials, biomarkers from questions
3. Cross-reference with NCCN guidelines for accuracy
4. Document disease-specific topic patterns

### Phase 2: Create Prompt Files
For each disease:
1. Copy MM prompt as template
2. Update header/context
3. Update disease_stage rules
4. Update disease_type hierarchy
5. Update treatment_line terminology
6. Update treatment lists with drug classes
7. Update biomarker rules & redundancy
8. Update trial lists
9. Add disease-specific topic disambiguation
10. Create 3-5 few-shot examples

### Phase 3: Testing & Validation
1. Tag sample questions with new prompts
2. Review accuracy vs manual tags
3. Iterate on prompt based on errors
4. Add edge cases to examples

---

## File Naming Convention

```
prompts/v2.0/disease_prompts/
├── dlbcl_prompt.txt
├── fl_prompt.txt (follicular_lymphoma_prompt.txt)
├── mcl_prompt.txt (mantle_cell_lymphoma_prompt.txt)
├── cll_prompt.txt
└── all_prompt.txt (acute_lymphoblastic_leukemia_prompt.txt)
```

---

## Priority Order

Based on likely question volume and complexity:
1. **CLL** - High volume, well-defined BTKi/venetoclax landscape
2. **DLBCL** - High volume, complex CAR-T/bispecific landscape
3. **FL** - Moderate volume, overlaps with DLBCL treatments
4. **MCL** - Moderate volume, BTKi-focused
5. **ALL** - Lower volume, distinct from B-cell malignancies

---

## Questions for Steve

1. Do you have sample tagged questions for these diseases I can review?
2. Are there specific activities/funders focused on these diseases?
3. Any diseases that should be combined (e.g., FL/DLBCL as "NHL")?
4. Priority order preference?

