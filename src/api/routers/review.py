"""
Review API endpoints for V3 human review workflow.

Provides endpoints for:
- Reviewing questions with model disagreements
- Submitting human corrections
- Analyzing disagreement patterns
- Generating review exports
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import Optional, List, Dict, Any
import math
import logging
import json
import csv
import io
from datetime import datetime

from ..services.database import get_database
from ..schemas import (
    ReviewCorrection,
    ReviewCorrectionCreate,
    DisagreementPattern,
    DisagreementPatternListResponse,
    VotingResultSummary,
    AgreementLevel,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/review", tags=["review"])


# ============== Review Queue ==============

@router.get("/queue")
async def get_review_queue(
    agreement_level: Optional[str] = Query(None, description="Filter by: conflict, majority"),
    iteration: Optional[int] = Query(None, description="Filter by iteration"),
    category: Optional[str] = Query(None, description="Filter by disagreement category"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """
    Get questions in the review queue (those with model disagreements).

    Prioritizes conflicts over majority votes.
    Returns questions with their voting results for side-by-side comparison.
    """
    db = get_database()

    offset = (page - 1) * page_size

    # Get voting results that need review
    results, total = db.get_voting_results(
        agreement_level=agreement_level,
        needs_review=True,
        iteration=iteration,
        limit=page_size,
        offset=offset
    )

    # Enrich with question details
    questions = []
    for result in results:
        question = db.get_question_detail(result.get("question_id"))
        if question:
            questions.append({
                "question_id": result.get("question_id"),
                "question_text": question.get("question_text"),
                "correct_answer": question.get("correct_answer"),
                "agreement_level": result.get("agreement_level"),
                "iteration": result.get("iteration"),
                "gpt_tags": result.get("gpt_tags"),
                "claude_tags": result.get("claude_tags"),
                "gemini_tags": result.get("gemini_tags"),
                "aggregated_tags": result.get("aggregated_tags"),
                "created_at": result.get("created_at")
            })

    # Get stats
    conflict_count = db.count_voting_results(agreement_level="conflict", needs_review=True)
    majority_count = db.count_voting_results(agreement_level="majority", needs_review=True)

    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return {
        "questions": questions,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "stats": {
            "conflicts": conflict_count,
            "majority_votes": majority_count,
            "total_pending": conflict_count + majority_count
        }
    }


@router.get("/queue/{question_id}")
async def get_review_item(question_id: int):
    """
    Get full review context for a question.

    Includes:
    - Question content
    - All 3 model votes with reasoning
    - Web search results used (if any)
    - Previous corrections for this question
    """
    db = get_database()

    question = db.get_question_detail(question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    # Get the most recent voting result
    voting_results = db.get_voting_results_for_question(question_id)
    latest_vote = voting_results[0] if voting_results else None

    # Get previous corrections
    corrections = db.get_corrections_for_question(question_id)

    return {
        "question": question,
        "voting_result": latest_vote,
        "web_searches": latest_vote.get("web_searches", []) if latest_vote else [],
        "previous_corrections": corrections,
        "suggested_tags": latest_vote.get("aggregated_tags") if latest_vote else None
    }


# ============== Corrections ==============

@router.post("/corrections/{question_id}")
async def submit_correction(
    question_id: int,
    correction: ReviewCorrectionCreate
):
    """
    Submit a human correction for a question.

    The correction is logged for prompt refinement and the question's
    tags are updated to the corrected values.
    """
    db = get_database()

    # Verify question exists
    question = db.get_question_detail(question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    # Get the current voting result to capture original tags
    voting_results = db.get_voting_results_for_question(question_id)
    original_tags = {}
    if voting_results:
        original_tags = voting_results[0].get("aggregated_tags", {})

    # Save the correction
    correction_id = db.save_review_correction(
        question_id=question_id,
        iteration=correction.iteration,
        original_tags=original_tags,
        corrected_tags=correction.corrected_tags,
        disagreement_category=correction.disagreement_category,
        reviewer_notes=correction.reviewer_notes
    )

    # Update the question's tags to the corrected values
    db.update_question_tags(question_id, correction.corrected_tags)

    # Mark the voting result as reviewed
    if voting_results:
        db.mark_voting_result_reviewed(voting_results[0].get("id"))

    logger.info(f"Correction submitted for question {question_id}")

    return {
        "success": True,
        "message": "Correction submitted",
        "question_id": question_id,
        "correction_id": correction_id
    }


@router.get("/corrections")
async def list_corrections(
    iteration: Optional[int] = Query(None, description="Filter by iteration"),
    category: Optional[str] = Query(None, description="Filter by disagreement category"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100)
):
    """
    List human corrections for prompt refinement analysis.
    """
    db = get_database()

    offset = (page - 1) * page_size

    corrections, total = db.get_review_corrections(
        iteration=iteration,
        category=category,
        limit=page_size,
        offset=offset
    )

    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return {
        "corrections": corrections,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }


@router.get("/corrections/export")
async def export_corrections(
    iteration: Optional[int] = Query(None, description="Filter by iteration"),
    format: str = Query("json", description="Export format: json, csv")
):
    """
    Export corrections for a given iteration.

    Use this to analyze patterns and refine prompts.
    """
    db = get_database()

    corrections, total = db.get_review_corrections(iteration=iteration, limit=10000)

    # Group by category
    by_category: Dict[str, int] = {}
    by_tag_field: Dict[str, int] = {}

    for c in corrections:
        cat = c.get("disagreement_category", "unknown")
        by_category[cat] = by_category.get(cat, 0) + 1

        # Compare original vs corrected to find changed fields
        original = c.get("original_tags", {})
        corrected = c.get("corrected_tags", {})
        for field in corrected:
            if original.get(field) != corrected.get(field):
                by_tag_field[field] = by_tag_field.get(field, 0) + 1

    if format == "csv":
        # Generate CSV
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "question_id", "iteration", "disagreement_category",
            "original_tags", "corrected_tags", "reviewer_notes", "reviewed_at"
        ])
        writer.writeheader()
        for c in corrections:
            writer.writerow({
                "question_id": c.get("question_id"),
                "iteration": c.get("iteration"),
                "disagreement_category": c.get("disagreement_category"),
                "original_tags": json.dumps(c.get("original_tags", {})),
                "corrected_tags": json.dumps(c.get("corrected_tags", {})),
                "reviewer_notes": c.get("reviewer_notes", ""),
                "reviewed_at": c.get("reviewed_at")
            })

        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=corrections_iter{iteration or 'all'}.csv"}
        )

    return {
        "iteration": iteration,
        "total_corrections": total,
        "corrections": corrections,
        "summary": {
            "by_category": by_category,
            "by_tag_field": by_tag_field
        }
    }


# ============== Disagreement Analysis ==============

@router.get("/patterns", response_model=DisagreementPatternListResponse)
async def list_disagreement_patterns(
    iteration: Optional[int] = Query(None, description="Filter by iteration"),
    implemented: Optional[bool] = Query(None, description="Filter by implementation status")
):
    """
    List identified disagreement patterns.

    These are automatically detected from corrections and can be used
    to improve prompts in the next iteration.
    """
    db = get_database()

    patterns, total = db.get_disagreement_patterns(
        iteration=iteration,
        implemented=implemented
    )

    return DisagreementPatternListResponse(
        patterns=patterns,
        total=total
    )


@router.post("/patterns/analyze")
async def analyze_patterns(iteration: int = Query(..., description="Iteration to analyze")):
    """
    Run analysis to identify disagreement patterns from corrections.

    This groups corrections by category and identifies common themes
    that can be addressed in prompt refinement.
    """
    db = get_database()

    # Get all corrections for the iteration
    corrections, _ = db.get_review_corrections(iteration=iteration, limit=10000)

    if not corrections:
        return {
            "iteration": iteration,
            "patterns_found": 0,
            "patterns": [],
            "recommendations": []
        }

    # Group corrections by category and analyze
    pattern_groups: Dict[str, List[Dict]] = {}
    for c in corrections:
        category = c.get("disagreement_category", "uncategorized")
        if category not in pattern_groups:
            pattern_groups[category] = []
        pattern_groups[category].append(c)

    # Create patterns from groups
    patterns = []
    recommendations = []

    for category, group in pattern_groups.items():
        if len(group) >= 3:  # Only create pattern if 3+ occurrences
            # Sample example questions
            example_ids = [c.get("question_id") for c in group[:5]]

            pattern = {
                "category": category,
                "frequency": len(group),
                "example_questions": example_ids,
                "implemented": False
            }

            # Save pattern to database
            pattern_id = db.save_disagreement_pattern(
                iteration=iteration,
                category=category,
                frequency=len(group),
                example_questions=example_ids,
                recommended_action=f"Review {category} cases and update prompt guidance"
            )
            pattern["id"] = pattern_id
            patterns.append(pattern)

            recommendations.append({
                "category": category,
                "frequency": len(group),
                "action": f"Add clarification for {category} cases in prompt v{iteration + 1}"
            })

    return {
        "iteration": iteration,
        "patterns_found": len(patterns),
        "patterns": patterns,
        "recommendations": recommendations
    }


@router.put("/patterns/{pattern_id}/implemented")
async def mark_pattern_implemented(pattern_id: int):
    """
    Mark a disagreement pattern as implemented in the prompt.

    Use this after updating the prompt to address a pattern.
    """
    db = get_database()

    success = db.mark_pattern_implemented(pattern_id)
    if not success:
        raise HTTPException(status_code=404, detail="Pattern not found")

    return {
        "success": True,
        "pattern_id": pattern_id,
        "status": "implemented"
    }


# ============== Statistics ==============

@router.get("/stats")
async def get_review_stats():
    """
    Get review workflow statistics.
    """
    db = get_database()

    # Get queue stats
    conflict_count = db.count_voting_results(agreement_level="conflict", needs_review=True)
    majority_count = db.count_voting_results(agreement_level="majority", needs_review=True)

    # Get correction stats
    corrections, total_corrections = db.get_review_corrections(limit=1)

    # Get stats by iteration
    by_iteration: Dict[int, int] = {}
    all_corrections, _ = db.get_review_corrections(limit=10000)
    for c in all_corrections:
        iter_num = c.get("iteration", 0)
        by_iteration[iter_num] = by_iteration.get(iter_num, 0) + 1

    # Get stats by category
    by_category: Dict[str, int] = {}
    for c in all_corrections:
        cat = c.get("disagreement_category", "unknown")
        by_category[cat] = by_category.get(cat, 0) + 1

    return {
        "queue_size": conflict_count + majority_count,
        "corrections_submitted": total_corrections,
        "by_iteration": by_iteration,
        "by_category": by_category,
        "reviewer_activity": {},  # Would track by reviewer if we had auth
        "avg_review_time_seconds": 0  # Would calculate if we tracked times
    }


@router.get("/stats/accuracy")
async def get_accuracy_stats(iteration: Optional[int] = Query(None)):
    """
    Get accuracy statistics comparing model predictions to human corrections.
    """
    db = get_database()

    corrections, total = db.get_review_corrections(iteration=iteration, limit=10000)

    if total == 0:
        return {
            "iteration": iteration,
            "overall_accuracy": 0.0,
            "by_tag_field": {},
            "by_model": {
                "gpt": 0.0,
                "claude": 0.0,
                "gemini": 0.0,
                "aggregated": 0.0
            }
        }

    # Calculate accuracy per field
    tag_fields = ["topic", "disease_state", "disease_stage", "disease_type",
                  "treatment_line", "treatment", "biomarker", "trial"]

    by_tag_field = {}
    for field in tag_fields:
        correct = 0
        total_field = 0
        for c in corrections:
            original = c.get("original_tags", {})
            corrected = c.get("corrected_tags", {})
            if field in corrected:
                total_field += 1
                if original.get(field) == corrected.get(field):
                    correct += 1

        if total_field > 0:
            by_tag_field[field] = {
                "correct": correct,
                "total": total_field,
                "accuracy": round(correct / total_field, 3)
            }

    # Calculate overall accuracy
    total_fields = sum(f["total"] for f in by_tag_field.values())
    total_correct = sum(f["correct"] for f in by_tag_field.values())
    overall_accuracy = round(total_correct / total_fields, 3) if total_fields > 0 else 0.0

    return {
        "iteration": iteration,
        "overall_accuracy": overall_accuracy,
        "by_tag_field": by_tag_field,
        "by_model": {
            "gpt": 0.0,  # Would require storing individual model votes
            "claude": 0.0,
            "gemini": 0.0,
            "aggregated": overall_accuracy
        }
    }


# ============== Spot Checks ==============

@router.get("/spot-checks")
async def get_spot_check_queue(
    count: int = Query(10, ge=1, le=50, description="Number of questions to return")
):
    """
    Get a random sample of unanimously tagged questions for spot-checking.

    Even when models agree, we do periodic human verification (default 10%)
    to ensure quality and catch systematic errors.
    """
    db = get_database()

    questions = db.get_random_unanimous_questions(count)

    total_unanimous = db.count_voting_results(agreement_level="unanimous")

    return {
        "questions": questions,
        "total_available": total_unanimous,
        "sample_rate": 0.10
    }


@router.post("/spot-checks/{question_id}/verify")
async def submit_spot_check(
    question_id: int,
    is_correct: bool = Query(..., description="Whether the unanimous tags are correct"),
    correction: Optional[ReviewCorrectionCreate] = None
):
    """
    Submit spot-check result for a unanimously tagged question.

    If is_correct=False, provide correction details.
    """
    db = get_database()

    question = db.get_question_detail(question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    correction_id = None

    if not is_correct and correction:
        # Get current tags as original
        voting_results = db.get_voting_results_for_question(question_id)
        original_tags = voting_results[0].get("aggregated_tags", {}) if voting_results else {}

        # Save the correction
        correction_id = db.save_review_correction(
            question_id=question_id,
            iteration=correction.iteration,
            original_tags=original_tags,
            corrected_tags=correction.corrected_tags,
            disagreement_category="spot_check_failed",
            reviewer_notes=correction.reviewer_notes
        )

        # Update the question's tags
        db.update_question_tags(question_id, correction.corrected_tags)

    # Log the spot check result
    db.log_spot_check(question_id, is_correct)

    return {
        "success": True,
        "question_id": question_id,
        "verified": is_correct,
        "correction_id": correction_id
    }


# ============== Batch Operations ==============

@router.post("/batch/approve-unanimous")
async def batch_approve_unanimous(iteration: int = Query(..., description="Iteration to approve")):
    """
    Approve all unanimous votes for an iteration.

    This finalizes the tags for questions where all 3 models agreed.
    Should be called after spot-checking a sample.
    """
    db = get_database()

    # Get all unanimous results for the iteration
    results, _ = db.get_voting_results(
        agreement_level="unanimous",
        iteration=iteration,
        limit=100000
    )

    approved_count = 0
    for result in results:
        question_id = result.get("question_id")
        tags = result.get("aggregated_tags", {})

        # Update question tags
        db.update_question_tags(question_id, tags)

        # Mark as approved (not needing review)
        db.mark_voting_result_reviewed(result.get("id"))

        approved_count += 1

    logger.info(f"Approved {approved_count} unanimous votes for iteration {iteration}")

    return {
        "success": True,
        "iteration": iteration,
        "approved_count": approved_count
    }


@router.post("/batch/export-for-review")
async def export_for_review(
    iteration: int = Query(..., description="Iteration to export"),
    agreement_level: Optional[str] = Query(None, description="Filter by agreement level")
):
    """
    Export questions needing review to Excel for offline review.

    Returns a downloadable CSV file with questions, model votes,
    and space for corrections.
    """
    db = get_database()

    # Get voting results
    results, total = db.get_voting_results(
        agreement_level=agreement_level,
        needs_review=True,
        iteration=iteration,
        limit=10000
    )

    # Build export data
    export_data = []
    for result in results:
        question = db.get_question_detail(result.get("question_id"))
        if question:
            export_data.append({
                "question_id": result.get("question_id"),
                "question_text": question.get("question_text"),
                "correct_answer": question.get("correct_answer"),
                "agreement_level": result.get("agreement_level"),
                "gpt_tags": json.dumps(result.get("gpt_tags", {})),
                "claude_tags": json.dumps(result.get("claude_tags", {})),
                "gemini_tags": json.dumps(result.get("gemini_tags", {})),
                "aggregated_tags": json.dumps(result.get("aggregated_tags", {})),
            })

    # Generate CSV
    output = io.StringIO()
    if export_data:
        writer = csv.DictWriter(output, fieldnames=export_data[0].keys())
        writer.writeheader()
        writer.writerows(export_data)

    filename = f"review_iteration_{iteration}_{agreement_level or 'all'}.csv"

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
