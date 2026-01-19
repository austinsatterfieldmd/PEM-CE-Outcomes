"""
Novel Entities API endpoints for Automated CE Outcomes Dashboard.

Provides endpoints for reviewing and managing novel entities extracted by LLM
that are not yet in the static knowledge base.

Migrated from V2 with updated imports for V3 structure.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import math

from ..services.database import get_database
from ..schemas import (
    EntityType,
    EntityStatus,
    NovelEntityCreate,
    NovelEntitySummary,
    NovelEntityDetail,
    NovelEntityOccurrence,
    NovelEntityApproval,
    NovelEntityRejection,
    BulkApprovalRequest,
    NovelEntityListResponse,
    NovelEntityStats,
)

router = APIRouter(prefix="/novel-entities", tags=["novel-entities"])


# ============== List & Search ==============

@router.get("/", response_model=NovelEntityListResponse)
async def list_novel_entities(
    status: Optional[str] = Query(None, description="Filter by status: pending, approved, auto_approved, rejected"),
    entity_type: Optional[str] = Query(None, description="Filter by type: treatment, trial, disease, biomarker"),
    min_confidence: Optional[float] = Query(None, ge=0, le=1, description="Minimum confidence threshold"),
    min_occurrences: Optional[int] = Query(None, ge=1, description="Minimum occurrence count"),
    search: Optional[str] = Query(None, description="Search entity names"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("occurrence_count", description="Sort field"),
    sort_desc: bool = Query(True, description="Sort descending")
):
    """
    List novel entities with filters and pagination.

    Use this to view the queue of entities awaiting review or to browse
    approved/rejected entities.
    """
    db = get_database()

    entities, total = db.list_novel_entities(
        status=status,
        entity_type=entity_type,
        min_confidence=min_confidence,
        min_occurrences=min_occurrences,
        search_query=search,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_desc=sort_desc
    )

    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return NovelEntityListResponse(
        entities=[
            NovelEntitySummary(
                id=e["id"],
                entity_name=e["entity_name"],
                entity_type=e["entity_type"],
                normalized_name=e.get("normalized_name"),
                confidence=e.get("confidence"),
                occurrence_count=e.get("occurrence_count", 1),
                first_seen=e.get("first_seen"),
                last_seen=e.get("last_seen"),
                status=e.get("status", "pending"),
                drug_class=e.get("drug_class"),
                synonyms=e.get("synonyms", []),
                notes=e.get("notes")
            )
            for e in entities
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/stats", response_model=NovelEntityStats)
async def get_novel_entity_stats():
    """
    Get statistics about novel entities.

    Use this to display dashboard counters showing pending entities,
    entities ready for auto-approval, etc.
    """
    db = get_database()
    stats = db.get_novel_entity_stats()

    return NovelEntityStats(**stats)


# ============== Detail ==============

@router.get("/{entity_id}", response_model=NovelEntityDetail)
async def get_novel_entity(entity_id: int):
    """
    Get full details of a novel entity including all occurrences.

    Use this to review the entity in context before approving/rejecting.
    """
    db = get_database()

    entity = db.get_novel_entity_detail(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Novel entity not found")

    return NovelEntityDetail(
        id=entity["id"],
        entity_name=entity["entity_name"],
        entity_type=entity["entity_type"],
        normalized_name=entity.get("normalized_name"),
        confidence=entity.get("confidence"),
        occurrence_count=entity.get("occurrence_count", 1),
        first_seen=entity.get("first_seen"),
        last_seen=entity.get("last_seen"),
        status=entity.get("status", "pending"),
        drug_class=entity.get("drug_class"),
        synonyms=entity.get("synonyms", []),
        notes=entity.get("notes"),
        reviewed_by=entity.get("reviewed_by"),
        reviewed_at=entity.get("reviewed_at"),
        occurrences=[
            NovelEntityOccurrence(
                id=occ["id"],
                question_id=occ.get("question_id"),
                source_text=occ.get("source_text", ""),
                extraction_confidence=occ.get("extraction_confidence"),
                created_at=occ.get("created_at"),
                question_stem=occ.get("question_stem"),
                correct_answer=occ.get("correct_answer")
            )
            for occ in entity.get("occurrences", [])
        ]
    )


# ============== Approval/Rejection ==============

@router.post("/{entity_id}/approve")
async def approve_novel_entity(entity_id: int, approval: NovelEntityApproval):
    """
    Approve a novel entity for addition to the knowledge base.

    After approval, the entity will be included in the next KB update.
    Optionally specify drug_class (for treatments) and synonyms.
    """
    db = get_database()

    # Verify entity exists
    entity = db.get_novel_entity_detail(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Novel entity not found")

    success = db.approve_novel_entity(
        entity_id=entity_id,
        reviewed_by=approval.reviewed_by,
        drug_class=approval.drug_class,
        synonyms=approval.synonyms
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to approve entity")

    return {
        "success": True,
        "message": f"Entity '{entity['entity_name']}' approved",
        "entity_id": entity_id
    }


@router.post("/{entity_id}/reject")
async def reject_novel_entity(entity_id: int, rejection: NovelEntityRejection):
    """
    Reject a novel entity.

    Rejected entities are excluded from KB updates and future tagging.
    """
    db = get_database()

    # Verify entity exists
    entity = db.get_novel_entity_detail(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Novel entity not found")

    success = db.reject_novel_entity(
        entity_id=entity_id,
        reviewed_by=rejection.reviewed_by,
        notes=rejection.notes
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to reject entity")

    return {
        "success": True,
        "message": f"Entity '{entity['entity_name']}' rejected",
        "entity_id": entity_id
    }


# ============== Bulk Operations ==============

@router.post("/bulk-approve")
async def bulk_approve_entities(request: BulkApprovalRequest):
    """
    Auto-approve entities meeting confidence and occurrence thresholds.

    Default thresholds: confidence >= 0.90 AND occurrences >= 3
    """
    db = get_database()

    approved_count = db.bulk_approve_novel_entities(
        min_confidence=request.min_confidence,
        min_occurrences=request.min_occurrences,
        reviewed_by=request.reviewed_by
    )

    return {
        "success": True,
        "approved_count": approved_count,
        "thresholds": {
            "min_confidence": request.min_confidence,
            "min_occurrences": request.min_occurrences
        }
    }


# ============== KB Export ==============

@router.get("/export/approved")
async def export_approved_entities(
    entity_type: Optional[str] = Query(None, description="Filter by type")
):
    """
    Export all approved entities ready to be added to KB.

    Use this to get the data needed for KB update scripts.
    """
    db = get_database()

    entities = db.get_approved_entities_for_kb(entity_type=entity_type)

    # Group by type for easier KB integration
    grouped = {}
    for e in entities:
        etype = e["entity_type"]
        if etype not in grouped:
            grouped[etype] = []
        grouped[etype].append({
            "name": e["normalized_name"] or e["entity_name"],
            "original_name": e["entity_name"],
            "drug_class": e.get("drug_class"),
            "synonyms": e.get("synonyms", [])
        })

    return {
        "total": len(entities),
        "by_type": grouped
    }
