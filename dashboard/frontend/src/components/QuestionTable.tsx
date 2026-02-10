import { TrendingUp, TrendingDown, Minus, Info, X } from 'lucide-react'
import { useState } from 'react'
import type { Question, TagStatus } from '../types'

interface QuestionTableProps {
  questions: Question[]
  loading: boolean
  onSelect: (question: Question) => void
  selectedId?: number
  /** If true, show worst_case_agreement instead of tag_status (for Review page) */
  showWorstCaseStatus?: boolean
}

export function QuestionTable({ questions, loading, onSelect, selectedId, showWorstCaseStatus = false }: QuestionTableProps) {
  const [showStatusLegend, setShowStatusLegend] = useState(false)

  if (loading) {
    return (
      <div className="w-full bg-white rounded-2xl border border-slate-200/60 shadow-sm overflow-hidden">
        <div className="animate-pulse">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="p-4 border-b border-slate-100">
              <div className="h-4 bg-slate-200 rounded w-3/4 mb-3"></div>
              <div className="flex gap-2">
                <div className="h-6 bg-slate-100 rounded-full w-24"></div>
                <div className="h-6 bg-slate-100 rounded-full w-32"></div>
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (questions.length === 0) {
    return (
      <div className="w-full bg-white rounded-2xl border border-slate-200/60 shadow-sm p-12 text-center">
        <div className="text-slate-400 text-lg">No questions found</div>
        <p className="text-slate-500 text-sm mt-2">Try adjusting your search or filters</p>
      </div>
    )
  }

  // Helper to render knowledge gain badge
  const renderKnowledgeGain = (gain: number | null | undefined) => {
    if (gain == null) return null  // Catches both null and undefined
    
    const isPositive = gain > 0
    const isNeutral = gain === 0
    
    return (
      <div className={`flex items-center gap-1 text-sm ${
        isPositive ? 'text-emerald-600' : isNeutral ? 'text-slate-400' : 'text-red-500'
      }`}>
        {isPositive ? (
          <TrendingUp className="w-3.5 h-3.5" />
        ) : isNeutral ? (
          <Minus className="w-3.5 h-3.5" />
        ) : (
          <TrendingDown className="w-3.5 h-3.5" />
        )}
        <span className="font-medium">
          {isPositive ? '+' : ''}{gain.toFixed(1)}%
        </span>
      </div>
    )
  }

  // Helper to render tag status badge
  const renderTagStatus = (status: TagStatus | null) => {
    if (!status) return null

    const statusConfig: Record<TagStatus, { label: string; colors: string }> = {
      verified: { label: 'Verified', colors: 'bg-emerald-100 text-emerald-700' },
      unanimous: { label: 'Unanimous', colors: 'bg-emerald-50 text-emerald-600' },
      majority: { label: 'Majority', colors: 'bg-amber-100 text-amber-700' },
      conflict: { label: 'Conflict', colors: 'bg-red-100 text-red-700' },
    }

    const config = statusConfig[status]
    return (
      <span className={`px-2 py-0.5 rounded text-xs font-medium ${config.colors}`}>
        {config.label}
      </span>
    )
  }

  // Helper to render QCore grade badge
  const renderQCoreGrade = (score: number | null, grade: string | null) => {
    if (score === null || grade === null) return <span className="text-slate-400 text-xs">—</span>

    const gradeConfig: Record<string, string> = {
      'A': 'bg-emerald-100 text-emerald-700',
      'B': 'bg-blue-100 text-blue-700',
      'C': 'bg-amber-100 text-amber-700',
      'D': 'bg-red-100 text-red-700',
      'F': 'bg-red-200 text-red-800',
    }

    return (
      <div className="flex items-center gap-1.5">
        <span className={`px-1.5 py-0.5 rounded text-xs font-semibold ${gradeConfig[grade] || 'bg-slate-100 text-slate-600'}`}>
          {grade}
        </span>
        <span className="text-xs text-slate-500">{score}</span>
      </div>
    )
  }

  // Tag Status Legend Modal
  const StatusLegendModal = () => (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowStatusLegend(false)}>
      <div className="bg-white rounded-xl shadow-xl p-6 max-w-md mx-4" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-slate-900">
            {showWorstCaseStatus ? 'Agreement Status Legend' : 'Tag Status Legend'}
          </h3>
          <button onClick={() => setShowStatusLegend(false)} className="p-1 hover:bg-slate-100 rounded">
            <X className="w-5 h-5 text-slate-500" />
          </button>
        </div>
        <p className="text-sm text-slate-600 mb-4">
          {showWorstCaseStatus
            ? 'Status shows the worst-case agreement across ALL tag fields. If any field has a conflict, the overall status is conflict.'
            : 'Status is computed from 8 core tags: topic, disease_state, disease_stage, disease_type, treatment_line, treatment, biomarker, and trial.'
          }
        </p>
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <span className="px-2 py-0.5 rounded text-xs font-medium bg-emerald-100 text-emerald-700 w-20 text-center">Verified</span>
            <span className="text-sm text-slate-600">Human-reviewed and confirmed</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="px-2 py-0.5 rounded text-xs font-medium bg-emerald-50 text-emerald-600 w-20 text-center">Unanimous</span>
            <span className="text-sm text-slate-600">
              {showWorstCaseStatus
                ? 'All 3 models agreed on ALL tag fields'
                : 'All 3 models agreed on all 8 core tags'
              }
            </span>
          </div>
          <div className="flex items-center gap-3">
            <span className="px-2 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-700 w-20 text-center">Majority</span>
            <span className="text-sm text-slate-600">
              {showWorstCaseStatus
                ? '2/3 models agreed on some fields (no conflicts)'
                : '2/3 models agreed (no conflicts)'
              }
            </span>
          </div>
          <div className="flex items-center gap-3">
            <span className="px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-700 w-20 text-center">Conflict</span>
            <span className="text-sm text-slate-600">
              {showWorstCaseStatus
                ? 'Models disagreed on 1+ fields (3-way split)'
                : 'Models disagreed on 1+ core tags'
              }
            </span>
          </div>
        </div>
      </div>
    </div>
  )

  return (
    <div className="bg-white rounded-2xl border border-slate-200/60 shadow-sm overflow-hidden">
      {/* Status Legend Modal */}
      {showStatusLegend && <StatusLegendModal />}

      {/* Table Header */}
      <div className="hidden md:grid grid-cols-12 gap-2 px-4 py-3 bg-slate-50 border-b border-slate-200 text-xs font-semibold text-slate-500 uppercase tracking-wide">
        <div className="col-span-4">Question</div>
        <div className="col-span-2">Disease State</div>
        <div className="col-span-2">Topic</div>
        <div className="col-span-1">QCore</div>
        <div className="col-span-1 flex items-center gap-1">
          <button
            onClick={(e) => { e.stopPropagation(); setShowStatusLegend(true); }}
            className="p-0.5 hover:bg-slate-200 rounded transition-colors"
            title={showWorstCaseStatus ? "View agreement status legend" : "View tag status legend"}
          >
            <Info className="w-3.5 h-3.5 text-slate-400" />
          </button>
          <span>{showWorstCaseStatus ? 'Agree' : 'Status'}</span>
        </div>
        <div className="col-span-2">Performance</div>
      </div>

      {/* Table Body */}
      <div className="divide-y divide-slate-100">
        {questions.map((question, index) => (
          <button
            key={question.id}
            onClick={() => onSelect(question)}
            className={`w-full text-left p-4 md:px-4 md:py-3 hover:bg-slate-50 transition-colors animate-fade-in ${
              selectedId === question.id ? 'bg-primary-50 hover:bg-primary-50' : ''
            }`}
            style={{ opacity: 0, animationDelay: `${index * 0.03}s` }}
          >
            <div className="md:grid md:grid-cols-12 md:gap-2 md:items-center">
              {/* Question Stem */}
              <div className="col-span-4">
                <p className="text-slate-900 line-clamp-2 text-sm leading-relaxed">
                  {question.question_stem}
                </p>
              </div>

              {/* Disease State */}
              <div className="col-span-2 mt-2 md:mt-0">
                {question.disease_state ? (
                  <span className="px-2 py-0.5 bg-violet-50 text-violet-700 rounded text-xs font-medium">
                    {question.disease_state}
                  </span>
                ) : (
                  <span className="text-slate-400 text-xs">—</span>
                )}
              </div>

              {/* Topic */}
              <div className="col-span-2 mt-2 md:mt-0">
                {question.topic ? (
                  <span className="px-2 py-0.5 bg-primary-50 text-primary-700 rounded text-xs font-medium">
                    {question.topic}
                  </span>
                ) : (
                  <span className="text-slate-400 text-xs">—</span>
                )}
              </div>

              {/* QCore Score */}
              <div className="col-span-1 mt-2 md:mt-0">
                {renderQCoreGrade(question.qcore_score, question.qcore_grade)}
              </div>

              {/* Tag Status / Agreement Status */}
              <div className="col-span-1 mt-2 md:mt-0">
                {renderTagStatus(showWorstCaseStatus ? question.worst_case_agreement : question.tag_status)}
              </div>

              {/* Performance */}
              <div className="col-span-2 mt-3 md:mt-0">
                {question.pre_score != null || question.post_score != null ? (
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-2 text-xs">
                      {question.pre_score != null && (
                        <span className="text-slate-500">
                          Pre: <span className="font-medium text-slate-700">{question.pre_score?.toFixed(1)}%</span>
                        </span>
                      )}
                      {question.post_score != null && (
                        <span className="text-slate-500">
                          Post: <span className="font-medium text-slate-700">{question.post_score?.toFixed(1)}%</span>
                        </span>
                      )}
                    </div>
                    {renderKnowledgeGain(question.knowledge_gain)}
                  </div>
                ) : (
                  <span className="text-slate-400 text-xs">No data</span>
                )}
              </div>

            </div>

            {/* Treatment tag on mobile */}
            {question.treatment && (
              <div className="mt-2 md:hidden">
                <span className="px-2 py-1 bg-amber-50 text-amber-700 rounded text-xs">
                  {question.treatment}
                </span>
              </div>
            )}
          </button>
        ))}
      </div>
    </div>
  )
}

