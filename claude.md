# Claude.md

This file provides context and guidelines for Claude Code when working on this project.

## Project Overview

This is an Automated CE Outcomes Dashboard and Tagging System designed to process and analyze continuing education (CE) outcomes data using AI-powered multi-model tagging with a two-stage disease-specific architecture.

## Tagging Architecture: V2.0 Two-Stage System

### Stage 1: Disease Classification
- **Single premium LLM** (Claude Sonnet 4.5 or GPT-4o)
- Lightweight prompt (~1K tokens)
- Returns: `disease_state` (e.g., "Breast cancer") + optional `disease_stage`
- **Cost**: ~$0.01 per question

### Stage 2: Disease-Specific Tagging
- **3-model parallel voting** (GPT-4o + Claude Sonnet 3.5 + Gemini Pro)
- Disease-specific prompt loaded based on Stage 1 result
- Focused prompts (~2-3K tokens) with disease-specific rules
- Returns: Remaining 7 tag fields with voting consensus
- **Cost**: ~$0.08 per question

### Total Cost & Benefits
- **~$0.09 per question** (40% savings vs V1.0 single-stage)
- Modular disease-specific rules (easy to update)
- Better accuracy (focused context, targeted rules)
- Cleaner architecture (one rule file per disease)

## Project Structure

```
src/
├── api/                          # FastAPI REST endpoints
│   ├── routers/                  # API route handlers
│   └── schemas.py                # Pydantic models
├── core/
│   ├── taggers/                  # Multi-model tagging system
│   │   ├── openrouter_client.py  # Unified LLM client (GPT, Claude, Gemini)
│   │   ├── disease_classifier.py # Stage 1: Disease classification
│   │   ├── multi_model_tagger.py # Two-stage orchestration + voting
│   │   └── vote_aggregator.py    # 3-model consensus logic
│   ├── services/
│   │   ├── disease_prompt_manager.py # Disease-specific prompt loader
│   │   └── prompt_manager.py     # Prompt version management
│   ├── knowledge/                # Domain knowledge
│   │   ├── constants.py          # Disease states, abbreviations
│   │   └── topic_constants.py    # Topic keywords
│   └── preprocessing/            # Data preprocessing
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
```

## Key Components

### Disease-Specific Rules (Priority Diseases)

**Completed:**
1. ✓ **Breast cancer** - Complex subtyping (HR+/HER2-, HER2+, HER2-low, TNBC)

**TODO:**
2. **NSCLC** - Molecular subtypes (EGFR, ALK, ROS1, KRAS G12C, etc.)
3. **Multiple Myeloma** - No staging, R/R vs newly diagnosed
4. **CRC** - MSI-H, biomarker testing emphasis
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

## Configuration

### Environment Variables
- `OPENROUTER_API_KEY`: Required for LLM calls
- See `.env.template` for full list

### Config Files
- `config/config.yaml`: Main config (prompt version, tagging settings)
- `config/models.yaml`: LLM model configs (costs, context windows)
- `config/logging.yaml`: Logging configuration

## Key Technologies

- Python 3.9+
- FastAPI (API framework)
- OpenRouter (multi-model LLM routing)
- SQLite (local database)
- YAML configuration
- Git version control

## Current Status

**Implemented:**
- ✓ Two-stage architecture (Stage 1: Disease classification, Stage 2: Voting)
- ✓ DiseaseClassifier class
- ✓ DiseasePromptManager class
- ✓ MultiModelTagger with V1/V2 support
- ✓ Breast cancer disease-specific rules (complete)
- ✓ Fallback prompt for diseases without specific rules

**TODO:**
- Unit tests for disease_classifier and prompt_manager
- Dry-run validation script
- Additional disease rules (NSCLC, MM, CRC, etc.)
- Frontend integration with two-stage results

## Notes

- Main branch: master
- Default prompt version: v2.0 (two-stage)
- V1.0 still available for backwards compatibility
- Cost savings: ~40% vs V1.0 single-stage approach
