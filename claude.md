# Claude.md

This file provides context and guidelines for Claude Code when working on this project.

## Project Overview

**PEM Eye Care CE Outcomes Dashboard** — A system for measuring and tracking educational outcomes across PEM eye care continuing education content.

This project is architecturally based on the CE-Outcomes oncology dashboard but operates as a **completely independent system** with its own database, repo, and deployment.

- **GitHub:** https://github.com/austinsatterfieldmd/PEM-CE-Outcomes
- **Supabase:** Project `bdeuexcvlzmdacjycpen` (https://bdeuexcvlzmdacjycpen.supabase.co)
- **Vercel:** TBD

### Key Architecture Decision
We kept the original database field names (disease_state, disease_stage, disease_type, biomarker, etc.) to avoid touching 487 references across 13 migration files and the entire frontend/backend. The fields are repurposed:
- `disease_state` → stores eye care condition (e.g., "AMD", "Glaucoma")
- `disease_stage` → stores condition severity (e.g., "Late AMD — geographic atrophy")
- `disease_type` → stores condition subtype (e.g., "Neovascular AMD (nAMD)")
- `is_oncology` → repurposed as relevance flag (TRUE = eye care question)
- `biomarker_1-5` → stores diagnostic markers (e.g., "OCT", "IOP measurement")
- `metastatic_site_1-3` → stores comorbidities (e.g., "Diabetes mellitus")
- `resistance_mechanism` → stores refractory context (e.g., "Anti-VEGF inadequate responder")

### Content Scope
15 eye care conditions across 6 categories:
- Retinal: AMD, Diabetic eye disease, Retinitis pigmentosa, MacTel, UME, RVO
- Glaucoma
- Anterior segment: DED, NK, Keratoconus, Allergic conjunctivitis, OSD
- Eyelid/Adnexa: Blepharitis, TED
- Surgical: Cataract/Refractive, Presbyopia
- Cross-discipline: Ocular toxicity from cancer therapy

### Key Files
- `prompts/v1.0/eye_care_classifier_prompt.txt` — Stage 1 classifier
- `prompts/v1.0/base/field_definitions.md` — 66-field tag schema
- `src/core/knowledge/eye_care_constants.py` — Conditions, treatments, abbreviation mappings
- `prompts/_oncology_reference/` — Archived oncology prompts (local only, .gitignored)

## Dashboard Deployment

**Supabase is the single source of truth** for all dashboard data.

- Import pipeline: Tag questions → Import to Supabase (`--target supabase`)
- 17 tables created from 13 migrations
- Frontend reads directly from Supabase via JS client

## Working Style Preferences

### No Edits Without Explicit Approval
When the user asks a QUESTION or makes an investigative statement, DO NOT EDIT FILES. Research, report findings, propose changes, and WAIT for approval.

### Commit After Every Change
After editing prompts, config files, or any file that affects tagging behavior, git add and commit IMMEDIATELY.