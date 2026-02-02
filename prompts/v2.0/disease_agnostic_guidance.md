# Disease-Agnostic Tagging Guidance (V2.0)

This document contains tagging rules that apply universally across all disease states. These rules should be included in EVERY disease-specific prompt.

---

## Required vs Optional Tags

| Tag | Required? | Can Infer? | Notes |
|-----|-----------|------------|-------|
| **topic** | **ALWAYS** | N/A | Every question receives a topic tag |
| **disease_state** | ALWAYS (oncology) | N/A | Determined in Stage 1 |
| **disease_stage** | When applicable | **YES** | From trial, drug, or context; null for heme |
| **disease_type** | When applicable | **YES** | From trial, drug, or context |
| **treatment_line** | When applicable | **YES** | From trial, drug, or context |
| **treatment** | When applicable | **YES** | From trial context; only fundable drugs |
| **biomarker** | When applicable | **CAREFUL** | From trial enrollment criteria; avoid false positives |
| **trial** | When mentioned/inferred | **YES** | For Clinical efficacy & Study design topics |

**Key points**:
- Not every question has a treatment. Questions about diagnosis, prognosis, biomarker testing, or MOA may have `treatment: null`.
- Tags can be **inferred** from trial context, drug associations, and clinical knowledge even when not explicitly stated.
- See Section 7 for detailed inference guidance.

---

## 1. TOPIC Tag (REQUIRED)

### Valid Values (13 categories)
| Topic | Description | Use When... |
|-------|-------------|-------------|
| **Treatment selection** | Questions about choosing WHICH drug/therapy to use among options | "What is the preferred treatment?", "Which regimen should be used?" |
| **Treatment indication** | Questions about FDA approval, eligible patients, candidacy criteria | "Approved for...", "Indicated for...", "Which patients are candidates?", "Does X exclude this patient?" |
| **Clinical efficacy** | Questions about trial results, response rates, survival | Trial names mentioned, PFS/OS/ORR discussed, "key findings" |
| **Safety profile** | Questions about knowing WHAT AEs to expect or recognize (awareness) | "What are the common AEs?", "Which symptoms should you ask about?" |
| **AE management** | Questions about what to DO about an AE already occurring (intervention) | Case vignettes with patient symptoms, "develops toxicity", "next step in management" |
| **Prophylaxis** | Questions about PREVENTING toxicities before they occur | "What prophylaxis is needed?", "How to prevent infections?", "Recommended before starting X" |
| **Biomarker testing** | Questions about which tests to order | "What testing is recommended?", "Which biomarker..." |
| **Mechanism of action** | Questions about how drugs work | "Target of...", "MOA of...", "How does X work?" |
| **Diagnosis** | Questions about diagnostic workup, staging | "Initial workup", "Staging evaluation" |
| **Prognosis** | Questions about outcomes, risk stratification | "Expected survival", "Prognostic factors" |
| **Study design** | Questions about trial design, patient populations, endpoints | "Patient population enrolled", "Primary endpoint", "Trial design" |
| **Multidisciplinary care** | Questions about team-based care, referrals, coordination | "Multidisciplinary team", "When to refer", "Care coordination" |
| **Disparities in care** | Questions about inequities in treatment access or outcomes | "Racial disparities", "Socioeconomic factors", "Access to care" |
| **Barriers to care** | Questions about obstacles to receiving optimal treatment | "Barriers to treatment", "Adherence challenges", "Cost barriers" |

### Topic Detection Rules

1. **Trial Names → Clinical efficacy**
   - If question mentions a trial name (KEYNOTE-xxx, DESTINY-xxx, CheckMate-xxx, etc.), default to "Clinical efficacy"
   - Exception: If question asks "What therapy from trial X is recommended?", use "Treatment selection"
   - Pattern: `"key findings from..."`, `"trial showed..."`, `"results of..."` → Clinical efficacy

2. **Case Vignettes → AE management**
   - If question starts with patient scenario (age, gender, symptoms) AND asks what to do about a symptom → "AE management"
   - Pattern: `"A 65-year-old woman on pembrolizumab develops grade 2 pneumonitis..."` → AE management
   - Key phrases: `"develops"`, `"presents with"`, `"what is the next step"`, `"recommended management"`

3. **"What AEs" vs "What to do about AE"**
   - "What are the common adverse events with X?" → **Safety profile** (asking about the profile)
   - "Patient develops AE, what do you do?" → **AE management** (asking how to manage)

4. **MOA Indicators**
   - Strong indicators: `"mechanism of action"`, `"targets"`, `"pathway"`, `"how does X work"`, `"inhibits"`, `"blocks"`
   - Pattern: `"functions by causing..."`, `"receptor signaling pathway"` → MOA

5. **Study Design vs Clinical Efficacy**
   - "What patient population was enrolled?" → **Study design**
   - "What was the primary endpoint?" → **Study design**
   - "What were the results/findings?" → **Clinical efficacy**
   - If question asks about BOTH design AND results, prefer **Clinical efficacy**

6. **Disparities/Barriers Topics**
   - Questions about access issues, socioeconomic factors → **Barriers to care** or **Disparities in care**
   - If specifically about racial/ethnic disparities → **Disparities in care**
   - If about practical obstacles (cost, transportation, etc.) → **Barriers to care**

7. **Treatment selection vs Treatment indication** (CRITICAL DISTINCTION)
   - **Treatment selection** = choosing WHICH drug/regimen to use from among options for a patient
   - **Treatment indication** = whether the patient MEETS CRITERIA for a treatment (eligibility, indications, contraindications, candidacy)
   - Key test: Is the question asking "which drug?" (selection) or "is this patient eligible / does this patient qualify?" (indication)
   - Examples:
     - "Which regimen is most appropriate for this patient?" → **Treatment selection**
     - "Which eligibility criteria for CAR-T cell therapy apply?" → **Treatment indication**
     - "Does this patient's age exclude transplant?" → **Treatment indication**
     - "A man with R/R MM relapsed after 5 prior therapies. Which eligibility criteria for CAR-T?" → **Treatment indication**

8. **Safety profile vs AE management** (CRITICAL DISTINCTION)
   - **Safety profile** = knowing WHAT adverse events to expect or recognize (awareness, anticipation, recognition)
   - **AE management** = what to DO about an AE that has already occurred (hold drug, dose-reduce, administer treatment)
   - Key test: Is the question asking "what might happen?" (safety profile) or "what do you do now that it happened?" (management)
   - Examples:
     - "Which symptoms will you ask about to determine if he is experiencing cardiovascular AEs?" → **Safety profile** (recognizing)
     - "What are common AEs of carfilzomib?" → **Safety profile** (awareness)
     - "Patient develops Grade 3 CRS. What is the recommended management?" → **AE management** (intervention)
     - "Patient on pembrolizumab develops pneumonitis. What is the next step?" → **AE management** (action)
   - NOTE: Questions about racial/population differences in AE rates (e.g., CRS rates in different populations) should be classified based on the educational focus. If the focus is on understanding the safety profile → **Safety profile**, not "Disparities in care."

9. **Prophylaxis vs Safety profile vs AE management** (CRITICAL THREE-WAY DISTINCTION)
   - **Safety profile** = knowing WHAT adverse events to expect (awareness, education, recognition)
   - **Prophylaxis** = knowing HOW TO PREVENT toxicities before they occur (prevention, premedication, mitigation planning)
   - **AE management** = knowing WHAT TO DO after an AE has already occurred (intervention, dose modification, supportive care)

   Key test: What is the educational focus?
   - "What AEs should patients expect?" → **Safety profile** (awareness)
   - "What should be given to prevent AEs before starting therapy?" → **Prophylaxis** (prevention)
   - "Patient has Grade 2 CRS, what do you do?" → **AE management** (intervention)

   Examples:
   - "What prophylaxis is recommended before starting bispecific antibody therapy?" → **Prophylaxis**
   - "A patient starting elranatamab needs IVIg prophylaxis. What is the regimen?" → **Prophylaxis**
   - "Which treatments require antiviral prophylaxis?" → **Prophylaxis**
   - "A patient develops hypogammaglobulinemia on teclistamab. What do you do?" → **AE management** (AE already occurred)

   **Treatment tagging for Prophylaxis questions**: Tag the drug(s) that CAUSE the toxicity requiring prophylaxis, NOT the prophylactic agent itself.
   - Example: Question about IVIg prophylaxis for bispecific-induced infections → treatment_1: "Teclistamab" (or relevant bispecific), NOT "IVIg"
   - The correct answer (the prophylactic agent) is NOT the treatment tag; the drug being managed IS.

   **When NOT to use Prophylaxis** (even if prophylaxis is mentioned):
   - If the question is primarily about care coordination, referrals, or team-based care → **Multidisciplinary care**
   - Example: "You are a research nurse coordinating enrollment for a patient eligible for bispecific antibody therapy. You need to counsel on CRS/ICANS and coordinate early referrals." → **Multidisciplinary care** (focus is on coordination process, not prophylaxis itself)

10. **Default Fallback**
   - If multiple topics could apply, choose the PRIMARY educational focus
   - "Treatment selection" is the most common topic (use when asking about drug choice)
   - When truly ambiguous, prefer: Treatment selection > Clinical efficacy > others

### Topic Examples

```
Q: "What is the first-line treatment for EGFR+ NSCLC?"
Topic: Treatment selection (choosing which drug)

Q: "What did the FLAURA trial show regarding PFS?"
Topic: Clinical efficacy (trial results)

Q: "What are the common adverse events with osimertinib?"
Topic: Safety profile (knowing what AEs to expect)

Q: "A patient develops pneumonitis on osimertinib. What do you do?"
Topic: AE management (acting on AE)

Q: "How does osimertinib inhibit EGFR?"
Topic: Mechanism of action

Q: "Which patients are candidates for pembrolizumab monotherapy?"
Topic: Treatment indication (eligibility criteria)

Q: "A man with R/R MM relapsed after 5 prior therapies. Which eligibility criteria for CAR-T apply?"
Topic: Treatment indication (candidacy, NOT treatment selection)

Q: "Which symptoms should you ask about to detect carfilzomib cardiotoxicity?"
Topic: Safety profile (recognition/awareness, NOT AE management)

Q: "Differences in CRS rates after CAR-T in Black vs White patients relate to..."
Topic: Safety profile (the educational focus is understanding the safety profile, not disparities)

Q: "What prophylaxis is recommended for patients starting bispecific antibody therapy?"
Topic: Prophylaxis (prevention BEFORE toxicity occurs)
Treatment: the bispecific (e.g., teclistamab), NOT the prophylactic agent

Q: "A patient starting elranatamab requires IVIg. What is the recommended regimen?"
Topic: Prophylaxis (prevention)
Treatment: Elranatamab (the drug requiring prophylaxis), NOT IVIg

Q: "Which treatments for MM require antiviral prophylaxis?"
Topic: Prophylaxis (identifying which drugs need preventive measures)

Q: "Patient on teclistamab develops hypogammaglobulinemia and recurrent infections. What do you do?"
Topic: AE management (AE has already occurred, managing it now)
Treatment: Teclistamab

Q: "You are coordinating enrollment for bispecific therapy. You must counsel on CRS/ICANS and arrange referrals."
Topic: Multidisciplinary care (focus is on coordination, NOT prophylaxis itself)
```

---

## 2. TRIAL Tag

### Detection Rules

1. **NCT Numbers (Highest Confidence)**
   - Pattern: `NCT\d{8}` (e.g., NCT03170557)
   - Always extract NCT numbers when present

2. **Known Trial Name Patterns**
   - Format: NAME-NUMBER (e.g., KEYNOTE-189, DESTINY-Breast04, CheckMate-227)
   - Common prefixes: KEYNOTE, CheckMate, DESTINY, FLAURA, DREAMM, LOTIS, TROPION, MONARCH, MONALEESA, PALOMA, IMPASSION, IMBRAVE, EMERALD, EMPOWER, RATIFY, QUAZAR, ASCERTAIN
   - Cooperative group trials: SWOG-xxxx, CALGB-xxxx, ECOG-xxxx (require hyphen + numbers)

3. **False Positive Blocklist - DO NOT Tag These**
   - Phase designations: "Phase 1", "Phase 2", "Phase 3" (study design, not trial name)
   - Performance status: "ECOG PS", "ECOG performance" (not trials)
   - Biomarkers/genes: ROCK2, JAK1, JAK2, CD6, FLT3, IDH1 (gene names, not trials)
   - Day patterns: "Day 28", "Day 100" (timepoints, not trials)
   - Generic words: "benefit", "impact", "outcome", "progress"

4. **Trial Name Extraction Rules**

   **For most topics**: Only tag explicitly mentioned trials
   - DO NOT infer trial names from drugs alone
   - If LLM infers a trial not in the text, REJECT it

   **EXCEPTION - Trial Inference Allowed for Clinical Efficacy & Study Design**:
   When the topic is **Clinical efficacy** or **Study design**, the LLM SHOULD infer the trial name based on:
   - Drug combination + indication + efficacy data mentioned
   - This is valuable because questions often describe trial results without naming the trial

   **Example of allowed inference:**
   ```
   Q: "Which of the following is correct?"
   A: "SG + pembrolizumab has been shown to have superior PFS in a phase 3 trial over pembrolizumab alone in 1L mTNBC"

   Inference: This describes the ASCENT-04 trial
   Trial tag: ASCENT-04
   Topic: Clinical efficacy
   ```

   **When to infer trials:**
   - Topic is Clinical efficacy or Study design
   - Specific drug combination is mentioned
   - Specific indication/population is mentioned
   - Efficacy data (PFS, OS, ORR, etc.) is referenced
   - The LLM has high confidence in the mapping

   **When NOT to infer trials:**
   - Topic is Treatment selection (just asking which drug to use)
   - Only a single drug mentioned without efficacy context
   - Generic statements without specific population/indication

5. **Web Search Trigger (Stage 1 Only)**
   - If disease_state cannot be determined AND a trial name is detected → trigger web search
   - Query: `"{trial_name} oncology clinical trial disease"`
   - Use result to infer disease_state

### Trial Tag Output
- Return the trial name as mentioned in text (preserve capitalization)
- If NCT number and trial name both present, prefer trial name
- Example: `"KEYNOTE-756"` (not "Keynote 756" or "KEYNOTE756")

---

## 3. TREATMENT Tag

### Purpose: Tag Fundable Drugs Only

The treatment tag is designed to identify drugs of interest to **pharmaceutical CME funders**. This means:

**DO NOT tag:**
- Chemotherapy agents (capecitabine, carboplatin, cisplatin, docetaxel, paclitaxel, etoposide, etc.)
- Radiation therapy (WBRT, SBRT, proton therapy, etc.)
- Surgical procedures (resection, lobectomy, mastectomy, etc.)
- Supportive care (antiemetics, growth factors, steroids for non-GVHD, etc.)
- Hormonal backbone therapies when used with a fundable drug (fulvestrant, letrozole, anastrozole)

**DO tag:**
- Targeted therapies (TKIs, mAbs, ADCs, bispecifics)
- Immunotherapies (checkpoint inhibitors, CAR-T)
- Novel agents in clinical trials
- Drugs with active pharmaceutical interest

### Not Every Question Has a Treatment

Many questions legitimately have `treatment: null`:
- Biomarker testing questions ("What testing should be ordered?")
- Diagnostic workup questions
- Prognostic questions
- MOA questions (unless asking about a specific drug's MOA)
- Some clinical efficacy questions (focusing on endpoints, not drugs)

### Detection Priority (Answer > Stem > Trial)

1. **Drugs in Correct Answer (Highest Priority)**
   - Drugs mentioned in the correct answer are almost always the relevant treatment
   - Confidence: 0.95-1.0

2. **Drugs in Question Stem (Second Priority)**
   - Drugs in the stem are often context (what patient is ON)
   - May be PAST treatments (filter these out)
   - Confidence: 0.80-0.85

3. **Trial-Drug Mappings (Third Priority)**
   - If trial name mentioned, look up associated drugs
   - Confidence: 0.75 (lower because inferred, not explicit)

### Past Treatment Filtering

DO NOT tag drugs that are clearly past/prior treatments:
- `"previously treated with..."` → past treatment
- `"after progression on..."` → past treatment
- `"refractory to..."` → past treatment
- `"history of treatment with..."` → past treatment

Tag the CURRENT/recommended treatment, not what failed.

```
Q: "A patient previously treated with osimertinib now has progressive disease. What is the recommended treatment?"
A: "Amivantamab plus chemotherapy"
Treatment: amivantamab (NOT osimertinib, NOT chemotherapy)
```

### Single vs Multiple Treatments

**Typical case: Single treatment**
Most questions have ONE treatment of interest.

**When to tag multiple treatments:**

1. **Case vignette with multiple correct options (A or B)**
   ```
   Q: "What is the appropriate treatment for HER2-low mBC after progression on CDK4/6i?"
   A: "Trastuzumab deruxtecan or sacituzumab govitecan"
   Treatment: trastuzumab deruxtecan; sacituzumab govitecan
   ```

2. **Combination regimen with multiple fundable drugs**
   ```
   Q: "What did the ASCENT-04 trial evaluate?"
   A: "Sacituzumab govitecan plus pembrolizumab"
   Treatment: sacituzumab govitecan; pembrolizumab (both are fundable)

   Q: "What is the VIKTORIA-1 regimen?"
   A: "Gedatolisib plus palbociclib plus fulvestrant"
   Treatment: gedatolisib; palbociclib (fulvestrant is hormonal backbone, not tagged)
   ```

3. **Combination with only ONE fundable drug → tag only the fundable drug**
   ```
   Q: "What is the CAPItello-291 regimen?"
   A: "Capivasertib plus fulvestrant"
   Treatment: capivasertib (fulvestrant is hormonal backbone)

   Q: "What did FLAURA2 evaluate?"
   A: "Osimertinib plus chemotherapy"
   Treatment: osimertinib (chemotherapy not tagged)
   ```

### Drug Class → Specific Drug Expansion

When the question/answer refers to a **drug class** rather than a specific drug, expand to the specific approved drugs in that class for the indication.

**Rule**: Tag all drugs in that class that were approved at the time the question was written (based on activity date or context).

**Examples:**

```
Q: "For early-stage HR+ BC, what adjuvant therapy improves outcomes?"
A: "CDK4/6 inhibitor plus aromatase inhibitor"
Context: Question written when only abemaciclib was approved for adjuvant
Treatment: abemaciclib

Context: Question written after ribociclib also approved for adjuvant
Treatment: abemaciclib; ribociclib
```

```
Q: "For NDMM, what is the preferred induction?"
A: "Anti-CD38 monoclonal antibody-based quadruplet"
Treatment: daratumumab; isatuximab (both are approved anti-CD38 mAbs)
```

```
Q: "What targeted therapy is preferred for ALK+ NSCLC?"
A: "ALK inhibitor"
Treatment: alectinib; brigatinib; lorlatinib (all approved ALK inhibitors)
Note: If context specifies "first-line", may narrow to alectinib and brigatinib
```

### Drug Name Normalization

- Use generic names (not brand names): `"osimertinib"` not `"Tagrisso"`
- Common abbreviations to expand:
  - T-DXd → trastuzumab deruxtecan
  - T-DM1 → trastuzumab emtansine
  - SG → sacituzumab govitecan
  - Dato-DXd → datopotamab deruxtecan

### Multi-Drug Format

When tagging multiple treatments:
- Use semicolon separator: `"drug1; drug2"`
- Do NOT include non-fundable drugs in the list
- Order: Follow clinical convention or alphabetical

```json
{
    "treatment": "trastuzumab deruxtecan; sacituzumab govitecan"
}
```

---

## 4. BIOMARKER Tag

### Answer-Driven Selection

When multiple biomarkers are mentioned, select the one most relevant to the correct answer's treatment:

```
Q: "For EGFR-mutant, PD-L1 high NSCLC, what is the preferred treatment?"
A: "Osimertinib"
Biomarker: EGFR mutation (osimertinib targets EGFR, not PD-L1)
```

### EGFR Mutation Classification Hierarchy

1. **EGFR mutant (classical)** - L858R, exon 19 deletion
   - Most common, standard EGFR TKI-sensitive
   - Treatments: osimertinib, erlotinib, gefitinib

2. **EGFR exon 20 insertion** - Distinct mechanism
   - NOT sensitive to standard EGFR TKIs
   - Treatments: amivantamab, mobocertinib

3. **EGFR atypical mutations** - S768I, L861Q, G719X
   - May respond differently to different TKIs
   - Treatments vary

If the specific EGFR mutation type is not mentioned, use `"EGFR mutation"` (generic).

### HER2 Classification (Context-Dependent)

| Context | Mechanism | Biomarker Tag |
|---------|-----------|---------------|
| Breast cancer | Amplification/overexpression | HER2+ (amplification) |
| Breast cancer (low) | IHC 1+ or IHC 2+/FISH- | HER2-low |
| Gastric cancer | Amplification/overexpression | HER2+ (amplification) |
| NSCLC | Activating mutation | HER2 mutation |

The distinction matters because HER2 mutation in NSCLC is NOT the same as HER2+ in breast cancer.

### Biomarker Redundancy Prevention (Disease-Specific Rule)

See disease-specific prompts for rules on when biomarkers are redundant with disease_type.

Example: If `disease_type` is `"HER2+"`, don't also tag `biomarker: "HER2"` (redundant).

---

## 5. DISEASE STAGE Tag

### Solid Tumors (4 Values)

| Stage | When to Use | Example Patterns |
|-------|-------------|------------------|
| **Early-stage** | Stage I-III, curative intent, resectability not specified | "stage II", "early-stage", "adjuvant" |
| **Early-stage resectable** | Early-stage + surgery performed/planned | "resectable", "post-operative", "R0 resection" |
| **Early-stage unresectable** | Stage III locally advanced, not surgical candidate | "unresectable", "locally advanced", "inoperable" |
| **Metastatic** | Stage IV, distant metastases | "stage IV", "metastatic", "mBC", "mCRC" |

### SCLC (Special Staging - 2 Values)

| Stage | When to Use | Example Patterns |
|-------|-------------|------------------|
| **Limited-stage** | Confined to one hemithorax | "LS-SCLC", "limited-stage", "limited disease" |
| **Extensive-stage** | Spread beyond hemithorax | "ES-SCLC", "extensive-stage", "extensive disease" |

### Hematologic Malignancies → NULL

Hematologic malignancies do NOT have traditional staging.
- `disease_stage` should be `null` for ALL heme malignancies
- "Newly diagnosed" and "R/R" are TREATMENT LINES, not stages
- "High-risk" and "Standard-risk" are DISEASE TYPES, not stages

### Stage-Implying Abbreviations

| Abbreviation | Disease | Implied Stage |
|--------------|---------|---------------|
| mBC, MBC | Breast cancer | Metastatic |
| mCRC | CRC | Metastatic |
| mCRPC | Prostate cancer | Metastatic |
| mHSPC | Prostate cancer | Metastatic |
| nmCRPC | Prostate cancer | Early-stage unresectable |
| LS-SCLC | SCLC | Limited-stage |
| ES-SCLC | SCLC | Extensive-stage |

---

## 6. TREATMENT LINE Tag

### Solid Tumors by Stage

**Metastatic (Numbered Lines):**
| Line | When to Use | Example Patterns |
|------|-------------|------------------|
| **1L** | First-line, treatment-naive, frontline | "first-line", "1L", "frontline", "treatment-naive" |
| **2L+** | Second-line or later, after progression | "second-line", "2L+", "after progression on 1L", "heavily pretreated" |

**Early-Stage:**
| Line | When to Use | Example Patterns |
|------|-------------|------------------|
| **Adjuvant** | After surgery | "adjuvant", "post-operative" |
| **Neoadjuvant** | Before surgery | "neoadjuvant", "pre-operative" |
| **Perioperative** | Spanning pre- and post-surgery | "perioperative" |

### Hematologic Malignancies (Simplified Vocabulary)

| Line | When to Use | Maps From |
|------|-------------|-----------|
| **Newly diagnosed** | Untreated, induction, consolidation | "induction", "de novo", "treatment-naive" |
| **R/R** | Relapsed/refractory, salvage | "relapsed/refractory", "salvage", "after X prior lines" |
| **Maintenance** | Ongoing therapy after response | "maintenance", "continuation" |
| **Bridging** | Pre-CAR-T therapy | "bridging", "bridge to CAR-T" |

### GVHD (Steroid Status)

| Line | When to Use | Example Patterns |
|------|-------------|------------------|
| **Steroid-naive** | First-line, not yet on steroids | "steroid-naive", "first-line GVHD", "initial therapy" |
| **Steroid-refractory** | Failed steroids | "steroid-refractory", "SR-GVHD", "fails to respond to prednisone" |
| **Prophylaxis** | Prevention, not treatment | "GVHD prophylaxis", "prevention of GVHD" |

### Disease Type → Treatment Line Inference

Some disease types already imply treatment line:

| Disease Type | Implied Line | Implied Stage |
|--------------|--------------|---------------|
| Platinum-resistant | 2L+ | Metastatic |
| Platinum-sensitive (relapsed) | 2L+ | Metastatic |
| mHSPC | 1L | Metastatic |

---

## 7. Contextual Inference from Trials, Drugs, and Clinical Context

### Principle: Infer When Confident, But Avoid False Positives

Many tags can be **inferred** from trial names, drug combinations, and clinical context even when not explicitly stated. The LLM should use clinical knowledge to fill in implied values, but must exercise judgment to avoid false positives.

**Golden Rule**: If a trial or drug is strongly associated with a specific setting (stage, line, subtype, biomarker), infer those values. If the association is weak or context-dependent, leave as `null`.

### What Can Be Inferred from Trial Context

When a trial name is mentioned or inferred, the following tags can often be inferred:

| Tag | Can Infer? | Example |
|-----|------------|---------|
| **disease_stage** | YES | ASCENT-04 → Metastatic |
| **disease_type** | YES | ASCENT-04 → Triple-negative |
| **treatment_line** | YES | ASCENT-04 → 1L |
| **biomarker** | SOMETIMES | KEYNOTE-355 → PD-L1+ (but be careful) |
| **treatment** | YES | ASCENT-04 → sacituzumab govitecan; pembrolizumab |

### Trial → Context Inference Examples

**Example 1: ASCENT-04 (TNBC)**
```
Trial: ASCENT-04
Inferred context:
  - disease_stage: "Metastatic"
  - disease_type: "Triple-negative"
  - treatment_line: "1L"
  - biomarker: "PD-L1" (if question mentions PD-L1+ population)
  - treatment: "sacituzumab govitecan; pembrolizumab"
```

**Example 2: PERSEUS (Multiple myeloma)**
```
Trial: PERSEUS
Inferred context:
  - disease_stage: null (heme - no staging)
  - disease_type: "Transplant-eligible"
  - treatment_line: "Newly diagnosed"
  - treatment: "daratumumab; bortezomib; lenalidomide; dexamethasone"
```

**Example 3: DESTINY-Breast04**
```
Trial: DESTINY-Breast04
Inferred context:
  - disease_stage: "Metastatic"
  - disease_type: "HER2-low"
  - treatment_line: "2L+"
  - treatment: "trastuzumab deruxtecan"
```

**Example 4: FLAURA (NSCLC)**
```
Trial: FLAURA
Inferred context:
  - disease_stage: "Metastatic"
  - disease_type: "EGFR-mutated"
  - treatment_line: "1L"
  - biomarker: "EGFR mutation"
  - treatment: "osimertinib"
```

### Drug → Context Inference Examples

Some drugs are so strongly associated with specific contexts that they imply tags:

| Drug | Implied Context |
|------|-----------------|
| osimertinib | EGFR mutation (biomarker), usually 1L metastatic |
| alectinib, lorlatinib | ALK rearrangement (biomarker) |
| sacituzumab govitecan | Often TNBC or HER2-low, usually 2L+ |
| daratumumab, isatuximab | Multiple myeloma |
| ruxolitinib (in GVHD context) | Steroid-refractory |
| PARP inhibitors | BRCA mutation (biomarker) |

### When to Infer vs When to Leave Null

**INFER when:**
- Trial is mentioned and has well-defined patient population
- Drug + indication combination strongly implies setting
- Clinical context makes the inference unambiguous
- The question explicitly or implicitly focuses on that setting

**DO NOT INFER when:**
- Trial enrolled multiple populations (e.g., DESTINY-Breast04 enrolled both HR+ and TNBC HER2-low)
- Drug is used across many settings (e.g., pembrolizumab is used in many cancers and lines)
- Question is asking about the drug's general profile, not a specific setting
- Inference would require assumptions not supported by context

### Biomarker Inference Caution

Biomarker inference requires extra caution:

**Safe to infer:**
- EGFR TKIs → EGFR mutation
- ALK inhibitors → ALK rearrangement
- PARP inhibitors + breast/ovarian → BRCA mutation
- Pembrolizumab + TNBC + 1L → PD-L1+ (KEYNOTE-355 required PD-L1+)

**Do NOT infer:**
- General immunotherapy use → PD-L1+ (many IO trials don't require PD-L1+)
- HER2-directed therapy → HER2+ biomarker (may be captured in disease_type instead)
- Trial mention alone → biomarker (unless biomarker was an enrollment criterion)

### Inference Validation

When inferring, the LLM should:
1. **State confidence**: High confidence for well-defined trials, lower for edge cases
2. **Check for conflicts**: If explicit text contradicts inference, use explicit text
3. **Prefer explicit over inferred**: If stage is stated as "early-stage" but drug implies metastatic, use "early-stage"

### Inference Example Walkthrough

**Question:** "What were the key findings from the PERSEUS trial in multiple myeloma?"

**Step-by-step inference:**
1. Trial: PERSEUS (explicitly mentioned)
2. Disease state: Multiple myeloma (explicitly mentioned)
3. Disease stage: `null` (heme malignancy, no staging)
4. Disease type: `"Transplant-eligible"` (PERSEUS enrolled transplant-eligible NDMM)
5. Treatment line: `"Newly diagnosed"` (PERSEUS was for newly diagnosed patients)
6. Treatment: `"daratumumab"` + others (D-VRd regimen, but only daratumumab is fundable)
7. Biomarker: `null` (no biomarker-selected population)
8. Topic: "Clinical efficacy" (asking about findings)

**Result:**
```json
{
    "topic": "Clinical efficacy",
    "disease_stage": null,
    "disease_type": "Transplant-eligible",
    "treatment_line": "Newly diagnosed",
    "treatment": "daratumumab",
    "biomarker": null,
    "trial": "PERSEUS"
}
```

---

---

## 8. Output Format

Each tag should return:

```json
{
    "topic": "Treatment selection",
    "disease_state": "Breast cancer",
    "disease_stage": "Metastatic",
    "disease_type": "HR+/HER2-",
    "treatment_line": "1L",
    "treatment": "ribociclib",
    "biomarker": null,
    "trial": null
}
```

### Null vs Empty String
- Use `null` when the tag genuinely doesn't apply (e.g., no trial mentioned, no fundable treatment)
- Don't use empty string `""`

### Examples of Valid Null Treatment

```json
// Biomarker testing question - no treatment
{
    "topic": "Biomarker testing",
    "disease_state": "NSCLC",
    "treatment": null
}

// MOA question - treatment may or may not apply
{
    "topic": "Mechanism of action",
    "disease_state": "Breast cancer",
    "treatment": "trastuzumab deruxtecan"  // If asking about specific drug's MOA
}

// Diagnostic question - no treatment
{
    "topic": "Diagnosis",
    "disease_state": "Multiple myeloma",
    "treatment": null
}
```

### Multi-Value Tags

**Treatment** is the only tag that commonly has multiple values:
- Use semicolon separator: `"drug1; drug2"`
- Only include fundable drugs
- Example: `"trastuzumab deruxtecan; sacituzumab govitecan"`

Other tags are typically single value only.

---

## 9. Integration with Disease-Specific Prompts

This disease-agnostic guidance should be combined with disease-specific rules:

1. Include this guidance as the BASE for all prompts
2. Add disease-specific rules that OVERRIDE or EXTEND these rules
3. Disease-specific rules cover:
   - `disease_type` hierarchy (e.g., HER2+ vs HER2-low for breast cancer)
   - Biomarker redundancy (when NOT to tag biomarker)
   - Disease-specific staging nuances
   - Disease-specific treatment lines

Example structure:
```
[Include disease_agnostic_guidance.md]
[Add breast_cancer_specific_rules.md]
[Add few-shot examples for breast cancer]
```
