"""
Reports API endpoints for CME Question Explorer.

Provides aggregated performance analytics and trend data for report generation.
"""

from fastapi import APIRouter, HTTPException
from typing import Optional, List

from ..services.database import get_database
from ..models.schemas import (
    AggregateByTagRequest,
    AggregateByTagWithSegmentsRequest,
    AggregateByDemographicRequest,
    AggregateBySegmentRequest,
    TrendRequest,
    AggregatedMetric,
    AggregatedReportResponse,
    SegmentReportResponse,
    TrendDataPoint,
    TrendReportResponse,
    DemographicOptions,
    SegmentOptions,
    ActivityCreate,
    ActivityResponse,
    ActivityListResponse,
    ReportFilters,
)

router = APIRouter(prefix="/reports", tags=["reports"])


# ============== Aggregation Endpoints ==============

@router.post("/aggregate/by-tag", response_model=AggregatedReportResponse)
async def aggregate_by_tag(request: AggregateByTagRequest):
    """
    Aggregate performance metrics grouped by a tag field.
    
    Use this to generate bar charts showing pre/post scores by topic, treatment, biomarker, etc.
    """
    db = get_database()
    
    try:
        results = db.aggregate_performance_by_tag(
            group_by=request.group_by.value,
            topics=request.filters.topics,
            disease_states=request.filters.disease_states,
            disease_stages=request.filters.disease_stages,
            disease_types=request.filters.disease_types,
            treatment_lines=request.filters.treatment_lines,
            treatments=request.filters.treatments,
            biomarkers=request.filters.biomarkers,
            trials=request.filters.trials,
            activities=request.filters.activities,
            quarters=request.filters.quarters,
        )
        
        # Convert to response format with knowledge gain calculation
        data = []
        for r in results:
            knowledge_gain = None
            if r["avg_pre_score"] is not None and r["avg_post_score"] is not None:
                knowledge_gain = round(r["avg_post_score"] - r["avg_pre_score"], 1)
            
            data.append(AggregatedMetric(
                group_value=r["group_value"],
                avg_pre_score=r["avg_pre_score"],
                avg_post_score=r["avg_post_score"],
                knowledge_gain=knowledge_gain,
                total_n=r.get("total_pre_n", 0) + r.get("total_post_n", 0),
                question_count=r["question_count"]
            ))
        
        return AggregatedReportResponse(
            group_by=request.group_by.value,
            data=data,
            filters_applied=request.filters
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/aggregate/by-tag-with-segments", response_model=AggregatedReportResponse)
async def aggregate_by_tag_with_segments(request: AggregateByTagWithSegmentsRequest):
    """
    Aggregate performance metrics grouped by a tag field AND audience segments.

    Returns data with both group_value (e.g., topic) and segment (e.g., 'community')
    so you can compare how different audience segments perform within each tag group.

    Example: Get performance by Topic for Community Oncs vs Academic Oncs
    """
    db = get_database()

    try:
        # Convert enum values to strings
        segments = [s.value if hasattr(s, 'value') else s for s in request.segments]

        results = db.aggregate_performance_by_tag_and_segment(
            group_by=request.group_by.value,
            segments=segments,
            topics=request.filters.topics,
            disease_states=request.filters.disease_states,
            disease_stages=request.filters.disease_stages,
            disease_types=request.filters.disease_types,
            treatment_lines=request.filters.treatment_lines,
            treatments=request.filters.treatments,
            biomarkers=request.filters.biomarkers,
            trials=request.filters.trials,
            activities=request.filters.activities,
            quarters=request.filters.quarters,
        )

        # Convert to response format with knowledge gain calculation
        data = []
        for r in results:
            knowledge_gain = None
            if r["avg_pre_score"] is not None and r["avg_post_score"] is not None:
                knowledge_gain = round(r["avg_post_score"] - r["avg_pre_score"], 1)

            data.append(AggregatedMetric(
                group_value=r["group_value"],
                segment=r["segment"],
                avg_pre_score=r["avg_pre_score"],
                avg_post_score=r["avg_post_score"],
                knowledge_gain=knowledge_gain,
                total_n=r.get("total_pre_n", 0) + r.get("total_post_n", 0),
                question_count=r["question_count"]
            ))

        return AggregatedReportResponse(
            group_by=request.group_by.value,
            segments=segments,
            data=data,
            filters_applied=request.filters
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/aggregate/by-demographic", response_model=AggregatedReportResponse)
async def aggregate_by_demographic(request: AggregateByDemographicRequest):
    """
    Aggregate performance metrics grouped by a demographic segment.
    
    Use this to generate bar charts showing pre/post scores by specialty, practice setting, or region.
    """
    db = get_database()
    
    try:
        results = db.aggregate_performance_by_demographic(
            segment_by=request.segment_by.value,
            topics=request.filters.topics,
            disease_states=request.filters.disease_states,
            treatments=request.filters.treatments,
            biomarkers=request.filters.biomarkers,
            activities=request.filters.activities,
            quarters=request.filters.quarters,
        )
        
        # Convert to response format
        data = []
        for r in results:
            knowledge_gain = None
            if r["avg_pre_score"] is not None and r["avg_post_score"] is not None:
                knowledge_gain = round(r["avg_post_score"] - r["avg_pre_score"], 1)
            
            data.append(AggregatedMetric(
                group_value=r["segment_value"],
                avg_pre_score=r["avg_pre_score"],
                avg_post_score=r["avg_post_score"],
                knowledge_gain=knowledge_gain,
                total_n=r["total_n"],
                question_count=r["question_count"]
            ))
        
        return AggregatedReportResponse(
            group_by=request.segment_by.value,
            data=data,
            filters_applied=request.filters
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/aggregate/by-segment", response_model=SegmentReportResponse)
async def aggregate_by_segment(request: AggregateBySegmentRequest):
    """
    Aggregate performance metrics grouped by audience segment.

    Available segments:
    - overall: All respondents combined
    - medical_oncologist: Medical oncologists only
    - app: Advanced Practice Providers
    - academic: Academic setting practitioners
    - community: Community setting practitioners
    - surgical_oncologist: Surgical oncologists
    - radiation_oncologist: Radiation oncologists

    Use this to compare performance across different audience types.
    """
    db = get_database()

    try:
        # Convert enum values to strings if needed
        segments = [s.value if hasattr(s, 'value') else s for s in request.segments] if request.segments else None

        results = db.aggregate_performance_by_segment(
            segments=segments,
            topics=request.filters.topics if request.filters else None,
            disease_states=request.filters.disease_states if request.filters else None,
            disease_stages=request.filters.disease_stages if request.filters else None,
            disease_types=request.filters.disease_types if request.filters else None,
            treatment_lines=request.filters.treatment_lines if request.filters else None,
            treatments=request.filters.treatments if request.filters else None,
            biomarkers=request.filters.biomarkers if request.filters else None,
            trials=request.filters.trials if request.filters else None,
            activities=request.filters.activities if request.filters else None,
            quarters=request.filters.quarters if request.filters else None,
        )

        # Convert to response format
        data = []
        for r in results:
            knowledge_gain = None
            if r["avg_pre_score"] is not None and r["avg_post_score"] is not None:
                knowledge_gain = round(r["avg_post_score"] - r["avg_pre_score"], 1)

            data.append(AggregatedMetric(
                group_value=r["segment"],
                avg_pre_score=r["avg_pre_score"],
                avg_post_score=r["avg_post_score"],
                knowledge_gain=knowledge_gain,
                total_n=r.get("total_pre_n", 0) + r.get("total_post_n", 0),
                question_count=r["question_count"]
            ))

        return SegmentReportResponse(
            data=data,
            filters_applied=request.filters
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/options/segments", response_model=SegmentOptions)
async def get_segment_options():
    """Get available audience segments with question counts."""
    db = get_database()
    segments = db.get_available_segments()
    return SegmentOptions(segments=segments)


@router.post("/trends", response_model=TrendReportResponse)
async def get_trends(request: TrendRequest):
    """
    Get performance trends over time (by quarter).

    Use this to generate line charts showing how performance changes across quarters.
    Optionally segment by specialty, practice setting, or region.
    """
    db = get_database()
    
    results = db.get_performance_trends(
        segment_by=request.segment_by.value if request.segment_by else None,
        topics=request.filters.topics,
        disease_states=request.filters.disease_states,
        treatments=request.filters.treatments,
        biomarkers=request.filters.biomarkers,
    )
    
    data = [
        TrendDataPoint(
            quarter=r["quarter"],
            segment_value=r["segment_value"],
            avg_pre_score=r["avg_pre_score"],
            avg_post_score=r["avg_post_score"],
            total_n=r["total_n"]
        )
        for r in results
    ]
    
    return TrendReportResponse(
        segment_by=request.segment_by.value if request.segment_by else None,
        data=data,
        filters_applied=request.filters
    )


# ============== Filter Options Endpoints ==============

@router.get("/options/demographics", response_model=DemographicOptions)
async def get_demographic_options():
    """Get available demographic filter options."""
    db = get_database()
    
    options = db.get_demographic_options()
    quarters = db.get_available_quarters()
    
    return DemographicOptions(
        specialties=options.get("specialties", []),
        practice_settings=options.get("practice_settings", []),
        regions=options.get("regions", []),
        practice_states=options.get("practice_states", []),
        quarters=quarters
    )


# ============== Activity Management Endpoints ==============

@router.get("/activities", response_model=ActivityListResponse)
async def list_activities(
    quarter: Optional[str] = None,
    has_date: Optional[bool] = None
):
    """List all activities with optional filters."""
    db = get_database()
    
    activities = db.list_activities(quarter=quarter, has_date=has_date)
    
    return ActivityListResponse(
        activities=[
            ActivityResponse(
                id=a["id"],
                activity_name=a["activity_name"],
                activity_date=a["activity_date"],
                quarter=a["quarter"],
                target_audience=a["target_audience"],
                description=a["description"],
                question_count=a["question_count"],
                created_at=a["created_at"]
            )
            for a in activities
        ],
        total=len(activities)
    )


@router.get("/activities/{activity_id}", response_model=ActivityResponse)
async def get_activity(activity_id: int):
    """Get activity by ID."""
    db = get_database()
    
    activity = db.get_activity(activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    return ActivityResponse(
        id=activity["id"],
        activity_name=activity["activity_name"],
        activity_date=activity["activity_date"],
        quarter=activity["quarter"],
        target_audience=activity["target_audience"],
        description=activity["description"],
        question_count=activity["question_count"],
        created_at=activity["created_at"]
    )


@router.put("/activities/{activity_name}", response_model=ActivityResponse)
async def update_activity(activity_name: str, activity: ActivityCreate):
    """Update activity metadata (date, target audience, description)."""
    db = get_database()
    
    # Upsert the activity metadata
    activity_id = db.upsert_activity_metadata(
        activity_name=activity_name,
        activity_date=activity.activity_date,
        target_audience=activity.target_audience,
        description=activity.description
    )
    
    # Fetch and return the updated activity
    updated = db.get_activity(activity_id)
    
    return ActivityResponse(
        id=updated["id"],
        activity_name=updated["activity_name"],
        activity_date=updated["activity_date"],
        quarter=updated["quarter"],
        target_audience=updated["target_audience"],
        description=updated["description"],
        question_count=updated["question_count"],
        created_at=updated["created_at"]
    )


# ============== Quick Stats Endpoint ==============

@router.get("/stats/summary")
async def get_report_stats():
    """Get summary statistics for report generation capabilities."""
    db = get_database()
    
    stats = db.get_stats()
    tag_options = db.get_filter_options()
    demo_options = db.get_demographic_options()
    quarters = db.get_available_quarters()
    
    return {
        "database": stats,
        "available_filters": {
            "topics": len(tag_options.get("topics", [])),
            "disease_states": len(tag_options.get("disease_states", [])),
            "treatments": len(tag_options.get("treatments", [])),
            "biomarkers": len(tag_options.get("biomarkers", [])),
            "trials": len(tag_options.get("trials", [])),
            "activities": len(tag_options.get("activities", [])),
        },
        "available_demographics": {
            "specialties": len(demo_options.get("specialties", [])),
            "practice_settings": len(demo_options.get("practice_settings", [])),
            "regions": len(demo_options.get("regions", [])),
            "quarters": len(quarters),
        },
        "report_ready": stats.get("demographic_records", 0) > 0 or stats.get("questions_with_performance", 0) > 0
    }


# ============== Export Endpoints ==============

@router.post("/export/questions")
async def export_questions_for_report(request: ReportFilters):
    """
    Get all questions matching the report filters for Excel export.
    Returns full question details including tags and performance data.
    """
    db = get_database()

    questions = db.get_questions_for_export(
        topics=request.topics,
        disease_states=request.disease_states,
        disease_stages=request.disease_stages,
        disease_types=request.disease_types,
        treatment_lines=request.treatment_lines,
        treatments=request.treatments,
        biomarkers=request.biomarkers,
        trials=request.trials,
        activities=request.activities,
    )

    return {"questions": questions, "total": len(questions)}









