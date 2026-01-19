/**
 * CME Outcomes Dashboard V3
 *
 * Main application with 3-model LLM voting review system.
 *
 * Tabs:
 * - Explorer: Search and browse questions
 * - Review: 3-model voting review queue
 * - Reports: Analytics and reporting (future)
 */

import { useState, useEffect } from 'react'
import { Search, Filter, Database, ClipboardCheck, BarChart3, RefreshCw, Play, X, ChevronDown } from 'lucide-react'
import { ReviewConflicts } from './components/ReviewConflicts'
import {
  searchQuestions,
  getFilterOptions,
  getStats,
  getTaggingStats,
  createTaggingJob,
  listTaggingJobs,
} from './api/client'
import type { Question, FilterOptions, SearchFilters, Stats, TaggingStats, TaggingJob } from './types'

type TabView = 'explorer' | 'review' | 'reports'

function App() {
  const [activeTab, setActiveTab] = useState<TabView>('explorer')

  // Explorer state
  const [questions, setQuestions] = useState<Question[]>([])
  const [filterOptions, setFilterOptions] = useState<FilterOptions | null>(null)
  const [stats, setStats] = useState<Stats | null>(null)
  const [taggingStats, setTaggingStats] = useState<TaggingStats | null>(null)
  const [loading, setLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [filters, setFilters] = useState<SearchFilters>({})
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [total, setTotal] = useState(0)
  const [showFilters, setShowFilters] = useState(false)

  // Tagging job state
  const [activeJobs, setActiveJobs] = useState<TaggingJob[]>([])

  // Load initial data
  useEffect(() => {
    Promise.all([getFilterOptions(), getStats(), getTaggingStats()])
      .then(([options, statsData, taggingStatsData]) => {
        setFilterOptions(options)
        setStats(statsData)
        setTaggingStats(taggingStatsData)
      })
      .catch(console.error)

    // Load active jobs
    listTaggingJobs('running').then(setActiveJobs).catch(console.error)
  }, [])

  // Search when filters change
  useEffect(() => {
    const doSearch = async () => {
      setLoading(true)
      try {
        const result = await searchQuestions({
          query: searchQuery || undefined,
          ...filters,
          page,
          page_size: 20,
        })
        setQuestions(result.questions)
        setTotalPages(result.total_pages)
        setTotal(result.total)
      } catch (error) {
        console.error('Search failed:', error)
      } finally {
        setLoading(false)
      }
    }

    const debounce = setTimeout(doSearch, 300)
    return () => clearTimeout(debounce)
  }, [searchQuery, filters, page])

  // Start tagging job
  const handleStartTagging = async () => {
    if (questions.length === 0) return

    const questionIds = questions.map(q => q.id)
    try {
      const job = await createTaggingJob(questionIds, 1, true)
      setActiveJobs(prev => [...prev, job])
    } catch (error) {
      console.error('Failed to start tagging:', error)
    }
  }

  // Refresh stats
  const handleRefreshStats = async () => {
    try {
      const [statsData, taggingStatsData] = await Promise.all([getStats(), getTaggingStats()])
      setStats(statsData)
      setTaggingStats(taggingStatsData)
    } catch (error) {
      console.error('Failed to refresh stats:', error)
    }
  }

  const activeFilterCount = Object.values(filters).filter(
    v => v && (Array.isArray(v) ? v.length > 0 : true)
  ).length

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-slate-100 flex flex-col">
      {/* Header */}
      <header className="bg-primary-500 border-b border-primary-600 sticky top-0 z-40">
        <div className="max-w-[1600px] mx-auto px-6 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 bg-white/20 rounded-lg flex items-center justify-center">
                <Database className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-bold text-white">CME Outcomes Dashboard</h1>
                <p className="text-sm text-white/70">V3 - 3-Model Voting System</p>
              </div>
            </div>

            {/* Tab Navigation */}
            <div className="flex items-center gap-2">
              <button
                onClick={() => setActiveTab('explorer')}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all ${
                  activeTab === 'explorer'
                    ? 'bg-white text-primary-500 shadow-lg'
                    : 'text-white/80 hover:text-white hover:bg-white/10'
                }`}
              >
                <Database className="w-4 h-4" />
                Explorer
              </button>
              <button
                onClick={() => setActiveTab('review')}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all ${
                  activeTab === 'review'
                    ? 'bg-white text-primary-500 shadow-lg'
                    : 'text-white/80 hover:text-white hover:bg-white/10'
                }`}
              >
                <ClipboardCheck className="w-4 h-4" />
                Review
                {taggingStats && taggingStats.review_pending > 0 && (
                  <span className="px-2 py-0.5 bg-red-500 text-white text-xs rounded-full">
                    {taggingStats.review_pending}
                  </span>
                )}
              </button>
              <button
                onClick={() => setActiveTab('reports')}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all ${
                  activeTab === 'reports'
                    ? 'bg-white text-primary-500 shadow-lg'
                    : 'text-white/80 hover:text-white hover:bg-white/10'
                }`}
              >
                <BarChart3 className="w-4 h-4" />
                Reports
              </button>
            </div>

            {/* Refresh Button */}
            <button
              onClick={handleRefreshStats}
              className="p-2 text-white/80 hover:text-white hover:bg-white/10 rounded-lg transition-all"
              title="Refresh stats"
            >
              <RefreshCw className="w-5 h-5" />
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-[1600px] mx-auto px-6 py-6 flex-1">
        {activeTab === 'explorer' && (
          <>
            {/* Stats Cards */}
            <div className="grid grid-cols-4 gap-4 mb-6">
              <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
                <div className="text-sm text-slate-600">Total Questions</div>
                <div className="text-2xl font-bold text-slate-900">
                  {stats?.total_questions.toLocaleString() || 0}
                </div>
              </div>
              <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
                <div className="text-sm text-slate-600">V3 Tagged</div>
                <div className="text-2xl font-bold text-emerald-600">
                  {taggingStats?.total_tagged.toLocaleString() || 0}
                </div>
              </div>
              <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
                <div className="text-sm text-slate-600">Unanimous (3/3)</div>
                <div className="text-2xl font-bold text-emerald-600">
                  {taggingStats?.by_agreement?.unanimous || 0}
                </div>
              </div>
              <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
                <div className="text-sm text-slate-600">Needs Review</div>
                <div className="text-2xl font-bold text-amber-600">
                  {taggingStats?.review_pending || 0}
                </div>
              </div>
            </div>

            {/* Search Bar */}
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-4 mb-4">
              <div className="flex flex-col md:flex-row gap-4">
                <div className="flex-1 relative">
                  <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                  <input
                    type="text"
                    placeholder="Search questions by keyword..."
                    value={searchQuery}
                    onChange={e => {
                      setSearchQuery(e.target.value)
                      setPage(1)
                    }}
                    className="w-full pl-12 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
                  />
                </div>

                <button
                  onClick={() => setShowFilters(!showFilters)}
                  className={`flex items-center gap-2 px-5 py-3 rounded-xl font-medium transition-all ${
                    showFilters || activeFilterCount > 0
                      ? 'bg-primary-500 text-white shadow-lg'
                      : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                  }`}
                >
                  <Filter className="w-4 h-4" />
                  Filters
                  {activeFilterCount > 0 && (
                    <span className="px-2 py-0.5 bg-white/20 rounded-full text-xs">
                      {activeFilterCount}
                    </span>
                  )}
                  <ChevronDown className={`w-4 h-4 transition-transform ${showFilters ? 'rotate-180' : ''}`} />
                </button>

                {/* Tag Selected Questions Button */}
                <button
                  onClick={handleStartTagging}
                  disabled={questions.length === 0 || loading}
                  className="flex items-center gap-2 px-5 py-3 bg-emerald-500 hover:bg-emerald-600 disabled:bg-slate-300 text-white rounded-xl font-medium transition-all shadow-lg"
                >
                  <Play className="w-4 h-4" />
                  Tag {total > 0 ? total.toLocaleString() : 0} Questions
                </button>
              </div>

              {/* Filter Panel (simplified) */}
              {showFilters && filterOptions && (
                <div className="mt-4 pt-4 border-t border-slate-200 grid grid-cols-4 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Disease State</label>
                    <select
                      value={filters.disease_states?.[0] || ''}
                      onChange={e => setFilters(prev => ({
                        ...prev,
                        disease_states: e.target.value ? [e.target.value] : undefined,
                      }))}
                      className="w-full px-3 py-2 border border-slate-200 rounded-lg"
                    >
                      <option value="">All</option>
                      {filterOptions.disease_states.map(opt => (
                        <option key={opt.value} value={opt.value}>
                          {opt.value} ({opt.count})
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Topic</label>
                    <select
                      value={filters.topics?.[0] || ''}
                      onChange={e => setFilters(prev => ({
                        ...prev,
                        topics: e.target.value ? [e.target.value] : undefined,
                      }))}
                      className="w-full px-3 py-2 border border-slate-200 rounded-lg"
                    >
                      <option value="">All</option>
                      {filterOptions.topics.map(opt => (
                        <option key={opt.value} value={opt.value}>
                          {opt.value} ({opt.count})
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Treatment</label>
                    <select
                      value={filters.treatments?.[0] || ''}
                      onChange={e => setFilters(prev => ({
                        ...prev,
                        treatments: e.target.value ? [e.target.value] : undefined,
                      }))}
                      className="w-full px-3 py-2 border border-slate-200 rounded-lg"
                    >
                      <option value="">All</option>
                      {filterOptions.treatments.slice(0, 50).map(opt => (
                        <option key={opt.value} value={opt.value}>
                          {opt.value} ({opt.count})
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="flex items-end">
                    <button
                      onClick={() => {
                        setFilters({})
                        setSearchQuery('')
                      }}
                      className="flex items-center gap-2 px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg"
                    >
                      <X className="w-4 h-4" />
                      Clear All
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Active Jobs Banner */}
            {activeJobs.length > 0 && (
              <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-4">
                <div className="flex items-center gap-3">
                  <div className="animate-spin">
                    <RefreshCw className="w-5 h-5 text-blue-600" />
                  </div>
                  <div>
                    <div className="font-medium text-blue-900">Tagging in progress</div>
                    <div className="text-sm text-blue-700">
                      {activeJobs[0].progress.completed} / {activeJobs[0].progress.total_questions} questions
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Results Count */}
            <div className="text-sm text-slate-600 mb-4">
              Showing <span className="font-semibold text-slate-900">{questions.length}</span> of{' '}
              <span className="font-semibold text-slate-900">{total.toLocaleString()}</span> questions
            </div>

            {/* Questions Table */}
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
              <table className="w-full">
                <thead className="bg-slate-50 border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm font-medium text-slate-600">ID</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-slate-600">Question</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-slate-600">Topic</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-slate-600">Disease State</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-slate-600">Treatment</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {loading ? (
                    <tr>
                      <td colSpan={5} className="px-4 py-8 text-center text-slate-500">
                        Loading...
                      </td>
                    </tr>
                  ) : questions.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-4 py-8 text-center text-slate-500">
                        No questions found
                      </td>
                    </tr>
                  ) : (
                    questions.map(q => (
                      <tr key={q.id} className="hover:bg-slate-50">
                        <td className="px-4 py-3 text-sm text-slate-600">#{q.id}</td>
                        <td className="px-4 py-3 text-sm text-slate-900 max-w-md truncate">
                          {q.question_stem?.substring(0, 100)}...
                        </td>
                        <td className="px-4 py-3">
                          {q.topic && (
                            <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded">
                              {q.topic}
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          {q.disease_state && (
                            <span className="px-2 py-1 bg-purple-100 text-purple-700 text-xs rounded">
                              {q.disease_state}
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          {q.treatment && (
                            <span className="px-2 py-1 bg-emerald-100 text-emerald-700 text-xs rounded">
                              {q.treatment}
                            </span>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="mt-4 flex items-center justify-center gap-2">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-4 py-2 bg-white border border-slate-200 rounded-lg disabled:opacity-50"
                >
                  Previous
                </button>
                <span className="px-4 py-2 text-slate-600">
                  Page {page} of {totalPages}
                </span>
                <button
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="px-4 py-2 bg-white border border-slate-200 rounded-lg disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            )}
          </>
        )}

        {activeTab === 'review' && <ReviewConflicts onReviewComplete={handleRefreshStats} />}

        {activeTab === 'reports' && (
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-12 text-center">
            <BarChart3 className="w-12 h-12 text-slate-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-slate-900 mb-2">Reports Coming Soon</h3>
            <p className="text-slate-600">
              Analytics and reporting features will be available in a future update.
            </p>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-primary-500 border-t border-primary-600 mt-auto">
        <div className="max-w-[1600px] mx-auto px-6 py-3">
          <div className="text-center text-sm text-white/70">
            CME Outcomes Dashboard V3 - 3-Model Voting System
          </div>
        </div>
      </footer>
    </div>
  )
}

export default App
