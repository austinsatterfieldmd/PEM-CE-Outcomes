# Automated CE Outcomes Dashboard (V3)

A medical education (CME) question tagging system that assigns 8 categorical tags to oncology questions using a 3-model LLM voting architecture.

## Features

- **3-Model Voting**: GPT-5.2, Claude Opus 4.5, and Gemini 2.5 Pro independently tag each question
- **100% Accuracy Target**: Unanimous (3/3) auto-accept, majority (2/3) or conflict requires human review
- **Web Search**: Perplexity Sonar for looking up novel trials, recent approvals
- **Unified API**: Single OpenRouter API key for all models
- **React Dashboard**: Search, filter, review, and analyze tagged questions

## Tag Categories

1. **Disease State** (79 values): NSCLC, Breast cancer, AML, GVHD, etc.
2. **Topic** (10 values): Treatment selection, Clinical efficacy, etc.
3. **Disease Stage**: Early-stage, Metastatic, Limited-stage, etc.
4. **Disease Type**: HR+/HER2-, EGFR-mutated, etc.
5. **Treatment Line**: 1L, 2L+, Adjuvant, R/R, etc.
6. **Treatment**: Drug names
7. **Biomarker**: EGFR mutation, HER2+, etc.
8. **Trial**: Clinical trial names

## Quick Start

```bash
# 1. Clone and setup
cd Automated-CE-Outcomes-Dashboard
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Configure
cp .env.template .env
# Edit .env and add your OPENROUTER_API_KEY

# 3. Run backend
python -m src.api.main

# 4. Run frontend (separate terminal)
cd dashboard
npm install
npm run dev
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Question Input                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Knowledge Enrichment Layer                      │
│  (Pre-extracts patterns from rules/KB for LLM context)      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              3-Model Parallel Voting                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                   │
│  │ GPT-5.2  │  │ Claude   │  │ Gemini   │                   │
│  │          │  │ Opus 4.5 │  │ 2.5 Pro  │                   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                   │
│       └─────────────┼─────────────┘                         │
│                     ▼                                        │
│              Vote Aggregator                                 │
└─────────────────────────────────────────────────────────────┘
                              │
           ┌──────────────────┼──────────────────┐
           ▼                  ▼                  ▼
    ┌───────────┐      ┌───────────┐      ┌───────────┐
    │ Unanimous │      │ Majority  │      │ Conflict  │
    │   (3/3)   │      │   (2/3)   │      │ (all diff)│
    │Auto-accept│      │  REVIEW   │      │  REVIEW   │
    └───────────┘      └───────────┘      └───────────┘
```

## Project Structure

```
Automated-CE-Outcomes-Dashboard/
├── src/
│   ├── core/
│   │   ├── taggers/          # 3-model voting logic
│   │   ├── knowledge/        # Domain rules & KB
│   │   └── services/         # Web search, prompts
│   ├── api/                  # FastAPI backend
│   └── workflows/            # Tagging orchestration
├── prompts/                  # Versioned prompt templates
├── knowledge_base/           # Entity databases
├── dashboard/                # React frontend
└── data/                     # Databases & review files
```

## Cost Estimate

Per question (~$0.12):
- GPT-5.2: $0.028
- Claude Opus 4.5: $0.073
- Gemini 2.5 Pro: $0.020

Total for 3,800 questions: ~$460

## License

Proprietary - MJH Life Sciences
