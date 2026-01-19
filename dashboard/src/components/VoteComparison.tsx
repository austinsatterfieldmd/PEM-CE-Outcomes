/**
 * VoteComparison Component
 *
 * Displays a side-by-side comparison of tags from the 3 voting models:
 * GPT-5.2, Claude Opus 4.5, and Gemini 2.5 Pro
 *
 * Highlights agreements and disagreements for easy review.
 */

import { Check, X, AlertTriangle, Brain } from 'lucide-react'
import type { Tags } from '../types'

interface VoteComparisonProps {
  gptTags: Tags
  claudeTags: Tags
  geminiTags: Tags
  aggregatedTags: Tags
  agreementLevel: 'unanimous' | 'majority' | 'conflict'
  onSelectTag?: (field: string, value: string | null) => void
  editableTags?: Tags
}

const TAG_FIELDS = [
  { key: 'topic', label: 'Topic' },
  { key: 'disease_state', label: 'Disease State' },
  { key: 'disease_stage', label: 'Disease Stage' },
  { key: 'disease_type', label: 'Disease Type' },
  { key: 'treatment_line', label: 'Treatment Line' },
  { key: 'treatment', label: 'Treatment' },
  { key: 'biomarker', label: 'Biomarker' },
  { key: 'trial', label: 'Trial' },
] as const

const MODEL_COLORS = {
  gpt: { bg: 'bg-emerald-50', border: 'border-emerald-200', text: 'text-emerald-700', accent: 'bg-emerald-100' },
  claude: { bg: 'bg-orange-50', border: 'border-orange-200', text: 'text-orange-700', accent: 'bg-orange-100' },
  gemini: { bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-700', accent: 'bg-blue-100' },
}

export function VoteComparison({
  gptTags,
  claudeTags,
  geminiTags,
  aggregatedTags,
  agreementLevel,
  onSelectTag,
  editableTags,
}: VoteComparisonProps) {
  // Check if all 3 models agree on a field
  const getFieldAgreement = (field: string): 'unanimous' | 'majority' | 'conflict' => {
    const gptVal = (gptTags as Record<string, unknown>)[field]
    const claudeVal = (claudeTags as Record<string, unknown>)[field]
    const geminiVal = (geminiTags as Record<string, unknown>)[field]

    const values = [gptVal, claudeVal, geminiVal].filter(v => v !== null && v !== undefined)

    if (values.length === 0) return 'unanimous' // All null
    if (new Set(values).size === 1) return 'unanimous' // All same

    // Count occurrences
    const counts: Record<string, number> = {}
    values.forEach(v => {
      const key = String(v)
      counts[key] = (counts[key] || 0) + 1
    })

    const maxCount = Math.max(...Object.values(counts))
    return maxCount >= 2 ? 'majority' : 'conflict'
  }

  // Get unique values for a field across models
  const getUniqueValues = (field: string): string[] => {
    const gptVal = (gptTags as Record<string, unknown>)[field]
    const claudeVal = (claudeTags as Record<string, unknown>)[field]
    const geminiVal = (geminiTags as Record<string, unknown>)[field]

    const values = new Set<string>()
    if (gptVal) values.add(String(gptVal))
    if (claudeVal) values.add(String(claudeVal))
    if (geminiVal) values.add(String(geminiVal))

    return Array.from(values)
  }

  return (
    <div className="space-y-4">
      {/* Agreement Level Banner */}
      <div className={`p-3 rounded-lg flex items-center gap-3 ${
        agreementLevel === 'unanimous'
          ? 'bg-emerald-50 border border-emerald-200'
          : agreementLevel === 'majority'
          ? 'bg-amber-50 border border-amber-200'
          : 'bg-red-50 border border-red-200'
      }`}>
        {agreementLevel === 'unanimous' ? (
          <>
            <Check className="w-5 h-5 text-emerald-600" />
            <span className="font-medium text-emerald-700">All 3 models agree</span>
          </>
        ) : agreementLevel === 'majority' ? (
          <>
            <AlertTriangle className="w-5 h-5 text-amber-600" />
            <span className="font-medium text-amber-700">2 of 3 models agree (majority vote)</span>
          </>
        ) : (
          <>
            <X className="w-5 h-5 text-red-600" />
            <span className="font-medium text-red-700">Models disagree - needs review</span>
          </>
        )}
      </div>

      {/* Model Headers */}
      <div className="grid grid-cols-4 gap-2 text-sm font-medium">
        <div className="px-3 py-2"></div>
        <div className={`px-3 py-2 rounded-t-lg ${MODEL_COLORS.gpt.bg} ${MODEL_COLORS.gpt.text} text-center`}>
          <Brain className="w-4 h-4 inline mr-1" />
          GPT-5.2
        </div>
        <div className={`px-3 py-2 rounded-t-lg ${MODEL_COLORS.claude.bg} ${MODEL_COLORS.claude.text} text-center`}>
          <Brain className="w-4 h-4 inline mr-1" />
          Claude Opus 4.5
        </div>
        <div className={`px-3 py-2 rounded-t-lg ${MODEL_COLORS.gemini.bg} ${MODEL_COLORS.gemini.text} text-center`}>
          <Brain className="w-4 h-4 inline mr-1" />
          Gemini 2.5 Pro
        </div>
      </div>

      {/* Tag Fields Grid */}
      <div className="border border-slate-200 rounded-lg overflow-hidden">
        {TAG_FIELDS.map((field, idx) => {
          const fieldAgreement = getFieldAgreement(field.key)
          const gptVal = (gptTags as Record<string, unknown>)[field.key] as string | null
          const claudeVal = (claudeTags as Record<string, unknown>)[field.key] as string | null
          const geminiVal = (geminiTags as Record<string, unknown>)[field.key] as string | null
          const aggregatedVal = (aggregatedTags as Record<string, unknown>)[field.key] as string | null
          const editableVal = editableTags ? (editableTags as Record<string, unknown>)[field.key] as string | null : aggregatedVal
          const uniqueValues = getUniqueValues(field.key)

          return (
            <div
              key={field.key}
              className={`grid grid-cols-4 gap-2 ${idx > 0 ? 'border-t border-slate-200' : ''} ${
                fieldAgreement === 'conflict' ? 'bg-red-50/30' : fieldAgreement === 'majority' ? 'bg-amber-50/30' : ''
              }`}
            >
              {/* Field Label */}
              <div className="px-3 py-2 bg-slate-50 font-medium text-slate-700 flex items-center gap-2">
                {field.label}
                {fieldAgreement === 'conflict' && (
                  <span className="px-1.5 py-0.5 text-xs bg-red-100 text-red-700 rounded">!</span>
                )}
              </div>

              {/* GPT Value */}
              <div className={`px-3 py-2 ${MODEL_COLORS.gpt.bg} ${MODEL_COLORS.gpt.border} border-l`}>
                <TagValue
                  value={gptVal}
                  isSelected={editableVal === gptVal}
                  isAgreed={gptVal === aggregatedVal}
                  onClick={() => onSelectTag?.(field.key, gptVal)}
                  canSelect={!!onSelectTag && fieldAgreement !== 'unanimous'}
                />
              </div>

              {/* Claude Value */}
              <div className={`px-3 py-2 ${MODEL_COLORS.claude.bg} ${MODEL_COLORS.claude.border} border-l`}>
                <TagValue
                  value={claudeVal}
                  isSelected={editableVal === claudeVal}
                  isAgreed={claudeVal === aggregatedVal}
                  onClick={() => onSelectTag?.(field.key, claudeVal)}
                  canSelect={!!onSelectTag && fieldAgreement !== 'unanimous'}
                />
              </div>

              {/* Gemini Value */}
              <div className={`px-3 py-2 ${MODEL_COLORS.gemini.bg} ${MODEL_COLORS.gemini.border} border-l`}>
                <TagValue
                  value={geminiVal}
                  isSelected={editableVal === geminiVal}
                  isAgreed={geminiVal === aggregatedVal}
                  onClick={() => onSelectTag?.(field.key, geminiVal)}
                  canSelect={!!onSelectTag && fieldAgreement !== 'unanimous'}
                />
              </div>
            </div>
          )
        })}
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 text-xs text-slate-500 pt-2">
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded bg-emerald-200 border border-emerald-400"></div>
          <span>Selected/Agreed</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded bg-slate-200 border border-slate-300"></div>
          <span>Not selected</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded bg-red-100 border border-red-300"></div>
          <span>Conflict</span>
        </div>
      </div>
    </div>
  )
}

// Sub-component for individual tag values
function TagValue({
  value,
  isSelected,
  isAgreed,
  onClick,
  canSelect,
}: {
  value: string | null
  isSelected: boolean
  isAgreed: boolean
  onClick?: () => void
  canSelect: boolean
}) {
  if (!value) {
    return <span className="text-slate-400 text-sm italic">null</span>
  }

  const baseClasses = 'px-2 py-1 rounded text-sm inline-block'
  const selectableClasses = canSelect
    ? 'cursor-pointer hover:ring-2 hover:ring-primary-500/50'
    : ''
  const selectedClasses = isSelected
    ? 'bg-emerald-200 text-emerald-800 ring-2 ring-emerald-500'
    : isAgreed
    ? 'bg-slate-100 text-slate-700'
    : 'bg-slate-100 text-slate-600'

  return (
    <button
      className={`${baseClasses} ${selectedClasses} ${selectableClasses}`}
      onClick={onClick}
      disabled={!canSelect}
    >
      {value}
      {isSelected && <Check className="w-3 h-3 inline ml-1" />}
    </button>
  )
}
