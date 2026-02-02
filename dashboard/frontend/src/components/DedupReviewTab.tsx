/**
 * DedupReviewTab - Deduplication review interface
 *
 * Lists duplicate clusters for review with:
 * - Status filters (pending, confirmed, rejected)
 * - Cluster list with summary info
 * - Click to open detailed cluster view
 */

import { useState, useEffect } from 'react'
import { Layers, CheckCircle, XCircle, Clock, RefreshCw, Upload } from 'lucide-react'
import DedupClusterView from './DedupClusterView'

interface ClusterMember {
  question_id: number
  source_id: string | null
  similarity_to_canonical: number | null
  is_canonical: boolean
  question_stem: string | null
  correct_answer: string | null
  incorrect_answers: string[] | null
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

interface DedupStats {
  total_clusters: number
  pending_clusters: number
  confirmed_clusters: number
  rejected_clusters: number
  duplicate_questions: number
}

const API_BASE = 'http://127.0.0.1:8000/api'

export default function DedupReviewTab() {
  const [clusters, setClusters] = useState<DuplicateCluster[]>([])
  const [stats, setStats] = useState<DedupStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<string>('pending')
  const [selectedCluster, setSelectedCluster] = useState<DuplicateCluster | null>(null)
  const [importing, setImporting] = useState(false)

  // Fetch stats and clusters
  const fetchData = async () => {
    setLoading(true)
    setError(null)
    try {
      // Fetch stats
      const statsRes = await fetch(`${API_BASE}/dedup/stats`)
      if (!statsRes.ok) throw new Error('Failed to fetch stats')
      const statsData = await statsRes.json()
      setStats(statsData)

      // Fetch clusters
      const clustersRes = await fetch(
        `${API_BASE}/dedup/clusters?status=${statusFilter}&limit=50`
      )
      if (!clustersRes.ok) throw new Error('Failed to fetch clusters')
      const clustersData = await clustersRes.json()
      setClusters(clustersData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [statusFilter])

  // Import dedup report
  const handleImport = async () => {
    const reportPath = prompt(
      'Enter the path to the dedup report JSON file:',
      'data/checkpoints/dedup_report_20260129_151953.json'
    )
    if (!reportPath) return

    setImporting(true)
    try {
      const res = await fetch(`${API_BASE}/dedup/import`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ report_path: reportPath }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Import failed')
      }
      const result = await res.json()
      alert(`Imported ${result.clusters_created} clusters`)
      fetchData()
    } catch (err) {
      alert(`Import error: ${err instanceof Error ? err.message : 'Unknown'}`)
    } finally {
      setImporting(false)
    }
  }

  // Handle cluster actions
  const handleClusterAction = async (
    clusterId: number,
    action: 'confirm' | 'reject',
    canonicalId?: number,
    selectedQuestionIds?: number[]
  ) => {
    try {
      const endpoint =
        action === 'confirm'
          ? `${API_BASE}/dedup/clusters/${clusterId}/confirm`
          : `${API_BASE}/dedup/clusters/${clusterId}/reject`

      const body =
        action === 'confirm'
          ? {
              canonical_question_id: canonicalId,
              selected_question_ids: selectedQuestionIds,
              reviewed_by: 'user'
            }
          : { reviewed_by: 'user' }

      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })

      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Action failed')
      }

      // Refresh data
      fetchData()
      setSelectedCluster(null)
    } catch (err) {
      alert(`Error: ${err instanceof Error ? err.message : 'Unknown'}`)
    }
  }

  // Status badge component
  const StatusBadge = ({ status }: { status: string }) => {
    const colors: Record<string, string> = {
      pending: 'bg-yellow-100 text-yellow-800',
      confirmed: 'bg-green-100 text-green-800',
      rejected: 'bg-red-100 text-red-800',
    }
    const icons: Record<string, React.ReactNode> = {
      pending: <Clock className="h-3 w-3" />,
      confirmed: <CheckCircle className="h-3 w-3" />,
      rejected: <XCircle className="h-3 w-3" />,
    }
    return (
      <span
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${colors[status] || 'bg-gray-100 text-gray-800'}`}
      >
        {icons[status]}
        {status}
      </span>
    )
  }

  if (selectedCluster) {
    return (
      <DedupClusterView
        cluster={selectedCluster}
        onClose={() => setSelectedCluster(null)}
        onConfirm={(canonicalId, selectedQuestionIds) =>
          handleClusterAction(selectedCluster.cluster_id, 'confirm', canonicalId, selectedQuestionIds)
        }
        onReject={() => handleClusterAction(selectedCluster.cluster_id, 'reject')}
      />
    )
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Layers className="h-6 w-6 text-primary-600" />
          <h1 className="text-2xl font-bold text-slate-900">Dedup Review</h1>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleImport}
            disabled={importing}
            className="flex items-center gap-2 px-4 py-2 bg-blue-50 hover:bg-blue-100 text-blue-700 rounded-lg transition-all disabled:opacity-50"
          >
            <Upload className="h-4 w-4" />
            {importing ? 'Importing...' : 'Import Report'}
          </button>
          <button
            onClick={fetchData}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition-all disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-lg border border-slate-200 p-4">
            <div className="text-2xl font-bold text-slate-900">{stats.total_clusters}</div>
            <div className="text-sm text-slate-500">Total Clusters</div>
          </div>
          <div className="bg-yellow-50 rounded-lg border border-yellow-200 p-4">
            <div className="text-2xl font-bold text-yellow-700">{stats.pending_clusters}</div>
            <div className="text-sm text-yellow-600">Pending Review</div>
          </div>
          <div className="bg-green-50 rounded-lg border border-green-200 p-4">
            <div className="text-2xl font-bold text-green-700">{stats.confirmed_clusters}</div>
            <div className="text-sm text-green-600">Confirmed</div>
          </div>
          <div className="bg-red-50 rounded-lg border border-red-200 p-4">
            <div className="text-2xl font-bold text-red-700">{stats.rejected_clusters}</div>
            <div className="text-sm text-red-600">Rejected</div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-2 mb-4">
        <span className="text-sm text-slate-600">Filter:</span>
        {['pending', 'confirmed', 'rejected', 'all'].map((status) => (
          <button
            key={status}
            onClick={() => setStatusFilter(status === 'all' ? '' : status)}
            className={`px-3 py-1 rounded-lg text-sm transition-all ${
              (status === 'all' && statusFilter === '') || statusFilter === status
                ? 'bg-primary-100 text-primary-700 font-medium'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            {status.charAt(0).toUpperCase() + status.slice(1)}
          </button>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-lg mb-4">
          {error}
        </div>
      )}

      {/* Clusters List */}
      {loading ? (
        <div className="text-center py-12 text-slate-500">Loading clusters...</div>
      ) : clusters.length === 0 ? (
        <div className="text-center py-12">
          <Layers className="h-12 w-12 text-slate-300 mx-auto mb-4" />
          <div className="text-slate-500">No duplicate clusters found</div>
          <div className="text-sm text-slate-400 mt-2">
            Import a dedup report to start reviewing duplicates
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {clusters.map((cluster) => (
            <div
              key={cluster.cluster_id}
              onClick={() => setSelectedCluster(cluster)}
              className="bg-white rounded-lg border border-slate-200 p-4 hover:border-primary-300 hover:shadow-sm cursor-pointer transition-all"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="text-lg font-semibold text-slate-900">
                    Cluster #{cluster.cluster_id}
                  </div>
                  <StatusBadge status={cluster.status} />
                  <span className="text-sm text-slate-500">
                    {cluster.members.length} questions
                  </span>
                  {cluster.similarity_threshold && (
                    <span className="text-sm text-slate-500">
                      {(cluster.similarity_threshold * 100).toFixed(0)}% threshold
                    </span>
                  )}
                </div>
                <div className="text-sm text-slate-400">
                  {cluster.created_at
                    ? new Date(cluster.created_at).toLocaleDateString()
                    : ''}
                </div>
              </div>
              {cluster.members.length > 0 && (
                <div className="mt-2 text-sm text-slate-600 line-clamp-2">
                  {cluster.members[0].question_stem?.substring(0, 150)}...
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
