// Tag status values (computed from 8 core tags)
export type TagStatus = 'verified' | 'unanimous' | 'majority' | 'conflict'

// Question types
export interface Question {
  id: number
  source_id: string | number | null  // QGD - QUESTIONGROUPDESIGNATION from Excel
  question_stem: string
  topic: string | null
  topic_confidence: number | null
  disease_state: string | null
  disease_state_confidence: number | null
  treatment: string | null
  pre_score: number | null
  post_score: number | null
  knowledge_gain: number | null
  sample_size: number | null
  activity_count: number
  tag_status: TagStatus | null  // Computed agreement status across 8 core tags
  worst_case_agreement: TagStatus | null  // Worst case across ALL fields (for review queue)
  // QCore quality score (0-100)
  qcore_score: number | null
  qcore_grade: string | null  // A, B, C, D
}

export interface ActivityInfo {
  activity_name: string
  activity_date: string | null
  quarter: string | null
  performance?: PerformanceMetric[]  // Per-activity performance (if available)
}

export interface QuestionDetailData {
  id: number
  source_id: string | number | null  // QGD - QUESTIONGROUPDESIGNATION from Excel
  source_question_id: number | null  // DataFrame index from checkpoint
  question_stem: string
  correct_answer: string | null
  incorrect_answers: string[] | null
  source_file: string | null
  tags: TagInfo
  performance: PerformanceMetric[]  // Combined performance across all activities
  activities: string[]  // Legacy: list of activity names (backwards compatible)
  activity_details?: ActivityInfo[]  // New: detailed activity info with dates and per-activity performance
  // QCore quality score (0-100)
  qcore_score: number | null
  qcore_grade: string | null  // A, B, C, D
  qcore_breakdown: Record<string, any> | null  // Detailed scoring breakdown
}

export interface TagInfo {
  // === Group A: Core Classification (20 fields) ===
  topic: string | null
  topic_confidence: number | null
  topic_method: string | null
  disease_state: string | null  // Legacy field for backwards compatibility
  disease_state_1: string | null  // Primary disease state
  disease_state_2: string | null  // Secondary disease state (rare: e.g., MM + NHL)
  disease_state_confidence: number | null
  disease_stage: string | null
  disease_stage_confidence: number | null
  disease_type_1: string | null
  disease_type_2: string | null
  disease_type_confidence: number | null
  treatment_line: string | null
  treatment_line_confidence: number | null

  // === Multi-value Existing Fields (15 slots) ===
  treatment_1: string | null
  treatment_2: string | null
  treatment_3: string | null
  treatment_4: string | null
  treatment_5: string | null
  treatment_confidence: number | null
  biomarker_1: string | null
  biomarker_2: string | null
  biomarker_3: string | null
  biomarker_4: string | null
  biomarker_5: string | null
  biomarker_confidence: number | null
  trial_1: string | null
  trial_2: string | null
  trial_3: string | null
  trial_4: string | null
  trial_5: string | null
  trial_confidence: number | null

  // === Group B: Patient Characteristics (8 fields) ===
  treatment_eligibility: string | null
  age_group: string | null
  organ_dysfunction: string | null
  fitness_status: string | null
  disease_specific_factor: string | null
  comorbidity_1: string | null
  comorbidity_2: string | null
  comorbidity_3: string | null

  // === Group C: Treatment Metadata (10 fields) ===
  drug_class_1: string | null
  drug_class_2: string | null
  drug_class_3: string | null
  drug_target_1: string | null
  drug_target_2: string | null
  drug_target_3: string | null
  prior_therapy_1: string | null
  prior_therapy_2: string | null
  prior_therapy_3: string | null
  resistance_mechanism: string | null

  // === Group D: Clinical Context (7 fields) ===
  metastatic_site_1: string | null
  metastatic_site_2: string | null
  metastatic_site_3: string | null
  symptom_1: string | null
  symptom_2: string | null
  symptom_3: string | null
  performance_status: string | null

  // === Group E: Safety/Toxicity (7 fields) ===
  toxicity_type_1: string | null
  toxicity_type_2: string | null
  toxicity_type_3: string | null
  toxicity_type_4: string | null
  toxicity_type_5: string | null
  toxicity_organ: string | null
  toxicity_grade: string | null

  // === Group F: Efficacy/Outcomes (5 fields) ===
  efficacy_endpoint_1: string | null
  efficacy_endpoint_2: string | null
  efficacy_endpoint_3: string | null
  outcome_context: string | null
  clinical_benefit: string | null

  // === Group G: Evidence/Guidelines (3 fields) ===
  guideline_source_1: string | null
  guideline_source_2: string | null
  evidence_type: string | null

  // === Group H: Question Format/Quality (13 LLM-tagged fields) ===
  cme_outcome_level: string | null
  data_response_type: string | null
  stem_type: string | null
  lead_in_type: string | null
  answer_format: string | null
  answer_length_pattern: string | null
  distractor_homogeneity: string | null
  flaw_absolute_terms: boolean | null
  flaw_grammatical_cue: boolean | null
  flaw_implausible_distractor: boolean | null
  flaw_clang_association: boolean | null
  flaw_convergence_vulnerability: boolean | null
  flaw_double_negative: boolean | null

  // === Computed Fields (2) ===
  answer_option_count: number | null
  correct_answer_position: string | null

  // === Review metadata ===
  needs_review: boolean | null
  review_flags: string[] | string | null
  review_reason: string | null
  review_notes: string | null  // Reviewer comments for few-shot learning
  flagged_at: string | null
  agreement_level: string | null  // unanimous, majority, conflict
  tag_status: TagStatus | null  // Computed from 8 core tags: verified, unanimous, majority, conflict
  worst_case_agreement: TagStatus | null  // Worst case across ALL fields: verified, unanimous, majority, conflict
}

export interface PerformanceMetric {
  segment: string
  pre_score: number | null
  post_score: number | null
  pre_n: number | null
  post_n: number | null
}

// Filter types
export interface FilterOptions {
  topics: FilterOption[]
  disease_states: FilterOption[]
  disease_stages: FilterOption[]
  disease_types: FilterOption[]
  treatment_lines: FilterOption[]
  treatments: FilterOption[]
  biomarkers: FilterOption[]
  trials: FilterOption[]
  activities: FilterOption[]
  source_files: FilterOption[]  // For batch tracking
  // Patient Characteristics filter options (new in 70-field schema)
  treatment_eligibilities: FilterOption[]
  age_groups: FilterOption[]
  fitness_statuses: FilterOption[]
  organ_dysfunctions: FilterOption[]
  disease_specific_factors: FilterOption[]
  comorbidities: FilterOption[]
  // Treatment Details
  drug_classes: FilterOption[]
  drug_targets: FilterOption[]
  prior_therapies: FilterOption[]
  resistance_mechanisms: FilterOption[]
  // Clinical Context
  metastatic_sites: FilterOption[]
  symptoms: FilterOption[]
  performance_statuses: FilterOption[]
  // Safety/Toxicity
  toxicity_types: FilterOption[]
  toxicity_organs: FilterOption[]
  toxicity_grades: FilterOption[]
  // Efficacy/Outcomes
  efficacy_endpoints: FilterOption[]
  outcome_contexts: FilterOption[]
  clinical_benefits: FilterOption[]
  // Evidence/Guidelines
  guideline_sources: FilterOption[]
  evidence_types: FilterOption[]
  // Question Format
  cme_outcome_levels: FilterOption[]
  stem_types: FilterOption[]
  lead_in_types: FilterOption[]
  answer_formats: FilterOption[]
  distractor_homogeneities: FilterOption[]
}

export interface FilterOption {
  value: string
  count: number
}

export interface SearchFilters {
  topics?: string[]
  disease_states?: string[]
  disease_stages?: string[]
  disease_types?: string[]
  treatment_lines?: string[]
  treatments?: string[]
  biomarkers?: string[]
  trials?: string[]
  activities?: string[]
  source_files?: string[]  // For batch tracking
  // Patient Characteristics filters (new in 70-field schema)
  treatment_eligibilities?: string[]
  age_groups?: string[]
  fitness_statuses?: string[]
  organ_dysfunctions?: string[]
  min_confidence?: number
  max_confidence?: number
  has_performance_data?: boolean
  min_sample_size?: number
  needs_review?: boolean
  review_flag_filter?: string
  worst_case_agreement?: string  // Filter by worst_case_agreement status (ALL fields)
  tag_status_filter?: string  // Filter by tag_status (8 core tags): verified_only, verified_or_unanimous, verified_unanimous_majority
  exclude_numeric?: boolean  // Hide questions with data_response_type = 'Numeric'
  // Activity date range filter (YYYY-MM format)
  activity_start_after?: string  // Filter activities starting on or after this month
  activity_start_before?: string  // Filter activities starting on or before this month
  // Advanced filters — category_key -> selected values
  advanced_filters?: Record<string, string[]>
}

// Response types
export interface SearchResponse {
  questions: Question[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface Stats {
  total_questions: number
  tagged_questions: number
  total_activities: number
  questions_need_review: number
}

// Report types
export type TagGroupBy =
  | 'topic' | 'disease_state' | 'disease_stage' | 'disease_type' | 'treatment_line' | 'treatment' | 'biomarker' | 'trial'
  // Patient Characteristics (new in 70-field schema)
  | 'treatment_eligibility' | 'age_group' | 'fitness_status' | 'organ_dysfunction'
  // Treatment Metadata
  | 'drug_class' | 'drug_target'
  // Clinical Context
  | 'metastatic_site' | 'performance_status'
  // Safety/Toxicity
  | 'toxicity_type' | 'toxicity_organ' | 'toxicity_grade'
  // Efficacy/Outcomes
  | 'efficacy_endpoint' | 'outcome_context' | 'clinical_benefit'
  // Evidence/Guidelines
  | 'guideline_source' | 'evidence_type'
  // Question Format
  | 'cme_outcome_level'
export type DemographicSegment = 'specialty' | 'practice_setting' | 'region' | 'practice_state'
export type AudienceSegment = 'overall' | 'ophthalmologist' | 'optometrist' | 'app' | 'pharmacist'

export interface ReportFilters {
  topics?: string[]
  disease_states?: string[]
  disease_stages?: string[]
  disease_types?: string[]
  treatment_lines?: string[]
  treatments?: string[]
  biomarkers?: string[]
  trials?: string[]
  activities?: string[]
  quarters?: string[]
  specialties?: string[]
  practice_settings?: string[]
  regions?: string[]
}

export interface AggregatedMetric {
  group_value: string
  segment?: string  // Audience segment when comparing segments
  avg_pre_score: number | null
  avg_post_score: number | null
  knowledge_gain: number | null
  total_n: number
  question_count: number
}

export interface AggregatedReportResponse {
  group_by: string
  segments?: string[]  // Segments included when comparing
  data: AggregatedMetric[]
  filters_applied: ReportFilters
}

export interface SegmentReportResponse {
  data: AggregatedMetric[]
  filters_applied: ReportFilters | null
}

export interface TrendDataPoint {
  quarter: string
  segment_value: string
  avg_pre_score: number | null
  avg_post_score: number | null
  total_n: number
}

export interface TrendReportResponse {
  segment_by: string | null
  data: TrendDataPoint[]
  filters_applied: ReportFilters
}

export interface DemographicOptions {
  specialties: string[]
  practice_settings: string[]
  regions: string[]
  practice_states: string[]
  quarters: string[]
}

export interface SegmentInfo {
  segment: string
  count: number
}

export interface SegmentOptions {
  segments: SegmentInfo[]
}

export interface Activity {
  id: number
  activity_name: string
  activity_date: string | null
  quarter: string | null
  target_audience: string | null
  description: string | null
  question_count: number
  created_at: string | null
}

export interface ReportStatsResponse {
  database: Stats
  available_filters: {
    topics: number
    disease_states: number
    treatments: number
    biomarkers: number
    trials: number
    activities: number
  }
  available_demographics: {
    specialties: number
    practice_settings: number
    regions: number
    quarters: number
  }
  report_ready: boolean
}

// === Model Voting Types (for review interface) ===

export interface FieldVote {
  final_value: string | null
  gpt_value: string | null
  claude_value: string | null
  gemini_value: string | null
  agreement: 'unanimous' | 'majority' | 'conflict'
  confidence: number
  dissenting_model?: string | null
}

export interface VotingDetails {
  field_votes: Record<string, FieldVote>
  overall_agreement: 'unanimous' | 'majority' | 'conflict'
  overall_confidence: number
  review_reason?: string | null
  web_searches_used?: WebSearchResult[]
}

export interface WebSearchResult {
  query: string
  result: string
  source?: string
}

// === Field Group Definitions (for UI organization) ===

export const FIELD_GROUPS = {
  core: {
    label: 'Core Classification',
    fields: ['topic', 'disease_state_1', 'disease_state_2', 'disease_stage', 'disease_type_1', 'disease_type_2', 'treatment_line']
  },
  multiValue: {
    label: 'Treatments, Biomarkers & Trials',
    fields: [
      'treatment_1', 'treatment_2', 'treatment_3', 'treatment_4', 'treatment_5',
      'biomarker_1', 'biomarker_2', 'biomarker_3', 'biomarker_4', 'biomarker_5',
      'trial_1', 'trial_2', 'trial_3', 'trial_4', 'trial_5'
    ]
  },
  treatmentDetails: {
    label: 'Treatment Details',
    fields: ['drug_class_1', 'drug_class_2', 'drug_class_3', 'drug_target_1', 'drug_target_2', 'drug_target_3',
             'prior_therapy_1', 'prior_therapy_2', 'prior_therapy_3', 'resistance_mechanism']
  },
  patientCharacteristics: {
    label: 'Patient Characteristics',
    fields: ['treatment_eligibility', 'age_group', 'organ_dysfunction', 'fitness_status', 'disease_specific_factor',
             'comorbidity_1', 'comorbidity_2', 'comorbidity_3']
  },
  clinicalContext: {
    label: 'Clinical Context',
    fields: ['metastatic_site_1', 'metastatic_site_2', 'metastatic_site_3',
             'symptom_1', 'symptom_2', 'symptom_3', 'performance_status']
  },
  safetyToxicity: {
    label: 'Safety & Toxicity',
    fields: ['toxicity_type_1', 'toxicity_type_2', 'toxicity_type_3', 'toxicity_type_4', 'toxicity_type_5',
             'toxicity_organ', 'toxicity_grade']
  },
  efficacyOutcomes: {
    label: 'Efficacy & Outcomes',
    fields: ['efficacy_endpoint_1', 'efficacy_endpoint_2', 'efficacy_endpoint_3', 'outcome_context', 'clinical_benefit']
  },
  evidenceGuidelines: {
    label: 'Evidence & Guidelines',
    fields: ['guideline_source_1', 'guideline_source_2', 'evidence_type']
  },
  questionQuality: {
    label: 'Question Format & Quality',
    fields: ['cme_outcome_level', 'data_response_type', 'stem_type', 'lead_in_type', 'answer_format',
             'answer_length_pattern', 'distractor_homogeneity', 'flaw_absolute_terms', 'flaw_grammatical_cue',
             'flaw_implausible_distractor', 'flaw_clang_association', 'flaw_convergence_vulnerability', 'flaw_double_negative']
  },
  computed: {
    label: 'Computed Fields',
    fields: ['answer_option_count', 'correct_answer_position']
  },
  review: {
    label: 'Review Metadata',
    fields: ['needs_review', 'agreement_level', 'review_reason']
  }
} as const

/**
 * Advanced filter categories available in the Advanced Filters modal.
 * Each entry maps a category key (matching FilterOptions and the backend advanced_filters dict)
 * to its display label and group. The key is used as the filter key in SearchFilters.advanced_filters.
 */
export const ADVANCED_FILTER_CATEGORIES: {
  key: string
  label: string
  group: string
}[] = [
  // Patient Characteristics
  { key: 'treatment_eligibilities', label: 'Treatment Eligibility', group: 'Patient Characteristics' },
  { key: 'age_groups', label: 'Age Group', group: 'Patient Characteristics' },
  { key: 'fitness_statuses', label: 'Fitness Status', group: 'Patient Characteristics' },
  { key: 'organ_dysfunctions', label: 'Organ Dysfunction', group: 'Patient Characteristics' },
  { key: 'disease_specific_factors', label: 'Disease-Specific Factor', group: 'Patient Characteristics' },
  { key: 'comorbidities', label: 'Comorbidity', group: 'Patient Characteristics' },
  // Treatment Details
  { key: 'drug_classes', label: 'Drug Class', group: 'Treatment Details' },
  { key: 'drug_targets', label: 'Drug Target', group: 'Treatment Details' },
  { key: 'prior_therapies', label: 'Prior Therapy', group: 'Treatment Details' },
  { key: 'resistance_mechanisms', label: 'Resistance Mechanism', group: 'Treatment Details' },
  // Clinical Context
  { key: 'metastatic_sites', label: 'Metastatic Site', group: 'Clinical Context' },
  { key: 'symptoms', label: 'Symptom', group: 'Clinical Context' },
  { key: 'performance_statuses', label: 'Performance Status', group: 'Clinical Context' },
  // Safety & Toxicity
  { key: 'toxicity_types', label: 'Toxicity Type', group: 'Safety & Toxicity' },
  { key: 'toxicity_organs', label: 'Toxicity Organ', group: 'Safety & Toxicity' },
  { key: 'toxicity_grades', label: 'Toxicity Grade', group: 'Safety & Toxicity' },
  // Efficacy & Outcomes
  { key: 'efficacy_endpoints', label: 'Efficacy Endpoint', group: 'Efficacy & Outcomes' },
  { key: 'outcome_contexts', label: 'Outcome Context', group: 'Efficacy & Outcomes' },
  { key: 'clinical_benefits', label: 'Clinical Benefit', group: 'Efficacy & Outcomes' },
  // Evidence & Guidelines
  { key: 'guideline_sources', label: 'Guideline Source', group: 'Evidence & Guidelines' },
  { key: 'evidence_types', label: 'Evidence Type', group: 'Evidence & Guidelines' },
  // Question Format
  { key: 'cme_outcome_levels', label: 'CME Outcome Level', group: 'Question Format' },
  { key: 'stem_types', label: 'Stem Type', group: 'Question Format' },
  { key: 'lead_in_types', label: 'Lead-in Type', group: 'Question Format' },
  { key: 'answer_formats', label: 'Answer Format', group: 'Question Format' },
  { key: 'distractor_homogeneities', label: 'Distractor Homogeneity', group: 'Question Format' },
]

/** Human-readable labels for all tag field keys. */
export const FIELD_LABELS: Record<string, string> = {
  // Core Classification
  disease_state_1: 'Disease State 1',
  disease_state_2: 'Disease State 2 (Rare)',
  disease_stage: 'Disease Stage',
  disease_type_1: 'Disease Type 1',
  disease_type_2: 'Disease Type 2',
  treatment_line: 'Treatment Line',
  // Multi-value
  treatment_1: 'Treatment 1',
  treatment_2: 'Treatment 2',
  treatment_3: 'Treatment 3',
  treatment_4: 'Treatment 4',
  treatment_5: 'Treatment 5',
  biomarker_1: 'Biomarker 1',
  biomarker_2: 'Biomarker 2',
  biomarker_3: 'Biomarker 3',
  biomarker_4: 'Biomarker 4',
  biomarker_5: 'Biomarker 5',
  trial_1: 'Trial 1',
  trial_2: 'Trial 2',
  trial_3: 'Trial 3',
  trial_4: 'Trial 4',
  trial_5: 'Trial 5',
  // Patient Characteristics
  treatment_eligibility: 'Treatment Eligibility',
  age_group: 'Age Group',
  organ_dysfunction: 'Organ Dysfunction',
  fitness_status: 'Fitness Status',
  disease_specific_factor: 'Disease-Specific Factor',
  comorbidity_1: 'Comorbidity 1',
  comorbidity_2: 'Comorbidity 2',
  comorbidity_3: 'Comorbidity 3',
  // Treatment Metadata
  drug_class_1: 'Drug Class 1',
  drug_class_2: 'Drug Class 2',
  drug_class_3: 'Drug Class 3',
  drug_target_1: 'Drug Target 1',
  drug_target_2: 'Drug Target 2',
  drug_target_3: 'Drug Target 3',
  prior_therapy_1: 'Prior Therapy 1',
  prior_therapy_2: 'Prior Therapy 2',
  prior_therapy_3: 'Prior Therapy 3',
  resistance_mechanism: 'Resistance Mechanism',
  // Clinical Context
  metastatic_site_1: 'Metastatic Site 1',
  metastatic_site_2: 'Metastatic Site 2',
  metastatic_site_3: 'Metastatic Site 3',
  symptom_1: 'Symptom 1',
  symptom_2: 'Symptom 2',
  symptom_3: 'Symptom 3',
  performance_status: 'Performance Status',
  // Safety/Toxicity
  toxicity_type_1: 'Toxicity Type 1',
  toxicity_type_2: 'Toxicity Type 2',
  toxicity_type_3: 'Toxicity Type 3',
  toxicity_type_4: 'Toxicity Type 4',
  toxicity_type_5: 'Toxicity Type 5',
  toxicity_organ: 'Toxicity Organ',
  toxicity_grade: 'Toxicity Grade',
  // Efficacy/Outcomes
  efficacy_endpoint_1: 'Efficacy Endpoint 1',
  efficacy_endpoint_2: 'Efficacy Endpoint 2',
  efficacy_endpoint_3: 'Efficacy Endpoint 3',
  outcome_context: 'Outcome Context',
  clinical_benefit: 'Clinical Benefit',
  // Evidence/Guidelines
  guideline_source_1: 'Guideline Source 1',
  guideline_source_2: 'Guideline Source 2',
  evidence_type: 'Evidence Type',
  // Question Format/Quality
  cme_outcome_level: 'CME Outcome Level',
  data_response_type: 'Data Response Type',
  stem_type: 'Stem Type',
  lead_in_type: 'Lead-in Type',
  answer_format: 'Answer Format',
  answer_length_pattern: 'Answer Length Pattern',
  distractor_homogeneity: 'Distractor Homogeneity',
  flaw_absolute_terms: 'Flaw: Absolute Terms',
  flaw_grammatical_cue: 'Flaw: Grammatical Cue',
  flaw_implausible_distractor: 'Flaw: Implausible Distractor',
  flaw_clang_association: 'Flaw: Clang Association',
  flaw_convergence_vulnerability: 'Flaw: Convergence Vulnerability',
  flaw_double_negative: 'Flaw: Double Negative',
  // Computed
  answer_option_count: 'Answer Option Count',
  correct_answer_position: 'Correct Answer Position',
  // Review
  needs_review: 'Needs Review',
  agreement_level: 'Agreement Level',
  review_reason: 'Review Reason',
}

