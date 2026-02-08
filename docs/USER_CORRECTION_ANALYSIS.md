# User Correction Analysis: 120 Heme Questions

## Executive Summary

Analysis of 77 questions with checkpoint comparison reveals a **critical pattern**: **LLMs are massively under-tagging**. Nearly every correction is `None → value`, meaning LLMs left fields empty that should have been populated.

**Questions analyzed:** 77 (with checkpoint data available)
**Total field corrections:** 700+ across all fields

---

## Priority 1: Critical Gaps (High-Frequency Corrections)

### 1. treatment_line (70 corrections)
**Problem:** LLMs leaving treatment_line NULL when it's inferable from context.

| Pattern | Count | Diseases |
|---------|-------|----------|
| NULL → "R/R" | 47 | ALL, CLL, DLBCL, FL |
| NULL → "Newly diagnosed" | 12 | ALL, CLL, DLBCL, FL |
| NULL → "Consolidation" | 4 | ALL |
| NULL → "Induction" | 3 | ALL |
| NULL → "Maintenance" | 1 | ALL |
| NULL → "MRD+" | 1 | ALL |

**Prompt Fix for ALL HEME PROMPTS:**
```
### treatment_line INFERENCE RULES:
- If question mentions "relapsed", "refractory", "R/R", "prior therapy", "second-line" → tag "R/R"
- If question mentions "newly diagnosed", "frontline", "first-line", "untreated" → tag "Newly diagnosed"
- ALL-specific:
  - "Induction" for initial intensive treatment
  - "Consolidation" for post-induction therapy
  - "Maintenance" for ongoing suppressive therapy
  - "MRD+" for MRD-positive disease state

**CRITICAL:** Do NOT leave treatment_line NULL when context clearly implies it.
```

---

### 2. drug_class_1 (70 corrections)
**Problem:** LLMs not tagging drug classes even when drugs are mentioned.

| Pattern | Count |
|---------|-------|
| NULL → "CAR-T therapy" | 24 |
| NULL → "Bispecific antibody" | 20 |
| NULL → "BCL-2 inhibitor" | 4 |
| NULL → "Asparaginase" | 4 |
| NULL → "Tyrosine kinase inhibitor" | 4 |
| NULL → "Covalent BTKi" | 3 |
| NULL → "Non-covalent BTKi" | 2 |
| NULL → "IMiD" | 2 |
| NULL → "PI3K inhibitor" | 2 |

**Prompt Fix for ALL HEME PROMPTS:**
```
### drug_class_1 AUTO-INFERENCE:
When tagging treatment_1, ALWAYS also tag drug_class_1:

| If treatment_1 contains | Tag drug_class_1 as |
|-------------------------|---------------------|
| axi-cel, liso-cel, tisa-cel, brexu-cel, obe-cel | "CAR-T therapy" |
| glofitamab, epcoritamab, mosunetuzumab | "Bispecific antibody" |
| blinatumomab | "Bispecific antibody" |
| venetoclax | "BCL-2 inhibitor" |
| ibrutinib, acalabrutinib, zanubrutinib | "Covalent BTKi" |
| pirtobrutinib | "Non-covalent BTKi" |
| lenalidomide | "IMiD" |
| idelalisib, duvelisib, copanlisib | "PI3K inhibitor" |
| ponatinib, dasatinib, imatinib | "Tyrosine kinase inhibitor" |
| asparaginase, pegaspargase, Erwinaze | "Asparaginase" |
```

---

### 3. drug_target_1 (69 corrections)
**Problem:** LLMs not tagging drug targets.

| Pattern | Count |
|---------|-------|
| NULL → "CD19" | 33 |
| NULL → "CD20" | 11 |
| NULL → "BTK" | 6 |
| NULL → "BCL-2" | 4 |
| NULL → "BCR-ABL" | 4 |
| NULL → "Asparagine synthetase" | 4 |

**Prompt Fix for ALL HEME PROMPTS:**
```
### drug_target_1 AUTO-INFERENCE:
When tagging treatment_1, ALWAYS also tag drug_target_1:

| Drug class | Primary target |
|------------|----------------|
| CAR-T (most) | "CD19" |
| Anti-CD20 (rituximab, obinutuzumab) | "CD20" |
| Bispecifics (CD20xCD3) | "CD20" (tumor) - do NOT tag CD3 |
| Blinatumomab (CD19xCD3) | "CD19" (tumor) - do NOT tag CD3 |
| BTK inhibitors | "BTK" |
| BCL-2 inhibitors | "BCL-2" |
| TKIs (ponatinib, dasatinib) | "BCR-ABL" |
| Asparaginase | "Asparagine synthetase" |
| IMiDs | "Cereblon" |
```

---

### 4. treatment_1 (66 corrections)
**Problem:** LLMs not tagging specific drug names.

**Top added treatments:**
- Axicabtagene ciloleucel (10x)
- Blinatumomab (8x)
- Glofitamab (5x)
- Venetoclax (5x)
- Lisocabtagene maraleucel (4x)
- Ponatinib (4x)
- Epcoritamab (3x)
- Asparaginase Erwinia chrysanthemi (3x)

**Prompt Fix:** Ensure all disease prompts have complete drug lists with canonical spelling.

---

### 5. age_group (61 corrections)
**Problem:** LLMs not inferring age from clinical vignettes.

| Pattern | Count |
|---------|-------|
| NULL → "Young" | 30 |
| NULL → "Transitional" | 19 |
| NULL → "AYA" | 6 |
| NULL → "Elderly" | 4 |
| NULL → "Pediatric" | 2 |

**Prompt Fix for ALL HEME PROMPTS:**
```
### age_group INFERENCE:
- Ages 15-39 → "AYA" (Adolescent/Young Adult)
- Ages 40-59 → "Young" or "Transitional"
- Ages 60-74 → "Transitional"
- Ages 75+ → "Elderly"
- If age is stated, ALWAYS tag age_group

**ALL-specific:**
- Pediatric protocols often used for AYA
- Age affects treatment intensity decisions
```

---

### 6. disease_type_1 (42 corrections)
**Problem:** LLMs not tagging disease subtypes.

**ALL (22 corrections):**
- NULL → "B-ALL" (22x) - LLMs should default to B-ALL when B-cell is mentioned

**DLBCL (13 corrections):**
- NULL → "Non-GCB" (6x)
- NULL → "IPI high-intermediate" (3x)
- NULL → "GCB" (1x)
- NULL → "Double-hit" (1x)
- NULL → "IPI high" (1x)

**Prompt Fix:**
```
### disease_type_1 for DLBCL:
- ALWAYS tag GCB vs Non-GCB when mentioned
- Tag IPI risk category when stated (IPI high, IPI high-intermediate, IPI low)
- Tag "Double-hit" or "Double-expressor" when mentioned

### disease_type_1 for ALL:
- "B-ALL" when B-cell lineage is mentioned (this is the vast majority)
- "T-ALL" when T-cell lineage is mentioned
```

---

### 7. disease_type_2 (21 corrections)
**Problem:** LLMs not tagging secondary disease characteristics.

**ALL (14 corrections):**
- NULL → "Ph-" (8x) - Philadelphia chromosome negative
- NULL → "Ph+" (5x) - Philadelphia chromosome positive
- NULL → "Ph-like" (1x)

**Prompt Fix for ALL prompt:**
```
### disease_type_2 for ALL:
- ALWAYS tag Ph status when mentioned:
  - "Ph+" or "Philadelphia chromosome positive" or "t(9;22)" → disease_type_2: "Ph+"
  - "Ph-" or "Philadelphia chromosome negative" → disease_type_2: "Ph-"
  - "Ph-like" or "BCR-ABL1-like" → disease_type_2: "Ph-like"
```

---

### 8. treatment_eligibility (34 corrections)
**Problem:** LLMs not tagging patient eligibility status.

| Pattern | Count |
|---------|-------|
| NULL → "CAR-T eligible" | 17 |
| NULL → "Requires treatment" | 7 |
| NULL → "CAR-T ineligible" | 2 |
| NULL → "Transplant-ineligible" | 2 |
| NULL → "Transplant-eligible" | 2 |

**Prompt Fix for ALL HEME PROMPTS:**
```
### treatment_eligibility INFERENCE:
- If patient is receiving CAR-T → "CAR-T eligible"
- If question discusses CAR-T contraindications → "CAR-T ineligible"
- If "transplant candidate" or receiving transplant → "Transplant-eligible"
- If "transplant ineligible" or frail/elderly → "Transplant-ineligible"
- CLL-specific: If initiating treatment → "Requires treatment"
```

---

### 9. biomarker_1 (34 corrections)
**Problem:** LLMs under-tagging biomarkers.

**Top biomarkers added:**
- MRD positive (5x)
- Ki67-high (4x)
- MRD negative (4x)
- CD20 (3x)
- MRD (3x) - general
- CD19 (2x)
- del(17p) (2x)
- t(9;22) (2x)
- POD24 (1x)
- EZH2 mutation (1x)

**Prompt Fix for ALL HEME PROMPTS:**
```
### biomarker_1 INFERENCE:
- ALWAYS tag MRD status when mentioned (MRD positive, MRD negative, MRD)
- Tag CD19/CD20 when relevant to target therapy
- Tag cytogenetics: del(17p), t(9;22), BCL2/BCL6/MYC rearrangements
- Tag prognostic markers: Ki67-high, POD24, EZH2 mutation
```

---

### 10. prior_therapy_1 (31 corrections)
**Problem:** LLMs not tagging prior therapies.

| Pattern | Count |
|---------|-------|
| NULL → "Prior R-CHOP" | 9 |
| NULL → "Prior BR" | 5 |
| NULL → "Prior Pola-R-CHP" | 3 |
| NULL → "Prior covalent BTKi" | 3 |
| NULL → "Prior chemoimmunotherapy" | 2 |
| NULL → "Prior asparaginase" | 2 |

**Prompt Fix for ALL HEME PROMPTS:**
```
### prior_therapy_1 INFERENCE:
- When patient is in R/R setting, INFER prior therapy from context
- Common prior therapies by disease:
  - DLBCL: "Prior R-CHOP", "Prior Pola-R-CHP"
  - FL: "Prior BR", "Prior R-CHOP"
  - CLL: "Prior covalent BTKi", "Prior CIT", "Prior venetoclax"
  - ALL: "Prior chemotherapy", "Prior asparaginase"

- Use drug CLASS for prior_therapy, not specific drug names:
  - "Prior covalent BTKi" (not "Prior ibrutinib")
  - "Prior anti-CD20" (not "Prior rituximab")
```

---

## Priority 2: Medium-Frequency Corrections

### 11. evidence_type (29 corrections)
| Pattern | Count |
|---------|-------|
| NULL → "Guideline recommendation" | 7 |
| NULL → "Phase 2" | 5 |
| NULL → "Phase 3" | 5 |
| NULL → "Retrospective study" | 3 |
| NULL → "Phase 1/2" | 3 |

**Prompt Fix:**
```
### evidence_type INFERENCE:
- If NCCN/ASCO/ESMO mentioned → "Guideline recommendation"
- If specific trial mentioned → Look up trial phase
- If "real-world" or registry data → "Real-world evidence"
- If no evidence source mentioned → Leave NULL (do not guess)
```

---

### 12. disease_stage (17 corrections)
**Problem:** LLMs not tagging stage for lymphomas.

| Pattern | Count | Diseases |
|---------|-------|----------|
| NULL → "Stage III" | 10 | DLBCL, FL |
| NULL → "Stage IV" | 5 | DLBCL, FL |
| NULL → "Advanced stage" | 1 | DLBCL |

**Prompt Fix for DLBCL and FL:**
```
### disease_stage for lymphomas:
- Tag stage when mentioned in clinical vignette
- "Advanced stage" = Stage III or IV
- Stage I-II = "Limited stage" or specific stage
```

---

### 13. disease_specific_factor (16 corrections)
| Pattern | Count |
|---------|-------|
| NULL → "Early relapse" | 8 |
| NULL → "Primary refractory" | 3 |
| NULL → "Bulky disease" | 2 |

**Prompt Fix for DLBCL:**
```
### disease_specific_factor for DLBCL:
- "Early relapse" - relapse within 12 months of initial therapy
- "Primary refractory" - no response to initial therapy
- "Bulky disease" - tumor mass ≥7.5-10 cm
- "Extranodal involvement" - disease outside lymph nodes
```

---

### 14. fitness_status (17 corrections)
| Pattern | Count |
|---------|-------|
| NULL → "Fit" | 15 |
| NULL → "Unfit" | 2 |

**Prompt Fix:**
```
### fitness_status INFERENCE:
- If patient receiving intensive therapy (CAR-T, intensive chemo) → "Fit"
- If young/middle-aged with no mentioned comorbidities → "Fit"
- If elderly with comorbidities or dose-reduced therapy → "Unfit"
- If frail or palliative intent → "Frail"
```

---

### 15. toxicity_type_1 (17 corrections)
| Pattern | Count |
|---------|-------|
| NULL → "CRS" | 6 |
| NULL → "ICANS" | 2 |
| NULL → "Silent inactivation" | 2 |

**Prompt Fix for CAR-T questions:**
```
### CAR-T toxicities:
- ALWAYS tag CRS when CAR-T is discussed
- Tag ICANS for neurotoxicity
- Tag "Prolonged cytopenias" when mentioned
```

---

### 16. efficacy_endpoint_1 (15 corrections)
| Pattern | Count |
|---------|-------|
| NULL → "Overall response rate (ORR)" | 6 |
| NULL → "MRD negativity rate" | 3 |
| NULL → "Progression-free survival (PFS)" | 2 |

**Prompt Fix:**
```
### efficacy_endpoint_1 INFERENCE:
- Tag endpoint ONLY when discussed in question/answer
- Common heme endpoints:
  - "Overall response rate (ORR)"
  - "Complete response rate (CR)"
  - "MRD negativity rate"
  - "Progression-free survival (PFS)"
  - "Event-free survival (EFS)"
  - "Overall survival (OS)"
```

---

## Field-by-Disease Matrix

| Field | ALL | CLL | DLBCL | FL |
|-------|-----|-----|-------|-----|
| treatment_line | 21 | 8 | 25 | 16 |
| drug_class_1 | 20 | 9 | 23 | 18 |
| drug_target_1 | 20 | 9 | 24 | 16 |
| treatment_1 | 20 | 9 | 21 | 16 |
| age_group | 22 | 7 | 23 | 9 |
| disease_type_1 | 22 | 3 | 13 | 4 |
| disease_type_2 | 14 | 0 | 5 | 2 |
| treatment_eligibility | 8 | 1 | 16 | 9 |
| biomarker_1 | 15 | 5 | 9 | 5 |
| prior_therapy_1 | 6 | 6 | 14 | 5 |
| evidence_type | 4 | 4 | 11 | 10 |
| disease_stage | 0 | 0 | 13 | 4 |
| disease_specific_factor | 0 | 0 | 14 | 2 |
| fitness_status | 6 | 1 | 8 | 2 |
| toxicity_type_1 | 3 | 2 | 6 | 6 |
| efficacy_endpoint_1 | 4 | 3 | 3 | 5 |

---

## Key Insights for Prompt Improvements

### Pattern 1: LLMs are Under-Tagging (Not Over-Tagging)
The overwhelming pattern is NULL → value corrections. LLMs are being too conservative and not inferring values from context.

**Fix:** Add explicit "INFERENCE RULES" sections telling LLMs WHEN to tag, not just WHAT to tag.

### Pattern 2: Drug-Class-Target Triad
When a treatment is tagged, drug_class and drug_target should ALWAYS be tagged as well.

**Fix:** Add lookup tables mapping drugs → classes → targets in each prompt.

### Pattern 3: Disease Subtypes Are Critical
- ALL: B-ALL vs T-ALL, Ph+ vs Ph-
- DLBCL: GCB vs Non-GCB, IPI risk, Double-hit
- FL: FLIPI risk, Grade, POD24
- CLL: del(17p)/TP53, IGHV status

**Fix:** Add subtype inference rules to each disease prompt.

### Pattern 4: Age and Fitness Matter
LLMs not extracting age_group and fitness_status from clinical vignettes.

**Fix:** Add explicit age ranges and fitness inference rules.

### Pattern 5: R/R Context Implies Prior Therapy
When treatment_line = "R/R", LLMs should infer prior_therapy from disease context.

**Fix:** Add prior therapy inference section.

---

## Recommended Changes by Prompt File

### all_prompt.txt (ALL)
1. Add B-ALL default for B-cell
2. Add Ph+/Ph- inference from t(9;22) mention
3. Add age_group inference for AYA/Pediatric
4. Add MRD status tagging rules
5. Add asparaginase-specific tagging

### cll_prompt.txt (CLL)
1. Add del(17p)/TP53 and IGHV tagging
2. Add BTKi class inference
3. Add "Requires treatment" eligibility
4. Add prior therapy inference for R/R

### dlbcl_prompt.txt (DLBCL)
1. Add GCB/Non-GCB inference
2. Add IPI risk tagging
3. Add Double-hit/Double-expressor
4. Add disease_specific_factor (early relapse, primary refractory)
5. Add CAR-T toxicity defaults (CRS, ICANS)

### fl_prompt.txt (FL)
1. Add FLIPI risk tagging
2. Add grade inference
3. Add POD24 as biomarker (COMPLETED)
4. Add prior therapy inference

### mcl_prompt.txt (MCL)
1. Add fitness_status inference
2. Add BTKi class inference
3. Add prior therapy patterns

---

## Example Few-Shot Corrections

### Example 1: ALL - Missing Ph+ status
**Question:** "55-year-old with B-ALL, t(9;22) positive, CR after induction..."
**LLM Tagged:** disease_type_1: NULL, disease_type_2: NULL
**User Corrected:** disease_type_1: "B-ALL", disease_type_2: "Ph+"

### Example 2: DLBCL - Missing drug class/target
**Question:** "Patient treated with axicabtagene ciloleucel..."
**LLM Tagged:** treatment_1: "Axicabtagene ciloleucel", drug_class_1: NULL, drug_target_1: NULL
**User Corrected:** drug_class_1: "CAR-T therapy", drug_target_1: "CD19"

### Example 3: FL - Missing prior therapy
**Question:** "FL patient progressed 18 months after BR, now R/R..."
**LLM Tagged:** treatment_line: "R/R", prior_therapy_1: NULL
**User Corrected:** prior_therapy_1: "Prior BR"

### Example 4: CLL - Missing treatment eligibility
**Question:** "CLL patient with iwCLL criteria requiring treatment..."
**LLM Tagged:** treatment_eligibility: NULL
**User Corrected:** treatment_eligibility: "Requires treatment"

---

## Implementation Priority

1. **Immediate (All Heme Prompts):**
   - Add drug_class/drug_target lookup tables
   - Add treatment_line inference rules
   - Add age_group inference from vignettes

2. **Disease-Specific:**
   - ALL: Ph+/Ph- inference, MRD tagging
   - DLBCL: GCB/Non-GCB, IPI, disease_specific_factor
   - FL: FLIPI, POD24 (done), prior therapy
   - CLL: del(17p)/TP53, IGHV, treatment eligibility

3. **Cross-Prompt (Consider for all prompts including solid tumors):**
   - Drug → Class → Target auto-inference
   - Age extraction from clinical vignettes
   - Fitness status inference from treatment intensity
