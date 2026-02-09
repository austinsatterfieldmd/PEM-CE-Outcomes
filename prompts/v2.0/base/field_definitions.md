# Field Definitions (66 LLM-Tagged Fields)

You must assign values for all 66 fields below. Use `null` for fields that are not applicable or cannot be determined.

## Value Selection Guidance

**Strict fields** (marked with "Valid values"): Use ONLY the listed values.
- topic, disease_stage, treatment_line, toxicity_organ, toxicity_grade, outcome_context, clinical_benefit, guideline_source, evidence_type, cme_outcome_level, data_response_type, stem_type, lead_in_type, answer_format, answer_length_pattern, distractor_homogeneity

**Open fields with common values** (marked with "Common values"): Prefer the listed values when they apply. If the question contains a value not in the list but you are confident it is correct, you may use that value instead.
- disease_state, disease_type, treatment_1-5, biomarker_1-5, trial_1-5, drug_class_1-3, drug_target_1-3, prior_therapy_1-3, resistance_mechanism, metastatic_site_1-3, symptom_1-3, toxicity_type_1-5, efficacy_endpoint_1-3, disease_specific_factor, comorbidity_1-3

---

## Core Classification (4 fields)

### 1. topic
**REQUIRED** - Every question must have exactly one topic. Never null.

| Topic | Use When... |
|-------|-------------|
| **Treatment selection** | Choosing WHICH drug/regimen to use for a patient (patient vignette + "which therapy") |
| **Treatment indication** | Whether a patient MEETS CRITERIA for a treatment — eligibility, candidacy, indications. "Which patients are candidates?", "Is this patient eligible?" |
| **Clinical efficacy** | Response rates, survival outcomes, clinical trial results, "key findings" |
| **Safety profile** | Knowing WHAT AEs to expect or recognize — awareness, anticipation. "What are the common AEs?", "Which symptoms should you monitor?" |
| **AE management** | What to DO about an AE already occurring — hold drug, dose-reduce, manage. "Patient develops toxicity, what is the next step?" |
| **Biomarker testing** | Molecular testing, companion diagnostics, test interpretation |
| **Mechanism of action** | Drug targets, pathways, MOA |
| **Diagnosis** | Staging, imaging, diagnostic procedures |
| **Prognosis** | Risk stratification, recurrence scores, survival prediction |
| **Study design** | Trial design, patient enrollment criteria, endpoints |
| **Multidisciplinary care** | Team-based care, referrals, care coordination |
| **Shared decision-making** | Patient-provider communication, discussing treatment options with patients, addressing patient concerns/preferences |
| **Disparities in care** | Racial/ethnic disparities, inequities in access/outcomes |
| **Barriers to care** | Obstacles to treatment (cost, access, adherence) |

### 2. disease_stage
**OPTIONAL** - Can be null, but try hard to infer before accepting null.

**For Solid Tumors:**
- `"Early-stage"` - Stage I-III (curative intent)
- `"Early-stage resectable"` - Stage I-III, surgical candidate
- `"Early-stage unresectable"` - Stage III locally advanced, not surgical
- `"Metastatic"` - Stage IV or metastatic disease

**For SCLC:**
- `"Limited-stage"` - Confined to one hemithorax
- `"Extensive-stage"` - Beyond hemithorax

**For Hematologic Malignancies:**
- Use disease-specific staging systems when mentioned:
  - Multiple myeloma: `"R-ISS I"`, `"R-ISS II"`, `"R-ISS III"`
  - Lymphoma: `"Ann Arbor I"`, `"Ann Arbor II"`, `"Ann Arbor III"`, `"Ann Arbor IV"`
  - CLL: `"Rai 0"`, `"Rai I-II"`, `"Rai III-IV"`, `"Binet A"`, `"Binet B"`, `"Binet C"`
- `null` if staging not mentioned (focus on treatment_line instead)

### 3. disease_type
**OPTIONAL** - Specific molecular or histologic subtype if mentioned or inferable.

Examples by disease (see disease-specific module for details):
- Breast: `"HR+/HER2-"`, `"HER2+"`, `"HER2-low"`, `"Triple-negative"`, `"DCIS"`, `"ILC"`
- NSCLC: `"Squamous"`, `"Non-squamous"`, `"Adenocarcinoma"` (molecular markers like EGFR, ALK, KRAS G12C go in biomarker fields)
- CRC: `"MSI-H/dMMR"`, `"MSS"`, `"Left-sided"`, `"Right-sided"` (BRAF V600E, RAS status go in biomarker fields)
- Heme: `"High-risk"`, `"Standard-risk"` (transplant eligibility goes in treatment_eligibility field)

### 4. treatment_line
**OPTIONAL** - Can be null, but try hard to infer before accepting null.

**For Metastatic/Advanced (Solid Tumors):**
- `"1L"` - First-line metastatic
- `"2L+"` - Second-line or later
- `"Maintenance"` - Maintenance therapy

**For Early-Stage:**
- `"Adjuvant"` - After surgery
- `"Neoadjuvant"` - Before surgery
- `"Perioperative"` - Before and after surgery

**For Hematologic:**
- `"Newly diagnosed"` - Untreated, induction
- `"R/R"` - Relapsed/refractory, salvage
- `"Maintenance"` - Ongoing therapy after response
- `"Bridging"` - Pre-CAR-T therapy

---

## Multi-value Fields (15 fields)

### 5-9. treatment_1 through treatment_5
**OPTIONAL** - Only tag fundable drugs of pharmaceutical interest.

**CRITICAL RULES:**
- DO NOT tag: chemotherapy, radiation, surgery, hormonal backbone (fulvestrant, letrozole when combined with fundable drug)
- For combinations with one fundable drug, tag ONLY the fundable drug
- Put each drug in a separate field (treatment_1, treatment_2, etc.)
- Use `null` for unused slots

**Fundable drug categories:**
- Targeted therapies (TKIs, mAbs)
- Antibody-drug conjugates (ADCs)
- Immunotherapies (checkpoint inhibitors, CAR-T, bispecifics)
- Novel agents in clinical trials

### 10-14. biomarker_1 through biomarker_5
**OPTIONAL** - Tag when clinically relevant AND not redundant with disease_type.

**REDUNDANCY RULE:** If biomarker is already captured in disease_type, use null
- Example: If disease_type is "EGFR-mutated", don't also tag biomarker: "EGFR mutation"

**EXCEPTION:** If topic is "Biomarker testing", you MAY tag the biomarker being tested

**Common values (use these when applicable, but may use other values if confident):**
- Predictive: `"PD-L1"`, `"EGFR mutation"`, `"ALK"`, `"HER2"`, `"BRCA1/2"`, `"MSI-H"`, `"TMB"`, `"PIK3CA"`, `"ESR1"`
- Prognostic: `"Ki-67"`, `"Oncotype DX"`, `"MammaPrint"`
- Resistance: `"T790M"`, `"ESR1"`, `"C797S"`

### 15-19. trial_1 through trial_5
**CONDITIONAL** — Tag behavior depends on topic:

**Always tag** when a trial name is **explicitly mentioned** in the question stem or answer choices (any topic).

**Inference ALLOWED** only when topic is:
- "Clinical efficacy" — Infer from drug + indication + efficacy context
- "Study design" — Infer from drug + indication + study methodology context

**Inference NOT ALLOWED** for all other topics (Treatment selection, Treatment indication, AE management, Biomarker testing, Mechanism of action, Patient selection, Supportive care, Monitoring/follow-up). For these topics, use null unless the trial is explicitly named in the stem or answer choices.

---

## Group A: Treatment Metadata (10 fields)

### 20-22. drug_class_1 through drug_class_3
**OPTIONAL** - Therapeutic class of drugs mentioned.

**Common values (use these when applicable, but may use other values if confident):**
`"Monoclonal antibody"`, `"Antibody-drug conjugate (ADC)"`, `"Bispecific antibody"`, `"CAR-T therapy"`, `"Immune checkpoint inhibitor"`, `"CDK4/6 inhibitor"`, `"EGFR TKI"`, `"ALK inhibitor"`, `"ROS1 inhibitor"`, `"KRAS G12C inhibitor"`, `"BRAF inhibitor"`, `"MEK inhibitor"`, `"HER2 TKI"`, `"BTK inhibitor"`, `"BCL-2 inhibitor"`, `"PI3K inhibitor"`, `"AKT inhibitor"`, `"PARP inhibitor"`, `"FLT3 inhibitor"`, `"IDH inhibitor"`, `"JAK inhibitor"`, `"Menin inhibitor"`, `"FGFR inhibitor"`, `"MET inhibitor"`, `"RET inhibitor"`, `"NTRK inhibitor"`, `"Bispecific T-cell engager"`, `"Aromatase inhibitor"`, `"SERD"`, `"IMiD"`, `"Proteasome inhibitor"`, `"Hypomethylating agent"`, `"Targeted cytotoxin"`

### 23-25. drug_target_1 through drug_target_3
**OPTIONAL** - Molecular target of the drug(s) mentioned.

**Common values (use these when applicable, but may use other values if confident):**
`"EGFR"`, `"ALK"`, `"ROS1"`, `"RET"`, `"MET"`, `"NTRK"`, `"KRAS G12C"`, `"BRAF V600E"`, `"HER2"`, `"CDK4/6"`, `"PIK3CA"`, `"AKT"`, `"BRCA1/2"`, `"PD-1"`, `"PD-L1"`, `"CTLA-4"`, `"LAG-3"`, `"CD19"`, `"CD20"`, `"CD38"`, `"BCMA"`, `"GPRC5D"`, `"Trop-2"`, `"FRa"`, `"Nectin-4"`, `"BTK"`, `"BCL-2"`, `"FLT3"`, `"IDH1"`, `"IDH2"`, `"JAK1/2"`, `"Menin-KMT2A"`, `"FGFR"`, `"VEGF/VEGFR"`, `"Androgen receptor"`, `"Estrogen receptor"`

### 26-28. prior_therapy_1 through prior_therapy_3
**OPTIONAL** - Prior treatments mentioned as context for current decision.

**When to tag:**
- Question mentions "after progression on X"
- Question mentions "previously treated with X"
- Prior therapy influences current treatment choice

**Examples:** `"Prior CDK4/6 inhibitor"`, `"Prior platinum"`, `"Prior immunotherapy"`, `"Prior trastuzumab"`

### 29. resistance_mechanism
**OPTIONAL** - Specific resistance mechanism mentioned.

**Common values (use these when applicable, but may use other values if confident):**
`"T790M mutation"`, `"C797S mutation"`, `"MET amplification"`, `"HER2 amplification"`, `"PIK3CA mutation"`, `"PTEN loss"`, `"ESR1 mutation"`, `"ALK resistance mutation"`, `"BTK C481S mutation"`, `"Histologic transformation"`, `"Lineage plasticity"`

---

## Group B: Clinical Context (9 fields)

### 30-32. metastatic_site_1 through metastatic_site_3
**OPTIONAL** - Sites of metastatic disease if mentioned.

**Common values (use these when applicable, but may use other values if confident):**
`"Brain metastases"`, `"CNS metastases"`, `"Leptomeningeal disease"`, `"Bone metastases"`, `"Liver metastases"`, `"Lung metastases"`, `"Lymph node metastases"`, `"Peritoneal carcinomatosis"`, `"Pleural effusion"`, `"Ascites"`, `"Oligometastatic disease"`

### 33-35. symptom_1 through symptom_3
**OPTIONAL** - Clinical symptoms mentioned in vignette.

**Common values (use these when applicable, but may use other values if confident):**
`"Pain"`, `"Bone pain"`, `"Fatigue"`, `"Nausea/vomiting"`, `"Dyspnea"`, `"Cough"`, `"Weight loss"`, `"Diarrhea"`, `"Peripheral neuropathy"`, `"Cognitive impairment"`, `"Febrile neutropenia"`

### 36-37. special_population_1 through special_population_2
**OPTIONAL** - Special patient populations mentioned.

**Valid values:**
`"Pediatric"` (<18 years), `"AYA"` (15-39, adolescent/young adult), `"Young"` (adults <65), `"Transitional"` (65-75), `"Elderly"` (75+), `"Pregnant"`, `"Organ dysfunction - Renal"`, `"Organ dysfunction - Hepatic"`, `"Organ dysfunction - Cardiac"`, `"Poor performance status (ECOG >=2)"`, `"Frail"`, `"Transplant-eligible"`, `"Transplant-ineligible"`, `"CAR-T eligible"`, `"High-risk cytogenetics"`, `"Standard-risk cytogenetics"`, `"Autoimmune disease"`

**Note:** For CNS involvement, use `metastatic_site`: "Brain metastases" or "Leptomeningeal disease" instead.

### 38. performance_status
**OPTIONAL** - ECOG performance status if mentioned.

**Valid values:**
`"ECOG 0"`, `"ECOG 1"`, `"ECOG 0-1"`, `"ECOG 2"`, `"ECOG 3-4"`

**Note:** For fitness categories (Fit/Unfit/Frail), use `fitness_status` in the Patient Characteristics group instead.

---

## Group C: Safety/Toxicity (7 fields)

### 39-43. toxicity_type_1 through toxicity_type_5
**OPTIONAL** - Specific toxicities mentioned.

**Common values (use these when applicable, but may use other values if confident):**
- Immune-related: `"Immune-related colitis"`, `"Immune-related hepatitis"`, `"Immune-related pneumonitis"`, `"Immune-related thyroiditis"`, `"Immune-related myocarditis"`
- Hematologic: `"Neutropenia"`, `"Febrile neutropenia"`, `"Thrombocytopenia"`, `"Anemia"`, `"Pancytopenia"`
- GI: `"Diarrhea"`, `"Nausea/vomiting"`, `"Mucositis/stomatitis"`, `"Hepatotoxicity"`
- Cardiac: `"QT prolongation"`, `"Cardiomyopathy"`, `"Hypertension"`
- Pulmonary: `"Interstitial lung disease (ILD)"`, `"Pneumonitis"`
- Neurologic: `"Peripheral neuropathy"`, `"ICANS"`, `"Neurotoxicity"`
- CAR-T specific: `"Cytokine release syndrome (CRS)"`, `"Tumor lysis syndrome (TLS)"`
- Dermatologic: `"Rash"`, `"Hand-foot syndrome"`

### 44. toxicity_organ
**OPTIONAL** - Organ system affected by toxicity.

**Valid values:**
`"Cardiac"`, `"Pulmonary"`, `"Hepatic"`, `"Renal"`, `"Gastrointestinal"`, `"Dermatologic"`, `"Neurologic"`, `"Ocular"`, `"Hematologic"`, `"Endocrine"`

### 45. toxicity_grade
**OPTIONAL** - Grade of toxicity if mentioned.

**Valid values:**
`"Grade 1"`, `"Grade 2"`, `"Grade 3"`, `"Grade 4"`, `"Grade 5"`, `"Grade 1-2"`, `"Grade >=3"`, `"Any grade"`, `"Serious"`, `"Dose-limiting"`

---

## Group D: Efficacy/Outcomes (5 fields)

### 46-48. efficacy_endpoint_1 through efficacy_endpoint_3
**CONDITIONAL** — Tag ONLY when:
1. Topic is "Clinical efficacy" (always tag the endpoints discussed), OR
2. A specific endpoint (PFS, OS, ORR, etc.) is **explicitly mentioned in the question stem**

Use null when topic is NOT "Clinical efficacy" AND no endpoint is explicitly named in the stem. Do NOT infer endpoints from answer choices or trial knowledge alone.

**Common values (use these when applicable, but may use other values if confident):**
- Survival: `"Overall survival (OS)"`, `"Progression-free survival (PFS)"`, `"Disease-free survival (DFS)"`, `"Event-free survival (EFS)"`, `"Duration of response (DOR)"`
- Response: `"Overall response rate (ORR)"`, `"Complete response rate (CR)"`, `"Pathologic complete response (pCR)"`, `"MRD negativity"`
- Disease control: `"Disease control rate (DCR)"`, `"Clinical benefit rate (CBR)"`
- QoL: `"Health-related quality of life (HRQoL)"`, `"Patient-reported outcomes (PRO)"`

### 49. outcome_context
**OPTIONAL** - Context of the efficacy data.

**Valid values:**
`"Primary endpoint met"`, `"Primary endpoint not met"`, `"Secondary endpoint"`, `"Exploratory endpoint"`, `"Subgroup analysis"`, `"Post-hoc analysis"`, `"Interim analysis"`, `"Final analysis"`, `"Updated analysis"`, `"Long-term follow-up"`

### 50. clinical_benefit
**OPTIONAL** - Nature of the clinical benefit.

**Valid values:**
`"Statistically significant"`, `"Clinically meaningful"`, `"Non-inferior"`, `"Superior"`, `"Trend toward benefit"`, `"No significant difference"`, `"Hazard ratio"`, `"Absolute benefit"`, `"Relative risk reduction"`

---

## Group E: Evidence/Guidelines (3 fields)

### 51-52. guideline_source_1 through guideline_source_2
**CONDITIONAL** - Tag ONLY when a guideline body is **explicitly named** in the question stem or answer choices (e.g., "per NCCN guidelines", "ASCO recommends", "according to ESMO", "IMWG criteria").

Use null (DEFAULT) when no guideline body is explicitly mentioned. Do NOT infer NCCN/ASCO/ESMO from a treatment being "standard of care", "preferred", or "recommended" without naming the source.

**Valid values:**
`"NCCN"`, `"ASCO"`, `"ESMO"`, `"ASH"`, `"ELN"`, `"IMWG"`, `"IWCLL"`, `"FDA label"`, `"EMA label"`, `"ASTRO"`, `"Expert consensus"`

### 53. evidence_type
**OPTIONAL** - Type of evidence discussed.

**Valid values:**
`"Phase 3 RCT"`, `"Phase 2 RCT"`, `"Phase 1/2 trial"`, `"Phase 1 trial"`, `"Single-arm trial"`, `"Real-world evidence"`, `"Retrospective study"`, `"Meta-analysis"`, `"Systematic review"`, `"Guideline recommendation"`

**Note:** Trial phase is captured within evidence_type (e.g., "Phase 3 RCT"). A separate trial_phase field is not needed.

---

## Group F: Question Format/Quality (13 fields)

This section evaluates both the educational level AND the structural quality of the question for internal QA.

### 54. cme_outcome_level
**OPTIONAL** - Moore's level of CME outcome.

**Valid values:**
- `"3 - Knowledge"` - Question tests recall/recognition of information
- `"4 - Competence"` - Question tests application of knowledge to a clinical scenario

**How to determine:**
- **Level 3 (Knowledge):** "What is the mechanism of action of X?", "Which biomarker predicts response to Y?"
- **Level 4 (Competence):** Patient vignette asking "What is the best treatment for this patient?", case-based decision making

### 55. data_response_type
**OPTIONAL** - Type of response the question elicits (content type).

**Valid values:**
- `"Numeric"` - Answer is a specific number (e.g., "What was the ORR?")
- `"Qualitative"` - Answer is descriptive (e.g., "Which best describes the mechanism?")
- `"Comparative"` - Answer compares options (e.g., "Which is preferred?")
- `"Boolean"` - Answer is Yes/No (e.g., "Is X approved for Y?")

### 56. stem_type
**OPTIONAL** - Format of the question stem.

**Valid values:**
- `"Clinical vignette"` - Patient case scenario (tests application)
- `"Direct question"` - Straightforward question without patient context (tests recall)
- `"Incomplete statement"` - "The mechanism of X is..." format

### 57. lead_in_type
**OPTIONAL** - Type of question lead-in.

**Valid values:**
- `"Standard"` - "Which of the following...", "What is the most..."
- `"Negative (EXCEPT/NOT)"` - "All of the following EXCEPT...", "Which is NOT..."
- `"Best answer"` - "What is the BEST...", "most appropriate", "most likely"
- `"True statement"` - "Which statement is TRUE...", "Which is correct..."

### 58. answer_format
**OPTIONAL** - Structure of answer options.

**Valid values:**
- `"Single best"` - Standard single correct answer format
- `"Compound (A+B)"` - "A and B", "Both A and C" as options
- `"All of above"` - "All of the above" is an answer option
- `"None of above"` - "None of the above" is an answer option
- `"True-False"` - True/False format

### 59. answer_length_pattern
**OPTIONAL** - Relative length of answer options. **DEFAULT: "Uniform"**

**CRITICAL: Most questions are Uniform.** Only use "Variable" when there is a dramatically obvious length difference (one option is a brief phrase while another is a full sentence).

**Valid values:**
- `"Uniform"` - **DEFAULT.** All options are roughly similar length. This includes:
  - All short phrases (2-6 words each)
  - All medium phrases (5-10 words each)
  - All sentences (10-20 words each)
  - Minor variation within the same general category
- `"Variable"` - **RARE.** Only when one option is dramatically longer (3x+). Example: one option is 3 words, another is 15+ words.
- `"Correct longest"` - Correct answer is dramatically longer than all distractors (flaw indicator)
- `"Correct shortest"` - Correct answer is dramatically shorter than all distractors (flaw indicator)

**Decision rule: When in doubt, use "Uniform".**

**Examples:**
- **Uniform**: "Myeloma related to Gaucher disease" / "Progressive Gaucher disease" / "Gaucher disease-related osteoporosis" (all 3-5 words) → Uniform
- **Uniform**: Drug names, regimen names, or any set of options that are all in the same general length range → Uniform
- **Variable**: One option is "Pembrolizumab" (1 word) while another is "Combination of platinum-based chemotherapy with maintenance pemetrexed following disease stabilization" (10+ words) → Variable

**Note:** "Correct longest" and "Correct shortest" are testwise cues indicating potential item writing issues - only use when the correct answer stands out dramatically in length.

### 60. distractor_homogeneity
**OPTIONAL** - Whether answer options are structurally interchangeable or substantively different.

**Valid values:**

**"Homogeneous"** — All options are the **same TYPE and similar SPECIFICITY** (interchangeable format, just swapping one entity for another):
- All specific drug names: "Osimertinib" / "Erlotinib" / "Afatinib" / "Gefitinib"
- All regimen names: "Dara-VRd" / "VRd" / "KRd" / "Isa-VRd"
- All biomarkers: "EGFR" / "ALK" / "ROS1" / "KRAS"
- All short clinical phrases of similar scope

**"Heterogeneous"** — Options differ in TYPE, SPECIFICITY, or are **substantively different statements**:
- Mixed categories (drug name vs. dosing schedule vs. monitoring plan)
- Different scope/specificity (brief phrase vs. complex multi-clause statement)
- Substantively different clinical assertions even if sharing a broad theme
- Example: "This patient's age does not exclude transplant" / "Deeper remission will not be possible" / "If deferred, transplant no longer an option" / "Transplant unlikely to prolong TTP" → **Heterogeneous** (different clinical rationales requiring independent evaluation)

**Decision rule:** If options are interchangeable in format (just swapping one entity for another), use "Homogeneous". If each option must be evaluated on its own clinical merits, use "Heterogeneous".

---

### Item Writing Flaws (61-66)

These 6 fields are **boolean** (true/false). Set to `true` if the flaw is present, `false` if not.

### 61. flaw_absolute_terms
**BOOLEAN** - Answer options contain absolute terms.

Set `true` if any answer option contains: "always", "never", "all", "none", "only", "must", "cannot"

**Why it matters:** Test-wise examinees know absolutes are usually wrong.

### 62. flaw_grammatical_cue
**BOOLEAN** - Stem grammar reveals the answer.

Set `true` if:
- Stem ends with "a" or "an" and only one option starts with correct vowel/consonant
- Stem uses singular but some options are plural (or vice versa)
- Subject-verb agreement issues that eliminate options

**Why it matters:** Grammar matching guides to correct answer without content knowledge.

### 63. flaw_implausible_distractor
**BOOLEAN** - Contains obviously wrong options.

Set `true` if any distractor is clearly wrong to anyone with basic clinical knowledge (e.g., "Homeopathy" as treatment option for cancer, a drug from completely wrong class).

**Why it matters:** Reduces effective choices and inflates guessing success.

### 64. flaw_clang_association
**BOOLEAN** - Answer shares unusual words/phrases with stem.

Set `true` if the correct answer contains a distinctive word or phrase that also appears in the stem (word repetition beyond common clinical terms).

**Why it matters:** Word repetition guides to correct answer without actual knowledge.

### 65. flaw_convergence_vulnerability
**BOOLEAN** - Correct answer combines elements from multiple options.

Set `true` if:
- Multiple options share common elements
- The correct answer has the most overlapping elements with other options
- Test-taker could reason to correct answer by finding the "most complete" option

**Why it matters:** Allows reasoning to answer without content knowledge.

### 66. flaw_double_negative
**BOOLEAN** - Negative stem combined with negative option.

Set `true` if:
- Stem contains "NOT", "EXCEPT", "LEAST likely", etc. AND
- One or more answer options contain negative phrasing

**Why it matters:** Increases cognitive load, tests reading comprehension rather than knowledge.
