import { useEffect, useState, memo, useMemo } from 'react'
import { X, Check, AlertCircle, Tag, Activity, FileText, TrendingUp, Pencil, Save, XCircle, AlertTriangle, CheckCircle, ChevronDown, ChevronRight, HelpCircle, Database } from 'lucide-react'
import { getQuestionDetail, updateQuestionTags, updateOncologyStatus, markDataError } from '../services/api'
import type { QuestionDetailData } from '../types'
import { FIELD_GROUPS } from '../types'
import { useAuth } from './AuthProvider'
import { FieldGuidanceModal } from './FieldGuidanceModal'
import { DropdownSelect, DropdownWithOther, AutocompleteInput } from './inputs'
import { getFieldConfig, getFieldSuggestions } from '../config/canonicalValues'
import { loadUserDefinedValues, detectCustomValues, addToLocalCache } from '../config/userDefinedValues'

// Stable text input that uses local state to prevent focus loss
// Only syncs with parent on blur or Enter key
interface StableTextInputProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  className?: string
}

const StableTextInput = memo(function StableTextInput({
  value,
  onChange,
  placeholder,
  className
}: StableTextInputProps) {
  const [localValue, setLocalValue] = useState(value)

  // Sync local state when external value changes (e.g., on cancel/reset)
  useEffect(() => {
    setLocalValue(value)
  }, [value])

  const handleBlur = () => {
    if (localValue !== value) {
      onChange(localValue)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      onChange(localValue)
    }
  }

  return (
    <input
      type="text"
      value={localValue}
      onChange={(e) => setLocalValue(e.target.value)}
      onBlur={handleBlur}
      onKeyDown={handleKeyDown}
      className={className}
      placeholder={placeholder}
    />
  )
})

// Stable TagRow component (defined outside to prevent recreation on parent re-render)
interface TagRowProps {
  label: string
  value: string | null | undefined
  confidence?: number | null
  isEditing: boolean
  tagKey: string
  onEdit?: (value: string) => void
  color?: string
  conflictFields?: Set<string>
  majorityFields?: Set<string>
}

const TagRow = memo(function TagRow({
  label,
  value,
  confidence,
  isEditing,
  tagKey,
  onEdit,
  color,
  conflictFields,
  majorityFields
}: TagRowProps) {
  const hasConflict = conflictFields?.has(tagKey) ?? false
  const hasMajority = majorityFields?.has(tagKey) ?? false
  if (!value && !isEditing) return null

  const fieldConfig = getFieldConfig(tagKey)

  // Render the appropriate input type based on field configuration
  const renderInput = () => {
    if (!onEdit) return null

    switch (fieldConfig.inputType) {
      case 'dropdown':
        return (
          <DropdownSelect
            key={`dropdown-${tagKey}`}
            value={value || ''}
            options={fieldConfig.values || []}
            onChange={onEdit}
            placeholder={`Select ${label.toLowerCase()}`}
            className="flex-1"
          />
        )
      case 'dropdown_other':
        return (
          <DropdownWithOther
            key={`dropdown-other-${tagKey}`}
            value={value || ''}
            options={fieldConfig.values || []}
            onChange={onEdit}
            placeholder={`Select ${label.toLowerCase()}`}
            className="flex-1"
          />
        )
      case 'autocomplete':
        return (
          <AutocompleteInput
            key={`autocomplete-${tagKey}`}
            value={value || ''}
            suggestions={getFieldSuggestions(tagKey)}
            onChange={onEdit}
            placeholder={`Enter ${label.toLowerCase()}`}
            className="flex-1"
          />
        )
      default:
        return (
          <StableTextInput
            key={`input-${tagKey}`}
            value={value || ''}
            onChange={onEdit}
            className="flex-1 px-3 py-1.5 border border-slate-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder={`Enter ${label.toLowerCase()}`}
          />
        )
    }
  }

  return (
    <div className="flex items-center justify-between py-2">
      <div className="flex items-center gap-2 min-w-[160px]">
        <span className="text-sm font-medium text-slate-600">{label}:</span>
        {hasConflict && (
          <span className="text-xs px-1.5 py-0.5 rounded bg-red-100 text-red-700 font-medium">
            Conflict
          </span>
        )}
        {hasMajority && !hasConflict && (
          <span className="text-xs px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 font-medium">
            Majority
          </span>
        )}
      </div>
      {isEditing && onEdit ? (
        renderInput()
      ) : (
        <div className="flex-1 flex items-center justify-between">
          <span className={`text-sm px-2 py-0.5 rounded ${color || 'text-slate-900'}`}>
            {value || <span className="text-slate-400 italic">Not set</span>}
          </span>
          {confidence !== undefined && confidence !== null && (
            <span className={`text-xs px-2 py-0.5 rounded ${
              confidence >= 0.7 ? 'bg-green-100 text-green-800' :
              confidence >= 0.4 ? 'bg-yellow-100 text-yellow-800' :
              'bg-red-100 text-red-800'
            }`}>
              {(confidence * 100).toFixed(0)}%
            </span>
          )}
        </div>
      )}
    </div>
  )
})

interface QuestionReviewDetailProps {
  questionId: number
  onClose: () => void
  onReviewComplete?: () => void
}

interface EditableTags {
  // Core fields
  topic: string
  disease_state_1: string  // Primary disease state
  disease_state_2: string  // Secondary disease state (rare: e.g., MM + NHL)
  disease_stage: string
  disease_type_1: string
  disease_type_2: string
  treatment_line: string
  // Multi-value fields
  treatment_1: string
  treatment_2: string
  treatment_3: string
  treatment_4: string
  treatment_5: string
  biomarker_1: string
  biomarker_2: string
  biomarker_3: string
  biomarker_4: string
  biomarker_5: string
  trial_1: string
  trial_2: string
  trial_3: string
  trial_4: string
  trial_5: string
  // Patient Characteristics
  treatment_eligibility: string
  age_group: string
  organ_dysfunction: string
  fitness_status: string
  disease_specific_factor: string
  comorbidity_1: string
  comorbidity_2: string
  comorbidity_3: string
  // Treatment Metadata
  drug_class_1: string
  drug_class_2: string
  drug_class_3: string
  drug_target_1: string
  drug_target_2: string
  drug_target_3: string
  prior_therapy_1: string
  prior_therapy_2: string
  prior_therapy_3: string
  resistance_mechanism: string
  // Clinical Context
  metastatic_site_1: string
  metastatic_site_2: string
  metastatic_site_3: string
  symptom_1: string
  symptom_2: string
  symptom_3: string
  performance_status: string
  // Safety & Toxicity
  toxicity_type_1: string
  toxicity_type_2: string
  toxicity_type_3: string
  toxicity_type_4: string
  toxicity_type_5: string
  toxicity_organ: string
  toxicity_grade: string
  // Efficacy & Outcomes
  efficacy_endpoint_1: string
  efficacy_endpoint_2: string
  efficacy_endpoint_3: string
  outcome_context: string
  clinical_benefit: string
  // Evidence & Guidelines
  guideline_source_1: string
  guideline_source_2: string
  evidence_type: string
  // Question Quality
  cme_outcome_level: string
  data_response_type: string
  stem_type: string
  lead_in_type: string
  answer_format: string
  answer_length_pattern: string
  distractor_homogeneity: string
}

export function QuestionReviewDetail({ questionId, onClose, onReviewComplete }: QuestionReviewDetailProps) {
  const { isAdmin } = useAuth()
  const [data, setData] = useState<QuestionDetailData | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedSegment, setSelectedSegment] = useState<string>('overall')
  const [selectedActivity, setSelectedActivity] = useState<string | null>(null)
  const [isEditing, setIsEditing] = useState(false)
  const [isEditingQuestion, setIsEditingQuestion] = useState(false)
  const [saving, setSaving] = useState(false)
  const [editedQuestionStem, setEditedQuestionStem] = useState('')
  const [showNotOncologyConfirm, setShowNotOncologyConfirm] = useState(false)
  const [showDataErrorConfirm, setShowDataErrorConfirm] = useState(false)
  const [showFieldGuidance, setShowFieldGuidance] = useState(false)
  const [showAgreementLegend, setShowAgreementLegend] = useState(false)
  const [editedTags, setEditedTags] = useState<EditableTags>({
    // Core fields
    topic: '',
    disease_state_1: '',
    disease_state_2: '',
    disease_stage: '',
    disease_type_1: '',
    disease_type_2: '',
    treatment_line: '',
    // Multi-value fields
    treatment_1: '',
    treatment_2: '',
    treatment_3: '',
    treatment_4: '',
    treatment_5: '',
    biomarker_1: '',
    biomarker_2: '',
    biomarker_3: '',
    biomarker_4: '',
    biomarker_5: '',
    trial_1: '',
    trial_2: '',
    trial_3: '',
    trial_4: '',
    trial_5: '',
    // Patient Characteristics
    treatment_eligibility: '',
    age_group: '',
    organ_dysfunction: '',
    fitness_status: '',
    disease_specific_factor: '',
    comorbidity_1: '',
    comorbidity_2: '',
    comorbidity_3: '',
    // Treatment Metadata
    drug_class_1: '',
    drug_class_2: '',
    drug_class_3: '',
    drug_target_1: '',
    drug_target_2: '',
    drug_target_3: '',
    prior_therapy_1: '',
    prior_therapy_2: '',
    prior_therapy_3: '',
    resistance_mechanism: '',
    // Clinical Context
    metastatic_site_1: '',
    metastatic_site_2: '',
    metastatic_site_3: '',
    symptom_1: '',
    symptom_2: '',
    symptom_3: '',
    performance_status: '',
    // Safety & Toxicity
    toxicity_type_1: '',
    toxicity_type_2: '',
    toxicity_type_3: '',
    toxicity_type_4: '',
    toxicity_type_5: '',
    toxicity_organ: '',
    toxicity_grade: '',
    // Efficacy & Outcomes
    efficacy_endpoint_1: '',
    efficacy_endpoint_2: '',
    efficacy_endpoint_3: '',
    outcome_context: '',
    clinical_benefit: '',
    // Evidence & Guidelines
    guideline_source_1: '',
    guideline_source_2: '',
    evidence_type: '',
    // Question Quality
    cme_outcome_level: '',
    data_response_type: '',
    stem_type: '',
    lead_in_type: '',
    answer_format: '',
    answer_length_pattern: '',
    distractor_homogeneity: '',
  })
  // Track which field groups are expanded (core is expanded by default for review)
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set([
    'core', 'multiValue', 'treatmentDetails', 'patientCharacteristics',
    'clinicalContext', 'safetyToxicity', 'efficacyOutcomes', 'evidenceGuidelines', 'questionQuality'
  ]))
  // Review notes for capturing reviewer comments (for few-shot learning)
  const [reviewNotes, setReviewNotes] = useState('')

  // Load user-defined values on mount (for dropdown options)
  useEffect(() => {
    loadUserDefinedValues()
  }, [])

  // Lock body scroll when modal is open
  useEffect(() => {
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = ''
    }
  }, [])

  useEffect(() => {
    setLoading(true)
    getQuestionDetail(questionId)
      .then(result => {
        setData(result)
        // Initialize editable tags and question stem from data
        setEditedTags({
          // Core fields
          topic: result.tags.topic || '',
          disease_state_1: result.tags.disease_state_1 || result.tags.disease_state || '',  // Fallback to legacy disease_state
          disease_state_2: result.tags.disease_state_2 || '',
          disease_stage: result.tags.disease_stage || '',
          disease_type_1: result.tags.disease_type_1 || '',
          disease_type_2: result.tags.disease_type_2 || '',
          treatment_line: result.tags.treatment_line || '',
          // Multi-value fields
          treatment_1: result.tags.treatment_1 || '',
          treatment_2: result.tags.treatment_2 || '',
          treatment_3: result.tags.treatment_3 || '',
          treatment_4: result.tags.treatment_4 || '',
          treatment_5: result.tags.treatment_5 || '',
          biomarker_1: result.tags.biomarker_1 || '',
          biomarker_2: result.tags.biomarker_2 || '',
          biomarker_3: result.tags.biomarker_3 || '',
          biomarker_4: result.tags.biomarker_4 || '',
          biomarker_5: result.tags.biomarker_5 || '',
          trial_1: result.tags.trial_1 || '',
          trial_2: result.tags.trial_2 || '',
          trial_3: result.tags.trial_3 || '',
          trial_4: result.tags.trial_4 || '',
          trial_5: result.tags.trial_5 || '',
          // Patient Characteristics
          treatment_eligibility: result.tags.treatment_eligibility || '',
          age_group: result.tags.age_group || '',
          organ_dysfunction: result.tags.organ_dysfunction || '',
          fitness_status: result.tags.fitness_status || '',
          disease_specific_factor: result.tags.disease_specific_factor || '',
          comorbidity_1: result.tags.comorbidity_1 || '',
          comorbidity_2: result.tags.comorbidity_2 || '',
          comorbidity_3: result.tags.comorbidity_3 || '',
          // Treatment Metadata
          drug_class_1: result.tags.drug_class_1 || '',
          drug_class_2: result.tags.drug_class_2 || '',
          drug_class_3: result.tags.drug_class_3 || '',
          drug_target_1: result.tags.drug_target_1 || '',
          drug_target_2: result.tags.drug_target_2 || '',
          drug_target_3: result.tags.drug_target_3 || '',
          prior_therapy_1: result.tags.prior_therapy_1 || '',
          prior_therapy_2: result.tags.prior_therapy_2 || '',
          prior_therapy_3: result.tags.prior_therapy_3 || '',
          resistance_mechanism: result.tags.resistance_mechanism || '',
          // Clinical Context
          metastatic_site_1: result.tags.metastatic_site_1 || '',
          metastatic_site_2: result.tags.metastatic_site_2 || '',
          metastatic_site_3: result.tags.metastatic_site_3 || '',
          symptom_1: result.tags.symptom_1 || '',
          symptom_2: result.tags.symptom_2 || '',
          symptom_3: result.tags.symptom_3 || '',
          performance_status: result.tags.performance_status || '',
          // Safety & Toxicity
          toxicity_type_1: result.tags.toxicity_type_1 || '',
          toxicity_type_2: result.tags.toxicity_type_2 || '',
          toxicity_type_3: result.tags.toxicity_type_3 || '',
          toxicity_type_4: result.tags.toxicity_type_4 || '',
          toxicity_type_5: result.tags.toxicity_type_5 || '',
          toxicity_organ: result.tags.toxicity_organ || '',
          toxicity_grade: result.tags.toxicity_grade || '',
          // Efficacy & Outcomes
          efficacy_endpoint_1: result.tags.efficacy_endpoint_1 || '',
          efficacy_endpoint_2: result.tags.efficacy_endpoint_2 || '',
          efficacy_endpoint_3: result.tags.efficacy_endpoint_3 || '',
          outcome_context: result.tags.outcome_context || '',
          clinical_benefit: result.tags.clinical_benefit || '',
          // Evidence & Guidelines
          guideline_source_1: result.tags.guideline_source_1 || '',
          guideline_source_2: result.tags.guideline_source_2 || '',
          evidence_type: result.tags.evidence_type || '',
          // Question Quality
          cme_outcome_level: result.tags.cme_outcome_level || '',
          data_response_type: result.tags.data_response_type || '',
          stem_type: result.tags.stem_type || '',
          lead_in_type: result.tags.lead_in_type || '',
          answer_format: result.tags.answer_format || '',
          answer_length_pattern: result.tags.answer_length_pattern || '',
          distractor_homogeneity: result.tags.distractor_homogeneity || '',
        })
        setEditedQuestionStem(result.question_stem)
        setReviewNotes(result.tags?.review_notes || '')
      })
      .catch(err => {
        console.error('Failed to load question details:', err)
      })
      .finally(() => setLoading(false))
  }, [questionId])

  // Save tags and mark as reviewed
  const saveTags = async (markAsReviewed: boolean = false) => {
    if (!data) return

    setSaving(true)
    try {
      // Detect custom values that need to be persisted for future dropdowns
      const customValues = detectCustomValues(editedTags as unknown as { [key: string]: string | boolean | number | null | undefined })

      // Include edited question stem if it was modified
      const payload: Record<string, any> = {
        ...editedTags,
        mark_as_reviewed: markAsReviewed,
        // Send custom values to be persisted in the database
        custom_values: customValues.length > 0 ? customValues : undefined,
        // Review notes (reviewer comments for few-shot learning)
        review_notes: reviewNotes || null
      }
      if (editedQuestionStem !== data.question_stem) {
        payload.question_stem = editedQuestionStem
      }

      const result = await updateQuestionTags(questionId, payload)

      // Update local cache with custom values so they appear immediately in dropdowns
      customValues.forEach(cv => addToLocalCache(cv.field_name, cv.value))

      if (result.savedLocally) {
        // In Vercel mode - don't try to refresh from API
        // Just update local state and close editing mode
        setIsEditing(false)
        setIsEditingQuestion(false)
        if (markAsReviewed && onReviewComplete) {
          onReviewComplete()
        }
      } else {
        // Normal mode - refresh data from API
        const updated = await getQuestionDetail(questionId)
        setData(updated)
        setEditedQuestionStem(updated.question_stem)
        setIsEditing(false)
        setIsEditingQuestion(false)

        if (markAsReviewed && onReviewComplete) {
          onReviewComplete()
        }
      }
    } catch (error) {
      console.error('Failed to save tags:', error)
      alert('Failed to save tags. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  // Save edited question stem
  const saveQuestionStem = async () => {
    if (!data) return

    setSaving(true)
    try {
      await updateQuestionTags(questionId, {
        question_stem: editedQuestionStem
      })

      // Refresh data
      const updated = await getQuestionDetail(questionId)
      setData(updated)
      setIsEditingQuestion(false)
    } catch (error) {
      console.error('Failed to save question:', error)
      alert('Failed to save question. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  // Mark as non-oncology - show confirmation first
  const handleMarkNonOncology = () => {
    setShowNotOncologyConfirm(true)
  }

  // Confirm marking as non-oncology
  const confirmMarkNonOncology = async () => {
    setShowNotOncologyConfirm(false)
    setSaving(true)
    try {
      await updateOncologyStatus(questionId, false)

      // Refresh data and notify parent
      const updated = await getQuestionDetail(questionId)
      setData(updated)

      if (onReviewComplete) {
        onReviewComplete()
      }
    } catch (error) {
      console.error('Failed to update oncology status:', error)
      alert('Failed to update oncology status. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  // Show data error confirmation
  const handleMarkDataError = () => {
    setShowDataErrorConfirm(true)
  }

  // Confirm marking as data error
  const confirmMarkDataError = async () => {
    setShowDataErrorConfirm(false)
    setSaving(true)
    try {
      await markDataError(questionId, 'data_quality', 'Missing or malformed answer options')

      if (onReviewComplete) {
        onReviewComplete()
      }
    } catch (error) {
      console.error('Failed to mark as data error:', error)
      alert('Failed to mark as data error. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  // Mark as reviewed without changes
  const handleMarkAsReviewed = async () => {
    setSaving(true)
    try {
      await updateQuestionTags(questionId, {
        mark_as_reviewed: true
      })

      if (onReviewComplete) {
        onReviewComplete()
      }
    } catch (error) {
      console.error('Failed to mark as reviewed:', error)
      alert('Failed to mark as reviewed. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  // Parse review_reason to get fields with conflicts or majority votes (separately)
  // Memoize to prevent recreating Sets on every render
  // IMPORTANT: Must be before any early returns to satisfy React's rules of hooks
  const { conflictFields, majorityFields } = useMemo(() => {
    const conflicts = new Set<string>()
    const majorities = new Set<string>()

    if (!data?.tags?.review_reason) return { conflictFields: conflicts, majorityFields: majorities }
    const reason = data.tags.review_reason

    // Parse patterns like "conflict_in_fields:symptom_2,treatment_1" or "majority_in_fields:topic"
    const conflictMatch = reason.match(/conflict_in_fields:([^|]+)/)
    const majorityMatch = reason.match(/majority_in_fields:([^|]+)/)

    if (conflictMatch) {
      conflictMatch[1].split(',').forEach(f => conflicts.add(f.trim()))
    }
    if (majorityMatch) {
      majorityMatch[1].split(',').forEach(f => majorities.add(f.trim()))
    }
    return { conflictFields: conflicts, majorityFields: majorities }
  }, [data?.tags?.review_reason])

  if (loading) {
    return (
      <div className="fixed inset-y-0 right-0 w-[800px] bg-white shadow-2xl flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto"></div>
          <p className="text-slate-500 mt-2">Loading question details...</p>
        </div>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="fixed inset-y-0 right-0 w-[800px] bg-white shadow-2xl flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-2" />
          <p className="text-slate-700">Failed to load question details</p>
        </div>
      </div>
    )
  }

  // Parse review flags
  const reviewFlags = (() => {
    try {
      if (data.tags.review_flags && typeof data.tags.review_flags === 'string') {
        return JSON.parse(data.tags.review_flags)
      }
      return data.tags.review_flags || []
    } catch {
      return []
    }
  })()

  // Get flag type labels
  const getFlagLabel = (flag: string): { label: string; color: string } => {
    const flagLower = flag.toLowerCase()
    if (flag === 'not_oncology') {
      return { label: 'Oncology Filter', color: 'bg-purple-100 text-purple-800' }
    } else if (flag === 'tag_errors' || flagLower === 'low_confidence') {
      return { label: 'Low Confidence', color: 'bg-yellow-100 text-yellow-800' }
    } else if (flag === 'question_errors') {
      return { label: 'Question Error', color: 'bg-red-100 text-red-800' }
    } else if (flagLower === 'llm_fallback') {
      return { label: 'LLM Fallback', color: 'bg-orange-100 text-orange-800' }
    } else if (flagLower === 'ambiguous_topic') {
      return { label: 'Ambiguous Topic', color: 'bg-blue-100 text-blue-800' }
    } else if (flagLower === 'stage_line_conflict') {
      return { label: 'Stage/Line Conflict', color: 'bg-pink-100 text-pink-800' }
    }
    return { label: flag.replace(/_/g, ' '), color: 'bg-gray-100 text-gray-800' }
  }

  // Collapsible field group section component - always shows all groups so user can add missing tags
  const FieldGroupSection = ({
    label,
    isExpanded,
    onToggle,
    children
  }: {
    label: string
    isExpanded: boolean
    onToggle: () => void
    children: React.ReactNode
  }) => {
    return (
      <div className="bg-slate-50 rounded-xl overflow-hidden">
        <button
          onClick={onToggle}
          className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-100 transition-colors"
        >
          <span className="text-sm font-semibold text-slate-700">{label}</span>
          {isExpanded ? (
            <ChevronDown className="w-4 h-4 text-slate-400" />
          ) : (
            <ChevronRight className="w-4 h-4 text-slate-400" />
          )}
        </button>
        {isExpanded && (
          <div className="px-4 pb-3 border-t border-slate-200 space-y-2">
            {children}
          </div>
        )}
      </div>
    )
  }

  return (
    <>
      <div className="fixed inset-0 bg-black/20 z-40" onClick={onClose} />
      <div
        className="fixed inset-y-0 right-0 w-[800px] bg-white shadow-2xl z-50 overflow-hidden flex flex-col"
      >
        <div className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between flex-shrink-0">
          <div className="flex-1">
            <div className="flex items-center gap-3">
              <h2 className="text-xl font-bold text-slate-900">
                Review Question #{data.source_id || data.id}
              </h2>
            </div>

            {/* Flag Reasons */}
            {reviewFlags.length > 0 && (
              <div className="mt-2">
                <div className="flex items-center gap-2">
                  <span className="text-sm text-slate-600">Flagged for:</span>
                  {reviewFlags.map((flag: string, idx: number) => {
                    const { label, color } = getFlagLabel(flag)
                    return (
                      <span key={idx} className={`text-xs px-2 py-1 rounded ${color}`}>
                        {label}
                      </span>
                    )
                  })}
                </div>
                {data.tags.flagged_at && (
                  <div className="text-xs text-slate-500 mt-1">
                    Flagged on {new Date(data.tags.flagged_at).toLocaleDateString()} at {new Date(data.tags.flagged_at).toLocaleTimeString()}
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="flex items-center gap-2">
            {isAdmin && (
              <>
                {/* Edit Question Button */}
                {!isEditingQuestion ? (
                  <button
                    onClick={() => setIsEditingQuestion(true)}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-blue-50 hover:bg-blue-100 text-blue-700 rounded-lg transition-all"
                  >
                    <Pencil className="h-4 w-4" />
                    Edit Question
                  </button>
                ) : (
                  <>
                    <button
                      onClick={saveQuestionStem}
                      disabled={saving}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-green-50 hover:bg-green-100 text-green-700 rounded-lg transition-all disabled:opacity-50"
                    >
                      <Save className="h-4 w-4" />
                      Save Question
                    </button>
                    <button
                      onClick={() => {
                        setIsEditingQuestion(false)
                        setEditedQuestionStem(data.question_stem)
                      }}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition-all"
                    >
                      <XCircle className="h-4 w-4" />
                      Cancel
                    </button>
                  </>
                )}

                {/* Edit Tags Button */}
                {!isEditing ? (
                  <button
                    onClick={() => setIsEditing(true)}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-blue-50 hover:bg-blue-100 text-blue-700 rounded-lg transition-all"
                  >
                    <Pencil className="h-4 w-4" />
                    Edit Tags
                  </button>
                ) : (
                  <>
                    <button
                      onMouseDown={() => {
                        // Blur any focused input to commit pending values before save
                        if (document.activeElement instanceof HTMLElement) {
                          document.activeElement.blur()
                        }
                      }}
                      onClick={() => {
                        // Small delay to allow blur-triggered state updates to process
                        setTimeout(() => saveTags(true), 50)
                      }}
                      disabled={saving}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-green-50 hover:bg-green-100 text-green-700 rounded-lg transition-all disabled:opacity-50"
                    >
                      <Check className="h-4 w-4" />
                      Save & Mark Reviewed
                    </button>
                    <button
                      onClick={() => {
                        setIsEditing(false)
                        // Reset to original values
                        setEditedTags({
                          topic: data.tags.topic || '',
                          disease_state_1: data.tags.disease_state_1 || data.tags.disease_state || '',
                          disease_state_2: data.tags.disease_state_2 || '',
                          disease_stage: data.tags.disease_stage || '',
                          disease_type_1: data.tags.disease_type_1 || '',
                          disease_type_2: data.tags.disease_type_2 || '',
                          treatment_line: data.tags.treatment_line || '',
                          treatment_1: data.tags.treatment_1 || '',
                          treatment_2: data.tags.treatment_2 || '',
                          treatment_3: data.tags.treatment_3 || '',
                          treatment_4: data.tags.treatment_4 || '',
                          treatment_5: data.tags.treatment_5 || '',
                          biomarker_1: data.tags.biomarker_1 || '',
                          biomarker_2: data.tags.biomarker_2 || '',
                          biomarker_3: data.tags.biomarker_3 || '',
                          biomarker_4: data.tags.biomarker_4 || '',
                          biomarker_5: data.tags.biomarker_5 || '',
                          trial_1: data.tags.trial_1 || '',
                          trial_2: data.tags.trial_2 || '',
                          trial_3: data.tags.trial_3 || '',
                          trial_4: data.tags.trial_4 || '',
                          trial_5: data.tags.trial_5 || '',
                          treatment_eligibility: data.tags.treatment_eligibility || '',
                          age_group: data.tags.age_group || '',
                          organ_dysfunction: data.tags.organ_dysfunction || '',
                          fitness_status: data.tags.fitness_status || '',
                          disease_specific_factor: data.tags.disease_specific_factor || '',
                          comorbidity_1: data.tags.comorbidity_1 || '',
                          comorbidity_2: data.tags.comorbidity_2 || '',
                          comorbidity_3: data.tags.comorbidity_3 || '',
                          drug_class_1: data.tags.drug_class_1 || '',
                          drug_class_2: data.tags.drug_class_2 || '',
                          drug_class_3: data.tags.drug_class_3 || '',
                          drug_target_1: data.tags.drug_target_1 || '',
                          drug_target_2: data.tags.drug_target_2 || '',
                          drug_target_3: data.tags.drug_target_3 || '',
                          prior_therapy_1: data.tags.prior_therapy_1 || '',
                          prior_therapy_2: data.tags.prior_therapy_2 || '',
                          prior_therapy_3: data.tags.prior_therapy_3 || '',
                          resistance_mechanism: data.tags.resistance_mechanism || '',
                          metastatic_site_1: data.tags.metastatic_site_1 || '',
                          metastatic_site_2: data.tags.metastatic_site_2 || '',
                          metastatic_site_3: data.tags.metastatic_site_3 || '',
                          symptom_1: data.tags.symptom_1 || '',
                          symptom_2: data.tags.symptom_2 || '',
                          symptom_3: data.tags.symptom_3 || '',
                          performance_status: data.tags.performance_status || '',
                          toxicity_type_1: data.tags.toxicity_type_1 || '',
                          toxicity_type_2: data.tags.toxicity_type_2 || '',
                          toxicity_type_3: data.tags.toxicity_type_3 || '',
                          toxicity_type_4: data.tags.toxicity_type_4 || '',
                          toxicity_type_5: data.tags.toxicity_type_5 || '',
                          toxicity_organ: data.tags.toxicity_organ || '',
                          toxicity_grade: data.tags.toxicity_grade || '',
                          efficacy_endpoint_1: data.tags.efficacy_endpoint_1 || '',
                          efficacy_endpoint_2: data.tags.efficacy_endpoint_2 || '',
                          efficacy_endpoint_3: data.tags.efficacy_endpoint_3 || '',
                          outcome_context: data.tags.outcome_context || '',
                          clinical_benefit: data.tags.clinical_benefit || '',
                          guideline_source_1: data.tags.guideline_source_1 || '',
                          guideline_source_2: data.tags.guideline_source_2 || '',
                          evidence_type: data.tags.evidence_type || '',
                          cme_outcome_level: data.tags.cme_outcome_level || '',
                          data_response_type: data.tags.data_response_type || '',
                          stem_type: data.tags.stem_type || '',
                          lead_in_type: data.tags.lead_in_type || '',
                          answer_format: data.tags.answer_format || '',
                          answer_length_pattern: data.tags.answer_length_pattern || '',
                          distractor_homogeneity: data.tags.distractor_homogeneity || '',
                        })
                      }}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition-all"
                    >
                      <XCircle className="h-4 w-4" />
                      Cancel
                    </button>
                  </>
                )}

                {/* Mark as Non-Oncology Button */}
                <button
                  onClick={handleMarkNonOncology}
                  disabled={saving}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-purple-50 hover:bg-purple-100 text-purple-700 rounded-lg transition-all disabled:opacity-50"
                >
                  <AlertTriangle className="h-4 w-4" />
                  Not Oncology
                </button>

                {/* Mark as Data Error Button */}
                <button
                  onClick={handleMarkDataError}
                  disabled={saving}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-red-50 hover:bg-red-100 text-red-700 rounded-lg transition-all disabled:opacity-50"
                >
                  <Database className="h-4 w-4" />
                  Data Error
                </button>

                {/* Mark as Reviewed (no changes) */}
                {!isEditing && !isEditingQuestion && (
                  <button
                    onClick={handleMarkAsReviewed}
                    disabled={saving}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-green-50 hover:bg-green-100 text-green-700 rounded-lg transition-all disabled:opacity-50"
                  >
                    <CheckCircle className="h-4 w-4" />
                    Mark Reviewed
                  </button>
                )}
              </>
            )}

            <button
              onClick={onClose}
              className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto" style={{ overflowAnchor: 'none' }}>
        <div className="p-6 space-y-6">
          {/* Question Stem */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <FileText className="h-5 w-5 text-slate-500" />
              <h3 className="font-semibold text-slate-900">Question</h3>
            </div>
            {isEditingQuestion ? (
              <textarea
                value={editedQuestionStem}
                onChange={(e) => setEditedQuestionStem(e.target.value)}
                className="w-full p-3 border border-blue-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                rows={4}
              />
            ) : (
              <p className="text-slate-700 bg-slate-50 p-4 rounded-lg leading-relaxed">
                {data.question_stem}
              </p>
            )}
          </div>

          {/* Answers */}
          <div>
            <h3 className="font-semibold text-slate-900 mb-3">Answers</h3>
            <div className="space-y-2">
              <div className="flex items-start gap-2 bg-green-50 p-3 rounded-lg border border-green-200">
                <Check className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
                <span className="text-slate-700">{data.correct_answer}</span>
              </div>
              {data.incorrect_answers?.map((answer, idx) => (
                <div key={idx} className="flex items-start gap-2 bg-slate-50 p-3 rounded-lg">
                  <X className="h-5 w-5 text-slate-400 flex-shrink-0 mt-0.5" />
                  <span className="text-slate-600">{answer}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Tags - 70-field schema with collapsible groups */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Tag className="h-5 w-5 text-slate-500" />
              <h3 className="font-semibold text-slate-900">Tags</h3>
              <button
                onClick={() => setShowFieldGuidance(true)}
                className="p-1 hover:bg-slate-100 rounded-full transition-colors"
                title="Field Guidance"
              >
                <HelpCircle className="h-4 w-4 text-slate-400 hover:text-slate-600" />
              </button>
              {data.tags.worst_case_agreement && (
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setShowAgreementLegend(true)}
                    className="p-0.5 hover:bg-slate-200 rounded transition-colors"
                    title="Agreement status legend"
                  >
                    <AlertCircle className="w-3.5 h-3.5 text-slate-400" />
                  </button>
                  <span className={`text-xs px-2 py-0.5 rounded ${
                    data.tags.worst_case_agreement === 'verified' ? 'bg-emerald-100 text-emerald-700' :
                    data.tags.worst_case_agreement === 'unanimous' ? 'bg-emerald-50 text-emerald-600' :
                    data.tags.worst_case_agreement === 'majority' ? 'bg-amber-100 text-amber-700' :
                    'bg-red-100 text-red-700'
                  }`}>
                    {data.tags.worst_case_agreement === 'verified' ? 'Verified' :
                     data.tags.worst_case_agreement === 'unanimous' ? 'Unanimous' :
                     data.tags.worst_case_agreement === 'majority' ? 'Majority' :
                     'Conflict'}
                  </span>
                </div>
              )}
            </div>

            <div className="space-y-2">
              {/* Core Classification Group */}
              <FieldGroupSection
                label={FIELD_GROUPS.core.label}
                isExpanded={expandedGroups.has('core')}
                onToggle={() => {
                  setExpandedGroups(prev => {
                    const next = new Set(prev)
                    if (next.has('core')) next.delete('core')
                    else next.add('core')
                    return next
                  })
                }}
              >
                <TagRow label="Topic" value={isEditing ? editedTags.topic : data.tags.topic} confidence={data.tags.topic_confidence} isEditing={isEditing} tagKey="topic" onEdit={(v) => setEditedTags({...editedTags, topic: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Disease State 1" value={isEditing ? editedTags.disease_state_1 : (data.tags.disease_state_1 || data.tags.disease_state)} confidence={data.tags.disease_state_confidence} isEditing={isEditing} tagKey="disease_state_1" onEdit={(v) => setEditedTags({...editedTags, disease_state_1: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Disease State 2 (Rare)" value={isEditing ? editedTags.disease_state_2 : data.tags.disease_state_2} isEditing={isEditing} tagKey="disease_state_2" onEdit={(v) => setEditedTags({...editedTags, disease_state_2: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Disease Stage" value={isEditing ? editedTags.disease_stage : data.tags.disease_stage} confidence={data.tags.disease_stage_confidence} isEditing={isEditing} tagKey="disease_stage" onEdit={(v) => setEditedTags({...editedTags, disease_stage: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Disease Type" value={isEditing ? editedTags.disease_type_1 : data.tags.disease_type_1} confidence={data.tags.disease_type_confidence} isEditing={isEditing} tagKey="disease_type_1" onEdit={(v) => setEditedTags({...editedTags, disease_type_1: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Disease Type 2" value={isEditing ? editedTags.disease_type_2 : data.tags.disease_type_2} isEditing={isEditing} tagKey="disease_type_2" onEdit={(v) => setEditedTags({...editedTags, disease_type_2: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Treatment Line" value={isEditing ? editedTags.treatment_line : data.tags.treatment_line} confidence={data.tags.treatment_line_confidence} isEditing={isEditing} tagKey="treatment_line" onEdit={(v) => setEditedTags({...editedTags, treatment_line: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
              </FieldGroupSection>

              {/* Treatments, Biomarkers & Trials Group */}
              <FieldGroupSection
                label={FIELD_GROUPS.multiValue.label}
                isExpanded={expandedGroups.has('multiValue')}
                onToggle={() => {
                  setExpandedGroups(prev => {
                    const next = new Set(prev)
                    if (next.has('multiValue')) next.delete('multiValue')
                    else next.add('multiValue')
                    return next
                  })
                }}
              >
                {/* Treatments */}
                <TagRow label="Treatment 1" value={isEditing ? editedTags.treatment_1 : data.tags.treatment_1} confidence={data.tags.treatment_confidence} isEditing={isEditing} tagKey="treatment_1" onEdit={(v) => setEditedTags({...editedTags, treatment_1: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Treatment 2" value={isEditing ? editedTags.treatment_2 : data.tags.treatment_2} isEditing={isEditing} tagKey="treatment_2" onEdit={(v) => setEditedTags({...editedTags, treatment_2: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Treatment 3" value={isEditing ? editedTags.treatment_3 : data.tags.treatment_3} isEditing={isEditing} tagKey="treatment_3" onEdit={(v) => setEditedTags({...editedTags, treatment_3: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Treatment 4" value={isEditing ? editedTags.treatment_4 : data.tags.treatment_4} isEditing={isEditing} tagKey="treatment_4" onEdit={(v) => setEditedTags({...editedTags, treatment_4: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Treatment 5" value={isEditing ? editedTags.treatment_5 : data.tags.treatment_5} isEditing={isEditing} tagKey="treatment_5" onEdit={(v) => setEditedTags({...editedTags, treatment_5: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                {/* Biomarkers */}
                <TagRow label="Biomarker 1" value={isEditing ? editedTags.biomarker_1 : data.tags.biomarker_1} confidence={data.tags.biomarker_confidence} isEditing={isEditing} tagKey="biomarker_1" onEdit={(v) => setEditedTags({...editedTags, biomarker_1: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Biomarker 2" value={isEditing ? editedTags.biomarker_2 : data.tags.biomarker_2} isEditing={isEditing} tagKey="biomarker_2" onEdit={(v) => setEditedTags({...editedTags, biomarker_2: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Biomarker 3" value={isEditing ? editedTags.biomarker_3 : data.tags.biomarker_3} isEditing={isEditing} tagKey="biomarker_3" onEdit={(v) => setEditedTags({...editedTags, biomarker_3: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Biomarker 4" value={isEditing ? editedTags.biomarker_4 : data.tags.biomarker_4} isEditing={isEditing} tagKey="biomarker_4" onEdit={(v) => setEditedTags({...editedTags, biomarker_4: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Biomarker 5" value={isEditing ? editedTags.biomarker_5 : data.tags.biomarker_5} isEditing={isEditing} tagKey="biomarker_5" onEdit={(v) => setEditedTags({...editedTags, biomarker_5: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                {/* Trials */}
                <TagRow label="Trial 1" value={isEditing ? editedTags.trial_1 : data.tags.trial_1} confidence={data.tags.trial_confidence} isEditing={isEditing} tagKey="trial_1" onEdit={(v) => setEditedTags({...editedTags, trial_1: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Trial 2" value={isEditing ? editedTags.trial_2 : data.tags.trial_2} isEditing={isEditing} tagKey="trial_2" onEdit={(v) => setEditedTags({...editedTags, trial_2: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Trial 3" value={isEditing ? editedTags.trial_3 : data.tags.trial_3} isEditing={isEditing} tagKey="trial_3" onEdit={(v) => setEditedTags({...editedTags, trial_3: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Trial 4" value={isEditing ? editedTags.trial_4 : data.tags.trial_4} isEditing={isEditing} tagKey="trial_4" onEdit={(v) => setEditedTags({...editedTags, trial_4: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Trial 5" value={isEditing ? editedTags.trial_5 : data.tags.trial_5} isEditing={isEditing} tagKey="trial_5" onEdit={(v) => setEditedTags({...editedTags, trial_5: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
              </FieldGroupSection>

              {/* Treatment Details Group */}
              <FieldGroupSection
                label={FIELD_GROUPS.treatmentDetails.label}
                isExpanded={expandedGroups.has('treatmentDetails')}
                onToggle={() => {
                  setExpandedGroups(prev => {
                    const next = new Set(prev)
                    if (next.has('treatmentDetails')) next.delete('treatmentDetails')
                    else next.add('treatmentDetails')
                    return next
                  })
                }}
              >
                <TagRow label="Drug Class 1" value={isEditing ? editedTags.drug_class_1 : data.tags.drug_class_1} isEditing={isEditing} tagKey="drug_class_1" onEdit={(v) => setEditedTags({...editedTags, drug_class_1: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Drug Class 2" value={isEditing ? editedTags.drug_class_2 : data.tags.drug_class_2} isEditing={isEditing} tagKey="drug_class_2" onEdit={(v) => setEditedTags({...editedTags, drug_class_2: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Drug Class 3" value={isEditing ? editedTags.drug_class_3 : data.tags.drug_class_3} isEditing={isEditing} tagKey="drug_class_3" onEdit={(v) => setEditedTags({...editedTags, drug_class_3: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Drug Target 1" value={isEditing ? editedTags.drug_target_1 : data.tags.drug_target_1} isEditing={isEditing} tagKey="drug_target_1" onEdit={(v) => setEditedTags({...editedTags, drug_target_1: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Drug Target 2" value={isEditing ? editedTags.drug_target_2 : data.tags.drug_target_2} isEditing={isEditing} tagKey="drug_target_2" onEdit={(v) => setEditedTags({...editedTags, drug_target_2: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Drug Target 3" value={isEditing ? editedTags.drug_target_3 : data.tags.drug_target_3} isEditing={isEditing} tagKey="drug_target_3" onEdit={(v) => setEditedTags({...editedTags, drug_target_3: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Prior Therapy 1" value={isEditing ? editedTags.prior_therapy_1 : data.tags.prior_therapy_1} isEditing={isEditing} tagKey="prior_therapy_1" onEdit={(v) => setEditedTags({...editedTags, prior_therapy_1: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Prior Therapy 2" value={isEditing ? editedTags.prior_therapy_2 : data.tags.prior_therapy_2} isEditing={isEditing} tagKey="prior_therapy_2" onEdit={(v) => setEditedTags({...editedTags, prior_therapy_2: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Prior Therapy 3" value={isEditing ? editedTags.prior_therapy_3 : data.tags.prior_therapy_3} isEditing={isEditing} tagKey="prior_therapy_3" onEdit={(v) => setEditedTags({...editedTags, prior_therapy_3: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Resistance Mechanism" value={isEditing ? editedTags.resistance_mechanism : data.tags.resistance_mechanism} isEditing={isEditing} tagKey="resistance_mechanism" onEdit={(v) => setEditedTags({...editedTags, resistance_mechanism: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
              </FieldGroupSection>

              {/* Patient Characteristics Group */}
              <FieldGroupSection
                label={FIELD_GROUPS.patientCharacteristics.label}
                isExpanded={expandedGroups.has('patientCharacteristics')}
                onToggle={() => {
                  setExpandedGroups(prev => {
                    const next = new Set(prev)
                    if (next.has('patientCharacteristics')) next.delete('patientCharacteristics')
                    else next.add('patientCharacteristics')
                    return next
                  })
                }}
              >
                <TagRow label="Treatment Eligibility" value={isEditing ? editedTags.treatment_eligibility : data.tags.treatment_eligibility} isEditing={isEditing} tagKey="treatment_eligibility" onEdit={(v) => setEditedTags({...editedTags, treatment_eligibility: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Age Group" value={isEditing ? editedTags.age_group : data.tags.age_group} isEditing={isEditing} tagKey="age_group" onEdit={(v) => setEditedTags({...editedTags, age_group: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Organ Dysfunction" value={isEditing ? editedTags.organ_dysfunction : data.tags.organ_dysfunction} isEditing={isEditing} tagKey="organ_dysfunction" onEdit={(v) => setEditedTags({...editedTags, organ_dysfunction: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Fitness Status" value={isEditing ? editedTags.fitness_status : data.tags.fitness_status} isEditing={isEditing} tagKey="fitness_status" onEdit={(v) => setEditedTags({...editedTags, fitness_status: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Disease Specific Factor" value={isEditing ? editedTags.disease_specific_factor : data.tags.disease_specific_factor} isEditing={isEditing} tagKey="disease_specific_factor" onEdit={(v) => setEditedTags({...editedTags, disease_specific_factor: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Comorbidity 1" value={isEditing ? editedTags.comorbidity_1 : data.tags.comorbidity_1} isEditing={isEditing} tagKey="comorbidity_1" onEdit={(v) => setEditedTags({...editedTags, comorbidity_1: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Comorbidity 2" value={isEditing ? editedTags.comorbidity_2 : data.tags.comorbidity_2} isEditing={isEditing} tagKey="comorbidity_2" onEdit={(v) => setEditedTags({...editedTags, comorbidity_2: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Comorbidity 3" value={isEditing ? editedTags.comorbidity_3 : data.tags.comorbidity_3} isEditing={isEditing} tagKey="comorbidity_3" onEdit={(v) => setEditedTags({...editedTags, comorbidity_3: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
              </FieldGroupSection>

              {/* Clinical Context Group */}
              <FieldGroupSection
                label={FIELD_GROUPS.clinicalContext.label}
                isExpanded={expandedGroups.has('clinicalContext')}
                onToggle={() => {
                  setExpandedGroups(prev => {
                    const next = new Set(prev)
                    if (next.has('clinicalContext')) next.delete('clinicalContext')
                    else next.add('clinicalContext')
                    return next
                  })
                }}
              >
                <TagRow label="Metastatic Site 1" value={isEditing ? editedTags.metastatic_site_1 : data.tags.metastatic_site_1} isEditing={isEditing} tagKey="metastatic_site_1" onEdit={(v) => setEditedTags({...editedTags, metastatic_site_1: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Metastatic Site 2" value={isEditing ? editedTags.metastatic_site_2 : data.tags.metastatic_site_2} isEditing={isEditing} tagKey="metastatic_site_2" onEdit={(v) => setEditedTags({...editedTags, metastatic_site_2: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Metastatic Site 3" value={isEditing ? editedTags.metastatic_site_3 : data.tags.metastatic_site_3} isEditing={isEditing} tagKey="metastatic_site_3" onEdit={(v) => setEditedTags({...editedTags, metastatic_site_3: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Symptom 1" value={isEditing ? editedTags.symptom_1 : data.tags.symptom_1} isEditing={isEditing} tagKey="symptom_1" onEdit={(v) => setEditedTags({...editedTags, symptom_1: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Symptom 2" value={isEditing ? editedTags.symptom_2 : data.tags.symptom_2} isEditing={isEditing} tagKey="symptom_2" onEdit={(v) => setEditedTags({...editedTags, symptom_2: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Symptom 3" value={isEditing ? editedTags.symptom_3 : data.tags.symptom_3} isEditing={isEditing} tagKey="symptom_3" onEdit={(v) => setEditedTags({...editedTags, symptom_3: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Performance Status" value={isEditing ? editedTags.performance_status : data.tags.performance_status} isEditing={isEditing} tagKey="performance_status" onEdit={(v) => setEditedTags({...editedTags, performance_status: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
              </FieldGroupSection>

              {/* Safety & Toxicity Group */}
              <FieldGroupSection
                label={FIELD_GROUPS.safetyToxicity.label}
                isExpanded={expandedGroups.has('safetyToxicity')}
                onToggle={() => {
                  setExpandedGroups(prev => {
                    const next = new Set(prev)
                    if (next.has('safetyToxicity')) next.delete('safetyToxicity')
                    else next.add('safetyToxicity')
                    return next
                  })
                }}
              >
                <TagRow label="Toxicity Type 1" value={isEditing ? editedTags.toxicity_type_1 : data.tags.toxicity_type_1} isEditing={isEditing} tagKey="toxicity_type_1" onEdit={(v) => setEditedTags({...editedTags, toxicity_type_1: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Toxicity Type 2" value={isEditing ? editedTags.toxicity_type_2 : data.tags.toxicity_type_2} isEditing={isEditing} tagKey="toxicity_type_2" onEdit={(v) => setEditedTags({...editedTags, toxicity_type_2: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Toxicity Type 3" value={isEditing ? editedTags.toxicity_type_3 : data.tags.toxicity_type_3} isEditing={isEditing} tagKey="toxicity_type_3" onEdit={(v) => setEditedTags({...editedTags, toxicity_type_3: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Toxicity Type 4" value={isEditing ? editedTags.toxicity_type_4 : data.tags.toxicity_type_4} isEditing={isEditing} tagKey="toxicity_type_4" onEdit={(v) => setEditedTags({...editedTags, toxicity_type_4: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Toxicity Type 5" value={isEditing ? editedTags.toxicity_type_5 : data.tags.toxicity_type_5} isEditing={isEditing} tagKey="toxicity_type_5" onEdit={(v) => setEditedTags({...editedTags, toxicity_type_5: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Toxicity Organ" value={isEditing ? editedTags.toxicity_organ : data.tags.toxicity_organ} isEditing={isEditing} tagKey="toxicity_organ" onEdit={(v) => setEditedTags({...editedTags, toxicity_organ: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Toxicity Grade" value={isEditing ? editedTags.toxicity_grade : data.tags.toxicity_grade} isEditing={isEditing} tagKey="toxicity_grade" onEdit={(v) => setEditedTags({...editedTags, toxicity_grade: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
              </FieldGroupSection>

              {/* Efficacy & Outcomes Group */}
              <FieldGroupSection
                label={FIELD_GROUPS.efficacyOutcomes.label}
                isExpanded={expandedGroups.has('efficacyOutcomes')}
                onToggle={() => {
                  setExpandedGroups(prev => {
                    const next = new Set(prev)
                    if (next.has('efficacyOutcomes')) next.delete('efficacyOutcomes')
                    else next.add('efficacyOutcomes')
                    return next
                  })
                }}
              >
                <TagRow label="Efficacy Endpoint 1" value={isEditing ? editedTags.efficacy_endpoint_1 : data.tags.efficacy_endpoint_1} isEditing={isEditing} tagKey="efficacy_endpoint_1" onEdit={(v) => setEditedTags({...editedTags, efficacy_endpoint_1: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Efficacy Endpoint 2" value={isEditing ? editedTags.efficacy_endpoint_2 : data.tags.efficacy_endpoint_2} isEditing={isEditing} tagKey="efficacy_endpoint_2" onEdit={(v) => setEditedTags({...editedTags, efficacy_endpoint_2: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Efficacy Endpoint 3" value={isEditing ? editedTags.efficacy_endpoint_3 : data.tags.efficacy_endpoint_3} isEditing={isEditing} tagKey="efficacy_endpoint_3" onEdit={(v) => setEditedTags({...editedTags, efficacy_endpoint_3: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Outcome Context" value={isEditing ? editedTags.outcome_context : data.tags.outcome_context} isEditing={isEditing} tagKey="outcome_context" onEdit={(v) => setEditedTags({...editedTags, outcome_context: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Clinical Benefit" value={isEditing ? editedTags.clinical_benefit : data.tags.clinical_benefit} isEditing={isEditing} tagKey="clinical_benefit" onEdit={(v) => setEditedTags({...editedTags, clinical_benefit: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
              </FieldGroupSection>

              {/* Evidence & Guidelines Group */}
              <FieldGroupSection
                label={FIELD_GROUPS.evidenceGuidelines.label}
                isExpanded={expandedGroups.has('evidenceGuidelines')}
                onToggle={() => {
                  setExpandedGroups(prev => {
                    const next = new Set(prev)
                    if (next.has('evidenceGuidelines')) next.delete('evidenceGuidelines')
                    else next.add('evidenceGuidelines')
                    return next
                  })
                }}
              >
                <TagRow label="Guideline Source 1" value={isEditing ? editedTags.guideline_source_1 : data.tags.guideline_source_1} isEditing={isEditing} tagKey="guideline_source_1" onEdit={(v) => setEditedTags({...editedTags, guideline_source_1: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Guideline Source 2" value={isEditing ? editedTags.guideline_source_2 : data.tags.guideline_source_2} isEditing={isEditing} tagKey="guideline_source_2" onEdit={(v) => setEditedTags({...editedTags, guideline_source_2: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Evidence Type" value={isEditing ? editedTags.evidence_type : data.tags.evidence_type} isEditing={isEditing} tagKey="evidence_type" onEdit={(v) => setEditedTags({...editedTags, evidence_type: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
              </FieldGroupSection>

              {/* Question Format & Quality Group */}
              <FieldGroupSection
                label={FIELD_GROUPS.questionQuality.label}
                isExpanded={expandedGroups.has('questionQuality')}
                onToggle={() => {
                  setExpandedGroups(prev => {
                    const next = new Set(prev)
                    if (next.has('questionQuality')) next.delete('questionQuality')
                    else next.add('questionQuality')
                    return next
                  })
                }}
              >
                <TagRow label="CME Outcome Level" value={isEditing ? editedTags.cme_outcome_level : data.tags.cme_outcome_level} isEditing={isEditing} tagKey="cme_outcome_level" onEdit={(v) => setEditedTags({...editedTags, cme_outcome_level: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Data Response Type" value={isEditing ? editedTags.data_response_type : data.tags.data_response_type} isEditing={isEditing} tagKey="data_response_type" onEdit={(v) => setEditedTags({...editedTags, data_response_type: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Stem Type" value={isEditing ? editedTags.stem_type : data.tags.stem_type} isEditing={isEditing} tagKey="stem_type" onEdit={(v) => setEditedTags({...editedTags, stem_type: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Lead-in Type" value={isEditing ? editedTags.lead_in_type : data.tags.lead_in_type} isEditing={isEditing} tagKey="lead_in_type" onEdit={(v) => setEditedTags({...editedTags, lead_in_type: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Answer Format" value={isEditing ? editedTags.answer_format : data.tags.answer_format} isEditing={isEditing} tagKey="answer_format" onEdit={(v) => setEditedTags({...editedTags, answer_format: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Answer Length Pattern" value={isEditing ? editedTags.answer_length_pattern : data.tags.answer_length_pattern} isEditing={isEditing} tagKey="answer_length_pattern" onEdit={(v) => setEditedTags({...editedTags, answer_length_pattern: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                <TagRow label="Distractor Homogeneity" value={isEditing ? editedTags.distractor_homogeneity : data.tags.distractor_homogeneity} isEditing={isEditing} tagKey="distractor_homogeneity" onEdit={(v) => setEditedTags({...editedTags, distractor_homogeneity: v})} conflictFields={conflictFields} majorityFields={majorityFields} />
                {/* Boolean flaw indicators - read-only display */}
                {data.tags.flaw_absolute_terms && <TagRow label="Flaw: Absolute Terms" value="Yes" isEditing={false} tagKey="flaw_absolute_terms" color="bg-yellow-100 text-yellow-800" conflictFields={conflictFields} majorityFields={majorityFields} />}
                {data.tags.flaw_grammatical_cue && <TagRow label="Flaw: Grammatical Cue" value="Yes" isEditing={false} tagKey="flaw_grammatical_cue" color="bg-yellow-100 text-yellow-800" conflictFields={conflictFields} majorityFields={majorityFields} />}
                {data.tags.flaw_implausible_distractor && <TagRow label="Flaw: Implausible Distractor" value="Yes" isEditing={false} tagKey="flaw_implausible_distractor" color="bg-yellow-100 text-yellow-800" conflictFields={conflictFields} majorityFields={majorityFields} />}
                {data.tags.flaw_clang_association && <TagRow label="Flaw: Clang Association" value="Yes" isEditing={false} tagKey="flaw_clang_association" color="bg-yellow-100 text-yellow-800" conflictFields={conflictFields} majorityFields={majorityFields} />}
                {data.tags.flaw_convergence_vulnerability && <TagRow label="Flaw: Convergence Vulnerability" value="Yes" isEditing={false} tagKey="flaw_convergence_vulnerability" color="bg-yellow-100 text-yellow-800" conflictFields={conflictFields} majorityFields={majorityFields} />}
                {data.tags.flaw_double_negative && <TagRow label="Flaw: Double Negative" value="Yes" isEditing={false} tagKey="flaw_double_negative" color="bg-yellow-100 text-yellow-800" conflictFields={conflictFields} majorityFields={majorityFields} />}
                {/* Computed fields - read-only */}
                {data.tags.answer_option_count && <TagRow label="Answer Options" value={String(data.tags.answer_option_count)} isEditing={false} tagKey="answer_option_count" conflictFields={conflictFields} majorityFields={majorityFields} />}
                {data.tags.correct_answer_position && <TagRow label="Correct Answer Position" value={data.tags.correct_answer_position} isEditing={false} tagKey="correct_answer_position" conflictFields={conflictFields} majorityFields={majorityFields} />}
              </FieldGroupSection>

              {/* Review Notes Section */}
              {isEditing ? (
                <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mt-4">
                  <label className="block text-sm font-semibold text-amber-800 mb-2">
                    Review Notes (for few-shot learning)
                  </label>
                  <textarea
                    value={reviewNotes}
                    onChange={(e) => setReviewNotes(e.target.value)}
                    placeholder="Add notes about your corrections (e.g., 'LLM over-tagged clinical_benefit', 'Should be R/R not 2L')..."
                    className="w-full px-3 py-2 border border-amber-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent resize-none bg-white"
                    rows={3}
                  />
                  <p className="text-xs text-amber-600 mt-1">
                    These notes help improve future tagging accuracy
                  </p>
                </div>
              ) : reviewNotes ? (
                <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mt-4">
                  <h4 className="text-sm font-semibold text-amber-800 mb-2">Review Notes</h4>
                  <p className="text-sm text-amber-900 whitespace-pre-wrap">{reviewNotes}</p>
                </div>
              ) : null}
            </div>
          </div>

          {/* Source */}
          <div>
            <h3 className="font-semibold text-slate-900 mb-2">Source</h3>
            <div className="space-y-1">
              {data.source_id && (
                <p className="text-sm">
                  <span className="text-slate-500">QGD:</span>{' '}
                  <span className="font-mono text-slate-700">{data.source_id}</span>
                </p>
              )}
              <p className="text-sm text-slate-600">{data.source_file}</p>
            </div>
          </div>

          {/* Performance Metrics (if available) */}
          {data.performance && data.performance.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-3">
                <TrendingUp className="h-5 w-5 text-slate-500" />
                <h3 className="font-semibold text-slate-900">Performance Metrics</h3>
              </div>

              {/* Segment selector */}
              {(() => {
                // Define segments with display names - Row 1: specialty, Row 2: practice setting
                const segmentRows = [
                  [
                    { key: 'overall', label: 'Overall' },
                    { key: 'medical_oncologist', label: 'Med/Heme Oncs' },
                    { key: 'surgical_oncologist', label: 'Surg Oncs' },
                    { key: 'radiation_oncologist', label: 'Rad Oncs' },
                    { key: 'app', label: 'APPs' },
                  ],
                  [
                    { key: 'community', label: 'Community Oncs' },
                    { key: 'academic', label: 'Academic Oncs' },
                  ]
                ]

                // Get available segments from data
                const availableSegments = new Set(data.performance.map(p => p.segment))

                return (
                  <div className="space-y-2 mb-3">
                    {segmentRows.map((row, rowIndex) => (
                      <div key={rowIndex} className="flex gap-2 flex-wrap">
                        {row.map(segment => {
                          const hasData = availableSegments.has(segment.key)
                          const isSelected = selectedSegment === segment.key

                          return (
                            <button
                              key={segment.key}
                              onClick={() => hasData && setSelectedSegment(segment.key)}
                              disabled={!hasData}
                              className={`px-3 py-1 rounded-lg text-sm transition-all ${
                                isSelected
                                  ? 'bg-primary-100 text-primary-700 font-medium'
                                  : hasData
                                    ? 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                                    : 'bg-slate-50 text-slate-300 cursor-not-allowed'
                              }`}
                            >
                              {segment.label}
                            </button>
                          )
                        })}
                      </div>
                    ))}
                  </div>
                )
              })()}

              {/* Activity selector if there are multiple activities */}
              {data.activities && data.activities.length > 1 && (
                <div className="mb-3">
                  <label className="block text-sm font-medium text-slate-700 mb-2">Activity</label>
                  <select
                    value={selectedActivity || ''}
                    onChange={(e) => setSelectedActivity(e.target.value || null)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                  >
                    <option value="">All Activities Combined</option>
                    {data.activities.map(activity => (
                      <option key={activity} value={activity}>{activity}</option>
                    ))}
                  </select>
                </div>
              )}

              {/* Performance metrics display */}
              {(() => {
                const filteredMetrics = data.performance.filter(p => {
                  const matchesSegment = selectedSegment === 'overall'
                    ? p.segment === 'overall' || p.segment === 'Overall'
                    : p.segment === selectedSegment
                  return matchesSegment
                })

                if (filteredMetrics.length === 0) {
                  return <p className="text-slate-500 text-sm italic">No performance data available for this selection</p>
                }

                return (
                  <div className="bg-slate-50 p-4 rounded-lg space-y-3">
                    {filteredMetrics.map((metric, idx) => {
                      const performanceGain = (metric.pre_score !== null && metric.post_score !== null)
                        ? metric.post_score - metric.pre_score
                        : null
                      return (
                        <div key={idx} className="grid grid-cols-3 gap-4">
                          <div>
                            <p className="text-xs text-slate-500 uppercase tracking-wide mb-1">Pre-Test</p>
                            <p className="text-lg font-semibold text-slate-900">
                              {metric.pre_score?.toFixed(1) ?? '—'}%
                            </p>
                            {metric.pre_n && <p className="text-xs text-slate-400">n={metric.pre_n}</p>}
                          </div>
                          <div>
                            <p className="text-xs text-slate-500 uppercase tracking-wide mb-1">Post-Test</p>
                            <p className="text-lg font-semibold text-slate-900">
                              {metric.post_score?.toFixed(1) ?? '—'}%
                            </p>
                            {metric.post_n && <p className="text-xs text-slate-400">n={metric.post_n}</p>}
                          </div>
                          <div>
                            <p className="text-xs text-slate-500 uppercase tracking-wide mb-1">Change</p>
                            {performanceGain !== null ? (
                              <p className={`text-lg font-semibold ${
                                performanceGain > 0 ? 'text-green-600' :
                                performanceGain < 0 ? 'text-red-600' :
                                'text-slate-600'
                              }`}>
                                {performanceGain > 0 ? '+' : ''}{performanceGain.toFixed(1)}%
                              </p>
                            ) : (
                              <p className="text-lg font-semibold text-slate-400">—</p>
                            )}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )
              })()}
            </div>
          )}

          {/* Activities */}
          {data.activities && data.activities.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-3">
                <Activity className="h-5 w-5 text-slate-500" />
                <h3 className="font-semibold text-slate-900">Activities</h3>
              </div>
              <div className="flex flex-wrap gap-2">
                {data.activities.map((activity, idx) => (
                  <span key={idx} className="px-3 py-1 bg-blue-50 text-blue-700 rounded-lg text-sm">
                    {activity}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
        </div>
      </div>

      {/* Not Oncology Confirmation Modal */}
      {showNotOncologyConfirm && (
        <>
          <div className="fixed inset-0 bg-black/50 z-[60]" onClick={() => setShowNotOncologyConfirm(false)} />
          <div className="fixed inset-0 flex items-center justify-center z-[70] p-4">
            <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 rounded-full bg-purple-100 flex items-center justify-center">
                  <AlertTriangle className="h-6 w-6 text-purple-600" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-slate-900">Remove from Oncology Dataset?</h3>
                  <p className="text-sm text-slate-500">This action can be undone later</p>
                </div>
              </div>
              <p className="text-slate-600 mb-6">
                Are you sure this question is not oncology-related? This will remove it from the oncology dataset and it will no longer appear in standard searches.
              </p>
              <div className="flex justify-end gap-3">
                <button
                  onClick={() => setShowNotOncologyConfirm(false)}
                  className="px-4 py-2 text-sm font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={confirmMarkNonOncology}
                  disabled={saving}
                  className="px-4 py-2 text-sm font-medium text-white bg-purple-600 hover:bg-purple-700 rounded-lg transition-colors disabled:opacity-50"
                >
                  {saving ? 'Removing...' : 'Yes, Remove'}
                </button>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Data Error Confirmation Modal */}
      {showDataErrorConfirm && (
        <>
          <div className="fixed inset-0 bg-black/50 z-[60]" onClick={() => setShowDataErrorConfirm(false)} />
          <div className="fixed inset-0 flex items-center justify-center z-[70] p-4">
            <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center">
                  <Database className="h-6 w-6 text-red-600" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-slate-900">Mark as Data Error?</h3>
                  <p className="text-sm text-slate-500">Question has data quality issues</p>
                </div>
              </div>
              <p className="text-slate-600 mb-6">
                This question has missing or malformed data (e.g., missing answer options). It will be hidden from the dashboard and tracked separately for data cleanup.
              </p>
              <div className="flex justify-end gap-3">
                <button
                  onClick={() => setShowDataErrorConfirm(false)}
                  className="px-4 py-2 text-sm font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={confirmMarkDataError}
                  disabled={saving}
                  className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-lg transition-colors disabled:opacity-50"
                >
                  {saving ? 'Marking...' : 'Yes, Mark as Error'}
                </button>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Field Guidance Modal */}
      <FieldGuidanceModal
        isOpen={showFieldGuidance}
        onClose={() => setShowFieldGuidance(false)}
      />

      {/* Agreement Status Legend Modal */}
      {showAgreementLegend && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowAgreementLegend(false)}>
          <div className="bg-white rounded-xl shadow-xl p-6 max-w-md mx-4" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-slate-900">Tag Agreement Status</h3>
              <button onClick={() => setShowAgreementLegend(false)} className="p-1 hover:bg-slate-100 rounded">
                <X className="w-5 h-5 text-slate-500" />
              </button>
            </div>
            <p className="text-sm text-slate-600 mb-4">
              This status reflects the worst-case LLM agreement across <strong>ALL</strong> tagged fields. If any single field has a conflict, the overall status shows Conflict.
            </p>
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <span className="px-2 py-0.5 rounded text-xs font-medium bg-emerald-100 text-emerald-700 w-20 text-center">Verified</span>
                <span className="text-sm text-slate-600">Human-reviewed and confirmed</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="px-2 py-0.5 rounded text-xs font-medium bg-emerald-50 text-emerald-600 w-20 text-center">Unanimous</span>
                <span className="text-sm text-slate-600">All 3 models agreed on all fields</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="px-2 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-700 w-20 text-center">Majority</span>
                <span className="text-sm text-slate-600">2/3 models agreed (some fields have 2-1 split)</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-700 w-20 text-center">Conflict</span>
                <span className="text-sm text-slate-600">At least one field has 3-way disagreement</span>
              </div>
            </div>
            <p className="text-xs text-slate-500 mt-4 border-t pt-4">
              Note: This differs from the Question Explorer which uses only 8 core tags (topic, disease_state, disease_stage, disease_type, treatment_line, treatment, biomarker, trial).
            </p>
          </div>
        </div>
      )}
    </>
  )
}
