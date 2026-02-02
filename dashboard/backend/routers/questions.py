"""
Question API routes.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
import math
import logging
import traceback

logger = logging.getLogger(__name__)

from ..services.database import get_database
from ..services.corrections import save_correction, find_edited_fields, register_verified_canonical_values
from ..services.checkpoint import (
    update_question_in_checkpoint,
    update_question_stem_in_checkpoint,
    update_question_oncology_status_in_checkpoint,
    export_to_multispecialty,
)
from ..models.schemas import (
    SearchRequest,
    SearchResponse,
    SearchFilters,
    QuestionSummary,
    QuestionDetail,
    FilterOptions,
    TagInfo,
    TagUpdate,
    PerformanceMetric,
    ActivityDetailInfo,
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
        source_files=request.filters.source_files,
        # Patient characteristics filters (70-field schema)
        treatment_eligibilities=request.filters.treatment_eligibilities,
        age_groups=request.filters.age_groups,
        fitness_statuses=request.filters.fitness_statuses,
        organ_dysfunctions=request.filters.organ_dysfunctions,
        min_confidence=request.filters.min_confidence,
        max_confidence=request.filters.max_confidence,
        has_performance_data=request.filters.has_performance_data,
        min_sample_size=request.filters.min_sample_size,
        needs_review=request.filters.needs_review,
        review_flag_filter=request.filters.review_flag_filter,
        worst_case_agreement=request.filters.worst_case_agreement,
        tag_status_filter=request.filters.tag_status_filter,
        exclude_numeric=request.filters.exclude_numeric,
        activity_start_after=request.filters.activity_start_after,
        activity_start_before=request.filters.activity_start_before,
        page=request.pagination.page,
        page_size=request.pagination.page_size,
        sort_by=request.sort_by,
        sort_desc=request.sort_desc,
        advanced_filters=request.filters.advanced_filters,
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


@router.post("/export/full", response_model=ExportResponse)
async def export_questions_full_endpoint(filters: SearchFilters):
    """
    Export questions with ALL 70 tag fields for comprehensive Excel export.
    Supports filtering by source_file for batch workflow.
    Use this endpoint for Review Queue exports.
    """
    try:
        db = get_database()

        questions = db.get_questions_for_full_export(
            source_files=filters.source_files,
            needs_review=filters.needs_review,
            disease_states=filters.disease_states,
        )

        return ExportResponse(
            questions=[QuestionExport(**q) for q in questions],
            total=len(questions)
        )
    except Exception as e:
        logger.error(f"Full export failed: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Full export failed: {str(e)}")


@router.get("/{question_id}", response_model=QuestionDetail)
async def get_question(question_id: int):
    """
    Get full details for a specific question.
    """
    db = get_database()
    question = db.get_question_detail(question_id)
    
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    # Convert activity_details to ActivityDetailInfo objects
    activity_details = []
    for ad in question.get("activity_details", []):
        activity_details.append(ActivityDetailInfo(
            activity_name=ad["activity_name"],
            activity_date=ad.get("activity_date"),
            quarter=ad.get("quarter"),
            performance=[PerformanceMetric(**p) for p in ad.get("performance", [])]
        ))

    return QuestionDetail(
        id=question["id"],
        question_stem=question["question_stem"],
        correct_answer=question["correct_answer"],
        incorrect_answers=question["incorrect_answers"],
        source_file=question["source_file"],
        tags=TagInfo(**question["tags"]),
        performance=[PerformanceMetric(**p) for p in question["performance"]],
        activities=question["activities"],
        activity_details=activity_details,
        qcore_score=question.get("qcore_score"),
        qcore_grade=question.get("qcore_grade"),
        qcore_breakdown=question.get("qcore_breakdown")
    )


@router.put("/{question_id}/tags", response_model=TagInfo)
async def update_question_tags(question_id: int, tags: TagUpdate):
    """
    Update tags for a specific question (70-field schema).
    If mark_as_reviewed is True, all confidence scores are set to 1.0 to remove from review queue.
    """
    db = get_database()

    # Check if question exists
    question = db.get_question_detail(question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    # Update question stem if provided (admin only - validation should happen on frontend)
    if tags.question_stem is not None:
        db.update_question_stem(question_id, tags.question_stem)

        # Propagate stem edit to checkpoint for Excel write-back
        source_question_id = question.get("source_question_id")
        disease_state = question.get("tags", {}).get("disease_state")
        if source_question_id and disease_state:
            update_question_stem_in_checkpoint(
                source_question_id=source_question_id,
                disease_state=disease_state,
                new_question_stem=tags.question_stem,
            )

    # Build tags dictionary from all 70 fields
    confidence_score = 1.0  # Manual edits get full confidence

    tags_dict = {}

    # === Group A: Core Classification ===
    if tags.topic is not None:
        tags_dict['topic'] = tags.topic
        tags_dict['topic_confidence'] = confidence_score
        tags_dict['topic_method'] = 'manual'
    if tags.disease_state is not None:
        tags_dict['disease_state'] = tags.disease_state
        tags_dict['disease_state_confidence'] = confidence_score
    if tags.disease_state_1 is not None:
        tags_dict['disease_state_1'] = tags.disease_state_1
    if tags.disease_state_2 is not None:
        tags_dict['disease_state_2'] = tags.disease_state_2
        logger.info(f"[DEBUG] disease_state_2 received: {tags.disease_state_2!r}")
    if tags.disease_stage is not None:
        tags_dict['disease_stage'] = tags.disease_stage
        tags_dict['disease_stage_confidence'] = confidence_score
    if tags.disease_type_1 is not None:
        tags_dict['disease_type_1'] = tags.disease_type_1
    if tags.disease_type_2 is not None:
        tags_dict['disease_type_2'] = tags.disease_type_2
    if tags.disease_type_1 is not None or tags.disease_type_2 is not None:
        tags_dict['disease_type_confidence'] = confidence_score
    if tags.treatment_line is not None:
        tags_dict['treatment_line'] = tags.treatment_line
        tags_dict['treatment_line_confidence'] = confidence_score

    # === Multi-value Fields ===
    for i in range(1, 6):
        treatment_field = f'treatment_{i}'
        if getattr(tags, treatment_field, None) is not None:
            tags_dict[treatment_field] = getattr(tags, treatment_field)
    if any(getattr(tags, f'treatment_{i}', None) is not None for i in range(1, 6)):
        tags_dict['treatment_confidence'] = confidence_score

    for i in range(1, 6):
        biomarker_field = f'biomarker_{i}'
        if getattr(tags, biomarker_field, None) is not None:
            tags_dict[biomarker_field] = getattr(tags, biomarker_field)
    if any(getattr(tags, f'biomarker_{i}', None) is not None for i in range(1, 6)):
        tags_dict['biomarker_confidence'] = confidence_score

    for i in range(1, 6):
        trial_field = f'trial_{i}'
        if getattr(tags, trial_field, None) is not None:
            tags_dict[trial_field] = getattr(tags, trial_field)
    if any(getattr(tags, f'trial_{i}', None) is not None for i in range(1, 6)):
        tags_dict['trial_confidence'] = confidence_score

    # === Group B: Patient Characteristics ===
    if tags.treatment_eligibility is not None:
        tags_dict['treatment_eligibility'] = tags.treatment_eligibility
    if tags.age_group is not None:
        tags_dict['age_group'] = tags.age_group
    if tags.organ_dysfunction is not None:
        tags_dict['organ_dysfunction'] = tags.organ_dysfunction
    if tags.fitness_status is not None:
        tags_dict['fitness_status'] = tags.fitness_status
    if tags.disease_specific_factor is not None:
        tags_dict['disease_specific_factor'] = tags.disease_specific_factor
    for i in range(1, 4):
        field = f'comorbidity_{i}'
        if getattr(tags, field, None) is not None:
            tags_dict[field] = getattr(tags, field)

    # === Group C: Treatment Metadata ===
    for i in range(1, 4):
        for prefix in ['drug_class', 'drug_target', 'prior_therapy']:
            field = f'{prefix}_{i}'
            if getattr(tags, field, None) is not None:
                tags_dict[field] = getattr(tags, field)
    if tags.resistance_mechanism is not None:
        tags_dict['resistance_mechanism'] = tags.resistance_mechanism

    # === Group D: Clinical Context ===
    for i in range(1, 4):
        for prefix in ['metastatic_site', 'symptom']:
            field = f'{prefix}_{i}'
            if getattr(tags, field, None) is not None:
                tags_dict[field] = getattr(tags, field)
    if tags.performance_status is not None:
        tags_dict['performance_status'] = tags.performance_status

    # === Group E: Safety/Toxicity ===
    for i in range(1, 6):
        field = f'toxicity_type_{i}'
        if getattr(tags, field, None) is not None:
            tags_dict[field] = getattr(tags, field)
    if tags.toxicity_organ is not None:
        tags_dict['toxicity_organ'] = tags.toxicity_organ
    if tags.toxicity_grade is not None:
        tags_dict['toxicity_grade'] = tags.toxicity_grade

    # === Group F: Efficacy/Outcomes ===
    for i in range(1, 4):
        field = f'efficacy_endpoint_{i}'
        if getattr(tags, field, None) is not None:
            tags_dict[field] = getattr(tags, field)
    if tags.outcome_context is not None:
        tags_dict['outcome_context'] = tags.outcome_context
    if tags.clinical_benefit is not None:
        tags_dict['clinical_benefit'] = tags.clinical_benefit

    # === Group G: Evidence/Guidelines ===
    for i in range(1, 3):
        field = f'guideline_source_{i}'
        if getattr(tags, field, None) is not None:
            tags_dict[field] = getattr(tags, field)
    if tags.evidence_type is not None:
        tags_dict['evidence_type'] = tags.evidence_type

    # === Group H: Question Format/Quality ===
    if tags.cme_outcome_level is not None:
        tags_dict['cme_outcome_level'] = tags.cme_outcome_level
    if tags.data_response_type is not None:
        tags_dict['data_response_type'] = tags.data_response_type
    if tags.stem_type is not None:
        tags_dict['stem_type'] = tags.stem_type
    if tags.lead_in_type is not None:
        tags_dict['lead_in_type'] = tags.lead_in_type
    if tags.answer_format is not None:
        tags_dict['answer_format'] = tags.answer_format
    if tags.answer_length_pattern is not None:
        tags_dict['answer_length_pattern'] = tags.answer_length_pattern
    if tags.distractor_homogeneity is not None:
        tags_dict['distractor_homogeneity'] = tags.distractor_homogeneity

    # Boolean flaw fields
    if tags.flaw_absolute_terms is not None:
        tags_dict['flaw_absolute_terms'] = tags.flaw_absolute_terms
    if tags.flaw_grammatical_cue is not None:
        tags_dict['flaw_grammatical_cue'] = tags.flaw_grammatical_cue
    if tags.flaw_implausible_distractor is not None:
        tags_dict['flaw_implausible_distractor'] = tags.flaw_implausible_distractor
    if tags.flaw_clang_association is not None:
        tags_dict['flaw_clang_association'] = tags.flaw_clang_association
    if tags.flaw_convergence_vulnerability is not None:
        tags_dict['flaw_convergence_vulnerability'] = tags.flaw_convergence_vulnerability
    if tags.flaw_double_negative is not None:
        tags_dict['flaw_double_negative'] = tags.flaw_double_negative

    # Capture original tags BEFORE update for correction tracking
    original_tags = question["tags"].copy()

    # Update using the new 70-field method
    db.update_tags(question_id, tags_dict, mark_as_reviewed=tags.mark_as_reviewed)

    # Get updated question data
    updated = db.get_question_detail(question_id)
    corrected_tags = updated["tags"]

    # Persist any custom values that the user entered (values not in static dropdown lists)
    # The frontend detects these and sends them in the custom_values field
    if tags.custom_values:
        for cv in tags.custom_values:
            field_name = cv.get('field_name')
            value = cv.get('value')
            if field_name and value:
                added = db.add_user_defined_value(field_name, value)
                if added:
                    logger.info(f"Persisted custom value '{value}' for field '{field_name}'")

    # Save correction for few-shot learning and update checkpoint (only if this was a review save)
    if tags.mark_as_reviewed:
        disease_state = corrected_tags.get('disease_state') or original_tags.get('disease_state')
        edited_fields = find_edited_fields(original_tags, corrected_tags)

        if disease_state:
            # Save correction record for few-shot learning
            save_correction(
                question_id=question_id,
                question_stem=question.get("question_stem", ""),
                correct_answer=question.get("correct_answer"),
                incorrect_answers=question.get("incorrect_answers"),
                disease_state=disease_state,
                original_tags=original_tags,
                corrected_tags=corrected_tags,
                source_question_id=question.get("source_question_id"),
                source_id=str(question.get("source_id", "")) if question.get("source_id") is not None else None,
            )

            # Update the checkpoint JSON file (source of truth for Snowflake export)
            source_question_id = question.get("source_question_id")
            if source_question_id:
                update_question_in_checkpoint(
                    source_question_id=source_question_id,
                    disease_state=disease_state,
                    corrected_tags=corrected_tags,
                    edited_fields=edited_fields,
                )
                logger.info(f"Updated checkpoint for question {source_question_id}")
            else:
                logger.warning(f"Question {question_id} has no source_question_id, checkpoint not updated")

        # Register verified tag values as canonical for future normalization
        # This ensures new values become the standard for case-insensitive matching
        register_verified_canonical_values(corrected_tags)

    return TagInfo(**corrected_tags)


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
    Get filter options dynamically based on current filter selections (70-field schema).
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
        # Patient characteristics (70-field schema)
        treatment_eligibilities=current_filters.treatment_eligibilities,
        age_groups=current_filters.age_groups,
        fitness_statuses=current_filters.fitness_statuses,
        organ_dysfunctions=current_filters.organ_dysfunctions,
        advanced_filters=current_filters.advanced_filters,
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
    Non-oncology questions are:
    - Filtered out from the database view
    - Updated in the checkpoint file
    - Exported to multispecialty_questions.xlsx
    - Protected from future import overwrite
    """
    try:
        logger.info(f"Updating oncology status for question {question_id} to {request.is_oncology}")
        db = get_database()

        # Check if question exists
        question = db.get_question_detail(question_id)
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")

        # 1. Update oncology status in database
        db.update_question_oncology_status(question_id, request.is_oncology)
        logger.info(f"Successfully updated oncology status in DB for question {question_id}")

        # 2. Mark as reviewed (protects from import overwrite)
        db.update_tags(question_id, {}, mark_as_reviewed=True)
        logger.info(f"Marked question {question_id} as reviewed (edit protection)")

        # 3. Update checkpoint file
        disease_state = question.get("tags", {}).get("disease_state")
        source_question_id = question.get("source_question_id")
        if disease_state and source_question_id:
            update_question_oncology_status_in_checkpoint(
                source_question_id=source_question_id,
                disease_state=disease_state,
                is_oncology=request.is_oncology,
            )
            logger.info(f"Updated checkpoint for question {question_id}")

        # 4. If marking as non-oncology, export to multispecialty file
        if not request.is_oncology:
            source_id = question.get("source_id")
            question_stem = question.get("question_stem", "")
            correct_answer = question.get("correct_answer", "")

            # Get activities
            activities_list = question.get("activities", [])
            activities_str = ", ".join(activities_list) if activities_list else ""

            # Determine disease state for multispecialty (use original or generic)
            multispecialty_disease = disease_state or "Non-oncology"

            export_to_multispecialty(
                source_id=str(source_id) if source_id else "",
                question_stem=question_stem,
                correct_answer=correct_answer,
                activities=activities_str,
                disease_state=multispecialty_disease,
                source=f"Dashboard review (was: {disease_state})",
            )
            logger.info(f"Exported question {question_id} to multispecialty file")

        return {"message": f"Question marked as {'oncology' if request.is_oncology else 'non-oncology'}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating oncology status: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to update oncology status: {str(e)}")

