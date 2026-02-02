"""
QBoost Analyzer - Question Quality Analysis Service.

Orchestrates the full QBoost analysis workflow:
1. Parse uploaded document (Word format)
2. Run questions through LLM tagging pipeline
3. Calculate QBoost scores
4. Assess learning objective alignment
5. Return comprehensive analysis results
"""
import asyncio
import logging
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime

from .outcomes_doc_parser import ParsedQuestion, ParsedDocument
from ..preprocessing.qboost_scorer import calculate_qboost_score
from ..taggers.openrouter_client import OpenRouterClient, get_openrouter_client

logger = logging.getLogger(__name__)


@dataclass
class LearningObjectiveAlignment:
    """Assessment of how well a question aligns with its learning objective."""
    score: int  # 0-100
    grade: str  # A, B, C, D, F
    assessment: str  # Brief explanation
    suggestions: list[str] = field(default_factory=list)


@dataclass
class QuestionAnalysis:
    """Complete analysis of a single question."""
    question_number: int
    question_stem: str
    options: list[str]
    correct_answer: str
    learning_objective: str

    # LLM-generated tags
    tags: dict = field(default_factory=dict)
    tagging_model: str = ""

    # QBoost score
    qboost_score: float = 0.0
    qboost_grade: str = "F"
    qboost_breakdown: dict = field(default_factory=dict)
    ready_for_deployment: bool = False

    # Learning objective alignment
    lo_alignment: Optional[LearningObjectiveAlignment] = None

    # Metadata
    cme_level: str = "Knowledge"
    analysis_timestamp: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "question_number": self.question_number,
            "question_stem": self.question_stem,
            "options": self.options,
            "correct_answer": self.correct_answer,
            "learning_objective": self.learning_objective,
            "tags": self.tags,
            "tagging_model": self.tagging_model,
            "qboost_score": self.qboost_score,
            "qboost_grade": self.qboost_grade,
            "qboost_breakdown": self.qboost_breakdown,
            "ready_for_deployment": self.ready_for_deployment,
            "lo_alignment": {
                "score": self.lo_alignment.score,
                "grade": self.lo_alignment.grade,
                "assessment": self.lo_alignment.assessment,
                "suggestions": self.lo_alignment.suggestions,
            } if self.lo_alignment else None,
            "cme_level": self.cme_level,
            "analysis_timestamp": self.analysis_timestamp,
        }


@dataclass
class DocumentAnalysis:
    """Complete analysis of an uploaded document."""
    filename: str
    activity_title: str
    analysis_timestamp: str
    total_questions: int
    questions: list[QuestionAnalysis]

    # Summary statistics
    avg_qboost_score: float = 0.0
    avg_lo_alignment: float = 0.0
    grade_distribution: dict = field(default_factory=dict)
    ready_count: int = 0
    warnings: list[str] = field(default_factory=list)

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
            "avg_qboost_score": self.avg_qboost_score,
            "avg_lo_alignment": self.avg_lo_alignment,
            "grade_distribution": self.grade_distribution,
            "ready_count": self.ready_count,
            "ready_percentage": round(self.ready_count / self.total_questions * 100, 1) if self.total_questions > 0 else 0,
            "warnings": self.warnings,
            "total_cost": round(self.total_cost, 4),
            "model_used": self.model_used,
            "questions": [q.to_dict() for q in self.questions],
        }


# Prompt for LLM-based question tagging (focused on quality fields)
QBOOST_TAGGING_PROMPT = """You are an expert medical education quality analyst. Analyze this CME question and provide tags for quality assessment.

## Question
Stem: {question_stem}

Answer Options:
{options}

Correct Answer: {correct_answer}

## Instructions
Analyze this question and return a JSON object with the following fields:

### Content Tags
- topic: Educational topic (Treatment selection, Clinical efficacy, Safety profile, AE management, Disease overview, Diagnostic workup, Emerging therapies, Guidelines/evidence, Patient communication, Biomarker testing)
- disease_state: The cancer type if oncology (e.g., "NSCLC", "Breast cancer", "Multiple myeloma")

### Question Quality Tags (Group F)
- cme_outcome_level: "3 - Knowledge" for recall/recognition OR "4 - Competence" for application/decision
- data_response_type: "Qualitative", "Comparative", "Boolean", or "Numeric" (avoid numeric)
- stem_type: "Clinical vignette", "Case series", "Direct question", or "Incomplete statement"
- lead_in_type: "Standard", "Negative (EXCEPT/NOT)", "Best answer", "Most appropriate", or "Most likely"
- answer_format: "Single best", "Multiple correct", "True/false", or "Compound (A+B)"
- answer_length_pattern: "Uniform" (options similar length), "Variable", "Correct longest", or "Correct shortest"
- distractor_homogeneity: "Homogeneous" (all options same type) or "Heterogeneous" (mixed types)

### Item Writing Flaws (true/false)
- flaw_absolute_terms: true if options contain "always", "never", "all", "none"
- flaw_grammatical_cue: true if grammar reveals the answer (article agreement, verb form, etc.)
- flaw_implausible_distractor: true if any distractor is obviously wrong
- flaw_clang_association: true if words in stem match words in correct answer
- flaw_convergence_vulnerability: true if correct answer can be determined by elimination
- flaw_double_negative: true if stem or options use double negatives

Return ONLY valid JSON, no explanation.

Example:
{{
    "topic": "Treatment selection",
    "disease_state": "NSCLC",
    "cme_outcome_level": "4 - Competence",
    "data_response_type": "Qualitative",
    "stem_type": "Clinical vignette",
    "lead_in_type": "Best answer",
    "answer_format": "Single best",
    "answer_length_pattern": "Uniform",
    "distractor_homogeneity": "Homogeneous",
    "flaw_absolute_terms": false,
    "flaw_grammatical_cue": false,
    "flaw_implausible_distractor": false,
    "flaw_clang_association": false,
    "flaw_convergence_vulnerability": false,
    "flaw_double_negative": false
}}"""


# Prompt for learning objective alignment assessment
LO_ALIGNMENT_PROMPT = """You are an expert in medical education assessment. Evaluate how well this question aligns with its stated learning objective.

## Learning Objective
{learning_objective}

## Question
{question_stem}

Answer Options:
{options}

Correct Answer: {correct_answer}

## Instructions
Assess alignment on a 0-100 scale:
- 90-100 (A): Perfect alignment - question directly measures the objective
- 80-89 (B): Strong alignment - question clearly relates to objective
- 65-79 (C): Moderate alignment - question partially addresses objective
- 50-64 (D): Weak alignment - question tangentially related
- 0-49 (F): Poor alignment - question doesn't measure the objective

Return a JSON object:
{{
    "score": <0-100>,
    "grade": "<A/B/C/D/F>",
    "assessment": "<1-2 sentence explanation>",
    "suggestions": ["<improvement suggestion 1>", "<improvement suggestion 2>"]
}}

Return ONLY valid JSON, no additional text."""


class QBoostAnalyzer:
    """
    QBoost analysis service for question quality assessment.

    Supports two modes:
    1. Single model (cost-effective): Uses GPT-5.2 only (~$0.035/question)
    2. Multi-model voting (accurate): Uses GPT + Claude + Gemini (~$0.13/question)
    """

    def __init__(
        self,
        client: Optional[OpenRouterClient] = None,
        use_single_model: bool = True,
        model: str = "gpt",
    ):
        """
        Initialize QBoost analyzer.

        Args:
            client: OpenRouter client instance
            use_single_model: If True, use single model for cost savings
            model: Which model to use ("gpt", "claude", "gemini")
        """
        self.client = client or get_openrouter_client()
        self.use_single_model = use_single_model
        self.model = model

    async def _tag_question(self, question: ParsedQuestion) -> tuple[dict, str]:
        """
        Tag a question using LLM.

        Returns:
            Tuple of (tags dict, model used)
        """
        # Format options
        options_text = "\n".join(question.options)

        # Build prompt
        prompt = QBOOST_TAGGING_PROMPT.format(
            question_stem=question.question_stem,
            options=options_text,
            correct_answer=f"{question.correct_answer}. {question.correct_answer_text}",
        )

        messages = [
            {"role": "system", "content": "You are a medical education quality analyst. Return only valid JSON."},
            {"role": "user", "content": prompt},
        ]

        try:
            response = await self.client.generate(
                messages=messages,
                model=self.model,
            )
            content = response.get("content", "{}")

            # Parse JSON from response
            import json
            import re

            # Clean markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            tags = json.loads(content.strip())
            model_name = response.get("model", self.model)

            return tags, model_name

        except Exception as e:
            logger.error(f"Error tagging question {question.question_number}: {e}")
            return {}, self.model

    async def _assess_lo_alignment(
        self,
        question: ParsedQuestion
    ) -> LearningObjectiveAlignment:
        """Assess how well the question aligns with its learning objective."""
        if not question.learning_objective:
            return LearningObjectiveAlignment(
                score=0,
                grade="N/A",
                assessment="No learning objective provided",
                suggestions=["Add a learning objective for this question"],
            )

        options_text = "\n".join(question.options)

        prompt = LO_ALIGNMENT_PROMPT.format(
            learning_objective=question.learning_objective,
            question_stem=question.question_stem,
            options=options_text,
            correct_answer=f"{question.correct_answer}. {question.correct_answer_text}",
        )

        messages = [
            {"role": "system", "content": "You are a medical education assessment expert. Return only valid JSON."},
            {"role": "user", "content": prompt},
        ]

        try:
            response = await self.client.generate(
                messages=messages,
                model=self.model,
            )
            content = response.get("content", "{}")

            # Parse JSON
            import json
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            result = json.loads(content.strip())

            return LearningObjectiveAlignment(
                score=result.get("score", 0),
                grade=result.get("grade", "F"),
                assessment=result.get("assessment", ""),
                suggestions=result.get("suggestions", []),
            )

        except Exception as e:
            logger.error(f"Error assessing LO alignment for Q{question.question_number}: {e}")
            return LearningObjectiveAlignment(
                score=0,
                grade="F",
                assessment=f"Error during assessment: {str(e)}",
                suggestions=[],
            )

    async def analyze_question(self, question: ParsedQuestion) -> QuestionAnalysis:
        """
        Analyze a single question.

        Args:
            question: Parsed question from document

        Returns:
            Complete question analysis
        """
        # Tag the question
        tags, model_used = await self._tag_question(question)

        # Determine CME level from tags or document
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

        # Calculate QBoost score
        qboost_result = calculate_qboost_score(tags, cme_level=cme_level)

        # Assess learning objective alignment
        lo_alignment = await self._assess_lo_alignment(question)

        return QuestionAnalysis(
            question_number=question.question_number,
            question_stem=question.question_stem,
            options=question.options,
            correct_answer=question.correct_answer,
            learning_objective=question.learning_objective,
            tags=tags,
            tagging_model=model_used,
            qboost_score=qboost_result["total_score"],
            qboost_grade=qboost_result["grade"],
            qboost_breakdown=qboost_result["breakdown"],
            ready_for_deployment=qboost_result["ready_for_deployment"],
            lo_alignment=lo_alignment,
            cme_level=cme_level_str,
            analysis_timestamp=datetime.now().isoformat(),
        )

    async def analyze_document(
        self,
        parsed_doc: ParsedDocument,
        parallel: bool = True,
    ) -> DocumentAnalysis:
        """
        Analyze all questions in a parsed document.

        Args:
            parsed_doc: Parsed document from outcomes_doc_parser
            parallel: Whether to analyze questions in parallel

        Returns:
            Complete document analysis
        """
        questions_analyzed = []

        if parallel:
            # Analyze all questions in parallel
            tasks = [self.analyze_question(q) for q in parsed_doc.questions]
            questions_analyzed = await asyncio.gather(*tasks)
        else:
            # Analyze sequentially
            for q in parsed_doc.questions:
                analysis = await self.analyze_question(q)
                questions_analyzed.append(analysis)

        # Calculate summary statistics
        total = len(questions_analyzed)
        if total > 0:
            avg_qboost = sum(q.qboost_score for q in questions_analyzed) / total
            lo_scores = [q.lo_alignment.score for q in questions_analyzed if q.lo_alignment and q.lo_alignment.score > 0]
            avg_lo = sum(lo_scores) / len(lo_scores) if lo_scores else 0
            ready_count = sum(1 for q in questions_analyzed if q.ready_for_deployment)

            # Grade distribution
            grade_dist = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
            for q in questions_analyzed:
                if q.qboost_grade in grade_dist:
                    grade_dist[q.qboost_grade] += 1
        else:
            avg_qboost = 0
            avg_lo = 0
            ready_count = 0
            grade_dist = {}

        # Estimate cost (GPT-5.2 single model)
        # Input: ~1500 tokens/question, Output: ~500 tokens/question
        # $1.75/M input, $14/M output
        # Per question: (1500 * 1.75 + 500 * 14) / 1_000_000 = ~$0.01
        # Two LLM calls per question (tagging + LO alignment) = ~$0.02
        estimated_cost = total * 0.02

        return DocumentAnalysis(
            filename=parsed_doc.filename,
            activity_title=parsed_doc.activity_title,
            analysis_timestamp=datetime.now().isoformat(),
            total_questions=total,
            questions=list(questions_analyzed),
            avg_qboost_score=round(avg_qboost, 1),
            avg_lo_alignment=round(avg_lo, 1),
            grade_distribution=grade_dist,
            ready_count=ready_count,
            warnings=parsed_doc.parse_warnings,
            total_cost=estimated_cost,
            model_used=self.model,
        )


# Convenience function for quick analysis
async def analyze_outcomes_document(
    file_bytes: bytes,
    filename: str,
    model: str = "gpt",
) -> DocumentAnalysis:
    """
    Convenience function to analyze an uploaded outcomes document.

    Args:
        file_bytes: Document content as bytes
        filename: Original filename

    Returns:
        Complete document analysis
    """
    from .outcomes_doc_parser import parse_outcomes_document_from_bytes

    # Parse document
    parsed_doc = parse_outcomes_document_from_bytes(file_bytes, filename)

    # Analyze
    analyzer = QBoostAnalyzer(model=model)
    return await analyzer.analyze_document(parsed_doc)
