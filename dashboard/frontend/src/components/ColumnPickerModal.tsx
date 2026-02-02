import { useState, useMemo } from 'react'
import { X, Search, Check } from 'lucide-react'
import { ADVANCED_FILTER_CATEGORIES } from '../types'

interface AdvancedFiltersModalProps {
  isOpen: boolean
  onClose: () => void
  selectedCategories: string[]
  onApply: (categories: string[]) => void
}

// Build grouped structure from the flat ADVANCED_FILTER_CATEGORIES array
const GROUPS = (() => {
  const map = new Map<string, { key: string; label: string }[]>()
  for (const cat of ADVANCED_FILTER_CATEGORIES) {
    if (!map.has(cat.group)) map.set(cat.group, [])
    map.get(cat.group)!.push({ key: cat.key, label: cat.label })
  }
  return Array.from(map.entries()).map(([group, items]) => ({ group, items }))
})()

export function ColumnPickerModal({ isOpen, onClose, selectedCategories, onApply }: AdvancedFiltersModalProps) {
  // Local working state — only committed to parent on Apply
  const [localSelected, setLocalSelected] = useState<Set<string>>(new Set(selectedCategories))
  const [searchQuery, setSearchQuery] = useState('')

  // Reset local state when modal opens
  const [prevOpen, setPrevOpen] = useState(false)
  if (isOpen && !prevOpen) {
    setLocalSelected(new Set(selectedCategories))
    setSearchQuery('')
  }
  if (isOpen !== prevOpen) {
    setPrevOpen(isOpen)
  }

  // Filter categories by search query
  const filteredGroups = useMemo(() => {
    if (!searchQuery.trim()) return GROUPS
    const query = searchQuery.toLowerCase()
    return GROUPS
      .map(g => ({
        ...g,
        items: g.items.filter(item =>
          item.label.toLowerCase().includes(query) || item.key.toLowerCase().includes(query)
        ),
      }))
      .filter(g => g.items.length > 0)
  }, [searchQuery])

  const toggleCategory = (key: string) => {
    setLocalSelected(prev => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  const handleApply = () => {
    onApply(Array.from(localSelected))
    onClose()
  }

  const handleClearAll = () => {
    setLocalSelected(new Set())
  }

  if (!isOpen) return null

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/30 z-[100]" onClick={onClose} />

      {/* Modal */}
      <div className="fixed inset-0 z-[101] flex items-center justify-center p-4">
        <div className="bg-white rounded-xl shadow-2xl w-full max-w-md max-h-[80vh] flex flex-col overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Advanced Filters</h2>
              <p className="text-xs text-slate-500 mt-0.5">Select filter categories to add to the filter panel</p>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 hover:bg-slate-100 rounded-lg transition-colors"
            >
              <X className="h-5 w-5 text-slate-500" />
            </button>
          </div>

          {/* Search */}
          <div className="px-5 py-3 border-b border-slate-200">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <input
                type="text"
                placeholder="Search categories..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-violet-500 focus:border-transparent text-sm"
                autoFocus
              />
            </div>
          </div>

          {/* Body — simple grouped checklist */}
          <div className="flex-1 overflow-y-auto px-5 py-3 space-y-4">
            {filteredGroups.map(({ group, items }) => (
              <div key={group}>
                <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">{group}</h3>
                <div className="space-y-0.5">
                  {items.map(item => {
                    const isSelected = localSelected.has(item.key)
                    return (
                      <div
                        key={item.key}
                        onClick={() => toggleCategory(item.key)}
                        className={`flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer text-sm transition-colors ${
                          isSelected
                            ? 'bg-violet-50 text-violet-900'
                            : 'text-slate-600 hover:bg-slate-50'
                        }`}
                      >
                        <div
                          className={`w-4 h-4 rounded border flex items-center justify-center flex-shrink-0 transition-colors ${
                            isSelected
                              ? 'bg-violet-600 border-violet-600'
                              : 'border-slate-300'
                          }`}
                        >
                          {isSelected && <Check className="h-3 w-3 text-white" />}
                        </div>
                        <span>{item.label}</span>
                      </div>
                    )
                  })}
                </div>
              </div>
            ))}

            {filteredGroups.length === 0 && (
              <div className="text-center py-8 text-sm text-slate-400">
                No categories match &ldquo;{searchQuery}&rdquo;
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between px-5 py-3 border-t border-slate-200 bg-slate-50">
            <div className="flex items-center gap-3">
              {localSelected.size > 0 && (
                <span className="text-xs text-slate-500">
                  {localSelected.size} selected
                </span>
              )}
              {localSelected.size > 0 && (
                <button
                  onClick={handleClearAll}
                  className="text-xs text-slate-500 hover:text-slate-700 underline"
                >
                  Clear all
                </button>
              )}
            </div>
            <button
              onClick={handleApply}
              className="px-4 py-2 bg-violet-600 text-white rounded-lg text-sm font-medium hover:bg-violet-700 transition-colors"
            >
              Apply
            </button>
          </div>
        </div>
      </div>
    </>
  )
}
