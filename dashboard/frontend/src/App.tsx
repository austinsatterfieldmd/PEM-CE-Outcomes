import { useState, useEffect } from 'react'
import { Search, Filter, ChevronDown, X, BarChart3, Database, ClipboardCheck, Download, ArrowUpDown, SlidersHorizontal, Zap } from 'lucide-react'
import { QuestionTable } from './components/QuestionTable'
import { FilterPanel } from './components/FilterPanel'
import { ColumnPickerModal } from './components/ColumnPickerModal'
import { QuestionDetail } from './components/QuestionDetail'
import { QuestionReviewDetail } from './components/QuestionReviewDetail'
import { StatsCards } from './components/StatsCards'
import ReportBuilder from './components/ReportBuilder'
import ReviewTab from './components/ReviewTab'
import QSuiteTab from './components/QSuiteTab'
import { UserMenu } from './components/AuthProvider'
import { ExportEditsButton } from './components/ExportEditsButton'
import { searchQuestions, getFilterOptions, getDynamicFilterOptions, getStats, exportQuestions, exportQuestionsFull } from './services/api'
import type { Question, FilterOptions, SearchFilters, Stats } from './types'
import { loadUserDefinedValues } from './config/userDefinedValues'
import { checkVercelMode } from './services/localEdits'
import perLogoWhite from './assets/per-logo-white.png'

type TabView = 'explorer' | 'reports' | 'review' | 'qsuite'

// Helper to get URL search params
const getUrlQuestionId = (): number | null => {
  const params = new URLSearchParams(window.location.search)
  const questionId = params.get('question')
  return questionId ? parseInt(questionId, 10) : null
}

// Helper to get initial tab from URL hash
const getInitialTab = (): TabView => {
  // If there's a question parameter, default to explorer
  if (getUrlQuestionId()) {
    return 'explorer'
  }
  const hash = window.location.hash.replace('#', '')
  if (hash === 'reports' || hash === 'explorer' || hash === 'review' || hash === 'qsuite') {
    return hash as TabView
  }
  // Support legacy hash routes by mapping to review
  if (hash === 'needs-review' || hash === 'dedup-review' || hash === 'proposals') {
    return 'review'
  }
  return 'explorer'
}

function App() {
  // Tab state - initialize from URL hash
  const [activeTab, setActiveTab] = useState<TabView>(getInitialTab)

  // Update URL hash when tab changes
  useEffect(() => {
    window.location.hash = activeTab
  }, [activeTab])
  
  // State
  const [questions, setQuestions] = useState<Question[]>([])
  const [selectedQuestion, setSelectedQuestion] = useState<Question | null>(null)
  const [filterOptions, setFilterOptions] = useState<FilterOptions | null>(null)
  const [dynamicFilterOptions, setDynamicFilterOptions] = useState<FilterOptions | null>(null)
  const [stats, setStats] = useState<Stats | null>(null)
  const [loading, setLoading] = useState(true)
  const [showFilters, setShowFilters] = useState(true)
  const [showColumnPicker, setShowColumnPicker] = useState(false)
  const [selectedAdvancedCategories, setSelectedAdvancedCategories] = useState<string[]>(() => {
    try {
      const saved = localStorage.getItem('selectedAdvancedCategories')
      return saved ? JSON.parse(saved) : []
    } catch { return [] }
  })
  
  // Search & filter state
  const [searchQuery, setSearchQuery] = useState('')
  const [filters, setFilters] = useState<SearchFilters>({})
  const [reviewFlagFilter, setReviewFlagFilter] = useState<string | null>(null)
  const [reviewSourceFileFilter, setReviewSourceFileFilter] = useState<string | null>(null)
  const [reviewSearchQuery, setReviewSearchQuery] = useState('')
  const [reviewSortBy, setReviewSortBy] = useState('flagged_at')
  const [reviewSortDesc, setReviewSortDesc] = useState(true)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [total, setTotal] = useState(0)
  const [sortBy, setSortBy] = useState('knowledge_gain')
  const [sortDesc, setSortDesc] = useState(true)
  const [refreshTrigger, setRefreshTrigger] = useState(0)

  // Activity date range filter state
  const [activityDateRange, setActivityDateRange] = useState<{
    startMonth: number | null
    startYear: number | null
    endMonth: number | null
    endYear: number | null
  }>({ startMonth: null, startYear: null, endMonth: null, endYear: null })
  
  // Load initial data (including user-defined values for dropdowns)
  useEffect(() => {
    // Load user-defined values early so they're available for dropdowns
    loadUserDefinedValues()

    // Check Vercel mode early so isVercelMode() returns correct value
    checkVercelMode()

    Promise.all([getFilterOptions(), getStats()])
      .then(([options, statsData]) => {
        setFilterOptions(options)
        setDynamicFilterOptions(options) // Initially same as full options
        setStats(statsData)
      })
      .catch(console.error)
  }, [])

  // Handle URL question parameter - open question detail if ?question=ID is present
  useEffect(() => {
    const urlQuestionId = getUrlQuestionId()
    if (urlQuestionId) {
      // Create a minimal Question object to open the detail panel
      const minimalQuestion: Question = {
        id: urlQuestionId,
        source_id: null,
        question_stem: '',
        topic: null,
        topic_confidence: null,
        disease_state: null,
        disease_state_confidence: null,
        treatment: null,
        pre_score: null,
        post_score: null,
        knowledge_gain: null,
        sample_size: null,
        activity_count: 0,
        tag_status: null,
        worst_case_agreement: null,
        qcore_score: null,
        qcore_grade: null,
      }
      setSelectedQuestion(minimalQuestion)
      setActiveTab('explorer')
      // Clear the URL parameter to avoid reopening on refresh
      window.history.replaceState({}, '', window.location.pathname + window.location.hash)
    }
  }, [])
  
  // Update dynamic filter options when filters change
  useEffect(() => {
    const hasActiveFilters = Object.values(filters).some(v => v && (Array.isArray(v) ? v.length > 0 : true))
    
    if (hasActiveFilters) {
      getDynamicFilterOptions(filters)
        .then(setDynamicFilterOptions)
        .catch(console.error)
    } else {
      // No filters active, use full options
      setDynamicFilterOptions(filterOptions)
    }
  }, [filters, filterOptions])
  
  // Search when filters change
  useEffect(() => {
    const doSearch = async () => {
      setLoading(true)
      try {
        // If on review tab, add needs_review filter (for Questions Needing Review sub-tab)
        const searchParams = activeTab === 'review'
          ? {
              needs_review: true,
              query: reviewSearchQuery || undefined,
              review_flag_filter: reviewFlagFilter || undefined,
              source_files: reviewSourceFileFilter ? [reviewSourceFileFilter] : undefined,
              page,
              page_size: 20,
              sort_by: reviewSortBy,
              sort_desc: reviewSortDesc,
            }
          : {
              query: searchQuery || undefined,
              ...filters,
              // Activity date range filter
              activity_start_after: activityDateRange.startMonth && activityDateRange.startYear
                ? `${activityDateRange.startYear}-${String(activityDateRange.startMonth).padStart(2, '0')}`
                : undefined,
              activity_start_before: activityDateRange.endMonth && activityDateRange.endYear
                ? `${activityDateRange.endYear}-${String(activityDateRange.endMonth).padStart(2, '0')}`
                : undefined,
              page,
              page_size: 20,
              sort_by: sortBy,
              sort_desc: sortDesc,
            }

        const result = await searchQuestions(searchParams)
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
  }, [searchQuery, filters, page, sortBy, sortDesc, refreshTrigger, activeTab, reviewFlagFilter, reviewSourceFileFilter, reviewSearchQuery, reviewSortBy, reviewSortDesc, activityDateRange])
  
  // Clear all filters
  const clearFilters = () => {
    setFilters({})
    setSearchQuery('')
    setPage(1)
  }

  // Export to Excel
  const handleExport = async () => {
    try {
      setLoading(true)
      console.log('Starting export with filters:', filters)

      // Use the export endpoint which returns all matching questions with full data including activities
      const result = await exportQuestions(filters)

      console.log('Total questions fetched:', result.total)

      if (result.questions.length === 0) {
        alert('No questions to export.')
        return
      }

      // Convert to CSV format with all tags and activities
      const headers = [
        'ID',
        'Question',
        'Correct Answer',
        'Incorrect Answers',
        'Topic',
        'Disease State',
        'Disease Type',
        'Disease Stage',
        'Treatment',
        'Treatment Line',
        'Biomarker',
        'Trial',
        'Pre-Test Score',
        'Post-Test Score',
        'Knowledge Gain',
        'Sample Size',
        'Activities'
      ]

      const csvRows = [
        headers.join(','),
        ...result.questions.map(q => [
          q.id,
          `"${(q.question_stem || '').replace(/"/g, '""')}"`,
          `"${(q.correct_answer || '').replace(/"/g, '""')}"`,
          `"${(q.incorrect_answers || '').replace(/"/g, '""')}"`,
          `"${(q.topic || '').replace(/"/g, '""')}"`,
          `"${(q.disease_state || '').replace(/"/g, '""')}"`,
          `"${(q.disease_type || '').replace(/"/g, '""')}"`,
          `"${(q.disease_stage || '').replace(/"/g, '""')}"`,
          `"${(q.treatment || '').replace(/"/g, '""')}"`,
          `"${(q.treatment_line || '').replace(/"/g, '""')}"`,
          `"${(q.biomarker || '').replace(/"/g, '""')}"`,
          `"${(q.trial || '').replace(/"/g, '""')}"`,
          q.pre_score !== null ? q.pre_score.toFixed(1) + '%' : '',
          q.post_score !== null ? q.post_score.toFixed(1) + '%' : '',
          q.knowledge_gain !== null ? (q.knowledge_gain > 0 ? '+' : '') + q.knowledge_gain.toFixed(1) + '%' : '',
          q.sample_size || '',
          `"${(q.activities || '').replace(/"/g, '""')}"`
        ].join(','))
      ]

      console.log('Generated CSV rows:', csvRows.length)

      // Create and download the file
      const csvContent = csvRows.join('\n')
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
      const link = document.createElement('a')
      const url = URL.createObjectURL(blob)
      link.setAttribute('href', url)
      link.setAttribute('download', `questions_export_${new Date().toISOString().split('T')[0]}.csv`)
      link.style.visibility = 'hidden'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)

      console.log('Export successful')
    } catch (error) {
      console.error('Export failed:', error)
      const errorMessage = error instanceof Error ? error.message : 'Unknown error'
      alert(`Failed to export questions: ${errorMessage}`)
    } finally {
      setLoading(false)
    }
  }

  // Export Review Queue questions with all 70 fields
  const handleReviewExport = async () => {
    try {
      setLoading(true)
      const exportFilters = {
        needs_review: true,
        source_files: reviewSourceFileFilter ? [reviewSourceFileFilter] : undefined,
      }
      console.log('Starting review export with filters:', exportFilters)

      const result = await exportQuestionsFull(exportFilters)

      console.log('Total questions fetched:', result.total)

      if (result.questions.length === 0) {
        alert('No questions to export.')
        return
      }

      // CSV headers - all 70 fields + metadata
      const headers = [
        'ID', 'Source File', 'Question', 'Correct Answer', 'Incorrect Answers',
        // Core Classification
        'Topic', 'Disease State', 'Disease Type 1', 'Disease Type 2', 'Disease Stage', 'Treatment Line',
        // Multi-value Fields
        'Treatment 1', 'Treatment 2', 'Treatment 3', 'Treatment 4', 'Treatment 5',
        'Biomarker 1', 'Biomarker 2', 'Biomarker 3', 'Biomarker 4', 'Biomarker 5',
        'Trial 1', 'Trial 2', 'Trial 3', 'Trial 4', 'Trial 5',
        // Patient Characteristics
        'Treatment Eligibility', 'Age Group', 'Organ Dysfunction', 'Fitness Status', 'Disease Specific Factor',
        'Comorbidity 1', 'Comorbidity 2', 'Comorbidity 3',
        // Treatment Metadata
        'Drug Class 1', 'Drug Class 2', 'Drug Class 3',
        'Drug Target 1', 'Drug Target 2', 'Drug Target 3',
        'Prior Therapy 1', 'Prior Therapy 2', 'Prior Therapy 3', 'Resistance Mechanism',
        // Clinical Context
        'Metastatic Site 1', 'Metastatic Site 2', 'Metastatic Site 3',
        'Symptom 1', 'Symptom 2', 'Symptom 3', 'Performance Status',
        // Safety/Toxicity
        'Toxicity Type 1', 'Toxicity Type 2', 'Toxicity Type 3', 'Toxicity Type 4', 'Toxicity Type 5',
        'Toxicity Organ', 'Toxicity Grade',
        // Efficacy/Outcomes
        'Efficacy Endpoint 1', 'Efficacy Endpoint 2', 'Efficacy Endpoint 3', 'Outcome Context', 'Clinical Benefit',
        // Evidence/Guidelines
        'Guideline Source 1', 'Guideline Source 2', 'Evidence Type',
        // Question Format/Quality
        'CME Outcome Level', 'Data Response Type', 'Stem Type', 'Lead-in Type', 'Answer Format',
        'Answer Length Pattern', 'Distractor Homogeneity',
        'Flaw: Absolute Terms', 'Flaw: Grammatical Cue', 'Flaw: Implausible Distractor',
        'Flaw: Clang Association', 'Flaw: Convergence Vulnerability', 'Flaw: Double Negative',
        // Computed
        'Answer Option Count', 'Correct Answer Position',
        // Performance
        'Pre-Test Score', 'Post-Test Score', 'Knowledge Gain', 'Sample Size', 'Activities'
      ]

      const escapeCSV = (val: string | number | boolean | null | undefined) => {
        if (val === null || val === undefined) return ''
        if (typeof val === 'boolean') return val ? 'TRUE' : 'FALSE'
        const str = String(val)
        return `"${str.replace(/"/g, '""')}"`
      }

      const csvRows = [
        headers.join(','),
        ...result.questions.map(q => [
          q.id, escapeCSV(q.source_file), escapeCSV(q.question_stem), escapeCSV(q.correct_answer), escapeCSV(q.incorrect_answers),
          // Core
          escapeCSV(q.topic), escapeCSV(q.disease_state), escapeCSV(q.disease_type_1), escapeCSV(q.disease_type_2), escapeCSV(q.disease_stage), escapeCSV(q.treatment_line),
          // Multi-value
          escapeCSV(q.treatment_1), escapeCSV(q.treatment_2), escapeCSV(q.treatment_3), escapeCSV(q.treatment_4), escapeCSV(q.treatment_5),
          escapeCSV(q.biomarker_1), escapeCSV(q.biomarker_2), escapeCSV(q.biomarker_3), escapeCSV(q.biomarker_4), escapeCSV(q.biomarker_5),
          escapeCSV(q.trial_1), escapeCSV(q.trial_2), escapeCSV(q.trial_3), escapeCSV(q.trial_4), escapeCSV(q.trial_5),
          // Patient Characteristics
          escapeCSV(q.treatment_eligibility), escapeCSV(q.age_group), escapeCSV(q.organ_dysfunction), escapeCSV(q.fitness_status), escapeCSV(q.disease_specific_factor),
          escapeCSV(q.comorbidity_1), escapeCSV(q.comorbidity_2), escapeCSV(q.comorbidity_3),
          // Treatment Metadata
          escapeCSV(q.drug_class_1), escapeCSV(q.drug_class_2), escapeCSV(q.drug_class_3),
          escapeCSV(q.drug_target_1), escapeCSV(q.drug_target_2), escapeCSV(q.drug_target_3),
          escapeCSV(q.prior_therapy_1), escapeCSV(q.prior_therapy_2), escapeCSV(q.prior_therapy_3), escapeCSV(q.resistance_mechanism),
          // Clinical Context
          escapeCSV(q.metastatic_site_1), escapeCSV(q.metastatic_site_2), escapeCSV(q.metastatic_site_3),
          escapeCSV(q.symptom_1), escapeCSV(q.symptom_2), escapeCSV(q.symptom_3), escapeCSV(q.performance_status),
          // Safety/Toxicity
          escapeCSV(q.toxicity_type_1), escapeCSV(q.toxicity_type_2), escapeCSV(q.toxicity_type_3), escapeCSV(q.toxicity_type_4), escapeCSV(q.toxicity_type_5),
          escapeCSV(q.toxicity_organ), escapeCSV(q.toxicity_grade),
          // Efficacy/Outcomes
          escapeCSV(q.efficacy_endpoint_1), escapeCSV(q.efficacy_endpoint_2), escapeCSV(q.efficacy_endpoint_3), escapeCSV(q.outcome_context), escapeCSV(q.clinical_benefit),
          // Evidence/Guidelines
          escapeCSV(q.guideline_source_1), escapeCSV(q.guideline_source_2), escapeCSV(q.evidence_type),
          // Question Format/Quality
          escapeCSV(q.cme_outcome_level), escapeCSV(q.data_response_type), escapeCSV(q.stem_type), escapeCSV(q.lead_in_type), escapeCSV(q.answer_format),
          escapeCSV(q.answer_length_pattern), escapeCSV(q.distractor_homogeneity),
          escapeCSV(q.flaw_absolute_terms), escapeCSV(q.flaw_grammatical_cue), escapeCSV(q.flaw_implausible_distractor),
          escapeCSV(q.flaw_clang_association), escapeCSV(q.flaw_convergence_vulnerability), escapeCSV(q.flaw_double_negative),
          // Computed
          q.answer_option_count || '', escapeCSV(q.correct_answer_position),
          // Performance
          q.pre_score !== null && q.pre_score !== undefined ? q.pre_score.toFixed(1) + '%' : '',
          q.post_score !== null && q.post_score !== undefined ? q.post_score.toFixed(1) + '%' : '',
          q.knowledge_gain !== null && q.knowledge_gain !== undefined ? (q.knowledge_gain > 0 ? '+' : '') + q.knowledge_gain.toFixed(1) + '%' : '',
          q.sample_size || '',
          escapeCSV(q.activities)
        ].join(','))
      ]

      // Create filename with source file if filtered
      const filename = reviewSourceFileFilter
        ? `review_export_${reviewSourceFileFilter.replace(/[^a-zA-Z0-9]/g, '_')}_${new Date().toISOString().split('T')[0]}.csv`
        : `review_export_all_${new Date().toISOString().split('T')[0]}.csv`

      const csvContent = csvRows.join('\n')
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
      const link = document.createElement('a')
      const url = URL.createObjectURL(blob)
      link.setAttribute('href', url)
      link.setAttribute('download', filename)
      link.style.visibility = 'hidden'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)

      console.log('Review export successful')
    } catch (error) {
      console.error('Review export failed:', error)
      const errorMessage = error instanceof Error ? error.message : 'Unknown error'
      alert(`Failed to export review questions: ${errorMessage}`)
    } finally {
      setLoading(false)
    }
  }

  // Count active filters
  const activeFilterCount = Object.values(filters).filter(v => v && (Array.isArray(v) ? v.length > 0 : true)).length
  
  return (
    <div className={`min-h-screen flex flex-col ${activeTab === 'reports' ? 'bg-slate-900' : 'bg-gradient-to-br from-slate-50 via-blue-50/30 to-slate-100'}`}>
      {/* Header - PER Blue Background */}
      <header className="bg-primary-500 border-b border-primary-600 sticky top-0 z-40">
        <div className="max-w-[1600px] mx-auto px-6 py-3">
          <div className="flex items-center justify-between">
            {/* Logo and Title */}
            <div className="flex items-center gap-4">
              <img
                src={perLogoWhite}
                alt="PER Logo"
                className="h-10 w-auto"
              />
              <div className="border-l border-white/30 pl-4">
                <h1 className="text-lg font-bold text-white">
                  Outcomes Questions Database
                </h1>
                <p className="text-sm text-white/70">
                  Search and analyze outcomes questions
                </p>
              </div>
            </div>

            {/* Tab Navigation - shifted right with more spacing */}
            <div className="flex items-center gap-2 ml-8">
              <button
                onClick={() => setActiveTab('explorer')}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all ${
                  activeTab === 'explorer'
                    ? 'bg-white text-primary-500 shadow-lg'
                    : 'text-white/80 hover:text-white hover:bg-white/10'
                }`}
              >
                <Database className="w-4 h-4" />
                Question Explorer
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
              </button>
              <button
                onClick={() => setActiveTab('qsuite')}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all ${
                  activeTab === 'qsuite'
                    ? 'bg-white text-primary-500 shadow-lg'
                    : 'text-white/80 hover:text-white hover:bg-white/10'
                }`}
              >
                <Zap className="w-4 h-4" />
                Q-Suite
              </button>
            </div>

            {/* Export Edits (Vercel Mode) + User Menu */}
            <div className="flex items-center gap-4">
              <ExportEditsButton />
              <UserMenu />
            </div>
          </div>
        </div>
      </header>
      
      {/* Main Content */}
      <main className="w-full max-w-[1600px] mx-auto px-6 py-6 flex-1">
        {activeTab === 'explorer' ? (
          <>
            {/* Stats Cards */}
            {stats && (
              <StatsCards
                stats={stats}
                onNeedsReviewClick={() => setActiveTab('review')}
              />
            )}
            
            {/* Search Bar & Filters */}
            <div className="mt-6 w-full bg-white rounded-2xl shadow-sm shadow-slate-200/50 border border-slate-200/60 p-4">
              <div className="flex flex-col md:flex-row gap-4">
                {/* Search Input */}
                <div className="flex-1 relative">
                  <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                  <input
                    type="text"
                    placeholder="Search questions by keyword..."
                    value={searchQuery}
                    onChange={(e) => {
                      setSearchQuery(e.target.value)
                      setPage(1)
                    }}
                    className="w-full pl-12 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all"
                  />
                </div>

                {/* Advanced Filters Toggle */}
                <button
                  onClick={() => setShowColumnPicker(true)}
                  className={`flex items-center gap-2 px-4 py-3 rounded-xl font-medium transition-all ${
                    selectedAdvancedCategories.length > 0
                      ? 'bg-violet-600 text-white shadow-lg shadow-violet-600/20'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  <SlidersHorizontal className="w-4 h-4" />
                  Advanced Filters
                  {selectedAdvancedCategories.length > 0 && (
                    <span className="ml-1 px-2 py-0.5 bg-white/20 rounded-full text-xs">
                      {selectedAdvancedCategories.length}
                    </span>
                  )}
                </button>

                {/* Filter Toggle */}
                <button
                  onClick={() => setShowFilters(!showFilters)}
                  className={`flex items-center gap-2 px-5 py-3 rounded-xl font-medium transition-all ${
                    showFilters || activeFilterCount > 0
                      ? 'bg-primary-500 text-white shadow-lg shadow-primary-500/20'
                      : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                  }`}
                >
                  <Filter className="w-4 h-4" />
                  Filters
                  {activeFilterCount > 0 && (
                    <span className="ml-1 px-2 py-0.5 bg-white/20 rounded-full text-xs">
                      {activeFilterCount}
                    </span>
                  )}
                  <ChevronDown className={`w-4 h-4 transition-transform ${showFilters ? 'rotate-180' : ''}`} />
                </button>
                
                {/* Clear Filters */}
                {(activeFilterCount > 0 || searchQuery) && (
                  <button
                    onClick={clearFilters}
                    className="flex items-center gap-2 px-4 py-3 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-xl transition-all"
                  >
                    <X className="w-4 h-4" />
                    Clear
                  </button>
                )}
              </div>
              
              {/* Filter Panel */}
              {showFilters && filterOptions && (
                <FilterPanel
                  options={dynamicFilterOptions || filterOptions}
                  filters={filters}
                  onChange={(newFilters) => {
                    setFilters(newFilters)
                    setPage(1)
                  }}
                  advancedCategories={selectedAdvancedCategories}
                />
              )}
            </div>
            
            {/* Results Count, Legend, and Export */}
            <div className="mt-4 flex items-center justify-between text-sm text-slate-600">
              <div>
                Showing <span className="font-semibold text-slate-900">{questions.length}</span> of{' '}
                <span className="font-semibold text-slate-900">{total.toLocaleString()}</span> questions
              </div>

              {/* Activity Date Range Filter */}
              <div className="flex items-center gap-1.5 text-xs">
                <span className="font-medium text-slate-700">Activity Date:</span>
                {/* From date group */}
                <div className="flex items-center gap-1 px-2 py-0.5 bg-slate-50 rounded border border-slate-200">
                  <span className="text-slate-500 font-medium">From</span>
                  <select
                    value={activityDateRange.startMonth ?? ''}
                    onChange={(e) => {
                      setActivityDateRange(prev => ({ ...prev, startMonth: e.target.value ? parseInt(e.target.value) : null }))
                      setPage(1)
                    }}
                    className="px-1.5 py-0.5 bg-white border border-slate-200 rounded text-slate-700 focus:outline-none focus:ring-1 focus:ring-primary-500/20 text-xs"
                  >
                    <option value="">Mon</option>
                    {['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'].map((m, i) => (
                      <option key={i + 1} value={i + 1}>{m}</option>
                    ))}
                  </select>
                  <select
                    value={activityDateRange.startYear ?? ''}
                    onChange={(e) => {
                      setActivityDateRange(prev => ({ ...prev, startYear: e.target.value ? parseInt(e.target.value) : null }))
                      setPage(1)
                    }}
                    className="px-1.5 py-0.5 bg-white border border-slate-200 rounded text-slate-700 focus:outline-none focus:ring-1 focus:ring-primary-500/20 text-xs"
                  >
                    <option value="">Year</option>
                    {[2022, 2023, 2024, 2025, 2026].map(y => (
                      <option key={y} value={y}>{y}</option>
                    ))}
                  </select>
                </div>
                {/* To date group */}
                <div className="flex items-center gap-1 px-2 py-0.5 bg-slate-50 rounded border border-slate-200">
                  <span className="text-slate-500 font-medium">To</span>
                  <select
                    value={activityDateRange.endMonth ?? ''}
                    onChange={(e) => {
                      setActivityDateRange(prev => ({ ...prev, endMonth: e.target.value ? parseInt(e.target.value) : null }))
                      setPage(1)
                    }}
                    className="px-1.5 py-0.5 bg-white border border-slate-200 rounded text-slate-700 focus:outline-none focus:ring-1 focus:ring-primary-500/20 text-xs"
                  >
                    <option value="">Mon</option>
                    {['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'].map((m, i) => (
                      <option key={i + 1} value={i + 1}>{m}</option>
                    ))}
                  </select>
                  <select
                    value={activityDateRange.endYear ?? ''}
                    onChange={(e) => {
                      setActivityDateRange(prev => ({ ...prev, endYear: e.target.value ? parseInt(e.target.value) : null }))
                      setPage(1)
                    }}
                    className="px-1.5 py-0.5 bg-white border border-slate-200 rounded text-slate-700 focus:outline-none focus:ring-1 focus:ring-primary-500/20 text-xs"
                  >
                    <option value="">Year</option>
                    {[2022, 2023, 2024, 2025, 2026].map(y => (
                      <option key={y} value={y}>{y}</option>
                    ))}
                  </select>
                </div>
                {(activityDateRange.startMonth || activityDateRange.startYear || activityDateRange.endMonth || activityDateRange.endYear) && (
                  <button
                    onClick={() => {
                      setActivityDateRange({ startMonth: null, startYear: null, endMonth: null, endYear: null })
                      setPage(1)
                    }}
                    className="p-1 hover:bg-slate-200 rounded transition-colors"
                    title="Clear date filter"
                  >
                    <X className="w-3.5 h-3.5 text-slate-400" />
                  </button>
                )}
              </div>

              {/* Export and Sort Options */}
              <div className="flex items-center gap-3">
                {/* Export Button */}
                <button
                  onClick={handleExport}
                  disabled={loading || total === 0}
                  className="flex items-center gap-2 px-4 py-2 bg-emerald-500 hover:bg-emerald-600 disabled:bg-slate-300 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors text-sm shadow-sm"
                  title={`Export ${total.toLocaleString()} filtered questions to CSV`}
                >
                  <Download className="w-4 h-4" />
                  Export ({total.toLocaleString()})
                </button>

                <div className="w-px h-6 bg-slate-300"></div>

                <span>Sort by:</span>
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  className="px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-slate-700 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
                >
                  <option value="knowledge_gain">Performance Change</option>
                  <option value="pre_score">Pre-Test Score</option>
                  <option value="qcore_score">QCore Score</option>
                  <option value="sample_size">Sample Size</option>
                  <option value="disease_state">Disease State</option>
                  <option value="topic">Topic</option>
                </select>
                <button
                  onClick={() => setSortDesc(!sortDesc)}
                  className={`p-1.5 rounded-lg transition-colors ${sortDesc ? 'bg-primary-100 text-primary-700' : 'hover:bg-slate-100'}`}
                  title={sortDesc ? 'Sorted descending' : 'Sorted ascending'}
                >
                  <ArrowUpDown className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Results Table */}
            <div className="mt-4">
              <QuestionTable
                questions={questions}
                loading={loading}
                onSelect={setSelectedQuestion}
                selectedId={selectedQuestion?.id}
              />
            </div>
            
            {/* Pagination */}
            {totalPages > 1 && (
              <div className="mt-4 flex items-center justify-center gap-2">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-4 py-2 bg-white border border-slate-200 rounded-lg text-slate-700 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-50 transition-colors"
                >
                  Previous
                </button>
                <span className="px-4 py-2 text-slate-600">
                  Page {page} of {totalPages}
                </span>
                <button
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="px-4 py-2 bg-white border border-slate-200 rounded-lg text-slate-700 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-50 transition-colors"
                >
                  Next
                </button>
              </div>
            )}
          </>
        ) : activeTab === 'reports' ? (
          /* Reports Tab */
          <ReportBuilder />
        ) : activeTab === 'qsuite' ? (
          /* Q-Suite Tab */
          <QSuiteTab />
        ) : (
          /* Review Tab with sub-tabs */
          <ReviewTab
            questionsContent={
              <>
                {/* Search Bar and Sort for Review */}
                <div className="bg-white rounded-xl shadow-sm border border-slate-200/60 p-4">
                  <div className="flex flex-col md:flex-row gap-4">
                    {/* Search Input */}
                    <div className="flex-1 relative">
                      <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                      <input
                        type="text"
                        placeholder="Search review questions by keyword..."
                        value={reviewSearchQuery}
                        onChange={(e) => {
                          setReviewSearchQuery(e.target.value)
                          setPage(1)
                        }}
                        className="w-full pl-12 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-red-500/20 focus:border-red-500 transition-all"
                      />
                    </div>

                    {/* Sort Options */}
                    <div className="flex items-center gap-3">
                      <span className="text-sm text-slate-600">Sort by:</span>
                      <select
                        value={reviewSortBy}
                        onChange={(e) => setReviewSortBy(e.target.value)}
                        className="px-3 py-2 bg-white border border-slate-200 rounded-lg text-slate-700 focus:outline-none focus:ring-2 focus:ring-red-500/20"
                      >
                        <option value="flagged_at">Date Added to Queue</option>
                        <option value="id">Question ID</option>
                        <option value="disease_state">Disease State</option>
                        <option value="topic">Topic</option>
                        <option value="confidence">Confidence</option>
                      </select>
                      <button
                        onClick={() => setReviewSortDesc(!reviewSortDesc)}
                        className={`p-2 rounded-lg transition-colors ${reviewSortDesc ? 'bg-red-100 text-red-700' : 'hover:bg-slate-100'}`}
                        title={reviewSortDesc ? 'Sorted descending (newest first)' : 'Sorted ascending (oldest first)'}
                      >
                        <ArrowUpDown className="w-4 h-4" />
                      </button>
                    </div>

                    {/* Clear Search */}
                    {reviewSearchQuery && (
                      <button
                        onClick={() => {
                          setReviewSearchQuery('')
                          setPage(1)
                        }}
                        className="flex items-center gap-2 px-4 py-2 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-xl transition-all"
                      >
                        <X className="w-4 h-4" />
                        Clear
                      </button>
                    )}
                  </div>
                </div>

                {/* Flag Type Filter */}
                <div className="bg-white rounded-xl shadow-sm border border-slate-200/60 p-4 mt-4">
                  <div className="flex items-center gap-3 flex-wrap">
                    <span className="text-sm font-medium text-slate-700">Filter by reason:</span>
                    <div className="flex gap-2 flex-wrap">
                      <button
                        onClick={() => setReviewFlagFilter(null)}
                        className={`px-3 py-1.5 text-sm rounded-lg transition-all ${
                          reviewFlagFilter === null
                            ? 'bg-blue-500 text-white shadow-sm'
                            : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                        }`}
                      >
                        All
                      </button>
                      {/* LLM Voting Disagreements */}
                      <button
                        onClick={() => setReviewFlagFilter('conflict_in_fields')}
                        className={`px-3 py-1.5 text-sm rounded-lg transition-all ${
                          reviewFlagFilter === 'conflict_in_fields'
                            ? 'bg-red-500 text-white shadow-sm'
                            : 'bg-red-50 text-red-700 hover:bg-red-100'
                        }`}
                        title="3-way split between models on tag fields"
                      >
                        LLM Conflict
                      </button>
                      <button
                        onClick={() => setReviewFlagFilter('majority_in_fields')}
                        className={`px-3 py-1.5 text-sm rounded-lg transition-all ${
                          reviewFlagFilter === 'majority_in_fields'
                            ? 'bg-orange-500 text-white shadow-sm'
                            : 'bg-orange-50 text-orange-700 hover:bg-orange-100'
                        }`}
                        title="2/1 split between models on tag fields"
                      >
                        LLM Majority
                      </button>
                      {/* User-flagged reasons */}
                      <button
                        onClick={() => setReviewFlagFilter('May not be an oncology question')}
                        className={`px-3 py-1.5 text-sm rounded-lg transition-all ${
                          reviewFlagFilter === 'May not be an oncology question'
                            ? 'bg-purple-500 text-white shadow-sm'
                            : 'bg-purple-50 text-purple-700 hover:bg-purple-100'
                        }`}
                      >
                        Not Oncology
                      </button>
                      <button
                        onClick={() => setReviewFlagFilter('Potential tag errors')}
                        className={`px-3 py-1.5 text-sm rounded-lg transition-all ${
                          reviewFlagFilter === 'Potential tag errors'
                            ? 'bg-amber-500 text-white shadow-sm'
                            : 'bg-amber-50 text-amber-700 hover:bg-amber-100'
                        }`}
                      >
                        Tag Errors
                      </button>
                      <button
                        onClick={() => setReviewFlagFilter('Potential question errors')}
                        className={`px-3 py-1.5 text-sm rounded-lg transition-all ${
                          reviewFlagFilter === 'Potential question errors'
                            ? 'bg-slate-500 text-white shadow-sm'
                            : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                        }`}
                      >
                        Question Errors
                      </button>
                      {/* API/Tagging Errors */}
                      <button
                        onClick={() => setReviewFlagFilter('api_error')}
                        className={`px-3 py-1.5 text-sm rounded-lg transition-all ${
                          reviewFlagFilter === 'api_error'
                            ? 'bg-rose-600 text-white shadow-sm'
                            : 'bg-rose-50 text-rose-700 hover:bg-rose-100'
                        }`}
                        title="Questions that failed during API tagging - need manual tagging"
                      >
                        API Error
                      </button>
                    </div>

                    {/* Source File Filter - for batch workflow */}
                    {filterOptions?.source_files && filterOptions.source_files.length > 0 && (
                      <>
                        <div className="w-px h-6 bg-slate-300 mx-2"></div>
                        <span className="text-sm font-medium text-slate-700">Batch:</span>
                        <select
                          value={reviewSourceFileFilter || ''}
                          onChange={(e) => {
                            setReviewSourceFileFilter(e.target.value || null)
                            setPage(1)
                          }}
                          className="px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 max-w-[200px]"
                        >
                          <option value="">All batches</option>
                          {filterOptions.source_files.map(sf => (
                            <option key={sf.value} value={sf.value}>
                              {sf.value} ({sf.count})
                            </option>
                          ))}
                        </select>
                      </>
                    )}

                    <span className="text-sm text-slate-500 ml-auto">
                      {total} question{total !== 1 ? 's' : ''}
                    </span>

                    {/* Export Button */}
                    <button
                      onClick={handleReviewExport}
                      disabled={loading || total === 0}
                      className="flex items-center gap-2 px-4 py-1.5 bg-emerald-500 hover:bg-emerald-600 disabled:bg-slate-300 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors text-sm shadow-sm"
                      title={`Export ${total.toLocaleString()} questions with all 70 tag fields`}
                    >
                      <Download className="w-4 h-4" />
                      Export
                    </button>
                  </div>
                </div>

                <div className="bg-white rounded-2xl shadow-sm border border-slate-200/60 p-6 mt-4">
                  <QuestionTable
                    questions={questions}
                    onSelect={setSelectedQuestion}
                    selectedId={selectedQuestion?.id}
                    loading={loading}
                    showWorstCaseStatus={true}
                  />
                </div>

                {/* Pagination */}
                {totalPages > 1 && (
                  <div className="flex items-center justify-center gap-2 mt-4">
                    <button
                      onClick={() => setPage(p => Math.max(1, p - 1))}
                      disabled={page === 1}
                      className="px-4 py-2 bg-white border border-slate-200 rounded-lg text-slate-700 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-50 transition-colors"
                    >
                      Previous
                    </button>
                    <span className="px-4 py-2 text-slate-600">
                      Page {page} of {totalPages}
                    </span>
                    <button
                      onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                      disabled={page === totalPages}
                      className="px-4 py-2 bg-white border border-slate-200 rounded-lg text-slate-700 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-50 transition-colors"
                    >
                      Next
                    </button>
                  </div>
                )}
              </>
            }
          />
        )}
      </main>
      
      {/* Advanced Filters Modal */}
      <ColumnPickerModal
        isOpen={showColumnPicker}
        onClose={() => setShowColumnPicker(false)}
        selectedCategories={selectedAdvancedCategories}
        onApply={(categories) => {
          setSelectedAdvancedCategories(categories)
          localStorage.setItem('selectedAdvancedCategories', JSON.stringify(categories))
        }}
      />

      {/* Question Detail Slide-over */}
      {selectedQuestion && activeTab === 'review' ? (
        <QuestionReviewDetail
          questionId={selectedQuestion.id}
          onClose={() => setSelectedQuestion(null)}
          onReviewComplete={() => {
            // Refresh the search results and stats when review is complete
            setSelectedQuestion(null)
            setRefreshTrigger(t => t + 1)
          }}
        />
      ) : selectedQuestion ? (
        <QuestionDetail
          questionId={selectedQuestion.id}
          onClose={() => setSelectedQuestion(null)}
          onTagsUpdated={() => {
            // Refresh the search results when tags are updated
            setRefreshTrigger(t => t + 1)
          }}
        />
      ) : null}

      {/* Footer Banner */}
      <footer className="bg-primary-500 border-t border-primary-600 mt-auto">
        <div className="max-w-[1600px] mx-auto px-6 py-4">
          <div className="flex items-center justify-center gap-2 text-sm text-white">
            <span>259 Prospect Plains Rd, Bldg H</span>
            <span className="text-accent-400">•</span>
            <span>Monroe, NJ 08831</span>
            <span className="text-accent-400">•</span>
            <a href="mailto:info@gotoper.com" className="text-accent-400 hover:text-accent-300 transition-colors">
              info@gotoper.com
            </a>
            <span className="text-accent-400">•</span>
            <span>Copyright© {new Date().getFullYear()} Physicians' Education Resource®, LLC.</span>
            <span className="text-accent-400">•</span>
            <span>All rights reserved.</span>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default App

