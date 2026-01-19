"""
Tagging API endpoints for V3 3-model LLM voting system.

Provides endpoints for:
- Initiating tagging jobs with 3-model voting
- Checking tagging job status
- Retrieving voting results
- Managing prompt versions
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import Optional, List, Dict, Any
import math
import logging
import uuid
import asyncio
import os
from datetime import datetime

from ..services.database import get_database
from ..schemas import (
    TaggingRequest,
    TaggingProgress,
    TaggingJobStatus,
    VotingResult,
    VotingResultSummary,
    VotingResultListResponse,
    PromptVersion,
    PromptVersionListResponse,
    AgreementLevel,
)

# Import V3 core components
from ...core.taggers import MultiModelTagger, OpenRouterClient, VoteAggregator
from ...core.services import PromptManager, WebSearchService
from ...core.knowledge import KnowledgeEnricher

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tagging", tags=["tagging"])

# In-memory job tracking (would be Redis in production)
_active_jobs: Dict[str, TaggingJobStatus] = {}

# Singleton instances (initialized lazily)
_tagger: Optional[MultiModelTagger] = None
_prompt_manager: Optional[PromptManager] = None


def get_tagger() -> MultiModelTagger:
    """Get or create the MultiModelTagger singleton."""
    global _tagger
    if _tagger is None:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=500,
                detail="OPENROUTER_API_KEY environment variable not set"
            )

        # Initialize components
        client = OpenRouterClient(api_key)
        aggregator = VoteAggregator()
        enricher = KnowledgeEnricher()
        prompt_manager = get_prompt_manager()
        web_search = WebSearchService(client)

        _tagger = MultiModelTagger(
            client=client,
            aggregator=aggregator,
            enricher=enricher,
            prompt_manager=prompt_manager,
            web_search=web_search
        )
    return _tagger


def get_prompt_manager() -> PromptManager:
    """Get or create the PromptManager singleton."""
    global _prompt_manager
    if _prompt_manager is None:
        # Determine prompts directory path
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        prompts_dir = os.path.join(base_dir, "prompts")
        _prompt_manager = PromptManager(prompts_dir)
    return _prompt_manager


async def run_tagging_job(job_id: str, request: TaggingRequest):
    """Background task to run the actual tagging job."""
    job = _active_jobs.get(job_id)
    if not job:
        logger.error(f"Job {job_id} not found in active jobs")
        return

    try:
        job.status = "running"
        job.started_at = datetime.utcnow()

        db = get_database()
        tagger = get_tagger()

        # Build list of questions to process
        questions = []
        for qid in request.question_ids:
            q_detail = db.get_question_detail(qid)
            if q_detail:
                questions.append({
                    "id": qid,
                    "text": q_detail.get("question_text", ""),
                    "correct_answer": q_detail.get("correct_answer")
                })

        job.progress.total_questions = len(questions)

        # Progress callback to update job status
        def update_progress(completed: int, result: Any = None):
            job.progress.completed = completed
            if result:
                level = result.agreement_level
                if level == "unanimous":
                    job.progress.unanimous_count += 1
                elif level == "majority":
                    job.progress.majority_count += 1
                else:
                    job.progress.conflict_count += 1

                # Estimate cost (roughly $0.12 per question)
                job.progress.estimated_cost = completed * 0.12

        # Process questions in batches
        results = await tagger.tag_batch(questions, progress_callback=update_progress)

        # Store results in database
        for result in results:
            db.save_voting_result(
                question_id=result.question_id,
                iteration=request.iteration,
                prompt_version=get_prompt_manager().current_version,
                gpt_tags=result.model_votes.get("gpt", {}).tags if result.model_votes.get("gpt") else {},
                claude_tags=result.model_votes.get("claude", {}).tags if result.model_votes.get("claude") else {},
                gemini_tags=result.model_votes.get("gemini", {}).tags if result.model_votes.get("gemini") else {},
                aggregated_tags=result.aggregated_tags,
                agreement_level=result.agreement_level,
                needs_review=result.agreement_level != "unanimous",
                web_searches=result.web_searches
            )

        job.status = "completed"
        job.completed_at = datetime.utcnow()

        logger.info(f"Job {job_id} completed: {len(results)} questions tagged")

    except Exception as e:
        logger.exception(f"Job {job_id} failed: {e}")
        job.status = "failed"
        job.error_message = str(e)
        job.completed_at = datetime.utcnow()


# ============== Tagging Job Management ==============

@router.post("/jobs", response_model=TaggingJobStatus)
async def create_tagging_job(
    request: TaggingRequest,
    background_tasks: BackgroundTasks
):
    """
    Create a new tagging job to process questions with 3-model voting.

    The job runs asynchronously and can be monitored via GET /jobs/{job_id}.

    Args:
        request: Contains question_ids to tag, iteration number, and web search flag
    """
    job_id = str(uuid.uuid4())[:8]

    # Initialize job status
    job_status = TaggingJobStatus(
        job_id=job_id,
        status="pending",
        progress=TaggingProgress(
            total_questions=len(request.question_ids),
            completed=0,
            in_progress=0,
            failed=0,
            unanimous_count=0,
            majority_count=0,
            conflict_count=0,
            estimated_cost=0.0
        ),
        started_at=None,
        completed_at=None,
        error_message=None
    )

    _active_jobs[job_id] = job_status

    # Add background task to run the actual tagging
    background_tasks.add_task(run_tagging_job, job_id, request)

    logger.info(f"Created tagging job {job_id} for {len(request.question_ids)} questions")

    return job_status


@router.get("/jobs/{job_id}", response_model=TaggingJobStatus)
async def get_tagging_job_status(job_id: str):
    """
    Get the status of a tagging job.

    Returns current progress including:
    - Questions completed/in_progress/failed
    - Agreement breakdown (unanimous/majority/conflict)
    - Estimated API cost so far
    """
    if job_id not in _active_jobs:
        raise HTTPException(status_code=404, detail="Tagging job not found")

    return _active_jobs[job_id]


@router.get("/jobs", response_model=List[TaggingJobStatus])
async def list_tagging_jobs(
    status: Optional[str] = Query(None, description="Filter by status: pending, running, completed, failed"),
    limit: int = Query(10, ge=1, le=100)
):
    """
    List recent tagging jobs.
    """
    jobs = list(_active_jobs.values())

    if status:
        jobs = [j for j in jobs if j.status == status]

    # Sort by created time (most recent first)
    jobs.sort(key=lambda x: x.started_at or datetime.min, reverse=True)

    return jobs[:limit]


@router.delete("/jobs/{job_id}")
async def cancel_tagging_job(job_id: str):
    """
    Cancel a running tagging job.
    """
    if job_id not in _active_jobs:
        raise HTTPException(status_code=404, detail="Tagging job not found")

    job = _active_jobs[job_id]
    if job.status not in ["pending", "running"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel job with status '{job.status}'"
        )

    job.status = "failed"
    job.error_message = "Cancelled by user"
    job.completed_at = datetime.utcnow()

    return {"success": True, "message": f"Job {job_id} cancelled"}


# ============== Voting Results ==============

@router.get("/results", response_model=VotingResultListResponse)
async def list_voting_results(
    agreement_level: Optional[str] = Query(None, description="Filter by: unanimous, majority, conflict"),
    needs_review: Optional[bool] = Query(None, description="Filter by review status"),
    iteration: Optional[int] = Query(None, description="Filter by iteration number"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """
    List voting results from 3-model tagging.

    Use this to review model agreement patterns and identify questions needing review.
    """
    db = get_database()

    offset = (page - 1) * page_size

    results, total = db.get_voting_results(
        agreement_level=agreement_level,
        needs_review=needs_review,
        iteration=iteration,
        limit=page_size,
        offset=offset
    )

    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return VotingResultListResponse(
        results=results,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/results/{result_id}", response_model=VotingResult)
async def get_voting_result(result_id: int):
    """
    Get full voting result details including individual model votes.
    """
    db = get_database()

    result = db.get_voting_result_by_id(result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Voting result not found")

    return result


@router.get("/results/by-question/{question_id}")
async def get_voting_results_for_question(question_id: int):
    """
    Get all voting results for a specific question across iterations.
    """
    db = get_database()

    results = db.get_voting_results_for_question(question_id)

    return {
        "question_id": question_id,
        "results": results,
        "total_iterations": len(set(r.get("iteration", 0) for r in results))
    }


# ============== Statistics ==============

@router.get("/stats")
async def get_tagging_stats():
    """
    Get tagging statistics across all iterations.
    """
    db = get_database()

    stats = db.get_tagging_statistics()

    return stats


@router.get("/stats/models")
async def get_model_agreement_stats():
    """
    Get detailed model agreement statistics.

    Shows which model pairs agree most often and common disagreement patterns.
    """
    db = get_database()

    stats = db.get_model_agreement_statistics()

    return stats


# ============== Prompt Management ==============

@router.get("/prompts", response_model=PromptVersionListResponse)
async def list_prompt_versions():
    """
    List all prompt versions used for tagging.
    """
    pm = get_prompt_manager()

    versions = pm.list_versions()

    return PromptVersionListResponse(
        versions=versions,
        current_version=pm.current_version
    )


@router.get("/prompts/{version}")
async def get_prompt_version(version: str):
    """
    Get details of a specific prompt version including performance metrics.
    """
    pm = get_prompt_manager()

    try:
        prompt_version = pm.load_version(version)
        return {
            "version": prompt_version.version,
            "iteration": prompt_version.iteration,
            "system_prompt": prompt_version.system_prompt,
            "examples_count": len(prompt_version.examples),
            "edge_cases_count": len(prompt_version.edge_cases),
            "changelog": prompt_version.changelog,
            "performance_metrics": prompt_version.performance_metrics
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Prompt version not found")


@router.post("/prompts/reload")
async def reload_current_prompt():
    """
    Reload the current prompt from disk.

    Use this after editing prompt files to apply changes without restart.
    """
    global _prompt_manager, _tagger

    # Reset singletons to force reload
    _prompt_manager = None
    _tagger = None

    # Reinitialize
    pm = get_prompt_manager()

    return {
        "success": True,
        "message": "Prompt reloaded",
        "current_version": pm.current_version
    }


# ============== Single Question Tagging ==============

@router.post("/tag-single/{question_id}")
async def tag_single_question(
    question_id: int,
    use_web_search: bool = Query(True, description="Enable web search for unknown entities")
):
    """
    Tag a single question with 3-model voting.

    Returns immediately with the voting result (synchronous).
    Use this for testing or on-demand tagging.
    """
    db = get_database()

    # Verify question exists
    question = db.get_question_detail(question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    try:
        tagger = get_tagger()

        # Tag the question
        result = await tagger.tag_question(
            question_id=question_id,
            question_text=question.get("question_text", ""),
            correct_answer=question.get("correct_answer"),
            use_web_search=use_web_search
        )

        # Save result to database
        db.save_voting_result(
            question_id=question_id,
            iteration=1,  # Default iteration for single tags
            prompt_version=get_prompt_manager().current_version,
            gpt_tags=result.model_votes.get("gpt", {}).tags if result.model_votes.get("gpt") else {},
            claude_tags=result.model_votes.get("claude", {}).tags if result.model_votes.get("claude") else {},
            gemini_tags=result.model_votes.get("gemini", {}).tags if result.model_votes.get("gemini") else {},
            aggregated_tags=result.aggregated_tags,
            agreement_level=result.agreement_level,
            needs_review=result.agreement_level != "unanimous",
            web_searches=result.web_searches
        )

        return {
            "question_id": question_id,
            "status": "completed",
            "agreement_level": result.agreement_level,
            "aggregated_tags": result.aggregated_tags,
            "needs_review": result.agreement_level != "unanimous",
            "model_votes": {
                "gpt": result.model_votes.get("gpt", {}).tags if result.model_votes.get("gpt") else None,
                "claude": result.model_votes.get("claude", {}).tags if result.model_votes.get("claude") else None,
                "gemini": result.model_votes.get("gemini", {}).tags if result.model_votes.get("gemini") else None,
            },
            "disagreements": [
                {
                    "field": d["field"],
                    "values": d["values"]
                }
                for d in result.disagreements
            ] if result.disagreements else [],
            "confidence": result.confidence
        }

    except Exception as e:
        logger.exception(f"Error tagging question {question_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tag-batch")
async def tag_batch_sync(
    question_ids: List[int],
    use_web_search: bool = Query(True, description="Enable web search"),
    max_concurrent: int = Query(5, ge=1, le=20, description="Max concurrent API calls")
):
    """
    Tag multiple questions synchronously (for smaller batches).

    For larger batches, use POST /jobs to run asynchronously.
    Limited to 50 questions max.
    """
    if len(question_ids) > 50:
        raise HTTPException(
            status_code=400,
            detail="Batch size too large. Use POST /jobs for batches > 50 questions."
        )

    db = get_database()
    tagger = get_tagger()

    # Build question list
    questions = []
    for qid in question_ids:
        q_detail = db.get_question_detail(qid)
        if q_detail:
            questions.append({
                "id": qid,
                "text": q_detail.get("question_text", ""),
                "correct_answer": q_detail.get("correct_answer")
            })

    # Process batch
    results = await tagger.tag_batch(questions)

    # Save results
    pm = get_prompt_manager()
    for result in results:
        db.save_voting_result(
            question_id=result.question_id,
            iteration=1,
            prompt_version=pm.current_version,
            gpt_tags=result.model_votes.get("gpt", {}).tags if result.model_votes.get("gpt") else {},
            claude_tags=result.model_votes.get("claude", {}).tags if result.model_votes.get("claude") else {},
            gemini_tags=result.model_votes.get("gemini", {}).tags if result.model_votes.get("gemini") else {},
            aggregated_tags=result.aggregated_tags,
            agreement_level=result.agreement_level,
            needs_review=result.agreement_level != "unanimous",
            web_searches=result.web_searches
        )

    # Summarize results
    summary = {
        "total": len(results),
        "unanimous": sum(1 for r in results if r.agreement_level == "unanimous"),
        "majority": sum(1 for r in results if r.agreement_level == "majority"),
        "conflict": sum(1 for r in results if r.agreement_level == "conflict"),
        "results": [
            {
                "question_id": r.question_id,
                "agreement_level": r.agreement_level,
                "aggregated_tags": r.aggregated_tags
            }
            for r in results
        ]
    }

    return summary
