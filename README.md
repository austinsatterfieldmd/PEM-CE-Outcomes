# CE Outcomes Dashboard

A comprehensive medical education (CME) question tagging and analytics platform that combines AI-powered tagging, deduplication, and performance visualization.

## Features

### 1. Two-Stage AI Tagging System
- **Stage 1**: 3-model voting (GPT, Claude, Gemini) classifies oncology status + disease state
- **Stage 2**: Disease-specific prompts generate 66 metadata fields
- Web search fallback via Perplexity Sonar for novel entities
- Cost: ~$0.14 per canonical question

### 2. Question Deduplication
- Semantic embedding comparison (OpenAI text-embedding-3-small)
- 95% cosine similarity threshold
- Quality-based canonical selection
- Hierarchical validation (V2) for data quality assurance

### 3. Interactive Dashboard
- **Question Explorer**: Search, filter, and browse tagged questions
- **Review Tab**: Deduplication review, tag proposals, LLM evaluation metrics
- **QBoost Tab**: Question quality analysis with data-driven scoring
- Performance visualization by activity and audience segment

### 4. Disease-Specific Prompts
Complete prompts available for:
- Multiple Myeloma (MM)
- Non-Small Cell Lung Cancer (NSCLC)
- Colorectal Cancer (CRC)
- Breast Cancer

Fallback prompt for other oncology diseases.

---

## 66-Field Tag Schema

### Core Fields (19)
| Field | Description | Examples |
|-------|-------------|----------|
| `topic` | Educational focus (10 values) | Treatment selection, Clinical efficacy |
| `disease_stage` | Cancer stage | Early-stage, Metastatic |
| `disease_type` | Molecular/receptor subtype | HR+/HER2-, EGFR-mutated, TNBC |
| `treatment_line` | Therapy sequence | 1L, 2L+, Adjuvant, R/R |
| `treatment_1-5` | Drug/regimen names | pembrolizumab, osimertinib |
| `biomarker_1-5` | Tested markers | EGFR mutation, HER2+, PD-L1 |
| `trial_1-5` | Clinical trial names | KEYNOTE-756, DESTINY-Breast03 |

### Group A: Treatment Metadata (10)
`drug_class_1-3`, `drug_target_1-3`, `prior_therapy_1-3`, `resistance_mechanism`

### Group B: Clinical Context (9)
`metastatic_site_1-3`, `symptom_1-3`, `special_population_1-2`, `performance_status`

### Group C: Safety/Toxicity (7)
`toxicity_type_1-5`, `toxicity_organ`, `toxicity_grade`

### Group D: Efficacy/Outcomes (5)
`efficacy_endpoint_1-3`, `outcome_context`, `clinical_benefit`

### Group E: Evidence/Guidelines (3)
`guideline_source_1-2`, `evidence_type`

### Group F: Question Format/Quality (13)
`cme_outcome_level`, `data_response_type`, `stem_type`, `lead_in_type`, `answer_format`, `answer_length_pattern`, `distractor_homogeneity`, plus 6 boolean flaw fields

### Computed Fields (2)
`answer_option_count`, `correct_answer_position`

---

## Dashboard Features

### Question Explorer
- Full-text search across question stems
- Filter by disease, topic, treatment, biomarker, trial
- Activity date range filtering
- Sort by performance change, pre/post scores
- Pagination with configurable page size

### Review Tab
Three integrated review interfaces:

**Dedup Review**
- Side-by-side question comparison with diff highlighting
- Confirm/reject duplicate clusters
- Partial cluster confirmation support
- Activity list per question

**Tag Proposals**
- Retroactive tag application system
- Keyword-based candidate search
- Approve/skip individual candidates
- Batch apply approved tags

**LLM Eval**
- Model accuracy metrics (GPT vs Claude vs Gemini)
- Agreement level analysis (unanimous/majority/conflict)
- Field group breakdown
- Top problem fields identification

### QBoost Tab
Question quality analysis engine:
- Data-driven flaw penalty scoring (0-100)
- Grade calculation (A-F) by CME level
- Similar question finder via embeddings
- Performance prediction from historical data
- Improvement suggestions

---

## Quick Start

### Backend Setup
```bash
cd Automated-CE-Outcomes-Dashboard
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

pip install -r requirements.txt
pip install -r dashboard/requirements.txt

# Configure environment
cp .env.template .env
# Edit .env with your OPENROUTER_API_KEY

# Run backend
cd dashboard/backend
python main.py
```

### Frontend Setup
```bash
cd dashboard/frontend
npm install
npm run dev
```

Dashboard available at `http://localhost:5173`

---

## Project Structure

```
CE-Outcomes-Dashboard/
├── src/
│   ├── core/
│   │   ├── taggers/           # 3-model voting, disease classifier
│   │   ├── preprocessing/     # QBoost scorer, tag normalizer
│   │   ├── knowledge/         # Disease states, constants
│   │   └── services/          # Prompt manager, analyzers
│   ├── api/                   # API schemas
│   └── deduplication/         # Embedding & cleanup
├── prompts/
│   └── v2.0/
│       ├── disease_classifier_prompt.txt
│       ├── disease_prompts/   # MM, NSCLC, CRC, Breast
│       ├── disease_agnostic_guidance.md
│       └── fallback_prompt.txt
├── dashboard/
│   ├── backend/               # FastAPI backend
│   │   ├── main.py
│   │   ├── routers/           # questions, dedup, proposals, eval, qboost
│   │   └── services/          # database, checkpoint, corrections
│   └── frontend/              # React + TypeScript + Vite
│       └── src/
│           ├── App.tsx
│           └── components/    # Explorer, Review, QBoost tabs
├── scripts/                   # Batch processing utilities
├── deduplication_v2/          # Hierarchical validation system
├── config/                    # YAML configuration files
└── data/                      # Local data (gitignored)
```

---

## Configuration

### Environment Variables
```bash
# Required
OPENROUTER_API_KEY=sk-or-v1-xxx

# Optional model overrides
OPENROUTER_MODEL_GPT=openai/gpt-4o
OPENROUTER_MODEL_CLAUDE=anthropic/claude-sonnet-4
OPENROUTER_MODEL_GEMINI=google/gemini-2.0-flash

# Database
DATABASE_PATH=data/databases/questions.db

# Server
API_HOST=127.0.0.1
API_PORT=8000
```

### Config Files
- `config/models.yaml` - LLM model configurations
- `config/canonical_values.yaml` - Standardized tag values
- `config/qboost_calibration.yaml` - Quality scoring weights
- `config/excluded_questions.yaml` - Permanent exclusion list

---

## Cost Estimates

| Component | Cost |
|-----------|------|
| Deduplication (embedding) | $0.004/question |
| Stage 1 (3-model classifier) | $0.01/question |
| Stage 2 (3-model, 66-field) | $0.13/question |
| **Total per canonical** | **~$0.14** |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    React Dashboard                           │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐                      │
│  │Explorer │  │ Review  │  │ QBoost  │                      │
│  └────┬────┘  └────┬────┘  └────┬────┘                      │
└───────┼────────────┼────────────┼───────────────────────────┘
        │            │            │
        ▼            ▼            ▼
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Backend                            │
│  /questions  /dedup  /proposals  /eval  /qboost  /reports   │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│                   SQLite Database                            │
│  questions, tags, activities, dedup_clusters, proposals      │
└─────────────────────────────────────────────────────────────┘

            AI TAGGING PIPELINE

┌─────────────────────────────────────────────────────────────┐
│  Stage 1: Disease Classification (3-Model Voting)            │
│  → is_oncology: true/false                                   │
│  → disease_state: "Multiple Myeloma" / null                  │
└─────────────────────────────────────────────────────────────┘
                         │
         ┌───────────────┴───────────────┐
         ▼                               ▼
┌─────────────────┐          ┌─────────────────────────────────┐
│  NON-ONCOLOGY   │          │  ONCOLOGY                        │
│  Skip Stage 2   │          │  Load disease-specific prompt    │
│  (save $0.08)   │          │  → 66-field JSON output          │
└─────────────────┘          └─────────────────────────────────┘
```

---

## 3-Model Voting Logic

| Agreement | Pattern | Action |
|-----------|---------|--------|
| **Unanimous** | 3/3 agree | Auto-accept |
| **Majority** | 2/3 agree | Accept majority, flag for review |
| **Conflict** | 1/1/1 | No auto-assign, flag for review |

Web search triggered on ANY disagreement for factual fields.

---

## License

Proprietary - MJH Life Sciences
