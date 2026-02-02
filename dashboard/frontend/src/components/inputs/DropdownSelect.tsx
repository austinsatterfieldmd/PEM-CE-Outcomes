import { ChevronDown } from 'lucide-react'

interface DropdownSelectProps {
  value: string
  options: string[]
  onChange: (value: string) => void
  placeholder?: string
  allowEmpty?: boolean
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

export function DropdownSelect({
  value,
  options,
  onChange,
  placeholder = 'Select...',
  allowEmpty = true,
  className = '',
}: DropdownSelectProps) {
  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    // Find the scrollable container and save its scroll position
    const scrollContainer = findScrollableParent(e.target)
    const scrollTop = scrollContainer?.scrollTop ?? 0

    // Call the onChange handler
    onChange(e.target.value)

    // Restore scroll position after React re-renders
    if (scrollContainer) {
      requestAnimationFrame(() => {
        scrollContainer.scrollTop = scrollTop
      })
    }
  }

  return (
    <div className={`relative ${className}`}>
      <select
        value={value}
        onChange={handleChange}
        className="w-full px-3 py-1.5 pr-8 border border-slate-300 rounded-md bg-white text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent appearance-none cursor-pointer"
      >
        {allowEmpty && (
          <option value="">{placeholder}</option>
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
