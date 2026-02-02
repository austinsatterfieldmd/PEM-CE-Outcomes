import { useState, useMemo } from 'react'
import { X, Search, ChevronDown, ChevronRight } from 'lucide-react'
import { FIELD_GUIDANCE, GUIDANCE_GROUPS, FieldGuidanceInfo } from '../config/fieldGuidance'

interface FieldGuidanceModalProps {
  isOpen: boolean
  onClose: () => void
}

export function FieldGuidanceModal({ isOpen, onClose }: FieldGuidanceModalProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set(['core', 'multiValue']))

  // Filter fields based on search query
  const filteredGroups = useMemo(() => {
    if (!searchQuery.trim()) {
      return GUIDANCE_GROUPS
    }

    const query = searchQuery.toLowerCase()
    const filtered: Record<string, { label: string; fields: string[] }> = {}

    for (const [groupKey, group] of Object.entries(GUIDANCE_GROUPS)) {
      const matchingFields = group.fields.filter(fieldKey => {
        const guidance = FIELD_GUIDANCE[fieldKey]
        if (!guidance) return false

        // Search in field key, description, examples, allowed values, and notes
        const searchableText = [
          fieldKey,
          guidance.description,
          ...(guidance.examples || []),
          ...(guidance.allowedValues || []),
          guidance.note || '',
        ].join(' ').toLowerCase()

        return searchableText.includes(query)
      })

      if (matchingFields.length > 0) {
        filtered[groupKey] = { label: group.label, fields: matchingFields }
      }
    }

    return filtered
  }, [searchQuery])

  // When searching, expand all groups with matches
  const effectiveExpandedGroups = useMemo(() => {
    if (searchQuery.trim()) {
      return new Set(Object.keys(filteredGroups))
    }
    return expandedGroups
  }, [searchQuery, filteredGroups, expandedGroups])

  const toggleGroup = (groupKey: string) => {
    setExpandedGroups(prev => {
      const next = new Set(prev)
      if (next.has(groupKey)) {
        next.delete(groupKey)
      } else {
        next.add(groupKey)
      }
      return next
    })
  }

  if (!isOpen) return null

  return (
    <>
      {/* Floating panel - no backdrop, allows interaction with rest of UI */}
      <div className="fixed right-[820px] top-4 bottom-4 w-[450px] bg-white rounded-xl shadow-2xl border border-slate-200 z-[90] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 bg-slate-50">
          <h2 className="text-lg font-semibold text-slate-900">Field Guidance</h2>
          <button
            onClick={onClose}
            className="p-1.5 hover:bg-slate-200 rounded-lg transition-colors"
          >
            <X className="h-5 w-5 text-slate-500" />
          </button>
        </div>

        {/* Search */}
        <div className="px-4 py-3 border-b border-slate-200">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search fields..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
            />
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {Object.entries(filteredGroups).map(([groupKey, group]) => (
            <div key={groupKey} className="bg-slate-50 rounded-lg overflow-hidden">
              {/* Group Header */}
              <button
                onClick={() => toggleGroup(groupKey)}
                className="w-full flex items-center justify-between px-3 py-2.5 hover:bg-slate-100 transition-colors"
              >
                <span className="text-sm font-semibold text-slate-700">{group.label}</span>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-400">{group.fields.length} fields</span>
                  {effectiveExpandedGroups.has(groupKey) ? (
                    <ChevronDown className="h-4 w-4 text-slate-400" />
                  ) : (
                    <ChevronRight className="h-4 w-4 text-slate-400" />
                  )}
                </div>
              </button>

              {/* Group Fields */}
              {effectiveExpandedGroups.has(groupKey) && (
                <div className="px-3 pb-3 space-y-2">
                  {group.fields.map(fieldKey => {
                    const guidance = FIELD_GUIDANCE[fieldKey]
                    if (!guidance) return null

                    return (
                      <FieldGuidanceItem
                        key={fieldKey}
                        fieldKey={fieldKey}
                        guidance={guidance}
                        searchQuery={searchQuery}
                      />
                    )
                  })}
                </div>
              )}
            </div>
          ))}

          {Object.keys(filteredGroups).length === 0 && (
            <div className="text-center py-8 text-slate-500">
              No fields match "{searchQuery}"
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-slate-200 bg-slate-50">
          <p className="text-xs text-slate-500">
            Use these guidelines when editing tags. Fields with dropdown icons have restricted values.
          </p>
        </div>
      </div>
    </>
  )
}

// Individual field guidance item
function FieldGuidanceItem({
  fieldKey,
  guidance,
  searchQuery,
}: {
  fieldKey: string
  guidance: FieldGuidanceInfo
  searchQuery: string
}) {
  // Format field key for display (e.g., "treatment_1" -> "treatment_1")
  const displayKey = fieldKey.replace(/_/g, '_')

  // Highlight matching text
  const highlightText = (text: string) => {
    if (!searchQuery.trim()) return text
    const regex = new RegExp(`(${searchQuery})`, 'gi')
    const parts = text.split(regex)
    return parts.map((part, i) =>
      regex.test(part) ? (
        <mark key={i} className="bg-yellow-200 rounded px-0.5">{part}</mark>
      ) : part
    )
  }

  return (
    <div className="bg-white rounded-lg p-3 border border-slate-200">
      {/* Field name */}
      <div className="flex items-center gap-2 mb-1.5">
        <code className="text-xs font-mono bg-slate-100 px-1.5 py-0.5 rounded text-blue-700">
          {highlightText(displayKey)}
        </code>
        {guidance.allowedValues && (
          <span className="text-xs px-1.5 py-0.5 rounded bg-purple-100 text-purple-700">
            dropdown
          </span>
        )}
      </div>

      {/* Description */}
      <p className="text-sm text-slate-700 mb-2">
        {highlightText(guidance.description)}
      </p>

      {/* Allowed values (for dropdowns) */}
      {guidance.allowedValues && (
        <div className="mb-2">
          <span className="text-xs font-medium text-slate-500 uppercase tracking-wide">Allowed values:</span>
          <div className="flex flex-wrap gap-1 mt-1">
            {guidance.allowedValues.map((value, i) => (
              <span key={i} className="text-xs px-1.5 py-0.5 bg-slate-100 text-slate-700 rounded">
                {highlightText(value)}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Examples (for free-text fields) */}
      {guidance.examples && !guidance.allowedValues && (
        <div className="mb-2">
          <span className="text-xs font-medium text-slate-500 uppercase tracking-wide">Examples:</span>
          <div className="flex flex-wrap gap-1 mt-1">
            {guidance.examples.slice(0, 5).map((example, i) => (
              <span key={i} className="text-xs px-1.5 py-0.5 bg-blue-50 text-blue-700 rounded">
                {highlightText(example)}
              </span>
            ))}
            {guidance.examples.length > 5 && (
              <span className="text-xs text-slate-400">+{guidance.examples.length - 5} more</span>
            )}
          </div>
        </div>
      )}

      {/* Note */}
      {guidance.note && (
        <p className="text-xs text-slate-500 italic">
          {highlightText(guidance.note)}
        </p>
      )}
    </div>
  )
}
