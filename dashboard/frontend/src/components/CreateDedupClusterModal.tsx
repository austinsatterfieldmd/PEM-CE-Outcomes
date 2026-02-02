/**
 * CreateDedupClusterModal - Modal for creating a dedup cluster from keyword search
 *
 * Allows user to:
 * - Start from a source question
 * - Search for similar questions by keyword
 * - Select which questions to include as duplicates
 * - Designate one as canonical
 * - Create the cluster for review
 */

import { useState, useEffect } from 'react'
import { X, Search, Layers, AlertCircle, Check, Star } from 'lucide-react'
import { searchDuplicateCandidates, createDedupCluster, type DuplicateCandidate } from '../services/api'

interface CreateDedupClusterModalProps {
  sourceQuestion: {
    id: number
    source_id: string | null
    question_stem: string | null
    correct_answer?: string | null
  }
  onClose: () => void
  onCreated: (clusterId: number) => void
}

export default function CreateDedupClusterModal({ sourceQuestion, onClose, onCreated }: CreateDedupClusterModalProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [candidates, setCandidates] = useState<DuplicateCandidate[]>([])
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set([sourceQuestion.id]))
  const [canonicalId, setCanonicalId] = useState<number>(sourceQuestion.id)
  const [loading, setLoading] = useState(false)
  const [searching, setSearching] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Search for candidates when query changes (debounced)
  useEffect(() => {
    if (!searchQuery.trim()) {
      setCandidates([])
      return
    }

    const timer = setTimeout(async () => {
      setSearching(true)
      setError(null)
      try {
        const results = await searchDuplicateCandidates(searchQuery, sourceQuestion.id, 30)
        setCandidates(results)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Search failed')
      } finally {
        setSearching(false)
      }
    }, 300)

    return () => clearTimeout(timer)
  }, [searchQuery, sourceQuestion.id])

  // Toggle selection
  const toggleSelect = (id: number) => {
    const newSelected = new Set(selectedIds)
    if (newSelected.has(id)) {
      // Can't deselect the source question
      if (id === sourceQuestion.id) return
      newSelected.delete(id)
      // If deselecting the canonical, reset to source
      if (id === canonicalId) {
        setCanonicalId(sourceQuestion.id)
      }
    } else {
      newSelected.add(id)
    }
    setSelectedIds(newSelected)
  }

  // Set as canonical
  const setAsCanonical = (id: number) => {
    if (!selectedIds.has(id)) {
      // Auto-select if setting as canonical
      setSelectedIds(new Set([...selectedIds, id]))
    }
    setCanonicalId(id)
  }

  // Create the cluster
  const handleCreate = async () => {
    if (selectedIds.size < 2) {
      setError('Select at least 2 questions to create a duplicate cluster')
      return
    }

    setLoading(true)
    setError(null)
    try {
      const result = await createDedupCluster({
        question_ids: Array.from(selectedIds),
        canonical_question_id: canonicalId,
        similarity_threshold: 0.90
      })
      onCreated(result.cluster_id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create cluster')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl max-w-3xl w-full mx-4 max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b flex-shrink-0">
          <div className="flex items-center gap-2">
            <Layers className="h-5 w-5 text-primary-600" />
            <h2 className="text-lg font-semibold text-slate-900">Flag as Potential Duplicate</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-slate-100 rounded-lg transition-colors"
          >
            <X className="h-5 w-5 text-slate-500" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* Source Question */}
          <div className="mb-6">
            <h3 className="text-sm font-medium text-slate-700 mb-2">Source Question</h3>
            <div className="bg-primary-50 border border-primary-200 rounded-lg p-3">
              <div className="flex items-start gap-2">
                <Star className="h-4 w-4 text-primary-600 mt-0.5 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-slate-900 line-clamp-2">{sourceQuestion.question_stem}</p>
                  <p className="text-xs text-slate-500 mt-1">QGD: {sourceQuestion.source_id}</p>
                </div>
                <span className="text-xs bg-primary-100 text-primary-700 px-2 py-0.5 rounded">
                  {canonicalId === sourceQuestion.id ? 'Canonical' : 'Selected'}
                </span>
              </div>
            </div>
          </div>

          {/* Search */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Search for Similar Questions
            </label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Enter keywords from the question..."
                className="w-full pl-9 pr-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Search by keywords in question stem or correct answer
            </p>
          </div>

          {/* Search Results */}
          {searching && (
            <div className="text-center py-4 text-slate-500">
              Searching...
            </div>
          )}

          {!searching && candidates.length > 0 && (
            <div className="space-y-2">
              <p className="text-sm text-slate-600 mb-2">
                Found {candidates.length} potential matches. Select duplicates:
              </p>
              {candidates.map((candidate) => (
                <div
                  key={candidate.id}
                  className={`border rounded-lg p-3 cursor-pointer transition-colors ${
                    selectedIds.has(candidate.id)
                      ? 'border-primary-300 bg-primary-50'
                      : 'border-slate-200 hover:border-slate-300'
                  }`}
                  onClick={() => toggleSelect(candidate.id)}
                >
                  <div className="flex items-start gap-3">
                    <div className={`mt-0.5 w-5 h-5 rounded border flex items-center justify-center flex-shrink-0 ${
                      selectedIds.has(candidate.id)
                        ? 'bg-primary-500 border-primary-500'
                        : 'border-slate-300'
                    }`}>
                      {selectedIds.has(candidate.id) && (
                        <Check className="h-3.5 w-3.5 text-white" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-slate-900 line-clamp-2">
                        {candidate.question_stem}
                      </p>
                      {candidate.correct_answer && (
                        <p className="text-xs text-slate-500 mt-1 line-clamp-1">
                          Answer: {candidate.correct_answer}
                        </p>
                      )}
                      <div className="flex items-center gap-3 mt-1 text-xs text-slate-400">
                        <span>QGD: {candidate.source_id}</span>
                        {candidate.disease_state && <span>{candidate.disease_state}</span>}
                      </div>
                    </div>
                    {selectedIds.has(candidate.id) && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          setAsCanonical(candidate.id)
                        }}
                        className={`text-xs px-2 py-1 rounded transition-colors ${
                          canonicalId === candidate.id
                            ? 'bg-amber-100 text-amber-700'
                            : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                        }`}
                      >
                        {canonicalId === candidate.id ? 'Canonical' : 'Make Canonical'}
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {!searching && searchQuery && candidates.length === 0 && (
            <div className="text-center py-4 text-slate-500">
              No matching questions found
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="flex items-center gap-2 text-red-600 text-sm bg-red-50 px-3 py-2 rounded-lg mt-4">
              <AlertCircle className="h-4 w-4 flex-shrink-0" />
              {error}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t bg-slate-50 flex-shrink-0">
          <div className="text-sm text-slate-600">
            {selectedIds.size} question{selectedIds.size !== 1 ? 's' : ''} selected
            {selectedIds.size >= 2 && (
              <span className="text-green-600 ml-2">Ready to create cluster</span>
            )}
          </div>
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleCreate}
              disabled={loading || selectedIds.size < 2}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Creating...' : 'Create Duplicate Cluster'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
