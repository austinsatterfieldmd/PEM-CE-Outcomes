/**
 * ReviewConflicts Page Component
 *
 * Main page for reviewing questions where models disagreed.
 * Allows human reviewers to see all 3 model votes and submit corrections.
 */

import { useState, useEffect } from 'react'
import { AlertTriangle, Check, X, ChevronLeft, ChevronRight, Save, RotateCcw, Search } from 'lucide-react'
import { VoteComparison } from './VoteComparison'
import {
  getReviewQueue,
  getReviewItem,
  submitCorrection,
  batchApproveUnanimous,
} from '../api/client'
import type { ReviewQuestion, Tags, VotingResult, Question } from '../types'

interface ReviewConflictsProps {
  onReviewComplete?: () => void
}

export function ReviewConflicts({ onReviewComplete }: ReviewConflictsProps) {
  // Queue state
  const [queue, setQueue] = useState<ReviewQuestion[]>([])
  const [queueStats, setQueueStats] = useState({ conflicts: 0, majority_votes: 0, total_pending: 0 })
  const [loading, setLoading] = useState(true)
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)

  // Current item state
  const [selectedQuestion, setSelectedQuestion] = useState<ReviewQuestion | null>(null)
  const [questionDetail, setQuestionDetail] = useState<Question | null>(null)
  const [votingResult, setVotingResult] = useState<VotingResult | null>(null)
  const [editableTags, setEditableTags] = useState<Tags>({})
  const [reviewerNotes, setReviewerNotes] = useState('')
  const [category, setCategory] = useState('')
  const [saving, setSaving] = useState(false)

  // Filters
  const [filterLevel, setFilterLevel] = useState<'all' | 'conflict' | 'majority'>('all')

  // Load queue
  useEffect(() => {
    loadQueue()
  }, [currentPage, filterLevel])

  const loadQueue = async () => {
    setLoading(true)
    try {
      const result = await getReviewQueue({
        agreement_level: filterLevel === 'all' ? undefined : filterLevel,
        page: currentPage,
        page_size: 20,
      })
      setQueue(result.questions)
      setQueueStats(result.stats)
      setTotalPages(result.total_pages)
    } catch (error) {
      console.error('Failed to load queue:', error)
    } finally {
      setLoading(false)
    }
  }

  // Load question details when selected
  useEffect(() => {
    if (selectedQuestion) {
      loadQuestionDetail(selectedQuestion.question_id)
    }
  }, [selectedQuestion])

  const loadQuestionDetail = async (questionId: number) => {
    try {
      const result = await getReviewItem(questionId)
      setQuestionDetail(result.question)
      setVotingResult(result.voting_result)
      setEditableTags(result.suggested_tags || {})
      setReviewerNotes('')
      setCategory('')
    } catch (error) {
      console.error('Failed to load question detail:', error)
    }
  }

  // Handle tag selection from VoteComparison
  const handleSelectTag = (field: string, value: string | null) => {
    setEditableTags(prev => ({
      ...prev,
      [field]: value,
    }))
  }

  // Submit correction
  const handleSubmitCorrection = async () => {
    if (!selectedQuestion) return

    setSaving(true)
    try {
      await submitCorrection(selectedQuestion.question_id, {
        question_id: selectedQuestion.question_id,
        iteration: selectedQuestion.iteration,
        corrected_tags: editableTags,
        disagreement_category: category || undefined,
        reviewer_notes: reviewerNotes || undefined,
      })

      // Move to next question
      const currentIndex = queue.findIndex(q => q.question_id === selectedQuestion.question_id)
      if (currentIndex < queue.length - 1) {
        setSelectedQuestion(queue[currentIndex + 1])
      } else {
        setSelectedQuestion(null)
        loadQueue()
      }

      onReviewComplete?.()
    } catch (error) {
      console.error('Failed to submit correction:', error)
    } finally {
      setSaving(false)
    }
  }

  // Skip question
  const handleSkip = () => {
    const currentIndex = queue.findIndex(q => q.question_id === selectedQuestion?.question_id)
    if (currentIndex < queue.length - 1) {
      setSelectedQuestion(queue[currentIndex + 1])
    } else {
      setSelectedQuestion(null)
    }
  }

  // Reset editable tags
  const handleReset = () => {
    if (selectedQuestion) {
      setEditableTags(selectedQuestion.aggregated_tags)
      setReviewerNotes('')
      setCategory('')
    }
  }

  // Batch approve unanimous
  const handleBatchApprove = async () => {
    if (!confirm('This will approve all unanimous votes for the current iteration. Continue?')) return

    try {
      const result = await batchApproveUnanimous(1) // TODO: Get current iteration
      alert(`Approved ${result.approved_count} questions`)
      loadQueue()
      onReviewComplete?.()
    } catch (error) {
      console.error('Failed to batch approve:', error)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">3-Model Review Queue</h2>
          <p className="text-slate-600 mt-1">
            Review questions where models disagreed. Select the correct tags for each field.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleBatchApprove}
            className="flex items-center gap-2 px-4 py-2 bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg transition-colors"
          >
            <Check className="w-4 h-4" />
            Approve All Unanimous
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-red-100 rounded-lg">
              <X className="w-5 h-5 text-red-600" />
            </div>
            <div>
              <div className="text-2xl font-bold text-slate-900">{queueStats.conflicts}</div>
              <div className="text-sm text-slate-600">Conflicts (0/3 agree)</div>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-amber-100 rounded-lg">
              <AlertTriangle className="w-5 h-5 text-amber-600" />
            </div>
            <div>
              <div className="text-2xl font-bold text-slate-900">{queueStats.majority_votes}</div>
              <div className="text-sm text-slate-600">Majority (2/3 agree)</div>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-slate-100 rounded-lg">
              <Search className="w-5 h-5 text-slate-600" />
            </div>
            <div>
              <div className="text-2xl font-bold text-slate-900">{queueStats.total_pending}</div>
              <div className="text-sm text-slate-600">Total Pending</div>
            </div>
          </div>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2">
        {(['all', 'conflict', 'majority'] as const).map(level => (
          <button
            key={level}
            onClick={() => {
              setFilterLevel(level)
              setCurrentPage(1)
            }}
            className={`px-4 py-2 rounded-lg font-medium transition-all ${
              filterLevel === level
                ? level === 'conflict'
                  ? 'bg-red-500 text-white'
                  : level === 'majority'
                  ? 'bg-amber-500 text-white'
                  : 'bg-primary-500 text-white'
                : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
            }`}
          >
            {level === 'all' ? 'All' : level === 'conflict' ? 'Conflicts Only' : 'Majority Only'}
          </button>
        ))}
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-3 gap-6">
        {/* Queue List */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="p-4 bg-slate-50 border-b border-slate-200">
            <h3 className="font-medium text-slate-900">Questions to Review</h3>
          </div>
          <div className="divide-y divide-slate-200 max-h-[600px] overflow-y-auto">
            {loading ? (
              <div className="p-4 text-center text-slate-500">Loading...</div>
            ) : queue.length === 0 ? (
              <div className="p-4 text-center text-slate-500">No questions to review</div>
            ) : (
              queue.map(q => (
                <button
                  key={q.question_id}
                  onClick={() => setSelectedQuestion(q)}
                  className={`w-full p-4 text-left hover:bg-slate-50 transition-colors ${
                    selectedQuestion?.question_id === q.question_id ? 'bg-primary-50' : ''
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <span
                      className={`px-2 py-0.5 text-xs rounded font-medium ${
                        q.agreement_level === 'conflict'
                          ? 'bg-red-100 text-red-700'
                          : 'bg-amber-100 text-amber-700'
                      }`}
                    >
                      {q.agreement_level}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-slate-900 truncate">
                        #{q.question_id}
                      </div>
                      <div className="text-xs text-slate-500 truncate mt-1">
                        {q.question_text?.substring(0, 80)}...
                      </div>
                    </div>
                  </div>
                </button>
              ))
            )}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="p-4 border-t border-slate-200 flex items-center justify-between">
              <button
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="p-1 rounded hover:bg-slate-100 disabled:opacity-50"
              >
                <ChevronLeft className="w-5 h-5" />
              </button>
              <span className="text-sm text-slate-600">
                {currentPage} / {totalPages}
              </span>
              <button
                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                className="p-1 rounded hover:bg-slate-100 disabled:opacity-50"
              >
                <ChevronRight className="w-5 h-5" />
              </button>
            </div>
          )}
        </div>

        {/* Review Panel */}
        <div className="col-span-2">
          {selectedQuestion && questionDetail ? (
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
              {/* Question Header */}
              <div className="p-4 bg-slate-50 border-b border-slate-200">
                <h3 className="font-medium text-slate-900">
                  Question #{selectedQuestion.question_id}
                </h3>
              </div>

              {/* Question Content */}
              <div className="p-4 border-b border-slate-200">
                <div className="prose prose-sm max-w-none">
                  <p className="text-slate-700">{questionDetail.question_stem}</p>
                </div>
                {questionDetail.correct_answer && (
                  <div className="mt-3 p-3 bg-emerald-50 rounded-lg">
                    <span className="text-xs font-medium text-emerald-700">Correct Answer:</span>
                    <p className="text-sm text-emerald-800 mt-1">{questionDetail.correct_answer}</p>
                  </div>
                )}
              </div>

              {/* Vote Comparison */}
              <div className="p-4 border-b border-slate-200">
                {selectedQuestion && (
                  <VoteComparison
                    gptTags={selectedQuestion.gpt_tags}
                    claudeTags={selectedQuestion.claude_tags}
                    geminiTags={selectedQuestion.gemini_tags}
                    aggregatedTags={selectedQuestion.aggregated_tags}
                    agreementLevel={selectedQuestion.agreement_level}
                    onSelectTag={handleSelectTag}
                    editableTags={editableTags}
                  />
                )}
              </div>

              {/* Review Notes */}
              <div className="p-4 border-b border-slate-200 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Disagreement Category
                  </label>
                  <select
                    value={category}
                    onChange={e => setCategory(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500/20"
                  >
                    <option value="">Select category...</option>
                    <option value="disease_state_ambiguity">Disease State Ambiguity</option>
                    <option value="topic_confusion">Topic Confusion</option>
                    <option value="treatment_line_unclear">Treatment Line Unclear</option>
                    <option value="biomarker_interpretation">Biomarker Interpretation</option>
                    <option value="trial_identification">Trial Identification</option>
                    <option value="multiple_correct">Multiple Valid Options</option>
                    <option value="other">Other</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Reviewer Notes (optional)
                  </label>
                  <textarea
                    value={reviewerNotes}
                    onChange={e => setReviewerNotes(e.target.value)}
                    rows={2}
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500/20 resize-none"
                    placeholder="Add notes about this correction..."
                  />
                </div>
              </div>

              {/* Actions */}
              <div className="p-4 flex items-center justify-between bg-slate-50">
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleReset}
                    className="flex items-center gap-2 px-4 py-2 text-slate-600 hover:bg-slate-200 rounded-lg transition-colors"
                  >
                    <RotateCcw className="w-4 h-4" />
                    Reset
                  </button>
                  <button
                    onClick={handleSkip}
                    className="flex items-center gap-2 px-4 py-2 text-slate-600 hover:bg-slate-200 rounded-lg transition-colors"
                  >
                    Skip
                  </button>
                </div>
                <button
                  onClick={handleSubmitCorrection}
                  disabled={saving}
                  className="flex items-center gap-2 px-6 py-2 bg-primary-500 hover:bg-primary-600 text-white rounded-lg transition-colors disabled:opacity-50"
                >
                  <Save className="w-4 h-4" />
                  {saving ? 'Saving...' : 'Save Correction'}
                </button>
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-12 text-center">
              <Search className="w-12 h-12 text-slate-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-slate-900 mb-2">Select a question to review</h3>
              <p className="text-slate-600">
                Choose a question from the list to see the model votes and submit corrections.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
