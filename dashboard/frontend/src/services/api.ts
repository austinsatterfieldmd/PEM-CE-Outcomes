import type {
  SearchResponse,
  FilterOptions,
  Stats,
  QuestionDetailData,
  SearchFilters,
  ReportFilters,
  TagGroupBy,
  DemographicSegment,
  AudienceSegment,
  AggregatedReportResponse,
  SegmentReportResponse,
  TrendReportResponse,
  DemographicOptions,
  SegmentOptions,
  Activity,
  ReportStatsResponse
} from '../types'
import { getAuthHeaders } from './auth'

const API_BASE = '/api'

/**
 * Fetch wrapper that includes authentication headers
 */
async function authFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const authHeaders = await getAuthHeaders()

  const response = await fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      ...authHeaders,
    },
  })

  // If we get a 401, the token may have expired - could trigger re-auth here
  if (response.status === 401) {
    // For now, just throw an error. The AuthProvider will handle re-authentication.
    throw new Error('Authentication required. Please sign in again.')
  }

  return response
}

// Search questions with filters
export async function searchQuestions(params: SearchFilters & {
  query?: string
  page?: number
  page_size?: number
  sort_by?: string
  sort_desc?: boolean
}): Promise<SearchResponse> {
  const { query, page = 1, page_size = 20, sort_by = 'id', sort_desc = false, ...filters } = params

  const body: Record<string, unknown> = {
    filters: {
      query,
      ...filters
    },
    pagination: {
      page,
      page_size
    },
    sort_by,
    sort_desc
  }

  const response = await authFetch(`${API_BASE}/questions/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  })
  
  if (!response.ok) {
    throw new Error(`Search failed: ${response.statusText}`)
  }
  
  return response.json()
}

// Get filter options
export async function getFilterOptions(): Promise<FilterOptions> {
  const response = await authFetch(`${API_BASE}/questions/filters/options`)
  
  if (!response.ok) {
    throw new Error(`Failed to get filter options: ${response.statusText}`)
  }
  
  return response.json()
}

// Get dynamic filter options based on current selections
export async function getDynamicFilterOptions(currentFilters: SearchFilters): Promise<FilterOptions> {
  const response = await authFetch(`${API_BASE}/questions/filters/options/dynamic`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(currentFilters)
  })
  
  if (!response.ok) {
    throw new Error(`Failed to get dynamic filter options: ${response.statusText}`)
  }
  
  return response.json()
}

// Get question details
export async function getQuestionDetail(id: number): Promise<QuestionDetailData> {
  const response = await authFetch(`${API_BASE}/questions/${id}`)
  
  if (!response.ok) {
    throw new Error(`Failed to get question details: ${response.statusText}`)
  }
  
  return response.json()
}

// Get stats
export async function getStats(): Promise<Stats> {
  const response = await authFetch(`${API_BASE}/questions/stats/summary`)
  
  if (!response.ok) {
    throw new Error(`Failed to get stats: ${response.statusText}`)
  }
  
  return response.json()
}

// Update question tags (70-field schema)
export async function updateQuestionTags(id: number, tags: {
  // Core Classification
  topic?: string | null
  disease_state?: string | null
  disease_state_1?: string | null
  disease_state_2?: string | null
  disease_stage?: string | null
  disease_type_1?: string | null
  disease_type_2?: string | null
  treatment_line?: string | null
  // Multi-value fields
  treatment_1?: string | null
  treatment_2?: string | null
  treatment_3?: string | null
  treatment_4?: string | null
  treatment_5?: string | null
  biomarker_1?: string | null
  biomarker_2?: string | null
  biomarker_3?: string | null
  biomarker_4?: string | null
  biomarker_5?: string | null
  trial_1?: string | null
  trial_2?: string | null
  trial_3?: string | null
  trial_4?: string | null
  trial_5?: string | null
  // Patient Characteristics
  treatment_eligibility?: string | null
  age_group?: string | null
  organ_dysfunction?: string | null
  fitness_status?: string | null
  disease_specific_factor?: string | null
  // Treatment Metadata
  drug_class_1?: string | null
  drug_class_2?: string | null
  drug_class_3?: string | null
  drug_target_1?: string | null
  drug_target_2?: string | null
  drug_target_3?: string | null
  prior_therapy_1?: string | null
  prior_therapy_2?: string | null
  prior_therapy_3?: string | null
  resistance_mechanism?: string | null
  // Clinical Context
  metastatic_site_1?: string | null
  metastatic_site_2?: string | null
  metastatic_site_3?: string | null
  symptom_1?: string | null
  symptom_2?: string | null
  symptom_3?: string | null
  performance_status?: string | null
  // Safety/Toxicity
  toxicity_type_1?: string | null
  toxicity_type_2?: string | null
  toxicity_type_3?: string | null
  toxicity_type_4?: string | null
  toxicity_type_5?: string | null
  toxicity_organ?: string | null
  toxicity_grade?: string | null
  // Efficacy/Outcomes
  efficacy_endpoint_1?: string | null
  efficacy_endpoint_2?: string | null
  efficacy_endpoint_3?: string | null
  outcome_context?: string | null
  clinical_benefit?: string | null
  // Evidence/Guidelines
  guideline_source_1?: string | null
  guideline_source_2?: string | null
  evidence_type?: string | null
  // Question Format/Quality
  cme_outcome_level?: string | null
  data_response_type?: string | null
  stem_type?: string | null
  lead_in_type?: string | null
  answer_format?: string | null
  answer_length_pattern?: string | null
  distractor_homogeneity?: string | null
  flaw_absolute_terms?: boolean | null
  flaw_grammatical_cue?: boolean | null
  flaw_implausible_distractor?: boolean | null
  flaw_clang_association?: boolean | null
  flaw_convergence_vulnerability?: boolean | null
  flaw_double_negative?: boolean | null
  // Admin fields
  question_stem?: string | null
  mark_as_reviewed?: boolean
  // User-defined values to persist (custom values not in static dropdown lists)
  custom_values?: Array<{ field_name: string; value: string }>
}): Promise<void> {
  const response = await authFetch(`${API_BASE}/questions/${id}/tags`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(tags)
  })

  if (!response.ok) {
    throw new Error(`Failed to update tags: ${response.statusText}`)
  }
}

// Flag question for review
export async function flagQuestion(id: number, reasons: string[]): Promise<void> {
  const response = await authFetch(`${API_BASE}/questions/${id}/flag`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reasons })
  })

  if (!response.ok) {
    throw new Error(`Failed to flag question: ${response.statusText}`)
  }
}

// Update question oncology status
export async function updateOncologyStatus(id: number, isOncology: boolean): Promise<void> {
  const response = await authFetch(`${API_BASE}/questions/${id}/oncology-status`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ is_oncology: isOncology })
  })

  if (!response.ok) {
    throw new Error(`Failed to update oncology status: ${response.statusText}`)
  }
}

// ============== User-Defined Values API Functions ==============

// Get all user-defined values (custom values that users have entered via "Other...")
export async function getUserDefinedValues(): Promise<Record<string, string[]>> {
  const response = await authFetch(`${API_BASE}/user-values/`)

  if (!response.ok) {
    // If the endpoint doesn't exist yet, return empty object
    if (response.status === 404) {
      return {}
    }
    throw new Error(`Failed to get user-defined values: ${response.statusText}`)
  }

  const data = await response.json()
  return data.values || {}
}

// Get user-defined values for a specific field
export async function getUserDefinedValuesForField(fieldName: string): Promise<string[]> {
  const response = await authFetch(`${API_BASE}/user-values/${fieldName}`)

  if (!response.ok) {
    if (response.status === 404) {
      return []
    }
    throw new Error(`Failed to get user-defined values: ${response.statusText}`)
  }

  return response.json()
}

// ============== Report API Functions ==============

// Aggregate performance by tag
export async function aggregateByTag(
  groupBy: TagGroupBy,
  filters: ReportFilters = {}
): Promise<AggregatedReportResponse> {
  const response = await authFetch(`${API_BASE}/reports/aggregate/by-tag`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      group_by: groupBy,
      filters
    })
  })

  if (!response.ok) {
    throw new Error(`Failed to aggregate by tag: ${response.statusText}`)
  }

  return response.json()
}

// Aggregate performance by tag with segment comparison
export async function aggregateByTagWithSegments(
  groupBy: TagGroupBy,
  segments: AudienceSegment[],
  filters: ReportFilters = {}
): Promise<AggregatedReportResponse> {
  const response = await authFetch(`${API_BASE}/reports/aggregate/by-tag-with-segments`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      group_by: groupBy,
      segments,
      filters
    })
  })

  if (!response.ok) {
    throw new Error(`Failed to aggregate by tag with segments: ${response.statusText}`)
  }

  return response.json()
}

// Aggregate performance by demographic
export async function aggregateByDemographic(
  segmentBy: DemographicSegment,
  filters: ReportFilters = {}
): Promise<AggregatedReportResponse> {
  const response = await authFetch(`${API_BASE}/reports/aggregate/by-demographic`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      segment_by: segmentBy,
      filters
    })
  })

  if (!response.ok) {
    throw new Error(`Failed to aggregate by demographic: ${response.statusText}`)
  }

  return response.json()
}

// Aggregate performance by audience segment
export async function aggregateBySegment(
  segments: AudienceSegment[] | null = null,
  filters: ReportFilters = {}
): Promise<SegmentReportResponse> {
  const response = await authFetch(`${API_BASE}/reports/aggregate/by-segment`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      segments,
      filters
    })
  })

  if (!response.ok) {
    throw new Error(`Failed to aggregate by segment: ${response.statusText}`)
  }

  return response.json()
}

// Get available audience segments
export async function getSegmentOptions(): Promise<SegmentOptions> {
  const response = await authFetch(`${API_BASE}/reports/options/segments`)

  if (!response.ok) {
    throw new Error(`Failed to get segment options: ${response.statusText}`)
  }

  return response.json()
}

// Get performance trends over time
export async function getPerformanceTrends(
  segmentBy: DemographicSegment | null = null,
  filters: ReportFilters = {}
): Promise<TrendReportResponse> {
  const response = await authFetch(`${API_BASE}/reports/trends`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      segment_by: segmentBy,
      filters
    })
  })
  
  if (!response.ok) {
    throw new Error(`Failed to get trends: ${response.statusText}`)
  }
  
  return response.json()
}

// Get demographic filter options
export async function getDemographicOptions(): Promise<DemographicOptions> {
  const response = await authFetch(`${API_BASE}/reports/options/demographics`)
  
  if (!response.ok) {
    throw new Error(`Failed to get demographic options: ${response.statusText}`)
  }
  
  return response.json()
}

// Get activities list
export async function getActivities(params: {
  quarter?: string
  has_date?: boolean
} = {}): Promise<{ activities: Activity[], total: number }> {
  const searchParams = new URLSearchParams()
  if (params.quarter) searchParams.append('quarter', params.quarter)
  if (params.has_date !== undefined) searchParams.append('has_date', String(params.has_date))
  
  const url = `${API_BASE}/reports/activities${searchParams.toString() ? '?' + searchParams.toString() : ''}`
  const response = await authFetch(url)
  
  if (!response.ok) {
    throw new Error(`Failed to get activities: ${response.statusText}`)
  }
  
  return response.json()
}

// Update activity metadata
export async function updateActivity(activityName: string, data: {
  activity_date?: string | null
  target_audience?: string | null
  description?: string | null
}): Promise<Activity> {
  const response = await authFetch(`${API_BASE}/reports/activities/${encodeURIComponent(activityName)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      activity_name: activityName,
      ...data
    })
  })
  
  if (!response.ok) {
    throw new Error(`Failed to update activity: ${response.statusText}`)
  }
  
  return response.json()
}

// Get report stats summary
export async function getReportStats(): Promise<ReportStatsResponse> {
  const response = await authFetch(`${API_BASE}/reports/stats/summary`)

  if (!response.ok) {
    throw new Error(`Failed to get report stats: ${response.statusText}`)
  }

  return response.json()
}

// Export questions for report - includes all 70 tag fields for full export
export interface QuestionExport {
  id: number
  question_stem: string
  correct_answer: string | null
  incorrect_answers: string | null
  source_file: string | null
  // Core Classification
  topic: string | null
  disease_state: string | null
  disease_type: string | null  // Legacy alias
  disease_type_1: string | null
  disease_type_2: string | null
  disease_stage: string | null
  treatment: string | null  // Legacy alias
  treatment_line: string | null
  biomarker: string | null  // Legacy alias
  trial: string | null  // Legacy alias
  // Multi-value Fields
  treatment_1: string | null
  treatment_2: string | null
  treatment_3: string | null
  treatment_4: string | null
  treatment_5: string | null
  biomarker_1: string | null
  biomarker_2: string | null
  biomarker_3: string | null
  biomarker_4: string | null
  biomarker_5: string | null
  trial_1: string | null
  trial_2: string | null
  trial_3: string | null
  trial_4: string | null
  trial_5: string | null
  // Patient Characteristics
  treatment_eligibility: string | null
  age_group: string | null
  organ_dysfunction: string | null
  fitness_status: string | null
  disease_specific_factor: string | null
  comorbidity_1: string | null
  comorbidity_2: string | null
  comorbidity_3: string | null
  // Treatment Metadata
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
  // Clinical Context
  metastatic_site_1: string | null
  metastatic_site_2: string | null
  metastatic_site_3: string | null
  symptom_1: string | null
  symptom_2: string | null
  symptom_3: string | null
  performance_status: string | null
  // Safety/Toxicity
  toxicity_type_1: string | null
  toxicity_type_2: string | null
  toxicity_type_3: string | null
  toxicity_type_4: string | null
  toxicity_type_5: string | null
  toxicity_organ: string | null
  toxicity_grade: string | null
  // Efficacy/Outcomes
  efficacy_endpoint_1: string | null
  efficacy_endpoint_2: string | null
  efficacy_endpoint_3: string | null
  outcome_context: string | null
  clinical_benefit: string | null
  // Evidence/Guidelines
  guideline_source_1: string | null
  guideline_source_2: string | null
  evidence_type: string | null
  // Question Format/Quality
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
  // Computed
  answer_option_count: number | null
  correct_answer_position: string | null
  // Performance
  pre_score: number | null
  post_score: number | null
  knowledge_gain: number | null
  sample_size: number | null
  activities: string | null
}

export async function exportQuestionsForReport(filters: ReportFilters): Promise<{ questions: QuestionExport[], total: number }> {
  const response = await authFetch(`${API_BASE}/reports/export/questions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(filters)
  })

  if (!response.ok) {
    throw new Error(`Failed to export questions: ${response.statusText}`)
  }

  return response.json()
}

// Export questions with full data including activities (for Question Explorer export)
export async function exportQuestions(filters: SearchFilters): Promise<{ questions: QuestionExport[], total: number }> {
  const response = await authFetch(`${API_BASE}/questions/export`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(filters)
  })

  if (!response.ok) {
    throw new Error(`Failed to export questions: ${response.statusText}`)
  }

  return response.json()
}

// Export questions with ALL 70 tag fields (for Review Queue batch workflow)
export async function exportQuestionsFull(filters: SearchFilters): Promise<{ questions: QuestionExport[], total: number }> {
  const response = await authFetch(`${API_BASE}/questions/export/full`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(filters)
  })

  if (!response.ok) {
    throw new Error(`Failed to export questions: ${response.statusText}`)
  }

  return response.json()
}

// ============== Tag Proposal API Functions ==============

export interface ProposalCandidate {
  id: number
  question_id: number
  match_score: number
  current_value: string | null
  decision: 'pending' | 'approved' | 'skipped'
  decided_at: string | null
  decided_by: string | null
  notes: string | null
  question_stem: string | null
  correct_answer: string | null
  source_id: string | null
}

export interface TagProposal {
  id: number
  field_name: string
  proposed_value: string
  search_query: string | null
  proposal_reason: string | null
  status: 'pending' | 'reviewing' | 'ready_to_apply' | 'applied' | 'abandoned'
  match_count: number
  approved_count: number
  created_at: string | null
  created_by: string | null
  completed_at: string | null
  candidates?: ProposalCandidate[]
}

export interface ProposalStats {
  total: number
  pending: number
  reviewing: number
  ready_to_apply: number
  applied: number
  abandoned: number
}

// Get proposal stats
export async function getProposalStats(): Promise<ProposalStats> {
  const response = await authFetch(`${API_BASE}/proposals/stats`)
  if (!response.ok) {
    throw new Error(`Failed to get proposal stats: ${response.statusText}`)
  }
  return response.json()
}

// List proposals with optional status filter
export async function getProposals(status?: string): Promise<TagProposal[]> {
  const url = status
    ? `${API_BASE}/proposals?status=${status}`
    : `${API_BASE}/proposals`
  const response = await authFetch(url)
  if (!response.ok) {
    throw new Error(`Failed to get proposals: ${response.statusText}`)
  }
  return response.json()
}

// Create a new proposal
export async function createProposal(data: {
  field_name: string
  proposed_value: string
  search_query: string
  proposal_reason?: string
  created_by?: string
}): Promise<TagProposal> {
  const response = await authFetch(`${API_BASE}/proposals`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  })
  if (!response.ok) {
    throw new Error(`Failed to create proposal: ${response.statusText}`)
  }
  return response.json()
}

// Get proposal with candidates
export async function getProposal(proposalId: number): Promise<TagProposal> {
  const response = await authFetch(`${API_BASE}/proposals/${proposalId}`)
  if (!response.ok) {
    throw new Error(`Failed to get proposal: ${response.statusText}`)
  }
  return response.json()
}

// Review candidates (approve/skip)
export async function reviewProposalCandidates(
  proposalId: number,
  data: {
    approved_ids: number[]
    skipped_ids: number[]
    reviewed_by?: string
  }
): Promise<{ proposal_id: number; approved_count: number; pending_count: number; status: string }> {
  const response = await authFetch(`${API_BASE}/proposals/${proposalId}/review`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  })
  if (!response.ok) {
    throw new Error(`Failed to review candidates: ${response.statusText}`)
  }
  return response.json()
}

// Apply proposal tags to approved candidates
export async function applyProposal(
  proposalId: number,
  reviewedBy?: string
): Promise<{ proposal_id: number; field_name: string; proposed_value: string; updated_count: number }> {
  const response = await authFetch(`${API_BASE}/proposals/${proposalId}/apply`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reviewed_by: reviewedBy })
  })
  if (!response.ok) {
    throw new Error(`Failed to apply proposal: ${response.statusText}`)
  }
  return response.json()
}

// Abandon a proposal
export async function abandonProposal(proposalId: number): Promise<{ status: string; proposal_id: number }> {
  const response = await authFetch(`${API_BASE}/proposals/${proposalId}`, {
    method: 'DELETE'
  })
  if (!response.ok) {
    throw new Error(`Failed to abandon proposal: ${response.statusText}`)
  }
  return response.json()
}

// ============== Dedup API Functions ==============

export interface DuplicateCandidate {
  id: number
  source_id: string | null
  question_stem: string | null
  correct_answer: string | null
  disease_state: string | null
  topic: string | null
}

// Search for potential duplicate candidates
export async function searchDuplicateCandidates(
  query: string,
  excludeId?: number,
  limit: number = 50
): Promise<DuplicateCandidate[]> {
  const params = new URLSearchParams({ query, limit: limit.toString() })
  if (excludeId) {
    params.append('exclude_id', excludeId.toString())
  }
  const response = await authFetch(`${API_BASE}/dedup/search?${params}`)
  if (!response.ok) {
    throw new Error(`Failed to search duplicates: ${response.statusText}`)
  }
  return response.json()
}

// Create a dedup cluster
export async function createDedupCluster(data: {
  question_ids: number[]
  similarity_threshold?: number
  canonical_question_id?: number
}): Promise<{ cluster_id: number; status: string }> {
  const response = await authFetch(`${API_BASE}/dedup/clusters`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  })
  if (!response.ok) {
    throw new Error(`Failed to create cluster: ${response.statusText}`)
  }
  return response.json()
}