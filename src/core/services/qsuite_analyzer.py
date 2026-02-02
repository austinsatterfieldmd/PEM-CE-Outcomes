"""
Q-Suite Analyzer - Combined Question Quality Analysis Service.

The Q-Suite includes three tools:
- QCore: Quality scoring (flaw deductions, structure bonuses)
- QPredict: Performance prediction (embedding search → similar Q analysis → ML prediction)
- QBoost: LLM accuracy + LO alignment + improvement suggestions

This service orchestrates all three in a combined workflow:
1. Parse uploaded document (Word format)
2. Run combined LLM call for tagging + accuracy assessment
3. Calculate QCore scores
4. Optionally predict performance (QPredict)
5. Return comprehensive analysis results
"""
import asyncio
import logging
import re
from typing import Optional, List
from dataclasses import dataclass, field
from datetime import datetime

from .outcomes_doc_parser import ParsedQuestion, ParsedDocument
from ..preprocessing.qcore_scorer import calculate_qcore_score

logger = logging.getLogger(__name__)


@dataclass
class WebSearchResult:
    """Result from Perplexity Sonar web search for fact-checking."""
    search_performed: bool = False
    search_query: str = ""
    trial_name: str = ""
    key_findings: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    accuracy_adjustment: int = 0  # +/- adjustment to accuracy score
    verification_note: str = ""  # Human-readable summary


@dataclass
class QBoostAssessment:
    """LLM-based accuracy and alignment assessment."""
    # Accuracy assessment
    accuracy_score: int = 0  # 0-100
    accuracy_grade: str = "N/A"
    accuracy_issues: list[str] = field(default_factory=list)

    # Learning Objective alignment
    lo_score: int = 0  # 0-100
    lo_grade: str = "N/A"
    lo_assessment: str = ""
    lo_suggestions: list[str] = field(default_factory=list)

    # Improvement suggestions
    suggestions: list[str] = field(default_factory=list)

    # Model identification (for Quorum mode)
    model_name: str = ""

    # Web search verification (for fact-checking)
    web_search: Optional[WebSearchResult] = None


@dataclass
class QuorumResult:
    """Result from Quorum (3-model aggregation) analysis."""
    # Aggregated tags (majority voting)
    aggregated_tags: dict = field(default_factory=dict)

    # Individual model results
    gpt_tags: dict = field(default_factory=dict)
    claude_tags: dict = field(default_factory=dict)
    gemini_tags: dict = field(default_factory=dict)

    # Individual QBoost assessments
    gpt_qboost: Optional[QBoostAssessment] = None
    claude_qboost: Optional[QBoostAssessment] = None
    gemini_qboost: Optional[QBoostAssessment] = None

    # Averaged QCore score
    avg_qcore_score: float = 0.0
    gpt_qcore_score: float = 0.0
    claude_qcore_score: float = 0.0
    gemini_qcore_score: float = 0.0

    # Averaged QBoost scores (accuracy and LO alignment)
    avg_accuracy_score: float = 0.0
    avg_lo_score: float = 0.0


@dataclass
class QPredictResult:
    """Similar question with performance data for prediction."""
    question_id: int
    source_id: str
    similarity_score: float  # 0-100%
    question_stem_preview: str
    performance: dict = field(default_factory=dict)  # pre, post, n by segment
    qcore_score: float = 0.0  # Quality score of similar question
    qcore_grade: str = ""  # Grade of similar question


@dataclass
class QuestionAnalysis:
    """Complete analysis of a single question."""
    question_number: int
    question_stem: str
    options: list[str]
    correct_answer: str
    learning_objective: str

    # QCore results
    tags: dict = field(default_factory=dict)
    qcore_score: float = 0.0
    qcore_grade: str = "D"  # D is now the floor (no F grade)
    qcore_breakdown: dict = field(default_factory=dict)
    ready_for_deployment: bool = False

    # QBoost results (LLM assessment) - single model
    qboost: Optional[QBoostAssessment] = None

    # Quorum results (3-model aggregation)
    quorum: Optional[QuorumResult] = None
    is_quorum: bool = False  # True if Quorum mode was used

    # QPredict results (similar questions for performance prediction)
    similar_questions: list[QPredictResult] = field(default_factory=list)

    # Metadata
    cme_level: str = "Knowledge"
    tagging_model: str = ""
    analysis_timestamp: str = ""

    # Cost tracking (actual API costs)
    api_cost: float = 0.0

    def _qboost_to_dict(self, qb: Optional[QBoostAssessment]) -> Optional[dict]:
        """Helper to convert QBoostAssessment to dict."""
        if not qb:
            return None
        result = {
            "accuracy_score": qb.accuracy_score,
            "accuracy_grade": qb.accuracy_grade,
            "accuracy_issues": qb.accuracy_issues,
            "lo_score": qb.lo_score,
            "lo_grade": qb.lo_grade,
            "lo_assessment": qb.lo_assessment,
            "lo_suggestions": qb.lo_suggestions,
            "suggestions": qb.suggestions,
            "model_name": qb.model_name,
        }
        # Add web search results if present
        if qb.web_search and qb.web_search.search_performed:
            result["web_search"] = {
                "search_performed": qb.web_search.search_performed,
                "trial_name": qb.web_search.trial_name,
                "key_findings": qb.web_search.key_findings,
                "sources": qb.web_search.sources,
                "accuracy_adjustment": qb.web_search.accuracy_adjustment,
                "verification_note": qb.web_search.verification_note,
            }
        return result

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            "question_number": self.question_number,
            "question_stem": self.question_stem,
            "options": self.options,
            "correct_answer": self.correct_answer,
            "learning_objective": self.learning_objective,
            "tags": self.tags,
            "qcore_score": self.qcore_score,
            "qcore_grade": self.qcore_grade,
            "qcore_breakdown": self.qcore_breakdown,
            "ready_for_deployment": self.ready_for_deployment,
            "qboost": self._qboost_to_dict(self.qboost),
            "is_quorum": self.is_quorum,
            "similar_questions": [
                {
                    "question_id": sq.question_id,
                    "source_id": sq.source_id,
                    "similarity_score": sq.similarity_score,
                    "question_stem_preview": sq.question_stem_preview,
                    "performance": sq.performance,
                }
                for sq in self.similar_questions
            ],
            "cme_level": self.cme_level,
            "tagging_model": self.tagging_model,
            "analysis_timestamp": self.analysis_timestamp,
            "api_cost": self.api_cost,
        }

        # Add Quorum-specific results if present
        if self.quorum and self.is_quorum:
            result["quorum"] = {
                "gpt_qboost": self._qboost_to_dict(self.quorum.gpt_qboost),
                "claude_qboost": self._qboost_to_dict(self.quorum.claude_qboost),
                "gemini_qboost": self._qboost_to_dict(self.quorum.gemini_qboost),
                "gpt_qcore_score": self.quorum.gpt_qcore_score,
                "claude_qcore_score": self.quorum.claude_qcore_score,
                "gemini_qcore_score": self.quorum.gemini_qcore_score,
                "avg_qcore_score": self.quorum.avg_qcore_score,
                "avg_accuracy_score": self.quorum.avg_accuracy_score,
                "avg_lo_score": self.quorum.avg_lo_score,
            }

        return result


@dataclass
class DocumentAnalysis:
    """Complete analysis of an uploaded document."""
    filename: str
    activity_title: str
    analysis_timestamp: str
    total_questions: int
    questions: list[QuestionAnalysis]

    # Summary statistics
    avg_qcore_score: float = 0.0
    avg_qboost_accuracy: float = 0.0
    avg_qboost_lo: float = 0.0
    grade_distribution: dict = field(default_factory=dict)
    ready_count: int = 0
    warnings: list[str] = field(default_factory=list)

    # Analysis options used
    options_used: dict = field(default_factory=dict)

    # Cost tracking
    total_cost: float = 0.0
    model_used: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "filename": self.filename,
            "activity_title": self.activity_title,
            "analysis_timestamp": self.analysis_timestamp,
            "total_questions": self.total_questions,
            "avg_qcore_score": self.avg_qcore_score,
            "avg_qboost_accuracy": self.avg_qboost_accuracy,
            "avg_qboost_lo": self.avg_qboost_lo,
            "grade_distribution": self.grade_distribution,
            "ready_count": self.ready_count,
            "ready_percentage": round(self.ready_count / self.total_questions * 100, 1) if self.total_questions > 0 else 0,
            "warnings": self.warnings,
            "options_used": self.options_used,
            "total_cost": round(self.total_cost, 4),
            "model_used": self.model_used,
            "questions": [q.to_dict() for q in self.questions],
        }


# Combined prompt for QCore tagging + QBoost assessment (single LLM call)
QSUITE_COMBINED_PROMPT = """You are an expert medical education quality analyst. Analyze this CME question and provide comprehensive quality assessment.

## Question
Stem: {question_stem}

Answer Options:
{options}

Correct Answer: {correct_answer}

{lo_section}

## Instructions
Provide a comprehensive analysis with TWO sections:

### SECTION 1: QCore Tags (for quality scoring)
Return quality fields as JSON:

{{
    "tags": {{
        "topic": "<Educational topic>",
        "disease_state": "<Cancer type if oncology>",
        "cme_outcome_level": "3 - Knowledge" or "4 - Competence",
        "data_response_type": "Qualitative" | "Comparative" | "Boolean" | "Numeric",
        "stem_type": "Clinical vignette" | "Case series" | "Direct question" | "Incomplete statement",
        "lead_in_type": "Standard" | "Negative (EXCEPT/NOT)" | "Best answer" | "Most appropriate" | "Most likely",
        "answer_format": "Single best" | "Multiple correct" | "True/false" | "Compound (A+B)",
        "answer_length_pattern": "Uniform" | "Variable" | "Correct longest" | "Correct shortest",
        "distractor_homogeneity": "Homogeneous" | "Heterogeneous",
        "flaw_absolute_terms": true/false,
        "flaw_grammatical_cue": true/false,
        "flaw_implausible_distractor": true/false,
        "flaw_clang_association": true/false,
        "flaw_convergence_vulnerability": true/false,
        "flaw_double_negative": true/false
    }},

### SECTION 2: QBoost Assessment (accuracy + LO alignment)

    "qboost": {{
        "accuracy_score": <0-100>,
        "accuracy_grade": "<A/B/C/D/F>",
        "accuracy_issues": ["<issue 1>", "<issue 2>"],
        "lo_score": <0-100>,
        "lo_grade": "<A/B/C/D/F>",
        "lo_assessment": "<1-2 sentence assessment of LO alignment>",
        "lo_suggestions": ["<suggestion 1>"],
        "suggestions": ["<overall improvement suggestion 1>", "<suggestion 2>"]
    }}
}}

## Scoring Guidelines

**Accuracy (0-100):**
- 90-100 (A): Correct answer is factually accurate, distractors are plausible
- 80-89 (B): Minor issues but fundamentally sound
- 65-79 (C): Some accuracy concerns
- 50-64 (D): Significant accuracy issues
- 0-49 (F): Major factual errors

**LO Alignment (0-100):**
- 90-100 (A): Question directly measures the learning objective
- 80-89 (B): Strong alignment with objective
- 65-79 (C): Moderate alignment
- 50-64 (D): Weak alignment
- 0-49 (F): Poor alignment

Return ONLY valid JSON, no additional text."""


class QSuiteAnalyzer:
    """
    Q-Suite combined analysis service.

    Supports configurable analysis with checkboxes:
    - QCore: Always on (tagging + scoring)
    - QPredict: Optional (find similar questions → analyze performance → predict)
    - QBoost: Optional (LLM accuracy + LO alignment)
    """

    def __init__(
        self,
        client=None,
        model: str = "gpt",
    ):
        """
        Initialize Q-Suite analyzer.

        Args:
            client: OpenRouter client instance
            model: Which model to use ("gpt", "claude", "gemini")
        """
        self.client = client
        self.model = model

        if client is None:
            try:
                from ..taggers.openrouter_client import get_openrouter_client
                self.client = get_openrouter_client()
            except Exception as e:
                logger.warning(f"Could not initialize OpenRouter client: {e}")

    # Common clinical trial name patterns
    TRIAL_PATTERNS = [
        r'\b(CHECKMATE[-\s]?\d+)',
        r'\b(KEYNOTE[-\s]?\d+)',
        r'\b(DESTINY[-\s]?\w+[-\s]?\d*)',
        r'\b(COLUMBUS)',
        r'\b(BEACON)',
        r'\b(POLO)',
        r'\b(MONALEESA[-\s]?\d+)',
        r'\b(PALOMA[-\s]?\d+)',
        r'\b(MONARCH[-\s]?\d+)',
        r'\b(IMpower\d+)',
        r'\b(PACIFIC)',
        r'\b(ADAURA)',
        r'\b(POSEIDON)',
        r'\b(HIMALAYA)',
        r'\b(TOPAZ[-\s]?\d+)',
        r'\b(FLAURA\d*)',
        r'\b(LIBRETTO[-\s]?\d+)',
        r'\b(GEOMETRY[-\s]?\w+[-\s]?\d*)',
        r'\b(CodeBreaK[-\s]?\d+)',
        r'\b(KRYSTAL[-\s]?\d+)',
        r'\b(ASCENT)',
        r'\b(TROPICS[-\s]?\d+)',
        r'\b(DREAMM[-\s]?\d+)',
        r'\b(CARTITUDE[-\s]?\d+)',
        r'\b(MAIA)',
        r'\b(CASSIOPEIA)',
        r'\b(GRIFFIN)',
        r'\b(BOSTON)',
    ]

    def _extract_trial_names(self, text: str) -> list[str]:
        """Extract clinical trial names from text."""
        trials = []
        for pattern in self.TRIAL_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            trials.extend(matches)
        return list(set(trials))  # Deduplicate

    def _mentions_recent_data(self, text: str) -> bool:
        """Check if text mentions recent/updated data that may need verification."""
        recent_patterns = [
            r'recent\s+(data|analysis|results|update)',
            r'updated\s+(analysis|results|data)',
            r'(2024|2025)\s+(data|results|update)',
            r'latest\s+(data|analysis|results)',
            r'primary\s+(analysis|endpoint)',
            r'overall\s+survival',
            r'OS\s+(benefit|improvement|data)',
            r'statistically\s+significant',
        ]
        for pattern in recent_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    async def _fact_check_with_web_search(
        self,
        question_stem: str,
        correct_answer: str,
        trial_names: list[str],
        disease_state: str = "",
    ) -> WebSearchResult:
        """
        Use Perplexity Sonar to fact-check clinical trial claims.

        Args:
            question_stem: The question text
            correct_answer: The correct answer text
            trial_names: List of trial names detected
            disease_state: Disease context if known

        Returns:
            WebSearchResult with verification data
        """
        if not trial_names:
            return WebSearchResult(search_performed=False)

        # Build search query
        trial = trial_names[0]  # Focus on first trial mentioned
        search_query = f"{trial} clinical trial latest results overall survival efficacy 2024 2025"

        try:
            # Call Perplexity Sonar for web search
            messages = [
                {
                    "role": "system",
                    "content": """You are a clinical trial fact-checker. Search for the latest published results for the specified trial and verify claims.

Return a JSON response with:
{
    "trial_name": "CHECKMATE-816",
    "latest_data_date": "2025-01",
    "key_findings": ["Finding 1", "Finding 2"],
    "claim_verified": true/false,
    "verification_note": "Brief explanation of verification result",
    "sources": ["Source 1", "Source 2"]
}"""
                },
                {
                    "role": "user",
                    "content": f"""Search for the latest results of the {trial} clinical trial.

Question context: {question_stem[:500]}
Correct answer being verified: {correct_answer}
Disease: {disease_state}

Find the most recent published data and verify if the correct answer aligns with current evidence."""
                }
            ]

            response = await self.client.generate(
                model="search",
                messages=messages,
                web_search=True,
            )

            content = response.get("content", "{}")
            search_cost = response.get("cost", 0.0)

            # Parse JSON response
            import json
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            try:
                result_data = json.loads(content.strip())
            except json.JSONDecodeError:
                # If JSON parsing fails, extract key info from text
                result_data = {
                    "key_findings": [content[:200]],
                    "verification_note": "Web search completed but response not in expected format",
                    "claim_verified": None,
                }

            # Determine accuracy adjustment
            claim_verified = result_data.get("claim_verified")
            if claim_verified is True:
                accuracy_adjustment = 5  # Boost score if web confirms accuracy
                verification_note = f"✓ Web verified: {result_data.get('verification_note', 'Answer confirmed by current evidence')}"
            elif claim_verified is False:
                accuracy_adjustment = -15  # Significant penalty if web contradicts
                verification_note = f"⚠ Web check: {result_data.get('verification_note', 'Answer may conflict with current evidence')}"
            else:
                accuracy_adjustment = 0
                verification_note = f"○ Web search: {result_data.get('verification_note', 'Inconclusive - manual review recommended')}"

            return WebSearchResult(
                search_performed=True,
                search_query=search_query,
                trial_name=trial,
                key_findings=result_data.get("key_findings", []),
                sources=result_data.get("sources", []),
                accuracy_adjustment=accuracy_adjustment,
                verification_note=verification_note,
            )

        except Exception as e:
            logger.warning(f"Web search fact-check failed: {e}")
            return WebSearchResult(
                search_performed=True,
                search_query=search_query,
                trial_name=trial,
                verification_note=f"Web search failed: {str(e)}",
            )

    async def _run_combined_analysis(
        self,
        question: ParsedQuestion,
        include_qboost: bool = True,
        model_override: str = None,
    ) -> tuple[dict, Optional[QBoostAssessment], str, float]:
        """
        Run combined LLM call for QCore tags + QBoost assessment.

        Args:
            question: The parsed question to analyze
            include_qboost: Whether to include QBoost assessment
            model_override: Override the model to use (for Quorum mode)

        Returns:
            Tuple of (tags dict, QBoost assessment or None, model used, api_cost)
        """
        # Use override model if provided (for Quorum mode), otherwise use instance model
        model_to_use = model_override or self.model

        # Format options
        options_text = "\n".join(question.options)

        # Add LO section if available
        lo_section = ""
        if question.learning_objective and include_qboost:
            lo_section = f"""
## Learning Objective
{question.learning_objective}
"""

        # Build prompt
        prompt = QSUITE_COMBINED_PROMPT.format(
            question_stem=question.question_stem,
            options=options_text,
            correct_answer=f"{question.correct_answer}. {question.correct_answer_text}",
            lo_section=lo_section,
        )

        messages = [
            {"role": "system", "content": "You are a medical education quality analyst. Return only valid JSON."},
            {"role": "user", "content": prompt},
        ]

        try:
            response = await self.client.generate(
                messages=messages,
                model=model_to_use,
            )
            content = response.get("content", "{}")
            api_cost = response.get("cost", 0.0)  # Actual cost from OpenRouter

            # Parse JSON from response
            import json
            import re

            # Clean markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            result = json.loads(content.strip())
            model_name = response.get("model", self.model)

            tags = result.get("tags", {})

            qboost_data = result.get("qboost", {})
            qboost = None
            if include_qboost and qboost_data:
                qboost = QBoostAssessment(
                    accuracy_score=qboost_data.get("accuracy_score", 0),
                    accuracy_grade=qboost_data.get("accuracy_grade", "N/A"),
                    accuracy_issues=qboost_data.get("accuracy_issues", []),
                    lo_score=qboost_data.get("lo_score", 0),
                    lo_grade=qboost_data.get("lo_grade", "N/A"),
                    lo_assessment=qboost_data.get("lo_assessment", ""),
                    lo_suggestions=qboost_data.get("lo_suggestions", []),
                    suggestions=qboost_data.get("suggestions", []),
                )

                # Check if web search fact-checking is needed
                full_text = f"{question.question_stem} {question.correct_answer_text}"
                trial_names = self._extract_trial_names(full_text)
                needs_verification = bool(trial_names) or self._mentions_recent_data(full_text)

                # Debug logging for web search triggering
                logger.info(f"Q{question.question_number} web search check: trials={trial_names}, needs_verification={needs_verification}")
                if full_text and ('CHECKMATE' in full_text.upper() or 'KEYNOTE' in full_text.upper()):
                    logger.info(f"Q{question.question_number} contains trial keyword but extracted: {trial_names}")

                if needs_verification and trial_names:
                    logger.info(f"Q{question.question_number} triggering web search for: {trial_names}")
                    web_result = await self._fact_check_with_web_search(
                        question_stem=question.question_stem,
                        correct_answer=question.correct_answer_text,
                        trial_names=trial_names,
                        disease_state=tags.get("disease_state", ""),
                    )
                    qboost.web_search = web_result

                    # Apply accuracy adjustment from web search
                    if web_result.accuracy_adjustment != 0:
                        original_score = qboost.accuracy_score
                        qboost.accuracy_score = max(0, min(100, qboost.accuracy_score + web_result.accuracy_adjustment))
                        logger.info(f"Accuracy adjusted: {original_score} → {qboost.accuracy_score} (web: {web_result.accuracy_adjustment:+d})")

                        # Add web verification to issues list
                        if web_result.verification_note:
                            qboost.accuracy_issues.insert(0, web_result.verification_note)

                    # Add search cost to total
                    api_cost += web_result.search_performed and 0.01 or 0  # ~$0.01 per search

            logger.info(f"Q{question.question_number} [{model_name}] completed with cost=${api_cost:.4f}")
            return tags, qboost, model_name, api_cost

        except Exception as e:
            logger.error(f"Error in combined analysis for Q{question.question_number}: {e}")
            return {}, None, self.model, 0.0

    async def _run_quorum_analysis(
        self,
        question: ParsedQuestion,
        include_qboost: bool = True,
    ) -> tuple[QuorumResult, float]:
        """
        Run Quorum analysis - all 3 models in parallel.

        Returns:
            Tuple of (QuorumResult with aggregated tags and individual QBoost assessments, total_cost)
        """
        # Create tasks for all 3 models in parallel using model_override
        models = ['gpt', 'claude', 'gemini']
        tasks = [
            self._run_combined_analysis(question, include_qboost=include_qboost, model_override=model)
            for model in models
        ]

        # Run all 3 models in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Parse results (now includes cost as 4th element)
        gpt_tags, gpt_qboost, _, gpt_cost = results[0] if not isinstance(results[0], Exception) else ({}, None, 'gpt', 0.0)
        claude_tags, claude_qboost, _, claude_cost = results[1] if not isinstance(results[1], Exception) else ({}, None, 'claude', 0.0)
        gemini_tags, gemini_qboost, _, gemini_cost = results[2] if not isinstance(results[2], Exception) else ({}, None, 'gemini', 0.0)
        total_cost = gpt_cost + claude_cost + gemini_cost

        # Set model names
        if gpt_qboost:
            gpt_qboost.model_name = 'GPT-5.2'
        if claude_qboost:
            claude_qboost.model_name = 'Claude Opus'
        if gemini_qboost:
            gemini_qboost.model_name = 'Gemini 2.5'

        # Aggregate tags using majority voting
        aggregated_tags = self._aggregate_tags([gpt_tags, claude_tags, gemini_tags])

        # Calculate averaged QBoost scores
        accuracy_scores = [qb.accuracy_score for qb in [gpt_qboost, claude_qboost, gemini_qboost] if qb and qb.accuracy_score > 0]
        lo_scores = [qb.lo_score for qb in [gpt_qboost, claude_qboost, gemini_qboost] if qb and qb.lo_score > 0]
        avg_accuracy = round(sum(accuracy_scores) / len(accuracy_scores), 1) if accuracy_scores else 0.0
        avg_lo = round(sum(lo_scores) / len(lo_scores), 1) if lo_scores else 0.0

        return QuorumResult(
            aggregated_tags=aggregated_tags,
            gpt_tags=gpt_tags,
            claude_tags=claude_tags,
            gemini_tags=gemini_tags,
            gpt_qboost=gpt_qboost,
            claude_qboost=claude_qboost,
            gemini_qboost=gemini_qboost,
            avg_accuracy_score=avg_accuracy,
            avg_lo_score=avg_lo,
        ), total_cost

    def _aggregate_tags(self, tag_dicts: list[dict]) -> dict:
        """
        Aggregate tags from multiple models using majority voting.

        For boolean fields: majority wins
        For string fields: take most common value (or first non-empty)
        """
        if not tag_dicts:
            return {}

        aggregated = {}
        all_keys = set()
        for td in tag_dicts:
            all_keys.update(td.keys())

        for key in all_keys:
            values = [td.get(key) for td in tag_dicts if td.get(key) is not None]

            if not values:
                aggregated[key] = None
                continue

            # For boolean fields (flaw_*)
            if key.startswith('flaw_'):
                # Count True values
                true_count = sum(1 for v in values if v is True or str(v).lower() == 'true')
                aggregated[key] = true_count >= 2  # Majority wins

            else:
                # For string/other fields: take most common value
                from collections import Counter
                value_counts = Counter(str(v) for v in values if v)
                if value_counts:
                    most_common = value_counts.most_common(1)[0][0]
                    aggregated[key] = most_common
                else:
                    aggregated[key] = values[0] if values else None

        return aggregated

    async def analyze_question(
        self,
        question: ParsedQuestion,
        include_qboost: bool = True,
        include_qpredict: bool = False,
    ) -> QuestionAnalysis:
        """
        Analyze a single question with selected tools.

        Args:
            question: Parsed question from document
            include_qboost: Whether to include LLM accuracy + LO assessment
            include_qpredict: Whether to predict performance (find similar Qs, analyze, predict)

        Returns:
            Complete question analysis
        """
        is_quorum = self.model == 'quorum'
        quorum_result = None
        qboost = None
        model_used = self.model
        question_cost = 0.0

        if is_quorum:
            # Run Quorum analysis (all 3 models in parallel)
            quorum_result, question_cost = await self._run_quorum_analysis(question, include_qboost=include_qboost)
            tags = quorum_result.aggregated_tags
            model_used = "Quorum (GPT + Claude + Gemini)"

            # Calculate individual QCore scores for each model's tags
            def get_cme_level(t):
                cme_tag = t.get("cme_outcome_level", "")
                return 4 if "4" in str(cme_tag) or "competence" in str(cme_tag).lower() else 3

            gpt_cme = get_cme_level(quorum_result.gpt_tags)
            claude_cme = get_cme_level(quorum_result.claude_tags)
            gemini_cme = get_cme_level(quorum_result.gemini_tags)

            gpt_score = calculate_qcore_score(quorum_result.gpt_tags, cme_level=gpt_cme)
            claude_score = calculate_qcore_score(quorum_result.claude_tags, cme_level=claude_cme)
            gemini_score = calculate_qcore_score(quorum_result.gemini_tags, cme_level=gemini_cme)

            quorum_result.gpt_qcore_score = gpt_score["total_score"]
            quorum_result.claude_qcore_score = claude_score["total_score"]
            quorum_result.gemini_qcore_score = gemini_score["total_score"]
            quorum_result.avg_qcore_score = round(
                (gpt_score["total_score"] + claude_score["total_score"] + gemini_score["total_score"]) / 3, 1
            )
        else:
            # Run single-model analysis
            tags, qboost, model_used, question_cost = await self._run_combined_analysis(
                question,
                include_qboost=include_qboost
            )

        # Determine CME level from tags
        cme_level_tag = tags.get("cme_outcome_level", "")
        if "4" in str(cme_level_tag) or "competence" in str(cme_level_tag).lower():
            cme_level = 4
            cme_level_str = "Competence"
        else:
            cme_level = 3
            cme_level_str = "Knowledge"

        # Add computed fields
        tags["answer_option_count"] = len(question.options)
        tags["correct_answer_position"] = question.correct_answer

        # Calculate QCore score (uses aggregated tags for Quorum, single tags otherwise)
        qcore_result = calculate_qcore_score(tags, cme_level=cme_level)

        # For Quorum mode, use the averaged score and derive grade from it
        if is_quorum:
            final_qcore_score = quorum_result.avg_qcore_score
            # Derive grade from averaged score (same thresholds as qcore_scorer)
            if final_qcore_score >= 90:
                final_grade = "A"
            elif final_qcore_score >= 80:
                final_grade = "B"
            elif final_qcore_score >= 70:
                final_grade = "C"
            else:
                final_grade = "D"
        else:
            final_qcore_score = qcore_result["total_score"]
            final_grade = qcore_result["grade"]

        # QPredict: Find similar questions (placeholder - needs embeddings infrastructure)
        similar_questions = []
        if include_qpredict:
            # TODO: Implement similarity search when embeddings are available
            pass

        return QuestionAnalysis(
            question_number=question.question_number,
            question_stem=question.question_stem,
            options=question.options,
            correct_answer=question.correct_answer,
            learning_objective=question.learning_objective,
            tags=tags,
            qcore_score=final_qcore_score,
            qcore_grade=final_grade,
            qcore_breakdown=qcore_result["breakdown"],
            ready_for_deployment=qcore_result["ready_for_deployment"],
            qboost=qboost,
            quorum=quorum_result,
            is_quorum=is_quorum,
            similar_questions=similar_questions,
            cme_level=cme_level_str,
            tagging_model=model_used,
            analysis_timestamp=datetime.now().isoformat(),
            api_cost=question_cost,
        )

    async def analyze_document(
        self,
        parsed_doc: ParsedDocument,
        include_qboost: bool = True,
        include_qpredict: bool = False,
        parallel: bool = True,
    ) -> DocumentAnalysis:
        """
        Analyze all questions in a parsed document.

        Args:
            parsed_doc: Parsed document from outcomes_doc_parser
            include_qboost: Whether to include LLM accuracy + LO assessment
            include_qpredict: Whether to find similar questions
            parallel: Whether to analyze questions in parallel

        Returns:
            Complete document analysis
        """
        questions_analyzed = []

        if parallel:
            tasks = [
                self.analyze_question(q, include_qboost=include_qboost, include_qpredict=include_qpredict)
                for q in parsed_doc.questions
            ]
            questions_analyzed = await asyncio.gather(*tasks)
        else:
            for q in parsed_doc.questions:
                analysis = await self.analyze_question(
                    q, include_qboost=include_qboost, include_qpredict=include_qpredict
                )
                questions_analyzed.append(analysis)

        # Calculate summary statistics
        total = len(questions_analyzed)
        if total > 0:
            avg_qcore = sum(q.qcore_score for q in questions_analyzed) / total

            # QBoost/Quorum averages (check both single-model and Quorum mode)
            qboost_accuracy_scores = []
            qboost_lo_scores = []
            for q in questions_analyzed:
                # Check single-model QBoost first
                if q.qboost and q.qboost.accuracy_score > 0:
                    qboost_accuracy_scores.append(q.qboost.accuracy_score)
                # Check Quorum mode (3-model aggregated)
                elif q.is_quorum and q.quorum and q.quorum.avg_accuracy_score > 0:
                    qboost_accuracy_scores.append(q.quorum.avg_accuracy_score)

                # Same for LO scores
                if q.qboost and q.qboost.lo_score > 0:
                    qboost_lo_scores.append(q.qboost.lo_score)
                elif q.is_quorum and q.quorum and q.quorum.avg_lo_score > 0:
                    qboost_lo_scores.append(q.quorum.avg_lo_score)

            avg_qboost_accuracy = sum(qboost_accuracy_scores) / len(qboost_accuracy_scores) if qboost_accuracy_scores else 0
            avg_qboost_lo = sum(qboost_lo_scores) / len(qboost_lo_scores) if qboost_lo_scores else 0

            ready_count = sum(1 for q in questions_analyzed if q.ready_for_deployment)

            # Grade distribution
            grade_dist = {"A": 0, "B": 0, "C": 0, "D": 0}  # No F grade
            for q in questions_analyzed:
                if q.qcore_grade in grade_dist:
                    grade_dist[q.qcore_grade] += 1

            # Calculate actual total cost from all questions
            actual_cost = sum(q.api_cost for q in questions_analyzed)
        else:
            avg_qcore = 0
            avg_qboost_accuracy = 0
            avg_qboost_lo = 0
            ready_count = 0
            grade_dist = {}
            actual_cost = 0.0

        return DocumentAnalysis(
            filename=parsed_doc.filename,
            activity_title=parsed_doc.activity_title,
            analysis_timestamp=datetime.now().isoformat(),
            total_questions=total,
            questions=list(questions_analyzed),
            avg_qcore_score=round(avg_qcore, 1),
            avg_qboost_accuracy=round(avg_qboost_accuracy, 1),
            avg_qboost_lo=round(avg_qboost_lo, 1),
            grade_distribution=grade_dist,
            ready_count=ready_count,
            warnings=parsed_doc.parse_warnings,
            options_used={
                "qcore": True,
                "qboost": include_qboost,
                "qpredict": include_qpredict,
            },
            total_cost=actual_cost,
            model_used=self.model,
        )


# Convenience function
async def analyze_outcomes_document(
    file_bytes: bytes,
    filename: str,
    model: str = "gpt",
    include_qboost: bool = True,
    include_qpredict: bool = False,
) -> DocumentAnalysis:
    """
    Convenience function to analyze an uploaded outcomes document.

    Args:
        file_bytes: Document content as bytes
        filename: Original filename
        model: LLM model to use
        include_qboost: Whether to include LLM accuracy + LO assessment
        include_qpredict: Whether to find similar questions

    Returns:
        Complete document analysis
    """
    from .outcomes_doc_parser import parse_outcomes_document_from_bytes

    parsed_doc = parse_outcomes_document_from_bytes(file_bytes, filename)
    analyzer = QSuiteAnalyzer(model=model)
    return await analyzer.analyze_document(
        parsed_doc,
        include_qboost=include_qboost,
        include_qpredict=include_qpredict,
    )
