# Tagging Workflow Runbook

## End-to-End Pipeline (Quick Reference)

```
1. Dry run           →  python scripts/run_stage2_batch.py --disease "X" --dry-run
2. Tag questions     →  python scripts/run_stage2_batch.py --disease "X" --limit 20
3. Import to Supa    →  python dashboard/scripts/import_stage2_results.py --upsert --file data/checkpoints/stage2_tagged_X.json
4. Performance data  →  python scripts/import_performance_data.py --disease "X" --target supabase
5. Verify in Supa    →  Check dashboard at Vercel
```

**IMPORTANT:** Step 2 auto-imports to SQLite but does NOT auto-sync to Supabase.
You MUST run steps 3-4 manually after tagging completes.

---

## Pre-Flight Checklist (BEFORE any tagging)

### 1. Verify Prompts Are Current
```bash
# Check recent prompt commits
git log --oneline -5 prompts/v2.0/disease_prompts/

# Verify no uncommitted prompt changes
git status prompts/
```

### 2. Check Existing Questions
```bash
# Count questions already tagged for this disease
python -c "import sqlite3; print(sqlite3.connect('dashboard/data/questions.db').execute(\"SELECT COUNT(*) FROM tags WHERE disease_state='Breast cancer'\").fetchone()[0])"
```

### 3. Confirm Supabase Access
```bash
# Quick connectivity check
python -c "from supabase import create_client; import os; from dotenv import load_dotenv; load_dotenv(); c = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_KEY')); print(f'Connected: {len(c.table(\"questions\").select(\"id\").limit(1).execute().data)} rows')"
```

---

## Step 1: Dry Run

Always dry-run first to see how many questions are available:

```bash
python scripts/run_stage2_batch.py --disease "Breast cancer" --dry-run
```

Expected output:
```
Found 1859 existing questions in dashboard database
Filtered to 768 Breast cancer questions
Excluding 20 questions that already exist in dashboard database
Remaining: 748 new questions to tag
Estimated API cost: $239.36
DRY RUN MODE - No API calls will be made
```

---

## Step 2: Tag Questions (3-Model Voting)

```bash
# Tag a batch (20 questions ≈ $6-7 API cost, ~10-12 minutes)
python scripts/run_stage2_batch.py --disease "Breast cancer" --limit 20
```

### What happens:
1. Loads questions from `data/checkpoints/stage2_ready_MASTER.xlsx`
2. Filters by disease, excludes already-tagged questions
3. Sends each question to 3 LLMs in parallel (GPT-4o, Claude Sonnet, Gemini Pro)
4. Aggregates votes → unanimous / majority / conflict
5. Saves checkpoint every 5 questions (auto-resume on failure)
6. Normalizes tags + calculates QCore scores
7. **Auto-imports to SQLite** (but NOT to Supabase)

### Key flags:
| Flag | Default | Purpose |
|------|---------|---------|
| `--limit N` | all | Process N questions max |
| `--start N` | 0 | Skip first N questions |
| `--batch-size N` | 5 | Checkpoint save frequency |
| `--dry-run` | false | Preview only, no API calls |
| `--exclude-db` | true | Skip questions already in SQLite |
| `--web-search` | false | Enable web search on disagreements |

### Output files:
- Checkpoint: `data/checkpoints/stage2_breast_cancer_checkpoint.json`
- Results: `data/checkpoints/stage2_tagged_breast_cancer.json`

### Cost estimate:
- ~$0.32 per question (Stage 1 skip + Stage 2 with 3 models)
- 20 questions ≈ $6.40

---

## Step 3: Import to Supabase

**This is the critical step that `run_stage2_batch.py` does NOT do automatically.**

```bash
python dashboard/scripts/import_stage2_results.py --upsert --file data/checkpoints/stage2_tagged_breast_cancer.json
```

### What this does:
- Reads the checkpoint JSON
- Normalizes tags via `TagNormalizer`
- Inserts new questions + tags into Supabase (default target)
- Calculates QCore scores
- Links questions to activities
- Skips human-reviewed questions (`edited_by_user=1`)

### Common errors:
| Error | Cause | Fix |
|-------|-------|-----|
| `duplicate key value violates unique constraint` | ID collision with existing question | Re-run; or manually insert with next available ID |
| `Could not find column X` | Extra fields in final_tags | Clean checkpoint or filter fields |

---

## Step 4: Import Performance Data

```bash
python scripts/import_performance_data.py --disease "Breast cancer" --target supabase
```

### What this does:
- Reads raw Excel file (`data/raw/FullColumnsSample_*.xlsx`)
- Matches questions by source_id (QGD)
- Aggregates pre/post scores by audience segment
- Upserts performance rows + demographic breakdowns to Supabase
- Creates activity records and question-activity links

### Flags:
| Flag | Purpose |
|------|---------|
| `--target supabase` | Write to Supabase (default is SQLite) |
| `--target both` | Write to both SQLite and Supabase |
| `--disease "X"` | Filter to one disease |
| `--dry-run` | Preview only |

---

## Step 5: Verify

### Check Supabase counts
```bash
python -c "
from supabase import create_client; import os; from dotenv import load_dotenv; load_dotenv()
c = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_KEY'))
t = c.table('tags').select('question_id').eq('disease_state', 'Breast cancer').execute()
print(f'Breast cancer tags in Supabase: {len(t.data)}')
"
```

### Check the Vercel dashboard
Navigate to the deployed dashboard and filter by Breast cancer. Verify:
- [ ] Question count matches expected total
- [ ] Tags are populated (topic, disease_type, treatment_line, etc.)
- [ ] QCore scores and grades are showing
- [ ] Performance data (pre/post scores) is visible
- [ ] New questions appear in the review queue (needs_review=true)

---

## After Editing Prompts

### CRITICAL: Commit Immediately
```bash
# After EVERY prompt change
git add prompts/v2.0/disease_prompts/<changed_file>.txt
git commit -m "fix: <description of change>"
git log --oneline -1  # Verify
```

---

## Reviewing Tagged Questions

After tagging, new questions go to the **review queue** in the dashboard.

### Review workflow:
1. Open dashboard → Review Queue → Filter by disease
2. Check each question's tags against the question stem + correct answer
3. Fix any incorrect tags
4. Add review notes for prompt improvement ideas
5. Click "Save & Mark Reviewed" (sets `edited_by_user=1`)

### After a review session:
- Pull review notes to identify prompt gaps
- Update prompts based on patterns
- Commit prompt changes
- Tag the next batch

---

## Standard Values Reference

### treatment_line (Solid Tumors)

**Early-Stage:**
| Value | When to Use |
|-------|-------------|
| `Adjuvant` | After surgery |
| `Neoadjuvant` | Before surgery |
| `Perioperative` | Before and after surgery |

**Metastatic (use specific line when prior therapies are countable):**
| Value | When to Use |
|-------|-------------|
| `1L` | First-line, treatment-naive metastatic |
| `2L` | Second-line (1 countable prior line) |
| `3L` | Third-line (2 countable prior lines) |
| `4L+` | Fourth-line or later |
| `2L+` | ONLY when exact line is ambiguous ("heavily pretreated") |
| `Maintenance` | Continuation after response |

### treatment_line (Heme)
| Value | When to Use |
|-------|-------------|
| `Newly diagnosed` | First-line, frontline, treatment-naive |
| `Treatment-naive` | CLL-specific first-line |
| `Induction` | Initial intensive phase (ALL, MCL) |
| `Consolidation` | Post-induction (ALL, MCL, FL) |
| `Maintenance` | Ongoing suppressive therapy |
| `R/R` | Relapsed/refractory, any line after failure |

### evidence_type
| Value | When to Use |
|-------|-------------|
| `Phase 1`, `Phase 1/2`, `Phase 2`, `Phase 2/3`, `Phase 3` | Trial phase |
| `Real-world evidence` | Registry, claims, EHR data |
| `Retrospective study` | Retrospective analysis |
| `Meta-analysis` | Pooled analysis |
| `Guideline recommendation` | NCCN, ASCO, ESMO guidance |

---

## Troubleshooting

### "0 exclusions" but questions exist
1. Check database path is correct
2. Verify running from project root
3. Check `source_id` format matches Excel QGD column

### Tags not showing in dashboard
1. Verify Supabase sync completed (Step 3)
2. Check browser — hard refresh (Ctrl+Shift+R)
3. Run verification query to confirm data in Supabase

### Prompt changes not taking effect
1. Verify git commit exists: `git log --oneline -1`
2. Confirm correct file was edited (check prompt filename matches disease)
3. Re-run tagging for new questions only (existing questions are excluded)

### Supabase import errors
1. `duplicate key`: ID collision — manually insert with next available ID
2. `column does not exist`: Extra fields in checkpoint — clean or filter
3. `409 Conflict`: Question already exists — check source_id in Supabase

### Performance data shows 0 matches
1. Check that the Excel file contains rows for this disease's QGDs
2. Verify the Excel path in `import_performance_data.py` is current
3. Run with `--dry-run` first to see match count
