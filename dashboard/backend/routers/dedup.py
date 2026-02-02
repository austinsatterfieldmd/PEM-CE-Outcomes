"""
Deduplication review API endpoints.

Provides endpoints for:
- Listing duplicate clusters
- Reviewing cluster details
- Confirming/rejecting duplicates
- Setting canonical questions
- Importing dedup reports
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import logging

from ..services.database import get_database

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dedup", tags=["deduplication"])


# ========== Pydantic Models ==========

class ClusterMember(BaseModel):
    question_id: int
    source_id: Optional[str] = None
    similarity_to_canonical: Optional[float] = None
    is_canonical: bool = False
    question_stem: Optional[str] = None
    correct_answer: Optional[str] = None
    incorrect_answers: Optional[List[str]] = None
    source_file: Optional[str] = None


class DuplicateCluster(BaseModel):
    cluster_id: int
    canonical_question_id: Optional[int] = None
    canonical_source_id: Optional[str] = None
    status: str  # 'pending', 'confirmed', 'rejected'
    similarity_threshold: Optional[float] = None
    created_at: Optional[str] = None
    reviewed_at: Optional[str] = None
    reviewed_by: Optional[str] = None
    member_count: Optional[int] = None
    members: List[ClusterMember] = []


class DedupStats(BaseModel):
    total_clusters: int
    pending_clusters: int
    confirmed_clusters: int
    rejected_clusters: int
    duplicate_questions: int


class ConfirmClusterRequest(BaseModel):
    canonical_question_id: int
    selected_question_ids: Optional[List[int]] = None  # If provided, only confirm these as duplicates
    reviewed_by: Optional[str] = None


class RejectClusterRequest(BaseModel):
    reviewed_by: Optional[str] = None


class ImportReportRequest(BaseModel):
    report_path: str


class CreateClusterRequest(BaseModel):
    question_ids: List[int]
    similarity_threshold: float = 0.90
    canonical_question_id: Optional[int] = None


class DuplicateCandidate(BaseModel):
    id: int
    source_id: Optional[str] = None
    question_stem: Optional[str] = None
    correct_answer: Optional[str] = None
    disease_state: Optional[str] = None
    topic: Optional[str] = None


# ========== Endpoints ==========

@router.get("/stats", response_model=DedupStats)
def get_dedup_stats():
    """Get deduplication statistics."""
    db = get_database()
    return db.get_dedup_stats()


@router.get("/clusters", response_model=List[DuplicateCluster])
def list_clusters(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    List duplicate clusters.

    Args:
        status: Filter by status ('pending', 'confirmed', 'rejected')
        limit: Max clusters to return
        offset: Pagination offset
    """
    db = get_database()
    clusters = db.get_duplicate_clusters(status=status, limit=limit, offset=offset)
    return clusters


@router.get("/clusters/{cluster_id}", response_model=DuplicateCluster)
def get_cluster(cluster_id: int):
    """Get a single cluster with full question details."""
    db = get_database()
    cluster = db.get_duplicate_cluster(cluster_id)
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    return cluster


@router.post("/clusters", response_model=dict)
def create_cluster(request: CreateClusterRequest):
    """Create a new duplicate cluster manually."""
    db = get_database()
    cluster_id = db.create_duplicate_cluster(
        question_ids=request.question_ids,
        similarity_threshold=request.similarity_threshold,
        canonical_question_id=request.canonical_question_id
    )
    return {"cluster_id": cluster_id, "status": "created"}


@router.post("/clusters/{cluster_id}/confirm")
def confirm_cluster(cluster_id: int, request: ConfirmClusterRequest):
    """
    Confirm a duplicate cluster and set the canonical question.

    This will:
    1. Mark the cluster as confirmed
    2. Set the canonical question
    3. Update all non-canonical questions' canonical_source_id

    If selected_question_ids is provided (partial confirmation):
    - Only confirm selected questions as duplicates
    - Remove unselected questions from the cluster
    """
    db = get_database()

    # Verify cluster exists
    cluster = db.get_duplicate_cluster(cluster_id)
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    # Verify canonical question is in cluster
    member_ids = [m["question_id"] for m in cluster["members"]]
    if request.canonical_question_id not in member_ids:
        raise HTTPException(
            status_code=400,
            detail="Canonical question must be a member of the cluster"
        )

    # If partial confirmation, verify selected questions are in cluster
    selected_ids = request.selected_question_ids
    if selected_ids:
        if request.canonical_question_id not in selected_ids:
            raise HTTPException(
                status_code=400,
                detail="Canonical question must be in selected questions"
            )
        for qid in selected_ids:
            if qid not in member_ids:
                raise HTTPException(
                    status_code=400,
                    detail=f"Selected question {qid} is not a member of the cluster"
                )
        if len(selected_ids) < 2:
            raise HTTPException(
                status_code=400,
                detail="Must select at least 2 questions as duplicates"
            )

    success = db.confirm_duplicate_cluster(
        cluster_id=cluster_id,
        canonical_question_id=request.canonical_question_id,
        selected_question_ids=selected_ids,
        reviewed_by=request.reviewed_by
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to confirm cluster")

    return {"status": "confirmed", "canonical_question_id": request.canonical_question_id}


@router.post("/clusters/{cluster_id}/reject")
def reject_cluster(cluster_id: int, request: RejectClusterRequest):
    """Reject a duplicate cluster (mark as not actually duplicates)."""
    db = get_database()

    # Verify cluster exists
    cluster = db.get_duplicate_cluster(cluster_id)
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    success = db.reject_duplicate_cluster(
        cluster_id=cluster_id,
        reviewed_by=request.reviewed_by
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to reject cluster")

    return {"status": "rejected"}


@router.post("/import")
def import_dedup_report(request: ImportReportRequest):
    """
    Import duplicates from a dedup report JSON file.

    The report should have a 'duplicates' array with objects containing:
    - canonical_source_id (or canonical_id): QGD of the canonical question
    - duplicate_source_id (or duplicate_id): QGD of the duplicate
    - similarity: Similarity score
    """
    import os

    if not os.path.exists(request.report_path):
        raise HTTPException(status_code=404, detail=f"Report file not found: {request.report_path}")

    db = get_database()
    try:
        clusters_created = db.import_dedup_report(request.report_path)
        return {
            "status": "imported",
            "clusters_created": clusters_created
        }
    except Exception as e:
        logger.error(f"Failed to import dedup report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search", response_model=List[DuplicateCandidate])
def search_duplicate_candidates(
    query: str,
    exclude_id: Optional[int] = None,
    limit: int = 50
):
    """
    Search for potential duplicate candidates using keyword search.

    This searches question_stem and correct_answer fields.
    Used when manually creating a dedup cluster.

    Args:
        query: Keyword to search for
        exclude_id: Question ID to exclude from results (the source question)
        limit: Max results to return
    """
    db = get_database()
    candidates = db.search_duplicate_candidates(
        query=query,
        exclude_id=exclude_id,
        limit=limit
    )
    return candidates
