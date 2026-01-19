"""
Pydantic models for the Automated CE Outcomes Dashboard API.

V3 includes new models for 3-model voting, review workflow, and prompt tracking.
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime, date
from enum import Enum


# ============== Question Models ==============

class PerformanceMetric(BaseModel):
    """Performance metrics for a single audience segment."""
    segment: str = Field(..., description="Audience segment (e.g., 'overall', 'medical_oncologists')")
    pre_score: Optional[float] = Field(None, description="Pre-test score percentage")
    post_score: Optional[float] = Field(None, description="Post-test score percentage")
    pre_n: Optional[int] = Field(None, description="Pre-test sample size")
    post_n: Optional[int] = Field(None, description="Post-test sample size")

    @property
    def knowledge_gain(self) -> Optional[float]:
        """Calculate knowledge gain (post - pre)."""
        if self.pre_score is not None and self.post_score is not None:
            return self.post_score - self.pre_score
        return None


class TagInfo(BaseModel):
    """Tag information with confidence score."""
    topic: Optional[str] = None
    topic_confidence: Optional[float] = None
    topic_method: Optional[str] = None
    disease_state: Optional[str] = None
    disease_state_confidence: Optional[float] = None
    disease_stage: Optional[str] = None
    disease_stage_confidence: Optional[float] = None
    disease_type: Optional[str] = None
    disease_type_confidence: Optional[float] = None
    treatment_line: Optional[str] = None
    treatment_line_confidence: Optional[float] = None
    treatment: Optional[str] = None
    treatment_confidence: Optional[float] = None
    biomarker: Optional[str] = None
    biomarker_confidence: Optional[float] = None
    trial: Optional[str] = None
    trial_confidence: Optional[float] = None
    needs_review: Optional[bool] = None
    review_flags: Optional[List[str]] = None
    flagged_at: Optional[datetime] = None


class TagUpdate(BaseModel):
    """Request model for updating tags on a question."""
    topic: Optional[str] = None
    disease_state: Optional[str] = None
    disease_stage: Optional[str] = None
    disease_type: Optional[str] = None
    treatment_line: Optional[str] = None
    treatment: Optional[str] = None
    biomarker: Optional[str] = None
    trial: Optional[str] = None
    question_stem: Optional[str] = Field(None, description="Updated question stem (admin only)")
    mark_as_reviewed: Optional[bool] = False


class FlagQuestionRequest(BaseModel):
    """Request model for flagging a question for review."""
    reasons: List[str] = Field(..., description="Reasons for flagging (e.g., 'May not be oncology', 'Tag errors', 'Question errors')")


class UpdateOncologyStatusRequest(BaseModel):
    """Request model for updating oncology status."""
    is_oncology: bool = Field(..., description="Whether the question is oncology-related")


class QuestionBase(BaseModel):
    """Base question model."""
    question_stem: str
    correct_answer: Optional[str] = None
    incorrect_answers: Optional[List[str]] = None


class QuestionCreate(QuestionBase):
    """Model for creating a new question."""
    activities: Optional[List[str]] = None
    source_file: Optional[str] = None


class QuestionSummary(BaseModel):
    """Summary view of a question for list display."""
    id: int
    question_stem: str
    topic: Optional[str] = None
    topic_confidence: Optional[float] = None
    disease_state: Optional[str] = None
    disease_state_confidence: Optional[float] = None
    treatment: Optional[str] = None
    pre_score: Optional[float] = Field(None, description="Overall pre-test score")
    post_score: Optional[float] = Field(None, description="Overall post-test score")
    knowledge_gain: Optional[float] = Field(None, description="Post - Pre score")
    sample_size: Optional[int] = Field(None, description="Total sample size (pre_n + post_n)")
    activity_count: int = Field(0, description="Number of activities using this question")


class QuestionDetail(BaseModel):
    """Full detail view of a question."""
    id: int
    question_stem: str
    correct_answer: Optional[str] = None
    incorrect_answers: Optional[List[str]] = None
    source_file: Optional[str] = None

    # Tags with confidence
    tags: TagInfo

    # Performance by segment
    performance: List[PerformanceMetric] = []

    # Activities
    activities: List[str] = []


# ============== Search & Filter Models ==============

class SearchFilters(BaseModel):
    """Search and filter parameters."""
    query: Optional[str] = Field(None, description="Full-text search query")
    topics: Optional[List[str]] = Field(None, description="Filter by topic(s)")
    disease_states: Optional[List[str]] = Field(None, description="Filter by disease state(s)")
    disease_stages: Optional[List[str]] = Field(None, description="Filter by disease stage(s)")
    disease_types: Optional[List[str]] = Field(None, description="Filter by disease type(s)")
    treatment_lines: Optional[List[str]] = Field(None, description="Filter by treatment line(s)")
    treatments: Optional[List[str]] = Field(None, description="Filter by treatment(s)")
    biomarkers: Optional[List[str]] = Field(None, description="Filter by biomarker(s)")
    trials: Optional[List[str]] = Field(None, description="Filter by trial(s)")
    activities: Optional[List[str]] = Field(None, description="Filter by activity(s)")
    min_confidence: Optional[float] = Field(None, ge=0, le=1, description="Minimum confidence threshold")
    max_confidence: Optional[float] = Field(None, ge=0, le=1, description="Maximum confidence threshold")
    has_performance_data: Optional[bool] = Field(None, description="Filter to questions with performance data")
    min_sample_size: Optional[int] = Field(None, ge=0, description="Minimum sample size (pre_n + post_n)")
    needs_review: Optional[bool] = Field(None, description="Filter to questions that need review")
    review_flag_filter: Optional[str] = Field(None, description="Filter by review flag type (not_oncology, tag_errors, question_errors)")


class PaginationParams(BaseModel):
    """Pagination parameters."""
    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")


class SearchRequest(BaseModel):
    """Combined search request with filters and pagination."""
    filters: SearchFilters = Field(default_factory=SearchFilters)
    pagination: PaginationParams = Field(default_factory=PaginationParams)
    sort_by: str = Field("id", description="Sort field")
    sort_desc: bool = Field(False, description="Sort descending")


class SearchResponse(BaseModel):
    """Search results response."""
    questions: List[QuestionSummary]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============== Export Models ==============

class QuestionExport(BaseModel):
    """Question data for export with all tags and activities."""
    id: int
    question_stem: str
    correct_answer: Optional[str] = None
    incorrect_answers: Optional[str] = Field(None, description="Pipe-separated list of incorrect answers")
    topic: Optional[str] = None
    disease_state: Optional[str] = None
    disease_type: Optional[str] = None
    disease_stage: Optional[str] = None
    treatment: Optional[str] = None
    treatment_line: Optional[str] = None
    biomarker: Optional[str] = None
    trial: Optional[str] = None
    pre_score: Optional[float] = None
    post_score: Optional[float] = None
    knowledge_gain: Optional[float] = None
    sample_size: Optional[int] = None
    activities: Optional[str] = Field(None, description="Semicolon-separated list of activity names")


class ExportResponse(BaseModel):
    """Response for export endpoint."""
    questions: List[QuestionExport]
    total: int


# ============== Filter Options Models ==============

class FilterOptions(BaseModel):
    """Available filter options with counts."""
    topics: List[dict] = Field(default_factory=list, description="Available topics with counts")
    disease_states: List[dict] = Field(default_factory=list)
    disease_stages: List[dict] = Field(default_factory=list)
    disease_types: List[dict] = Field(default_factory=list)
    treatment_lines: List[dict] = Field(default_factory=list)
    treatments: List[dict] = Field(default_factory=list)
    biomarkers: List[dict] = Field(default_factory=list)
    trials: List[dict] = Field(default_factory=list)
    activities: List[dict] = Field(default_factory=list)


# ============== Analytics Models ==============

class PerformanceAnalytics(BaseModel):
    """Aggregated performance analytics."""
    segment: str
    avg_pre_score: Optional[float] = None
    avg_post_score: Optional[float] = None
    avg_knowledge_gain: Optional[float] = None
    total_questions: int = 0
    questions_with_gain: int = 0


class TagDistribution(BaseModel):
    """Distribution of values for a tag category."""
    tag_name: str
    values: List[dict] = Field(default_factory=list, description="List of {value, count} pairs")


# ============== Activity Models ==============

class ActivityBase(BaseModel):
    """Base activity model."""
    activity_name: str
    activity_date: Optional[date] = None
    target_audience: Optional[str] = Field(None, description="Defines 'Key Learners' for this activity")
    description: Optional[str] = None


class ActivityCreate(ActivityBase):
    """Model for creating/updating an activity."""
    pass


class ActivityResponse(ActivityBase):
    """Activity response with additional metadata."""
    id: int
    quarter: Optional[str] = None
    question_count: int = 0
    created_at: Optional[datetime] = None


class ActivityListResponse(BaseModel):
    """List of activities."""
    activities: List[ActivityResponse]
    total: int


# ============== Report Models ==============

class TagGroupBy(str, Enum):
    """Valid fields to group by for tag-based reports."""
    TOPIC = "topic"
    DISEASE_STATE = "disease_state"
    DISEASE_STAGE = "disease_stage"
    DISEASE_TYPE = "disease_type"
    TREATMENT = "treatment"
    BIOMARKER = "biomarker"
    TRIAL = "trial"


class DemographicSegment(str, Enum):
    """Valid demographic segments."""
    SPECIALTY = "specialty"
    PRACTICE_SETTING = "practice_setting"
    REGION = "region"
    PRACTICE_STATE = "practice_state"


class AudienceSegment(str, Enum):
    """Valid audience segments (from the 7-segment data structure)."""
    OVERALL = "overall"
    MEDICAL_ONCOLOGIST = "medical_oncologist"
    APP = "app"
    ACADEMIC = "academic"
    COMMUNITY = "community"
    SURGICAL_ONCOLOGIST = "surgical_oncologist"
    RADIATION_ONCOLOGIST = "radiation_oncologist"


class ReportFilters(BaseModel):
    """Filters for report generation."""
    # Tag filters
    topics: Optional[List[str]] = Field(None, description="Filter by topic(s)")
    disease_states: Optional[List[str]] = Field(None, description="Filter by disease state(s)")
    disease_stages: Optional[List[str]] = Field(None, description="Filter by disease stage(s)")
    disease_types: Optional[List[str]] = Field(None, description="Filter by disease type(s)")
    treatment_lines: Optional[List[str]] = Field(None, description="Filter by treatment line(s)")
    treatments: Optional[List[str]] = Field(None, description="Filter by treatment(s)")
    biomarkers: Optional[List[str]] = Field(None, description="Filter by biomarker(s)")
    trials: Optional[List[str]] = Field(None, description="Filter by trial(s)")

    # Activity filters
    activities: Optional[List[str]] = Field(None, description="Filter by activity name(s)")
    quarters: Optional[List[str]] = Field(None, description="Filter by quarter(s), e.g., '2024 Q3'")

    # Demographic filters
    specialties: Optional[List[str]] = Field(None, description="Filter by specialty")
    practice_settings: Optional[List[str]] = Field(None, description="Filter by practice setting")
    regions: Optional[List[str]] = Field(None, description="Filter by region")

    # Audience segment filter
    segments: Optional[List[AudienceSegment]] = Field(None, description="Filter by audience segment(s)")


class AggregateByTagRequest(BaseModel):
    """Request for aggregating performance by a tag field."""
    group_by: TagGroupBy = Field(..., description="Tag field to group by")
    filters: ReportFilters = Field(default_factory=ReportFilters)


class AggregateByDemographicRequest(BaseModel):
    """Request for aggregating performance by a demographic segment."""
    segment_by: DemographicSegment = Field(..., description="Demographic field to segment by")
    filters: ReportFilters = Field(default_factory=ReportFilters)


class AggregateBySegmentRequest(BaseModel):
    """Request for aggregating performance by audience segment."""
    segments: Optional[List[AudienceSegment]] = Field(
        None,
        description="Specific segments to include (all if not specified)"
    )
    filters: Optional[ReportFilters] = Field(default_factory=ReportFilters)


class TrendRequest(BaseModel):
    """Request for performance trends over time."""
    segment_by: Optional[DemographicSegment] = Field(None, description="Optional demographic segmentation")
    filters: ReportFilters = Field(default_factory=ReportFilters)


class AggregatedMetric(BaseModel):
    """Single aggregated performance metric."""
    group_value: str = Field(..., description="The grouping value (e.g., topic name, specialty)")
    segment: Optional[str] = Field(None, description="Audience segment (when comparing segments)")
    avg_pre_score: Optional[float] = Field(None, description="Average pre-activity score")
    avg_post_score: Optional[float] = Field(None, description="Average post-activity score")
    knowledge_gain: Optional[float] = Field(None, description="Average knowledge gain (post - pre)")
    total_n: int = Field(0, description="Total number of respondents")
    question_count: int = Field(0, description="Number of questions in this group")


class AggregatedReportResponse(BaseModel):
    """Response for aggregated performance report."""
    group_by: str
    segments: Optional[List[str]] = Field(None, description="Segments included in comparison")
    data: List[AggregatedMetric]
    filters_applied: ReportFilters


class AggregateByTagWithSegmentsRequest(BaseModel):
    """Request for aggregating performance by a tag field with segment comparison."""
    group_by: TagGroupBy = Field(..., description="Tag field to group by")
    segments: List[AudienceSegment] = Field(..., description="Audience segments to compare")
    filters: ReportFilters = Field(default_factory=ReportFilters)


class SegmentReportResponse(BaseModel):
    """Response for audience segment performance report."""
    data: List[AggregatedMetric]
    filters_applied: Optional[ReportFilters] = None


class TrendDataPoint(BaseModel):
    """Single data point for trend charts."""
    quarter: str
    segment_value: str = Field("Overall", description="Segment name (e.g., 'Medical Oncology')")
    avg_pre_score: Optional[float] = None
    avg_post_score: Optional[float] = None
    total_n: int = 0


class TrendReportResponse(BaseModel):
    """Response for performance trend report."""
    segment_by: Optional[str] = None
    data: List[TrendDataPoint]
    filters_applied: ReportFilters


# ============== Demographic Options ==============

class DemographicOptions(BaseModel):
    """Available demographic filter options."""
    specialties: List[str] = Field(default_factory=list)
    practice_settings: List[str] = Field(default_factory=list)
    regions: List[str] = Field(default_factory=list)
    practice_states: List[str] = Field(default_factory=list)
    quarters: List[str] = Field(default_factory=list)


class SegmentInfo(BaseModel):
    """Information about an audience segment."""
    segment: str
    count: int


class SegmentOptions(BaseModel):
    """Available audience segment options with counts."""
    segments: List[SegmentInfo] = Field(default_factory=list)


# ============== Novel Entity Models ==============

class EntityType(str, Enum):
    """Valid entity types."""
    TREATMENT = "treatment"
    TRIAL = "trial"
    DISEASE = "disease"
    BIOMARKER = "biomarker"


class EntityStatus(str, Enum):
    """Novel entity review status."""
    PENDING = "pending"
    APPROVED = "approved"
    AUTO_APPROVED = "auto_approved"
    REJECTED = "rejected"


class NovelEntityCreate(BaseModel):
    """Request model for creating a novel entity."""
    entity_name: str = Field(..., description="The entity name as extracted")
    entity_type: EntityType = Field(..., description="Type of entity")
    confidence: float = Field(0.75, ge=0, le=1, description="Extraction confidence")
    question_id: Optional[int] = Field(None, description="Source question ID")
    source_text: Optional[str] = Field(None, description="Context text where entity was found")
    drug_class: Optional[str] = Field(None, description="Drug class for treatments")
    notes: Optional[str] = Field(None, description="Additional notes")


class NovelEntityOccurrence(BaseModel):
    """A single occurrence of a novel entity in a question."""
    id: int
    question_id: Optional[int]
    source_text: str
    extraction_confidence: Optional[float]
    created_at: Optional[datetime]
    question_stem: Optional[str] = Field(None, description="Truncated question stem")
    correct_answer: Optional[str]


class NovelEntitySummary(BaseModel):
    """Summary view of a novel entity for list display."""
    id: int
    entity_name: str
    entity_type: str
    normalized_name: Optional[str]
    confidence: Optional[float]
    occurrence_count: int
    first_seen: Optional[datetime]
    last_seen: Optional[datetime]
    status: str
    drug_class: Optional[str]
    synonyms: List[str] = Field(default_factory=list)
    notes: Optional[str]


class NovelEntityDetail(NovelEntitySummary):
    """Full detail view of a novel entity including occurrences."""
    reviewed_by: Optional[str]
    reviewed_at: Optional[datetime]
    occurrences: List[NovelEntityOccurrence] = Field(default_factory=list)


class NovelEntityApproval(BaseModel):
    """Request model for approving a novel entity."""
    reviewed_by: str = Field(..., description="Name/ID of reviewer")
    drug_class: Optional[str] = Field(None, description="Drug class (for treatments)")
    synonyms: Optional[List[str]] = Field(None, description="Alternative names/spellings")


class NovelEntityRejection(BaseModel):
    """Request model for rejecting a novel entity."""
    reviewed_by: str = Field(..., description="Name/ID of reviewer")
    notes: Optional[str] = Field(None, description="Reason for rejection")


class BulkApprovalRequest(BaseModel):
    """Request model for bulk auto-approval."""
    min_confidence: float = Field(0.90, ge=0, le=1, description="Minimum confidence threshold")
    min_occurrences: int = Field(3, ge=1, description="Minimum occurrence count")
    reviewed_by: str = Field("auto", description="Reviewer identifier")


class NovelEntityListResponse(BaseModel):
    """Response for listing novel entities."""
    entities: List[NovelEntitySummary]
    total: int
    page: int
    page_size: int
    total_pages: int


class NovelEntityStats(BaseModel):
    """Statistics about novel entities."""
    total: int = 0
    pending: int = 0
    approved: int = 0
    auto_approved: int = 0
    rejected: int = 0
    pending_by_type: dict = Field(default_factory=dict)
    ready_for_auto_approve: int = 0
    new_last_7_days: int = 0


# ============== V3: 3-Model Voting Models ==============

class AgreementLevel(str, Enum):
    """Agreement level among the 3 models."""
    UNANIMOUS = "unanimous"
    MAJORITY = "majority"
    CONFLICT = "conflict"


class ModelVote(BaseModel):
    """Single model's vote on tags for a question."""
    model_name: str = Field(..., description="Model identifier (gpt, claude, gemini)")
    tags: Dict[str, Any] = Field(..., description="Tags assigned by this model")
    confidence: Optional[float] = Field(None, description="Model's confidence in its response")
    reasoning: Optional[str] = Field(None, description="Model's reasoning for the tags")
    web_search_used: bool = Field(False, description="Whether web search was used")


class VotingResult(BaseModel):
    """Result of 3-model voting for a question."""
    id: int
    question_id: int
    iteration: int
    prompt_version: str
    gpt_tags: Dict[str, Any]
    claude_tags: Dict[str, Any]
    gemini_tags: Dict[str, Any]
    aggregated_tags: Dict[str, Any]
    agreement_level: AgreementLevel
    needs_review: bool
    web_searches: Optional[List[Dict]] = None
    created_at: datetime


class VotingResultSummary(BaseModel):
    """Summary of voting result for list view."""
    id: int
    question_id: int
    question_stem: str
    agreement_level: AgreementLevel
    needs_review: bool
    created_at: datetime


class VotingResultListResponse(BaseModel):
    """Response for listing voting results."""
    results: List[VotingResultSummary]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============== V3: Review Workflow Models ==============

class ReviewCorrection(BaseModel):
    """Human correction to model-generated tags."""
    id: int
    question_id: int
    iteration: int
    original_tags: Dict[str, Any]
    corrected_tags: Dict[str, Any]
    disagreement_category: Optional[str]
    reviewer_notes: Optional[str]
    reviewed_at: datetime


class ReviewCorrectionCreate(BaseModel):
    """Request to submit a human correction."""
    corrected_tags: Dict[str, Any] = Field(..., description="The corrected tag values")
    disagreement_category: Optional[str] = Field(None, description="Category of disagreement")
    reviewer_notes: Optional[str] = Field(None, description="Notes about the correction")


class DisagreementPattern(BaseModel):
    """Pattern of disagreements for analysis."""
    id: int
    iteration: int
    category: str
    frequency: int
    example_questions: List[int]
    recommended_action: Optional[str]
    implemented: bool
    created_at: datetime


class DisagreementPatternListResponse(BaseModel):
    """Response for listing disagreement patterns."""
    patterns: List[DisagreementPattern]
    total: int


# ============== V3: Tagging Workflow Models ==============

class TaggingRequest(BaseModel):
    """Request to tag a batch of questions."""
    question_ids: List[int] = Field(..., description="List of question IDs to tag")
    iteration: Optional[int] = Field(1, description="Iteration number for prompt refinement")
    use_web_search: bool = Field(True, description="Whether to enable web search for unknown entities")


class TaggingProgress(BaseModel):
    """Progress update for ongoing tagging job."""
    total_questions: int
    completed: int
    in_progress: int
    failed: int
    unanimous_count: int
    majority_count: int
    conflict_count: int
    estimated_cost: float


class TaggingJobStatus(BaseModel):
    """Status of a tagging job."""
    job_id: str
    status: Literal["pending", "running", "completed", "failed"]
    progress: TaggingProgress
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]


# ============== V3: Prompt Management Models ==============

class PromptVersion(BaseModel):
    """A version of the tagging prompt."""
    version: str
    iteration: int
    changelog: Optional[str]
    performance_metrics: Optional[Dict[str, float]]
    created_at: datetime


class PromptVersionListResponse(BaseModel):
    """Response for listing prompt versions."""
    versions: List[PromptVersion]
    current_version: str
