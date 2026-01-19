"""
Question API routes.

Migrated from V2 with updated imports for V3 structure.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
import math
import logging
import traceback

logger = logging.getLogger(__name__)

from ..services.database import get_database
from ..schemas import (
    SearchRequest,
    SearchResponse,
    SearchFilters,
    QuestionSummary,
    QuestionDetail,
    FilterOptions,
    TagInfo,
    TagUpdate,
    PerformanceMetric,
    FlagQuestionRequest,
    UpdateOncologyStatusRequest,
    QuestionExport,
    ExportResponse
)

router = APIRouter(prefix="/questions", tags=["questions"])


@router.post("/search", response_model=SearchResponse)
async def search_questions(request: SearchRequest):
    """
    Search questions with filters and pagination.
    """
    db = get_database()

    questions, total = db.search_questions(
        query=request.filters.query,
        topics=request.filters.topics,
        disease_states=request.filters.disease_states,
        disease_stages=request.filters.disease_stages,
        disease_types=request.filters.disease_types,
        treatment_lines=request.filters.treatment_lines,
        treatments=request.filters.treatments,
        biomarkers=request.filters.biomarkers,
        trials=request.filters.trials,
        activities=request.filters.activities,
        min_confidence=request.filters.min_confidence,
        max_confidence=request.filters.max_confidence,
        has_performance_data=request.filters.has_performance_data,
        min_sample_size=request.filters.min_sample_size,
        needs_review=request.filters.needs_review,
        review_flag_filter=request.filters.review_flag_filter,
        page=request.pagination.page,
        page_size=request.pagination.page_size,
        sort_by=request.sort_by,
        sort_desc=request.sort_desc
    )

    return SearchResponse(
        questions=[QuestionSummary(**q) for q in questions],
        total=total,
        page=request.pagination.page,
        page_size=request.pagination.page_size,
        total_pages=math.ceil(total / request.pagination.page_size) if total > 0 else 0
    )


@router.get("/search", response_model=SearchResponse)
async def search_questions_get(
    query: Optional[str] = None,
    topics: Optional[str] = Query(None, description="Comma-separated topic values"),
    disease_states: Optional[str] = Query(None, description="Comma-separated disease states"),
    treatments: Optional[str] = Query(None, description="Comma-separated treatments"),
    min_confidence: Optional[float] = Query(None, ge=0, le=1),
    max_confidence: Optional[float] = Query(None, ge=0, le=1),
    has_performance: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = "id",
    sort_desc: bool = False
):
    """
    Search questions with GET parameters (simpler alternative to POST).
    """
    db = get_database()

    # Parse comma-separated values and strip whitespace from each value
    topics_list = [t.strip() for t in topics.split(",")] if topics else None
    disease_states_list = [d.strip() for d in disease_states.split(",")] if disease_states else None
    treatments_list = [t.strip() for t in treatments.split(",")] if treatments else None

    questions, total = db.search_questions(
        query=query,
        topics=topics_list,
        disease_states=disease_states_list,
        treatments=treatments_list,
        min_confidence=min_confidence,
        max_confidence=max_confidence,
        has_performance_data=has_performance,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_desc=sort_desc
    )

    return SearchResponse(
        questions=[QuestionSummary(**q) for q in questions],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0
    )


# NOTE: Export endpoint must come BEFORE /{question_id} routes to avoid path conflicts
@router.post("/export", response_model=ExportResponse)
async def export_questions_endpoint(filters: SearchFilters):
    """
    Export questions matching filters with all tags and linked activities.
    Returns full data for Excel/CSV export including semicolon-separated activity names.
    """
    try:
        db = get_database()

        questions = db.get_questions_for_export(
            topics=filters.topics,
            disease_states=filters.disease_states,
            disease_stages=filters.disease_stages,
            disease_types=filters.disease_types,
            treatment_lines=filters.treatment_lines,
            treatments=filters.treatments,
            biomarkers=filters.biomarkers,
            trials=filters.trials,
            activities=filters.activities,
        )

        return ExportResponse(
            questions=[QuestionExport(**q) for q in questions],
            total=len(questions)
        )
    except Exception as e:
        logger.error(f"Export failed: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/{question_id}", response_model=QuestionDetail)
async def get_question(question_id: int):
    """
    Get full details for a specific question.
    """
    db = get_database()
    question = db.get_question_detail(question_id)

    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    return QuestionDetail(
        id=question["id"],
        question_stem=question["question_stem"],
        correct_answer=question["correct_answer"],
        incorrect_answers=question["incorrect_answers"],
        source_file=question["source_file"],
        tags=TagInfo(**question["tags"]),
        performance=[PerformanceMetric(**p) for p in question["performance"]],
        activities=question["activities"]
    )


@router.put("/{question_id}/tags", response_model=TagInfo)
async def update_question_tags(question_id: int, tags: TagUpdate):
    """
    Update tags for a specific question.
    If mark_as_reviewed is True, all confidence scores are set to 1.0 to remove from review queue.
    """
    db = get_database()

    # Check if question exists
    question = db.get_question_detail(question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    # If marking as reviewed, set all confidence scores to 1.0
    # Otherwise, set to 1.0 only for manually edited tags
    confidence_score = 1.0 if tags.mark_as_reviewed else 1.0

    # Update question stem if provided (admin only - validation should happen on frontend)
    if tags.question_stem is not None:
        db.update_question_stem(question_id, tags.question_stem)

    # Update tags (set confidence to 1.0 and method to 'manual' for manually edited tags)
    db.insert_tags(
        question_id=question_id,
        topic=tags.topic,
        topic_confidence=confidence_score if tags.topic else None,
        topic_method='manual' if tags.topic else None,
        disease_state=tags.disease_state,
        disease_state_confidence=confidence_score if tags.disease_state else None,
        disease_stage=tags.disease_stage,
        disease_type=tags.disease_type,
        treatment_line=tags.treatment_line,
        treatment_line_confidence=confidence_score if tags.treatment_line else None,
        treatment=tags.treatment,
        treatment_confidence=confidence_score if tags.treatment else None,
        biomarker=tags.biomarker,
        trial=tags.trial,
        overall_confidence=confidence_score if tags.mark_as_reviewed else None
    )

    # Return updated tags
    updated = db.get_question_detail(question_id)
    return TagInfo(**updated["tags"])


@router.get("/filters/options", response_model=FilterOptions)
async def get_filter_options():
    """
    Get all available filter options with counts.
    """
    db = get_database()
    options = db.get_filter_options()
    return FilterOptions(**options)


@router.post("/filters/options/dynamic", response_model=FilterOptions)
async def get_dynamic_filter_options(current_filters: SearchFilters):
    """
    Get filter options dynamically based on current filter selections.
    Returns only options that exist in the filtered dataset.
    """
    db = get_database()
    options = db.get_dynamic_filter_options(
        topics=current_filters.topics,
        disease_states=current_filters.disease_states,
        disease_stages=current_filters.disease_stages,
        disease_types=current_filters.disease_types,
        treatment_lines=current_filters.treatment_lines,
        treatments=current_filters.treatments,
        biomarkers=current_filters.biomarkers,
        trials=current_filters.trials,
    )
    return FilterOptions(**options)


@router.get("/stats/summary")
async def get_stats():
    """
    Get database statistics summary.
    """
    db = get_database()
    return db.get_stats()


@router.post("/{question_id}/flag")
async def flag_question(question_id: int, request: FlagQuestionRequest):
    """
    Flag a question for review with specific reasons.
    Adds the question to the "Questions Needing Review" list.
    """
    db = get_database()

    # Check if question exists
    question = db.get_question_detail(question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    # Flag the question
    db.flag_question(question_id, request.reasons)

    return {"message": "Question flagged for review", "reasons": request.reasons}


@router.put("/{question_id}/oncology-status")
async def update_oncology_status(question_id: int, request: UpdateOncologyStatusRequest):
    """
    Mark a question as oncology or non-oncology.
    Non-oncology questions can be filtered out from the database view.
    """
    try:
        logger.info(f"Updating oncology status for question {question_id} to {request.is_oncology}")
        db = get_database()

        # Check if question exists
        question = db.get_question_detail(question_id)
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")

        # Update oncology status
        db.update_question_oncology_status(question_id, request.is_oncology)
        logger.info(f"Successfully updated oncology status for question {question_id}")

        return {"message": f"Question marked as {'oncology' if request.is_oncology else 'non-oncology'}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating oncology status: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to update oncology status: {str(e)}")
