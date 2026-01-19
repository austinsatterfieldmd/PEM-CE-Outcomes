# Breast Cancer Tagging Rules

## Overview
Breast cancer requires highly specific subtyping based on hormone receptor (HR) and HER2 status. The LLM must **try very hard** to determine the molecular subtype, as this drives treatment selection and clinical outcomes assessment. Subtype determination is the #1 priority for breast cancer tagging.

---

## Field: disease_state
**Value:** `"Breast cancer"`

**Triggers:**
- "breast cancer", "breast carcinoma"
- "mBC", "MBC" (metastatic breast cancer)
- Any breast cancer subtype: "TNBC", "mTNBC", "HR+/HER2-", "HER2+", "HER2-low", "HER2-ultralow"
- "ductal carcinoma", "lobular carcinoma", "IDC", "ILC"
- "invasive ductal carcinoma", "invasive lobular carcinoma"

---

## Field: disease_stage

**Valid Values:**
- `"Early-stage"` - Stage I, II, or III (non-metastatic)
- `"Metastatic"` - Stage IV or explicitly stated as metastatic

**Decision Tree:**
```
Is the question about metastatic breast cancer?
├─ YES → "Metastatic"
│   └─ Triggers: "mBC", "MBC", "metastatic", "stage IV", "advanced breast cancer"
│
└─ NO → Is it about early-stage disease?
    ├─ YES → "Early-stage"
    │   └─ Triggers: "stage I", "stage II", "stage III", "early breast cancer",
    │                 "resectable", "operable", "non-metastatic", "localized"
    │
    └─ NOT MENTIONED → null
```

**Examples:**
- "A 55-year-old woman with newly diagnosed **metastatic** HER2+ breast cancer" → `"Metastatic"`
- "**Stage II** HR+/HER2- breast cancer patients" → `"Early-stage"`
- "Patients with **stage III** triple-negative breast cancer" → `"Early-stage"`
- "Breast cancer patients" (no stage mentioned) → `null`

**Note:** Stage III is considered "Early-stage" (non-metastatic, curative intent)

---

## Field: disease_type
**CRITICAL PRIORITY: Always try very hard to determine the subtype**

### Subtyping Hierarchy (in order of determination):

#### Step 1: Determine HER2 Status
```
HER2 IHC 3+ OR IHC 2+/ISH+ → HER2-positive (HER2+)
HER2 IHC 1+ OR IHC 2+/ISH- → HER2-low
HER2 IHC 0 with some membrane staining → HER2-ultralow
HER2 IHC 0 OR negative → HER2-negative
```

#### Step 2: If HER2-positive → disease_type: `"HER2+"`
- **DO NOT** also tag biomarker: "HER2" (redundant)
- Regardless of HR status (can be HR+/HER2+ or HR-/HER2+)
- **Rule:** HER2 status takes precedence over HR status

#### Step 3: If HER2-negative, determine HR status:
```
ER+ and/or PR+ → HR+/HER2-
ER- and PR- → Triple-negative (TNBC)
```

#### Step 4: Special HER2-low Category:
- HER2 IHC 1+ or IHC 2+/ISH-
- Can be HR+/HER2-low OR TNBC/HER2-low (usually not specified separately)
- **Distinct from HER2+** - not eligible for traditional HER2-targeted therapy (trastuzumab, pertuzumab)
- Eligible for HER2-low ADCs (trastuzumab deruxtecan)

#### Step 5: HER2-ultralow (Emerging Category):
- HER2 IHC 0 with some membrane staining
- Less common, usually mentioned explicitly in research contexts
- Investigational ADC eligibility

### Valid disease_type Values:

| Value | Definition | Redundant Biomarker |
|-------|------------|---------------------|
| `"HR+/HER2-"` | ER+ and/or PR+, HER2- | HER2 (don't tag) |
| `"HER2+"` or `"HER2-positive"` | HER2 IHC 3+ or 2+/ISH+ | HER2 (don't tag) |
| `"HER2-low"` | HER2 IHC 1+ or 2+/ISH- | None |
| `"HER2-ultralow"` | HER2 IHC 0 with membrane staining | None |
| `"Triple-negative"` or `"TNBC"` | ER-, PR-, HER2- | None |
| `"Invasive ductal carcinoma"` or `"IDC"` | Histology (use if subtype not specified) | None |
| `"Invasive lobular carcinoma"` or `"ILC"` | Histology (use if subtype not specified) | None |
| `null` | If truly not mentioned | N/A |

### Common Patterns & Examples:

**Pattern 1: HER2+ disease**
- Question: "A patient with **HER2-positive metastatic breast cancer**..."
- disease_type: `"HER2+"`
- biomarker: `null` (HER2 is redundant since it's in disease_type)

**Pattern 2: HR+/HER2- disease**
- Question: "Which CDK4/6 inhibitor is approved for **HR+/HER2- advanced breast cancer**?"
- disease_type: `"HR+/HER2-"`
- biomarker: `null`

**Pattern 3: ER+/PR+ (implies HR+/HER2- if HER2 not mentioned)**
- Question: "A patient with **ER+/PR+ breast cancer**..."
- disease_type: `"HR+/HER2-"` (if HER2- is implied or stated)
- biomarker: `null`

**Pattern 4: Triple-negative disease**
- Question: "In patients with **triple-negative breast cancer** (TNBC)..."
- disease_type: `"Triple-negative"`
- biomarker: `null`

**Pattern 5: HER2-low disease**
- Question: "The DESTINY-Breast04 trial evaluated trastuzumab deruxtecan in **HER2-low metastatic breast cancer**"
- disease_type: `"HER2-low"`
- biomarker: `null`

**Pattern 6: Subtype mentioned in answer, not question**
- Question: "What is the preferred second-line treatment for metastatic breast cancer progressing on endocrine therapy?"
- Answer: "Abemaciclib (for HR+/HER2- disease)"
- disease_type: `"HR+/HER2-"` (infer from answer if question context supports it)

**Pattern 7: Biomarker testing question (EXCEPTION to redundancy rule)**
- Question: "Which biomarker should be tested in all newly diagnosed breast cancer patients?"
- Answer: "ER, PR, and HER2"
- topic: `"Biomarker testing"`
- disease_type: `null` (not specific to subtype)
- biomarker: `"HER2"` (OK to tag because question is ABOUT testing)

---

## Field: treatment_line

### For Metastatic Breast Cancer:
| Value | Definition | Triggers |
|-------|------------|----------|
| `"1L"` | First-line metastatic | "first-line", "initial therapy", "treatment-naive metastatic", "newly diagnosed metastatic" |
| `"2L+"` | Second-line or later | "second-line", "third-line", "after progression on", "previously treated", "refractory", "relapsed" |
| `"Maintenance"` | Maintenance therapy | "maintenance", "continuing therapy after induction" |
| `null` | Not specified | |

### For Early-Stage Breast Cancer:
| Value | Definition | Triggers |
|-------|------------|----------|
| `"Adjuvant"` | After surgery | "adjuvant", "postoperative", "after resection", "after mastectomy", "after lumpectomy" |
| `"Neoadjuvant"` | Before surgery | "neoadjuvant", "preoperative", "prior to surgery", "before resection" |
| `"Perioperative"` | Before and after surgery | "perioperative" (rare in breast cancer) |
| `null` | Not specified | |

**Common Patterns:**

- "First-line therapy for **metastatic** HR+/HER2- breast cancer" → `"1L"`
- "After progression on **first-line** CDK4/6 inhibitor" → `"2L+"`
- "**Adjuvant** therapy for early-stage TNBC" → `"Adjuvant"`
- "**Neoadjuvant** chemotherapy for stage III breast cancer" → `"Neoadjuvant"`
- "High-risk early-stage breast cancer receiving **adjuvant** abemaciclib" → `"Adjuvant"`

---

## Field: treatment

### Common Breast Cancer Treatments:

#### HER2+ Breast Cancer:
**Targeted Therapies:**
- `"trastuzumab"` (Herceptin)
- `"pertuzumab"` (Perjeta)
- `"trastuzumab deruxtecan"` or `"T-DXd"` (Enhertu) - ADC
- `"trastuzumab emtansine"` or `"T-DM1"` (Kadcyla) - ADC
- `"neratinib"` (Nerlynx)
- `"tucatinib"` (Tukysa)
- `"lapatinib"` (Tykerb)
- `"margetuximab"` (Margenza)

**Common Combinations:**
- `"trastuzumab + pertuzumab + chemotherapy"` (1L metastatic or neoadjuvant)
- `"trastuzumab + pertuzumab"` (maintenance)
- `"trastuzumab deruxtecan"` (2L+ metastatic)
- `"tucatinib + trastuzumab + capecitabine"` (brain mets)

#### HR+/HER2- Breast Cancer:
**Endocrine Therapy:**
- `"letrozole"` (aromatase inhibitor)
- `"anastrozole"` (aromatase inhibitor)
- `"exemestane"` (aromatase inhibitor)
- `"tamoxifen"` (SERM)
- `"fulvestrant"` (Faslodex - SERD)

**CDK4/6 Inhibitors:**
- `"palbociclib"` (Ibrance)
- `"ribociclib"` (Kisqali)
- `"abemaciclib"` (Verzenio)

**Common Combinations:**
- `"palbociclib + letrozole"` (1L metastatic)
- `"ribociclib + letrozole"` (1L metastatic)
- `"abemaciclib + fulvestrant"` (2L+ metastatic)
- `"abemaciclib"` (adjuvant for high-risk early-stage)
- `"CDK4/6 inhibitor + endocrine therapy"` (when specific drug not mentioned)
- `"CDK4/6 inhibitor + aromatase inhibitor"` (when specific drugs not mentioned)

**Other Targeted Therapies:**
- `"everolimus"` (mTOR inhibitor) - usually with exemestane
- `"alpelisib"` (PI3K inhibitor) - for PIK3CA-mutated
- `"elacestrant"` (oral SERD) - for ESR1-mutated

#### Triple-Negative Breast Cancer (TNBC):
**Immunotherapy:**
- `"pembrolizumab"` (Keytruda)
- `"atezolizumab"` (Tecentriq)

**ADCs:**
- `"sacituzumab govitecan"` (Trodelvy) - TROP2-directed
- `"datopotamab deruxtecan"` (TROP2-directed, investigational)

**PARP Inhibitors (for BRCA-mutated TNBC):**
- `"olaparib"` (Lynparza)
- `"talazoparib"` (Talzenna)

**Common Combinations:**
- `"pembrolizumab + chemotherapy"` (1L metastatic, PD-L1+)
- `"atezolizumab + nab-paclitaxel"` (1L metastatic, PD-L1+)
- `"sacituzumab govitecan"` (2L+ metastatic)

#### Chemotherapy Regimens:
- `"AC"` (doxorubicin + cyclophosphamide)
- `"TC"` (docetaxel + cyclophosphamide)
- `"AC-T"` or `"AC followed by paclitaxel"` (adjuvant)
- `"nab-paclitaxel"` (Abraxane)
- `"paclitaxel"`
- `"docetaxel"`
- `"capecitabine"` (Xeloda)
- `"carboplatin"`
- `"doxorubicin"`

#### Drug Class (when specific agent not mentioned):
- `"CDK4/6 inhibitor"`
- `"aromatase inhibitor"`
- `"PARP inhibitor"`
- `"ADC"` (antibody-drug conjugate)
- `"chemotherapy"` (when no specific regimen mentioned)

---

## Field: biomarker

### When to Tag Biomarker:

**Tag biomarker when:**
1. Question is explicitly about biomarker testing
2. Biomarker is NOT already captured in disease_type
3. Biomarker mentioned for prognostic/predictive context beyond subtype

**DO NOT tag biomarker when:**
- disease_type is `"HER2+"` → Don't tag biomarker: `"HER2"` (redundant)
- disease_type is `"HR+/HER2-"` → Don't tag biomarker: `"HER2"` (redundant)
- disease_type is `"Triple-negative"` → Don't tag biomarker: `"HER2"` (redundant - implied negative)

**EXCEPTION: Biomarker testing questions**
- If topic is `"Biomarker testing"` and question is about HER2 testing → OK to tag biomarker: `"HER2"`

### Valid Biomarker Values:

**Predictive:**
- `"PD-L1"` (for immunotherapy in TNBC)
- `"ESR1"` (for elacestrant eligibility)
- `"PIK3CA"` (for alpelisib eligibility)
- `"BRCA1/2"` (for PARP inhibitors)
- `"TROP2"` (for sacituzumab govitecan - though all TNBC expresses TROP2)

**Prognostic:**
- `"Ki-67"` (proliferation marker)
- `"Oncotype DX"` (21-gene recurrence score)
- `"MammaPrint"` (70-gene signature)

**Testing Methods:**
- `"IHC"` (immunohistochemistry)
- `"FISH"` (fluorescence in situ hybridization)
- `"NGS"` (next-generation sequencing)

**Examples:**

- Question about **HER2 testing methods** → topic: `"Biomarker testing"`, biomarker: `"HER2"` ✓
- **HER2+ breast cancer** treatment question → disease_type: `"HER2+"`, biomarker: `null` ✓
- Question about **PIK3CA testing** for alpelisib → biomarker: `"PIK3CA"` ✓
- Question about **Oncotype DX** for early-stage HR+ disease → biomarker: `"Oncotype DX"` ✓
- **HR+/HER2- breast cancer** CDK4/6 inhibitor question → disease_type: `"HR+/HER2-"`, biomarker: `null` ✓

---

## Field: trial

### Key Breast Cancer Trials:

#### HER2+ Disease:
- `"CLEOPATRA"` - Trastuzumab + pertuzumab + docetaxel (1L metastatic)
- `"DESTINY-Breast03"` - Trastuzumab deruxtecan vs T-DM1 (2L metastatic)
- `"DESTINY-Breast04"` - Trastuzumab deruxtecan in HER2-low
- `"EMILIA"` - T-DM1 vs capecitabine + lapatinib
- `"KATHERINE"` - T-DM1 vs trastuzumab adjuvant (residual disease post-neoadjuvant)
- `"HER2CLIMB"` - Tucatinib + trastuzumab + capecitabine (brain mets)
- `"APHINITY"` - Pertuzumab adjuvant
- `"NALA"` - Neratinib + capecitabine
- `"SOPHIA"` - Margetuximab vs trastuzumab

#### HR+/HER2- Disease:
- `"MONALEESA-2"` - Ribociclib + letrozole (1L)
- `"MONALEESA-3"` - Ribociclib + fulvestrant
- `"MONALEESA-7"` - Ribociclib in premenopausal women
- `"MONARCH-2"` - Abemaciclib + fulvestrant (2L+)
- `"MONARCH-3"` - Abemaciclib + AI (1L)
- `"monarchE"` - Abemaciclib adjuvant (high-risk early-stage)
- `"PALOMA-2"` - Palbociclib + letrozole (1L)
- `"PALOMA-3"` - Palbociclib + fulvestrant (2L+)
- `"EMERALD"` - Elacestrant (ESR1-mutated)
- `"SOLAR-1"` - Alpelisib + fulvestrant (PIK3CA-mutated)

#### Triple-Negative Disease:
- `"KEYNOTE-355"` - Pembrolizumab + chemotherapy (1L, PD-L1+)
- `"IMpassion130"` - Atezolizumab + nab-paclitaxel (1L, PD-L1+)
- `"ASCENT"` - Sacituzumab govitecan (2L+)
- `"TROPiCS-02"` - Datopotamab deruxtecan
- `"OlympiAD"` - Olaparib (BRCA-mutated)
- `"EMBRACA"` - Talazoparib (BRCA-mutated)
- `"KEYNOTE-522"` - Pembrolizumab neoadjuvant

#### Pan-Subtype:
- `"I-SPY 2"` - Neoadjuvant adaptive trial (multiple subtypes)
- `"CREATE-X"` - Capecitabine adjuvant (residual disease after neoadjuvant)

---

## Complete Examples

### Example 1: HER2+ Metastatic, First-Line
**Question:** "What is the preferred first-line treatment for HER2-positive metastatic breast cancer based on the CLEOPATRA trial?"

**Answer:** "Trastuzumab + pertuzumab + docetaxel"

**Tags:**
```json
{
  "topic": "Treatment selection",
  "disease_state": "Breast cancer",
  "disease_stage": "Metastatic",
  "disease_type": "HER2+",
  "treatment_line": "1L",
  "treatment": "trastuzumab + pertuzumab + chemotherapy",
  "biomarker": null,
  "trial": "CLEOPATRA"
}
```

**Rationale:**
- HER2+ in disease_type → Don't tag HER2 as biomarker (redundant)
- Metastatic → treatment_line uses "1L" not "Adjuvant"
- First-line → "1L"

---

### Example 2: HR+/HER2- Metastatic, CDK4/6 Inhibitor
**Question:** "A 62-year-old postmenopausal woman with newly diagnosed HR+/HER2- metastatic breast cancer. Which regimen is most appropriate as initial therapy?"

**Answer:** "Ribociclib + letrozole"

**Tags:**
```json
{
  "topic": "Treatment selection",
  "disease_state": "Breast cancer",
  "disease_stage": "Metastatic",
  "disease_type": "HR+/HER2-",
  "treatment_line": "1L",
  "treatment": "ribociclib + letrozole",
  "biomarker": null,
  "trial": null
}
```

**Rationale:**
- "newly diagnosed metastatic" → treatment_line: "1L"
- HR+/HER2- in disease_type → Don't tag HER2 as biomarker
- No trial mentioned in question → trial: null

---

### Example 3: TNBC, Neoadjuvant
**Question:** "Which chemotherapy regimen demonstrated the highest pathologic complete response (pCR) rates in neoadjuvant treatment of triple-negative breast cancer?"

**Tags:**
```json
{
  "topic": "Clinical efficacy",
  "disease_state": "Breast cancer",
  "disease_stage": "Early-stage",
  "disease_type": "Triple-negative",
  "treatment_line": "Neoadjuvant",
  "treatment": null,
  "biomarker": null,
  "trial": null
}
```

**Rationale:**
- Neoadjuvant → Early-stage disease (before surgery)
- Asking about pCR rates → topic: "Clinical efficacy"
- No specific treatment mentioned → treatment: null
- Question is comparing regimens generically

---

### Example 4: HER2-low, Second-Line
**Question:** "Based on DESTINY-Breast04, what is the role of trastuzumab deruxtecan in HER2-low metastatic breast cancer?"

**Tags:**
```json
{
  "topic": "Clinical efficacy",
  "disease_state": "Breast cancer",
  "disease_stage": "Metastatic",
  "disease_type": "HER2-low",
  "treatment_line": "2L+",
  "treatment": "trastuzumab deruxtecan",
  "biomarker": null,
  "trial": "DESTINY-Breast04"
}
```

**Rationale:**
- HER2-low is distinct from HER2+ (different treatment eligibility)
- DESTINY-Breast04 enrolled 2L+ patients
- Asking about "role" suggests clinical efficacy/evidence

---

### Example 5: Biomarker Testing (EXCEPTION - Can Tag HER2)
**Question:** "Which biomarker tests should be performed on all newly diagnosed invasive breast cancer specimens?"

**Answer:** "ER, PR, and HER2"

**Tags:**
```json
{
  "topic": "Biomarker testing",
  "disease_state": "Breast cancer",
  "disease_stage": null,
  "disease_type": null,
  "treatment_line": null,
  "treatment": null,
  "biomarker": "HER2",
  "trial": null
}
```

**Rationale:**
- Question is explicitly ABOUT biomarker testing → OK to tag HER2 as biomarker
- No specific subtype mentioned → disease_type: null
- Could also accept biomarker: "ER" or biomarker: "PR" depending on answer focus
- Since answer lists all three, HER2 is appropriate (could also use "ER" or "PR")

---

### Example 6: Adjuvant CDK4/6 Inhibitor (High-Risk Early-Stage)
**Question:** "In the monarchE trial, which patients with early-stage HR+/HER2- breast cancer benefited from adjuvant abemaciclib?"

**Tags:**
```json
{
  "topic": "Clinical efficacy",
  "disease_state": "Breast cancer",
  "disease_stage": "Early-stage",
  "disease_type": "HR+/HER2-",
  "treatment_line": "Adjuvant",
  "treatment": "abemaciclib",
  "biomarker": null,
  "trial": "monarchE"
}
```

**Rationale:**
- Early-stage + adjuvant (post-surgery)
- monarchE studied high-risk early-stage disease
- Asking about which patients benefited → Clinical efficacy

---

### Example 7: PIK3CA-mutated HR+/HER2-
**Question:** "Which targeted therapy is approved for HR+/HER2- metastatic breast cancer with PIK3CA mutations?"

**Answer:** "Alpelisib + fulvestrant"

**Tags:**
```json
{
  "topic": "Treatment selection",
  "disease_state": "Breast cancer",
  "disease_stage": "Metastatic",
  "disease_type": "HR+/HER2-",
  "treatment_line": null,
  "treatment": "alpelisib + fulvestrant",
  "biomarker": "PIK3CA",
  "trial": null
}
```

**Rationale:**
- PIK3CA mutation is NOT captured in disease_type → tag as biomarker
- No treatment line mentioned → null
- Question is about targeted therapy for specific mutation

---

## Edge Cases & Clarifications

### Edge Case 1: HR+/HER2+ Disease
- Technically both HR+ and HER2+
- **Rule:** Use disease_type: `"HER2+"` (HER2 status takes precedence)
- **Rationale:** HER2+ drives treatment selection regardless of HR status
- Treatment approach is HER2-directed therapy (not endocrine therapy)

### Edge Case 2: TNBC vs Triple-Negative
- Both are acceptable
- **Preferred:** `"Triple-negative"` (matches canonical naming)
- **Also OK:** `"TNBC"` (widely used abbreviation)
- Be consistent within a dataset

### Edge Case 3: Stage III Breast Cancer
- Technically "locally advanced" but often treated like early-stage
- **Rule:** Use disease_stage: `"Early-stage"`
- **Rationale:** Stage III is non-metastatic and often receives curative-intent therapy (neoadjuvant/adjuvant)
- Stage III patients receive perioperative therapy, not metastatic treatment paradigms

### Edge Case 4: De Novo Metastatic vs Recurrent Metastatic
- Both are "metastatic" for tagging purposes
- **Rule:** disease_stage: `"Metastatic"` for both
- Don't distinguish de novo vs recurrent in tags
- Treatment approach is the same

### Edge Case 5: Maintenance Therapy
- Post-induction therapy continuation
- **Rule:** treatment_line: `"Maintenance"`
- **Example:** Trastuzumab + pertuzumab maintenance after chemotherapy completion in HER2+ mBC

### Edge Case 6: HER2-low in HR+ vs TNBC
- HER2-low can occur in both HR+ and TNBC
- **Rule:** Use disease_type: `"HER2-low"` (don't further specify HR status unless explicitly relevant)
- **Alternative:** If question emphasizes both, could use `"HR+/HER2-low"` but simpler to use `"HER2-low"` alone
- DESTINY-Breast04 included both HR+ and TNBC HER2-low patients

### Edge Case 7: Oncotype DX for Recurrence Risk
- Genomic test used for HR+/HER2- early-stage breast cancer
- **Rule:** Tag biomarker: `"Oncotype DX"` (prognostic test)
- Don't tag HER2 as biomarker (redundant with disease_type)
- Used to guide adjuvant chemotherapy decisions

---

## Summary Checklist for Breast Cancer Tagging

- [ ] **Always try very hard to determine subtype** (HR+/HER2-, HER2+, HER2-low, Triple-negative)
- [ ] **HER2 status first:** Determine HER2+ vs HER2-low vs HER2-negative before considering HR status
- [ ] **Stage:** Early-stage (I-III) vs Metastatic (IV)
- [ ] **Treatment line:** Adjuvant/Neoadjuvant for early-stage, 1L/2L+ for metastatic
- [ ] **Redundancy check:** If disease_type is HER2+ or HR+/HER2-, don't tag HER2 as biomarker (unless question is about testing)
- [ ] **HER2-low distinction:** HER2-low is distinct from HER2+ (different ADC eligibility)
- [ ] **Consider the answer:** Subtype may be revealed in answer even if not in question
- [ ] **Biomarker testing exception:** OK to tag HER2 as biomarker if topic is "Biomarker testing"
