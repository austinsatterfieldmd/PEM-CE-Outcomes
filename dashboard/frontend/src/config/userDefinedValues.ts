/**
 * User-Defined Values Module
 *
 * Manages custom values that users have entered via "Other..." in dropdown fields.
 * These values are persisted to the database and merged with static canonical values
 * to provide a seamless dropdown experience.
 *
 * Usage:
 *   1. Call loadUserDefinedValues() on app init to fetch from backend
 *   2. Call getUserDefinedValuesForField(fieldName) to get custom values for a field
 *   3. Call detectCustomValues(editedTags, originalTags) to find new custom values
 */

import { getUserDefinedValues } from '../services/apiRouter'
import { FIELD_GUIDANCE } from './fieldGuidance'

// In-memory cache of user-defined values
let userDefinedValuesCache: Record<string, string[]> = {}
let isLoaded = false
let loadPromise: Promise<void> | null = null

/**
 * Load user-defined values from the backend.
 * Safe to call multiple times - will only fetch once.
 */
export async function loadUserDefinedValues(): Promise<void> {
  if (isLoaded) return

  if (loadPromise) {
    return loadPromise
  }

  loadPromise = (async () => {
    try {
      userDefinedValuesCache = await getUserDefinedValues()
      isLoaded = true
      console.log('Loaded user-defined values:', Object.keys(userDefinedValuesCache).length, 'fields')
    } catch (error) {
      console.warn('Failed to load user-defined values:', error)
      // Don't fail - just use empty cache
      userDefinedValuesCache = {}
      isLoaded = true
    }
  })()

  return loadPromise
}

/**
 * Get user-defined values for a specific field.
 */
export function getUserDefinedValuesForField(fieldName: string): string[] {
  // Also check the base field name for numbered fields (treatment_2 -> treatment_1)
  const baseFieldName = getBaseFieldName(fieldName)

  const values = new Set<string>()

  // Add values from the exact field
  if (userDefinedValuesCache[fieldName]) {
    userDefinedValuesCache[fieldName].forEach(v => values.add(v))
  }

  // Add values from the base field (e.g., treatment_1 values apply to treatment_2)
  if (baseFieldName !== fieldName && userDefinedValuesCache[baseFieldName]) {
    userDefinedValuesCache[baseFieldName].forEach(v => values.add(v))
  }

  return Array.from(values).sort()
}

/**
 * Get the base field name for numbered fields.
 * E.g., treatment_2 -> treatment_1
 */
function getBaseFieldName(fieldName: string): string {
  const match = fieldName.match(/^(.+)_([2-9]|\d{2,})$/)
  if (match) {
    return `${match[1]}_1`
  }
  return fieldName
}

/**
 * Get static allowed values for a field from field guidance.
 */
function getStaticAllowedValues(fieldName: string): string[] {
  const baseFieldName = getBaseFieldName(fieldName)

  const fieldGuidance = FIELD_GUIDANCE[fieldName]
  const baseGuidance = FIELD_GUIDANCE[baseFieldName]

  if (fieldGuidance?.allowedValues && fieldGuidance.allowedValues.length > 0) {
    return fieldGuidance.allowedValues
  }
  if (baseGuidance?.allowedValues && baseGuidance.allowedValues.length > 0) {
    return baseGuidance.allowedValues
  }

  return []
}

/**
 * Get all values for a field (static + user-defined).
 */
export function getAllValuesForField(fieldName: string): string[] {
  const staticValues = getStaticAllowedValues(fieldName)
  const userValues = getUserDefinedValuesForField(fieldName)

  // Merge and dedupe
  const allValues = new Set<string>(staticValues)
  userValues.forEach(v => allValues.add(v))

  return Array.from(allValues).sort()
}

/**
 * Check if a value is a custom value (not in static allowed values).
 */
export function isCustomValue(fieldName: string, value: string): boolean {
  if (!value || !value.trim()) return false

  const staticValues = getStaticAllowedValues(fieldName)
  return staticValues.length > 0 && !staticValues.includes(value)
}

/**
 * Detect custom values in the edited tags that need to be persisted.
 * Returns a list of {field_name, value} objects for values that are:
 *   1. Not in the static allowed values
 *   2. Not already in the user-defined values cache
 *
 * @param editedTags - The tags being saved
 */
export function detectCustomValues(
  editedTags: { [key: string]: string | boolean | number | null | undefined }
): Array<{ field_name: string; value: string }> {
  const customValues: Array<{ field_name: string; value: string }> = []

  for (const [fieldName, value] of Object.entries(editedTags)) {
    // Only check string values
    if (typeof value !== 'string' || !value.trim()) continue

    // Check if this field has static allowed values
    const staticValues = getStaticAllowedValues(fieldName)
    if (staticValues.length === 0) continue // Free-text field, no need to persist

    // Check if the value is custom (not in static or already in user-defined)
    if (!staticValues.includes(value)) {
      const existingUserValues = getUserDefinedValuesForField(fieldName)
      if (!existingUserValues.includes(value)) {
        customValues.push({ field_name: fieldName, value })
      }
    }
  }

  return customValues
}

/**
 * Add a value to the local cache (called after successful save).
 * This keeps the cache in sync without needing to refetch.
 */
export function addToLocalCache(fieldName: string, value: string): void {
  if (!userDefinedValuesCache[fieldName]) {
    userDefinedValuesCache[fieldName] = []
  }
  if (!userDefinedValuesCache[fieldName].includes(value)) {
    userDefinedValuesCache[fieldName].push(value)
    userDefinedValuesCache[fieldName].sort()
  }
}

/**
 * Force reload user-defined values from the backend.
 */
export async function reloadUserDefinedValues(): Promise<void> {
  isLoaded = false
  loadPromise = null
  await loadUserDefinedValues()
}

/**
 * Check if values have been loaded.
 */
export function isUserDefinedValuesLoaded(): boolean {
  return isLoaded
}
