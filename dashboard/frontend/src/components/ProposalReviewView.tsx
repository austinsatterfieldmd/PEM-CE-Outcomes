/**
 * ProposalReviewView - Detailed view for reviewing proposal candidates
 *
 * Allows user to:
 * - See all candidate questions matching the search
 * - Approve or skip individual candidates
 * - Bulk approve/skip all pending
 * - Apply approved tags to database
 */

import { useState, useEffect } from 'react'
import { ArrowLeft, Check, X, CheckCircle, XCircle, RefreshCw, PlayCircle, Search } from 'lucide-react'
import {
  getProposal,
  reviewProposalCandidates,
  applyProposal,
  type TagProposal,
  type ProposalCandidate
} from '../services/apiRouter'

interface ProposalReviewViewProps {
  proposalId: number
  onClose: () => void
}

export default function ProposalReviewView({ proposalId, onClose }: ProposalReviewViewProps) {
  const [proposal, setProposal] = useState<TagProposal | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [processing, setProcessing] = useState(false)
  const [searchFilter, setSearchFilter] = useState('')
  const [showConfirmModal, setShowConfirmModal] = useState(false)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  // Fetch proposal with candidates
  const fetchProposal = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getProposal(proposalId)
      setProposal(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load proposal')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchProposal()
  }, [proposalId])

  // Handle approve/skip for a single candidate
  const handleReview = async (candidateId: number, decision: 'approved' | 'skipped') => {
    setProcessing(true)
    setError(null)
    try {
      await reviewProposalCandidates(proposalId, {
        approved_ids: decision === 'approved' ? [candidateId] : [],
        skipped_ids: decision === 'skipped' ? [candidateId] : [],
      })
      await fetchProposal()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update candidate')
    } finally {
      setProcessing(false)
    }
  }

  // Handle bulk approve/skip
  const handleBulkReview = async (decision: 'approved' | 'skipped') => {
    if (!proposal?.candidates) return
    const pendingIds = proposal.candidates
      .filter(c => c.decision === 'pending')
      .map(c => c.id)

    if (pendingIds.length === 0) return

    setProcessing(true)
    setError(null)
    try {
      await reviewProposalCandidates(proposalId, {
        approved_ids: decision === 'approved' ? pendingIds : [],
        skipped_ids: decision === 'skipped' ? pendingIds : [],
      })
      await fetchProposal()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update candidates')
    } finally {
      setProcessing(false)
    }
  }

  // Handle apply - show confirmation modal first
  const handleApplyClick = () => {
    if (!proposal || proposal.approved_count === 0) return
    setShowConfirmModal(true)
  }

  // Actually apply after confirmation
  const handleApplyConfirmed = async () => {
    if (!proposal) return
    setShowConfirmModal(false)
    setProcessing(true)
    try {
      const result = await applyProposal(proposalId)
      setSuccessMessage(`Successfully applied "${proposal.proposed_value}" to ${result.updated_count} questions`)
      // Auto-close after showing success
      setTimeout(() => onClose(), 2000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to apply tags')
      setProcessing(false)
    }
  }

  // Filter candidates by search
  const filteredCandidates = proposal?.candidates?.filter(c => {
    if (!searchFilter) return true
    const search = searchFilter.toLowerCase()
    return (
      c.question_stem?.toLowerCase().includes(search) ||
      c.correct_answer?.toLowerCase().includes(search) ||
      c.source_id?.includes(search)
    )
  }) || []

  // Count by decision
  const pendingCount = proposal?.candidates?.filter(c => c.decision === 'pending').length || 0
  const approvedCount = proposal?.candidates?.filter(c => c.decision === 'approved').length || 0
  const skippedCount = proposal?.candidates?.filter(c => c.decision === 'skipped').length || 0

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <RefreshCw className="h-8 w-8 text-primary-600 animate-spin" />
      </div>
    )
  }

  if (error || !proposal) {
    return (
      <div className="p-6">
        <button onClick={onClose} className="flex items-center gap-2 text-slate-600 hover:text-slate-900 mb-4">
          <ArrowLeft className="h-4 w-4" />
          Back to proposals
        </button>
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          {error || 'Proposal not found'}
        </div>
      </div>
    )
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <button onClick={onClose} className="flex items-center gap-2 text-slate-600 hover:text-slate-900 mb-2">
            <ArrowLeft className="h-4 w-4" />
            Back to proposals
          </button>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-slate-900">
              <code className="bg-slate-100 px-2 py-1 rounded text-lg">{proposal.field_name}</code>
              {' = '}
              <span className="text-primary-600">"{proposal.proposed_value}"</span>
            </h1>
          </div>
          {proposal.search_query && (
            <p className="text-slate-600 mt-1">
              Search: <span className="font-medium">"{proposal.search_query}"</span>
            </p>
          )}
          {proposal.proposal_reason && (
            <p className="text-slate-500 text-sm mt-1">{proposal.proposal_reason}</p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {proposal.status !== 'applied' && proposal.approved_count > 0 && (
            <button
              onClick={handleApplyClick}
              disabled={processing}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
            >
              <PlayCircle className="h-4 w-4" />
              Apply {approvedCount} Tags
            </button>
          )}
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6 flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-red-500 hover:text-red-700">
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-lg border p-4">
          <div className="text-2xl font-bold text-slate-900">{proposal.match_count}</div>
          <div className="text-sm text-slate-600">Total Matches</div>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <div className="text-2xl font-bold text-yellow-600">{pendingCount}</div>
          <div className="text-sm text-slate-600">Pending</div>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <div className="text-2xl font-bold text-green-600">{approvedCount}</div>
          <div className="text-sm text-slate-600">Approved</div>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <div className="text-2xl font-bold text-slate-400">{skippedCount}</div>
          <div className="text-sm text-slate-600">Skipped</div>
        </div>
      </div>

      {/* Bulk Actions & Search */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <button
            onClick={() => handleBulkReview('approved')}
            disabled={processing || pendingCount === 0}
            className="flex items-center gap-1 px-3 py-1.5 text-sm bg-green-100 text-green-700 rounded-lg hover:bg-green-200 transition-colors disabled:opacity-50"
          >
            <Check className="h-4 w-4" />
            Approve All Pending
          </button>
          <button
            onClick={() => handleBulkReview('skipped')}
            disabled={processing || pendingCount === 0}
            className="flex items-center gap-1 px-3 py-1.5 text-sm bg-slate-100 text-slate-600 rounded-lg hover:bg-slate-200 transition-colors disabled:opacity-50"
          >
            <X className="h-4 w-4" />
            Skip All Pending
          </button>
        </div>
        <div className="relative w-64">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input
            type="text"
            value={searchFilter}
            onChange={(e) => setSearchFilter(e.target.value)}
            placeholder="Filter candidates..."
            className="w-full pl-9 pr-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          />
        </div>
      </div>

      {/* Candidates List */}
      <div className="bg-white rounded-lg border overflow-hidden">
        <table className="w-full">
          <thead className="bg-slate-50 border-b">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-medium text-slate-600">Question</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-slate-600 w-64">Correct Answer</th>
              <th className="px-4 py-3 text-center text-sm font-medium text-slate-600 w-24">Current</th>
              <th className="px-4 py-3 text-center text-sm font-medium text-slate-600 w-20">Score</th>
              <th className="px-4 py-3 text-center text-sm font-medium text-slate-600 w-32">Decision</th>
              <th className="px-4 py-3 text-center text-sm font-medium text-slate-600 w-24">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {filteredCandidates.map((candidate) => (
              <CandidateRow
                key={candidate.id}
                candidate={candidate}
                searchQuery={proposal.search_query || ''}
                onApprove={() => handleReview(candidate.id, 'approved')}
                onSkip={() => handleReview(candidate.id, 'skipped')}
                processing={processing}
              />
            ))}
          </tbody>
        </table>
        {filteredCandidates.length === 0 && (
          <div className="text-center py-8 text-slate-500">
            No candidates found
          </div>
        )}
      </div>

      {/* Confirmation Modal */}
      {showConfirmModal && proposal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full mx-4 p-6">
            <h3 className="text-lg font-semibold text-slate-900 mb-2">Confirm Apply Tags</h3>
            <p className="text-slate-600 mb-6">
              This will set <code className="bg-slate-100 px-1.5 py-0.5 rounded text-sm">{proposal.field_name}</code> = <span className="font-medium text-primary-600">"{proposal.proposed_value}"</span> for <strong>{approvedCount}</strong> questions.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowConfirmModal(false)}
                className="px-4 py-2 text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleApplyConfirmed}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
              >
                Apply Tags
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Success Message */}
      {successMessage && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full mx-4 p-6 text-center">
            <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-slate-900 mb-2">Success!</h3>
            <p className="text-slate-600">{successMessage}</p>
          </div>
        </div>
      )}
    </div>
  )
}

// Individual candidate row component
interface CandidateRowProps {
  candidate: ProposalCandidate
  searchQuery: string
  onApprove: () => void
  onSkip: () => void
  processing: boolean
}

function CandidateRow({ candidate, searchQuery, onApprove, onSkip, processing }: CandidateRowProps) {
  // Highlight search term in text
  const highlightText = (text: string | null) => {
    if (!text || !searchQuery) return text
    const parts = text.split(new RegExp(`(${searchQuery})`, 'gi'))
    return parts.map((part, i) =>
      part.toLowerCase() === searchQuery.toLowerCase() ? (
        <mark key={i} className="bg-yellow-200 px-0.5 rounded">{part}</mark>
      ) : (
        part
      )
    )
  }

  const DecisionBadge = () => {
    if (candidate.decision === 'approved') {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
          <CheckCircle className="h-3 w-3" />
          Approved
        </span>
      )
    }
    if (candidate.decision === 'skipped') {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-600">
          <XCircle className="h-3 w-3" />
          Skipped
        </span>
      )
    }
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800">
        Pending
      </span>
    )
  }

  return (
    <tr className={`hover:bg-slate-50 ${candidate.decision !== 'pending' ? 'opacity-60' : ''}`}>
      <td className="px-4 py-3">
        <div className="text-sm text-slate-900">
          {highlightText(candidate.question_stem)}
        </div>
        <div className="text-xs text-slate-500 mt-1">
          QGD: {candidate.source_id}
        </div>
      </td>
      <td className="px-4 py-3">
        <div className="text-sm text-slate-700">
          {highlightText(candidate.correct_answer)}
        </div>
      </td>
      <td className="px-4 py-3 text-center">
        {candidate.current_value ? (
          <code className="text-xs bg-slate-100 px-1.5 py-0.5 rounded">
            {candidate.current_value}
          </code>
        ) : (
          <span className="text-slate-400 text-xs">—</span>
        )}
      </td>
      <td className="px-4 py-3 text-center text-sm text-slate-600">
        {candidate.match_score?.toFixed(2)}
      </td>
      <td className="px-4 py-3 text-center">
        <DecisionBadge />
      </td>
      <td className="px-4 py-3 text-center">
        {candidate.decision === 'pending' && (
          <div className="flex items-center justify-center gap-1">
            <button
              onClick={onApprove}
              disabled={processing}
              className="p-1.5 hover:bg-green-100 rounded text-green-600 transition-colors disabled:opacity-50"
              title="Approve"
            >
              <Check className="h-4 w-4" />
            </button>
            <button
              onClick={onSkip}
              disabled={processing}
              className="p-1.5 hover:bg-slate-100 rounded text-slate-500 transition-colors disabled:opacity-50"
              title="Skip"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        )}
      </td>
    </tr>
  )
}
