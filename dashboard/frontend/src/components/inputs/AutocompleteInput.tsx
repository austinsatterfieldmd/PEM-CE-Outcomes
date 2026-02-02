import { useState, useRef, useEffect } from 'react'

interface AutocompleteInputProps {
  value: string
  suggestions: string[]
  onChange: (value: string) => void
  placeholder?: string
  className?: string
}

export function AutocompleteInput({
  value,
  suggestions,
  onChange,
  placeholder = 'Type to search...',
  className = '',
}: AutocompleteInputProps) {
  const [inputValue, setInputValue] = useState(value)
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [filteredSuggestions, setFilteredSuggestions] = useState<string[]>([])
  const [highlightedIndex, setHighlightedIndex] = useState(-1)
  const inputRef = useRef<HTMLInputElement>(null)
  const suggestionsRef = useRef<HTMLDivElement>(null)

  // Sync input value with prop
  useEffect(() => {
    setInputValue(value)
  }, [value])

  // Filter suggestions based on input
  useEffect(() => {
    if (inputValue.trim() === '') {
      setFilteredSuggestions([])
      return
    }

    const lowerInput = inputValue.toLowerCase()
    const filtered = suggestions.filter(s =>
      s.toLowerCase().includes(lowerInput)
    ).slice(0, 10) // Limit to 10 suggestions

    setFilteredSuggestions(filtered)
    setHighlightedIndex(-1)
  }, [inputValue, suggestions])

  // Handle click outside to close suggestions
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        suggestionsRef.current &&
        !suggestionsRef.current.contains(e.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(e.target as Node)
      ) {
        setShowSuggestions(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value
    setInputValue(newValue)
    setShowSuggestions(true)
    onChange(newValue)
  }

  const handleSelectSuggestion = (suggestion: string) => {
    setInputValue(suggestion)
    onChange(suggestion)
    setShowSuggestions(false)
    setHighlightedIndex(-1)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!showSuggestions || filteredSuggestions.length === 0) return

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setHighlightedIndex(prev =>
          prev < filteredSuggestions.length - 1 ? prev + 1 : 0
        )
        break
      case 'ArrowUp':
        e.preventDefault()
        setHighlightedIndex(prev =>
          prev > 0 ? prev - 1 : filteredSuggestions.length - 1
        )
        break
      case 'Enter':
        e.preventDefault()
        if (highlightedIndex >= 0) {
          handleSelectSuggestion(filteredSuggestions[highlightedIndex])
        }
        break
      case 'Escape':
        setShowSuggestions(false)
        setHighlightedIndex(-1)
        break
    }
  }

  const handleFocus = () => {
    if (inputValue.trim() !== '' && filteredSuggestions.length > 0) {
      setShowSuggestions(true)
    }
  }

  const handleBlur = () => {
    // Delay hiding to allow click on suggestion
    setTimeout(() => {
      setShowSuggestions(false)
    }, 200)
  }

  return (
    <div className={`relative ${className}`}>
      <input
        ref={inputRef}
        type="text"
        value={inputValue}
        onChange={handleInputChange}
        onKeyDown={handleKeyDown}
        onFocus={handleFocus}
        onBlur={handleBlur}
        placeholder={placeholder}
        className="w-full px-3 py-1.5 border border-slate-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
      />

      {showSuggestions && filteredSuggestions.length > 0 && (
        <div
          ref={suggestionsRef}
          className="absolute z-50 w-full mt-1 bg-white border border-slate-200 rounded-md shadow-lg max-h-60 overflow-y-auto"
        >
          {filteredSuggestions.map((suggestion, index) => (
            <button
              key={suggestion}
              type="button"
              onClick={() => handleSelectSuggestion(suggestion)}
              className={`w-full px-3 py-2 text-left text-sm hover:bg-blue-50 ${
                index === highlightedIndex ? 'bg-blue-100' : ''
              }`}
            >
              {highlightMatch(suggestion, inputValue)}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

// Highlight matching text in suggestions
function highlightMatch(text: string, query: string) {
  if (!query.trim()) return text

  const lowerText = text.toLowerCase()
  const lowerQuery = query.toLowerCase()
  const startIndex = lowerText.indexOf(lowerQuery)

  if (startIndex === -1) return text

  const beforeMatch = text.slice(0, startIndex)
  const match = text.slice(startIndex, startIndex + query.length)
  const afterMatch = text.slice(startIndex + query.length)

  return (
    <>
      {beforeMatch}
      <span className="font-semibold text-blue-600">{match}</span>
      {afterMatch}
    </>
  )
}
