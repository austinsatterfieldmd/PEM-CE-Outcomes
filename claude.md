# Claude.md

This file provides context and guidelines for Claude Code when working on this project.

## 🚀 New Conversation Checklist

**At the start of each new conversation, remind the user:**

1. **Backend may not be running** - Background processes don't persist across conversations
2. **Check if dashboard is working** - If showing stale data, backend needs restart
3. **User should run backend in their own terminal** (so it persists):
   ```powershell
   cd "c:\Dev\CE-Outcomes-Dashboard\dashboard"
   python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
   ```

---

## Working Style Preferences

### ⚠️ CRITICAL: No Edits Without Explicit Approval

**When the user asks a QUESTION (ends with "?") or makes an investigative statement, DO NOT EDIT FILES.**

Instead:
1. Research/analyze the issue
2. Report findings
3. Propose changes (describe, don't implement)
4. WAIT for explicit user approval like "yes, make those changes" or "go ahead"

**Examples of investigative questions (NO EDITS):**
- "Is there no induction or consolidation around transplant in CLL?" → REPORT findings only
- "What does the ALL prompt show?" → READ and REPORT only
- "Why weren't those treatment lines used?" → EXPLAIN only
- "Are the directions clear enough?" → ANALYZE and REPORT only

**Examples of directive statements (EDITS OK):**
- "Update all heme prompts to match the ALL template"
- "Add the INFERENCE section to FL and MCL"
- "Fix the treatment_line section in DLBCL"

When in doubt, ASK before editing.

### ⚠️ CRITICAL: Commit After Every Change

**After editing prompts, config files, or any file that affects tagging behavior:**

1. **Git add and commit IMMEDIATELY** - Don't wait until the end
2. **Verify with `git diff`** before moving to next task
3. **Never mark a task "complete" without a commit**

```bash
# After EVERY prompt/config change
git add <file>
git commit -m "fix: <description>"
git log --oneline -1  # Verify commit exists
```

**Why this matters:**
- Session context can be lost at any time
- Uncommitted changes are invisible to future sessions
- A commit is the ONLY durable record of work done

**See also:** [docs/runbooks/tagging-workflow.md](docs/runbooks/tagging-workflow.md)

---

## Service Management

**Claude CAN and SHOULD restart backend services when needed.** This includes:

- Restarting the dashboard backend when database changes aren't reflected
- Starting services that have stopped
- Checking service health via API endpoints

### Restart Backend Command
```bash
cd "c:\Dev\CE-Outcomes-Dashboard\dashboard" && python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Run with `run_in_background: true` to keep it running.

### ⚠️ CRITICAL: Clear Port Before Restart

**Before restarting the backend, ALWAYS verify port 8000 is clear:**

```powershell
# Check if port 8000 is in use
netstat -ano | findstr ":8000" | findstr "LISTENING"

# If a process is found, kill it (replace PID with actual number)
powershell -Command "Stop-Process -Id <PID> -Force"

# Verify port is clear (should return nothing)
netstat -ano | findstr ":8000" | findstr "LISTENING"
```

**Why this matters:**
- Old Python processes can persist after failed restarts
- Multiple processes on same port causes "[WinError 10048]" binding errors
- New server starts but old server may still be receiving requests
- This can cause data inconsistency (writes go to wrong process)

**Do NOT consider a backend restart complete until:**
1. Port 8000 is confirmed clear (netstat shows nothing)
2. New uvicorn process is started
3. Health check returns expected data

### Verify Backend Health
```bash
curl -s "http://127.0.0.1:8000/health"
```

Expected response includes `total_questions` matching the database count.

---

## Review Queue Logic

**User-edited questions (`edited_by_user=1`) are NEVER shown in the review queue**, regardless of the `needs_review` flag. This is enforced at the database query level.

### Key Fields
- `edited_by_user` - Set to 1 when user clicks "Save & Mark Reviewed"
- `needs_review` - Set to 1 when tagging has conflicts/majority votes
- `tag_status` - 'verified', 'unanimous', 'majority', 'conflict'

### Bug Fix (Feb 6, 2026)
The database queries in [database.py](dashboard/backend/services/database.py) now explicitly exclude `edited_by_user=1` from needs_review filters. This prevents user-reviewed questions from reappearing in the queue even if `needs_review` wasn't properly cleared.

### Session Logs
Detailed session logs are saved in `docs/SESSION_LOG_YYYY-MM-DD.md` for audit trail.

### Review Notes

When the user says **"pull my review notes"**, query the `review_notes` column in the `tags` table:

```sql
SELECT q.source_id, t.disease_state, t.review_notes, t.review_reason
FROM tags t
JOIN questions q ON t.question_id = q.id
WHERE t.review_notes IS NOT NULL AND t.review_notes != ''
ORDER BY q.source_id DESC
LIMIT 10
```

- **Location:** `tags.review_notes` column in `dashboard/data/questions.db`
- **Written by:** User via the dashboard review UI ("Save & Mark Reviewed" with notes)
- **Purpose:** User observations about tagging quality, prompt gaps, and action items
- **Ordering:** Use `q.source_id DESC` as proxy for most recent (no updated_at timestamp)
- **Action:** Compile notes into actionable prompt/config improvements

---

## ⚠️ CRITICAL: Database Queries Must Match Dashboard View

**When querying the database, ALWAYS use the same filters as the dashboard** to avoid confusion between what Claude sees and what the user sees.

### Dashboard View Filter (Canonical Questions Only)
The dashboard only shows **canonical questions** - it excludes duplicates. Always include this filter:

```sql
WHERE (q.canonical_source_id IS NULL OR q.canonical_source_id = CAST(q.source_id AS TEXT))
```

### Example: Correct Way to Query Tag Values
```python
# CORRECT - matches dashboard view
cursor.execute('''
    SELECT t.treatment_line, COUNT(*) as cnt
    FROM tags t
    JOIN questions q ON t.question_id = q.id
    WHERE t.treatment_line IS NOT NULL
    AND (q.canonical_source_id IS NULL OR q.canonical_source_id = CAST(q.source_id AS TEXT))
    GROUP BY t.treatment_line
''')

# WRONG - includes duplicates, won't match dashboard
cursor.execute('''
    SELECT t.treatment_line, COUNT(*) FROM tags t GROUP BY t.treatment_line
''')
```

### Why This Matters
- Raw DB queries include ALL records (including duplicates)
- Dashboard filters to canonical questions only
- This caused confusion where Claude reported 6 questions but user only saw 1
- Always verify counts match what user sees in dashboard

---

## ⚠️ CRITICAL: Performance Score Calculations

**The raw data columns are NOT percentages - they are counts!**

### Column Definitions

| Column | Meaning |
|--------|---------|
| `PRESCORECALC` | Number of **correct** responses on pre-test |
| `PRESCOREN` | **Total** number of responses on pre-test |
| `POSTSCORECALC` | Number of **correct** responses on post-test |
| `POSTSCOREN` | **Total** number of responses on post-test |

### How to Calculate Percentages

```python
# CORRECT formula
pre_pct = (PRESCORECALC / PRESCOREN) * 100
post_pct = (POSTSCORECALC / POSTSCOREN) * 100
change = post_pct - pre_pct  # in percentage points (pp)

# For aggregated data (multiple rows):
pre_pct = (sum(PRESCORECALC) / sum(PRESCOREN)) * 100
post_pct = (sum(POSTSCORECALC) / sum(POSTSCOREN)) * 100
```

### Common Mistakes to Avoid

❌ **WRONG**: Treating `PRESCORECALC` as a percentage directly
❌ **WRONG**: Using weighted average of percentages (pre_pct * n / sum(n))
❌ **WRONG**: Dividing by count of rows instead of sum of N

✅ **CORRECT**: Sum all correct responses, divide by sum of all responses

### Example

```
Row 1: PRESCORECALC=7, PRESCOREN=10 (70% correct)
Row 2: PRESCORECALC=3, PRESCOREN=10 (30% correct)

WRONG: Average of 70% and 30% = 50%
CORRECT: (7+3)/(10+10) = 10/20 = 50% ✓ (same here, but not always!)

Row 1: PRESCORECALC=7, PRESCOREN=10 (70% correct)
Row 2: PRESCORECALC=30, PRESCOREN=100 (30% correct)

WRONG: Average of 70% and 30% = 50%
CORRECT: (7+30)/(10+100) = 37/110 = 33.6% ✓ (weighted by sample size!)
```

### Data Source Files

- **Raw Excel**: `data/raw/MyelomaDataTable_*.xlsx` - Contains per-row performance data
- **SCORINGGROUP column**: Identifies audience (Overall, MedicalOncology, NP/PA, NursingOncology, etc.)
- **TREATMENT_LINE column**: Newly diagnosed, R/R, Maintenance
- **DRUG_CLASS_1/2/3 columns**: Drug class tags (may need to check all 3)

---

## ⚠️ CRITICAL: Tagging Workflow Rules

**NEVER re-tag questions that already have tags in the database.**

### Before ANY Tagging Operation:

1. **QUERY THE DATABASE FIRST** to identify which questions are UNTAGGED:
   ```sql
   -- Find untagged questions for a disease
   SELECT q.id, q.qgd
   FROM questions q
   LEFT JOIN tags t ON q.id = t.question_id
   WHERE q.disease_state = 'Multiple Myeloma'
   AND t.id IS NULL;
   ```

2. **REPORT the count** of untagged questions to the user BEFORE proceeding

3. **Only tag questions that have NO existing tags** (LEFT JOIN...IS NULL)

### What "Tag Questions" Means:
- User says "tag the remaining questions" → Find UNTAGGED questions, run Stage 2 tagging on them
- User says "import tagged questions" → Import from checkpoint files (rare, only after fresh tagging)

### Checkpoint Files:
- Located in `data/checkpoints/stage2_tagged_*.json`
- These contain PREVIOUSLY TAGGED results
- **NEVER import checkpoint files** without verifying they contain NEW tagging results
- If checkpoint files exist from a previous session, they are STALE - do not use them

### The Import Script Protection:
- `import_stage2_results.py --upsert` protects questions with `edited_by_user=TRUE`
- But it will OVERWRITE questions that were tagged but not yet human-reviewed
- This is why we NEVER re-tag - even "protected" imports can cause data loss

### Recovery:
- If tags are accidentally overwritten, check git history for database backups
- The `edited_by_user` flag is the ONLY protection - ensure human-reviewed questions have this set

### Automatic Exclusion (Script Protection)

The `run_stage2_batch.py` script **automatically excludes** questions already in `dashboard/data/questions.db` via the `--exclude-db` flag (enabled by default).

**Expected output when running tagging:**
```
Found 367 existing questions in dashboard database
Filtered to 26 MCL questions
Excluding 18 questions that already exist in dashboard database
Remaining: 8 new questions to tag
```

**If you see 0 exclusions but know questions exist:**
1. Check `dashboard/data/questions.db` exists
2. Verify running from correct directory
3. Run: `python -c "import sqlite3; print(sqlite3.connect('dashboard/data/questions.db').execute('SELECT COUNT(*) FROM questions').fetchone()[0])"`

**To force re-tagging (DANGEROUS - wastes money):**
```bash
python scripts/run_stage2_batch.py --disease "MCL" --no-exclude-db
```

---

**TERMINAL COMMANDS**: When asking the user to run commands in their terminal:
1. ALWAYS provide full absolute paths - never use relative paths
2. Use PowerShell-compatible syntax: use `;` for command chaining (NOT `&&` which is Bash-only)
3. Quote paths containing spaces with double quotes

Examples:
- Good: `cd "c:\Users\snair\OneDrive - MJH\Documents\GitHub\Steve-V2-Outcomes-Tagger\Automated-CE-Outcomes-Dashboard\dashboard\frontend"; npm run dev`
- Bad: `cd dashboard/frontend && npm run dev` (relative path AND wrong separator)

## Project Overview

This is an Automated CE Outcomes Dashboard and Tagging System designed to process and analyze continuing education (CE) outcomes data using AI-powered multi-model tagging with a two-stage disease-specific architecture.

## Tagging Architecture: V2.0 Two-Stage System

### Stage 1: Disease Classification (3-Model Voting)
- **3-model parallel voting** (GPT-5.2, Claude Opus 4.5, Gemini 2.5 Pro)
- Lightweight prompt (~1K tokens)
- Returns: `is_oncology`, `disease_state`, `needs_review`, `review_reason`
- **Web search fallback**: Triggered on ANY disagreement (majority or conflict) for trial-based disease lookup
- **Cost**: ~$0.01 per question

### Stage 2: Disease-Specific Tagging (3-Model Voting)
- **3-model parallel voting** (GPT-4o + Claude Sonnet 3.5 + Gemini Pro)
- Disease-specific prompt loaded based on Stage 1 result
- Focused prompts (~3-4K tokens) with disease-specific rules
- Returns: **66 tag fields** organized in 6 groups (see Field Schema below)
- **Web search fallback**: Triggered on ANY disagreement for factual fields
- **Cost**: ~$0.13 per question

### Deduplication (Pre-Tagging)
- **Embedding model**: OpenAI text-embedding-3-small (1536 dimensions)
- **Similarity threshold**: 95% cosine similarity
- **Quality-based canonical selection**: Best version chosen (encoding, completeness, grammar)
- **Cost**: ~$0.00001 per question (negligible)

### Total Pipeline Cost

| Scenario | Cost | Notes |
|----------|------|-------|
| Duplicate question | ~$0.00001 | Dedup only, skip tagging |
| New non-oncology | ~$0.01 | Dedup + Stage 1, skip Stage 2 |
| New oncology | ~$0.14 | Dedup + Stage 1 + Stage 2 (66 fields) |

## Field Schema (66 LLM-Tagged + 2 Computed)

### Core Fields (19)
- `topic` - Educational focus (10 canonical values)
- `disease_stage` - Early-stage, Metastatic
- `disease_type` - Molecular/receptor subtype
- `treatment_line` - 1L, 2L+, Adjuvant, R/R
- `treatment_1-5` - Drug/regimen names (5 slots)
- `biomarker_1-5` - Tested markers (5 slots)
- `trial_1-5` - Clinical trial names (5 slots)

### Group A: Treatment Metadata (10)
- `drug_class_1-3` - Drug class (EGFR TKI, Anti-PD-1, etc.)
- `drug_target_1-3` - Molecular target (EGFR, HER2, PD-1, etc.)
- `prior_therapy_1-3` - Prior treatments
- `resistance_mechanism` - Resistance type

### Group B: Clinical Context (9)
- `metastatic_site_1-3` - Brain, Liver, Bone metastases
- `symptom_1-3` - Pain, Dyspnea, Fatigue
- `special_population_1-2` - Elderly, Frail, Organ dysfunction
- `performance_status` - ECOG 0-4, Fit/Unfit/Frail

### Group C: Safety/Toxicity (7)
- `toxicity_type_1-5` - Specific adverse events
- `toxicity_organ` - Affected organ system
- `toxicity_grade` - CTCAE grade

### Group D: Efficacy/Outcomes (5)
- `efficacy_endpoint_1-3` - OS, PFS, ORR, etc.
- `outcome_context` - Primary/Secondary endpoint, Subgroup analysis
- `clinical_benefit` - Statistically significant, Superior, etc.

### Group E: Evidence/Guidelines (3)
- `guideline_source_1-2` - NCCN, ASCO, ESMO
- `evidence_type` - Phase 3 RCT, Real-world evidence

### Group F: Question Format/Quality (13)
- `cme_outcome_level` - 3 - Knowledge, 4 - Competence
- `data_response_type` - Numeric, Qualitative, Comparative, Boolean
- `stem_type` - Clinical vignette, Direct question, Incomplete statement
- `lead_in_type` - Standard, Negative (EXCEPT/NOT), Best answer
- `answer_format` - Single best, Compound (A+B), All of above
- `answer_length_pattern` - Uniform, Variable, Correct longest
- `distractor_homogeneity` - Homogeneous, Heterogeneous
- `flaw_absolute_terms` - Boolean (true/false)
- `flaw_grammatical_cue` - Boolean
- `flaw_implausible_distractor` - Boolean
- `flaw_clang_association` - Boolean
- `flaw_convergence_vulnerability` - Boolean
- `flaw_double_negative` - Boolean

### Computed Fields (2) - Derived from raw data
- `answer_option_count` - 2-5 (count of answer options)
- `correct_answer_position` - A, B, C, D, E

## Voting & Review Logic

### Agreement Levels

| Level | Pattern | Behavior |
|-------|---------|----------|
| **Unanimous** | 3/3 agree | Auto-accept, no review needed |
| **Majority** | 2/3 agree | Accept majority value, FLAG FOR REVIEW |
| **Conflict** | 1/1/1 | NO auto-assignment, FLAG FOR REVIEW |

### Key Principles
1. **Never auto-resolve conflicts**: All 3 votes are preserved for LLM evaluation
2. **Majority votes flagged**: Even 2/1 agreement goes to review queue (for LLM eval)
3. **Web search on disagreement**: Both majority AND conflict trigger web search
4. **Preserve dissenting votes**: Know which model disagreed and what it said

### Review Reason Values

| Stage | Reason | Meaning |
|-------|--------|---------|
| Stage 1 | `oncology_conflict` | 3-way split on is_oncology |
| Stage 1 | `oncology_majority` | 2/1 split on is_oncology |
| Stage 1 | `disease_conflict` | 3-way split on disease_state |
| Stage 1 | `disease_majority` | 2/1 split on disease_state |
| Stage 1 | `conflict_resolved_by_web_search` | Web search broke a tie |
| Stage 2 | `conflict_in_fields:X,Y` | Conflict in specific fields |
| Stage 2 | `majority_in_fields:X,Y` | Majority vote in specific fields |
| Both | `*\|web_search_used` | Appended when web search was performed |

## Project Structure

```
src/
├── api/                          # FastAPI REST endpoints
│   ├── routers/                  # API route handlers
│   └── schemas.py                # Pydantic models
├── core/
│   ├── taggers/                  # Multi-model tagging system
│   │   ├── openrouter_client.py  # Unified LLM client (GPT, Claude, Gemini)
│   │   ├── disease_classifier.py # Stage 1: Disease classification (3-model voting)
│   │   ├── multi_model_tagger.py # Two-stage orchestration + voting
│   │   └── vote_aggregator.py    # 3-model consensus logic + review flagging
│   ├── services/
│   │   ├── disease_prompt_manager.py # Disease-specific prompt loader
│   │   └── prompt_manager.py     # Prompt version management
│   ├── knowledge/                # Domain knowledge
│   │   ├── constants.py          # Disease states, abbreviations
│   │   └── topic_constants.py    # Topic keywords
│   └── preprocessing/            # Data preprocessing
├── deduplication/                # Question deduplication
│   ├── embeddings.py             # OpenAI embedding generation
│   └── cleanup.py                # Text encoding cleanup
├── workflows/                    # Workflow orchestration
└── __init__.py

prompts/
├── v1.0/                         # Legacy single-stage prompts
│   ├── system_prompt.txt
│   └── few_shot_examples.json
└── v2.0/                         # Two-stage prompts (current)
    ├── disease_classifier_prompt.txt        # Stage 1 prompt
    ├── fallback_prompt.txt                  # Generic fallback
    ├── disease_rules/                       # Human-readable docs
    │   ├── breast_cancer.md                 # ✓ Complete
    │   ├── nsclc.md                         # TODO
    │   ├── multiple_myeloma.md              # TODO
    │   └── ...
    ├── disease_prompts/                     # LLM-ready prompts
    │   ├── breast_cancer_prompt.txt         # ✓ Complete
    │   └── ...
    └── templates/
        └── disease_rule_template.md         # Template for new diseases

knowledge_base/
└── oncology_entities.json        # Canonical diseases, treatments, biomarkers, trials

tests/
├── conftest.py                   # Shared fixtures
├── test_disease_classifier.py    # Stage 1 tests
├── test_disease_prompt_manager.py # Prompt loading tests
└── test_multi_model_tagger.py    # End-to-end tests

config/
├── config.yaml                   # Main configuration
├── models.yaml                   # LLM model configs
└── logging.yaml                  # Logging config

scripts/
├── run_deduplication.py          # Batch deduplication script
└── run_stage1_classification.py  # Stage 1 classification script
```

## Key Data Structures

### Stage 1 Response (DiseaseClassifier)
```python
{
    "is_oncology": True/False/None,  # None = conflict, needs review
    "disease_state": "Breast cancer",  # or None if conflict/undetermined
    "needs_review": True/False,
    "review_reason": "disease_majority",
    "voting_details": {
        "gpt": {"is_oncology": True, "disease_state": "Breast cancer"},
        "claude": {"is_oncology": True, "disease_state": "Breast cancer"},
        "gemini": {"is_oncology": True, "disease_state": "NSCLC"},
        "web_search": {"disease_state": "Breast cancer", "source": "trial_lookup"},
        "agreement": "majority",
        "oncology_agreement": "unanimous",
        "disease_agreement": "majority"
    }
}
```

### Stage 2 Response (AggregatedVote)
```python
AggregatedVote(
    question_id=123,
    overall_agreement=AgreementLevel.MAJORITY,
    overall_confidence=0.67,
    needs_review=True,
    review_reason="majority_in_fields:treatment,biomarker|web_search_used",
    # Individual model responses (preserved for LLM eval)
    gpt_tags={...},
    claude_tags={...},
    gemini_tags={...},
    # Final aggregated result
    final_tags={
        "topic": "Treatment selection",
        "disease_state": "Breast cancer",
        "disease_type": "HER2+",
        ...
    },
    # Per-field voting details
    tags={
        "treatment": TagVote(
            final_value="trastuzumab",
            agreement_level=AgreementLevel.MAJORITY,
            gpt_value="trastuzumab",
            claude_value="trastuzumab",
            gemini_value="pertuzumab",
            dissenting_model="gemini"
        ),
        ...
    },
    web_searches_used=[...]
)
```

## Key Components

### Disease-Specific Rules (Priority Diseases)

**Completed (66-field prompts):**
1. ✓ **Breast cancer** - Complex subtyping (HR+/HER2-, HER2+, HER2-low, TNBC)
2. ✓ **NSCLC** - Molecular subtypes (EGFR, ALK, ROS1, KRAS G12C, etc.)
3. ✓ **Multiple Myeloma** - No staging, R/R vs newly diagnosed
4. ✓ **CRC** - MSI-H, biomarker testing emphasis

**TODO:**
5. **SCLC** - Unique staging (Limited/Extensive)
6. **Prostate cancer** - Castration status
7. **Ovarian cancer** - BRCA, HRD, platinum resistance

### Breast Cancer Rules (Example)

**Critical subtyping hierarchy:**
1. Determine HER2 status: HER2+ > HER2-low > HER2-negative
2. If HER2+, use that as `disease_type` (takes precedence over HR status)
3. If HER2-negative, determine HR: HR+ → "HR+/HER2-", HR- → "Triple-negative"

**Redundancy prevention:**
- If `disease_type` is "HER2+", DON'T tag `biomarker`: "HER2" (redundant)
- Exception: Biomarker testing questions (topic is "Biomarker testing")

**Staging:**
- Early-stage: Stage I-III (includes Stage III locally advanced)
- Metastatic: Stage IV

**Treatment lines:**
- Early-stage: Adjuvant, Neoadjuvant, Perioperative
- Metastatic: 1L, 2L+, Maintenance

## Development Guidelines

### Adding a New Disease

1. **Create rule documentation:**
   ```bash
   cp prompts/v2.0/templates/disease_rule_template.md prompts/v2.0/disease_rules/your_disease.md
   ```

2. **Fill in disease-specific sections:**
   - disease_state triggers
   - disease_stage rules (disease-specific staging)
   - disease_type hierarchy (subtyping priority)
   - treatment_line rules (metastatic vs early-stage vs hematologic)
   - Common treatments by subtype
   - Biomarker redundancy rules
   - Key trials
   - Complete examples with rationale
   - Edge cases

3. **Convert to LLM prompt:**
   - Create `prompts/v2.0/disease_prompts/your_disease_prompt.txt`
   - Structured format for LLM consumption
   - Include few-shot examples for edge cases

4. **Test:**
   - Add unit tests to `tests/test_disease_classifier.py`
   - Validate with sample questions

### Code Style
- Use type hints
- Async/await for LLM calls
- Log key steps (disease classification, voting results, conflicts)
- Follow existing naming conventions

### Prompt Engineering Best Practices
- **Subtyping is critical**: Breast cancer, NSCLC require specific molecular subtypes
- **Prevent redundancy**: Don't tag biomarker when already in disease_type
- **Disease-specific rules**: SCLC staging (Limited/Extensive), hematologic no staging
- **Consider the answer**: Correct answer often reveals subtype/biomarker

## Testing Strategy

- **Unit tests**: Core logic (disease_classifier, vote_aggregator, prompt_manager)
- **Integration tests**: API endpoints, end-to-end tagging flow
- **Validation scripts**: Dry-run with sample questions (no API costs)
- **Manual review**: Visual inspection for accuracy
- **LLM Eval**: Review queue data used to evaluate model accuracy over time

## Configuration

### Environment Variables
- `OPENROUTER_API_KEY`: Required for LLM calls
- `OPENAI_API_KEY`: Required for embeddings (deduplication)
- See `.env.template` for full list

### Config Files
- `config/config.yaml`: Main config (prompt version, tagging settings)
- `config/models.yaml`: LLM model configs (costs, context windows)
- `config/logging.yaml`: Logging configuration

## Key Technologies

- Python 3.9+
- FastAPI (API framework)
- OpenRouter (multi-model LLM routing)
- OpenAI Embeddings (deduplication)
- SQLite (local database)
- Snowflake (production data source)
- YAML configuration
- Git version control

## Current Status

**Implemented:**
- ✓ Two-stage architecture (Stage 1: 3-model voting, Stage 2: 3-model voting)
- ✓ **66-field schema** across 6 groups (Core, Treatment Metadata, Clinical Context, Safety/Toxicity, Efficacy/Outcomes, Evidence/Guidelines, Question Format/Quality)
- ✓ DiseaseClassifier class with voting + web search fallback
- ✓ VoteAggregator with review flagging (majority + conflict) for all 66 fields
- ✓ MultiModelTagger with web search on ANY disagreement
- ✓ Disease-specific prompts: Breast cancer, NSCLC, Multiple Myeloma, CRC (all 66-field)
- ✓ Fallback prompt (66-field) for diseases without specific rules
- ✓ Deduplication pipeline with quality-based canonical selection
- ✓ Review reason tracking for LLM evaluation
- ✓ Question quality fields (Group F) for CME item analysis

**TODO:**
- Unit tests for 66-field vote_aggregator
- Tests for computed fields (answer_option_count, correct_answer_position)
- Post-processing normalizer for evolving fields
- Canonical term extraction from tagged data
- Frontend integration with review queue
- Snowflake integration for new question ingestion
- LLM eval dashboard for model accuracy tracking

## Notes

- Main branch: main
- Default prompt version: v2.0 (two-stage, 66-field schema)
- V1.0 still available for backwards compatibility
- **Field schema**: 66 LLM-tagged fields + 2 computed fields = 68 total
- **Boolean flaw fields**: 6 fields in Group F must be true/false (not strings, not null)
- **Computed fields**: answer_option_count and correct_answer_position are derived from raw data, not LLM-tagged
- All disagreements (majority + conflict) trigger web search and review
