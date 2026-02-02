"""
Q-Suite API endpoints.

Q-Suite includes three tools for question quality analysis:
- QCore: Quality scoring (flaw deductions, structure penalties) - always enabled
- QPredict: Performance prediction (embedding search → similar Q analysis → ML) - optional
- QBoost: LLM accuracy + LO alignment + suggestions - optional

Endpoints:
- Upload: Upload Word document (outcomes template) for combined analysis
- Quick score: Calculate QCore score from tags (no LLM)
- Calibration: Current flaw penalty weights
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks, Form
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from pathlib import Path
from datetime import datetime
import yaml
import logging
import sys
import asyncio
import uuid

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.preprocessing.qcore_scorer import (
    calculate_qcore_score,
    calculate_batch_qcore_scores,
    get_score_distribution,
    QCoreConfig,
)
# Backward compatibility aliases
calculate_qboost_score = calculate_qcore_score
QBoostConfig = QCoreConfig

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/qsuite", tags=["qsuite"])

# Path to calibration config
CONFIG_FILE = PROJECT_ROOT / "config" / "qcore_calibration.yaml"
# Fallback to old names for backward compatibility
if not CONFIG_FILE.exists():
    CONFIG_FILE = PROJECT_ROOT / "config" / "qpulse_calibration.yaml"
if not CONFIG_FILE.exists():
    CONFIG_FILE = PROJECT_ROOT / "config" / "qboost_calibration.yaml"

# In-memory storage for analysis results (simple approach)
# In production, would use database or Redis
_analysis_results: Dict[str, Dict] = {}


# ========== Pydantic Models ==========

class QuickScoreRequest(BaseModel):
    """Request model for quick score endpoint."""
    # Tags for scoring
    flaw_implausible_distractor: Optional[bool] = False
    flaw_grammatical_cue: Optional[bool] = False
    flaw_clang_association: Optional[bool] = False
    flaw_convergence_vulnerability: Optional[bool] = False
    flaw_absolute_terms: Optional[bool] = False
    flaw_double_negative: Optional[bool] = False
    stem_type: Optional[str] = None
    lead_in_type: Optional[str] = None
    answer_format: Optional[str] = None
    answer_length_pattern: Optional[str] = None
    distractor_homogeneity: Optional[str] = None
    answer_option_count: Optional[int] = 4
    cme_outcome_level: Optional[str] = "4 - Competence"


class QuickScoreResponse(BaseModel):
    """Response model for quick score endpoint."""
    total_score: float
    base_score: int
    flaw_deductions: int
    structure_deductions: int
    structure_bonuses: int
    flaw_count: int
    grade: str
    grade_interpretation: str
    cme_level: int
    level_description: str
    ready_for_deployment: bool
    breakdown: Dict[str, Any]


class AnalyzeRequest(BaseModel):
    """Request model for full analysis endpoint."""
    question_stem: str = Field(..., min_length=10)
    option_a: str = Field(..., min_length=1)
    option_b: str = Field(..., min_length=1)
    option_c: str = Field(..., min_length=1)
    option_d: str = Field(..., min_length=1)
    option_e: Optional[str] = None
    correct_answer: str = Field(..., pattern="^[A-E]$")
    disease_hint: Optional[str] = None
    activity_name: Optional[str] = None
    # Pre-tagged quality fields (optional - will be auto-detected if not provided)
    tags: Optional[Dict[str, Any]] = None


class CalibrationResponse(BaseModel):
    """Response model for calibration endpoint."""
    version: str
    calibration_date: str
    calibration_type: str
    questions_analyzed: int
    flaw_penalties: Dict[str, Any]
    structure_deductions: Dict[str, Any]
    structure_bonuses: Dict[str, Any]
    grading_scales: Dict[str, Any]


class BatchScoreRequest(BaseModel):
    """Request model for batch scoring."""
    question_ids: List[int]


class BatchScoreResponse(BaseModel):
    """Response model for batch scoring."""
    scores: List[Dict[str, Any]]
    distribution: Dict[str, Any]


class UploadResponse(BaseModel):
    """Response model for document upload."""
    analysis_id: str
    filename: str
    status: str
    message: str
    question_count: int = 0
    tools_enabled: List[str] = ["QCore"]  # Which Q-Suite tools are enabled


class AnalysisStatusResponse(BaseModel):
    """Response model for analysis status check."""
    analysis_id: str
    status: str  # pending, processing, completed, failed
    progress: int  # 0-100
    message: str
    tools_enabled: List[str] = []  # Which Q-Suite tools were used
    result: Optional[Dict[str, Any]] = None


# ========== Helper Functions ==========

def load_calibration() -> dict:
    """Load calibration config from YAML."""
    if not CONFIG_FILE.exists():
        logger.warning(f"Calibration file not found: {CONFIG_FILE}")
        return {}

    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def extract_cme_level(cme_value: Any) -> int:
    """Extract CME level (3 or 4) from various formats."""
    if cme_value is None:
        return 4  # Default to Level 4

    cme_str = str(cme_value).lower()
    if '3' in cme_str or 'knowledge' in cme_str:
        return 3
    return 4  # Default to Level 4 (Competence)


# ========== API Endpoints ==========

@router.post("/quick-score", response_model=QuickScoreResponse)
async def quick_score(request: QuickScoreRequest):
    """
    Calculate QBoost score from quality tags.

    Fast endpoint - no LLM calls, pure computation.
    Returns quality score (0-100), grade, and detailed breakdown.
    """
    try:
        # Convert request to tags dict
        tags = {
            'flaw_implausible_distractor': request.flaw_implausible_distractor,
            'flaw_grammatical_cue': request.flaw_grammatical_cue,
            'flaw_clang_association': request.flaw_clang_association,
            'flaw_convergence_vulnerability': request.flaw_convergence_vulnerability,
            'flaw_absolute_terms': request.flaw_absolute_terms,
            'flaw_double_negative': request.flaw_double_negative,
            'stem_type': request.stem_type,
            'lead_in_type': request.lead_in_type,
            'answer_format': request.answer_format,
            'answer_length_pattern': request.answer_length_pattern,
            'distractor_homogeneity': request.distractor_homogeneity,
            'answer_option_count': request.answer_option_count,
        }

        # Extract CME level
        cme_level = extract_cme_level(request.cme_outcome_level)

        # Calculate score
        result = calculate_qboost_score(tags, cme_level=cme_level)

        return QuickScoreResponse(**result)

    except Exception as e:
        logger.error(f"Error calculating quick score: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/calibration", response_model=CalibrationResponse)
async def get_calibration():
    """
    Get current QBoost calibration weights.

    Returns expert-default or data-driven penalty weights
    for flaws and structure issues.
    """
    try:
        config = load_calibration()

        if not config:
            # Return defaults from QBoostConfig if no file
            qb_config = QBoostConfig()
            return CalibrationResponse(
                version="1.0.0",
                calibration_date=datetime.now().isoformat(),
                calibration_type="hardcoded_defaults",
                questions_analyzed=0,
                flaw_penalties=qb_config.FLAW_PENALTIES,
                structure_deductions=qb_config.STRUCTURE_DEDUCTIONS,
                structure_bonuses=qb_config.STRUCTURE_BONUSES,
                grading_scales=qb_config.GRADE_THRESHOLDS,
            )

        return CalibrationResponse(
            version=config.get('version', '1.0.0'),
            calibration_date=config.get('calibration_date', ''),
            calibration_type=config.get('calibration_type', 'unknown'),
            questions_analyzed=config.get('questions_analyzed', 0),
            flaw_penalties=config.get('flaw_penalties', {}),
            structure_deductions=config.get('structure_deductions', {}),
            structure_bonuses=config.get('structure_bonuses', {}),
            grading_scales=config.get('grading_scales', {}),
        )

    except Exception as e:
        logger.error(f"Error loading calibration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/score-question/{question_id}")
async def score_question(question_id: int):
    """
    Calculate QBoost score for a question in the database.

    Looks up the question's tags and computes the quality score.
    """
    try:
        # Import database service here to avoid circular imports
        from dashboard.backend.services.database import DatabaseService

        db = DatabaseService()
        question = db.get_question_detail(question_id)

        if not question:
            raise HTTPException(status_code=404, detail=f"Question {question_id} not found")

        tags = question.get('tags', {})
        if not tags:
            raise HTTPException(status_code=400, detail=f"Question {question_id} has no tags")

        # Extract CME level
        cme_level = extract_cme_level(tags.get('cme_outcome_level'))

        # Calculate score
        result = calculate_qboost_score(tags, cme_level=cme_level)
        result['question_id'] = question_id
        result['source_id'] = question.get('source_id')

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error scoring question {question_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_qboost_stats():
    """
    Get QBoost score distribution for all questions in database.

    Returns aggregate statistics across all tagged questions.
    """
    try:
        # Import database service here to avoid circular imports
        from dashboard.backend.services.database import DatabaseService

        db = DatabaseService()

        # Get all questions with tags
        result = db.search_questions(limit=10000)  # Get all
        questions = result.get('questions', [])

        if not questions:
            return {
                'total_questions': 0,
                'scored_questions': 0,
                'distribution': None,
            }

        # Calculate scores for all questions
        scores = []
        for q in questions:
            tags = q.get('tags', {})
            if tags:
                cme_level = extract_cme_level(tags.get('cme_outcome_level'))
                score = calculate_qboost_score(tags, cme_level=cme_level)
                score['question_id'] = q.get('id')
                scores.append(score)

        # Get distribution
        distribution = get_score_distribution(scores)

        return {
            'total_questions': len(questions),
            'scored_questions': len(scores),
            'distribution': distribution,
        }

    except Exception as e:
        logger.error(f"Error getting QBoost stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== QCore Scoring Endpoints ==========

@router.get("/qcore/stats")
async def get_qcore_stats():
    """
    Get QCore scoring statistics for all questions in database.

    Returns grade distribution, average scores, and deployment readiness counts.
    """
    try:
        from dashboard.backend.services.database import DatabaseService
        db = DatabaseService()
        return db.get_qcore_stats()
    except Exception as e:
        logger.error(f"Error getting QCore stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/qcore/score-all")
async def score_all_questions():
    """
    Calculate and store QCore scores for all questions.

    This endpoint calculates scores based on existing quality tags
    (from staged tagging) and stores them in the database.

    Returns counts of scored, skipped, and failed questions.
    """
    try:
        from dashboard.backend.services.database import DatabaseService
        db = DatabaseService()
        result = db.calculate_qcore_for_all_questions()
        return {
            "status": "completed",
            "total": result['total'],
            "scored": result['scored'],
            "skipped": result['skipped'],
            "failed": result['failed'],
        }
    except Exception as e:
        logger.error(f"Error scoring all questions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/qcore/score/{question_id}")
async def score_single_question(question_id: int):
    """
    Calculate and store QCore score for a single question.

    Args:
        question_id: The question ID to score

    Returns:
        Score details including grade and breakdown
    """
    try:
        from dashboard.backend.services.database import DatabaseService
        db = DatabaseService()
        result = db.calculate_qcore_for_question(question_id)
        if not result:
            raise HTTPException(status_code=404, detail=f"Question {question_id} not found or has no tags")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error scoring question {question_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== Document Upload & Analysis Endpoints ==========

def _check_openrouter_api_key() -> bool:
    """Check if OpenRouter API key is configured."""
    import os
    key = os.environ.get('OPENROUTER_API_KEY', '')
    return bool(key and key.strip())


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    model: str = Form(default="gpt"),
    include_qboost: bool = Form(default=True),
    include_qpredict: bool = Form(default=False),
):
    """
    Upload an outcomes document for Q-Suite analysis.

    Accepts Word documents (.docx) in the PER Outcomes template format.
    Returns an analysis_id to retrieve results.

    The Q-Suite includes three tools (checkboxes):
    - QCore: Quality scoring (always enabled)
    - QBoost: LLM accuracy + LO alignment (optional, default ON)
    - QPredict: Similar question finder (optional, default OFF)

    Args:
        file: Word document (.docx)
        model: LLM model to use ("gpt", "claude", "gemini"). Default "gpt" (~$0.015/question)
        include_qboost: Whether to run QBoost (LLM accuracy + LO assessment)
        include_qpredict: Whether to run QPredict (find similar questions)

    Returns:
        UploadResponse with analysis_id for status checks
    """
    # Validate file type
    if not file.filename.endswith('.docx'):
        raise HTTPException(
            status_code=400,
            detail="Only .docx files are supported"
        )

    # Check if QBoost requires API key
    if include_qboost and not _check_openrouter_api_key():
        raise HTTPException(
            status_code=400,
            detail="QBoost requires an OpenRouter API key. Either uncheck QBoost or set the OPENROUTER_API_KEY environment variable."
        )

    try:
        # Read file content
        content = await file.read()

        # Parse document to get question count
        from src.core.services.outcomes_doc_parser import parse_outcomes_document_from_bytes
        parsed_doc = parse_outcomes_document_from_bytes(content, file.filename)

        # Generate analysis ID
        analysis_id = str(uuid.uuid4())[:8]

        # Store initial status with options
        _analysis_results[analysis_id] = {
            'status': 'pending',
            'progress': 0,
            'filename': file.filename,
            'question_count': len(parsed_doc.questions),
            'parsed_doc': parsed_doc,
            'model': model,
            'include_qboost': include_qboost,
            'include_qpredict': include_qpredict,
            'result': None,
            'error': None,
        }

        # Start analysis in background
        if background_tasks:
            background_tasks.add_task(
                _run_analysis, analysis_id, content, file.filename,
                model, include_qboost, include_qpredict
            )
        else:
            # For testing without background tasks
            asyncio.create_task(
                _run_analysis(analysis_id, content, file.filename,
                              model, include_qboost, include_qpredict)
            )

        # Build message about what's being analyzed
        tools_enabled = ["QCore"]
        if include_qboost:
            tools_enabled.append("QBoost")
        if include_qpredict:
            tools_enabled.append("QPredict")

        return UploadResponse(
            analysis_id=analysis_id,
            filename=file.filename,
            status='processing',
            message=f'Analysis started for {len(parsed_doc.questions)} questions ({", ".join(tools_enabled)})',
            question_count=len(parsed_doc.questions),
            tools_enabled=tools_enabled,
        )

    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Missing dependency: {str(e)}. Install with: pip install python-docx"
        )
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _run_analysis(
    analysis_id: str,
    content: bytes,
    filename: str,
    model: str,
    include_qboost: bool = True,
    include_qpredict: bool = False,
):
    """Background task to run the Q-Suite analysis."""
    try:
        _analysis_results[analysis_id]['status'] = 'processing'
        _analysis_results[analysis_id]['progress'] = 10

        # Use the new combined Q-Suite analyzer
        from src.core.services.qsuite_analyzer import analyze_outcomes_document

        # Run analysis with selected tools
        result = await analyze_outcomes_document(
            content, filename,
            model=model,
            include_qboost=include_qboost,
            include_qpredict=include_qpredict,
        )

        _analysis_results[analysis_id]['status'] = 'completed'
        _analysis_results[analysis_id]['progress'] = 100
        _analysis_results[analysis_id]['result'] = result.to_dict()

    except Exception as e:
        logger.error(f"Analysis failed for {analysis_id}: {e}")
        _analysis_results[analysis_id]['status'] = 'failed'
        _analysis_results[analysis_id]['error'] = str(e)


@router.get("/analysis/{analysis_id}", response_model=AnalysisStatusResponse)
async def get_analysis_status(analysis_id: str):
    """
    Get status and results of a document analysis.

    Args:
        analysis_id: ID returned from /upload endpoint

    Returns:
        Analysis status and results (if completed)
    """
    if analysis_id not in _analysis_results:
        raise HTTPException(status_code=404, detail=f"Analysis {analysis_id} not found")

    data = _analysis_results[analysis_id]

    # Build tools list from stored options
    tools_enabled = ["QCore"]
    if data.get('include_qboost', True):
        tools_enabled.append("QBoost")
    if data.get('include_qpredict', False):
        tools_enabled.append("QPredict")

    return AnalysisStatusResponse(
        analysis_id=analysis_id,
        status=data['status'],
        progress=data['progress'],
        message=data.get('error') or f"Analysis {data['status']}",
        tools_enabled=tools_enabled,
        result=data.get('result'),
    )


@router.get("/analysis/{analysis_id}/download")
async def download_analysis(analysis_id: str, format: str = "json"):
    """
    Download analysis results in specified format.

    Args:
        analysis_id: ID of completed analysis
        format: Output format ("json" or "excel")

    Returns:
        Analysis results as downloadable file
    """
    if analysis_id not in _analysis_results:
        raise HTTPException(status_code=404, detail=f"Analysis {analysis_id} not found")

    data = _analysis_results[analysis_id]

    if data['status'] != 'completed':
        raise HTTPException(status_code=400, detail="Analysis not yet completed")

    if format == "json":
        from fastapi.responses import JSONResponse
        return JSONResponse(
            content=data['result'],
            headers={"Content-Disposition": f"attachment; filename=qsuite_{analysis_id}.json"}
        )

    # Excel export (future)
    raise HTTPException(status_code=400, detail="Only JSON format currently supported")


# ========== Legacy Endpoints (kept for backward compatibility) ==========

@router.post("/analyze")
async def analyze_question(request: AnalyzeRequest):
    """
    Full question analysis (FUTURE).

    Will include:
    - QBoost quality score
    - Similar questions from database
    - LLM accuracy assessment
    - Performance prediction
    - Improvement suggestions
    """
    # For now, just return the quick score if tags provided
    if request.tags:
        cme_level = extract_cme_level(request.tags.get('cme_outcome_level'))
        result = calculate_qboost_score(request.tags, cme_level=cme_level)
        return {
            'quality_score': result,
            'similar_questions': [],  # Future
            'accuracy_assessment': None,  # Future
            'predicted_performance': None,  # Future
            'suggestions': [],  # Future
            'status': 'partial - tags only',
        }

    return {
        'status': 'not_implemented',
        'message': 'Full analysis requires LLM integration (Phase D)',
    }


@router.post("/find-similar")
async def find_similar_questions(request: AnalyzeRequest):
    """
    Find similar questions in database (FUTURE).

    Will use embedding-based similarity search.
    """
    return {
        'status': 'not_implemented',
        'message': 'Similarity search requires embeddings (Phase B)',
    }


@router.post("/predict")
async def predict_performance(request: AnalyzeRequest):
    """
    Predict question performance (FUTURE).

    Will use similar questions weighted average,
    then ML model when 4K questions available.
    """
    return {
        'status': 'not_implemented',
        'message': 'Performance prediction requires similar questions (Phase C)',
    }
