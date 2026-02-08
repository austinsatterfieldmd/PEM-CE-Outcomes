# Tagging Knowledge Base

This document captures learnings from analysis of tagged questions, user corrections, and prompt improvements.

Last updated: 2026-02-06

---

## Question Tracking: QGD as Source of Truth

**QUESTIONGROUPDESIGNATION (QGD) is the ONLY stable identifier for questions across all systems.**

### Database Mapping
- `source_id` = QGD (the stable key)
- `source_question_id` = internal ID from source system (NOT reliable for matching)

### Key Files and Locations

| File | Location | Purpose |
|------|----------|---------|
| Source file | `data/raw/stage2_ready_fixed_20260129_213111.xlsx` | All questions with QGD |
| Untagged QGDs | `data/raw/untagged_heme_qgds.json` | QGDs still needing tagging |
| Database | `dashboard/data/questions.db` | Uses `source_id` for QGD |
| Checkpoints | `data/checkpoints/stage2_tagged_*.json` | Tagging results with QGD |

### Original Project Data (Backup Location)
`C:\Users\snair\OneDrive - MJH\Documents\GitHub\Steve-V2-Outcomes-Tagger\Automated-CE-Outcomes-Dashboard\`

Contains:
- `data/checkpoints/` - All checkpoint files including heme and myeloma
- `data/corrections/` - User correction JSONL files by disease
- `data/exports/` - Exported tag CSVs
- `data/eval/` - Stage1/Stage2 review files, duplicate validation

---

## Heme Tagging Status (as of 2026-02-06)

| Disease | Total in Source | Tagged | Remaining |
|---------|-----------------|--------|-----------|
| ALL | 132 | 9 | **123** |
| DLBCL | 86 | 10 | **76** |
| CLL | 79 | 10 | **69** |
| FL | 30 | 10 | **20** |
| MCL | 26 | 10 | **16** |
| **TOTAL** | **353** | **49** | **304** |

---

## User Correction Patterns (Heme - excluding Myeloma)

Based on analysis of 50 corrections from `data/corrections/*.jsonl` files.

### Most Corrected Fields

| Field | # Corrections | Pattern |
|-------|---------------|---------|
| treatment_line | 25 | LLMs use "Treatment-naive", user wants "Newly diagnosed" |
| answer_length_pattern | 20 | LLMs say "Variable", often should be "Uniform" |
| distractor_homogeneity | 10 | LLMs default "Homogeneous", often "Heterogeneous" |
| biomarker_1 | 7 | Mixed over/under tagging |
| prior_therapy_1 | 5 | **LLMs UNDER-tag** - missing prior therapy when history mentioned |
| drug_class_1 | 5 | Need more specificity (e.g., "Covalent BTKi" not "BTK inhibitor") |
| disease_type_1 | 5 | LLMs put cytogenetics in disease_type (should be biomarker) |

### Specific Correction Examples

#### treatment_line (25 corrections)
- `"Treatment-naive"` → `"Newly diagnosed"` (standardized value)
- `null` → `"Newly diagnosed"` (LLMs failing to infer)
- `null` → `"R/R"` (LLMs failing to infer)

**Valid values**: "Newly diagnosed", "R/R", "Maintenance"

#### prior_therapy_1 (LLMs UNDER-tag)
- q4825 (ALL): `null` → `"Prior stem cell transplant"`
- q4833 (DLBCL): `null` → `"Prior CIT"`
- q4834 (DLBCL): `null` → `"Prior chemotherapy"`
- q4836 (MCL): `null` → `"Prior BTK inhibitor"`
- q4866 (CLL): `"Prior ibrutinib"` → `"Prior covalent BTKi"` (prefer class over drug)

**Rule**: Always tag prior therapy when patient history mentions prior treatments.

#### drug_class_1 (specificity issues)
- q4844 (CLL): `"BTK inhibitor"` → `"Non-covalent BTKi"`
- q4859 (FL): `"BTK inhibitor"` → `"Non-covalent BTKi"`
- q4841 (FL): `"XPO1 inhibitor"` → `""` (negative lead-in, don't tag)

**Rule**: NEVER use generic "BTK inhibitor" - always specify covalent vs non-covalent.

#### disease_type_1 (CLL cytogenetics misplacement)
- q4848: `"Unmutated IGHV"` → `null` (should be in biomarker)
- q4854: `"del(17p)/TP53-mutated"` → `null` (should be in biomarker)
- q4856: `"del(17p)/TP53-mutated"` → `null` (should be in biomarker)

**Rule**: Cytogenetics (del(17p), TP53, IGHV) go in biomarker_1-5, NOT disease_type.

#### biomarker_1 (mixed issues)
- q4874 (ALL): `"Philadelphia chromosome"` → `null` (over-tagged)
- q4837 (DLBCL): `"CD19"` → `null` (CD19 is drug target, not biomarker)
- q4861 (FL): `null` → `"POD24"` (under-tagged)
- q4873 (FL): `"EZH2 mutation"` → `"EZH2 wildtype"` (wrong value)

#### clinical_benefit (LLMs OVER-tag)
- q4842 (CLL): `"Non-inferior"` → `""` (not the main teaching point)
- q4862 (CLL): `"Superior"` → `""` (not the main teaching point)
- q4863 (CLL): `"Statistically significant"` → `""` (not the main teaching point)

**Rule**: Only tag when comparative efficacy is the main teaching point.

#### treatment_1 (specificity/negative lead-in)
- q4837 (DLBCL): `"CAR-T"` → `"Axicabtagene ciloleucel"` (be specific)
- q4841 (FL): `"Selinexor"` → `null` (negative lead-in - don't tag exception)
- q4864 (FL): `"tisagenlecleucel"` → `"Tisagenlecleucel"` (capitalization)

---

## Prompt Improvements Made

### treatment_line Standardization
- Changed from "Treatment-naive" to "Newly diagnosed"
- Changed from "1L", "2L", "3L+" to "Newly diagnosed", "R/R"
- Valid values: "Newly diagnosed", "R/R", "Maintenance", "Watch-and-wait" (FL only)

### CLL disease_type Rules
- Cytogenetics (del(17p), TP53, IGHV) → biomarker fields, NOT disease_type
- Risk categories (High-risk, CLL-IPI) → disease_type OK

### BTKi Specificity
- NEVER use generic "BTK inhibitor"
- Covalent: ibrutinib, acalabrutinib, zanubrutinib → "Covalent BTKi"
- Non-covalent: pirtobrutinib → "Non-covalent BTKi"

### Negative Lead-In Rules
| Question Type | Correct Answer | What to Tag |
|---------------|----------------|-------------|
| "NOT approved for X" | Unapproved drug | **Nothing** - the exception isn't an X drug |
| "EXCEPT for..." | Exception without benefit | **Tag the distractors** |
| "Which is NOT a mechanism of..." | Wrong mechanism | **Tag the drug**, not the wrong mechanism |

### Prior Therapy Rules
- ALWAYS tag when patient history mentions prior treatments
- Prefer drug CLASS over specific drug (e.g., "Prior covalent BTKi" not "Prior ibrutinib")
- Format: "Prior [regimen]" (e.g., "Prior R-CHOP", "Prior CIT")

---

## Normalization Issues (Still Present)

| Field | Issue | Fix |
|-------|-------|-----|
| toxicity_type_1 | `"Dysgeusia "` (trailing space) | Trim to `"Dysgeusia"` |
| drug_class_1 | `"Non-covalent BTK inhibitor"` (1x) vs `"Non-covalent BTKi"` (7x) | Standardize to `"Non-covalent BTKi"` |
| treatment_line | `"2L"`, `"3L+"` still exist | Standardize to `"R/R"` |
| disease_stage | `"Stage III"` vs `"Ann Arbor III"` | Standardize staging format |

---

## Complete Batch Tagging Workflow

### Step 1: Run Batch Tagging
```powershell
cd "c:\Dev\CE-Outcomes-Dashboard"
python scripts/run_stage2_batch.py --disease "MCL" --limit 16 --input "data/raw/stage2_ready_fixed_20260129_213111.xlsx"
```
- Outputs checkpoint to `data/checkpoints/stage2_tagged_<disease>.json`
- Auto-import attempts but may fail silently

### Step 2: Import to Dashboard Database (Manual - Recommended)
```powershell
cd "c:\Dev\CE-Outcomes-Dashboard\dashboard"
python scripts/import_stage2_results.py --file "../data/checkpoints/stage2_tagged_mcl.json" --upsert
```
- Uses QGD (`source_id`) for upsert: update existing, insert new
- Protects human-reviewed questions (won't overwrite)
- Sets `needs_review=TRUE` for questions with majority/conflict votes

### Step 3: Review in Dashboard
1. Start backend: `python -m uvicorn backend.main:app --reload` (from `dashboard/`)
2. Start frontend: `npm run dev` (from `dashboard/frontend/`)
3. Open dashboard (usually http://localhost:5173)
4. Go to **Review Queue** to see questions needing review
5. Review and correct tags → marks as `edited_by_user=TRUE`

### Step 4: Export for LLM Eval
- Checkpoint files in `data/checkpoints/` contain `field_votes` for LLM accuracy analysis
- Dashboard eval endpoint: `GET /api/eval/metrics` compares LLM tags vs user-corrected tags

### Import Behaviors
| Scenario | Action |
|----------|--------|
| New question (QGD not in DB) | INSERT |
| Existing question (not reviewed) | UPDATE tags |
| Existing question (human-reviewed) | SKIP (protect user edits) |
| Question in exclusion list | SKIP |

---

## Correction Files Reference

Location: `C:\Users\snair\OneDrive - MJH\Documents\GitHub\Steve-V2-Outcomes-Tagger\Automated-CE-Outcomes-Dashboard\data\corrections\`

| File | Records | Description |
|------|---------|-------------|
| `all_corrections.jsonl` | 7 | ALL disease corrections |
| `cll_corrections.jsonl` | 9 | CLL corrections |
| `dlbcl_corrections.jsonl` | 10 | DLBCL corrections |
| `fl_corrections.jsonl` | 12 | FL corrections |
| `mcl_corrections.jsonl` | 12 | MCL corrections |
| `multiple_myeloma_corrections.jsonl` | 168 | MM corrections (already addressed) |

Format: JSONL with `original_tags`, `corrected_tags`, `source_id` (QGD)

---

## LLM Eval System

The LLM Eval dashboard tracks model accuracy by comparing LLM-generated tags with user-verified tags.

### How It Works

1. **Checkpoint files** (`data/checkpoints/stage2_tagged_*.json`) contain:
   - `field_votes`: Original LLM model outputs (GPT, Claude, Gemini votes per field)
   - `final_tags`: User-verified/corrected tags

2. **Accuracy computation**: `final_tags` - `field_votes.final_value` = corrections needed

3. **Metrics tracked**:
   - Overall accuracy (field-level)
   - Per-model accuracy (GPT vs Claude vs Gemini)
   - Agreement level accuracy (unanimous vs majority vs conflict)
   - Field group accuracy (Core, Treatment Metadata, etc.)
   - Top problem fields

### Adding New Batches to LLM Eval

1. **Tag questions** → Outputs to `data/checkpoints/<batch_name>.json`
2. **User reviews** → Corrections saved to `final_tags` in checkpoint file
3. **Add to eval config** in `dashboard/backend/routers/eval.py`:

```python
CHECKPOINT_FILES = [
    "stage2_tagged_multiple_myeloma.json",  # 250 myeloma questions
    "heme_tagged_*.json",                    # Heme batches
    # Add new batches here:
    "stage2_tagged_nsclc.json",
    "stage2_tagged_breast_cancer.json",
]
```

4. **Verify**: `GET /api/eval/checkpoints` shows loaded files

### Checkpoint File Format

```json
{
  "results": [
    {
      "question_id": 123,
      "source_id": "7413",  // QGD - the stable identifier
      "question_stem": "...",
      "correct_answer": "...",
      "disease_state": "Multiple Myeloma",
      "final_tags": { ... },  // User-verified (source of truth)
      "field_votes": {        // Original LLM outputs
        "topic": {
          "final_value": "Treatment selection",
          "agreement": "unanimous",
          "gpt_value": "Treatment selection",
          "claude_value": "Treatment selection",
          "gemini_value": "Treatment selection"
        },
        ...
      },
      "needs_review": false,
      "review_reason": null
    }
  ]
}
```

### API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/eval/metrics` | Full metrics (all batches combined) |
| `GET /api/eval/summary` | Quick summary stats |
| `GET /api/eval/checkpoints` | List loaded checkpoint files |

---

## Key Learnings for LLM Tagging

1. **Be specific**: Use specific drug names (not "CAR-T") and specific drug classes (not "BTK inhibitor")
2. **Check history**: Always tag prior_therapy when patient history is mentioned
3. **Cytogenetics → biomarkers**: del(17p), TP53, IGHV go in biomarker fields, NOT disease_type
4. **Negative lead-ins**: Don't tag the exception in "NOT approved" questions
5. **clinical_benefit sparingly**: Only tag when comparative efficacy is the main teaching point
6. **Standardize values**: Use exact canonical values (e.g., "Newly diagnosed" not "Treatment-naive")
