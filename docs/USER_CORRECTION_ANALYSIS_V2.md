# User Correction Analysis v2 - ACCURATE

Based on comparison of LLM `final_tags` from checkpoints vs current database values for 93 user-edited questions.

---

## Summary by Category

| Category | Count | Description |
|----------|-------|-------------|
| **Normalization** | 73 | Case, abbreviation, format |
| **Additions** | 67 | LLM left NULL, user added |
| **Semantic Changes** | 77 | Different judgment/interpretation |
| **Specificity** | 6 | Adding detail to existing value |
| **Removals** | 38 | User removed incorrect LLM tag |

---

## 1. NORMALIZATION ISSUES (73)
**These need normalization rules, not prompt changes.**

### 1.1 ALL-CAPS Drug Names → Title Case (35)
| LLM | User | Count |
|-----|------|-------|
| `AXI-CEL` | `Axicabtagene ciloleucel` | 9 |
| `PIRTOBRUTINIB` | `Pirtobrutinib` | 5 |
| `LISO-CEL` | `Lisocabtagene maraleucel` | 5 |
| `GLOFITAMAB` | `Glofitamab` | 4 |
| `BREXU-CEL` | `Brexucabtagene autoleucel` | 3 |
| `TISAGENLECLEUCEL` | `Tisagenlecleucel` | 3 |
| `IBRUTINIB` | `Ibrutinib` | 2 |
| `TISA-CEL` | `Tisagenlecleucel` | 2 |
| `MOSUNETUZUMAB` | `Mosunetuzumab` | 1 |
| `EPCORITAMAB` | `Epcoritamab` | 1 |
| `NEMTABRUTINIB` | `Nemtabrutinib` | 1 |
| `ACALABRUTINIB` | `Acalabrutinib` | 1 |
| `PARSACLISIB` | `Parsaclisib` | 1 |
| `TAFASITAMAB` | `Tafasitamab` | 1 |
| `LENALIDOMIDE` | `Lenalidomide` | 1 |
| `POLATUZUMAB VEDOTIN` | `Polatuzumab vedotin` | 1 |

**Action:** Add to `config/normalization_rules.yaml`

### 1.2 Case Inconsistency (11)
| LLM | User | Count |
|-----|------|-------|
| `Newly Diagnosed` | `Newly diagnosed` | 11 |

**Action:** Add case normalization rule for treatment_line

### 1.3 Abbreviation Expansion (4)
| LLM | User | Count |
|-----|------|-------|
| `TKI` | `Tyrosine kinase inhibitor` | 4 |

**Action:** Add abbreviation expansion rules

### 1.4 Terminology Standardization (4)
| LLM | User | Count | Field |
|-----|------|-------|-------|
| `ASCT-ineligible` | `Transplant-ineligible` | 2 | treatment_eligibility |
| `HSCT-eligible` | `Transplant-eligible` | 2 | treatment_eligibility |

**Action:** Add ASCT/HSCT → Transplant normalization

---

## 2. TAGGING/SPECIFICITY ISSUES (Prompt Changes Needed)

### 2.1 MRD Status Specificity (9)
**LLMs tag `MRD` but should tag `MRD positive` or `MRD negative`**

| LLM | User | Count |
|-----|------|-------|
| `MRD` | `MRD positive` | 5 |
| `MRD` | `MRD negative` | 4 |

**Prompt Fix (ALL heme prompts):**
```
### biomarker_1: MRD Status
ALWAYS specify MRD status with direction:
- `"MRD positive"` - Detectable MRD
- `"MRD negative"` - Undetectable MRD
- `"MRD"` - ONLY if direction is not stated

Do NOT use just "MRD" when the question specifies positive or negative.
```

### 2.2 Ki-67 Specificity (3)
**LLMs tag `Ki-67` but should tag `Ki67-high` when elevated**

| LLM | User | Count |
|-----|------|-------|
| `Ki-67` | `Ki67-high` | 3 |

**Prompt Fix (FL, MCL, DLBCL prompts):**
```
### biomarker_1: Ki-67
When Ki-67 is mentioned with a value:
- Ki-67 ≥30% → `"Ki67-high"` (not just "Ki-67")
- Ki-67 <30% → `"Ki67-low"` or leave as `"Ki-67"`

Ki-67 is a proliferation marker. High Ki-67 indicates aggressive disease.
```

### 2.3 BCR-ABL Terminology (2)
**Use cytogenetic nomenclature for ALL**

| LLM | User | Count |
|-----|------|-------|
| `BCR-ABL` | `t(9;22)` | 2 |

**Prompt Fix (ALL prompt):**
```
### biomarker for Ph+ ALL:
Use cytogenetic notation for Philadelphia chromosome:
- `"t(9;22)"` - Preferred (cytogenetic notation)
- `"BCR-ABL"` - Also acceptable but prefer t(9;22)
```

---

## 3. TREATMENT_LINE ISSUES

### 3.1 Remove MRD+ as valid value
**MRD+ was tagged by LLM but user corrected:**
- 3x: `MRD+` → `R/R`
- 1x: `MRD+` → `Consolidation`
- 1x: `MRD+` → NULL
- 1 question still has `MRD+` (Q4936)

**Action:** Remove `MRD+` from ALL prompt treatment_line valid values.

### 3.2 Induction → Newly diagnosed (3)
User changed `Induction` to `Newly diagnosed` in 3 ALL questions.

**Investigation needed:** Are these semantically different contexts, or should "Induction" be used?

### 3.3 Newly Diagnosed → 1L (3)
User changed to `1L` for 3 questions (2 MCL, 1 DLBCL).

**Decision:** Is `1L` a valid synonym for `Newly diagnosed`? Currently not in valid values.

---

## 4. ADDITIONS (67 - LLM left NULL)
**These indicate LLM under-tagging. May need prompt emphasis.**

### By Field:
| Field | Count | Pattern |
|-------|-------|---------|
| biomarker_1 | 8 | CD20, CD19, POD24, MRD, Ki67-high |
| prior_therapy_2 | 8 | Prior CIT, Prior covalent BTKi, Prior CAR-T |
| treatment_2 | 8 | CAR-T drugs, bispecifics when answer is drug class |
| biomarker_2 | 7 | POD24, TCF3::PBX1 fusion, t(9;22) |
| treatment_1 | 7 | Venetoclax, Epcoritamab, Brexucabtagene |
| prior_therapy_1 | 6 | Prior BTK inhibitor, Prior CIT, Prior Pola-R-CHP |
| treatment_eligibility | 5 | CAR-T eligible, Requires treatment |
| trial_1 | 5 | BRUIN-MCL, ZUMA-5, BRUIN |

### Key Pattern: Drug Class Answers
When correct answer is a drug CLASS (e.g., "CAR T-cell therapy", "Bispecific antibodies"), LLMs should infer specific drugs:

**Q4908 (DLBCL):** Answer = "CAR T-cell therapy"
- User added: treatment_1=Axicabtagene ciloleucel, treatment_2=Lisocabtagene maraleucel, treatment_3=Tisagenlecleucel

**Q4883/Q4884 (FL):** Answer = "Bispecific antibodies"
- User added: treatment_1=Epcoritamab, treatment_2=Mosunetuzumab

**Prompt Fix (all prompts):**
```
### CRITICAL: Drug Class Answers
When the correct answer is a drug CLASS, tag all approved specific drugs:

| Answer Class | Tag as treatment_1, treatment_2, etc. |
|--------------|---------------------------------------|
| "CAR T-cell therapy" (DLBCL) | Axicabtagene ciloleucel, Lisocabtagene maraleucel, Tisagenlecleucel |
| "CAR T-cell therapy" (MCL) | Brexucabtagene autoleucel |
| "Bispecific antibodies" (FL, post-April 2024) | Mosunetuzumab, Epcoritamab |
| "Bispecific antibodies" (DLBCL) | Glofitamab, Epcoritamab |
```

---

## 5. REMOVALS (38 - User removed LLM tag)
**These indicate LLM over-tagging or wrong field placement.**

### Key Patterns:
| LLM Tagged | Removed | Count | Reason |
|------------|---------|-------|--------|
| `disease_specific_factor: POD24` | NULL | 2 | POD24 belongs in biomarker, not disease_specific_factor |
| `resistance_mechanism: POD24` | NULL | 2 | POD24 is not a resistance mechanism |
| `evidence_type: Guideline recommendation` | NULL | 2 | Over-tagged |
| `biomarker_2: BCL2 rearrangement` | NULL | 2 | Not relevant to question |
| `biomarker_1: MYC rearrangement` | NULL | 1 | Incorrect |
| `biomarker_1: Non-GCB` | NULL | 1 | Non-GCB is disease_type, not biomarker |
| `biomarker_1: ABC` | NULL | 1 | ABC is disease_type, not biomarker |

**Prompt Fixes:**
1. POD24 → biomarker only (already done in FL prompt)
2. Non-GCB, GCB, ABC → disease_type_1, not biomarker
3. Don't over-tag evidence_type

---

## 6. SEMANTIC/JUDGMENT CHANGES (77)

### 6.1 answer_length_pattern (20)
| LLM | User | Count |
|-----|------|-------|
| `Uniform` | `Variable` | 15 |
| `Uniform` | `Correct longest` | 2 |
| `Variable` | `Uniform` | 2 |

**Observation:** LLMs default to "Uniform" too often. 75% of corrections are Uniform → Variable.

**Prompt Fix (all prompts):**
```
### answer_length_pattern
- `"Uniform"` - ONLY if all options are within ±20% word count
- `"Variable"` - Any noticeable length variation (DEFAULT if unsure)
- `"Correct longest"` - Correct answer is clearly longer than distractors
- `"Correct shortest"` - Correct answer is clearly shorter
```

### 6.2 distractor_homogeneity (12)
| LLM | User | Count |
|-----|------|-------|
| `Homogeneous` | `Heterogeneous` | 6 |
| `Heterogeneous` | `Homogeneous` | 6 |

**Observation:** 50/50 split - this is subjective. No clear LLM bias.

### 6.3 cme_outcome_level (5)
| LLM | User | Count |
|-----|------|-------|
| `4 - Competence` | `3 - Knowledge` | 4 |
| `3 - Knowledge` | `4 - Competence` | 1 |

**Observation:** LLMs may be over-tagging as Competence. Need clearer criteria.

---

## 7. ACTION ITEMS

### Normalization Rules (config/normalization_rules.yaml)
1. Add ALL-CAPS drug name → Title case mappings (35+ drugs)
2. Add `Newly Diagnosed` → `Newly diagnosed` case normalization
3. Add `TKI` → `Tyrosine kinase inhibitor` expansion
4. Add `ASCT-*` → `Transplant-*` terminology
5. Add `HSCT-*` → `Transplant-*` terminology

### Prompt Fixes - ALL Heme Prompts
1. MRD status specificity (MRD positive/negative)
2. Ki-67 specificity (Ki67-high when ≥30%)
3. Drug class → specific drugs inference
4. answer_length_pattern: default to Variable if unsure

### Prompt Fixes - Disease-Specific
- **ALL:** Remove MRD+ from treatment_line, add t(9;22) preference
- **FL:** POD24 in biomarker only (done)
- **DLBCL:** Non-GCB/GCB/ABC in disease_type, not biomarker

### Database Cleanup
1. Q4936: Change treatment_line from `MRD+` to appropriate value
2. Verify `1L` vs `Newly diagnosed` preference

---

## 8. QUESTIONS TO INVESTIGATE

### Q4831, Q4851, Q4867: Newly Diagnosed → 1L
Why did user change these? Is `1L` preferred over `Newly diagnosed` for certain contexts?

### Q4936: MRD+ treatment_line
This still has `MRD+` - needs correction to appropriate value.

### Induction vs Newly diagnosed
3 ALL questions: User changed `Induction` → `Newly diagnosed`. When should each be used?
