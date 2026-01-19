/**
 * API Client for V3 CME Outcomes Dashboard
 *
 * Includes endpoints for:
 * - Questions search and management
 * - 3-model voting tagging
 * - Human review workflow
 * - Statistics and reports
 */

import type {
  Question,
  FilterOptions,
  SearchFilters,
  Stats,
  VotingResult,
  ReviewQuestion,
  ReviewCorrection,
  DisagreementPattern,
  TaggingJob,
  TaggingStats,
  ReviewStats,
  Tags,
} from '../types'

const API_BASE = '/api'

// Helper to build query string
function buildQueryString(params: Record<string, unknown>): string {
  const searchParams = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null) continue
    if (Array.isArray(value)) {
      value.forEach(v => searchParams.append(key, String(v)))
    } else {
      searchParams.append(key, String(value))
    }
  }
  return searchParams.toString()
}

// ============== Questions API ==============

export async function searchQuestions(params: SearchFilters & {
  query?: string
  page?: number
  page_size?: number
  sort_by?: string
  sort_desc?: boolean
  review_flag_filter?: string
}): Promise<{
  questions: Question[]
  total: number
  page: number
  total_pages: number
}> {
  const queryString = buildQueryString(params)
  const response = await fetch(`${API_BASE}/questions/search?${queryString}`)
  if (!response.ok) throw new Error('Failed to search questions')
  return response.json()
}

export async function getQuestionDetail(questionId: number): Promise<Question> {
  const response = await fetch(`${API_BASE}/questions/${questionId}`)
  if (!response.ok) throw new Error('Failed to get question detail')
  return response.json()
}

export async function getFilterOptions(): Promise<FilterOptions> {
  const response = await fetch(`${API_BASE}/questions/filters`)
  if (!response.ok) throw new Error('Failed to get filter options')
  return response.json()
}

export async function getDynamicFilterOptions(filters: SearchFilters): Promise<FilterOptions> {
  const queryString = buildQueryString(filters)
  const response = await fetch(`${API_BASE}/questions/filters/dynamic?${queryString}`)
  if (!response.ok) throw new Error('Failed to get dynamic filter options')
  return response.json()
}

export async function getStats(): Promise<Stats> {
  const response = await fetch(`${API_BASE}/questions/stats`)
  if (!response.ok) throw new Error('Failed to get stats')
  return response.json()
}

export async function updateQuestionTags(questionId: number, tags: Tags): Promise<void> {
  const response = await fetch(`${API_BASE}/questions/${questionId}/tags`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(tags),
  })
  if (!response.ok) throw new Error('Failed to update tags')
}

// ============== V3 Tagging API ==============

export async function createTaggingJob(
  questionIds: number[],
  iteration: number = 1,
  useWebSearch: boolean = true
): Promise<TaggingJob> {
  const response = await fetch(`${API_BASE}/tagging/jobs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question_ids: questionIds,
      iteration,
      use_web_search: useWebSearch,
    }),
  })
  if (!response.ok) throw new Error('Failed to create tagging job')
  return response.json()
}

export async function getTaggingJobStatus(jobId: string): Promise<TaggingJob> {
  const response = await fetch(`${API_BASE}/tagging/jobs/${jobId}`)
  if (!response.ok) throw new Error('Failed to get job status')
  return response.json()
}

export async function listTaggingJobs(status?: string, limit: number = 10): Promise<TaggingJob[]> {
  const params = new URLSearchParams()
  if (status) params.append('status', status)
  params.append('limit', String(limit))
  const response = await fetch(`${API_BASE}/tagging/jobs?${params}`)
  if (!response.ok) throw new Error('Failed to list jobs')
  return response.json()
}

export async function cancelTaggingJob(jobId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/tagging/jobs/${jobId}`, {
    method: 'DELETE',
  })
  if (!response.ok) throw new Error('Failed to cancel job')
}

export async function tagSingleQuestion(
  questionId: number,
  useWebSearch: boolean = true
): Promise<VotingResult> {
  const response = await fetch(
    `${API_BASE}/tagging/tag-single/${questionId}?use_web_search=${useWebSearch}`,
    { method: 'POST' }
  )
  if (!response.ok) throw new Error('Failed to tag question')
  return response.json()
}

export async function getVotingResults(params: {
  agreement_level?: string
  needs_review?: boolean
  iteration?: number
  page?: number
  page_size?: number
}): Promise<{
  results: VotingResult[]
  total: number
  page: number
  total_pages: number
}> {
  const queryString = buildQueryString(params)
  const response = await fetch(`${API_BASE}/tagging/results?${queryString}`)
  if (!response.ok) throw new Error('Failed to get voting results')
  return response.json()
}

export async function getVotingResultsForQuestion(questionId: number): Promise<{
  question_id: number
  results: VotingResult[]
  total_iterations: number
}> {
  const response = await fetch(`${API_BASE}/tagging/results/by-question/${questionId}`)
  if (!response.ok) throw new Error('Failed to get voting results for question')
  return response.json()
}

export async function getTaggingStats(): Promise<TaggingStats> {
  const response = await fetch(`${API_BASE}/tagging/stats`)
  if (!response.ok) throw new Error('Failed to get tagging stats')
  return response.json()
}

// ============== V3 Review API ==============

export async function getReviewQueue(params: {
  agreement_level?: string
  iteration?: number
  category?: string
  page?: number
  page_size?: number
}): Promise<{
  questions: ReviewQuestion[]
  total: number
  page: number
  total_pages: number
  stats: {
    conflicts: number
    majority_votes: number
    total_pending: number
  }
}> {
  const queryString = buildQueryString(params)
  const response = await fetch(`${API_BASE}/review/queue?${queryString}`)
  if (!response.ok) throw new Error('Failed to get review queue')
  return response.json()
}

export async function getReviewItem(questionId: number): Promise<{
  question: Question
  voting_result: VotingResult | null
  web_searches: unknown[]
  previous_corrections: ReviewCorrection[]
  suggested_tags: Tags | null
}> {
  const response = await fetch(`${API_BASE}/review/queue/${questionId}`)
  if (!response.ok) throw new Error('Failed to get review item')
  return response.json()
}

export async function submitCorrection(
  questionId: number,
  correction: ReviewCorrection
): Promise<{ success: boolean; correction_id: number }> {
  const response = await fetch(`${API_BASE}/review/corrections/${questionId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(correction),
  })
  if (!response.ok) throw new Error('Failed to submit correction')
  return response.json()
}

export async function listCorrections(params: {
  iteration?: number
  category?: string
  page?: number
  page_size?: number
}): Promise<{
  corrections: ReviewCorrection[]
  total: number
  page: number
  total_pages: number
}> {
  const queryString = buildQueryString(params)
  const response = await fetch(`${API_BASE}/review/corrections?${queryString}`)
  if (!response.ok) throw new Error('Failed to list corrections')
  return response.json()
}

export async function getDisagreementPatterns(params: {
  iteration?: number
  implemented?: boolean
}): Promise<{
  patterns: DisagreementPattern[]
  total: number
}> {
  const queryString = buildQueryString(params)
  const response = await fetch(`${API_BASE}/review/patterns?${queryString}`)
  if (!response.ok) throw new Error('Failed to get patterns')
  return response.json()
}

export async function analyzePatterns(iteration: number): Promise<{
  iteration: number
  patterns_found: number
  patterns: DisagreementPattern[]
  recommendations: { category: string; frequency: number; action: string }[]
}> {
  const response = await fetch(`${API_BASE}/review/patterns/analyze?iteration=${iteration}`, {
    method: 'POST',
  })
  if (!response.ok) throw new Error('Failed to analyze patterns')
  return response.json()
}

export async function getReviewStats(): Promise<ReviewStats> {
  const response = await fetch(`${API_BASE}/review/stats`)
  if (!response.ok) throw new Error('Failed to get review stats')
  return response.json()
}

export async function getSpotCheckQueue(count: number = 10): Promise<{
  questions: ReviewQuestion[]
  total_available: number
  sample_rate: number
}> {
  const response = await fetch(`${API_BASE}/review/spot-checks?count=${count}`)
  if (!response.ok) throw new Error('Failed to get spot check queue')
  return response.json()
}

export async function submitSpotCheck(
  questionId: number,
  isCorrect: boolean,
  correction?: ReviewCorrection
): Promise<{ success: boolean; correction_id?: number }> {
  const response = await fetch(
    `${API_BASE}/review/spot-checks/${questionId}/verify?is_correct=${isCorrect}`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: correction ? JSON.stringify(correction) : undefined,
    }
  )
  if (!response.ok) throw new Error('Failed to submit spot check')
  return response.json()
}

export async function batchApproveUnanimous(iteration: number): Promise<{
  success: boolean
  approved_count: number
}> {
  const response = await fetch(`${API_BASE}/review/batch/approve-unanimous?iteration=${iteration}`, {
    method: 'POST',
  })
  if (!response.ok) throw new Error('Failed to approve unanimous')
  return response.json()
}
