# CE Outcomes Dashboard - Vercel Deployment Questions

**Meeting Purpose:** Discuss deployment strategy for the CE Outcomes Dashboard to Vercel.

**Repository:** https://github.com/MJH-AI-Accelerator/CE-Outcomes-Dashboard

---

## Project Overview

The CE Outcomes Dashboard is a medical education (CME) question tagging and analytics platform with:
- **Frontend:** React + TypeScript + Vite + Tailwind
- **Backend:** FastAPI + SQLite
- **Features:** Question Explorer, Dedup Review, Tag Proposals, LLM Evaluation, QBoost Quality Scoring

---

## 1. Backend Architecture Decision

### Current Situation
The codebase has **two backend implementations**:

| Location | Type | Complexity |
|----------|------|------------|
| `dashboard/api/` | Vercel serverless functions | Simple endpoints (search, filters) |
| `dashboard/backend/` | Full FastAPI application | Complete backend with routers, services, database layer |

The existing `vercel.json` only routes to the serverless functions, not the full FastAPI backend.

### Questions
1. Which backend should we deploy?
   - Option A: Serverless functions only (simpler, limited features)
   - Option B: Full FastAPI backend (requires separate hosting)
   - Option C: Hybrid approach

2. If we need the full FastAPI backend, what hosting options do you recommend?
   - Railway
   - Render
   - AWS Lambda + API Gateway
   - Other?

3. Can Vercel handle a persistent FastAPI server, or is it strictly serverless?

---

## 2. Database Hosting

### Current Situation
- Using SQLite database (`dashboard/data/questions.db`)
- Contains ~250 questions with tags, corrections, dedup clusters, proposals
- Vercel serverless functions have **ephemeral filesystems** - SQLite won't persist

### Questions
1. What hosted database should we use?
   - Vercel Postgres (native integration)
   - Supabase (PostgreSQL, free tier)
   - PlanetScale (MySQL)
   - Neon (serverless PostgreSQL)
   - Turso (SQLite-compatible, edge-ready)

2. Who will handle the database schema migration from SQLite?

3. Do we need connection pooling for serverless cold starts?

4. What's the expected data volume? (Currently ~250 questions, growing to ~4,000)

---

## 3. Missing API Routes

### Current Situation
The `vercel.json` has routes for basic question search/filter endpoints, but is **missing routes** for key features:

| Feature | Endpoint Pattern | Purpose |
|---------|------------------|---------|
| Dedup Review | `/api/dedup/*` | Duplicate cluster review and confirmation |
| Tag Proposals | `/api/proposals/*` | Retroactive tag application system |
| LLM Evaluation | `/api/eval/*` | Model accuracy metrics |
| QBoost | `/api/qboost/*` | Question quality analysis |
| User Values | `/api/user-values/*` | Custom tag values |

### Questions
1. Should we add these routes to `vercel.json` as serverless functions?

2. Or should we deploy the full `dashboard/backend/` FastAPI app separately?

3. What's the tradeoff in terms of cost and maintenance?

---

## 4. Authentication (Okta)

### Current Situation
The `vercel.json` references Okta environment variables:
```json
"env": {
  "OKTA_ISSUER": "@okta_issuer",
  "OKTA_CLIENT_ID": "@okta_client_id",
  "OKTA_AUDIENCE": "@okta_audience"
}
```

### Questions
1. Is there an existing Okta application configured for this dashboard?

2. What callback URLs need to be added to Okta for the Vercel deployment?
   - Production: `https://<domain>/callback`
   - Preview: `https://<project>-*-vercel.app/callback`

3. Who should have access?
   - All MJH employees?
   - Specific teams (Medical Affairs, Editorial)?
   - Role-based access (admin vs viewer)?

4. Do we need to configure logout URLs as well?

---

## 5. Environment Variables & Secrets

### Required Variables

| Variable | Purpose | Source |
|----------|---------|--------|
| `OKTA_ISSUER` | Authentication | IT/Okta admin |
| `OKTA_CLIENT_ID` | Authentication | IT/Okta admin |
| `OKTA_AUDIENCE` | Authentication | IT/Okta admin |
| `DATABASE_URL` | Database connection | TBD based on DB choice |
| `OPENROUTER_API_KEY` | LLM tagging (if used in dashboard) | Project owner |

### Questions
1. How should we add secrets to Vercel?
   - Vercel dashboard UI?
   - Vercel CLI?
   - Integration with secrets manager?

2. Is there a shared secrets manager (1Password, AWS Secrets Manager, etc.)?

3. Should preview deployments use different credentials than production?

---

## 6. Build & Deploy Configuration

### Current Setup
- Root directory options: Repo root vs `dashboard/` subdirectory
- `vercel.json` is in `dashboard/` folder
- Frontend build command: `npm run vercel-build` (runs `tsc && vite build`)

### Questions
1. What should be the Vercel project's root directory?
   - Repo root (`/`)
   - Dashboard folder (`/dashboard`)

2. Should we use the existing `vercel.json` or modify it?

3. Preferred branch strategy?
   - `main` → Production
   - `develop` → Preview
   - Feature branches → Preview

4. Should we enable automatic deployments on push?

---

## 7. Domain & DNS

### Questions
1. What domain should the dashboard deploy to?
   - Subdomain of mjhlifesciences.com (e.g., `ce-outcomes.mjhlifesciences.com`)
   - Vercel default (e.g., `ce-outcomes-dashboard.vercel.app`)
   - Other?

2. Who manages DNS configuration?

3. Do we need SSL certificates, or does Vercel handle that automatically?

---

## 8. Data Loading & Sync

### Current Situation
- Data is loaded via Python scripts from local JSON/Excel files
- Script: `dashboard/scripts/import_stage2_results.py`
- No automated sync with external data sources

### Questions
1. How should production data be loaded initially?
   - Manual script execution?
   - Admin endpoint?
   - Database seed file?

2. Will there be ongoing data sync?
   - From Snowflake data warehouse?
   - Scheduled jobs?
   - Manual imports?

3. Do we need an admin interface for data management?

---

## 9. Timeline & Priorities

### Questions
1. What's the target launch date?

2. Which features are must-have for initial deployment?
   - [ ] Question Explorer (search, filter, view)
   - [ ] Performance metrics display
   - [ ] Dedup Review interface
   - [ ] Tag Proposals system
   - [ ] LLM Eval dashboard
   - [ ] QBoost quality analysis

3. Can we do a phased rollout (basic features first, then add more)?

---

## Summary Checklist

| Topic | Decision Needed |
|-------|-----------------|
| Backend | Serverless vs FastAPI vs Hybrid |
| Database | Which hosted DB provider |
| Missing routes | Add to vercel.json or separate backend |
| Okta | Configuration and access control |
| Secrets | How to manage in Vercel |
| Domain | URL and DNS setup |
| Data | Initial load and ongoing sync |
| Timeline | Launch date and feature priorities |

---

## Appendix: Current File Structure

```
CE-Outcomes-Dashboard/
├── dashboard/
│   ├── api/                  # Vercel serverless functions (simple)
│   ├── backend/              # Full FastAPI app (complex)
│   │   ├── main.py
│   │   ├── routers/          # questions, dedup, proposals, eval, qboost
│   │   └── services/         # database, checkpoint, corrections
│   ├── frontend/             # React + Vite
│   │   ├── src/
│   │   └── package.json
│   ├── vercel.json           # Current Vercel config
│   └── requirements.txt      # Python dependencies
├── src/                      # Core tagging system (not deployed)
├── prompts/                  # LLM prompts (not deployed)
└── scripts/                  # Utility scripts (not deployed)
```
