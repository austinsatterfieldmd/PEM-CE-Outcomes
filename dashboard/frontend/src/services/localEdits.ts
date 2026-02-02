/**
 * Local Edit Tracking Service
 *
 * Stores tag edits in browser localStorage for Vercel deployment.
 * Edits can be exported as JSON and manually applied to the database.
 */

const STORAGE_KEY = 'ce_dashboard_pending_edits'
const CUSTOM_VALUES_KEY = 'ce_dashboard_custom_values'

export interface LocalEdit {
  id: string  // unique edit ID
  questionId: number
  timestamp: string  // ISO date
  editor: string  // user email or name
  changes: Record<string, string | null>  // field -> new value
  previousValues?: Record<string, string | null>  // field -> old value (for review)
  markAsReviewed?: boolean
  questionStem?: string  // if question stem was edited
}

export interface PendingEdits {
  version: string
  exportedAt?: string
  edits: LocalEdit[]
}

/**
 * Get all pending edits from localStorage
 */
export function getPendingEdits(): LocalEdit[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (!stored) return []
    const data = JSON.parse(stored) as PendingEdits
    return data.edits || []
  } catch (error) {
    console.error('Failed to load pending edits:', error)
    return []
  }
}

/**
 * Save a new edit to localStorage
 */
export function saveLocalEdit(edit: Omit<LocalEdit, 'id' | 'timestamp'>): LocalEdit {
  const edits = getPendingEdits()

  const newEdit: LocalEdit = {
    ...edit,
    id: `edit_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
    timestamp: new Date().toISOString()
  }

  // Check if there's already an edit for this question - merge them
  const existingIndex = edits.findIndex(e => e.questionId === edit.questionId)
  if (existingIndex >= 0) {
    // Merge with existing edit
    const existing = edits[existingIndex]
    newEdit.previousValues = {
      ...existing.previousValues,
      ...edit.previousValues
    }
    newEdit.changes = {
      ...existing.changes,
      ...edit.changes
    }
    // Update existing edit
    edits[existingIndex] = newEdit
  } else {
    edits.push(newEdit)
  }

  const data: PendingEdits = {
    version: '1.0',
    edits
  }

  localStorage.setItem(STORAGE_KEY, JSON.stringify(data))

  // Dispatch custom event for components to react
  window.dispatchEvent(new CustomEvent('localEditsChanged', { detail: { count: edits.length } }))

  return newEdit
}

/**
 * Get count of pending edits
 */
export function getPendingEditCount(): number {
  return getPendingEdits().length
}

/**
 * Get all unique question IDs that have pending edits
 */
export function getEditedQuestionIds(): Set<number> {
  const edits = getPendingEdits()
  return new Set(edits.map(e => e.questionId))
}

/**
 * Get the pending edit for a specific question (if any)
 */
export function getPendingEditForQuestion(questionId: number): LocalEdit | null {
  const edits = getPendingEdits()
  return edits.find(e => e.questionId === questionId) || null
}

/**
 * Apply pending edits to question data (for display)
 * This merges local edits with server data so the UI shows updated values
 */
export function applyPendingEditsToTags(questionId: number, tags: Record<string, any>): Record<string, any> {
  const edit = getPendingEditForQuestion(questionId)
  if (!edit) return tags

  // Merge the changes into the tags
  return {
    ...tags,
    ...edit.changes
  }
}

/**
 * Export all pending edits as a downloadable JSON file
 */
export function exportPendingEdits(): void {
  const edits = getPendingEdits()

  if (edits.length === 0) {
    alert('No pending edits to export.')
    return
  }

  const exportData: PendingEdits = {
    version: '1.0',
    exportedAt: new Date().toISOString(),
    edits
  }

  const json = JSON.stringify(exportData, null, 2)
  const blob = new Blob([json], { type: 'application/json' })
  const url = URL.createObjectURL(blob)

  const link = document.createElement('a')
  link.href = url
  link.download = `ce_dashboard_edits_${new Date().toISOString().split('T')[0]}.json`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

/**
 * Clear all pending edits (use after successful import)
 */
export function clearPendingEdits(): void {
  localStorage.removeItem(STORAGE_KEY)
  window.dispatchEvent(new CustomEvent('localEditsChanged', { detail: { count: 0 } }))
}

/**
 * Remove a specific edit by question ID
 */
export function removePendingEdit(questionId: number): void {
  const edits = getPendingEdits()
  const filtered = edits.filter(e => e.questionId !== questionId)

  const data: PendingEdits = {
    version: '1.0',
    edits: filtered
  }

  localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
  window.dispatchEvent(new CustomEvent('localEditsChanged', { detail: { count: filtered.length } }))
}

// ============== Custom Values Storage ==============

/**
 * Store user-defined custom values locally (for Vercel mode)
 */
export function saveLocalCustomValue(fieldName: string, value: string): void {
  try {
    const stored = localStorage.getItem(CUSTOM_VALUES_KEY)
    const data: Record<string, string[]> = stored ? JSON.parse(stored) : {}

    if (!data[fieldName]) {
      data[fieldName] = []
    }

    if (!data[fieldName].includes(value)) {
      data[fieldName].push(value)
    }

    localStorage.setItem(CUSTOM_VALUES_KEY, JSON.stringify(data))
  } catch (error) {
    console.error('Failed to save custom value:', error)
  }
}

/**
 * Get locally stored custom values for a field
 */
export function getLocalCustomValues(fieldName: string): string[] {
  try {
    const stored = localStorage.getItem(CUSTOM_VALUES_KEY)
    if (!stored) return []
    const data: Record<string, string[]> = JSON.parse(stored)
    return data[fieldName] || []
  } catch (error) {
    console.error('Failed to load custom values:', error)
    return []
  }
}

/**
 * Get all locally stored custom values
 */
export function getAllLocalCustomValues(): Record<string, string[]> {
  try {
    const stored = localStorage.getItem(CUSTOM_VALUES_KEY)
    return stored ? JSON.parse(stored) : {}
  } catch (error) {
    console.error('Failed to load custom values:', error)
    return {}
  }
}

// ============== Vercel Mode Detection ==============

let isVercelModeCache: boolean | null = null

/**
 * Check if running in Vercel (read-only) mode
 * This is detected by checking if the backend API is unavailable
 */
export async function checkVercelMode(): Promise<boolean> {
  if (isVercelModeCache !== null) {
    return isVercelModeCache
  }

  try {
    // Try a simple health check to the API
    const response = await fetch('/api/questions/stats/summary', {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    })

    // If we get a 404 or other error, we're in Vercel mode
    isVercelModeCache = !response.ok
    return isVercelModeCache
  } catch (error) {
    // Network error means we're in Vercel mode (static hosting)
    isVercelModeCache = true
    return true
  }
}

/**
 * Manually set Vercel mode (for testing or override)
 */
export function setVercelMode(enabled: boolean): void {
  isVercelModeCache = enabled
}

/**
 * Get cached Vercel mode status (synchronous)
 */
export function isVercelMode(): boolean {
  return isVercelModeCache ?? false
}
