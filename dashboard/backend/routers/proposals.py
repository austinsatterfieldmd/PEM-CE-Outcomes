"""
Tag proposal API endpoints.

Provides endpoints for:
- Creating tag proposals with keyword search
- Listing proposals with status filters
- Reviewing proposal candidates (approve/skip)
- Applying approved tags to questions
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import logging

from ..services.database import get_database

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/proposals", tags=["tag-proposals"])


# ========== Pydantic Models ==========

class ProposalCandidate(BaseModel):
    id: int
    question_id: int
    match_score: float
    current_value: Optional[str] = None
    decision: str  # 'pending', 'approved', 'skipped'
    decided_at: Optional[str] = None
    decided_by: Optional[str] = None
    notes: Optional[str] = None
    question_stem: Optional[str] = None
    source_id: Optional[str] = None
    correct_answer: Optional[str] = None


class TagProposal(BaseModel):
    id: int
    field_name: str
    proposed_value: str
    search_query: Optional[str] = None
    proposal_reason: Optional[str] = None
    status: str  # 'pending', 'reviewing', 'ready_to_apply', 'applied', 'abandoned'
    match_count: int = 0
    approved_count: int = 0
    created_at: Optional[str] = None
    created_by: Optional[str] = None
    completed_at: Optional[str] = None
    candidates: List[ProposalCandidate] = []


class ProposalStats(BaseModel):
    total: int
    pending: int
    reviewing: int
    ready_to_apply: int
    applied: int
    abandoned: int


class CreateProposalRequest(BaseModel):
    field_name: str
    proposed_value: str
    search_query: str
    proposal_reason: str = ""
    created_by: Optional[str] = None


class ReviewCandidatesRequest(BaseModel):
    approved_ids: List[int] = []
    skipped_ids: List[int] = []
    reviewed_by: Optional[str] = None


class ApplyProposalRequest(BaseModel):
    reviewed_by: Optional[str] = None


# ========== Endpoints ==========

@router.get("/stats", response_model=ProposalStats)
def get_proposal_stats():
    """Get tag proposal statistics."""
    db = get_database()
    return db.get_proposal_stats()


@router.get("", response_model=List[TagProposal])
def list_proposals(status: Optional[str] = None):
    """
    List tag proposals.

    Args:
        status: Filter by status ('pending', 'reviewing', 'ready_to_apply', 'applied', 'abandoned')
    """
    db = get_database()
    proposals = db.get_tag_proposals(status=status)
    return proposals


@router.post("", response_model=TagProposal)
def create_proposal(request: CreateProposalRequest):
    """
    Create a new tag proposal and find matching candidates.

    This will:
    1. Create a proposal record
    2. Search questions using the provided keyword
    3. Create candidate records for matching questions
    """
    db = get_database()
    proposal = db.create_tag_proposal(
        field_name=request.field_name,
        proposed_value=request.proposed_value,
        search_query=request.search_query,
        proposal_reason=request.proposal_reason,
        created_by=request.created_by
    )
    return proposal


@router.get("/{proposal_id}", response_model=TagProposal)
def get_proposal(proposal_id: int):
    """Get a single proposal with all candidate questions."""
    db = get_database()
    proposal = db.get_proposal_with_candidates(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return proposal


@router.post("/{proposal_id}/review")
def review_candidates(proposal_id: int, request: ReviewCandidatesRequest):
    """
    Review proposal candidates - approve or skip them.

    Args:
        proposal_id: The proposal to review
        request: Contains lists of candidate IDs to approve or skip
    """
    db = get_database()

    # Verify proposal exists
    proposal = db.get_proposal_with_candidates(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    # Verify candidate IDs belong to this proposal
    candidate_ids = {c["id"] for c in proposal["candidates"]}
    for cid in request.approved_ids + request.skipped_ids:
        if cid not in candidate_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Candidate {cid} does not belong to this proposal"
            )

    result = db.review_proposal_candidates(
        proposal_id=proposal_id,
        approved_ids=request.approved_ids,
        skipped_ids=request.skipped_ids,
        reviewed_by=request.reviewed_by
    )
    return result


@router.post("/{proposal_id}/apply")
def apply_proposal(proposal_id: int, request: ApplyProposalRequest):
    """
    Apply approved tags to the database.

    This will:
    1. Update the tag field for all approved candidate questions
    2. Mark the proposal as 'applied'
    """
    db = get_database()

    # Verify proposal exists
    proposal = db.get_proposal_with_candidates(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    # Verify there are approved candidates
    if proposal["approved_count"] == 0:
        raise HTTPException(
            status_code=400,
            detail="No approved candidates to apply"
        )

    try:
        result = db.apply_proposal(
            proposal_id=proposal_id,
            reviewed_by=request.reviewed_by
        )
        return result
    except Exception as e:
        logger.error(f"Failed to apply proposal {proposal_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{proposal_id}")
def abandon_proposal(proposal_id: int):
    """Abandon a proposal (mark as abandoned without applying)."""
    db = get_database()

    # Verify proposal exists
    proposal = db.get_proposal_with_candidates(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    if proposal["status"] == "applied":
        raise HTTPException(
            status_code=400,
            detail="Cannot abandon an already applied proposal"
        )

    success = db.abandon_proposal(proposal_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to abandon proposal")

    return {"status": "abandoned", "proposal_id": proposal_id}
