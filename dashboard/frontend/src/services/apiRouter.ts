/**
 * API Router — Feature flag routing between FastAPI and Supabase backends.
 *
 * Toggle via VITE_USE_SUPABASE=true in environment variables.
 *
 * When Supabase is enabled:
 *   - All data flows directly from browser → Supabase PostgreSQL
 *   - No FastAPI backend needed
 *   - Full read/write on Vercel
 *
 * When Supabase is disabled (default):
 *   - All data flows through FastAPI backend (existing behavior)
 *   - Static JSON fallback for Vercel read-only mode
 */

import * as restApi from './api'
import * as supabaseApi from './supabaseApi'

const useSupabase = import.meta.env.VITE_USE_SUPABASE === 'true'

// ============================================================
// Search & Question Management
// ============================================================
export const searchQuestions = useSupabase ? supabaseApi.searchQuestions : restApi.searchQuestions
export const getFilterOptions = useSupabase ? supabaseApi.getFilterOptions : restApi.getFilterOptions
export const getDynamicFilterOptions = useSupabase ? supabaseApi.getDynamicFilterOptions : restApi.getDynamicFilterOptions
export const getQuestionDetail = useSupabase ? supabaseApi.getQuestionDetail : restApi.getQuestionDetail
export const getStats = useSupabase ? supabaseApi.getStats : restApi.getStats

// ============================================================
// Tag Updates & Review
// ============================================================
export const updateQuestionTags = useSupabase ? supabaseApi.updateQuestionTags : restApi.updateQuestionTags
export const flagQuestion = useSupabase ? supabaseApi.flagQuestion : restApi.flagQuestion
export const updateOncologyStatus = useSupabase ? supabaseApi.updateOncologyStatus : restApi.updateOncologyStatus
export const markDataError = useSupabase ? supabaseApi.markDataError : restApi.markDataError

// ============================================================
// User-Defined Values
// ============================================================
export const getUserDefinedValues = useSupabase ? supabaseApi.getUserDefinedValues : restApi.getUserDefinedValues
export const getUserDefinedValuesForField = useSupabase ? supabaseApi.getUserDefinedValuesForField : restApi.getUserDefinedValuesForField

// ============================================================
// Reports & Performance Analytics
// ============================================================
export const aggregateByTag = useSupabase ? supabaseApi.aggregateByTag : restApi.aggregateByTag
export const aggregateByTagWithSegments = useSupabase ? supabaseApi.aggregateByTagWithSegments : restApi.aggregateByTagWithSegments
export const aggregateByDemographic = useSupabase ? supabaseApi.aggregateByDemographic : restApi.aggregateByDemographic
export const aggregateBySegment = useSupabase ? supabaseApi.aggregateBySegment : restApi.aggregateBySegment
export const getSegmentOptions = useSupabase ? supabaseApi.getSegmentOptions : restApi.getSegmentOptions
export const getPerformanceTrends = useSupabase ? supabaseApi.getPerformanceTrends : restApi.getPerformanceTrends
export const getDemographicOptions = useSupabase ? supabaseApi.getDemographicOptions : restApi.getDemographicOptions
export const getActivities = useSupabase ? supabaseApi.getActivities : restApi.getActivities
export const updateActivity = useSupabase ? supabaseApi.updateActivity : restApi.updateActivity
export const getReportStats = useSupabase ? supabaseApi.getReportStats : restApi.getReportStats

// ============================================================
// Export Functions
// ============================================================
export const exportQuestionsForReport = useSupabase ? supabaseApi.exportQuestionsForReport : restApi.exportQuestionsForReport
export const exportQuestions = useSupabase ? supabaseApi.exportQuestions : (restApi as any).exportQuestions
export const exportQuestionsFull = useSupabase ? supabaseApi.exportQuestionsFull : restApi.exportQuestionsFull

// ============================================================
// Tag Proposals
// ============================================================
export const getProposalStats = useSupabase ? supabaseApi.getProposalStats : restApi.getProposalStats
export const getProposals = useSupabase ? supabaseApi.getProposals : restApi.getProposals
export const createProposal = useSupabase ? supabaseApi.createProposal : restApi.createProposal
export const getProposal = useSupabase ? supabaseApi.getProposal : restApi.getProposal
export const reviewProposalCandidates = useSupabase ? supabaseApi.reviewProposalCandidates : restApi.reviewProposalCandidates
export const applyProposal = useSupabase ? supabaseApi.applyProposal : restApi.applyProposal
export const abandonProposal = useSupabase ? supabaseApi.abandonProposal : restApi.abandonProposal

// ============================================================
// Deduplication
// ============================================================
export const searchDuplicateCandidates = useSupabase ? supabaseApi.searchDuplicateCandidates : restApi.searchDuplicateCandidates
export const createDedupCluster = useSupabase ? supabaseApi.createDedupCluster : restApi.createDedupCluster

// ============================================================
// Supabase-only functions (no FastAPI equivalent)
// ============================================================
export const getUserRole = supabaseApi.getUserRole
export const listUsersWithRoles = supabaseApi.listUsersWithRoles
export const setUserRole = supabaseApi.setUserRole

// ============================================================
// Re-export isSupabase flag for components that need to know
// ============================================================
export const isSupabaseMode = useSupabase
