# Web Search Strategy - V2.0 Two-Stage Architecture

The V2.0 tagging system uses **TWO SEPARATE WEB SEARCH MECHANISMS** at different stages:

---

## Stage 1: Disease Classification Web Search

**Location:** `src/core/taggers/disease_classifier.py`

**Purpose:** Identify disease from clinical trial names when disease cannot be determined from question/answer/activity

**When triggered:**
- Stage 1 LLM returns `disease_state: null`
- AND a trial name is detected in the question (e.g., KEYNOTE-756, CheckMate-227)

**Query format:**
```
"{trial_name} oncology clinical trial disease cancer"
```

**Context:**
```
"What disease/cancer type is studied in the {trial_name} trial?"
```

**Example:**
- Question: "Which of the following best describes key findings from the phase 3 KEYNOTE-756 trial?"
- Trial detected: "KEYNOTE-756"
- Web search query: "KEYNOTE-756 oncology clinical trial disease cancer"
- Result parsing: Looks for disease keywords (breast cancer, NSCLC, etc.)
- Output: `{"disease_state": "Breast cancer"}`

**Cost:** ~$0.005 per search (estimated 5-10% of questions)

---

## Stage 2: Factual Tag Conflict Resolution

**Location:** `src/core/taggers/multi_model_tagger.py` → `_handle_web_search()`

**Purpose:** Resolve conflicts between the 3 models on factual tag fields

**When triggered:**
- 3-model voting results in conflicts (`AgreementLevel.CONFLICT`)
- AND the conflicted field is factual (not clinical judgment)

**Searchable fields:**
- `treatment` - Drug names, regimens
- `trial` - Clinical trial names and details
- `biomarker` - Biomarker names and definitions
- `disease_stage` - Stage definitions (e.g., "extensive-stage vs metastatic")
- `disease_type` - Subtype clarification (e.g., "HER2-low vs HER2+")
- `treatment_line` - Treatment line terminology (e.g., "perioperative vs neoadjuvant")

**Excluded field:**
- `topic` - Requires clinical judgment, not factual lookup

### Field-Specific Search Strategies

#### Trial
**Query:** `"{entity} oncology clinical trial results efficacy"`
**Context:** `"What are the key findings and disease studied in the {entity} trial?"`
**Example:** DESTINY-Breast03 → trial results and HER2+ breast cancer context

#### Treatment
**Query:** `"{entity} oncology FDA approval indications mechanism"`
**Context:** `"What are the FDA-approved indications and mechanism of action for {entity}?"`
**Example:** trastuzumab deruxtecan → HER2-low breast cancer indication

#### Biomarker
**Query:** `"{entity} biomarker cancer predictive prognostic testing"`
**Context:** `"What is {entity} as a biomarker in oncology? Predictive or prognostic?"`
**Example:** PD-L1 → predictive biomarker for immunotherapy

#### Disease Stage
**Query:** `"{entity} cancer staging definition"`
**Context:** `"What does '{entity}' mean in cancer staging?"`
**Example:** Extensive-stage SCLC → clarifies staging system

#### Disease Type
**Query:** `"{entity} cancer subtype classification"`
**Context:** `"What is {entity} as a cancer subtype?"`
**Example:** HER2-low → distinct from HER2+ and HER2-negative

#### Treatment Line
**Query:** `"{entity} treatment line oncology definition"`
**Context:** `"What does '{entity}' mean in oncology treatment lines?"`
**Example:** Perioperative → before and after surgery

**Cost:** Included in existing tagging cost (~$0.005 per entity lookup, max 3 per question)

---

## Key Differences

| Aspect | Stage 1 Web Search | Stage 2 Web Search |
|--------|-------------------|-------------------|
| **Purpose** | Find disease from trial name | Resolve tag conflicts |
| **Trigger** | disease_state is null + trial detected | 3-model conflict on factual fields |
| **Scope** | Only disease identification | 6 different tag fields |
| **Query** | Generic trial lookup | Field-specific targeted queries |
| **Context** | "What disease is this trial?" | Field-specific questions |
| **Frequency** | 5-10% of questions | ~15-20% of questions with conflicts |
| **Output** | disease_state value | Factual information for conflict resolution |

---

## Cost Estimation

**Scenario:** 18,000 questions

**Stage 1 web searches:**
- Triggered: ~1,000 questions (5-10% with trial names but no disease)
- Cost: 1,000 × $0.005 = **$5**

**Stage 2 web searches:**
- Triggered: ~2,700 questions (15% with conflicts on factual fields)
- Avg searches per question: 1.5
- Cost: 2,700 × 1.5 × $0.005 = **$20.25**

**Total web search cost:** ~$25.25 for 18,000 questions
**Per-question web search cost:** ~$0.0014

---

## Implementation Notes

1. **Stage 1 is ALWAYS attempted** if disease_state is null and trial name detected
   - No user intervention required
   - Automatic fallback mechanism

2. **Stage 2 is OPTIONAL** and controlled by `use_web_search` flag
   - Can be disabled to save cost
   - Only triggers on conflicts (not all questions)

3. **Both stages use Perplexity Sonar** via OpenRouter
   - Real-time web search capability
   - Cached for 15 minutes (WebSearchService handles caching)

4. **Stage 1 happens BEFORE Stage 2**
   - Disease classification completes first
   - Then disease-specific prompt loaded
   - Then 3-model voting
   - Finally web search for conflicts (if enabled)

---

## Future Enhancements

1. **Confidence thresholding for Stage 1**
   - Only trigger web search if LLM confidence is low
   - Could reduce web search calls by 30-40%

2. **Smart caching across questions**
   - Cache trial → disease mappings
   - Cache drug → indication mappings
   - Reduce redundant searches

3. **Parallel web searches**
   - Search multiple conflicted fields simultaneously
   - Reduce total latency

4. **LLM-based result parsing**
   - Use small LLM to parse web search results
   - More accurate entity extraction
   - Better conflict resolution

---

**Last Updated:** 2026-01-16
**Version:** V2.0
