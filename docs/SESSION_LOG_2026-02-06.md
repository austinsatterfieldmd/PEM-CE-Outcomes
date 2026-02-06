# Session Log: February 6, 2026

## Summary
Fixed critical bug where user-reviewed questions (edited_by_user=1) were still appearing in the "needs review" queue.

## Issues Identified & Fixed

### 1. needs_review Flag Not Being Cleared
**Problem**: 46 questions had `edited_by_user=1` (meaning user had reviewed/saved them) but also `needs_review=1` (meaning they still appeared in the review queue).

**Root Cause**: This inconsistent state could occur through:
- Historical code that didn't properly clear needs_review when marking as reviewed
- The `flag_question` function can set `needs_review=1` on any question, even previously reviewed ones

**Fix Applied**:
1. **Database fix** (temporary): SQL update to clear inconsistent flags
   ```sql
   UPDATE tags SET needs_review = 0 WHERE edited_by_user = 1 AND needs_review = 1
   ```

2. **Code fix** (permanent): Modified [database.py](dashboard/backend/services/database.py) queries to exclude user-edited questions from review queue:
   - Line ~1343: Search query now excludes `edited_by_user=1` from `needs_review=1` filter
   - Line ~2833: Stats query now excludes `edited_by_user=1` from needs_review count

### 2. SQLite Connection Indicator Not Showing
**Problem**: Dashboard header only showed "Read-Only" badge in Vercel mode, no indicator when connected to SQLite backend.

**Fix**: Modified [ExportEditsButton.tsx](dashboard/frontend/src/components/ExportEditsButton.tsx) to show:
- Green "SQLite" badge with Database icon when connected to backend
- Gray "Read-Only" badge with CloudOff icon when in Vercel/offline mode

### 3. Re-Tagging Prevention (Already Implemented)
**Problem**: User was concerned about tagging script wasting money by re-tagging existing questions.

**Finding**: This was already fixed via the `--exclude-db` flag in [run_stage2_batch.py](scripts/run_stage2_batch.py). The script automatically excludes questions that exist in `dashboard/data/questions.db`.

## Files Modified This Session

| File | Change |
|------|--------|
| [database.py](dashboard/backend/services/database.py:1343) | Added `edited_by_user=0` check to needs_review filter |
| [database.py](dashboard/backend/services/database.py:2833) | Added `edited_by_user=0` check to stats query |
| [ExportEditsButton.tsx](dashboard/frontend/src/components/ExportEditsButton.tsx) | Added SQLite connection indicator |

## Key Files Reference (File Index)

### Backend
- [database.py](dashboard/backend/services/database.py) - Database operations, tag updates, search queries
- [questions.py](dashboard/backend/routers/questions.py) - API endpoints for questions
- [checkpoint.py](dashboard/backend/services/checkpoint.py) - Checkpoint file management

### Frontend
- [api.ts](dashboard/frontend/src/services/api.ts) - API service, `updateQuestionTags` function
- [localEdits.ts](dashboard/frontend/src/services/localEdits.ts) - Local storage for Vercel mode
- [QuestionDetail.tsx](dashboard/frontend/src/components/QuestionDetail.tsx) - Question detail panel, tag editing
- [QuestionReviewDetail.tsx](dashboard/frontend/src/components/QuestionReviewDetail.tsx) - Review queue detail panel
- [ExportEditsButton.tsx](dashboard/frontend/src/components/ExportEditsButton.tsx) - Connection status indicator

### Scripts
- [run_stage2_batch.py](scripts/run_stage2_batch.py) - Batch tagging script with `--exclude-db` flag
- [import_stage2_results.py](dashboard/scripts/import_stage2_results.py) - Import tagged results to dashboard DB
- [restore_reviewed_data.py](scripts/restore_reviewed_data.py) - One-time restore script

### Database
- [questions.db](dashboard/data/questions.db) - SQLite database with all questions and tags
- Key tables: `questions`, `tags`, `question_activities`
- Key tag columns: `edited_by_user`, `needs_review`, `tag_status`, `worst_case_agreement`

## Tag Edit Flow

When user saves tags via dashboard:

1. **Frontend** calls `updateQuestionTags()` in [api.ts:619](dashboard/frontend/src/services/api.ts#L619)
2. **Backend** receives PUT `/api/questions/{id}/tags` in [questions.py:234](dashboard/backend/routers/questions.py#L234)
3. **Database** `update_tags()` method called in [database.py:693](dashboard/backend/services/database.py#L693)
4. If `mark_as_reviewed=True`:
   - Sets `needs_review=0`
   - Sets `edited_by_user=1`
   - Sets `tag_status='verified'`
   - Sets `overall_confidence=1.0`

## Verification Commands

```powershell
# Check database stats
curl http://127.0.0.1:8000/api/questions/stats/summary

# Check for inconsistent flags (should return 0)
python -c "import sqlite3; c=sqlite3.connect('dashboard/data/questions.db'); print(c.execute('SELECT COUNT(*) FROM tags WHERE edited_by_user=1 AND needs_review=1').fetchone()[0])"

# Check total reviewed vs needs review
python -c "import sqlite3; c=sqlite3.connect('dashboard/data/questions.db'); print('edited_by_user:', c.execute('SELECT COUNT(*) FROM tags WHERE edited_by_user=1').fetchone()[0]); print('needs_review:', c.execute('SELECT COUNT(*) FROM tags WHERE needs_review=1').fetchone()[0])"
```

## Service Management

To restart the backend (needed after database changes):
```powershell
cd "c:\Dev\CE-Outcomes-Dashboard\dashboard"; python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

## Current Database State (End of Session)
- Total questions: 367
- Tagged questions: 366
- Questions needing review: 70
- User-edited questions: 297 (296 audited + 1 more today)
