# Tagging Workflow Runbook

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
# Count questions already in database
python -c "import sqlite3; print(sqlite3.connect('dashboard/data/questions.db').execute('SELECT COUNT(*) FROM questions').fetchone()[0])"

# Check specific disease count
python -c "import sqlite3; print(sqlite3.connect('dashboard/data/questions.db').execute(\"SELECT COUNT(*) FROM questions WHERE disease_state='MCL'\").fetchone()[0])"
```

### 3. Verify Backend Is Running (if editing via dashboard)
```bash
curl -s http://127.0.0.1:8000/health | python -c "import sys,json; d=json.load(sys.stdin); print(f'Questions: {d.get(\"total_questions\", \"?\")}')"
```

---

## Tagging New Questions

### Step 1: Dry Run First
```bash
python scripts/run_stage2_batch.py --disease "MCL" --dry-run
```

Expected output:
```
Found 367 existing questions in dashboard database
Filtered to 26 MCL questions
Excluding 18 questions that already exist in dashboard
Remaining: 8 new questions to tag
```

### Step 2: Run Actual Tagging (small batch)
```bash
python scripts/run_stage2_batch.py --disease "MCL" --limit 5
```

### Step 3: Verify Checkpoint Created
```bash
ls -la data/checkpoints/ | grep MCL | tail -5
```

### Step 4: Import to Dashboard
```bash
python dashboard/scripts/import_stage2_results.py --checkpoint data/checkpoints/stage2_tagged_MCL_*.json --upsert
```

**Note**: The import script automatically:
1. Normalizes tags via `TagNormalizer`
2. Calculates QCore scores for each imported question

**Dashboard edits**: When tags are edited via the dashboard UI (Save & Mark Reviewed), QCore scores are automatically recalculated. No manual action needed.

### Step 5: Verify Import
```bash
python -c "import sqlite3; print(sqlite3.connect('dashboard/data/questions.db').execute(\"SELECT COUNT(*) FROM questions WHERE disease_state='MCL'\").fetchone()[0])"
```

---

## After Editing Prompts

### CRITICAL: Commit Immediately
```bash
# After EVERY prompt change
git add prompts/v2.0/disease_prompts/<changed_file>.txt
git commit -m "fix: <description of change>"
```

### Verify Commit
```bash
git log --oneline -1
git show --stat HEAD
```

---

## Standard Values Reference

### treatment_line (Heme)
| Value | When to Use |
|-------|-------------|
| `Newly diagnosed` | First-line, frontline, treatment-naive |
| `Treatment-naive` | CLL-specific first-line |
| `Induction` | Initial intensive phase (ALL, MCL) |
| `Consolidation` | Post-induction (ALL, MCL, FL) |
| `Maintenance` | Ongoing suppressive therapy |
| `R/R` | Relapsed/refractory, any line after failure |
| `MRD+` | MRD-positive (ALL only) |

**DO NOT USE:** 1L, 2L, 2L+, 3L+

### evidence_type
| Value | When to Use |
|-------|-------------|
| `Phase 1`, `Phase 1/2`, `Phase 2`, `Phase 2/3`, `Phase 3` | Trial phase |
| `Real-world evidence` | Registry, claims, EHR data |
| `Retrospective study` | Retrospective analysis |
| `Meta-analysis` | Pooled analysis |
| `Guideline recommendation` | NCCN, ASCO, ESMO guidance |

**DO NOT USE:** Single-arm trial (use phase instead)

---

## Troubleshooting

### "0 exclusions" but questions exist
1. Check database path is correct
2. Verify running from project root
3. Check `source_id` format matches Excel QGD column

### Tags not showing in dashboard
1. Restart backend: `cd dashboard && python -m uvicorn backend.main:app --reload`
2. Clear browser cache
3. Check SQLite badge shows "SQLite" not "Offline"

### Prompt changes not taking effect
1. Verify git commit exists: `git log --oneline -1`
2. Confirm correct file was edited
3. Re-run tagging (new questions only)
