import { useState, useEffect } from 'react'
import { Check, X, Search, ArrowDownAZ, Hash } from 'lucide-react'
import type { FilterOptions, SearchFilters } from '../types'
import { ADVANCED_FILTER_CATEGORIES } from '../types'

interface FilterPanelProps {
  options: FilterOptions
  filters: SearchFilters
  onChange: (filters: SearchFilters) => void
  advancedCategories?: string[]
}

// Build a lookup from category key -> label
const CATEGORY_LABEL_MAP = new Map(
  ADVANCED_FILTER_CATEGORIES.map(c => [c.key, c.label])
)

export function FilterPanel({ options, filters, onChange, advancedCategories = [] }: FilterPanelProps) {
  const [sectionSearches, setSectionSearches] = useState<Record<string, string>>({})
  const [sortByFrequency, setSortByFrequency] = useState<Record<string, boolean>>({})

  // Clear section searches when all filters are cleared
  useEffect(() => {
    const hasActiveFilters = Object.values(filters).some(v => {
      if (v && typeof v === 'object' && !Array.isArray(v)) {
        // advanced_filters dict — check if any values exist
        return Object.values(v as Record<string, unknown>).some(arr => Array.isArray(arr) && arr.length > 0)
      }
      return v && (Array.isArray(v) ? v.length > 0 : true)
    })
    if (!hasActiveFilters) {
      setSectionSearches({})
    }
  }, [filters])

  // Core 8 tag filters
  const coreFilterSections = [
    { key: 'disease_states', label: 'Disease State', options: options.disease_states, searchable: true },
    { key: 'topics', label: 'Topic', options: options.topics, searchable: false },
    { key: 'treatments', label: 'Treatment', options: options.treatments, searchable: true },
    { key: 'treatment_lines', label: 'Treatment Line', options: options.treatment_lines || [], searchable: false },
    { key: 'disease_stages', label: 'Disease Stage', options: options.disease_stages, searchable: false },
    { key: 'disease_types', label: 'Disease Type', options: options.disease_types || [], searchable: true },
    { key: 'biomarkers', label: 'Biomarker', options: options.biomarkers, searchable: true },
    { key: 'trials', label: 'Trial', options: options.trials, searchable: true },
  ]

  // Build advanced filter sections from selected categories
  const advancedFilterSections = advancedCategories
    .map(catKey => {
      const catOptions = (options as Record<string, unknown>)[catKey] as { value: string; count: number }[] | undefined
      return {
        key: catKey,
        label: CATEGORY_LABEL_MAP.get(catKey) || catKey,
        options: catOptions || [],
        searchable: (catOptions?.length ?? 0) > 8,
      }
    })
    .filter(s => s.options.length > 0)

  // ---- Core filter toggle (top-level fields) ----
  const toggleFilter = (section: keyof SearchFilters, value: string) => {
    const current = filters[section] as string[] || []
    const updated = current.includes(value)
      ? current.filter(v => v !== value)
      : [...current, value]

    onChange({
      ...filters,
      [section]: updated.length > 0 ? updated : undefined
    })
  }

  const removeFilter = (section: keyof SearchFilters, value: string) => {
    const current = filters[section] as string[] || []
    const updated = current.filter(v => v !== value)
    onChange({
      ...filters,
      [section]: updated.length > 0 ? updated : undefined
    })
  }

  // ---- Advanced filter toggle (nested in filters.advanced_filters) ----
  const toggleAdvancedFilter = (category: string, value: string) => {
    const advFilters = { ...(filters.advanced_filters || {}) }
    const current = advFilters[category] || []
    const updated = current.includes(value)
      ? current.filter(v => v !== value)
      : [...current, value]

    if (updated.length > 0) {
      advFilters[category] = updated
    } else {
      delete advFilters[category]
    }

    onChange({
      ...filters,
      advanced_filters: Object.keys(advFilters).length > 0 ? advFilters : undefined
    })
  }

  const removeAdvancedFilter = (category: string, value: string) => {
    const advFilters = { ...(filters.advanced_filters || {}) }
    const current = advFilters[category] || []
    const updated = current.filter(v => v !== value)

    if (updated.length > 0) {
      advFilters[category] = updated
    } else {
      delete advFilters[category]
    }

    onChange({
      ...filters,
      advanced_filters: Object.keys(advFilters).length > 0 ? advFilters : undefined
    })
  }

  const getSelectedValues = (sectionKey: string, isAdvanced: boolean): string[] => {
    if (isAdvanced) {
      return filters.advanced_filters?.[sectionKey] || []
    }
    return (filters[sectionKey as keyof SearchFilters] as string[]) || []
  }

  const updateSectionSearch = (sectionKey: string, value: string) => {
    setSectionSearches(prev => ({ ...prev, [sectionKey]: value }))
  }

  const toggleSortOrder = (sectionKey: string) => {
    setSortByFrequency(prev => ({ ...prev, [sectionKey]: !prev[sectionKey] }))
  }

  // Filter and sort options based on search text and sort preference
  const getFilteredAndSortedOptions = (sectionKey: string, allOptions: { value: string; count: number }[]) => {
    const searchText = sectionSearches[sectionKey]?.toLowerCase() || ''
    const isSortedByFrequency = sortByFrequency[sectionKey] || false

    let filtered = allOptions
    if (searchText) {
      filtered = allOptions.filter(opt => opt.value.toLowerCase().includes(searchText))
    }

    if (isSortedByFrequency) {
      return [...filtered].sort((a, b) => b.count - a.count)
    } else {
      return [...filtered].sort((a, b) => a.value.localeCompare(b.value))
    }
  }

  // Collect all active filters for the badge display
  const activeFilters: { section: string; value: string; label: string; isAdvanced: boolean }[] = []
  coreFilterSections.forEach(section => {
    const values = (filters[section.key as keyof SearchFilters] as string[]) || []
    values.forEach(value => {
      activeFilters.push({ section: section.key, value, label: section.label, isAdvanced: false })
    })
  })
  // Advanced filters
  if (filters.advanced_filters) {
    for (const [catKey, values] of Object.entries(filters.advanced_filters)) {
      const label = CATEGORY_LABEL_MAP.get(catKey) || catKey
      values.forEach(value => {
        activeFilters.push({ section: catKey, value, label, isAdvanced: true })
      })
    }
  }

  // Render a filter card (shared between core and advanced)
  const renderFilterCard = (
    section: { key: string; label: string; options: { value: string; count: number }[]; searchable: boolean },
    isAdvanced: boolean
  ) => {
    const selected = getSelectedValues(section.key, isAdvanced)
    const selectedCount = selected.length
    const searchText = sectionSearches[section.key] || ''
    const isSortedByFrequency = sortByFrequency[section.key] || false
    const sortedOptions = getFilteredAndSortedOptions(section.key, section.options)

    const handleToggle = (value: string) => {
      if (isAdvanced) {
        toggleAdvancedFilter(section.key, value)
      } else {
        toggleFilter(section.key as keyof SearchFilters, value)
      }
    }

    return (
      <div key={section.key} className="bg-slate-50 rounded-xl p-4 min-h-[300px] min-w-[180px]">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-700">
            {section.label}
            {selectedCount > 0 && (
              <span className="px-2 py-0.5 bg-primary-500 text-white text-xs rounded-full">
                {selectedCount}
              </span>
            )}
            <span className="text-xs font-normal text-slate-400">
              ({sortedOptions.length})
            </span>
          </div>
          <button
            onClick={() => toggleSortOrder(section.key)}
            className={`p-1.5 rounded-lg transition-colors ${
              isSortedByFrequency ? 'bg-primary-100 text-primary-600' : 'hover:bg-slate-200 text-slate-500'
            }`}
            title={isSortedByFrequency ? 'Sorted by frequency (click for A-Z)' : 'Sorted A-Z (click for frequency)'}
          >
            {isSortedByFrequency ? (
              <Hash className="w-4 h-4" />
            ) : (
              <ArrowDownAZ className="w-4 h-4" />
            )}
          </button>
        </div>

        {/* Search input for searchable sections */}
        {section.searchable && (
          <div className="relative mb-2">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder={`Search ${section.label.toLowerCase()}s...`}
              value={searchText}
              onChange={(e) => updateSectionSearch(section.key, e.target.value)}
              className="w-full pl-9 pr-3 py-2 bg-white border border-slate-200 rounded-lg text-sm text-slate-700 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
            />
            {searchText && (
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  updateSectionSearch(section.key, '')
                }}
                className="absolute right-3 top-1/2 -translate-y-1/2 p-0.5 hover:bg-slate-100 rounded"
              >
                <X className="w-3 h-3 text-slate-400" />
              </button>
            )}
          </div>
        )}

        {/* Options list - always visible, scrollable, fixed height to prevent layout shift */}
        <div className="space-y-1 min-h-[200px] max-h-[200px] overflow-y-auto">
          {sortedOptions.length > 0 ? (
            sortedOptions.map(option => {
              const isSelected = selected.includes(option.value)

              return (
                <button
                  key={option.value}
                  onClick={() => handleToggle(option.value)}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-all ${
                    isSelected
                      ? 'bg-primary-500 text-white'
                      : 'hover:bg-white text-slate-600'
                  }`}
                >
                  <span className="truncate pr-2">{option.value}</span>
                  <span className={`flex items-center gap-1 flex-shrink-0 ${isSelected ? 'text-primary-100' : 'text-slate-400'}`}>
                    <span className="text-xs">{option.count}</span>
                    {isSelected && <Check className="w-3.5 h-3.5" />}
                  </span>
                </button>
              )
            })
          ) : (
            <p className="px-3 py-4 text-xs text-slate-400 text-center">
              No matches found{searchText ? ` for "${searchText}"` : ''}
            </p>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="mt-4 pt-4 border-t border-slate-200 w-full">
      {/* Active Filters Display */}
      {activeFilters.length > 0 && (
        <div className="mb-4 flex flex-wrap gap-2">
          {activeFilters.map(({ section, value, label, isAdvanced }) => (
            <span
              key={`${section}-${value}`}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm ${
                isAdvanced
                  ? 'bg-violet-50 text-violet-700'
                  : 'bg-primary-50 text-primary-700'
              }`}
            >
              <span className={isAdvanced ? 'text-violet-400' : 'text-primary-400'}>{label}:</span>
              <span className="font-medium">{value}</span>
              <button
                onClick={() => isAdvanced ? removeAdvancedFilter(section, value) : removeFilter(section as keyof SearchFilters, value)}
                className={`ml-1 p-0.5 rounded-full transition-colors ${
                  isAdvanced ? 'hover:bg-violet-100' : 'hover:bg-primary-100'
                }`}
              >
                <X className="w-3 h-3" />
              </button>
            </span>
          ))}
        </div>
      )}

      {/* Core Filter Sections (8 tags) - fixed 4-column grid that won't collapse */}
      <div className="w-full grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-4">
        {coreFilterSections.map(section => renderFilterCard(section, false))}
      </div>

      {/* Advanced Filter Cards (dynamically added) */}
      {advancedFilterSections.length > 0 && (
        <div className="mt-4 w-full grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-4">
          {advancedFilterSections.map(section => renderFilterCard(section, true))}
        </div>
      )}

      {/* Performance Data and Sample Size Filters */}
      <div className="mt-4 flex items-center gap-4">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={filters.has_performance_data === true}
            onChange={(e) => onChange({
              ...filters,
              has_performance_data: e.target.checked ? true : undefined
            })}
            className="w-4 h-4 rounded border-slate-300 text-primary-500 focus:ring-primary-500"
          />
          <span className="text-sm text-slate-600">Only questions with Pre- AND Post-Test Data</span>
        </label>

        <label className="flex items-center gap-2">
          <span className="text-sm text-slate-600">Min Sample Size:</span>
          <select
            value={filters.min_sample_size || ''}
            onChange={(e) => onChange({
              ...filters,
              min_sample_size: e.target.value ? parseInt(e.target.value) : undefined
            })}
            className="px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
          >
            <option value="">Any</option>
            <option value="10">10+</option>
            <option value="25">25+</option>
            <option value="50">50+</option>
            <option value="75">75+</option>
            <option value="100">100+</option>
          </select>
        </label>

        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={filters.exclude_numeric === true}
            onChange={(e) => onChange({
              ...filters,
              exclude_numeric: e.target.checked ? true : undefined
            })}
            className="w-4 h-4 rounded border-slate-300 text-primary-500 focus:ring-primary-500"
          />
          <span className="text-sm text-slate-600">Hide numeric questions</span>
        </label>

        <label className="flex items-center gap-2">
          <span className="text-sm text-slate-600">Tag Status:</span>
          <select
            value={filters.tag_status_filter || ''}
            onChange={(e) => onChange({
              ...filters,
              tag_status_filter: e.target.value || undefined
            })}
            className="px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
          >
            <option value="">Any</option>
            <option value="verified_only">Verified Only</option>
            <option value="verified_or_unanimous">Verified or Unanimous</option>
            <option value="verified_unanimous_majority">Verified, Unanimous, or Majority</option>
          </select>
        </label>
      </div>
    </div>
  )
}
