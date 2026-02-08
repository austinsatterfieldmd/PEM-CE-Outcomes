/**
 * DedupClusterView - Side-by-side comparison of duplicate questions
 *
 * Shows all questions in a cluster with:
 * - QGD (source_id) and DB ID
 * - Question stem with diff highlighting
 * - Correct answer
 * - Activity list
 * - Checkboxes for selecting which are duplicates
 * - Actions: Confirm Selected, Reject All, Select Canonical
 */

import { useState, useEffect } from 'react'
import { X, Star, CheckCircle, XCircle, ExternalLink, Square, CheckSquare } from 'lucide-react'

interface ClusterMember {
  question_id: number
  source_id: string | null
  similarity_to_canonical: number | null
  is_canonical: boolean
  question_stem: string | null
  correct_answer: string | null
  incorrect_answers?: string[] | null
  source_file: string | null
}

interface DuplicateCluster {
  cluster_id: number
  canonical_question_id: number | null
  canonical_source_id: string | null
  status: string
  similarity_threshold: number | null
  created_at: string | null
  reviewed_at: string | null
  reviewed_by: string | null
  member_count: number | null
  members: ClusterMember[]
}

interface QuestionActivities {
  [questionId: number]: string[]
}

interface Props {
  cluster: DuplicateCluster
  onClose: () => void
  onConfirm: (canonicalQuestionId: number, selectedQuestionIds?: number[]) => void
  onReject: () => void
}

const API_BASE = 'http://127.0.0.1:8002/api'

export default function DedupClusterView({ cluster, onClose, onConfirm, onReject }: Props) {
  const [selectedCanonical, setSelectedCanonical] = useState<number | null>(
    cluster.canonical_question_id
  )
  // Track which questions are selected as duplicates (all selected by default)
  const [selectedAsDuplicates, setSelectedAsDuplicates] = useState<Set<number>>(
    new Set(cluster.members.map(m => m.question_id))
  )
  const [activities, setActivities] = useState<QuestionActivities>({})
  const [loadingActivities, setLoadingActivities] = useState(true)

  // Fetch activities for each question
  useEffect(() => {
    const fetchActivities = async () => {
      setLoadingActivities(true)
      const activitiesMap: QuestionActivities = {}

      for (const member of cluster.members) {
        try {
          const res = await fetch(`${API_BASE}/questions/${member.question_id}`)
          if (res.ok) {
            const data = await res.json()
            activitiesMap[member.question_id] = data.activities || []
          }
        } catch {
          activitiesMap[member.question_id] = []
        }
      }

      setActivities(activitiesMap)
      setLoadingActivities(false)
    }

    fetchActivities()
  }, [cluster.members])

  // Set initial canonical if not set
  useEffect(() => {
    if (!selectedCanonical && cluster.members.length > 0) {
      // Default to the first member or the one marked as canonical
      const canonical = cluster.members.find((m) => m.is_canonical)
      setSelectedCanonical(canonical?.question_id || cluster.members[0].question_id)
    }
  }, [cluster.members, selectedCanonical])

  // Ensure canonical is always in selected duplicates
  useEffect(() => {
    if (selectedCanonical && !selectedAsDuplicates.has(selectedCanonical)) {
      setSelectedAsDuplicates(prev => new Set([...prev, selectedCanonical]))
    }
  }, [selectedCanonical, selectedAsDuplicates])

  const toggleDuplicateSelection = (questionId: number) => {
    // Don't allow deselecting the canonical
    if (questionId === selectedCanonical) return

    setSelectedAsDuplicates(prev => {
      const newSet = new Set(prev)
      if (newSet.has(questionId)) {
        newSet.delete(questionId)
      } else {
        newSet.add(questionId)
      }
      return newSet
    })
  }

  const handleConfirm = () => {
    if (!selectedCanonical) {
      alert('Please select a canonical question first')
      return
    }

    if (selectedAsDuplicates.size < 2) {
      alert('Please select at least 2 questions as duplicates')
      return
    }

    // Pass selected question IDs to the confirm handler
    onConfirm(selectedCanonical, Array.from(selectedAsDuplicates))
  }

  // Simple diff highlighting (word-based)
  const highlightDiff = (text: string, reference: string | null): React.ReactNode => {
    if (!reference || !text) return text

    const textWords = text.split(/\s+/)
    const refWords = new Set(reference.toLowerCase().split(/\s+/))

    return textWords.map((word, idx) => {
      const isMatch = refWords.has(word.toLowerCase())
      return (
        <span
          key={idx}
          className={isMatch ? '' : 'bg-yellow-200 rounded px-0.5'}
        >
          {word}{' '}
        </span>
      )
    })
  }

  // Get the canonical question's stem for diff comparison
  const canonicalStem =
    cluster.members.find((m) => m.question_id === selectedCanonical)?.question_stem || null

  const selectedCount = selectedAsDuplicates.size
  const unselectedCount = cluster.members.length - selectedCount

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-6xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-200 bg-slate-50">
          <div>
            <h2 className="text-xl font-bold text-slate-900">
              Cluster #{cluster.cluster_id}
            </h2>
            <div className="flex items-center gap-4 mt-1 text-sm text-slate-500">
              <span>{cluster.members.length} questions</span>
              {cluster.similarity_threshold && (
                <span>
                  {(cluster.similarity_threshold * 100).toFixed(0)}% similarity threshold
                </span>
              )}
              <span
                className={`px-2 py-0.5 rounded text-xs font-medium ${
                  cluster.status === 'pending'
                    ? 'bg-yellow-100 text-yellow-800'
                    : cluster.status === 'confirmed'
                      ? 'bg-green-100 text-green-800'
                      : 'bg-red-100 text-red-800'
                }`}
              >
                {cluster.status}
              </span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-slate-200 rounded-lg transition-colors"
          >
            <X className="h-5 w-5 text-slate-500" />
          </button>
        </div>

        {/* Instructions for multi-select */}
        {cluster.status === 'pending' && cluster.members.length > 2 && (
          <div className="px-4 py-2 bg-blue-50 border-b border-blue-100 text-sm text-blue-700">
            <strong>Tip:</strong> Use checkboxes to select which questions are duplicates of each other.
            Uncheck any questions that are NOT duplicates of the canonical.
          </div>
        )}

        {/* Questions */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {cluster.members.map((member) => {
            const isCanonical = member.question_id === selectedCanonical
            const isSelected = selectedAsDuplicates.has(member.question_id)
            const memberActivities = activities[member.question_id] || []

            return (
              <div
                key={member.question_id}
                className={`rounded-lg border-2 p-4 transition-all ${
                  isCanonical
                    ? 'border-green-400 bg-green-50'
                    : isSelected
                      ? 'border-blue-300 bg-blue-50/30'
                      : 'border-slate-200 bg-slate-50/50 opacity-60'
                }`}
              >
                {/* Question header */}
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    {/* Checkbox for duplicate selection */}
                    {cluster.status === 'pending' && (
                      <button
                        onClick={() => toggleDuplicateSelection(member.question_id)}
                        className={`p-1 rounded transition-colors ${
                          isCanonical
                            ? 'text-green-600 cursor-not-allowed'
                            : isSelected
                              ? 'text-blue-600 hover:text-blue-700'
                              : 'text-slate-400 hover:text-slate-600'
                        }`}
                        title={isCanonical ? 'Canonical is always included' : isSelected ? 'Click to exclude from duplicates' : 'Click to include as duplicate'}
                        disabled={isCanonical}
                      >
                        {isSelected ? (
                          <CheckSquare className="h-5 w-5" />
                        ) : (
                          <Square className="h-5 w-5" />
                        )}
                      </button>
                    )}

                    {isCanonical && (
                      <span className="flex items-center gap-1 px-2 py-1 bg-green-100 text-green-700 rounded text-xs font-medium">
                        <Star className="h-3 w-3" />
                        CANONICAL
                      </span>
                    )}
                    <span className="text-sm font-medium text-slate-700">
                      Question #{member.source_id || member.question_id}
                    </span>
                    {member.similarity_to_canonical !== null && !isCanonical && (
                      <span className="text-sm text-slate-500">
                        {(member.similarity_to_canonical * 100).toFixed(1)}% similar
                      </span>
                    )}
                  </div>
                  {!isCanonical && cluster.status === 'pending' && isSelected && (
                    <button
                      onClick={() => setSelectedCanonical(member.question_id)}
                      className="flex items-center gap-1 px-3 py-1 bg-blue-50 hover:bg-blue-100 text-blue-700 rounded-lg text-sm transition-colors"
                    >
                      <Star className="h-4 w-4" />
                      Make Canonical
                    </button>
                  )}
                </div>

                {/* Activities */}
                <div className="mb-3">
                  <span className="text-xs font-medium text-slate-500">Activities:</span>
                  {loadingActivities ? (
                    <span className="text-xs text-slate-400 ml-2">Loading...</span>
                  ) : memberActivities.length > 0 ? (
                    <div className="flex flex-wrap gap-1 mt-1">
                      {memberActivities.slice(0, 5).map((activity, i) => (
                        <span
                          key={i}
                          className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded"
                        >
                          {activity.length > 40 ? activity.substring(0, 40) + '...' : activity}
                        </span>
                      ))}
                      {memberActivities.length > 5 && (
                        <span className="text-xs text-slate-400">
                          +{memberActivities.length - 5} more
                        </span>
                      )}
                    </div>
                  ) : (
                    <span className="text-xs text-slate-400 ml-2">No activities</span>
                  )}
                </div>

                {/* Question stem */}
                <div className="mb-3">
                  <div className="text-xs font-medium text-slate-500 mb-1">Question:</div>
                  <div className="text-sm text-slate-800 bg-white rounded p-3 border border-slate-100">
                    {isCanonical
                      ? member.question_stem
                      : highlightDiff(member.question_stem || '', canonicalStem)}
                  </div>
                </div>

                {/* Correct answer */}
                <div className="mb-3">
                  <div className="text-xs font-medium text-slate-500 mb-1">Correct Answer:</div>
                  <div className="text-sm text-green-700 bg-green-50 rounded p-2 border border-green-100">
                    {member.correct_answer || 'N/A'}
                  </div>
                </div>

                {/* Incorrect answers */}
                {member.incorrect_answers && member.incorrect_answers.length > 0 && (
                  <div className="mb-3">
                    <div className="text-xs font-medium text-slate-500 mb-1">Incorrect Answers:</div>
                    <div className="space-y-1">
                      {member.incorrect_answers.map((answer, i) => (
                        <div
                          key={i}
                          className="text-sm text-red-700 bg-red-50 rounded p-2 border border-red-100"
                        >
                          {answer}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Link to full question */}
                <div className="mt-3 pt-3 border-t border-slate-100">
                  <a
                    href={`/?question=${member.question_id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800"
                  >
                    <ExternalLink className="h-3 w-3" />
                    View full question
                  </a>
                </div>
              </div>
            )
          })}
        </div>

        {/* Actions */}
        {cluster.status === 'pending' && (
          <div className="flex items-center justify-between p-4 border-t border-slate-200 bg-slate-50">
            <div className="text-sm text-slate-500">
              <div>
                {selectedCanonical
                  ? `Canonical: Question #${cluster.members.find(m => m.question_id === selectedCanonical)?.source_id || selectedCanonical}`
                  : 'Select a canonical question'}
              </div>
              <div className="text-xs text-slate-400 mt-1">
                {selectedCount} selected as duplicates
                {unselectedCount > 0 && ` • ${unselectedCount} excluded`}
              </div>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={onReject}
                className="flex items-center gap-2 px-4 py-2 bg-red-50 hover:bg-red-100 text-red-700 rounded-lg transition-colors"
              >
                <XCircle className="h-4 w-4" />
                None are Duplicates
              </button>
              <button
                onClick={handleConfirm}
                disabled={!selectedCanonical || selectedCount < 2}
                className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <CheckCircle className="h-4 w-4" />
                {selectedCount === cluster.members.length
                  ? 'Confirm All as Duplicates'
                  : `Confirm ${selectedCount} as Duplicates`}
              </button>
            </div>
          </div>
        )}

        {/* Already reviewed */}
        {cluster.status !== 'pending' && (
          <div className="flex items-center justify-between p-4 border-t border-slate-200 bg-slate-50">
            <div className="text-sm text-slate-500">
              {cluster.status === 'confirmed' ? (
                <span className="text-green-600">
                  Confirmed as duplicates. Canonical: Question #{cluster.canonical_source_id}
                </span>
              ) : (
                <span className="text-red-600">Marked as not duplicates</span>
              )}
              {cluster.reviewed_at && (
                <span className="ml-2 text-slate-400">
                  on {new Date(cluster.reviewed_at).toLocaleDateString()}
                </span>
              )}
            </div>
            <button
              onClick={onClose}
              className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition-colors"
            >
              Close
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
