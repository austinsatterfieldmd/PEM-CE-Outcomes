// Canonical values for tag fields - uses fieldGuidance.ts as source of truth
// All fields with allowedValues get dropdown_other (dropdown + free text "Other" option)
// User-defined values (from "Other..." entries) are merged with static values

import { FIELD_GUIDANCE } from './fieldGuidance'
import { getUserDefinedValuesForField } from './userDefinedValues'

export type InputType = 'dropdown' | 'dropdown_other' | 'autocomplete' | 'text'

export interface FieldConfig {
  inputType: InputType
  values?: string[]  // For dropdown and dropdown_other
  suggestions?: string[]  // For autocomplete (unused, now use dropdown_other)
  allowEmpty?: boolean
}

// Strict dropdown fields - ONLY these values allowed (no "Other" option)
const STRICT_DROPDOWN_FIELDS = new Set([
  // topic - allow custom values (new educational themes may emerge)
  'disease_stage',  // Must match staging conventions
  'treatment_line',  // Must match line conventions
  'age_group',
  'performance_status',
  'fitness_status',
  'organ_dysfunction',
  'treatment_eligibility',
  // toxicity_organ - allow custom values (other organ systems)
  'toxicity_grade',
  // outcome_context - allow custom values (other analysis types)
  // clinical_benefit - allow custom values (other benefit descriptors)
  // evidence_type - allow custom values (other study types)
  // guideline_source_1/2 - allow custom values (regional guidelines, etc.)
  'cme_outcome_level',
  'data_response_type',
  'stem_type',
  'lead_in_type',
  'answer_format',
  'answer_length_pattern',
  'distractor_homogeneity',
])

// Fields that should use pure text input (no dropdown)
const TEXT_ONLY_FIELDS = new Set([
  // Rare fields that benefit from free text entry
  'disease_state_2',  // Secondary disease state (rare, avoids dropdown timing issues)
  // Boolean flaw fields - not editable
  'flaw_absolute_terms',
  'flaw_grammatical_cue',
  'flaw_implausible_distractor',
  'flaw_clang_association',
  'flaw_convergence_vulnerability',
  'flaw_double_negative',
  // Computed fields - not editable
  'answer_option_count',
  'correct_answer_position',
])

// Helper to get values from fieldGuidance for a base field (treatment_1 -> treatment_1)
function getBaseFieldName(fieldName: string): string {
  // For numbered fields like treatment_2, get treatment_1
  const match = fieldName.match(/^(.+)_([2-9]|\d{2,})$/)
  if (match) {
    return `${match[1]}_1`
  }
  return fieldName
}

// Helper function to get field configuration
export function getFieldConfig(fieldName: string): FieldConfig {
  // Check if it's a text-only field
  if (TEXT_ONLY_FIELDS.has(fieldName)) {
    return {
      inputType: 'text',
      allowEmpty: true,
    }
  }

  // Get the base field name for numbered fields
  const baseFieldName = getBaseFieldName(fieldName)

  // Get guidance info for this field, then fall back to base field
  const fieldGuidance = FIELD_GUIDANCE[fieldName]
  const baseGuidance = FIELD_GUIDANCE[baseFieldName]

  // Get allowedValues - prefer field's own values, but inherit from base if empty
  let staticValues: string[] = []
  if (fieldGuidance?.allowedValues && fieldGuidance.allowedValues.length > 0) {
    staticValues = fieldGuidance.allowedValues
  } else if (baseGuidance?.allowedValues && baseGuidance.allowedValues.length > 0) {
    staticValues = baseGuidance.allowedValues
  }

  // Merge with user-defined values (custom values users have entered via "Other...")
  const userValues = getUserDefinedValuesForField(fieldName)
  const allowedValues = staticValues.length > 0
    ? [...new Set([...staticValues, ...userValues])].sort()
    : userValues

  if (!fieldGuidance && !baseGuidance) {
    // No guidance found, use text input
    return {
      inputType: 'text',
      allowEmpty: true,
    }
  }

  // Check if field has allowedValues (either its own or inherited from base)
  if (allowedValues.length > 0) {
    // Check if it's a strict dropdown (no "Other" option)
    if (STRICT_DROPDOWN_FIELDS.has(fieldName) || STRICT_DROPDOWN_FIELDS.has(baseFieldName)) {
      return {
        inputType: 'dropdown',
        values: allowedValues,
        allowEmpty: true,
      }
    }

    // Otherwise use dropdown with "Other" option
    return {
      inputType: 'dropdown_other',
      values: allowedValues,
      allowEmpty: true,
    }
  }

  // Fallback to text input
  return {
    inputType: 'text',
    allowEmpty: true,
  }
}

// Get suggestions for autocomplete/dropdown fields
export function getFieldSuggestions(fieldName: string): string[] {
  const config = getFieldConfig(fieldName)
  return config.values || []
}
