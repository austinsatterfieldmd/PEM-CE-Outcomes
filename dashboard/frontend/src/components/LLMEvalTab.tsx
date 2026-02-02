/**
 * LLMEvalTab - LLM Evaluation Dashboard
 *
 * Displays accuracy metrics for the multi-model tagging system:
 * - Summary statistics
 * - Accuracy by batch (improvement over time)
 * - Model comparison (GPT vs Claude vs Gemini)
 * - Agreement level analysis
 * - Field group breakdown
 * - Top problem fields
 */

import { useState, useEffect } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  Legend,
} from 'recharts'
import {
  Activity,
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
  Users,
  Layers,
  RefreshCw,
} from 'lucide-react'

const API_BASE = 'http://localhost:8000/api'

// Types for eval metrics
interface BatchStats {
  batch: string
  total_questions: number
  questions_with_edits: number
  question_accuracy: number
  total_fields: number
  edited_fields: number
  field_accuracy: number
}

interface ModelStats {
  model: string
  accuracy: number
  correct: number
  wrong: number
  null_to_needed: number
  value_to_cleared: number
}

interface AgreementStats {
  level: string
  total_fields: number
  edited_fields: number
  accuracy: number
  error_rate: number
}

interface FieldGroupStats {
  group: string
  total_fields: number
  edited_fields: number
  accuracy: number
  error_rate: number
  wrong_to_fixed: number
  null_to_added: number
  value_to_cleared: number
}

interface FieldStats {
  field: string
  group: string
  total: number
  errors: number
  error_rate: number
  top_corrections: { pattern: string; count: number }[]
}

interface EvalSummary {
  total_questions: number
  questions_with_edits: number
  question_edit_rate: number
  total_fields: number
  total_corrections: number
  overall_accuracy: number
  generated_at: string
}

interface DisagreementData {
  total_disagreements: number
  by_dissenter: Record<string, {
    times_dissented: number
    dissenter_correct: number
    dissenter_correct_pct: number
    majority_correct: number
    majority_correct_pct: number
  }>
}

interface EvalMetrics {
  summary: EvalSummary
  by_batch: BatchStats[]
  by_model: ModelStats[]
  by_agreement: AgreementStats[]
  by_field_group: FieldGroupStats[]
  top_problem_fields: FieldStats[]
  model_disagreement_analysis: DisagreementData
}

// Colors
const MODEL_COLORS: Record<string, string> = {
  GPT: '#10b981',     // emerald
  CLAUDE: '#8b5cf6',  // violet
  GEMINI: '#f59e0b',  // amber
}

const AGREEMENT_COLORS: Record<string, string> = {
  unanimous: '#10b981',  // green
  majority: '#f59e0b',   // amber
  conflict: '#ef4444',   // red
}

// Custom tooltip
const ChartTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null

  return (
    <div className="bg-slate-900 border border-slate-700 rounded-lg p-3 shadow-xl max-w-xs">
      <p className="font-semibold text-white mb-2 text-sm">{label}</p>
      <div className="space-y-1.5 text-xs">
        {payload.map((entry: any, idx: number) => (
          <div key={idx} className="flex items-center gap-2">
            <span
              className="w-2.5 h-2.5 rounded-sm"
              style={{ backgroundColor: entry.color }}
            />
            <span className="text-slate-300">{entry.name}:</span>
            <span className="font-mono text-white">
              {entry.value !== null && entry.value !== undefined
                ? typeof entry.value === 'number'
                  ? `${entry.value.toFixed(1)}%`
                  : entry.value
                : '—'}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function LLMEvalTab() {
  const [metrics, setMetrics] = useState<EvalMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchMetrics = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`${API_BASE}/eval/metrics`)
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      const data = await response.json()
      setMetrics(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load metrics')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchMetrics()
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="flex items-center gap-3 text-slate-500">
          <RefreshCw className="w-5 h-5 animate-spin" />
          <span>Loading evaluation metrics...</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
        <AlertTriangle className="w-8 h-8 text-red-500 mx-auto mb-2" />
        <p className="text-red-700 font-medium">Failed to load metrics</p>
        <p className="text-red-600 text-sm mt-1">{error}</p>
        <button
          onClick={fetchMetrics}
          className="mt-4 px-4 py-2 bg-red-100 hover:bg-red-200 text-red-700 rounded-lg text-sm font-medium transition-colors"
        >
          Retry
        </button>
      </div>
    )
  }

  if (!metrics) return null

  const { summary, by_batch, by_model, by_agreement, by_field_group, top_problem_fields, model_disagreement_analysis } = metrics

  return (
    <div className="space-y-6">
      {/* Summary Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl shadow-sm border border-slate-200/60 p-4">
          <div className="flex items-center gap-2 text-slate-500 text-sm mb-1">
            <Activity className="w-4 h-4" />
            Questions Analyzed
          </div>
          <div className="text-2xl font-bold text-slate-900">{summary.total_questions}</div>
          <div className="text-xs text-slate-500 mt-1">
            {summary.questions_with_edits} with human edits ({summary.question_edit_rate.toFixed(1)}%)
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-slate-200/60 p-4">
          <div className="flex items-center gap-2 text-slate-500 text-sm mb-1">
            <Layers className="w-4 h-4" />
            Total Fields
          </div>
          <div className="text-2xl font-bold text-slate-900">{summary.total_fields.toLocaleString()}</div>
          <div className="text-xs text-slate-500 mt-1">
            {summary.total_corrections} corrections
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-slate-200/60 p-4">
          <div className="flex items-center gap-2 text-slate-500 text-sm mb-1">
            <CheckCircle2 className="w-4 h-4" />
            Field Accuracy
          </div>
          <div className="text-2xl font-bold text-emerald-600">{summary.overall_accuracy}%</div>
          <div className="text-xs text-slate-500 mt-1">
            Overall LLM accuracy
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-slate-200/60 p-4">
          <div className="flex items-center gap-2 text-slate-500 text-sm mb-1">
            <Users className="w-4 h-4" />
            Best Model
          </div>
          <div className="text-2xl font-bold text-violet-600">
            {by_model.sort((a, b) => b.accuracy - a.accuracy)[0]?.model || '—'}
          </div>
          <div className="text-xs text-slate-500 mt-1">
            {by_model.sort((a, b) => b.accuracy - a.accuracy)[0]?.accuracy}% accuracy
          </div>
        </div>
      </div>

      {/* Charts Row 1: Batch Trend + Model Comparison */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Accuracy by Batch */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200/60 p-5">
          <h3 className="text-sm font-semibold text-slate-700 mb-4 flex items-center gap-2">
            <TrendingUp className="w-4 h-4" />
            Accuracy by Batch (Improvement Over Time)
          </h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={by_batch} margin={{ top: 10, right: 10, left: 0, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis
                  dataKey="batch"
                  tick={{ fill: '#64748b', fontSize: 11 }}
                  axisLine={{ stroke: '#cbd5e1' }}
                />
                <YAxis
                  domain={[80, 100]}
                  tick={{ fill: '#64748b', fontSize: 11 }}
                  axisLine={{ stroke: '#cbd5e1' }}
                  tickFormatter={(v) => `${v}%`}
                />
                <Tooltip content={<ChartTooltip />} />
                <Bar dataKey="field_accuracy" name="Field Accuracy" fill="#10b981" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          {by_batch.length >= 2 && (
            <div className="mt-2 text-xs text-slate-500 text-center">
              Trend: {by_batch[0].field_accuracy}% → {by_batch[by_batch.length - 1].field_accuracy}%
              <span className={by_batch[by_batch.length - 1].field_accuracy > by_batch[0].field_accuracy ? 'text-emerald-600' : 'text-red-600'}>
                {' '}({by_batch[by_batch.length - 1].field_accuracy > by_batch[0].field_accuracy ? '+' : ''}
                {(by_batch[by_batch.length - 1].field_accuracy - by_batch[0].field_accuracy).toFixed(1)} pts)
              </span>
            </div>
          )}
        </div>

        {/* Model Comparison */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200/60 p-5">
          <h3 className="text-sm font-semibold text-slate-700 mb-4 flex items-center gap-2">
            <Users className="w-4 h-4" />
            Model Comparison
          </h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={by_model} margin={{ top: 10, right: 10, left: 0, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis
                  dataKey="model"
                  tick={{ fill: '#64748b', fontSize: 11 }}
                  axisLine={{ stroke: '#cbd5e1' }}
                />
                <YAxis
                  domain={[90, 100]}
                  tick={{ fill: '#64748b', fontSize: 11 }}
                  axisLine={{ stroke: '#cbd5e1' }}
                  tickFormatter={(v) => `${v}%`}
                />
                <Tooltip content={<ChartTooltip />} />
                <Bar dataKey="accuracy" name="Accuracy" radius={[4, 4, 0, 0]}>
                  {by_model.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={MODEL_COLORS[entry.model] || '#94a3b8'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
            {by_model.map((m) => (
              <div key={m.model} className="text-center">
                <span className="font-medium" style={{ color: MODEL_COLORS[m.model] }}>{m.model}</span>
                <div className="text-slate-500">{m.accuracy}%</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Charts Row 2: Agreement Level + Field Groups */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Agreement Level */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200/60 p-5">
          <h3 className="text-sm font-semibold text-slate-700 mb-4 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4" />
            Accuracy by Agreement Level
          </h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={by_agreement} margin={{ top: 10, right: 10, left: 0, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis
                  dataKey="level"
                  tick={{ fill: '#64748b', fontSize: 11 }}
                  axisLine={{ stroke: '#cbd5e1' }}
                  tickFormatter={(v) => v.charAt(0).toUpperCase() + v.slice(1)}
                />
                <YAxis
                  domain={[0, 100]}
                  tick={{ fill: '#64748b', fontSize: 11 }}
                  axisLine={{ stroke: '#cbd5e1' }}
                  tickFormatter={(v) => `${v}%`}
                />
                <Tooltip content={<ChartTooltip />} />
                <Bar dataKey="accuracy" name="Accuracy" radius={[4, 4, 0, 0]}>
                  {by_agreement.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={AGREEMENT_COLORS[entry.level] || '#94a3b8'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-3 text-xs text-slate-500 text-center">
            Unanimous: {by_agreement.find(a => a.level === 'unanimous')?.accuracy || 0}% |
            Majority: {by_agreement.find(a => a.level === 'majority')?.accuracy || 0}% |
            Conflict: {by_agreement.find(a => a.level === 'conflict')?.accuracy || 0}%
          </div>
        </div>

        {/* Field Groups */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200/60 p-5">
          <h3 className="text-sm font-semibold text-slate-700 mb-4 flex items-center gap-2">
            <Layers className="w-4 h-4" />
            Error Rate by Field Group
          </h3>
          <div className="space-y-2 max-h-72 overflow-y-auto">
            {by_field_group.map((group) => (
              <div key={group.group} className="flex items-center gap-3">
                <div className="w-32 text-xs text-slate-600 truncate" title={group.group}>
                  {group.group}
                </div>
                <div className="flex-1 h-5 bg-slate-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-emerald-500 to-emerald-400 rounded-full"
                    style={{ width: `${group.accuracy}%` }}
                  />
                </div>
                <div className="w-16 text-xs text-right">
                  <span className="font-medium text-slate-700">{group.accuracy}%</span>
                  <span className="text-slate-400 ml-1">acc</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Dissenter Analysis */}
      {model_disagreement_analysis.total_disagreements > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200/60 p-5">
          <h3 className="text-sm font-semibold text-slate-700 mb-4 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" />
            When Models Disagreed ({model_disagreement_analysis.total_disagreements} cases)
          </h3>
          <div className="grid grid-cols-3 gap-4">
            {Object.entries(model_disagreement_analysis.by_dissenter).map(([model, stats]) => (
              <div key={model} className="bg-slate-50 rounded-lg p-4">
                <div className="font-medium mb-2" style={{ color: MODEL_COLORS[model] }}>{model}</div>
                <div className="text-sm text-slate-600">
                  <div>Dissented: {stats.times_dissented}x</div>
                  <div>Dissenter was right: <span className="font-medium">{stats.dissenter_correct_pct}%</span></div>
                  <div>Majority was right: <span className="font-medium">{stats.majority_correct_pct}%</span></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Top Problem Fields Table */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200/60 p-5">
        <h3 className="text-sm font-semibold text-slate-700 mb-4 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4" />
          Top Problem Fields
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200">
                <th className="text-left py-2 px-3 text-slate-600 font-medium">Field</th>
                <th className="text-left py-2 px-3 text-slate-600 font-medium">Group</th>
                <th className="text-right py-2 px-3 text-slate-600 font-medium">Errors</th>
                <th className="text-right py-2 px-3 text-slate-600 font-medium">Error Rate</th>
                <th className="text-left py-2 px-3 text-slate-600 font-medium">Top Correction Pattern</th>
              </tr>
            </thead>
            <tbody>
              {top_problem_fields.map((field, idx) => (
                <tr key={field.field} className={idx % 2 === 0 ? 'bg-slate-50/50' : ''}>
                  <td className="py-2 px-3 font-mono text-xs">{field.field}</td>
                  <td className="py-2 px-3 text-slate-500 text-xs">{field.group}</td>
                  <td className="py-2 px-3 text-right">{field.errors}</td>
                  <td className="py-2 px-3 text-right">
                    <span className={`font-medium ${field.error_rate > 10 ? 'text-red-600' : field.error_rate > 5 ? 'text-amber-600' : 'text-slate-600'}`}>
                      {field.error_rate}%
                    </span>
                  </td>
                  <td className="py-2 px-3 text-xs text-slate-500 max-w-xs truncate" title={field.top_corrections[0]?.pattern}>
                    {field.top_corrections[0] ? `[${field.top_corrections[0].count}x] ${field.top_corrections[0].pattern}` : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Generated timestamp */}
      <div className="text-xs text-slate-400 text-right">
        Generated: {new Date(summary.generated_at).toLocaleString()}
        <button
          onClick={fetchMetrics}
          className="ml-3 text-primary-500 hover:text-primary-600"
        >
          Refresh
        </button>
      </div>
    </div>
  )
}
