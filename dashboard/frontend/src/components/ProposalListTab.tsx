/**
 * ProposalListTab - Retagging proposal review interface
 *
 * Lists retagging proposals for review with:
 * - Status filters (pending, reviewing, ready_to_apply, applied, abandoned)
 * - Proposal list with summary info (field, value, match count, approval rate)
 * - Click to open detailed proposal review
 * - Create new proposal button
 */

import { useState, useEffect } from 'react'
import { Tag, CheckCircle, XCircle, Clock, RefreshCw, Plus, Trash2, PlayCircle } from 'lucide-react'
import CreateProposalModal from './CreateProposalModal'
import ProposalReviewView from './ProposalReviewView'
import {
  getProposalStats,
  getProposals,
  abandonProposal,
  type TagProposal,
  type ProposalStats
} from '../services/api'

type StatusFilter = 'all' | 'pending' | 'reviewing' | 'ready_to_apply' | 'applied' | 'abandoned'

export default function ProposalListTab() {
  const [proposals, setProposals] = useState<TagProposal[]>([])
  const [stats, setStats] = useState<ProposalStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('pending')
  const [selectedProposal, setSelectedProposal] = useState<TagProposal | null>(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [abandonConfirm, setAbandonConfirm] = useState<TagProposal | null>(null)

  // Fetch stats and proposals
  const fetchData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [statsData, proposalsData] = await Promise.all([
        getProposalStats(),
        getProposals(statusFilter === 'all' ? undefined : statusFilter)
      ])
      setStats(statsData)
      setProposals(proposalsData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [statusFilter])

  // Handle proposal abandon - show modal first
  const handleAbandonClick = (proposal: TagProposal) => {
    setAbandonConfirm(proposal)
  }

  // Actually abandon after confirmation
  const handleAbandonConfirmed = async () => {
    if (!abandonConfirm) return
    const proposalId = abandonConfirm.id
    setAbandonConfirm(null)
    try {
      await abandonProposal(proposalId)
      fetchData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to abandon proposal')
    }
  }

  // Status badge component
  const StatusBadge = ({ status }: { status: string }) => {
    const colors: Record<string, string> = {
      pending: 'bg-yellow-100 text-yellow-800',
      reviewing: 'bg-blue-100 text-blue-800',
      ready_to_apply: 'bg-green-100 text-green-800',
      applied: 'bg-emerald-100 text-emerald-800',
      abandoned: 'bg-gray-100 text-gray-500',
    }
    const icons: Record<string, React.ReactNode> = {
      pending: <Clock className="h-3 w-3" />,
      reviewing: <RefreshCw className="h-3 w-3" />,
      ready_to_apply: <PlayCircle className="h-3 w-3" />,
      applied: <CheckCircle className="h-3 w-3" />,
      abandoned: <XCircle className="h-3 w-3" />,
    }
    const labels: Record<string, string> = {
      pending: 'Pending',
      reviewing: 'Reviewing',
      ready_to_apply: 'Ready',
      applied: 'Applied',
      abandoned: 'Abandoned',
    }
    return (
      <span
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${colors[status] || 'bg-gray-100 text-gray-800'}`}
      >
        {icons[status]}
        {labels[status] || status}
      </span>
    )
  }

  // If viewing a proposal, show the review view
  if (selectedProposal) {
    return (
      <ProposalReviewView
        proposalId={selectedProposal.id}
        onClose={() => {
          setSelectedProposal(null)
          fetchData()
        }}
      />
    )
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Tag className="h-6 w-6 text-primary-600" />
          <h1 className="text-2xl font-bold text-slate-900">Retagging Proposals</h1>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => fetchData()}
            className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
            title="Refresh"
          >
            <RefreshCw className={`h-5 w-5 text-slate-600 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
          >
            <Plus className="h-4 w-4" />
            New Retagging Proposal
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-lg border p-4">
            <div className="text-2xl font-bold text-slate-900">{stats.total}</div>
            <div className="text-sm text-slate-600">Total Proposals</div>
          </div>
          <div className="bg-white rounded-lg border p-4">
            <div className="text-2xl font-bold text-yellow-600">{stats.pending + stats.reviewing}</div>
            <div className="text-sm text-slate-600">Pending Review</div>
          </div>
          <div className="bg-white rounded-lg border p-4">
            <div className="text-2xl font-bold text-green-600">{stats.ready_to_apply}</div>
            <div className="text-sm text-slate-600">Ready to Apply</div>
          </div>
          <div className="bg-white rounded-lg border p-4">
            <div className="text-2xl font-bold text-emerald-600">{stats.applied}</div>
            <div className="text-sm text-slate-600">Applied</div>
          </div>
        </div>
      )}

      {/* Status Filter Tabs */}
      <div className="flex gap-2 mb-4 border-b">
        {(['pending', 'reviewing', 'ready_to_apply', 'applied', 'abandoned', 'all'] as StatusFilter[]).map((status) => (
          <button
            key={status}
            onClick={() => setStatusFilter(status)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
              statusFilter === status
                ? 'border-primary-600 text-primary-600'
                : 'border-transparent text-slate-600 hover:text-slate-900'
            }`}
          >
            {status === 'all' ? 'All' : status === 'ready_to_apply' ? 'Ready' : status.charAt(0).toUpperCase() + status.slice(1)}
          </button>
        ))}
      </div>

      {/* Error State */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4">
          {error}
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="h-8 w-8 text-primary-600 animate-spin" />
        </div>
      )}

      {/* Empty State */}
      {!loading && proposals.length === 0 && (
        <div className="text-center py-12 text-slate-500">
          <Tag className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p>No retagging proposals found with status "{statusFilter}"</p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="mt-4 text-primary-600 hover:text-primary-700"
          >
            Create your first retagging proposal
          </button>
        </div>
      )}

      {/* Proposal List */}
      {!loading && proposals.length > 0 && (
        <div className="bg-white rounded-lg border overflow-hidden">
          <table className="w-full">
            <thead className="bg-slate-50 border-b">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium text-slate-600">Field</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-slate-600">Proposed Value</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-slate-600">Search Query</th>
                <th className="px-4 py-3 text-center text-sm font-medium text-slate-600">Matches</th>
                <th className="px-4 py-3 text-center text-sm font-medium text-slate-600">Approved</th>
                <th className="px-4 py-3 text-center text-sm font-medium text-slate-600">Status</th>
                <th className="px-4 py-3 text-center text-sm font-medium text-slate-600">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {proposals.map((proposal) => (
                <tr
                  key={proposal.id}
                  className="hover:bg-slate-50 cursor-pointer"
                  onClick={() => setSelectedProposal(proposal)}
                >
                  <td className="px-4 py-3">
                    <code className="text-sm bg-slate-100 px-1.5 py-0.5 rounded">
                      {proposal.field_name}
                    </code>
                  </td>
                  <td className="px-4 py-3 font-medium text-slate-900">
                    {proposal.proposed_value}
                  </td>
                  <td className="px-4 py-3 text-slate-600 text-sm">
                    {proposal.search_query}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className="text-sm font-medium">{proposal.match_count}</span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`text-sm font-medium ${proposal.approved_count > 0 ? 'text-green-600' : 'text-slate-400'}`}>
                      {proposal.approved_count}
                    </span>
                    {proposal.match_count > 0 && (
                      <span className="text-xs text-slate-400 ml-1">
                        ({Math.round((proposal.approved_count / proposal.match_count) * 100)}%)
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <StatusBadge status={proposal.status} />
                  </td>
                  <td className="px-4 py-3 text-center" onClick={(e) => e.stopPropagation()}>
                    {proposal.status !== 'applied' && proposal.status !== 'abandoned' && (
                      <button
                        onClick={() => handleAbandonClick(proposal)}
                        className="p-1 hover:bg-red-100 rounded text-red-600"
                        title="Abandon proposal"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Create Proposal Modal */}
      {showCreateModal && (
        <CreateProposalModal
          onClose={() => setShowCreateModal(false)}
          onCreated={(proposal) => {
            setShowCreateModal(false)
            setSelectedProposal(proposal)
          }}
        />
      )}

      {/* Abandon Confirmation Modal */}
      {abandonConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full mx-4 p-6">
            <h3 className="text-lg font-semibold text-slate-900 mb-2">Abandon Proposal?</h3>
            <p className="text-slate-600 mb-4">
              Are you sure you want to abandon the proposal for{' '}
              <code className="bg-slate-100 px-1.5 py-0.5 rounded text-sm">{abandonConfirm.field_name}</code> = <span className="font-medium">"{abandonConfirm.proposed_value}"</span>?
            </p>
            <p className="text-sm text-slate-500 mb-6">
              This will not delete any data, but the proposal will be marked as abandoned and won't be applied.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setAbandonConfirm(null)}
                className="px-4 py-2 text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleAbandonConfirmed}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
              >
                Abandon
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
