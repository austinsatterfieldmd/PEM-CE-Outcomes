# [Disease Name] Tagging Rules

## Overview
[Brief description of why this disease requires specific tagging rules. Highlight unique characteristics: complex subtyping, unique staging, special biomarkers, etc.]

---

## Field: disease_state
**Value:** `"[Canonical Disease Name]"`

**Triggers:**
- "[Full disease name]"
- "[Common abbreviation]"
- "[Common variant spellings]"
- "[Disease subtypes that map to this disease]"

---

## Field: disease_stage

**Valid Values:**
[List applicable staging values for this disease]

**Decision Tree:**
```
[Provide decision logic for determining stage]
```

**Examples:**
- "[Example trigger phrase]" → `"[Stage value]"`
- "[Example trigger phrase]" → `"[Stage value]"`

---

## Field: disease_type

**Valid disease_type Values:**

| Value | Definition | Notes |
|-------|------------|-------|
| `"[Subtype 1]"` | [Definition] | [Special notes, e.g., redundant biomarkers] |
| `"[Subtype 2]"` | [Definition] | [Special notes] |
| `null` | If truly not mentioned | N/A |

### Subtyping Hierarchy (if applicable):

**Priority:**
1. [First determination step]
2. [Second determination step]
3. [Third determination step]

### Common Patterns & Examples:

**Pattern 1: [Description]**
- Question: "[Example question text]"
- disease_type: `"[Value]"`
- Notes: [Rationale]

---

## Field: treatment_line

**Valid Values:**

### For [Setting 1] (e.g., Metastatic):
| Value | Definition | Triggers |
|-------|------------|----------|
| `"[Line]"` | [Definition] | "[trigger phrases]" |

### For [Setting 2] (e.g., Early-stage):
| Value | Definition | Triggers |
|-------|------------|----------|
| `"[Line]"` | [Definition] | "[trigger phrases]" |

**Common Patterns:**
- "[Example]" → `"[treatment_line value]"`

---

## Field: treatment

### Common [Disease] Treatments:

#### [Category 1] (e.g., Targeted Therapies):
**[Subcategory]:**
- `"[drug name]"` ([Brand name]) - [Notes]
- `"[drug name]"` ([Brand name]) - [Notes]

**Common Combinations:**
- `"[combination]"` ([Context/Setting])

#### [Category 2]:
[Continue structure]

#### Drug Class (when specific agent not mentioned):
- `"[Drug class]"`

---

## Field: biomarker

### When to Tag Biomarker:

**Tag biomarker when:**
1. [Condition 1]
2. [Condition 2]

**DO NOT tag biomarker when:**
- [Redundancy rule 1]
- [Redundancy rule 2]

### Valid Biomarker Values:

**Predictive:**
- `"[biomarker]"` ([Purpose])

**Prognostic:**
- `"[biomarker]"` ([Purpose])

**Testing Methods:**
- `"[method]"`

**Examples:**
- [Example scenario] → biomarker: `"[value]"` ✓
- [Example scenario] → biomarker: `null` ✓

---

## Field: trial

### Key [Disease] Trials:

#### [Subtype/Setting 1]:
- `"[TRIAL-NAME]"` - [Brief description]
- `"[TRIAL-NAME]"` - [Brief description]

#### [Subtype/Setting 2]:
- `"[TRIAL-NAME]"` - [Brief description]

---

## Complete Examples

### Example 1: [Description]
**Question:** "[Full question text]"

**Answer:** "[Correct answer]"

**Tags:**
```json
{
  "topic": "[Topic]",
  "disease_state": "[Disease Name]",
  "disease_stage": "[Stage or null]",
  "disease_type": "[Type or null]",
  "treatment_line": "[Line or null]",
  "treatment": "[Treatment or null]",
  "biomarker": "[Biomarker or null]",
  "trial": "[Trial or null]"
}
```

**Rationale:**
- [Explain key tagging decisions]
- [Note any redundancy prevention]
- [Clarify ambiguous choices]

---

### Example 2: [Description]
[Continue with more examples covering edge cases]

---

## Edge Cases & Clarifications

### Edge Case 1: [Description]
- [Scenario description]
- **Rule:** [How to handle]
- **Rationale:** [Why]

### Edge Case 2: [Description]
[Continue]

---

## Summary Checklist for [Disease] Tagging

- [ ] [Key rule 1]
- [ ] [Key rule 2]
- [ ] [Redundancy check]
- [ ] [Special consideration]
- [ ] [Consider the answer]
