import { useState, useRef } from 'react'
import { ChevronDown } from 'lucide-react'

interface DropdownWithOtherProps {
  value: string
  options: string[]
  onChange: (value: string) => void
  placeholder?: string
  className?: string
}

// Find the closest scrollable parent element
function findScrollableParent(element: HTMLElement | null): HTMLElement | null {
  while (element) {
    const style = window.getComputedStyle(element)
    const overflowY = style.overflowY
    if (overflowY === 'auto' || overflowY === 'scroll') {
      return element
    }
    element = element.parentElement
  }
  return null
}

export function DropdownWithOther({
  value,
  options,
  onChange,
  placeholder = 'Select...',
  className = '',
}: DropdownWithOtherProps) {
  // Track if user explicitly clicked "Other..." to enter a new custom value
  // This is DIFFERENT from having an existing custom value - those show in the dropdown
  const [isEnteringCustom, setIsEnteringCustom] = useState(false)
  const [customInputValue, setCustomInputValue] = useState('')
  // Track the value before entering "Other" mode so we can revert on Cancel
  const valueBeforeOther = useRef<string>(value)
  // Track if we're clicking Cancel to prevent blur from committing
  const isCancellingRef = useRef(false)
  // Ref to the select element for scroll position preservation
  const selectRef = useRef<HTMLSelectElement>(null)

  // Check if current value is custom (not in options list and not empty)
  const isCustomValue = value !== '' && !options.includes(value)

  const handleSelectChange = (newValue: string) => {
    // Save scroll position before any state changes
    const scrollContainer = findScrollableParent(selectRef.current)
    const scrollTop = scrollContainer?.scrollTop ?? 0

    if (newValue === '__other__') {
      // Save current value before entering Other mode
      valueBeforeOther.current = value
      setIsEnteringCustom(true)
      setCustomInputValue('')
    } else if (newValue === '__current_custom__') {
      // User selected the existing custom value, no change needed
    } else {
      setIsEnteringCustom(false)
      setCustomInputValue('')
      onChange(newValue)

      // Restore scroll position after React re-renders
      if (scrollContainer) {
        requestAnimationFrame(() => {
          scrollContainer.scrollTop = scrollTop
        })
      }
    }
  }

  const handleCustomInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    // Only update local state - don't call onChange on every keystroke
    // The value will be committed on blur or Enter
    setCustomInputValue(e.target.value)
  }

  const commitCustomValue = () => {
    if (customInputValue.trim() !== '') {
      onChange(customInputValue)
    } else {
      // Empty value, revert to previous
      onChange(valueBeforeOther.current)
    }
    setIsEnteringCustom(false)
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      commitCustomValue()
    } else if (e.key === 'Escape') {
      e.preventDefault()
      handleCancel()
    }
  }

  const handleBlur = () => {
    // Don't commit if Cancel button was clicked
    if (isCancellingRef.current) {
      isCancellingRef.current = false
      return
    }
    commitCustomValue()
  }

  const handleCancel = () => {
    // Revert to the value before entering "Other" mode
    isCancellingRef.current = true
    setIsEnteringCustom(false)
    setCustomInputValue('')
    onChange(valueBeforeOther.current)
  }

  // Only show custom input + Cancel when user explicitly clicked "Other..."
  if (isEnteringCustom) {
    return (
      <div className={`flex gap-2 ${className}`}>
        <input
          type="text"
          value={customInputValue}
          onChange={handleCustomInputChange}
          onKeyDown={handleKeyDown}
          onBlur={handleBlur}
          placeholder="Enter custom value..."
          className="flex-1 px-3 py-1.5 border border-slate-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          autoFocus
        />
        <button
          type="button"
          onMouseDown={() => { isCancellingRef.current = true }}
          onClick={handleCancel}
          className="px-2 py-1 text-xs text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded"
        >
          Cancel
        </button>
      </div>
    )
  }

  return (
    <div className={`relative ${className}`}>
      <select
        ref={selectRef}
        value={isCustomValue ? '__current_custom__' : value}
        onChange={(e) => handleSelectChange(e.target.value)}
        className="w-full px-3 py-1.5 pr-8 border border-slate-300 rounded-md bg-white text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent appearance-none cursor-pointer"
      >
        <option value="">{placeholder}</option>
        {/* "Other (custom value)..." always at top for consistency */}
        <option value="__other__">Other (custom value)...</option>
        {/* Show current custom value if it exists */}
        {isCustomValue && (
          <option value="__current_custom__">{value}</option>
        )}
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
      <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400 pointer-events-none" />
    </div>
  )
}
