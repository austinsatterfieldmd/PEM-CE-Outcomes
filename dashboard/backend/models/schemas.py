"""
Pydantic models for the CME Question Explorer API.
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
    """Tag information with confidence scores for all 70 LLM-tagged fields + 2 computed."""
    # === Group A: Core Classification (20 fields) ===
    topic: Optional[str] = None
    topic_confidence: Optional[float] = None
    topic_method: Optional[str] = None
    disease_state: Optional[str] = None
    disease_state_1: Optional[str] = None
    disease_state_2: Optional[str] = None
    disease_state_confidence: Optional[float] = None
    disease_stage: Optional[str] = None
    disease_stage_confidence: Optional[float] = None
    disease_type_1: Optional[str] = None
    disease_type_2: Optional[str] = None
    disease_type_confidence: Optional[float] = None
    treatment_line: Optional[str] = None
    treatment_line_confidence: Optional[float] = None

    # === Multi-value Existing Fields (15 slots) ===
    treatment_1: Optional[str] = None
    treatment_2: Optional[str] = None
    treatment_3: Optional[str] = None
    treatment_4: Optional[str] = None
    treatment_5: Optional[str] = None
    treatment_confidence: Optional[float] = None
    biomarker_1: Optional[str] = None
    biomarker_2: Optional[str] = None
    biomarker_3: Optional[str] = None
    biomarker_4: Optional[str] = None
    biomarker_5: Optional[str] = None
    biomarker_confidence: Optional[float] = None
    trial_1: Optional[str] = None
    trial_2: Optional[str] = None
    trial_3: Optional[str] = None
    trial_4: Optional[str] = None
    trial_5: Optional[str] = None
    trial_confidence: Optional[float] = None

    # === Group B: Patient Characteristics (8 fields) ===
    treatment_eligibility: Optional[str] = None
    age_group: Optional[str] = None
    organ_dysfunction: Optional[str] = None
    fitness_status: Optional[str] = None
    disease_specific_factor: Optional[str] = None
    comorbidity_1: Optional[str] = None
    comorbidity_2: Optional[str] = None
    comorbidity_3: Optional[str] = None

    # === Group C: Treatment Metadata (10 fields) ===
    drug_class_1: Optional[str] = None
    drug_class_2: Optional[str] = None
    drug_class_3: Optional[str] = None
    drug_target_1: Optional[str] = None
    drug_target_2: Optional[str] = None
    drug_target_3: Optional[str] = None
    prior_therapy_1: Optional[str] = None
    prior_therapy_2: Optional[str] = None
    prior_therapy_3: Optional[str] = None
    resistance_mechanism: Optional[str] = None

    # === Group D: Clinical Context (7 fields) ===
    metastatic_site_1: Optional[str] = None
    metastatic_site_2: Optional[str] = None
    metastatic_site_3: Optional[str] = None
    symptom_1: Optional[str] = None
    symptom_2: Optional[str] = None
    symptom_3: Optional[str] = None
    performance_status: Optional[str] = None

    # === Group E: Safety/Toxicity (7 fields) ===
    toxicity_type_1: Optional[str] = None
    toxicity_type_2: Optional[str] = None
    toxicity_type_3: Optional[str] = None
    toxicity_type_4: Optional[str] = None
    toxicity_type_5: Optional[str] = None
    toxicity_organ: Optional[str] = None
    toxicity_grade: Optional[str] = None

    # === Group F: Efficacy/Outcomes (5 fields) ===
    efficacy_endpoint_1: Optional[str] = None
    efficacy_endpoint_2: Optional[str] = None
    efficacy_endpoint_3: Optional[str] = None
    outcome_context: Optional[str] = None
    clinical_benefit: Optional[str] = None

    # === Group G: Evidence/Guidelines (3 fields) ===
    guideline_source_1: Optional[str] = None
    guideline_source_2: Optional[str] = None
    evidence_type: Optional[str] = None

    # === Group H: Question Format/Quality (13 LLM-tagged fields) ===
    cme_outcome_level: Optional[str] = None
    data_response_type: Optional[str] = None
    stem_type: Optional[str] = None
    lead_in_type: Optional[str] = None
    answer_format: Optional[str] = None
    answer_length_pattern: Optional[str] = None
    distractor_homogeneity: Optional[str] = None
    flaw_absolute_terms: Optional[bool] = None
    flaw_grammatical_cue: Optional[bool] = None
    flaw_implausible_distractor: Optional[bool] = None
    flaw_clang_association: Optional[bool] = None
    flaw_convergence_vulnerability: Optional[bool] = None
    flaw_double_negative: Optional[bool] = None

    # === Computed Fields (2) - derived from raw data ===
    answer_option_count: Optional[int] = None
    correct_answer_position: Optional[str] = None

    # === Review metadata ===
    needs_review: Optional[bool] = None
    review_flags: Optional[List[str]] = None
    review_reason: Optional[str] = None
    review_notes: Optional[str] = None  # Reviewer comments for few-shot learning
    flagged_at: Optional[datetime] = None

    # === Model voting data (for review interface) ===
    agreement_level: Optional[str] = None  # unanimous, majority, conflict


class TagUpdate(BaseModel):
    """Request model for updating tags on a question (all 70 LLM-tagged fields)."""
    # === Group A: Core Classification ===
    topic: Optional[str] = None
    disease_state: Optional[str] = None  # Legacy field
    disease_state_1: Optional[str] = None  # Primary disease state
    disease_state_2: Optional[str] = None  # Secondary disease state (rare: e.g., MM + NHL)
    disease_stage: Optional[str] = None
    disease_type_1: Optional[str] = None
    disease_type_2: Optional[str] = None
    treatment_line: Optional[str] = None

    # === Multi-value Existing Fields ===
    treatment_1: Optional[str] = None
    treatment_2: Optional[str] = None
    treatment_3: Optional[str] = None
    treatment_4: Optional[str] = None
    treatment_5: Optional[str] = None
    biomarker_1: Optional[str] = None
    biomarker_2: Optional[str] = None
    biomarker_3: Optional[str] = None
    biomarker_4: Optional[str] = None
    biomarker_5: Optional[str] = None
    trial_1: Optional[str] = None
    trial_2: Optional[str] = None
    trial_3: Optional[str] = None
    trial_4: Optional[str] = None
    trial_5: Optional[str] = None

    # === Group B: Patient Characteristics ===
    treatment_eligibility: Optional[str] = None
    age_group: Optional[str] = None
    organ_dysfunction: Optional[str] = None
    fitness_status: Optional[str] = None
    disease_specific_factor: Optional[str] = None
    comorbidity_1: Optional[str] = None
    comorbidity_2: Optional[str] = None
    comorbidity_3: Optional[str] = None

    # === Group C: Treatment Metadata ===
    drug_class_1: Optional[str] = None
    drug_class_2: Optional[str] = None
    drug_class_3: Optional[str] = None
    drug_target_1: Optional[str] = None
    drug_target_2: Optional[str] = None
    drug_target_3: Optional[str] = None
    prior_therapy_1: Optional[str] = None
    prior_therapy_2: Optional[str] = None
    prior_therapy_3: Optional[str] = None
    resistance_mechanism: Optional[str] = None

    # === Group D: Clinical Context ===
    metastatic_site_1: Optional[str] = None
    metastatic_site_2: Optional[str] = None
    metastatic_site_3: Optional[str] = None
    symptom_1: Optional[str] = None
    symptom_2: Optional[str] = None
    symptom_3: Optional[str] = None
    performance_status: Optional[str] = None

    # === Group E: Safety/Toxicity ===
    toxicity_type_1: Optional[str] = None
    toxicity_type_2: Optional[str] = None
    toxicity_type_3: Optional[str] = None
    toxicity_type_4: Optional[str] = None
    toxicity_type_5: Optional[str] = None
    toxicity_organ: Optional[str] = None
    toxicity_grade: Optional[str] = None

    # === Group F: Efficacy/Outcomes ===
    efficacy_endpoint_1: Optional[str] = None
    efficacy_endpoint_2: Optional[str] = None
    efficacy_endpoint_3: Optional[str] = None
    outcome_context: Optional[str] = None
    clinical_benefit: Optional[str] = None

    # === Group G: Evidence/Guidelines ===
    guideline_source_1: Optional[str] = None
    guideline_source_2: Optional[str] = None
    evidence_type: Optional[str] = None

    # === Group H: Question Format/Quality ===
    cme_outcome_level: Optional[str] = None
    data_response_type: Optional[str] = None
    stem_type: Optional[str] = None
    lead_in_type: Optional[str] = None
    answer_format: Optional[str] = None
    answer_length_pattern: Optional[str] = None
    distractor_homogeneity: Optional[str] = None
    flaw_absolute_terms: Optional[bool] = None
    flaw_grammatical_cue: Optional[bool] = None
    flaw_implausible_distractor: Optional[bool] = None
    flaw_clang_association: Optional[bool] = None
    flaw_convergence_vulnerability: Optional[bool] = None
    flaw_double_negative: Optional[bool] = None

    # === Admin fields ===
    question_stem: Optional[str] = Field(None, description="Updated question stem (admin only)")
    mark_as_reviewed: Optional[bool] = False
    review_notes: Optional[str] = Field(None, description="Reviewer comments for few-shot learning")

    # === User-defined values ===
    # When the frontend detects a custom value (not in static allowed values),
    # it sends the field_name and value here to be persisted for future dropdowns
    custom_values: Optional[List[Dict[str, str]]] = Field(
        None,
        description="List of {field_name, value} dicts for custom values to persist"
    )


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
    tag_status: Optional[str] = Field(None, description="Tag agreement status (8 core tags): verified, unanimous, majority, conflict")
    worst_case_agreement: Optional[str] = Field(None, description="Worst-case agreement across ALL fields: verified, unanimous, majority, conflict")
    # QCore quality score
    qcore_score: Optional[float] = Field(None, description="QCore quality score (0-100)")
    qcore_grade: Optional[str] = Field(None, description="QCore grade (A, B, C, D)")


class ActivityDetailInfo(BaseModel):
    """Detailed activity info with date and per-activity performance."""
    activity_name: str
    activity_date: Optional[date] = Field(None, description="Date of the activity")
    quarter: Optional[str] = Field(None, description="Quarter (e.g., '2024 Q3')")
    performance: List[PerformanceMetric] = Field(default_factory=list, description="Per-activity performance by segment")


class QuestionDetail(BaseModel):
    """Full detail view of a question."""
    id: int
    question_stem: str
    correct_answer: Optional[str] = None
    incorrect_answers: Optional[List[str]] = None
    source_file: Optional[str] = None

    # Tags with confidence
    tags: TagInfo

    # Combined performance by segment (across all activities)
    performance: List[PerformanceMetric] = []

    # Activities - legacy list of names (backwards compatible)
    activities: List[str] = []

    # Detailed activity info with dates and per-activity performance
    activity_details: List[ActivityDetailInfo] = Field(default_factory=list, description="Detailed activity info with dates and per-activity performance")

    # QCore quality score
    qcore_score: Optional[float] = Field(None, description="QCore quality score (0-100)")
    qcore_grade: Optional[str] = Field(None, description="QCore grade (A, B, C, D)")
    qcore_breakdown: Optional[Dict[str, Any]] = Field(None, description="QCore score breakdown")


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
    source_files: Optional[List[str]] = Field(None, description="Filter by source file(s) - for batch tracking")
    # Patient Characteristics filters (new in 70-field schema)
    treatment_eligibilities: Optional[List[str]] = Field(None, description="Filter by treatment eligibility (Transplant-eligible, etc.)")
    age_groups: Optional[List[str]] = Field(None, description="Filter by age group (Younger, Elderly, Very elderly)")
    fitness_statuses: Optional[List[str]] = Field(None, description="Filter by fitness status (Fit, Frail)")
    organ_dysfunctions: Optional[List[str]] = Field(None, description="Filter by organ dysfunction (Renal, Cardiac, Hepatic)")
    min_confidence: Optional[float] = Field(None, ge=0, le=1, description="Minimum confidence threshold")
    max_confidence: Optional[float] = Field(None, ge=0, le=1, description="Maximum confidence threshold")
    has_performance_data: Optional[bool] = Field(None, description="Filter to questions with performance data")
    min_sample_size: Optional[int] = Field(None, ge=0, description="Minimum sample size (pre_n + post_n)")
    needs_review: Optional[bool] = Field(None, description="Filter to questions that need review")
    review_flag_filter: Optional[str] = Field(None, description="Filter by review flag type (not_oncology, tag_errors, question_errors)")
    worst_case_agreement: Optional[str] = Field(None, description="Filter by worst_case_agreement status (ALL fields)")
    tag_status_filter: Optional[str] = Field(None, description="Filter by tag_status (8 core tags): verified_only, verified_or_unanimous, verified_unanimous_majority")
    exclude_numeric: Optional[bool] = Field(None, description="Exclude questions with data_response_type = 'Numeric'")
    # Activity date range filter (YYYY-MM format)
    activity_start_after: Optional[str] = Field(None, description="Filter activities starting on or after this month (YYYY-MM)")
    activity_start_before: Optional[str] = Field(None, description="Filter activities starting on or before this month (YYYY-MM)")
    # Advanced filters — dict of category_key -> selected values
    advanced_filters: Optional[Dict[str, List[str]]] = Field(None, description="Advanced filter categories (e.g. drug_classes, comorbidities)")


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
    """Question data for export with all 70 LLM-tagged fields + 2 computed + activities."""
    id: int
    question_stem: str
    correct_answer: Optional[str] = None
    incorrect_answers: Optional[str] = Field(None, description="Pipe-separated list of incorrect answers")
    source_file: Optional[str] = Field(None, description="Source file for batch tracking")

    # === Group A: Core Classification ===
    topic: Optional[str] = None
    disease_state: Optional[str] = None
    disease_type_1: Optional[str] = None
    disease_type_2: Optional[str] = None
    disease_stage: Optional[str] = None
    treatment_line: Optional[str] = None

    # === Multi-value Existing Fields ===
    treatment_1: Optional[str] = None
    treatment_2: Optional[str] = None
    treatment_3: Optional[str] = None
    treatment_4: Optional[str] = None
    treatment_5: Optional[str] = None
    biomarker_1: Optional[str] = None
    biomarker_2: Optional[str] = None
    biomarker_3: Optional[str] = None
    biomarker_4: Optional[str] = None
    biomarker_5: Optional[str] = None
    trial_1: Optional[str] = None
    trial_2: Optional[str] = None
    trial_3: Optional[str] = None
    trial_4: Optional[str] = None
    trial_5: Optional[str] = None

    # === Group B: Patient Characteristics ===
    treatment_eligibility: Optional[str] = None
    age_group: Optional[str] = None
    organ_dysfunction: Optional[str] = None
    fitness_status: Optional[str] = None
    disease_specific_factor: Optional[str] = None
    comorbidity_1: Optional[str] = None
    comorbidity_2: Optional[str] = None
    comorbidity_3: Optional[str] = None

    # === Group C: Treatment Metadata ===
    drug_class_1: Optional[str] = None
    drug_class_2: Optional[str] = None
    drug_class_3: Optional[str] = None
    drug_target_1: Optional[str] = None
    drug_target_2: Optional[str] = None
    drug_target_3: Optional[str] = None
    prior_therapy_1: Optional[str] = None
    prior_therapy_2: Optional[str] = None
    prior_therapy_3: Optional[str] = None
    resistance_mechanism: Optional[str] = None

    # === Group D: Clinical Context ===
    metastatic_site_1: Optional[str] = None
    metastatic_site_2: Optional[str] = None
    metastatic_site_3: Optional[str] = None
    symptom_1: Optional[str] = None
    symptom_2: Optional[str] = None
    symptom_3: Optional[str] = None
    performance_status: Optional[str] = None

    # === Group E: Safety/Toxicity ===
    toxicity_type_1: Optional[str] = None
    toxicity_type_2: Optional[str] = None
    toxicity_type_3: Optional[str] = None
    toxicity_type_4: Optional[str] = None
    toxicity_type_5: Optional[str] = None
    toxicity_organ: Optional[str] = None
    toxicity_grade: Optional[str] = None

    # === Group F: Efficacy/Outcomes ===
    efficacy_endpoint_1: Optional[str] = None
    efficacy_endpoint_2: Optional[str] = None
    efficacy_endpoint_3: Optional[str] = None
    outcome_context: Optional[str] = None
    clinical_benefit: Optional[str] = None

    # === Group G: Evidence/Guidelines ===
    guideline_source_1: Optional[str] = None
    guideline_source_2: Optional[str] = None
    evidence_type: Optional[str] = None

    # === Group H: Question Format/Quality ===
    cme_outcome_level: Optional[str] = None
    data_response_type: Optional[str] = None
    stem_type: Optional[str] = None
    lead_in_type: Optional[str] = None
    answer_format: Optional[str] = None
    answer_length_pattern: Optional[str] = None
    distractor_homogeneity: Optional[str] = None
    flaw_absolute_terms: Optional[bool] = None
    flaw_grammatical_cue: Optional[bool] = None
    flaw_implausible_distractor: Optional[bool] = None
    flaw_clang_association: Optional[bool] = None
    flaw_convergence_vulnerability: Optional[bool] = None
    flaw_double_negative: Optional[bool] = None

    # === Computed Fields ===
    answer_option_count: Optional[int] = None
    correct_answer_position: Optional[str] = None

    # === Performance data ===
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
    source_files: List[dict] = Field(default_factory=list, description="Source files for batch tracking")
    # Patient Characteristics filter options (new in 70-field schema)
    treatment_eligibilities: List[dict] = Field(default_factory=list)
    age_groups: List[dict] = Field(default_factory=list)
    fitness_statuses: List[dict] = Field(default_factory=list)
    organ_dysfunctions: List[dict] = Field(default_factory=list)
    disease_specific_factors: List[dict] = Field(default_factory=list)
    comorbidities: List[dict] = Field(default_factory=list)
    # Treatment Details
    drug_classes: List[dict] = Field(default_factory=list)
    drug_targets: List[dict] = Field(default_factory=list)
    prior_therapies: List[dict] = Field(default_factory=list)
    resistance_mechanisms: List[dict] = Field(default_factory=list)
    # Clinical Context
    metastatic_sites: List[dict] = Field(default_factory=list)
    symptoms: List[dict] = Field(default_factory=list)
    performance_statuses: List[dict] = Field(default_factory=list)
    # Safety/Toxicity
    toxicity_types: List[dict] = Field(default_factory=list)
    toxicity_organs: List[dict] = Field(default_factory=list)
    toxicity_grades: List[dict] = Field(default_factory=list)
    # Efficacy/Outcomes
    efficacy_endpoints: List[dict] = Field(default_factory=list)
    outcome_contexts: List[dict] = Field(default_factory=list)
    clinical_benefits: List[dict] = Field(default_factory=list)
    # Evidence/Guidelines
    guideline_sources: List[dict] = Field(default_factory=list)
    evidence_types: List[dict] = Field(default_factory=list)
    # Question Format
    cme_outcome_levels: List[dict] = Field(default_factory=list)
    stem_types: List[dict] = Field(default_factory=list)
    lead_in_types: List[dict] = Field(default_factory=list)
    answer_formats: List[dict] = Field(default_factory=list)
    distractor_homogeneities: List[dict] = Field(default_factory=list)


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
    # Patient Characteristics (new in 70-field schema)
    TREATMENT_ELIGIBILITY = "treatment_eligibility"
    AGE_GROUP = "age_group"
    FITNESS_STATUS = "fitness_status"
    ORGAN_DYSFUNCTION = "organ_dysfunction"
    # Treatment Metadata
    DRUG_CLASS = "drug_class"
    DRUG_TARGET = "drug_target"
    # Clinical Context
    METASTATIC_SITE = "metastatic_site"
    PERFORMANCE_STATUS = "performance_status"
    # Safety/Toxicity
    TOXICITY_TYPE = "toxicity_type"
    TOXICITY_ORGAN = "toxicity_organ"
    TOXICITY_GRADE = "toxicity_grade"
    # Efficacy/Outcomes
    EFFICACY_ENDPOINT = "efficacy_endpoint"
    OUTCOME_CONTEXT = "outcome_context"
    CLINICAL_BENEFIT = "clinical_benefit"
    # Evidence/Guidelines
    GUIDELINE_SOURCE = "guideline_source"
    EVIDENCE_TYPE = "evidence_type"
    # Question Format
    CME_OUTCOME_LEVEL = "cme_outcome_level"


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

