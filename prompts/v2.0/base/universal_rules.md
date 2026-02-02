# Universal Tagging Rules

These rules apply to ALL diseases. Disease-specific rules in the disease module take precedence when there is a conflict.

---

## Core Principles

### 1. Use Null Appropriately
- Use `null` when a value cannot be determined with confidence
- Use `null` for unused multi-value slots (e.g., treatment_3 through treatment_5 when only 2 drugs)
- **Never guess** - if uncertain, use `null`

### 2. Consider the Correct Answer
- The correct answer often reveals context not in the question
- Subtype, treatment line, and stage may be implied by the answer
- Use answer content to inform your tagging

### 3. Topic Definitions (Apply Consistently)

| Topic | Key Trigger | Example |
|-------|-------------|---------|
| **Treatment selection** | Patient vignette + "which therapy" — choosing WHICH drug/regimen to use | "A 55-year-old woman... which regimen is most appropriate?" |
| **Treatment indication** | Eligibility, candidacy, criteria — whether a patient MEETS CRITERIA for a treatment | "Which eligibility criteria for CAR-T?", "Does age exclude transplant?", "Which patients are candidates?" |
| **Clinical efficacy** | Trial results, response rates, survival | "What was the ORR in TRIAL-X?" |
| **Safety profile** | Knowing WHAT AEs to expect or recognize — awareness of the toxicity profile | "What are common AEs with X?", "Which symptoms should you ask about?" |
| **AE management** | What to DO about an AE that has occurred — hold, dose-reduce, treat | "Patient develops Grade 3 pneumonitis, what is the next step?" |
| **Biomarker testing** | Testing, companion diagnostics | "Which patients should be tested for X?" |
| **Mechanism of action** | How drug works | "What is the target of X?" |
| **Study design** | Enrollment, endpoints, trial structure | "Which patients were enrolled in TRIAL-X?" |

#### Critical Topic Boundaries

**Treatment selection vs Treatment indication:**
- **Treatment selection** = choosing WHICH drug/regimen from among options for a patient
- **Treatment indication** = whether the patient MEETS CRITERIA (eligibility, indications, contraindications, candidacy)
- If the question asks "which eligibility criteria," "is this patient a candidate," or "does X exclude Y from treatment" → **Treatment indication**
- If the question asks "which drug/regimen should be used" → **Treatment selection**

**Safety profile vs AE management:**
- **Safety profile** = knowing what AEs to expect or recognize (awareness, recognition)
- **AE management** = what to DO about an AE already occurring (intervention, management steps)
- "Which symptoms will you ask about to determine if he is experiencing adverse events?" → **Safety profile** (recognizing, not managing)
- "Patient develops Grade 2 CRS, what is the recommended management?" → **AE management** (acting on the AE)

---

## Treatment Tagging Rules

### Treatment Scope: Correct Answer Focus
Tag treatments from the **CORRECT ANSWER** primarily. Only tag stem treatments if they are the educational focus of the question. **Do NOT enumerate drugs from all answer options** — if A, B, C, D each list a different drug, only tag the drug(s) from the correct answer (and any focal drug in the stem). This prevents over-tagging with drugs that are merely distractors.

### Fundable Drugs Only
Tag ONLY drugs of pharmaceutical interest for CME funding:
- Targeted therapies (TKIs, mAbs)
- ADCs
- Immunotherapies (checkpoint inhibitors, CAR-T, bispecifics)
- Novel agents

### DO NOT Tag
- **Chemotherapy agents**: carboplatin, paclitaxel, docetaxel, capecitabine, doxorubicin, etc.
- **Hormonal backbone**: fulvestrant, letrozole, anastrozole, tamoxifen (when combined with fundable drug)
- **Radiation therapy**
- **Surgical procedures**
- **Supportive care**: G-CSF, antiemetics, steroids (unless explicitly the focus)

### Combination Therapy
- For combinations with ONE fundable drug: tag only the fundable drug
  - "ribociclib + letrozole" → treatment_1: "ribociclib" (letrozole not tagged)
  - "pembrolizumab + chemotherapy" → treatment_1: "pembrolizumab"
- For combinations with MULTIPLE fundable drugs: tag each in separate slots
  - "trastuzumab + pertuzumab" → treatment_1: "trastuzumab", treatment_2: "pertuzumab"

### Drug Class Expansion
When question mentions a drug class without specific agent:
- Expand to all approved drugs in that class (as of question STARTDATE)
- Put each drug in a separate treatment slot
- Example: "CDK4/6 inhibitor" for metastatic → treatment_1-3: palbociclib, ribociclib, abemaciclib

---

## Biomarker Redundancy Rules

### Core Rule
**DO NOT tag a biomarker if it is already captured in disease_type**

| If disease_type is... | Don't tag biomarker: |
|-----------------------|---------------------|
| `"EGFR-mutated"` | `"EGFR mutation"` |
| `"HER2+"` | `"HER2"` |
| `"ALK-positive"` | `"ALK"` |
| `"MSI-H/dMMR"` | `"MSI-H"` |
| `"BRCA-mutated"` | `"BRCA1/2"` |

### Exception: Biomarker Testing Topic
If topic is `"Biomarker testing"` and question is about testing for a specific biomarker, you MAY tag that biomarker even if it's in disease_type.

### Non-Redundant Biomarkers
Always OK to tag biomarkers that are ADDITIONAL to disease_type:
- PIK3CA (in HR+/HER2- breast cancer → tag as biomarker)
- ESR1 (in HR+/HER2- → tag as biomarker)
- PD-L1 (in any disease → tag as biomarker)
- TMB (in any disease → tag as biomarker)

---

## Trial Inference Rules

### When to Infer Trial Names
**ALLOWED** for topics: `"Clinical efficacy"`, `"Study design"`
- Use drug + indication + population to confidently identify the trial
- Must have high confidence - if uncertain, use `null`

**NOT ALLOWED** for all other topics: `"Treatment selection"`, `"Treatment indication"`, `"AE management"`, `"Biomarker testing"`, `"Mechanism of action"`, `"Patient selection"`, `"Supportive care"`, `"Monitoring/follow-up"`, `"Safety profile"`
- These ask "which drug to use" or about non-efficacy concepts — not "what did the trial show"
- Only tag trial if explicitly named in the question stem or answer choices

### Inference Requirements
All of these must be clear to infer a trial:
1. Specific drug(s)
2. Specific indication/disease state
3. Specific treatment line or setting
4. Clinical efficacy or study design context

---

## Group A-F Field Guidelines

### Group A: Treatment Metadata
- **drug_class**: Use when discussing a class of drugs (e.g., "EGFR TKI")
- **drug_target**: Use when discussing molecular target
- **prior_therapy**: Only tag when explicitly mentioned as prior treatment
- **resistance_mechanism**: Only tag when explicitly discussed

### Group B: Clinical Context
- **metastatic_site**: Only tag sites explicitly mentioned
- **symptom**: Only tag symptoms mentioned in vignette
- **special_population**: Tag patient characteristics that affect treatment (elderly, organ dysfunction)
- **performance_status**: Only tag if explicitly stated (ECOG, KPS, fit/unfit)

### Group C: Safety/Toxicity
- **toxicity_type**: Tag specific toxicities discussed
- **toxicity_organ**: Tag organ system if toxicity focus
- **toxicity_grade**: Tag grade if mentioned (Grade 3, Grade >=3)

### Group D: Efficacy/Outcomes
- **efficacy_endpoint**: Tag ONLY when topic is "Clinical efficacy" or "Study design". For ALL other topics (Treatment selection, Treatment indication, AE management, Biomarker testing, etc.), leave efficacy_endpoint fields **null** — even if endpoint data is mentioned in passing in the question text. Do not infer endpoints for non-efficacy questions.
- **outcome_context**: Same gating rule — only tag when topic is "Clinical efficacy" or "Study design"
- **clinical_benefit**: Same gating rule — only tag when topic is "Clinical efficacy" or "Study design"

### Group E: Evidence/Guidelines
- **guideline_source**: Tag ONLY when the guideline body (NCCN, ASCO, ESMO, IMWG, etc.) is **explicitly named** in the question stem or answer choices. Do NOT infer a guideline source from treatment recommendations alone.
- **evidence_type**: Tag ONLY when a specific study, trial, or evidence category is **explicitly referenced**. Do NOT infer evidence_type from treatment regimens alone (e.g., a clinical vignette asking "which treatment" is NOT automatically "Phase 3 RCT" just because a trial exists for that drug).
- **trial (inference restriction)**: Do NOT infer trial names from treatment regimens alone — the trial must be mentioned by name or NCT number. Exception: trial inference IS allowed when topic is "Clinical efficacy" or "Study design" (see Trial Inference Rules above).

### Group F: Question Format
- **cme_outcome_level**:
  - Level 3 (Knowledge): Tests recall/recognition
  - Level 4 (Competence): Tests application to clinical scenario
- **data_response_type**:
  - Numeric: Answer is a number
  - Qualitative: Answer is descriptive
  - Comparative: Answer compares options
- **answer_length_pattern**:
  - **Uniform** = all answer options are similar in length and detail (within roughly 50% of each other). When options are drug names, regimen names, short clinical phrases, or sentences of comparable length, use Uniform. **Default to Uniform when uncertain.**
  - **Variable** = answer options differ substantially in length (e.g., one option is a single word or short phrase while another is a full sentence or paragraph)
  - **Correct longest** = the correct answer is noticeably longer than the distractors
  - **Correct shortest** = the correct answer is noticeably shorter than the distractors
  - Examples:
    - A) Daratumumab  B) Bortezomib  C) Lenalidomide  D) Carfilzomib → **Uniform** (all single drug names)
    - A) Observation  B) Bortezomib, lenalidomide, dexamethasone for 4 cycles followed by ASCT  C) Lenalidomide  D) Daratumumab → **Variable** (option B is much longer)
    - A) Yes  B) No  C) Only if PD-L1 positive  D) Only in clinical trials → **Variable** (mixed lengths)
- **distractor_homogeneity**:
  - **Homogeneous** = all distractors (incorrect options) are from the SAME clinical category AND are plausible alternatives for the clinical scenario (e.g., all are proteasome inhibitors, all are staging systems, all are treatment regimens for the same setting)
  - **Heterogeneous** = distractors span DIFFERENT categories, include a mix of concepts, or include clearly implausible options (e.g., a drug mixed with a biomarker, or a treatment option mixed with a diagnostic test)
  - Examples:
    - A) Bortezomib  B) Carfilzomib  C) Ixazomib  D) Lenalidomide → **Homogeneous** (all are MM drugs, plausible alternatives)
    - A) Start CAR-T  B) Check MRD status  C) Continue lenalidomide  D) Refer to transplant → **Heterogeneous** (treatment, testing, continuation, referral — different categories)
- **endpoint_type**: Only for questions about trial endpoints

---

## Special Situations

### AE as Secondary Condition
When question asks about managing an AE (e.g., MDS from therapy):
- Keep the PRIMARY disease being treated as the disease context
- Use topic = "AE management" or "Safety profile"
- DO NOT change disease_state to the AE/complication

### Pan-Tumor Questions
For questions not specific to one disease:
- disease_type: `null`
- disease_stage: `null` (unless clearly stated)
- Focus on the treatment/biomarker being discussed

### Unknown Trial
If a trial is mentioned but you don't recognize it:
- Still tag the trial name as stated
- Tag what you can infer from context
- Use `null` for fields you cannot determine
