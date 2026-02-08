# Data Issues Tracker

Questions flagged during manual review that need investigation or correction.

---

## Flagged for Data Issues

| QID | Disease | Review Note | Status |
|-----|---------|-------------|--------|
| Q5015 | ALL | flag for data issue | Open |
| Q5010 | ALL | flag for data issue | Open |
| Q5009 | ALL | flag for data issue | Open |
| Q5004 | ALL | Flag this as a data issue | Open |
| Q5003 | ALL | Flag this question as having a data issue | Open |

---

## Resolved Issues (This Session)

| QID | Disease | Issue | Resolution |
|-----|---------|-------|------------|
| Q4989 | CLL | Compound answer "B or C" - LLMs can't assume option order | Added compound answer handling guidance to all heme prompts |
| Q4986 | CLL | BTK resistance mutation tagged in biomarker | Added rule: resistance mutations → resistance_mechanism, not biomarker |
| Q4985 | CLL | CME level 4 tagged when vignette not required | Added rule: if vignette not required to answer → Level 3 |
| Q4978 | DLBCL | Homogeneous distractors tagged as Variable length | Rule already existed; reinforced in prompts |
| Q4976 | DLBCL | Distractors incorrectly tagged as heterogeneous | Clarified homogeneous = same TYPE of answer |
| Q4966 | DLBCL | Age not being tagged when stated | Added age_group REQUIRED when age stated (prior session) |
| Q4962 | DLBCL | Variable + correct longest should be "Correct longest" | Added preference rule for Correct longest/shortest |
| Q4959 | MCL | CD19 leaked into biomarker | Added rule: drug targets → drug_target, not biomarker |
| Q4958 | MCL | Real-world evidence tagged from incorrect answers | Added rule: tag from correct answer only |
| Q4957 | MCL | Trial overruled despite explicit mention | Added rule: respect question stem |
| Q4953 | MCL | Transplant-ineligibility not tagged | Added guidance: tag when key to question population |
| Q4951 | FL | Answer length tagged as Variable (should be Uniform) | Reinforced homogeneous + uniform rule |
| Q4999 | ALL | BCR-ABL should not be in biomarker | Added rule: BCR-ABL → disease_type (Ph+), not biomarker |
| Q4996 | CLL | Prior ibrutinib instead of Prior covalent BTKi | Added rule: prefer drug CLASS over specific drug |

---

## Rules Added to Prompts (Session 2026-02-08)

### 1. Compound Answer Handling
When correct answer is "B or C" or similar, deduce the actual answer from clinical reasoning - don't assume option order matches original question.

### 2. Field Placement Rules
- **Resistance mutations** (C481S, T315I, BCL-2) → `resistance_mechanism`, NOT biomarker
- **Drug targets** (CD19, CD20, CD22, BCMA) → `drug_target`, NOT biomarker
- **BCR-ABL/Ph+** (as subtype) → `disease_type`, NOT biomarker
- **Cell of origin** (GCB/ABC/Non-GCB) → `disease_type`, NOT biomarker

### 3. Prior Therapy - Prefer CLASS
Use drug class instead of specific drug unless drug is unique in indication:
- `"Prior covalent BTKi"` instead of "Prior ibrutinib"
- `"Prior anti-CD20"` instead of "Prior rituximab"
- Exception: `"Prior Pola-R-CHP"` (unique in 1L DLBCL)

### 4. CME Level 3 vs 4
If vignette NOT required to answer → Level 3 (Knowledge), not Level 4
Test: Could someone answer correctly WITHOUT reading patient details?

### 5. Correct Longest/Shortest Preference
If answer lengths ARE variable AND correct answer is longest → tag "Correct longest" (not just "Variable")

### 6. Treatment Eligibility Standardization
- Use `"Transplant-eligible/ineligible"` (not ASCT/HSCT variants)
- Tag when question asks about specific patient population or trial subgroup

---

## How to Use This File

1. **Add new issues** when found during review (include QID, disease, brief description)
2. **Move to Resolved** when issue is addressed with rule added to prompts
3. **Track Open issues** that need investigation before a fix can be determined
