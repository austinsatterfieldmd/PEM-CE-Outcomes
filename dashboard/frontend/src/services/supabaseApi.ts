/**
 * Supabase API Service Layer
 *
 * Mirrors all functions in api.ts but uses Supabase client directly
 * instead of fetch() to FastAPI backend.
 *
 * Toggled via VITE_USE_SUPABASE=true in environment.
 */

import { getSupabaseClient } from './supabase'
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

// ============================================================
// Search & Question Management
// ============================================================

export async function searchQuestions(params: SearchFilters & {
  page?: number
  page_size?: number
  sort_by?: string
  sort_desc?: boolean
}): Promise<SearchResponse> {
  const supabase = getSupabaseClient()

  const { data, error } = await supabase.rpc('search_questions', {
    p_query: params.query || null,
    p_topics: params.topics?.length ? params.topics : null,
    p_disease_states: params.disease_states?.length ? params.disease_states : null,
    p_disease_stages: params.disease_stages?.length ? params.disease_stages : null,
    p_disease_types: params.disease_types?.length ? params.disease_types : null,
    p_treatment_lines: params.treatment_lines?.length ? params.treatment_lines : null,
    p_treatments: params.treatments?.length ? params.treatments : null,
    p_biomarkers: params.biomarkers?.length ? params.biomarkers : null,
    p_trials: params.trials?.length ? params.trials : null,
    p_activities: params.activities?.length ? params.activities : null,
    p_source_files: params.source_files?.length ? params.source_files : null,
    p_treatment_eligibilities: params.treatment_eligibilities?.length ? params.treatment_eligibilities : null,
    p_age_groups: params.age_groups?.length ? params.age_groups : null,
    p_fitness_statuses: params.fitness_statuses?.length ? params.fitness_statuses : null,
    p_organ_dysfunctions: params.organ_dysfunctions?.length ? params.organ_dysfunctions : null,
    p_min_confidence: params.min_confidence ?? null,
    p_max_confidence: params.max_confidence ?? null,
    p_has_performance_data: params.has_performance_data ?? null,
    p_min_sample_size: params.min_sample_size ?? null,
    p_needs_review: params.needs_review ?? null,
    p_worst_case_agreement: params.worst_case_agreement || null,
    p_tag_status_filter: params.tag_status_filter || null,
    p_exclude_numeric: params.exclude_numeric ?? null,
    p_activity_start_after: params.activity_start_after || null,
    p_activity_start_before: params.activity_start_before || null,
    p_advanced_filters: params.advanced_filters ? JSON.stringify(params.advanced_filters) : null,
    p_page: params.page || 1,
    p_page_size: params.page_size || 20,
    p_sort_by: params.sort_by || 'id',
    p_sort_desc: params.sort_desc || false
  })

  if (error) throw new Error(`Search failed: ${error.message}`)

  const result = data as any
  return {
    questions: result.questions || [],
    total: result.total || 0,
    total_pages: Math.ceil((result.total || 0) / (params.page_size || 20))
  }
}

export async function getFilterOptions(): Promise<FilterOptions> {
  const supabase = getSupabaseClient()
  const { data, error } = await supabase.rpc('get_filter_options')

  if (error) throw new Error(`Filter options failed: ${error.message}`)

  // Transform {value, count} arrays to match FilterOptions type
  const result = data as any
  const transform = (arr: any[]) => (arr || []).map((item: any) => ({
    value: item.value,
    count: item.count
  }))

  return {
    topics: transform(result.topics),
    disease_states: transform(result.disease_states),
    disease_stages: transform(result.disease_stages),
    disease_types: transform(result.disease_types),
    treatment_lines: transform(result.treatment_lines),
    treatments: transform(result.treatments),
    biomarkers: transform(result.biomarkers),
    trials: transform(result.trials),
    activities: transform(result.activities),
    source_files: transform(result.source_files),
    // Extended fields - these are populated by get_filter_options if data exists
    treatment_eligibilities: [],
    age_groups: [],
    fitness_statuses: [],
    organ_dysfunctions: [],
    disease_specific_factors: [],
    comorbidities: [],
    drug_classes: [],
    drug_targets: [],
    prior_therapies: [],
    resistance_mechanisms: [],
    metastatic_sites: [],
    symptoms: [],
    performance_statuses: [],
    toxicity_types: [],
    toxicity_organs: [],
    toxicity_grades: [],
    efficacy_endpoints: [],
    outcome_contexts: [],
    clinical_benefits: [],
    guideline_sources: [],
    evidence_types: [],
    cme_outcome_levels: [],
    stem_types: [],
    lead_in_types: [],
    answer_formats: [],
    distractor_homogeneities: []
  }
}

export async function getDynamicFilterOptions(currentFilters: SearchFilters): Promise<FilterOptions> {
  // For now, return same as static filter options
  // Dynamic filtering can be added as a separate RPC function later
  return getFilterOptions()
}

export async function getQuestionDetail(id: number): Promise<QuestionDetailData> {
  const supabase = getSupabaseClient()
  const { data, error } = await supabase.rpc('get_question_detail', {
    p_question_id: id
  })

  if (error) throw new Error(`Question detail failed: ${error.message}`)
  if (!data) throw new Error('Question not found')

  return data as QuestionDetailData
}

export async function getStats(): Promise<Stats> {
  const supabase = getSupabaseClient()
  const { data, error } = await supabase.rpc('get_stats_summary')

  if (error) throw new Error(`Stats failed: ${error.message}`)

  const result = data as any
  return {
    total_questions: result.total_questions || 0,
    tagged_questions: result.tagged_questions || 0,
    total_activities: result.total_activities || 0,
    questions_need_review: result.needs_review || 0
  }
}

// ============================================================
// Tag Updates & Review
// ============================================================

export async function updateQuestionTags(
  questionId: number,
  tags: Record<string, any>,
  previousValues?: Record<string, any>
): Promise<any> {
  const supabase = getSupabaseClient()

  // Extract special fields
  const markAsReviewed = tags.mark_as_reviewed
  const reviewNotes = tags.review_notes
  const questionStem = tags.question_stem

  // Build update object for tags table
  const tagUpdate: Record<string, any> = {}
  const tagFields = [
    'topic', 'disease_state', 'disease_stage', 'disease_type_1', 'disease_type_2',
    'treatment_line', 'treatment_1', 'treatment_2', 'treatment_3', 'treatment_4', 'treatment_5',
    'biomarker_1', 'biomarker_2', 'biomarker_3', 'biomarker_4', 'biomarker_5',
    'trial_1', 'trial_2', 'trial_3', 'trial_4', 'trial_5',
    'treatment_eligibility', 'age_group', 'organ_dysfunction', 'fitness_status',
    'disease_specific_factor', 'comorbidity_1', 'comorbidity_2', 'comorbidity_3',
    'drug_class_1', 'drug_class_2', 'drug_class_3',
    'drug_target_1', 'drug_target_2', 'drug_target_3',
    'prior_therapy_1', 'prior_therapy_2', 'prior_therapy_3', 'resistance_mechanism',
    'metastatic_site_1', 'metastatic_site_2', 'metastatic_site_3',
    'symptom_1', 'symptom_2', 'symptom_3', 'performance_status',
    'special_population_1', 'special_population_2',
    'toxicity_type_1', 'toxicity_type_2', 'toxicity_type_3', 'toxicity_type_4', 'toxicity_type_5',
    'toxicity_organ', 'toxicity_grade',
    'efficacy_endpoint_1', 'efficacy_endpoint_2', 'efficacy_endpoint_3',
    'outcome_context', 'clinical_benefit',
    'guideline_source_1', 'guideline_source_2', 'evidence_type',
    'cme_outcome_level', 'data_response_type', 'stem_type', 'lead_in_type',
    'answer_format', 'answer_length_pattern', 'distractor_homogeneity',
    'flaw_absolute_terms', 'flaw_grammatical_cue', 'flaw_implausible_distractor',
    'flaw_clang_association', 'flaw_convergence_vulnerability', 'flaw_double_negative',
    'answer_option_count', 'correct_answer_position'
  ]

  for (const field of tagFields) {
    if (field in tags) {
      tagUpdate[field] = tags[field]
    }
  }

  if (markAsReviewed) {
    tagUpdate.edited_by_user = true
    tagUpdate.edited_at = new Date().toISOString()
    tagUpdate.needs_review = false
    tagUpdate.tag_status = 'verified'
    tagUpdate.worst_case_agreement = 'verified'
  }

  if (reviewNotes !== undefined) {
    tagUpdate.review_notes = reviewNotes
  }

  // Update tags
  const { error: tagError } = await supabase
    .from('tags')
    .update(tagUpdate)
    .eq('question_id', questionId)

  if (tagError) throw new Error(`Tag update failed: ${tagError.message}`)

  // Update question stem if provided
  if (questionStem) {
    const { error: stemError } = await supabase
      .from('questions')
      .update({ question_stem: questionStem })
      .eq('id', questionId)

    if (stemError) throw new Error(`Stem update failed: ${stemError.message}`)
  }

  return { success: true, question_id: questionId }
}

export async function flagQuestion(id: number, reasons: string[]): Promise<{ savedLocally: boolean }> {
  const supabase = getSupabaseClient()

  const { error } = await supabase
    .from('tags')
    .update({
      needs_review: true,
      review_reason: reasons.join('|'),
      flagged_at: new Date().toISOString()
    })
    .eq('question_id', id)

  if (error) throw new Error(`Flag failed: ${error.message}`)
  return { savedLocally: false }
}

export async function updateOncologyStatus(id: number, isOncology: boolean): Promise<void> {
  const supabase = getSupabaseClient()

  const { error } = await supabase
    .from('questions')
    .update({ is_oncology: isOncology })
    .eq('id', id)

  if (error) throw new Error(`Oncology status update failed: ${error.message}`)
}

export async function markDataError(id: number, errorType: string = 'data_quality', errorDetails?: string): Promise<void> {
  const supabase = getSupabaseClient()

  const { error } = await supabase
    .from('data_error_questions')
    .upsert({
      question_id: id,
      error_type: errorType,
      error_details: errorDetails || null,
      reported_by: 'user'
    }, { onConflict: 'question_id' })

  if (error) throw new Error(`Data error marking failed: ${error.message}`)
}

// ============================================================
// User-Defined Values
// ============================================================

export async function getUserDefinedValues(): Promise<Record<string, string[]>> {
  const supabase = getSupabaseClient()

  const { data, error } = await supabase
    .from('user_defined_values')
    .select('field_name, value')
    .order('field_name')

  if (error) throw new Error(`User values failed: ${error.message}`)

  // Group by field_name
  const grouped: Record<string, string[]> = {}
  for (const row of (data || [])) {
    if (!grouped[row.field_name]) grouped[row.field_name] = []
    grouped[row.field_name].push(row.value)
  }
  return grouped
}

export async function getUserDefinedValuesForField(fieldName: string): Promise<string[]> {
  const supabase = getSupabaseClient()

  const { data, error } = await supabase
    .from('user_defined_values')
    .select('value')
    .eq('field_name', fieldName)

  if (error) throw new Error(`User values for ${fieldName} failed: ${error.message}`)
  return (data || []).map(row => row.value)
}

// ============================================================
// Reports & Performance Analytics
// ============================================================

export async function aggregateByTag(
  groupBy: TagGroupBy,
  filters: ReportFilters
): Promise<AggregatedReportResponse> {
  const supabase = getSupabaseClient()

  const { data, error } = await supabase.rpc('aggregate_by_tag', {
    p_group_by: groupBy,
    p_topics: filters.topics?.length ? filters.topics : null,
    p_disease_states: filters.disease_states?.length ? filters.disease_states : null,
    p_disease_stages: filters.disease_stages?.length ? filters.disease_stages : null,
    p_treatment_lines: filters.treatment_lines?.length ? filters.treatment_lines : null,
    p_treatments: filters.treatments?.length ? filters.treatments : null,
    p_activities: filters.activities?.length ? filters.activities : null,
    p_quarters: filters.quarters?.length ? filters.quarters : null
  })

  if (error) throw new Error(`Aggregate by tag failed: ${error.message}`)
  return { data: data || [] } as AggregatedReportResponse
}

export async function aggregateByTagWithSegments(
  groupBy: TagGroupBy,
  segments: AudienceSegment[],
  filters: ReportFilters
): Promise<AggregatedReportResponse> {
  // Use the same aggregate_by_tag for now
  // A dedicated with-segments RPC can be added later for cross-tab views
  return aggregateByTag(groupBy, filters)
}

export async function aggregateByDemographic(
  segmentBy: DemographicSegment,
  filters: ReportFilters
): Promise<AggregatedReportResponse> {
  // Use performance trends as a proxy for demographic aggregation
  const trends = await getPerformanceTrends(segmentBy, filters)
  return { data: trends.data || [] } as any
}

export async function aggregateBySegment(
  segments?: AudienceSegment[],
  filters?: ReportFilters
): Promise<SegmentReportResponse> {
  const supabase = getSupabaseClient()

  const { data, error } = await supabase.rpc('aggregate_by_segment', {
    p_segments: segments?.length ? segments : null,
    p_topics: filters?.topics?.length ? filters.topics : null,
    p_disease_states: filters?.disease_states?.length ? filters.disease_states : null,
    p_disease_stages: filters?.disease_stages?.length ? filters.disease_stages : null,
    p_treatment_lines: filters?.treatment_lines?.length ? filters.treatment_lines : null
  })

  if (error) throw new Error(`Aggregate by segment failed: ${error.message}`)
  return { data: data || [] } as SegmentReportResponse
}

export async function getSegmentOptions(): Promise<SegmentOptions> {
  return {
    segments: [
      'overall', 'medical_oncologist', 'app', 'academic',
      'community', 'surgical_oncologist', 'radiation_oncologist'
    ]
  } as SegmentOptions
}

export async function getPerformanceTrends(
  segmentBy?: DemographicSegment | string,
  filters?: ReportFilters
): Promise<TrendReportResponse> {
  const supabase = getSupabaseClient()

  const { data, error } = await supabase.rpc('get_performance_trends', {
    p_segment_by: segmentBy || null,
    p_topics: filters?.topics?.length ? filters.topics : null,
    p_disease_states: filters?.disease_states?.length ? filters.disease_states : null,
    p_treatment_lines: filters?.treatment_lines?.length ? filters.treatment_lines : null
  })

  if (error) throw new Error(`Performance trends failed: ${error.message}`)
  return { data: data || [] } as TrendReportResponse
}

export async function getDemographicOptions(): Promise<DemographicOptions> {
  const supabase = getSupabaseClient()

  const { data, error } = await supabase
    .from('demographic_performance')
    .select('specialty, practice_setting, region')

  if (error) throw new Error(`Demographic options failed: ${error.message}`)

  // Extract unique values
  const specialties = new Set<string>()
  const settings = new Set<string>()
  const regions = new Set<string>()

  for (const row of (data || [])) {
    if (row.specialty) specialties.add(row.specialty)
    if (row.practice_setting) settings.add(row.practice_setting)
    if (row.region) regions.add(row.region)
  }

  return {
    specialties: Array.from(specialties).sort(),
    practice_settings: Array.from(settings).sort(),
    regions: Array.from(regions).sort()
  } as DemographicOptions
}

export async function getActivities(params: {
  quarter?: string
  has_date?: boolean
}): Promise<Activity[]> {
  const supabase = getSupabaseClient()

  let query = supabase
    .from('activities')
    .select('*')
    .order('activity_date', { ascending: false, nullsFirst: false })

  if (params.quarter) {
    query = query.eq('quarter', params.quarter)
  }

  if (params.has_date === true) {
    query = query.not('activity_date', 'is', null)
  }

  const { data, error } = await query

  if (error) throw new Error(`Activities failed: ${error.message}`)
  return (data || []) as Activity[]
}

export async function updateActivity(activityName: string, data: {
  activity_date?: string
  quarter?: string
  target_audience?: string
  description?: string
}): Promise<void> {
  const supabase = getSupabaseClient()

  const { error } = await supabase
    .from('activities')
    .update(data)
    .eq('activity_name', activityName)

  if (error) throw new Error(`Activity update failed: ${error.message}`)
}

export async function getReportStats(): Promise<ReportStatsResponse> {
  return getStats() as any
}

// ============================================================
// Export Functions
// ============================================================

export async function exportQuestionsForReport(filters: ReportFilters): Promise<{ questions: any[], total: number }> {
  // Use search with large page size for export
  const result = await searchQuestions({
    ...filters,
    page: 1,
    page_size: 10000
  })
  return { questions: result.questions, total: result.total }
}

export async function exportQuestions(filters: SearchFilters): Promise<{ questions: any[], total: number }> {
  const result = await searchQuestions({
    ...filters,
    page: 1,
    page_size: 10000
  })
  return { questions: result.questions, total: result.total }
}

export async function exportQuestionsFull(filters: SearchFilters): Promise<{ questions: any[], total: number }> {
  // Full export with all 70 fields — get question details for each
  const searchResult = await searchQuestions({
    ...filters,
    page: 1,
    page_size: 10000
  })

  // For full export, we need all tag fields
  // The search results already include basic fields; for full export
  // we query the tags table directly
  const supabase = getSupabaseClient()
  const questionIds = searchResult.questions.map((q: any) => q.id)

  if (questionIds.length === 0) {
    return { questions: [], total: 0 }
  }

  const { data: fullData, error } = await supabase
    .from('tags')
    .select('*, questions!inner(id, source_id, question_stem, correct_answer, incorrect_answers)')
    .in('question_id', questionIds)

  if (error) throw new Error(`Full export failed: ${error.message}`)

  return { questions: fullData || [], total: fullData?.length || 0 }
}

// ============================================================
// Tag Proposals
// ============================================================

interface ProposalStats {
  pending: number
  approved: number
  rejected: number
  total: number
}

interface TagProposal {
  id: number
  field_name: string
  proposed_value: string
  search_query: string
  proposal_reason: string
  status: string
  match_count: number
  approved_count: number
  created_at: string
  created_by: string
  candidates?: any[]
}

export async function getProposalStats(): Promise<ProposalStats> {
  const supabase = getSupabaseClient()

  const { data, error } = await supabase
    .from('tag_proposals')
    .select('status')

  if (error) throw new Error(`Proposal stats failed: ${error.message}`)

  const stats = { pending: 0, approved: 0, rejected: 0, total: 0 }
  for (const row of (data || [])) {
    stats.total++
    if (row.status === 'pending') stats.pending++
    else if (row.status === 'approved') stats.approved++
    else if (row.status === 'rejected') stats.rejected++
  }
  return stats
}

export async function getProposals(status?: string): Promise<TagProposal[]> {
  const supabase = getSupabaseClient()

  let query = supabase
    .from('tag_proposals')
    .select('*')
    .order('created_at', { ascending: false })

  if (status) {
    query = query.eq('status', status)
  }

  const { data, error } = await query
  if (error) throw new Error(`Proposals failed: ${error.message}`)
  return (data || []) as TagProposal[]
}

export async function createProposal(proposalData: {
  field_name: string
  proposed_value: string
  search_query: string
  proposal_reason?: string
}): Promise<TagProposal> {
  const supabase = getSupabaseClient()

  const { data, error } = await supabase
    .from('tag_proposals')
    .insert(proposalData)
    .select()
    .single()

  if (error) throw new Error(`Create proposal failed: ${error.message}`)
  return data as TagProposal
}

export async function getProposal(proposalId: number): Promise<TagProposal> {
  const supabase = getSupabaseClient()

  const { data: proposal, error: propError } = await supabase
    .from('tag_proposals')
    .select('*')
    .eq('id', proposalId)
    .single()

  if (propError) throw new Error(`Get proposal failed: ${propError.message}`)

  const { data: candidates, error: candError } = await supabase
    .from('tag_proposal_candidates')
    .select('*')
    .eq('proposal_id', proposalId)

  if (candError) throw new Error(`Get candidates failed: ${candError.message}`)

  return { ...proposal, candidates: candidates || [] } as TagProposal
}

export async function reviewProposalCandidates(
  proposalId: number,
  decisions: { question_id: number; decision: string; notes?: string }[]
): Promise<any> {
  const supabase = getSupabaseClient()

  for (const dec of decisions) {
    const { error } = await supabase
      .from('tag_proposal_candidates')
      .update({
        decision: dec.decision,
        decided_at: new Date().toISOString(),
        notes: dec.notes || null
      })
      .eq('proposal_id', proposalId)
      .eq('question_id', dec.question_id)

    if (error) throw new Error(`Review candidate failed: ${error.message}`)
  }

  return { success: true }
}

export async function applyProposal(
  proposalId: number,
  reviewedBy?: string
): Promise<any> {
  const supabase = getSupabaseClient()

  // Get proposal details
  const proposal = await getProposal(proposalId)

  // Apply approved candidates
  const approved = (proposal.candidates || []).filter((c: any) => c.decision === 'approved')

  for (const candidate of approved) {
    const { error } = await supabase
      .from('tags')
      .update({ [proposal.field_name]: proposal.proposed_value })
      .eq('question_id', candidate.question_id)

    if (error) throw new Error(`Apply proposal failed for Q${candidate.question_id}: ${error.message}`)
  }

  // Mark proposal as completed
  await supabase
    .from('tag_proposals')
    .update({
      status: 'approved',
      approved_count: approved.length,
      completed_at: new Date().toISOString()
    })
    .eq('id', proposalId)

  return { status: 'applied', applied_count: approved.length }
}

export async function abandonProposal(proposalId: number): Promise<{ status: string; proposal_id: number }> {
  const supabase = getSupabaseClient()

  const { error } = await supabase
    .from('tag_proposals')
    .update({ status: 'rejected', completed_at: new Date().toISOString() })
    .eq('id', proposalId)

  if (error) throw new Error(`Abandon proposal failed: ${error.message}`)
  return { status: 'abandoned', proposal_id: proposalId }
}

// ============================================================
// Deduplication
// ============================================================

export async function searchDuplicateCandidates(
  query: string,
  excludeId?: number,
  limit: number = 10
): Promise<any[]> {
  const supabase = getSupabaseClient()

  let dbQuery = supabase
    .from('questions')
    .select('id, source_id, question_stem')
    .textSearch('fts_vector', query, { type: 'plain' })
    .limit(limit)

  if (excludeId) {
    dbQuery = dbQuery.neq('id', excludeId)
  }

  const { data, error } = await dbQuery
  if (error) throw new Error(`Duplicate search failed: ${error.message}`)
  return data || []
}

export async function createDedupCluster(clusterData: {
  canonical_question_id: number
  members: { question_id: number; similarity: number }[]
  similarity_threshold?: number
}): Promise<any> {
  const supabase = getSupabaseClient()

  // Create cluster
  const { data: cluster, error: clusterError } = await supabase
    .from('duplicate_clusters')
    .insert({
      canonical_question_id: clusterData.canonical_question_id,
      similarity_threshold: clusterData.similarity_threshold || 0.95
    })
    .select()
    .single()

  if (clusterError) throw new Error(`Create cluster failed: ${clusterError.message}`)

  // Add members
  const members = clusterData.members.map(m => ({
    cluster_id: cluster.cluster_id,
    question_id: m.question_id,
    similarity_to_canonical: m.similarity,
    is_canonical: m.question_id === clusterData.canonical_question_id
  }))

  const { error: memberError } = await supabase
    .from('cluster_members')
    .insert(members)

  if (memberError) throw new Error(`Add cluster members failed: ${memberError.message}`)

  return cluster
}

// ============================================================
// User Role Management (Admin)
// ============================================================

export async function getUserRole(): Promise<string> {
  const supabase = getSupabaseClient()
  const { data, error } = await supabase.rpc('get_user_role')

  if (error) {
    console.warn('Failed to get user role:', error.message)
    return 'user' // Default to read-only
  }

  return (data as string) || 'user'
}

export async function listUsersWithRoles(): Promise<any[]> {
  const supabase = getSupabaseClient()
  const { data, error } = await supabase.rpc('list_users_with_roles')

  if (error) throw new Error(`List users failed: ${error.message}`)
  return (data as any[]) || []
}

export async function setUserRole(userId: string, role: string): Promise<any> {
  const supabase = getSupabaseClient()
  const { data, error } = await supabase.rpc('set_user_role', {
    p_user_id: userId,
    p_role: role
  })

  if (error) throw new Error(`Set role failed: ${error.message}`)
  return data
}
