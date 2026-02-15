import { useState, useEffect, useCallback, useRef } from 'react'
import {
  BarChart3,
  Filter,
  ChevronDown,
  ChevronRight,
  RefreshCw,
  AlertCircle,
  Calendar,
  X,
  Users,
  Download,
  FileSpreadsheet,
  ArrowLeft,
  ArrowRight,
  Check,
  Settings,
  Play
} from 'lucide-react'
import PerformanceBarChart from './PerformanceBarChart'
import ActivityManager from './ActivityManager'
import {
  aggregateByTag,
  aggregateByTagWithSegments,
  getFilterOptions,
  getDynamicFilterOptions,
  getSegmentOptions,
  exportQuestionsForReport
} from '../services/apiRouter'
import type {
  TagGroupBy,
  AudienceSegment,
  ReportFilters,
  FilterOptions,
  SegmentOptions,
  AggregatedMetric
} from '../types'

// Wizard step types
type WizardStep = 'filters' | 'chart-type' | 'configure' | 'result'
type ChartFormat = 'single' | 'stacked' | 'grouped'

// Audience segment configuration
const AUDIENCE_SEGMENTS: { value: AudienceSegment; label: string; color: string }[] = [
  { value: 'overall', label: 'All Learners', color: '#6366f1' },
  { value: 'medical_oncologist', label: 'Med/Heme Oncs', color: '#8b5cf6' },
  { value: 'surgical_oncologist', label: 'Surg Oncs', color: '#ec4899' },
  { value: 'radiation_oncologist', label: 'Rad Oncs', color: '#f59e0b' },
  { value: 'app', label: 'APPs', color: '#10b981' },
  { value: 'community', label: 'Community', color: '#3b82f6' },
  { value: 'academic', label: 'Academic', color: '#ef4444' },
]

// Group by options organized by category
const GROUP_BY_OPTIONS: { value: TagGroupBy; label: string; group: string }[] = [
  // Core
  { value: 'topic', label: 'Topic', group: 'Core' },
  { value: 'disease_state', label: 'Disease State', group: 'Core' },
  { value: 'disease_stage', label: 'Disease Stage', group: 'Core' },
  { value: 'disease_type', label: 'Disease Type', group: 'Core' },
  { value: 'treatment_line', label: 'Treatment Line', group: 'Core' },
  { value: 'treatment', label: 'Treatment', group: 'Core' },
  { value: 'biomarker', label: 'Biomarker', group: 'Core' },
  { value: 'trial', label: 'Trial', group: 'Core' },
  // Treatment Metadata
  { value: 'drug_class', label: 'Drug Class', group: 'Treatment' },
  { value: 'drug_target', label: 'Drug Target', group: 'Treatment' },
  // Clinical Context
  { value: 'metastatic_site', label: 'Metastatic Site', group: 'Clinical' },
  { value: 'performance_status', label: 'Performance Status', group: 'Clinical' },
  // Safety
  { value: 'toxicity_type', label: 'Toxicity Type', group: 'Safety' },
  { value: 'toxicity_organ', label: 'Toxicity Organ', group: 'Safety' },
  // Efficacy
  { value: 'efficacy_endpoint', label: 'Efficacy Endpoint', group: 'Efficacy' },
  { value: 'clinical_benefit', label: 'Clinical Benefit', group: 'Efficacy' },
  // Evidence
  { value: 'guideline_source', label: 'Guideline Source', group: 'Evidence' },
  { value: 'evidence_type', label: 'Evidence Type', group: 'Evidence' },
  // Question Quality
  { value: 'cme_outcome_level', label: 'CME Outcome Level', group: 'Quality' },
]

// Chart format options
const CHART_FORMAT_OPTIONS: { value: ChartFormat; label: string; description: string }[] = [
  { value: 'single', label: 'Single Chart', description: 'Pre/Post bars for one audience per category' },
  { value: 'stacked', label: 'Stacked Charts', description: 'Separate chart for each audience, stacked vertically' },
  { value: 'grouped', label: 'Grouped Comparison', description: 'All audiences side-by-side per category' },
]

// Step indicator component
function StepIndicator({ currentStep, steps }: { currentStep: WizardStep; steps: { key: WizardStep; label: string }[] }) {
  const currentIndex = steps.findIndex(s => s.key === currentStep)

  return (
    <div className="flex items-center justify-center mb-8">
      {steps.map((step, index) => (
        <div key={step.key} className="flex items-center">
          <div className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-medium ${
            index < currentIndex
              ? 'bg-green-500 text-white'
              : index === currentIndex
              ? 'bg-indigo-500 text-white'
              : 'bg-slate-700 text-slate-400'
          }`}>
            {index < currentIndex ? <Check size={16} /> : index + 1}
          </div>
          <span className={`ml-2 text-sm ${
            index === currentIndex ? 'text-white font-medium' : 'text-slate-400'
          }`}>
            {step.label}
          </span>
          {index < steps.length - 1 && (
            <ChevronRight size={20} className="mx-4 text-slate-600" />
          )}
        </div>
      ))}
    </div>
  )
}

export default function ReportBuilder() {
  // Wizard state
  const [step, setStep] = useState<WizardStep>('filters')
  const [showActivityManager, setShowActivityManager] = useState(false)

  // Filter state
  const [filters, setFilters] = useState<ReportFilters>({})
  const [filterOptions, setFilterOptions] = useState<FilterOptions | null>(null)
  const [dynamicFilterOptions, setDynamicFilterOptions] = useState<FilterOptions | null>(null)
  const [segmentOptions, setSegmentOptions] = useState<SegmentOptions | null>(null)

  // Chart configuration state
  const [groupBy, setGroupBy] = useState<TagGroupBy>('topic')
  const [selectedAudiences, setSelectedAudiences] = useState<AudienceSegment[]>(['overall'])
  const [chartFormat, setChartFormat] = useState<ChartFormat>('single')
  const [chartLabels, setChartLabels] = useState({
    title: '',
    xAxis: '',
    yAxis: 'Score (%)'
  })

  // Generated report state
  const [generatedData, setGeneratedData] = useState<AggregatedMetric[] | null>(null)
  const [questionsCount, setQuestionsCount] = useState<number>(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Chart ref for export
  const chartRef = useRef<HTMLDivElement>(null)

  // Wizard steps
  const wizardSteps: { key: WizardStep; label: string }[] = [
    { key: 'filters', label: 'Select Filters' },
    { key: 'chart-type', label: 'Chart Type' },
    { key: 'configure', label: 'Configure' },
    { key: 'result', label: 'Result' },
  ]

  // Load filter options on mount
  useEffect(() => {
    async function loadOptions() {
      try {
        const [tagOpts, segOpts] = await Promise.all([
          getFilterOptions(),
          getSegmentOptions()
        ])
        setFilterOptions(tagOpts)
        setDynamicFilterOptions(tagOpts) // Initially same as full options
        setSegmentOptions(segOpts)
      } catch (err) {
        console.error('Failed to load options:', err)
      }
    }
    loadOptions()
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

  // Update default labels when groupBy changes
  useEffect(() => {
    const groupLabel = GROUP_BY_OPTIONS.find(g => g.value === groupBy)?.label || 'Category'
    setChartLabels(prev => ({
      ...prev,
      title: prev.title || `Performance by ${groupLabel}`,
      xAxis: prev.xAxis || groupLabel
    }))
  }, [groupBy])

  // Auto-switch away from 'single' when multiple audiences selected
  useEffect(() => {
    if (selectedAudiences.length > 1 && chartFormat === 'single') {
      setChartFormat('grouped')
    }
  }, [selectedAudiences, chartFormat])

  // Toggle filter selection
  const toggleFilter = (category: keyof ReportFilters, value: string) => {
    setFilters(prev => {
      const current = prev[category] as string[] | undefined
      if (current?.includes(value)) {
        const updated = current.filter(v => v !== value)
        return { ...prev, [category]: updated.length ? updated : undefined }
      } else {
        return { ...prev, [category]: [...(current || []), value] }
      }
    })
  }

  // Toggle audience selection
  const toggleAudience = (segment: AudienceSegment) => {
    setSelectedAudiences(prev => {
      if (prev.includes(segment)) {
        if (prev.length === 1) return prev // Don't allow empty selection
        return prev.filter(s => s !== segment)
      } else {
        return [...prev, segment]
      }
    })
  }

  // Clear all filters
  const clearFilters = () => setFilters({})

  // Count active filters
  const activeFilterCount = Object.values(filters).filter(v => v && v.length > 0).length

  // Generate report
  const generateReport = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      let data: AggregatedMetric[]

      if (selectedAudiences.length === 1) {
        // Single audience - use simple aggregation
        const response = await aggregateByTag(groupBy, filters)
        data = response.data
      } else {
        // Multiple audiences - use segment comparison
        const response = await aggregateByTagWithSegments(groupBy, selectedAudiences, filters)
        data = response.data
      }

      setGeneratedData(data)

      // Calculate total questions
      const totalQuestions = data.reduce((sum, d) => sum + d.question_count, 0)
      // For segment comparison, divide by number of segments to avoid counting same question multiple times
      setQuestionsCount(selectedAudiences.length > 1 ? Math.round(totalQuestions / selectedAudiences.length) : totalQuestions)

      setStep('result')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate report')
    } finally {
      setLoading(false)
    }
  }, [groupBy, selectedAudiences, filters])

  // Export chart as PNG
  const exportChartAsPNG = async () => {
    if (!chartRef.current) return

    try {
      // Dynamic import for html2canvas
      const html2canvas = (await import('html2canvas')).default

      const canvas = await html2canvas(chartRef.current, {
        backgroundColor: '#FFFFFF',
        scale: 2,
        logging: false
      })

      const link = document.createElement('a')
      link.download = `${chartLabels.title || 'chart'}.png`
      link.href = canvas.toDataURL('image/png')
      link.click()
    } catch (err) {
      console.error('Failed to export chart:', err)
      setError('Failed to export chart. Please try again.')
    }
  }

  // Export questions to Excel
  const exportQuestionsToExcel = async () => {
    try {
      // Dynamic import for xlsx
      const XLSX = await import('xlsx')

      // Fetch full question details from API
      const { questions } = await exportQuestionsForReport(filters)

      const exportData = questions.map(q => ({
        'ID': q.id,
        'Question': q.question_stem,
        'Topic': q.topic || '',
        'Disease State': q.disease_state || '',
        'Disease Type': q.disease_type || '',
        'Disease Stage': q.disease_stage || '',
        'Treatment': q.treatment || '',
        'Treatment Line': q.treatment_line || '',
        'Biomarker': q.biomarker || '',
        'Trial': q.trial || '',
        'Pre Score': q.pre_score,
        'Post Score': q.post_score,
        'Knowledge Gain': q.knowledge_gain,
        'Sample Size': q.sample_size,
        'Activities': q.activities || ''
      }))

      const worksheet = XLSX.utils.json_to_sheet(exportData)
      const workbook = XLSX.utils.book_new()
      XLSX.utils.book_append_sheet(workbook, worksheet, 'Questions')
      XLSX.writeFile(workbook, `report-questions-${new Date().toISOString().split('T')[0]}.xlsx`)
    } catch (err) {
      console.error('Failed to export to Excel:', err)
      setError('Failed to export to Excel. Please try again.')
    }
  }

  // Start new report
  const startNewReport = () => {
    setStep('filters')
    setGeneratedData(null)
    setChartLabels({ title: '', xAxis: '', yAxis: 'Score (%)' })
  }

  // Navigation
  const goToNextStep = () => {
    const currentIndex = wizardSteps.findIndex(s => s.key === step)
    if (currentIndex < wizardSteps.length - 1) {
      if (step === 'configure') {
        generateReport()
      } else {
        setStep(wizardSteps[currentIndex + 1].key)
      }
    }
  }

  const goToPreviousStep = () => {
    const currentIndex = wizardSteps.findIndex(s => s.key === step)
    if (currentIndex > 0) {
      setStep(wizardSteps[currentIndex - 1].key)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Report Generator</h2>
          <p className="text-slate-400 mt-1">
            Create grant-ready charts with customizable filters and export options
          </p>
        </div>
        <button
          onClick={() => setShowActivityManager(!showActivityManager)}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
            showActivityManager
              ? 'bg-indigo-500 text-white'
              : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
          }`}
        >
          <Calendar size={18} />
          <span>Manage Activities</span>
        </button>
      </div>

      {/* Activity Manager Panel */}
      {showActivityManager && (
        <ActivityManager onClose={() => setShowActivityManager(false)} />
      )}

      {/* Step Indicator */}
      <StepIndicator currentStep={step} steps={wizardSteps} />

      {/* Error Display */}
      {error && (
        <div className="bg-red-900/20 border border-red-800 rounded-lg p-4 flex items-center gap-3">
          <AlertCircle className="text-red-400" size={20} />
          <p className="text-red-300">{error}</p>
          <button onClick={() => setError(null)} className="ml-auto text-red-400 hover:text-red-300">
            <X size={18} />
          </button>
        </div>
      )}

      {/* Step Content */}
      <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6">
        {/* Step 1: Filters */}
        {step === 'filters' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                <Filter size={20} />
                Select Filters
              </h3>
              {activeFilterCount > 0 && (
                <button
                  onClick={clearFilters}
                  className="flex items-center gap-1 text-sm text-slate-400 hover:text-white"
                >
                  <X size={14} />
                  Clear all ({activeFilterCount})
                </button>
              )}
            </div>

            <p className="text-slate-400 text-sm">
              Choose filters to narrow down the questions included in your report. Leave empty for all questions.
            </p>

            {dynamicFilterOptions && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <FilterSection
                  title="Disease State"
                  options={dynamicFilterOptions.disease_states || []}
                  selected={filters.disease_states || []}
                  onToggle={(v) => toggleFilter('disease_states', v)}
                />
                <FilterSection
                  title="Disease Type"
                  options={dynamicFilterOptions.disease_types || []}
                  selected={filters.disease_types || []}
                  onToggle={(v) => toggleFilter('disease_types', v)}
                />
                <FilterSection
                  title="Disease Stage"
                  options={dynamicFilterOptions.disease_stages || []}
                  selected={filters.disease_stages || []}
                  onToggle={(v) => toggleFilter('disease_stages', v)}
                />
                <FilterSection
                  title="Topic"
                  options={dynamicFilterOptions.topics || []}
                  selected={filters.topics || []}
                  onToggle={(v) => toggleFilter('topics', v)}
                />
                <FilterSection
                  title="Treatment"
                  options={dynamicFilterOptions.treatments || []}
                  selected={filters.treatments || []}
                  onToggle={(v) => toggleFilter('treatments', v)}
                />
                <FilterSection
                  title="Treatment Line"
                  options={dynamicFilterOptions.treatment_lines || []}
                  selected={filters.treatment_lines || []}
                  onToggle={(v) => toggleFilter('treatment_lines', v)}
                />
                <FilterSection
                  title="Biomarker"
                  options={dynamicFilterOptions.biomarkers || []}
                  selected={filters.biomarkers || []}
                  onToggle={(v) => toggleFilter('biomarkers', v)}
                />
                <FilterSection
                  title="Trial"
                  options={dynamicFilterOptions.trials || []}
                  selected={filters.trials || []}
                  onToggle={(v) => toggleFilter('trials', v)}
                />
                <FilterSection
                  title="Activity"
                  options={dynamicFilterOptions.activities || []}
                  selected={filters.activities || []}
                  onToggle={(v) => toggleFilter('activities', v)}
                />
              </div>
            )}
          </div>
        )}

        {/* Step 2: Chart Type */}
        {step === 'chart-type' && (
          <div className="space-y-8">
            <div>
              <h3 className="text-lg font-semibold text-white flex items-center gap-2 mb-4">
                <BarChart3 size={20} />
                Group By
              </h3>
              <p className="text-slate-400 text-sm mb-4">
                Choose what to display on the X-axis of your chart.
              </p>
              <div className="space-y-3">
                {Array.from(new Set(GROUP_BY_OPTIONS.map(o => o.group))).map(group => (
                  <div key={group}>
                    <span className="text-xs text-slate-500 uppercase tracking-wider font-medium">{group}</span>
                    <div className="flex flex-wrap gap-2 mt-1">
                      {GROUP_BY_OPTIONS.filter(o => o.group === group).map(option => (
                        <button
                          key={option.value}
                          onClick={() => setGroupBy(option.value)}
                          className={`px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                            groupBy === option.value
                              ? 'bg-indigo-500 text-white'
                              : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                          }`}
                        >
                          {option.label}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <h3 className="text-lg font-semibold text-white flex items-center gap-2 mb-4">
                <Users size={20} />
                Audience Segments
              </h3>
              <p className="text-slate-400 text-sm mb-4">
                Select one or more audience segments to include in the report.
              </p>
              <div className="flex flex-wrap gap-2">
                {AUDIENCE_SEGMENTS.map(segment => {
                  const isSelected = selectedAudiences.includes(segment.value)
                  const count = segmentOptions?.segments.find(s => s.segment === segment.value)?.count
                  return (
                    <button
                      key={segment.value}
                      onClick={() => toggleAudience(segment.value)}
                      className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                        isSelected
                          ? 'text-white shadow-lg'
                          : 'bg-slate-700/50 text-slate-400 hover:bg-slate-700 hover:text-slate-300'
                      }`}
                      style={isSelected ? { backgroundColor: segment.color } : undefined}
                    >
                      <span
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: segment.color }}
                      />
                      {segment.label}
                      {count !== undefined && (
                        <span className={`text-xs ${isSelected ? 'text-white/70' : 'text-slate-500'}`}>
                          ({count})
                        </span>
                      )}
                    </button>
                  )
                })}
              </div>
            </div>

            <div>
              <h3 className="text-lg font-semibold text-white flex items-center gap-2 mb-4">
                <Settings size={20} />
                Chart Format
              </h3>
              <p className="text-slate-400 text-sm mb-4">
                {selectedAudiences.length > 1
                  ? 'Choose how to display multiple audiences.'
                  : 'Select multiple audiences above to enable comparison formats.'}
              </p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {CHART_FORMAT_OPTIONS.map(option => {
                  // Single chart is only valid for single audience
                  // Stacked and grouped are only valid for multiple audiences
                  const isDisabled =
                    (option.value === 'single' && selectedAudiences.length > 1) ||
                    (option.value !== 'single' && selectedAudiences.length <= 1)
                  return (
                    <button
                      key={option.value}
                      onClick={() => !isDisabled && setChartFormat(option.value)}
                      disabled={isDisabled}
                      className={`p-4 rounded-lg text-left transition-all ${
                        isDisabled
                          ? 'bg-slate-800/30 border-2 border-transparent cursor-not-allowed opacity-50'
                          : chartFormat === option.value
                            ? 'bg-indigo-500/20 border-2 border-indigo-500'
                            : 'bg-slate-700/50 border-2 border-transparent hover:border-slate-600'
                        }`}
                      >
                        <div className={`font-medium mb-1 ${isDisabled ? 'text-slate-500' : 'text-white'}`}>
                          {option.label}
                          {isDisabled && option.value === 'single' && (
                            <span className="ml-2 text-xs">(single audience only)</span>
                          )}
                          {isDisabled && option.value !== 'single' && (
                            <span className="ml-2 text-xs">(multiple audiences required)</span>
                          )}
                        </div>
                        <div className={`text-sm ${isDisabled ? 'text-slate-600' : 'text-slate-400'}`}>{option.description}</div>
                      </button>
                    )
                  })}
                </div>
              </div>
          </div>
        )}

        {/* Step 3: Configure */}
        {step === 'configure' && (
          <div className="space-y-6">
            <h3 className="text-lg font-semibold text-white flex items-center gap-2">
              <Settings size={20} />
              Configure Chart Labels
            </h3>
            <p className="text-slate-400 text-sm">
              Customize the labels for your chart. These will appear in the exported image.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Chart Title
                </label>
                <input
                  type="text"
                  value={chartLabels.title}
                  onChange={(e) => setChartLabels(prev => ({ ...prev, title: e.target.value }))}
                  placeholder="Performance by Topic"
                  className="w-full px-4 py-3 bg-slate-900 border border-slate-600 rounded-lg text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  X-Axis Label
                </label>
                <input
                  type="text"
                  value={chartLabels.xAxis}
                  onChange={(e) => setChartLabels(prev => ({ ...prev, xAxis: e.target.value }))}
                  placeholder="Topic"
                  className="w-full px-4 py-3 bg-slate-900 border border-slate-600 rounded-lg text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Y-Axis Label
                </label>
                <input
                  type="text"
                  value={chartLabels.yAxis}
                  onChange={(e) => setChartLabels(prev => ({ ...prev, yAxis: e.target.value }))}
                  placeholder="Score (%)"
                  className="w-full px-4 py-3 bg-slate-900 border border-slate-600 rounded-lg text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                />
              </div>
            </div>

            {/* Summary */}
            <div className="bg-slate-900/50 rounded-lg p-4">
              <h4 className="text-sm font-medium text-slate-300 mb-3">Report Summary</h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <span className="text-slate-500">Group By:</span>
                  <span className="ml-2 text-white">
                    {GROUP_BY_OPTIONS.find(g => g.value === groupBy)?.label}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500">Audiences:</span>
                  <span className="ml-2 text-white">{selectedAudiences.length}</span>
                </div>
                <div>
                  <span className="text-slate-500">Format:</span>
                  <span className="ml-2 text-white">
                    {selectedAudiences.length > 1
                      ? CHART_FORMAT_OPTIONS.find(f => f.value === chartFormat)?.label
                      : 'Single Chart'}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500">Filters:</span>
                  <span className="ml-2 text-white">{activeFilterCount || 'None'}</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Step 4: Result */}
        {step === 'result' && generatedData && (
          <div className="space-y-6">
            {/* Export buttons */}
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-white">Generated Report</h3>
              <div className="flex items-center gap-3">
                <button
                  onClick={exportChartAsPNG}
                  className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-500 text-white rounded-lg font-medium transition-colors"
                >
                  <Download size={18} />
                  Save as PNG
                </button>
                <button
                  onClick={exportQuestionsToExcel}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-medium transition-colors"
                >
                  <FileSpreadsheet size={18} />
                  Export to Excel
                </button>
                <button
                  onClick={startNewReport}
                  className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg font-medium transition-colors"
                >
                  <RefreshCw size={18} />
                  New Report
                </button>
              </div>
            </div>

            {/* Chart container with white background for export */}
            <div
              ref={chartRef}
              className="bg-white rounded-lg p-6"
              style={{ minHeight: chartFormat === 'stacked' && selectedAudiences.length > 1 ? selectedAudiences.length * 350 : (chartFormat === 'grouped' && selectedAudiences.length > 1 ? 400 + (selectedAudiences.length * 40) : 450) }}
            >
              <PerformanceBarChart
                data={generatedData}
                title={chartLabels.title}
                xAxisLabel={chartLabels.xAxis}
                yAxisLabel={chartLabels.yAxis}
                height={chartFormat === 'stacked' && selectedAudiences.length > 1 ? 300 : (chartFormat === 'grouped' && selectedAudiences.length > 1 ? 380 + (selectedAudiences.length * 35) : 400)}
                segments={selectedAudiences.length > 1 ? selectedAudiences : undefined}
                chartFormat={selectedAudiences.length > 1 ? chartFormat : 'single'}
                showN={true}
                whiteBackground={true}
              />
            </div>

            {/* Stats */}
            <div className="flex items-center gap-6 text-sm text-slate-400">
              <span>Questions in report: <strong className="text-white">{questionsCount}</strong></span>
              <span>Data points: <strong className="text-white">{generatedData.length}</strong></span>
            </div>
          </div>
        )}

        {/* Loading overlay */}
        {loading && (
          <div className="flex items-center justify-center py-12">
            <RefreshCw size={32} className="animate-spin text-indigo-400" />
            <span className="ml-3 text-slate-400 text-lg">Generating report...</span>
          </div>
        )}
      </div>

      {/* Navigation buttons */}
      {step !== 'result' && (
        <div className="flex items-center justify-between">
          <button
            onClick={goToPreviousStep}
            disabled={step === 'filters'}
            className={`flex items-center gap-2 px-6 py-3 rounded-lg font-medium transition-colors ${
              step === 'filters'
                ? 'bg-slate-800 text-slate-600 cursor-not-allowed'
                : 'bg-slate-700 text-white hover:bg-slate-600'
            }`}
          >
            <ArrowLeft size={18} />
            Back
          </button>

          <button
            onClick={goToNextStep}
            disabled={loading}
            className="flex items-center gap-2 px-6 py-3 bg-indigo-500 hover:bg-indigo-400 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
          >
            {step === 'configure' ? (
              <>
                <Play size={18} />
                Generate Report
              </>
            ) : (
              <>
                Next
                <ArrowRight size={18} />
              </>
            )}
          </button>
        </div>
      )}
    </div>
  )
}

// Filter Section Component
interface FilterSectionProps {
  title: string
  options: { value: string; count: number }[]
  selected: string[]
  onToggle: (value: string) => void
}

function FilterSection({ title, options, selected, onToggle }: FilterSectionProps) {
  const [expanded, setExpanded] = useState(false)
  const [search, setSearch] = useState('')

  const filteredOptions = options.filter(opt =>
    opt.value.toLowerCase().includes(search.toLowerCase())
  )
  const displayOptions = expanded ? filteredOptions : filteredOptions.slice(0, 5)

  if (options.length === 0) {
    return (
      <div className="bg-slate-900/50 rounded-lg p-3">
        <h4 className="text-sm font-medium text-slate-400 mb-2">{title}</h4>
        <p className="text-xs text-slate-500">No options available</p>
      </div>
    )
  }

  return (
    <div className="bg-slate-900/50 rounded-lg p-3">
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-sm font-medium text-slate-300">{title}</h4>
        {selected.length > 0 && (
          <span className="text-xs bg-indigo-500/20 text-indigo-300 px-2 py-0.5 rounded">
            {selected.length} selected
          </span>
        )}
      </div>

      {options.length > 5 && (
        <input
          type="text"
          placeholder={`Search ${title.toLowerCase()}...`}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full mb-2 px-2 py-1.5 text-xs bg-slate-800 border border-slate-600 rounded text-white placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
        />
      )}

      <div className="space-y-1 max-h-40 overflow-y-auto">
        {displayOptions.map(opt => (
          <label
            key={opt.value}
            className="flex items-center gap-2 text-sm cursor-pointer hover:bg-slate-700/50 rounded px-2 py-1"
          >
            <input
              type="checkbox"
              checked={selected.includes(opt.value)}
              onChange={() => onToggle(opt.value)}
              className="rounded border-slate-600 bg-slate-700 text-indigo-500 focus:ring-indigo-500"
            />
            <span className="text-slate-300 truncate flex-1" title={opt.value}>
              {opt.value}
            </span>
            {opt.count > 0 && (
              <span className="text-xs text-slate-500">{opt.count}</span>
            )}
          </label>
        ))}
      </div>

      {filteredOptions.length > 5 && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-xs text-indigo-400 hover:text-indigo-300 mt-2 flex items-center gap-1"
        >
          <ChevronDown size={14} className={expanded ? 'rotate-180' : ''} />
          {expanded ? 'Show less' : `Show ${filteredOptions.length - 5} more`}
        </button>
      )}
    </div>
  )
}
