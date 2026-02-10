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
import { getAuthHeaders, getCurrentUser } from './auth'
import {
  saveLocalEdit,
  saveLocalCustomValue,
  isVercelMode
} from './localEdits'

// API_BASE: Use VITE_API_URL env var if set (for Railway backend), otherwise use relative /api
const API_BASE = import.meta.env.VITE_API_URL || '/api'
const STATIC_DATA_BASE = '/data'

// Cache for static data
let staticQuestionsCache: any[] | null = null
let staticFiltersCache: any | null = null
let staticStatsCache: any | null = null
let staticPerformanceCache: Record<number, any[]> | null = null

/**
 * Load static questions data (for Vercel read-only mode)
 */
async function loadStaticQuestions(): Promise<any[]> {
  if (staticQuestionsCache) return staticQuestionsCache

  try {
    const response = await fetch(`${STATIC_DATA_BASE}/questions.json`)
    if (!response.ok) throw new Error('Static data not available')
    const data = await response.json()
    const questions = data.questions || []
    staticQuestionsCache = questions
    return questions
  } catch (error) {
    console.warn('Failed to load static questions:', error)
    return []
  }
}

/**
 * Load static filter options (for Vercel read-only mode)
 * Ensures all required arrays exist to prevent iteration errors
 */
async function loadStaticFilters(): Promise<FilterOptions> {
  if (staticFiltersCache) return staticFiltersCache

  // Default empty filter options to prevent "not iterable" errors
  const defaultFilters: FilterOptions = {
    topics: [],
    disease_states: [],
    disease_stages: [],
    disease_types: [],
    treatment_lines: [],
    treatments: [],
    biomarkers: [],
    trials: [],
    activities: [],
    source_files: [],
    // Patient Characteristics
    treatment_eligibilities: [],
    age_groups: [],
    fitness_statuses: [],
    organ_dysfunctions: [],
    disease_specific_factors: [],
    comorbidities: [],
    // Treatment Details
    drug_classes: [],
    drug_targets: [],
    prior_therapies: [],
    resistance_mechanisms: [],
    // Clinical Context
    metastatic_sites: [],
    symptoms: [],
    performance_statuses: [],
    // Safety/Toxicity
    toxicity_types: [],
    toxicity_organs: [],
    toxicity_grades: [],
    // Efficacy/Outcomes
    efficacy_endpoints: [],
    outcome_contexts: [],
    clinical_benefits: [],
    // Evidence/Guidelines
    guideline_sources: [],
    evidence_types: [],
    // Question Format
    cme_outcome_levels: [],
    stem_types: [],
    lead_in_types: [],
    answer_formats: [],
    distractor_homogeneities: []
  }

  try {
    const response = await fetch(`${STATIC_DATA_BASE}/filters.json`)
    if (!response.ok) throw new Error('Static filters not available')
    const rawFilters = await response.json()

    // Merge with defaults to ensure all arrays exist
    staticFiltersCache = {
      ...defaultFilters,
      ...rawFilters
    }
    return staticFiltersCache
  } catch (error) {
    console.warn('Failed to load static filters:', error)
    return defaultFilters
  }
}

/**
 * Load static stats (for Vercel read-only mode)
 * Transforms static file format to match Stats interface
 */
async function loadStaticStats(): Promise<Stats> {
  if (staticStatsCache) return staticStatsCache

  try {
    const response = await fetch(`${STATIC_DATA_BASE}/stats.json`)
    if (!response.ok) throw new Error('Static stats not available')
    const rawStats = await response.json()

    // Transform static file format to match Stats interface
    staticStatsCache = {
      total_questions: rawStats.total_questions ?? 0,
      tagged_questions: rawStats.tagged_questions ?? rawStats.total_questions ?? 0,
      total_activities: rawStats.total_activities ?? 0,
      questions_need_review: rawStats.questions_need_review ?? rawStats.needs_review ?? 0
    }
    return staticStatsCache
  } catch (error) {
    console.warn('Failed to load static stats:', error)
    return { total_questions: 0, tagged_questions: 0, total_activities: 0, questions_need_review: 0 }
  }
}

/**
 * Load static performance data (for Vercel read-only mode)
 */
async function loadStaticPerformance(): Promise<Record<number, any[]>> {
  if (staticPerformanceCache) return staticPerformanceCache

  try {
    const response = await fetch(`${STATIC_DATA_BASE}/performance.json`)
    if (!response.ok) throw new Error('Static performance not available')
    staticPerformanceCache = await response.json()
    return staticPerformanceCache || {}
  } catch (error) {
    console.warn('Failed to load static performance:', error)
    return {}
  }
}

/**
 * Filter and paginate static questions (client-side search)
 * Supports full SearchFilters for filtering in Vercel static mode
 */
function searchStaticQuestions(
  questions: any[],
  params: {
    query?: string
    page?: number
    page_size?: number
    sort_by?: string
    sort_desc?: boolean
    // Core filters
    disease_states?: string[]
    topics?: string[]
    source_files?: string[]
    needs_review?: boolean
    // Extended filters for static mode
    treatments?: string[]
    biomarkers?: string[]
    treatment_lines?: string[]
    disease_types?: string[]
    disease_stages?: string[]
    trials?: string[]
    // Tag status filters
    tag_status_filter?: string
    worst_case_agreement?: string
    // Performance/data filters
    has_performance_data?: boolean
    min_sample_size?: number
    exclude_numeric?: boolean
  }
): { questions: any[]; total: number; total_pages: number } {
  const { query, page = 1, page_size = 20, sort_by = 'id', sort_desc = false } = params

  // Filter
  let filtered = questions

  if (query) {
    const lowerQuery = query.toLowerCase()
    filtered = filtered.filter(q =>
      q.question_stem?.toLowerCase().includes(lowerQuery) ||
      q.correct_answer?.toLowerCase().includes(lowerQuery)
    )
  }

  if (params.disease_states?.length) {
    filtered = filtered.filter(q => params.disease_states?.includes(q.disease_state))
  }

  if (params.topics?.length) {
    filtered = filtered.filter(q => params.topics?.includes(q.topic))
  }

  if (params.source_files?.length) {
    filtered = filtered.filter(q => params.source_files?.includes(q.source_file))
  }

  if (params.needs_review !== undefined) {
    filtered = filtered.filter(q => q.needs_review === (params.needs_review ? 1 : 0))
  }

  // Extended filters - check multi-value fields (treatment_1-5, biomarker_1-5, etc.)
  if (params.treatments?.length) {
    filtered = filtered.filter(q => {
      const qTreatments = [q.treatment_1, q.treatment_2, q.treatment_3, q.treatment_4, q.treatment_5].filter(Boolean)
      return params.treatments!.some(t => qTreatments.includes(t))
    })
  }

  if (params.biomarkers?.length) {
    filtered = filtered.filter(q => {
      const qBiomarkers = [q.biomarker_1, q.biomarker_2, q.biomarker_3, q.biomarker_4, q.biomarker_5].filter(Boolean)
      return params.biomarkers!.some(b => qBiomarkers.includes(b))
    })
  }

  if (params.treatment_lines?.length) {
    filtered = filtered.filter(q => params.treatment_lines?.includes(q.treatment_line))
  }

  if (params.disease_types?.length) {
    filtered = filtered.filter(q => {
      const qTypes = [q.disease_type_1, q.disease_type_2].filter(Boolean)
      return params.disease_types!.some(t => qTypes.includes(t))
    })
  }

  if (params.disease_stages?.length) {
    filtered = filtered.filter(q => params.disease_stages?.includes(q.disease_stage))
  }

  if (params.trials?.length) {
    filtered = filtered.filter(q => {
      const qTrials = [q.trial_1, q.trial_2, q.trial_3, q.trial_4, q.trial_5].filter(Boolean)
      return params.trials!.some(t => qTrials.includes(t))
    })
  }

  // Tag status filters
  if (params.tag_status_filter) {
    if (params.tag_status_filter === 'verified_only') {
      filtered = filtered.filter(q => q.tag_status === 'verified')
    } else if (params.tag_status_filter === 'verified_or_unanimous') {
      filtered = filtered.filter(q => ['verified', 'unanimous'].includes(q.tag_status))
    } else if (params.tag_status_filter === 'verified_unanimous_majority') {
      filtered = filtered.filter(q => ['verified', 'unanimous', 'majority'].includes(q.tag_status))
    }
  }

  if (params.worst_case_agreement) {
    filtered = filtered.filter(q => q.worst_case_agreement === params.worst_case_agreement)
  }

  // Performance/data filters
  if (params.has_performance_data) {
    // Only questions with both pre AND post test scores
    filtered = filtered.filter(q => q.pre_score != null && q.post_score != null)
  }

  if (params.min_sample_size && params.min_sample_size > 0) {
    filtered = filtered.filter(q => (q.sample_size ?? 0) >= params.min_sample_size!)
  }

  if (params.exclude_numeric) {
    // Hide questions with data_response_type = 'Numeric'
    filtered = filtered.filter(q => q.data_response_type !== 'Numeric')
  }

  // Sort
  const sortField = sort_by || 'id'
  filtered.sort((a, b) => {
    const aVal = a[sortField] ?? ''
    const bVal = b[sortField] ?? ''
    if (aVal < bVal) return sort_desc ? 1 : -1
    if (aVal > bVal) return sort_desc ? -1 : 1
    return 0
  })

  // Paginate
  const total = filtered.length
  const total_pages = Math.ceil(total / page_size)
  const start = (page - 1) * page_size
  const paged = filtered.slice(start, start + page_size)

  return { questions: paged, total, total_pages }
}

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
// Falls back to static JSON data when API is unavailable (Vercel mode)
export async function searchQuestions(params: SearchFilters & {
  query?: string
  page?: number
  page_size?: number
  sort_by?: string
  sort_desc?: boolean
}): Promise<SearchResponse> {
  const { query, page = 1, page_size = 20, sort_by = 'id', sort_desc = false, ...filters } = params

  // Try API first
  try {
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

    if (response.ok) {
      return response.json()
    }
    // If API fails, fall through to static data
  } catch (error) {
    console.warn('API unavailable, using static data:', error)
  }

  // Fallback to static JSON data (Vercel mode)
  const questions = await loadStaticQuestions()
  const performanceData = await loadStaticPerformance()

  // Merge performance data with questions
  const questionsWithPerformance = questions.map(q => {
    const perf = performanceData[q.id]
    if (perf && perf.length > 0) {
      // Find 'overall' segment or use first available
      const overall = perf.find((p: any) => p.activity_name === 'overall') || perf[0]
      return {
        ...q,
        pre_score: overall?.pre_score ?? null,
        post_score: overall?.post_score ?? null,
        knowledge_gain: overall?.pre_score != null && overall?.post_score != null
          ? parseFloat((overall.post_score - overall.pre_score).toFixed(1))
          : null,
        sample_size: overall?.sample_size ?? null
      }
    }
    return q
  })

  const result = searchStaticQuestions(questionsWithPerformance, {
    query,
    page,
    page_size,
    sort_by,
    sort_desc,
    // Core filters
    disease_states: filters.disease_states,
    topics: filters.topics,
    source_files: filters.source_files,
    needs_review: filters.needs_review,
    // Extended filters for full static mode support
    treatments: filters.treatments,
    biomarkers: filters.biomarkers,
    treatment_lines: filters.treatment_lines,
    disease_types: filters.disease_types,
    disease_stages: filters.disease_stages,
    trials: filters.trials,
    tag_status_filter: filters.tag_status_filter,
    worst_case_agreement: filters.worst_case_agreement,
    // Performance/data filters
    has_performance_data: filters.has_performance_data,
    min_sample_size: filters.min_sample_size,
    exclude_numeric: filters.exclude_numeric
  })

  return {
    questions: result.questions,
    total: result.total,
    total_pages: result.total_pages,
    page,
    page_size
  }
}

// Get filter options
// Falls back to static JSON data when API is unavailable (Vercel mode)
export async function getFilterOptions(): Promise<FilterOptions> {
  try {
    const response = await authFetch(`${API_BASE}/questions/filters/options`)
    if (response.ok) {
      return response.json()
    }
  } catch (error) {
    console.warn('API unavailable, using static filters:', error)
  }

  // Fallback to static data
  return loadStaticFilters()
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
// Falls back to static JSON data when API is unavailable (Vercel mode)
export async function getQuestionDetail(id: number): Promise<QuestionDetailData> {
  try {
    const response = await authFetch(`${API_BASE}/questions/${id}`)
    if (response.ok) {
      return response.json()
    }
  } catch (error) {
    console.warn('API unavailable, using static data:', error)
  }

  // Fallback to static data
  const questions = await loadStaticQuestions()
  const question = questions.find(q => q.id === id)

  if (!question) {
    throw new Error(`Question ${id} not found`)
  }

  // Load performance data
  const performanceData = await loadStaticPerformance()
  const performance = performanceData[id] || []

  // Build QuestionDetailData structure from flat static data
  return {
    id: question.id,
    source_id: question.source_id,
    source_question_id: question.source_question_id,
    question_stem: question.question_stem,
    correct_answer: question.correct_answer,
    incorrect_answers: question.incorrect_answers ? JSON.parse(question.incorrect_answers) : null,
    source_file: question.source_file,
    qcore_score: question.qcore_score,
    qcore_grade: question.qcore_grade,
    qcore_breakdown: question.qcore_breakdown ? JSON.parse(question.qcore_breakdown) : null,
    tags: {
      topic: question.topic,
      topic_confidence: question.topic_confidence,
      topic_method: question.topic_method,
      disease_state: question.disease_state,
      disease_state_confidence: question.disease_state_confidence,
      disease_state_1: question.disease_state_1,
      disease_state_2: question.disease_state_2,
      disease_stage: question.disease_stage,
      disease_stage_confidence: question.disease_stage_confidence,
      disease_type_1: question.disease_type_1,
      disease_type_2: question.disease_type_2,
      disease_type_confidence: question.disease_type_confidence,
      treatment_line: question.treatment_line,
      treatment_line_confidence: question.treatment_line_confidence,
      treatment_1: question.treatment_1,
      treatment_2: question.treatment_2,
      treatment_3: question.treatment_3,
      treatment_4: question.treatment_4,
      treatment_5: question.treatment_5,
      treatment_confidence: question.treatment_confidence,
      biomarker_1: question.biomarker_1,
      biomarker_2: question.biomarker_2,
      biomarker_3: question.biomarker_3,
      biomarker_4: question.biomarker_4,
      biomarker_5: question.biomarker_5,
      biomarker_confidence: question.biomarker_confidence,
      trial_1: question.trial_1,
      trial_2: question.trial_2,
      trial_3: question.trial_3,
      trial_4: question.trial_4,
      trial_5: question.trial_5,
      trial_confidence: question.trial_confidence,
      treatment_eligibility: question.treatment_eligibility,
      age_group: question.age_group,
      organ_dysfunction: question.organ_dysfunction,
      fitness_status: question.fitness_status,
      disease_specific_factor: question.disease_specific_factor,
      comorbidity_1: question.comorbidity_1,
      comorbidity_2: question.comorbidity_2,
      comorbidity_3: question.comorbidity_3,
      drug_class_1: question.drug_class_1,
      drug_class_2: question.drug_class_2,
      drug_class_3: question.drug_class_3,
      drug_target_1: question.drug_target_1,
      drug_target_2: question.drug_target_2,
      drug_target_3: question.drug_target_3,
      prior_therapy_1: question.prior_therapy_1,
      prior_therapy_2: question.prior_therapy_2,
      prior_therapy_3: question.prior_therapy_3,
      resistance_mechanism: question.resistance_mechanism,
      metastatic_site_1: question.metastatic_site_1,
      metastatic_site_2: question.metastatic_site_2,
      metastatic_site_3: question.metastatic_site_3,
      symptom_1: question.symptom_1,
      symptom_2: question.symptom_2,
      symptom_3: question.symptom_3,
      performance_status: question.performance_status,
      toxicity_type_1: question.toxicity_type_1,
      toxicity_type_2: question.toxicity_type_2,
      toxicity_type_3: question.toxicity_type_3,
      toxicity_type_4: question.toxicity_type_4,
      toxicity_type_5: question.toxicity_type_5,
      toxicity_organ: question.toxicity_organ,
      toxicity_grade: question.toxicity_grade,
      efficacy_endpoint_1: question.efficacy_endpoint_1,
      efficacy_endpoint_2: question.efficacy_endpoint_2,
      efficacy_endpoint_3: question.efficacy_endpoint_3,
      outcome_context: question.outcome_context,
      clinical_benefit: question.clinical_benefit,
      guideline_source_1: question.guideline_source_1,
      guideline_source_2: question.guideline_source_2,
      evidence_type: question.evidence_type,
      cme_outcome_level: question.cme_outcome_level,
      data_response_type: question.data_response_type,
      stem_type: question.stem_type,
      lead_in_type: question.lead_in_type,
      answer_format: question.answer_format,
      answer_length_pattern: question.answer_length_pattern,
      distractor_homogeneity: question.distractor_homogeneity,
      flaw_absolute_terms: question.flaw_absolute_terms,
      flaw_grammatical_cue: question.flaw_grammatical_cue,
      flaw_implausible_distractor: question.flaw_implausible_distractor,
      flaw_clang_association: question.flaw_clang_association,
      flaw_convergence_vulnerability: question.flaw_convergence_vulnerability,
      flaw_double_negative: question.flaw_double_negative,
      answer_option_count: question.answer_option_count,
      correct_answer_position: question.correct_answer_position,
      needs_review: question.needs_review,
      review_flags: question.review_flags,
      review_reason: question.review_reason,
      flagged_at: question.flagged_at,
      agreement_level: question.agreement_level,
      tag_status: question.tag_status,
      worst_case_agreement: question.worst_case_agreement,
      review_notes: question.review_notes
    },
    performance,
    activities: [],
    activity_details: []
  }
}

// Get stats
// Falls back to static JSON data when API is unavailable (Vercel mode)
export async function getStats(): Promise<Stats> {
  try {
    const response = await authFetch(`${API_BASE}/questions/stats/summary`)
    if (response.ok) {
      return response.json()
    }
  } catch (error) {
    console.warn('API unavailable, using static stats:', error)
  }

  // Fallback to static data
  return loadStaticStats()
}

// Tag update payload type (70-field schema)
export type TagUpdatePayload = {
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
  review_notes?: string | null  // Reviewer comments for few-shot learning
  // User-defined values to persist (custom values not in static dropdown lists)
  custom_values?: Array<{ field_name: string; value: string }>
}

// Update question tags (70-field schema)
// In Vercel mode, saves to localStorage instead of API
export async function updateQuestionTags(
  id: number,
  tags: TagUpdatePayload,
  previousValues?: Record<string, string | null>
): Promise<{ savedLocally: boolean }> {
  // Check if we're in Vercel (read-only) mode
  if (isVercelMode()) {
    // Save to localStorage instead of API
    const user = getCurrentUser()

    // Extract the changes (non-meta fields)
    const changes: Record<string, string | null> = {}
    const metaFields = ['mark_as_reviewed', 'custom_values', 'question_stem', 'review_notes']

    for (const [key, value] of Object.entries(tags)) {
      if (!metaFields.includes(key)) {
        changes[key] = value as string | null
      }
    }

    // Save custom values to local storage
    if (tags.custom_values) {
      for (const cv of tags.custom_values) {
        saveLocalCustomValue(cv.field_name, cv.value)
      }
    }

    // Save the edit
    saveLocalEdit({
      questionId: id,
      editor: user?.email || user?.name || 'unknown',
      changes,
      previousValues,
      markAsReviewed: tags.mark_as_reviewed,
      questionStem: tags.question_stem || undefined,
      reviewNotes: tags.review_notes || undefined
    })

    return { savedLocally: true }
  }

  // Normal mode - save to API
  const response = await authFetch(`${API_BASE}/questions/${id}/tags`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(tags)
  })

  if (!response.ok) {
    throw new Error(`Failed to update tags: ${response.statusText}`)
  }

  return { savedLocally: false }
}

// Flag question for review
// In Vercel mode, saves the flag to localStorage
export async function flagQuestion(id: number, reasons: string[]): Promise<{ savedLocally: boolean }> {
  // Check if we're in Vercel (read-only) mode
  if (isVercelMode()) {
    const user = getCurrentUser()
    // Save as a local edit with the flag information
    saveLocalEdit({
      questionId: id,
      editor: user?.email || user?.name || 'unknown',
      changes: {
        needs_review: 'true',
        review_flags: reasons.join(', ')
      },
      previousValues: {}
    })
    return { savedLocally: true }
  }

  const response = await authFetch(`${API_BASE}/questions/${id}/flag`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reasons })
  })

  if (!response.ok) {
    throw new Error(`Failed to flag question: ${response.statusText}`)
  }

  return { savedLocally: false }
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

// Mark a question as having a data error (hides it from dashboard)
export async function markDataError(id: number, errorType: string = 'data_quality', errorDetails?: string): Promise<void> {
  const params = new URLSearchParams({ error_type: errorType })
  if (errorDetails) {
    params.append('error_details', errorDetails)
  }

  const response = await authFetch(`${API_BASE}/questions/${id}/data-error?${params}`, {
    method: 'POST'
  })

  if (!response.ok) {
    throw new Error(`Failed to mark data error: ${response.statusText}`)
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