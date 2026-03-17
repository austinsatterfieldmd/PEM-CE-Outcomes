import { useEffect, useState } from 'react'
import { X, Check, AlertCircle, Tag, Activity, FileText, TrendingUp, Pencil, Save, XCircle, Flag, ChevronDown, ChevronRight, Info, RefreshCw, Layers } from 'lucide-react'
import { getQuestionDetail, updateQuestionTags, flagQuestion } from '../services/apiRouter'
import CreateProposalModal from './CreateProposalModal'
import CreateDedupClusterModal from './CreateDedupClusterModal'
import type { QuestionDetailData, PerformanceMetric } from '../types'
import { FIELD_GROUPS } from '../types'
import { useAuth } from './AuthProvider'
import { useRole } from '../contexts/RoleContext'
import { SEGMENT_DEFS } from '../config/segmentConfig'

interface QuestionDetailProps {
  questionId: number
  onClose: () => void
  onTagsUpdated?: () => void
}

interface EditableTags {
  // Core Classification
  topic: string
  disease_state: string
  disease_state_1: string
  disease_state_2: string
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

// Helper function to initialize all editable tags from data
function initEditableTagsFromData(tags: any): EditableTags {
  return {
    // Core Classification
    topic: tags?.topic || '',
    disease_state: tags?.disease_state || '',
    disease_state_1: tags?.disease_state_1 || tags?.disease_state || '',
    disease_state_2: tags?.disease_state_2 || '',
    disease_stage: tags?.disease_stage || '',
    disease_type_1: tags?.disease_type_1 || '',
    disease_type_2: tags?.disease_type_2 || '',
    treatment_line: tags?.treatment_line || '',
    // Multi-value fields
    treatment_1: tags?.treatment_1 || '',
    treatment_2: tags?.treatment_2 || '',
    treatment_3: tags?.treatment_3 || '',
    treatment_4: tags?.treatment_4 || '',
    treatment_5: tags?.treatment_5 || '',
    biomarker_1: tags?.biomarker_1 || '',
    biomarker_2: tags?.biomarker_2 || '',
    biomarker_3: tags?.biomarker_3 || '',
    biomarker_4: tags?.biomarker_4 || '',
    biomarker_5: tags?.biomarker_5 || '',
    trial_1: tags?.trial_1 || '',
    trial_2: tags?.trial_2 || '',
    trial_3: tags?.trial_3 || '',
    trial_4: tags?.trial_4 || '',
    trial_5: tags?.trial_5 || '',
    // Patient Characteristics
    treatment_eligibility: tags?.treatment_eligibility || '',
    age_group: tags?.age_group || '',
    organ_dysfunction: tags?.organ_dysfunction || '',
    fitness_status: tags?.fitness_status || '',
    disease_specific_factor: tags?.disease_specific_factor || '',
    // Treatment Metadata
    drug_class_1: tags?.drug_class_1 || '',
    drug_class_2: tags?.drug_class_2 || '',
    drug_class_3: tags?.drug_class_3 || '',
    drug_target_1: tags?.drug_target_1 || '',
    drug_target_2: tags?.drug_target_2 || '',
    drug_target_3: tags?.drug_target_3 || '',
    prior_therapy_1: tags?.prior_therapy_1 || '',
    prior_therapy_2: tags?.prior_therapy_2 || '',
    prior_therapy_3: tags?.prior_therapy_3 || '',
    resistance_mechanism: tags?.resistance_mechanism || '',
    // Clinical Context
    metastatic_site_1: tags?.metastatic_site_1 || '',
    metastatic_site_2: tags?.metastatic_site_2 || '',
    metastatic_site_3: tags?.metastatic_site_3 || '',
    symptom_1: tags?.symptom_1 || '',
    symptom_2: tags?.symptom_2 || '',
    symptom_3: tags?.symptom_3 || '',
    performance_status: tags?.performance_status || '',
    // Safety & Toxicity
    toxicity_type_1: tags?.toxicity_type_1 || '',
    toxicity_type_2: tags?.toxicity_type_2 || '',
    toxicity_type_3: tags?.toxicity_type_3 || '',
    toxicity_type_4: tags?.toxicity_type_4 || '',
    toxicity_type_5: tags?.toxicity_type_5 || '',
    toxicity_organ: tags?.toxicity_organ || '',
    toxicity_grade: tags?.toxicity_grade || '',
    // Efficacy & Outcomes
    efficacy_endpoint_1: tags?.efficacy_endpoint_1 || '',
    efficacy_endpoint_2: tags?.efficacy_endpoint_2 || '',
    efficacy_endpoint_3: tags?.efficacy_endpoint_3 || '',
    outcome_context: tags?.outcome_context || '',
    clinical_benefit: tags?.clinical_benefit || '',
    // Evidence & Guidelines
    guideline_source_1: tags?.guideline_source_1 || '',
    guideline_source_2: tags?.guideline_source_2 || '',
    evidence_type: tags?.evidence_type || '',
    // Question Quality
    cme_outcome_level: tags?.cme_outcome_level || '',
    data_response_type: tags?.data_response_type || '',
    stem_type: tags?.stem_type || '',
    lead_in_type: tags?.lead_in_type || '',
    answer_format: tags?.answer_format || '',
    answer_length_pattern: tags?.answer_length_pattern || '',
    distractor_homogeneity: tags?.distractor_homogeneity || '',
  }
}

export function QuestionDetail({ questionId, onClose, onTagsUpdated }: QuestionDetailProps) {
  const { isAdmin: authIsAdmin } = useAuth()
  const { canEdit, isAdmin: roleIsAdmin } = useRole()
  // Use role-based access when available, fall back to auth-based
  const isAdmin = roleIsAdmin || authIsAdmin
  const [data, setData] = useState<QuestionDetailData | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedSegment, setSelectedSegment] = useState<string>('overall')
  const [selectedActivity, setSelectedActivity] = useState<string | null>(null) // null = all activities combined
  const [isEditing, setIsEditing] = useState(false)
  const [isEditingQuestion, setIsEditingQuestion] = useState(false)
  const [showQuestionWarning, setShowQuestionWarning] = useState(false)
  const [showFlagDialog, setShowFlagDialog] = useState(false)
  const [showRetaggingModal, setShowRetaggingModal] = useState(false)
  const [showDedupModal, setShowDedupModal] = useState(false)
  const [showAgreementLegend, setShowAgreementLegend] = useState(false)
  const [saving, setSaving] = useState(false)
  const [editedQuestionStem, setEditedQuestionStem] = useState('')
  const [selectedFlagReasons, setSelectedFlagReasons] = useState<string[]>([])
  const [editedTags, setEditedTags] = useState<EditableTags>({
    // Core Classification
    topic: '',
    disease_state: '',
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
  // Track which field groups are expanded (core is expanded by default for both view and edit modes)
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set(['core', 'edit-core']))
  // Reviewer notes for few-shot learning
  const [reviewNotes, setReviewNotes] = useState('')

  useEffect(() => {
    setLoading(true)
    getQuestionDetail(questionId)
      .then(result => {
        setData(result)
        // Initialize editable tags and question stem from data
        setEditedTags(initEditableTagsFromData(result.tags))
        setEditedQuestionStem(result.question_stem)
        // Initialize review notes
        setReviewNotes(result.tags?.review_notes || '')
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [questionId])

  // Lock body scroll when modal is open
  useEffect(() => {
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = ''
    }
  }, [])

  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (isEditing) {
          cancelEdit()
        } else {
          onClose()
        }
      }
    }
    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [onClose, isEditing])

  // Start editing
  const startEdit = () => {
    if (data) {
      setEditedTags(initEditableTagsFromData(data.tags))
      setIsEditing(true)
    }
  }

  // Cancel editing
  const cancelEdit = () => {
    setIsEditing(false)
    setIsEditingQuestion(false)
    setShowQuestionWarning(false)
    if (data) {
      setEditedTags(initEditableTagsFromData(data.tags))
      setEditedQuestionStem(data.question_stem)
    }
  }

  // Start editing question stem (admin only)
  const startEditQuestion = () => {
    if (!isAdmin) {
      alert('Admin access required to edit question stems.')
      return
    }
    setShowQuestionWarning(true)
  }

  // Confirm question stem editing after warning
  const confirmEditQuestion = () => {
    setShowQuestionWarning(false)
    setIsEditingQuestion(true)
  }

  // Cancel question stem editing
  const cancelEditQuestion = () => {
    setShowQuestionWarning(false)
    setIsEditingQuestion(false)
    if (data) {
      setEditedQuestionStem(data.question_stem)
    }
  }

  // Handle flag question
  const handleFlagQuestion = async () => {
    if (selectedFlagReasons.length === 0) {
      return
    }

    setSaving(true)
    try {
      const result = await flagQuestion(questionId, selectedFlagReasons)
      setShowFlagDialog(false)
      setSelectedFlagReasons([])

      if (result.savedLocally) {
        // In Vercel mode - show success message but don't try to refresh from API
        // The pending edits badge will update automatically
        onTagsUpdated?.()
      } else {
        // Normal mode - refresh data to show updated state
        const updated = await getQuestionDetail(questionId)
        setData(updated)
        onTagsUpdated?.()
      }
    } catch (error) {
      console.error('Failed to flag question:', error)
      alert('Failed to flag question. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  // Toggle flag reason
  const toggleFlagReason = (reason: string) => {
    setSelectedFlagReasons(prev =>
      prev.includes(reason)
        ? prev.filter(r => r !== reason)
        : [...prev, reason]
    )
  }

  // Save tags and mark as reviewed
  const saveTags = async (markAsReviewed: boolean = false) => {
    setSaving(true)
    try {
      // Prepare update payload with all 70 fields
      // Convert empty strings to null for proper API handling
      const updates: any = {
        // Core Classification
        topic: editedTags.topic || null,
        disease_state: editedTags.disease_state || null,
        disease_stage: editedTags.disease_stage || null,
        disease_type_1: editedTags.disease_type_1 || null,
        disease_type_2: editedTags.disease_type_2 || null,
        treatment_line: editedTags.treatment_line || null,
        // Multi-value fields
        treatment_1: editedTags.treatment_1 || null,
        treatment_2: editedTags.treatment_2 || null,
        treatment_3: editedTags.treatment_3 || null,
        treatment_4: editedTags.treatment_4 || null,
        treatment_5: editedTags.treatment_5 || null,
        biomarker_1: editedTags.biomarker_1 || null,
        biomarker_2: editedTags.biomarker_2 || null,
        biomarker_3: editedTags.biomarker_3 || null,
        biomarker_4: editedTags.biomarker_4 || null,
        biomarker_5: editedTags.biomarker_5 || null,
        trial_1: editedTags.trial_1 || null,
        trial_2: editedTags.trial_2 || null,
        trial_3: editedTags.trial_3 || null,
        trial_4: editedTags.trial_4 || null,
        trial_5: editedTags.trial_5 || null,
        // Patient Characteristics
        treatment_eligibility: editedTags.treatment_eligibility || null,
        age_group: editedTags.age_group || null,
        organ_dysfunction: editedTags.organ_dysfunction || null,
        fitness_status: editedTags.fitness_status || null,
        disease_specific_factor: editedTags.disease_specific_factor || null,
        // Treatment Metadata
        drug_class_1: editedTags.drug_class_1 || null,
        drug_class_2: editedTags.drug_class_2 || null,
        drug_class_3: editedTags.drug_class_3 || null,
        drug_target_1: editedTags.drug_target_1 || null,
        drug_target_2: editedTags.drug_target_2 || null,
        drug_target_3: editedTags.drug_target_3 || null,
        prior_therapy_1: editedTags.prior_therapy_1 || null,
        prior_therapy_2: editedTags.prior_therapy_2 || null,
        prior_therapy_3: editedTags.prior_therapy_3 || null,
        resistance_mechanism: editedTags.resistance_mechanism || null,
        // Clinical Context
        metastatic_site_1: editedTags.metastatic_site_1 || null,
        metastatic_site_2: editedTags.metastatic_site_2 || null,
        metastatic_site_3: editedTags.metastatic_site_3 || null,
        symptom_1: editedTags.symptom_1 || null,
        symptom_2: editedTags.symptom_2 || null,
        symptom_3: editedTags.symptom_3 || null,
        performance_status: editedTags.performance_status || null,
        // Safety & Toxicity
        toxicity_type_1: editedTags.toxicity_type_1 || null,
        toxicity_type_2: editedTags.toxicity_type_2 || null,
        toxicity_type_3: editedTags.toxicity_type_3 || null,
        toxicity_type_4: editedTags.toxicity_type_4 || null,
        toxicity_type_5: editedTags.toxicity_type_5 || null,
        toxicity_organ: editedTags.toxicity_organ || null,
        toxicity_grade: editedTags.toxicity_grade || null,
        // Efficacy & Outcomes
        efficacy_endpoint_1: editedTags.efficacy_endpoint_1 || null,
        efficacy_endpoint_2: editedTags.efficacy_endpoint_2 || null,
        efficacy_endpoint_3: editedTags.efficacy_endpoint_3 || null,
        outcome_context: editedTags.outcome_context || null,
        clinical_benefit: editedTags.clinical_benefit || null,
        // Evidence & Guidelines
        guideline_source_1: editedTags.guideline_source_1 || null,
        guideline_source_2: editedTags.guideline_source_2 || null,
        evidence_type: editedTags.evidence_type || null,
        // Question Quality
        cme_outcome_level: editedTags.cme_outcome_level || null,
        data_response_type: editedTags.data_response_type || null,
        stem_type: editedTags.stem_type || null,
        lead_in_type: editedTags.lead_in_type || null,
        answer_format: editedTags.answer_format || null,
        answer_length_pattern: editedTags.answer_length_pattern || null,
        distractor_homogeneity: editedTags.distractor_homogeneity || null,
        // Review flag and notes
        mark_as_reviewed: markAsReviewed,
        review_notes: reviewNotes || null
      }

      // Include question stem if it was edited (admin only)
      if (isEditingQuestion && data && editedQuestionStem !== data.question_stem) {
        updates.question_stem = editedQuestionStem
      }

      // Capture previous values for edit tracking (in Vercel mode)
      const previousValues: Record<string, string | null> = {}
      if (data?.tags) {
        for (const key of Object.keys(updates)) {
          if (key !== 'mark_as_reviewed' && key !== 'question_stem') {
            previousValues[key] = (data.tags as any)[key] ?? null
          }
        }
      }

      const result = await updateQuestionTags(questionId, updates, previousValues)

      if (result.savedLocally) {
        // In Vercel mode - show local save confirmation
        alert('Edit saved locally. Use "Export Edits" in the header to download your changes.')
        setIsEditing(false)
        setIsEditingQuestion(false)
        // Don't refresh from server (data won't change), but notify parent
        onTagsUpdated?.()
      } else {
        // Normal mode - refresh from server
        const updated = await getQuestionDetail(questionId)
        setData(updated)
        setEditedQuestionStem(updated.question_stem)
        setIsEditing(false)
        setIsEditingQuestion(false)
        onTagsUpdated?.()
      }

      // If marked as reviewed, close the detail panel
      if (markAsReviewed) {
        onClose()
      }
    } catch (error) {
      console.error('Failed to save tags:', error)
      alert('Failed to save tags. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  // Get performance for selected segment
  const getSegmentPerformance = (): PerformanceMetric | null => {
    if (!data?.performance) return null
    return data.performance.find(p => p.segment === selectedSegment) || null
  }

  const segmentPerf = getSegmentPerformance()

  // Helper to render tag input (inline to avoid re-mount issues)
  const renderTagInput = (label: string, field: keyof EditableTags, placeholder?: string) => (
    <div key={field} className="flex items-center gap-3 py-2">
      <label className="text-sm text-slate-500 w-28 flex-shrink-0">{label}</label>
      <input
        type="text"
        value={editedTags[field]}
        onChange={(e) => {
          const newValue = e.target.value
          setEditedTags(prev => ({ ...prev, [field]: newValue }))
        }}
        placeholder={placeholder || `Enter ${label.toLowerCase()}...`}
        className="flex-1 px-3 py-2 bg-white border border-slate-200 rounded-lg text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
      />
    </div>
  )

  // Confidence thresholds per tag type (matching qc_flags.py)
  const getConfidenceLevel = (tagField: string, confidence: number): 'high' | 'medium' | 'low' => {
    const thresholds: Record<string, { high: number; medium: number }> = {
      disease_state: { high: 0.85, medium: 0.70 },
      topic: { high: 0.75, medium: 0.55 },
      disease_stage: { high: 0.80, medium: 0.65 },
      disease_type: { high: 0.75, medium: 0.55 },
      treatment_line: { high: 0.80, medium: 0.65 },
      treatment: { high: 0.80, medium: 0.65 },
      biomarker: { high: 0.85, medium: 0.70 },
      trial: { high: 0.90, medium: 0.75 },
    }
    const config = thresholds[tagField] || { high: 0.80, medium: 0.60 }
    if (confidence >= config.high) return 'high'
    if (confidence >= config.medium) return 'medium'
    return 'low'
  }

  // Parse review_reason to get per-field agreement status
  const getFieldAgreementStatus = (field: string): 'conflict' | 'majority' | null => {
    const reviewReason = data?.tags?.review_reason
    if (!reviewReason) return null

    // Parse conflict_in_fields:field1,field2 and majority_in_fields:field1,field2
    const conflictMatch = reviewReason.match(/conflict_in_fields:([^|]+)/)
    const majorityMatch = reviewReason.match(/majority_in_fields:([^|]+)/)

    if (conflictMatch) {
      const conflictFields = conflictMatch[1].split(',').map(f => f.trim())
      if (conflictFields.includes(field)) return 'conflict'
    }

    if (majorityMatch) {
      const majorityFields = majorityMatch[1].split(',').map(f => f.trim())
      if (majorityFields.includes(field)) return 'majority'
    }

    return null
  }

  // Display tag component (read-only mode)
  const TagBadge = ({ label, value, confidence, tagField, color, fieldKey }: {
    label: string
    value: string | null | undefined
    confidence?: number | null
    tagField: string
    color: string
    fieldKey?: string  // The actual field name for agreement lookup
  }) => {
    if (!value) return null

    const level = confidence !== null && confidence !== undefined
      ? getConfidenceLevel(tagField, confidence)
      : null

    // Get per-field agreement status
    const agreementStatus = fieldKey ? getFieldAgreementStatus(fieldKey) : null

    return (
      <div className="flex items-center justify-between py-3 border-b border-slate-100 last:border-0">
        <div className="flex items-center gap-3">
          <span className="text-sm text-slate-500 w-28">{label}</span>
          <span className={`px-3 py-1.5 rounded-lg text-sm font-medium ${color}`}>
            {value}
          </span>
          {agreementStatus && (
            <span className={`text-xs px-1.5 py-0.5 rounded ${
              agreementStatus === 'conflict' ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-700'
            }`} title={agreementStatus === 'conflict' ? 'LLM models disagreed (3-way conflict)' : 'LLM majority vote (2/3 agreed)'}>
              {agreementStatus === 'conflict' ? '⚠ Conflict' : '⚡ Majority'}
            </span>
          )}
        </div>
        {confidence !== null && confidence !== undefined && level && (
          <span
            className={`text-xs px-2 py-1 rounded cursor-help ${
              level === 'high' ? 'bg-emerald-100 text-emerald-700' :
              level === 'medium' ? 'bg-amber-100 text-amber-700' :
              'bg-red-100 text-red-700'
            }`}
            title={level === 'low' ? 'Low confidence - review recommended' :
                   level === 'medium' ? 'Medium confidence' : 'High confidence'}
          >
            {(confidence * 100).toFixed(0)}%
          </span>
        )}
      </div>
    )
  }

  // Collapsible field group section component
  const FieldGroupSection = ({
    label,
    isExpanded,
    onToggle,
    hasData,
    children
  }: {
    label: string
    isExpanded: boolean
    onToggle: () => void
    hasData: boolean
    children: React.ReactNode
  }) => {
    // Don't show groups with no data
    if (!hasData) return null

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
          <div className="px-4 pb-3 border-t border-slate-200">
            {children}
          </div>
        )}
      </div>
    )
  }

  return (
    <>
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-slate-900/20 backdrop-blur-sm z-50"
        onClick={() => !isEditing && onClose()}
      />
      
      {/* Panel */}
      <div className="fixed right-0 top-0 bottom-0 w-full max-w-2xl bg-white shadow-2xl z-50 overflow-hidden flex flex-col animate-fade-in">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-slate-50">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold text-slate-900">
              Question #{data?.source_id || questionId}
            </h2>
            {data?.qcore_score !== null && data?.qcore_score !== undefined && data?.qcore_grade && (
              <span
                className={`px-2 py-1 rounded-lg text-sm font-bold border ${
                  data.qcore_grade === 'A' ? 'bg-emerald-100 text-emerald-700 border-emerald-200' :
                  data.qcore_grade === 'B' ? 'bg-blue-100 text-blue-700 border-blue-200' :
                  data.qcore_grade === 'C' ? 'bg-amber-100 text-amber-700 border-amber-200' :
                  'bg-orange-100 text-orange-700 border-orange-200'  /* D is the floor (no F grade) */
                }`}
                title={`QCore Quality Score: ${data.qcore_score.toFixed(0)}/100`}
              >
                QCore: {data.qcore_grade} ({data.qcore_score.toFixed(0)})
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {isEditing ? (
              <>
                <button
                  onClick={cancelEdit}
                  disabled={saving}
                  className="flex items-center gap-2 px-4 py-2 text-slate-600 bg-slate-200 hover:bg-slate-300 rounded-lg transition-colors disabled:opacity-50"
                >
                  <XCircle className="w-4 h-4" />
                  Cancel
                </button>
                <button
                  onClick={() => saveTags(false)}
                  disabled={saving}
                  className="flex items-center gap-2 px-4 py-2 bg-slate-400 text-white hover:bg-slate-500 rounded-lg transition-colors disabled:opacity-50"
                >
                  <Save className="w-4 h-4" />
                  {saving ? 'Saving...' : 'Save for Further Review'}
                </button>
                <button
                  onClick={() => saveTags(true)}
                  disabled={saving}
                  className="flex items-center gap-2 px-4 py-2 bg-emerald-500 text-white hover:bg-emerald-600 rounded-lg transition-colors disabled:opacity-50"
                >
                  <Check className="w-4 h-4" />
                  {saving ? 'Saving...' : 'Question Reviewed'}
                </button>
              </>
            ) : (
              <button
                onClick={onClose}
                className="p-2 hover:bg-slate-200 rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-slate-500" />
              </button>
            )}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="p-6 space-y-4 animate-pulse">
              <div className="h-20 bg-slate-200 rounded-lg"></div>
              <div className="h-40 bg-slate-100 rounded-lg"></div>
            </div>
          ) : data ? (
            <div className="p-6 space-y-6">
              {/* Question Stem */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-700">
                    <FileText className="w-4 h-4" />
                    Question
                  </h3>
                  <div className="flex items-center gap-2">
                    {canEdit && !isEditingQuestion && !isEditing && (
                      <>
                        <button
                          onClick={() => setShowRetaggingModal(true)}
                          className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-primary-600 hover:bg-primary-50 rounded-lg transition-colors"
                          title="Start a retagging proposal to apply a tag value to similar questions"
                        >
                          <RefreshCw className="w-3.5 h-3.5" />
                          Retagging Proposal
                        </button>
                        <button
                          onClick={() => setShowDedupModal(true)}
                          className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-violet-600 hover:bg-violet-50 rounded-lg transition-colors"
                          title="Flag this question as a potential duplicate and find similar questions"
                        >
                          <Layers className="w-3.5 h-3.5" />
                          Flag Duplicate
                        </button>
                        <button
                          onClick={() => setShowFlagDialog(true)}
                          className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-amber-600 hover:bg-amber-50 rounded-lg transition-colors"
                        >
                          <Flag className="w-3.5 h-3.5" />
                          Flag for Review
                        </button>
                      </>
                    )}
                    {isAdmin && !isEditingQuestion && !isEditing && (
                      <button
                        onClick={startEditQuestion}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-primary-600 hover:bg-primary-50 rounded-lg transition-colors"
                      >
                        <Pencil className="w-3.5 h-3.5" />
                        Edit Question
                      </button>
                    )}
                  </div>
                </div>
                {isEditingQuestion ? (
                  <div className="space-y-2">
                    <textarea
                      value={editedQuestionStem}
                      onChange={(e) => setEditedQuestionStem(e.target.value)}
                      className="w-full px-4 py-3 bg-white border-2 border-primary-300 rounded-xl text-slate-900 leading-relaxed focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 min-h-[100px]"
                      placeholder="Enter question text..."
                    />
                    <div className="flex gap-2">
                      <button
                        onClick={cancelEditQuestion}
                        className="flex items-center gap-2 px-3 py-1.5 text-sm text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
                      >
                        <XCircle className="w-4 h-4" />
                        Cancel
                      </button>
                      <button
                        onClick={() => saveTags(false)}
                        disabled={saving || !editedQuestionStem.trim()}
                        className="flex items-center gap-2 px-3 py-1.5 text-sm bg-primary-500 text-white hover:bg-primary-600 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <Save className="w-4 h-4" />
                        {saving ? 'Saving...' : 'Save Question'}
                      </button>
                    </div>
                  </div>
                ) : (
                  <p className="text-slate-900 leading-relaxed bg-slate-50 p-4 rounded-xl">
                    {data.question_stem}
                  </p>
                )}
              </div>

              {/* Answers */}
              <div>
                <h3 className="text-sm font-semibold text-slate-700 mb-3">Answers</h3>
                <div className="space-y-2">
                  {/* Correct Answer */}
                  {data.correct_answer && (
                    <div className="flex items-start gap-3 p-3 bg-emerald-50 border border-emerald-200 rounded-xl">
                      <Check className="w-5 h-5 text-emerald-600 mt-0.5 flex-shrink-0" />
                      <p className="text-emerald-800 text-sm">{data.correct_answer}</p>
                    </div>
                  )}
                  
                  {/* Incorrect Answers */}
                  {data.incorrect_answers?.map((answer, i) => (
                    <div key={i} className="flex items-start gap-3 p-3 bg-slate-50 rounded-xl">
                      <AlertCircle className="w-5 h-5 text-slate-400 mt-0.5 flex-shrink-0" />
                      <p className="text-slate-600 text-sm">{answer}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Performance Metrics */}
              {data.performance.length > 0 && (
                <div>
                  <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-700 mb-3">
                    <TrendingUp className="w-4 h-4" />
                    Performance Metrics
                  </h3>

                  {/* Activity Selector */}
                  {(data.activity_details?.length || data.activities.length) > 0 && (
                    <div className="mb-4">
                      <p className="text-xs text-slate-500 mb-2">Select Activity:</p>
                      <div className="flex flex-wrap gap-2">
                        <button
                          onClick={() => setSelectedActivity(null)}
                          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                            selectedActivity === null
                              ? 'bg-violet-500 text-white shadow-lg shadow-violet-500/20'
                              : 'bg-violet-50 text-violet-700 hover:bg-violet-100'
                          }`}
                        >
                          All Activities ({data.activity_details?.length || data.activities.length})
                        </button>
                        {/* Use activity_details if available, otherwise fall back to activities */}
                        {data.activity_details?.length ? (
                          data.activity_details.slice(0, 5).map((activityInfo, idx) => (
                            <button
                              key={idx}
                              onClick={() => setSelectedActivity(activityInfo.activity_name)}
                              title={`${activityInfo.activity_name}${activityInfo.activity_date ? ` (${activityInfo.activity_date})` : ''}`}
                              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all max-w-[200px] truncate ${
                                selectedActivity === activityInfo.activity_name
                                  ? 'bg-violet-500 text-white shadow-lg shadow-violet-500/20'
                                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                              }`}
                            >
                              {activityInfo.activity_name.length > 30 ? activityInfo.activity_name.substring(0, 30) + '...' : activityInfo.activity_name}
                            </button>
                          ))
                        ) : (
                          data.activities.slice(0, 5).map((activity, idx) => (
                            <button
                              key={idx}
                              onClick={() => setSelectedActivity(activity)}
                              title={activity}
                              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all max-w-[200px] truncate ${
                                selectedActivity === activity
                                  ? 'bg-violet-500 text-white shadow-lg shadow-violet-500/20'
                                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                              }`}
                            >
                              {activity.length > 30 ? activity.substring(0, 30) + '...' : activity}
                            </button>
                          ))
                        )}
                        {(data.activity_details?.length || data.activities.length) > 5 && (
                          <span className="px-3 py-1.5 text-xs text-slate-400">
                            +{(data.activity_details?.length || data.activities.length) - 5} more
                          </span>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Segment Selector */}
                  {(() => {
                    // Define segments with display names - Row 1: specialty, Row 2: practice setting
                    const allSegments = SEGMENT_DEFS.map(s => ({ key: s.key, label: s.label }))
                    const segmentRows = [allSegments]

                    // Get available segments from data
                    const availableSegments = new Set(data.performance.map(p => p.segment))

                    return (
                      <div className="space-y-2 mb-4">
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
                                  className={`px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-all ${
                                    isSelected
                                      ? 'bg-primary-500 text-white shadow-lg shadow-primary-500/20'
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

                  {/* Performance Display */}
                  {selectedActivity === null ? (
                    // Combined performance across all activities
                    segmentPerf && (
                      <div className="bg-gradient-to-br from-slate-50 to-slate-100 rounded-xl p-6">
                        <div className="text-center mb-4">
                          <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-violet-100 text-violet-700 rounded-full text-xs font-medium">
                            <Activity className="w-3 h-3" />
                            Combined across {data.activity_details?.length || data.activities.length} activit{(data.activity_details?.length || data.activities.length) === 1 ? 'y' : 'ies'}
                          </span>
                        </div>

                        <div className="grid grid-cols-3 gap-6">
                          {/* Pre Score */}
                          <div className="text-center">
                            <p className="text-sm text-slate-500 mb-1">Pre-Test</p>
                            <p className="text-3xl font-bold text-slate-800">
                              {segmentPerf.pre_score?.toFixed(1) ?? '—'}%
                            </p>
                            {segmentPerf.pre_n && (
                              <p className="text-xs text-slate-400 mt-1">n = {segmentPerf.pre_n}</p>
                            )}
                          </div>

                          {/* Arrow / Gain */}
                          <div className="text-center flex flex-col items-center justify-center">
                            {segmentPerf.pre_score !== null && segmentPerf.post_score !== null && (
                              <>
                                <div className={`text-2xl font-bold ${
                                  segmentPerf.post_score - segmentPerf.pre_score > 0
                                    ? 'text-emerald-600'
                                    : 'text-red-500'
                                }`}>
                                  {segmentPerf.post_score - segmentPerf.pre_score > 0 ? '+' : ''}
                                  {(segmentPerf.post_score - segmentPerf.pre_score).toFixed(1)}%
                                </div>
                                <p className="text-xs text-slate-400 mt-1">Performance Change</p>
                              </>
                            )}
                          </div>

                          {/* Post Score */}
                          <div className="text-center">
                            <p className="text-sm text-slate-500 mb-1">Post-Test</p>
                            <p className="text-3xl font-bold text-slate-800">
                              {segmentPerf.post_score?.toFixed(1) ?? '—'}%
                            </p>
                            {segmentPerf.post_n && (
                              <p className="text-xs text-slate-400 mt-1">n = {segmentPerf.post_n}</p>
                            )}
                          </div>
                        </div>

                        {/* Visual Bar with Dots */}
                        {segmentPerf.pre_score !== null && segmentPerf.post_score !== null && (
                          <div className="mt-6">
                            <div className="h-3 bg-slate-200 rounded-full relative">
                              {/* Colored bar between pre and post scores */}
                              {(() => {
                                const preScore = segmentPerf.pre_score
                                const postScore = segmentPerf.post_score
                                const improved = postScore >= preScore
                                const left = Math.min(preScore, postScore)
                                const width = Math.abs(postScore - preScore)

                                return (
                                  <div
                                    className={`absolute h-full rounded-full transition-all duration-500 ${
                                      improved ? 'bg-emerald-400' : 'bg-red-400'
                                    }`}
                                    style={{
                                      left: `${left}%`,
                                      width: `${width}%`
                                    }}
                                  />
                                )
                              })()}

                              {/* Pre-test dot */}
                              <div
                                className="absolute top-1/2 -translate-y-1/2 w-5 h-5 bg-slate-500 border-2 border-white rounded-full shadow-md transition-all duration-500 z-10"
                                style={{ left: `${segmentPerf.pre_score}%`, transform: 'translate(-50%, -50%)' }}
                                title={`Pre-test: ${segmentPerf.pre_score.toFixed(1)}%`}
                              />

                              {/* Post-test dot */}
                              <div
                                className={`absolute top-1/2 -translate-y-1/2 w-5 h-5 border-2 border-white rounded-full shadow-md transition-all duration-500 z-10 ${
                                  segmentPerf.post_score >= segmentPerf.pre_score ? 'bg-emerald-500' : 'bg-red-500'
                                }`}
                                style={{ left: `${segmentPerf.post_score}%`, transform: 'translate(-50%, -50%)' }}
                                title={`Post-test: ${segmentPerf.post_score.toFixed(1)}%`}
                              />
                            </div>
                            <div className="flex justify-between text-xs text-slate-400 mt-3">
                              <span>0%</span>
                              <div className="flex items-center gap-4">
                                <span className="flex items-center gap-1">
                                  <span className="w-2.5 h-2.5 bg-slate-500 rounded-full"></span>
                                  Pre
                                </span>
                                <span className="flex items-center gap-1">
                                  <span className={`w-2.5 h-2.5 rounded-full ${
                                    segmentPerf.post_score >= segmentPerf.pre_score ? 'bg-emerald-500' : 'bg-red-500'
                                  }`}></span>
                                  Post
                                </span>
                              </div>
                              <span>100%</span>
                            </div>
                          </div>
                        )}
                      </div>
                    )
                  ) : (
                    // Single activity selected - show per-activity performance if available
                    (() => {
                      // Find the activity details
                      const activityInfo = data.activity_details?.find(a => a.activity_name === selectedActivity)
                      const activityPerf = activityInfo?.performance?.find(p => p.segment === selectedSegment)

                      if (activityPerf && (activityPerf.pre_score !== null || activityPerf.post_score !== null)) {
                        // Per-activity performance is available - display it
                        return (
                          <div className="bg-gradient-to-br from-violet-50 to-purple-50 rounded-xl p-6">
                            <div className="text-center mb-4">
                              <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-violet-100 text-violet-700 rounded-full text-xs font-medium">
                                <Activity className="w-3 h-3" />
                                {selectedActivity.length > 50 ? selectedActivity.substring(0, 50) + '...' : selectedActivity}
                              </span>
                              {activityInfo?.activity_date && (
                                <p className="text-xs text-slate-500 mt-2">
                                  {new Date(activityInfo.activity_date).toLocaleDateString('en-US', {
                                    year: 'numeric',
                                    month: 'long',
                                    day: 'numeric'
                                  })}
                                  {activityInfo.quarter && ` (${activityInfo.quarter})`}
                                </p>
                              )}
                            </div>

                            <div className="grid grid-cols-3 gap-6">
                              {/* Pre Score */}
                              <div className="text-center">
                                <p className="text-sm text-slate-500 mb-1">Pre-Test</p>
                                <p className="text-3xl font-bold text-slate-800">
                                  {activityPerf.pre_score?.toFixed(1) ?? '—'}%
                                </p>
                                {activityPerf.pre_n && (
                                  <p className="text-xs text-slate-400 mt-1">n = {activityPerf.pre_n}</p>
                                )}
                              </div>

                              {/* Arrow / Gain */}
                              <div className="text-center flex flex-col items-center justify-center">
                                {activityPerf.pre_score !== null && activityPerf.post_score !== null && (
                                  <>
                                    <div className={`text-2xl font-bold ${
                                      activityPerf.post_score - activityPerf.pre_score > 0
                                        ? 'text-emerald-600'
                                        : 'text-red-500'
                                    }`}>
                                      {activityPerf.post_score - activityPerf.pre_score > 0 ? '+' : ''}
                                      {(activityPerf.post_score - activityPerf.pre_score).toFixed(1)}%
                                    </div>
                                    <p className="text-xs text-slate-400 mt-1">Performance Change</p>
                                  </>
                                )}
                              </div>

                              {/* Post Score */}
                              <div className="text-center">
                                <p className="text-sm text-slate-500 mb-1">Post-Test</p>
                                <p className="text-3xl font-bold text-slate-800">
                                  {activityPerf.post_score?.toFixed(1) ?? '—'}%
                                </p>
                                {activityPerf.post_n && (
                                  <p className="text-xs text-slate-400 mt-1">n = {activityPerf.post_n}</p>
                                )}
                              </div>
                            </div>

                            {/* Visual Bar with Dots */}
                            {activityPerf.pre_score !== null && activityPerf.post_score !== null && (
                              <div className="mt-6">
                                <div className="h-3 bg-slate-200 rounded-full relative">
                                  {(() => {
                                    const preScore = activityPerf.pre_score
                                    const postScore = activityPerf.post_score
                                    const improved = postScore >= preScore
                                    const left = Math.min(preScore, postScore)
                                    const width = Math.abs(postScore - preScore)

                                    return (
                                      <div
                                        className={`absolute h-full rounded-full transition-all duration-500 ${
                                          improved ? 'bg-emerald-400' : 'bg-red-400'
                                        }`}
                                        style={{
                                          left: `${left}%`,
                                          width: `${width}%`
                                        }}
                                      />
                                    )
                                  })()}

                                  <div
                                    className="absolute top-1/2 -translate-y-1/2 w-5 h-5 bg-slate-500 border-2 border-white rounded-full shadow-md transition-all duration-500 z-10"
                                    style={{ left: `${activityPerf.pre_score}%`, transform: 'translate(-50%, -50%)' }}
                                    title={`Pre-test: ${activityPerf.pre_score.toFixed(1)}%`}
                                  />

                                  <div
                                    className={`absolute top-1/2 -translate-y-1/2 w-5 h-5 border-2 border-white rounded-full shadow-md transition-all duration-500 z-10 ${
                                      activityPerf.post_score >= activityPerf.pre_score ? 'bg-emerald-500' : 'bg-red-500'
                                    }`}
                                    style={{ left: `${activityPerf.post_score}%`, transform: 'translate(-50%, -50%)' }}
                                    title={`Post-test: ${activityPerf.post_score.toFixed(1)}%`}
                                  />
                                </div>
                                <div className="flex justify-between text-xs text-slate-400 mt-3">
                                  <span>0%</span>
                                  <div className="flex items-center gap-4">
                                    <span className="flex items-center gap-1">
                                      <span className="w-2.5 h-2.5 bg-slate-500 rounded-full"></span>
                                      Pre
                                    </span>
                                    <span className="flex items-center gap-1">
                                      <span className={`w-2.5 h-2.5 rounded-full ${
                                        activityPerf.post_score >= activityPerf.pre_score ? 'bg-emerald-500' : 'bg-red-500'
                                      }`}></span>
                                      Post
                                    </span>
                                  </div>
                                  <span>100%</span>
                                </div>
                              </div>
                            )}
                          </div>
                        )
                      } else {
                        // No per-activity performance data - show placeholder
                        return (
                          <div className="bg-gradient-to-br from-amber-50 to-orange-50 rounded-xl p-6 text-center">
                            <div className="mb-3">
                              <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-amber-100 text-amber-700 rounded-full text-xs font-medium">
                                <Activity className="w-3 h-3" />
                                {selectedActivity.length > 50 ? selectedActivity.substring(0, 50) + '...' : selectedActivity}
                              </span>
                              {activityInfo?.activity_date && (
                                <p className="text-xs text-slate-500 mt-2">
                                  {new Date(activityInfo.activity_date).toLocaleDateString('en-US', {
                                    year: 'numeric',
                                    month: 'long',
                                    day: 'numeric'
                                  })}
                                  {activityInfo?.quarter && ` (${activityInfo.quarter})`}
                                </p>
                              )}
                            </div>
                            <div className="py-6">
                              <AlertCircle className="w-10 h-10 text-amber-400 mx-auto mb-3" />
                              <p className="text-amber-800 font-medium">Per-activity performance data not available</p>
                              <p className="text-amber-600 text-sm mt-2">
                                The source data contains combined performance across all activities.<br/>
                                To see per-activity metrics, this data would need to be added to the source files.
                              </p>
                            </div>
                            <button
                              onClick={() => setSelectedActivity(null)}
                              className="mt-2 text-sm text-amber-700 hover:text-amber-800 font-medium underline"
                            >
                              View combined performance instead
                            </button>
                          </div>
                        )
                      }
                    })()
                  )}
                </div>
              )}

              {/* Activities */}
              {(data.activity_details?.length || data.activities.length) > 0 && (
                <div>
                  {/* Header with activity date range */}
                  <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-700 mb-3">
                    <Activity className="w-4 h-4" />
                    Activities ({data.activity_details?.length || data.activities.length})
                    {data.activity_details?.length && (() => {
                      const dates = data.activity_details
                        .map(a => a.activity_date)
                        .filter(Boolean)
                        .map(d => new Date(d!))
                        .sort((a, b) => a.getTime() - b.getTime())
                      if (dates.length > 0) {
                        const earliest = dates[0]
                        const latest = dates[dates.length - 1]
                        const formatDate = (d: Date) => d.toLocaleDateString('en-US', { month: 'short', year: 'numeric' })
                        return (
                          <span className="text-xs font-normal text-slate-400 ml-1">
                            ({formatDate(earliest)} - {formatDate(latest)})
                          </span>
                        )
                      }
                      return null
                    })()}
                  </h3>
                  <div className="space-y-2 max-h-60 overflow-y-auto">
                    {data.activity_details?.length ? (
                      // New format with activity details - sorted by date (newest first), then alphabetically
                      [...data.activity_details]
                        .sort((a, b) => {
                          // Sort by date descending (newest first)
                          if (a.activity_date && b.activity_date) {
                            const dateCompare = new Date(b.activity_date).getTime() - new Date(a.activity_date).getTime()
                            if (dateCompare !== 0) return dateCompare
                          } else if (a.activity_date) {
                            return -1 // a has date, b doesn't - a comes first
                          } else if (b.activity_date) {
                            return 1 // b has date, a doesn't - b comes first
                          }
                          // Then alphabetically
                          return a.activity_name.localeCompare(b.activity_name)
                        })
                        .map((activityInfo, i) => (
                        <div
                          key={i}
                          className="px-3 py-2 bg-slate-50 rounded-lg text-sm hover:bg-slate-100 transition-colors cursor-pointer"
                          onClick={() => setSelectedActivity(activityInfo.activity_name)}
                        >
                          <div className="flex items-start gap-3">
                            {/* Date badge - prominent */}
                            {activityInfo.activity_date && (
                              <span className="flex-shrink-0 px-2 py-1 bg-violet-100 text-violet-700 rounded text-xs font-medium whitespace-nowrap">
                                {new Date(activityInfo.activity_date).toLocaleDateString('en-US', {
                                  month: 'short',
                                  year: 'numeric'
                                })}
                              </span>
                            )}
                            <div className="flex-1 min-w-0">
                              <span className="text-slate-700 font-medium block truncate">{activityInfo.activity_name}</span>
                              {activityInfo.quarter && (
                                <span className="text-xs text-slate-400">{activityInfo.quarter}</span>
                              )}
                            </div>
                          </div>
                        </div>
                      ))
                    ) : (
                      // Legacy format - just activity names
                      data.activities.map((activity, i) => (
                        <div
                          key={i}
                          className="px-3 py-2 bg-slate-50 rounded-lg text-sm text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer"
                          onClick={() => setSelectedActivity(activity)}
                        >
                          {activity}
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}

              {/* Tags */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-700">
                      <Tag className="w-4 h-4" />
                      Tags
                    </h3>
                    {data.tags.worst_case_agreement && (
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => setShowAgreementLegend(true)}
                          className="p-0.5 hover:bg-slate-200 rounded transition-colors"
                          title="Agreement status legend"
                        >
                          <Info className="w-3.5 h-3.5 text-slate-400" />
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
                  {canEdit && !isEditing && !isEditingQuestion && (
                    <button
                      onClick={startEdit}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-primary-600 hover:bg-primary-50 rounded-lg transition-colors"
                    >
                      <Pencil className="w-3.5 h-3.5" />
                      Edit Tags
                    </button>
                  )}
                </div>

                <div className="space-y-2">
                  {isEditing ? (
                    // Edit Mode - All fields in collapsible groups
                    <>
                      {/* Core Classification */}
                      <div className="bg-slate-50 rounded-xl overflow-hidden">
                        <button
                          type="button"
                          onClick={() => {
                            setExpandedGroups(prev => {
                              const next = new Set(prev)
                              if (next.has('edit-core')) next.delete('edit-core')
                              else next.add('edit-core')
                              return next
                            })
                          }}
                          className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-100 transition-colors"
                        >
                          <span className="text-sm font-semibold text-slate-700">Core Classification</span>
                          {expandedGroups.has('edit-core') ? <ChevronDown className="w-4 h-4 text-slate-400" /> : <ChevronRight className="w-4 h-4 text-slate-400" />}
                        </button>
                        {expandedGroups.has('edit-core') && (
                          <div className="px-4 pb-3 border-t border-slate-200 space-y-1">
                            {renderTagInput("Disease State", "disease_state", "e.g., Breast cancer")}
                            {renderTagInput("Topic", "topic", "e.g., Treatment selection")}
                            {renderTagInput("Disease Stage", "disease_stage", "e.g., Metastatic")}
                            {renderTagInput("Disease Type 1", "disease_type_1", "e.g., HER2+")}
                            {renderTagInput("Disease Type 2", "disease_type_2", "e.g., HR+")}
                            {renderTagInput("Treatment Line", "treatment_line", "e.g., 1L, 2L+, Adjuvant")}
                          </div>
                        )}
                      </div>

                      {/* Multi-value Fields */}
                      <div className="bg-slate-50 rounded-xl overflow-hidden">
                        <button
                          type="button"
                          onClick={() => {
                            setExpandedGroups(prev => {
                              const next = new Set(prev)
                              if (next.has('edit-multi')) next.delete('edit-multi')
                              else next.add('edit-multi')
                              return next
                            })
                          }}
                          className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-100 transition-colors"
                        >
                          <span className="text-sm font-semibold text-slate-700">Treatments, Biomarkers & Trials</span>
                          {expandedGroups.has('edit-multi') ? <ChevronDown className="w-4 h-4 text-slate-400" /> : <ChevronRight className="w-4 h-4 text-slate-400" />}
                        </button>
                        {expandedGroups.has('edit-multi') && (
                          <div className="px-4 pb-3 border-t border-slate-200 space-y-1">
                            {renderTagInput("Treatment 1", "treatment_1", "e.g., pembrolizumab")}
                            {renderTagInput("Treatment 2", "treatment_2")}
                            {renderTagInput("Treatment 3", "treatment_3")}
                            {renderTagInput("Treatment 4", "treatment_4")}
                            {renderTagInput("Treatment 5", "treatment_5")}
                            {renderTagInput("Biomarker 1", "biomarker_1", "e.g., PD-L1")}
                            {renderTagInput("Biomarker 2", "biomarker_2")}
                            {renderTagInput("Biomarker 3", "biomarker_3")}
                            {renderTagInput("Biomarker 4", "biomarker_4")}
                            {renderTagInput("Biomarker 5", "biomarker_5")}
                            {renderTagInput("Trial 1", "trial_1", "e.g., KEYNOTE-522")}
                            {renderTagInput("Trial 2", "trial_2")}
                            {renderTagInput("Trial 3", "trial_3")}
                            {renderTagInput("Trial 4", "trial_4")}
                            {renderTagInput("Trial 5", "trial_5")}
                          </div>
                        )}
                      </div>

                      {/* Patient Characteristics */}
                      <div className="bg-slate-50 rounded-xl overflow-hidden">
                        <button
                          type="button"
                          onClick={() => {
                            setExpandedGroups(prev => {
                              const next = new Set(prev)
                              if (next.has('edit-patient')) next.delete('edit-patient')
                              else next.add('edit-patient')
                              return next
                            })
                          }}
                          className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-100 transition-colors"
                        >
                          <span className="text-sm font-semibold text-slate-700">Patient Characteristics</span>
                          {expandedGroups.has('edit-patient') ? <ChevronDown className="w-4 h-4 text-slate-400" /> : <ChevronRight className="w-4 h-4 text-slate-400" />}
                        </button>
                        {expandedGroups.has('edit-patient') && (
                          <div className="px-4 pb-3 border-t border-slate-200 space-y-1">
                            {renderTagInput("Treatment Eligibility", "treatment_eligibility")}
                            {renderTagInput("Age Group", "age_group", "e.g., Elderly (65+)")}
                            {renderTagInput("Organ Dysfunction", "organ_dysfunction")}
                            {renderTagInput("Fitness Status", "fitness_status", "e.g., Fit, Frail")}
                            {renderTagInput("Disease Specific Factor", "disease_specific_factor")}
                          </div>
                        )}
                      </div>

                      {/* Treatment Metadata */}
                      <div className="bg-slate-50 rounded-xl overflow-hidden">
                        <button
                          type="button"
                          onClick={() => {
                            setExpandedGroups(prev => {
                              const next = new Set(prev)
                              if (next.has('edit-treatment-meta')) next.delete('edit-treatment-meta')
                              else next.add('edit-treatment-meta')
                              return next
                            })
                          }}
                          className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-100 transition-colors"
                        >
                          <span className="text-sm font-semibold text-slate-700">Treatment Metadata</span>
                          {expandedGroups.has('edit-treatment-meta') ? <ChevronDown className="w-4 h-4 text-slate-400" /> : <ChevronRight className="w-4 h-4 text-slate-400" />}
                        </button>
                        {expandedGroups.has('edit-treatment-meta') && (
                          <div className="px-4 pb-3 border-t border-slate-200 space-y-1">
                            {renderTagInput("Drug Class 1", "drug_class_1", "e.g., EGFR TKI")}
                            {renderTagInput("Drug Class 2", "drug_class_2")}
                            {renderTagInput("Drug Class 3", "drug_class_3")}
                            {renderTagInput("Drug Target 1", "drug_target_1", "e.g., EGFR")}
                            {renderTagInput("Drug Target 2", "drug_target_2")}
                            {renderTagInput("Drug Target 3", "drug_target_3")}
                            {renderTagInput("Prior Therapy 1", "prior_therapy_1")}
                            {renderTagInput("Prior Therapy 2", "prior_therapy_2")}
                            {renderTagInput("Prior Therapy 3", "prior_therapy_3")}
                            {renderTagInput("Resistance Mechanism", "resistance_mechanism")}
                          </div>
                        )}
                      </div>

                      {/* Clinical Context */}
                      <div className="bg-slate-50 rounded-xl overflow-hidden">
                        <button
                          type="button"
                          onClick={() => {
                            setExpandedGroups(prev => {
                              const next = new Set(prev)
                              if (next.has('edit-clinical')) next.delete('edit-clinical')
                              else next.add('edit-clinical')
                              return next
                            })
                          }}
                          className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-100 transition-colors"
                        >
                          <span className="text-sm font-semibold text-slate-700">Clinical Context</span>
                          {expandedGroups.has('edit-clinical') ? <ChevronDown className="w-4 h-4 text-slate-400" /> : <ChevronRight className="w-4 h-4 text-slate-400" />}
                        </button>
                        {expandedGroups.has('edit-clinical') && (
                          <div className="px-4 pb-3 border-t border-slate-200 space-y-1">
                            {renderTagInput("Metastatic Site 1", "metastatic_site_1", "e.g., Brain")}
                            {renderTagInput("Metastatic Site 2", "metastatic_site_2")}
                            {renderTagInput("Metastatic Site 3", "metastatic_site_3")}
                            {renderTagInput("Symptom 1", "symptom_1", "e.g., Pain")}
                            {renderTagInput("Symptom 2", "symptom_2")}
                            {renderTagInput("Symptom 3", "symptom_3")}
                            {renderTagInput("Performance Status", "performance_status", "e.g., ECOG 0-1")}
                          </div>
                        )}
                      </div>

                      {/* Safety & Toxicity */}
                      <div className="bg-slate-50 rounded-xl overflow-hidden">
                        <button
                          type="button"
                          onClick={() => {
                            setExpandedGroups(prev => {
                              const next = new Set(prev)
                              if (next.has('edit-safety')) next.delete('edit-safety')
                              else next.add('edit-safety')
                              return next
                            })
                          }}
                          className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-100 transition-colors"
                        >
                          <span className="text-sm font-semibold text-slate-700">Safety & Toxicity</span>
                          {expandedGroups.has('edit-safety') ? <ChevronDown className="w-4 h-4 text-slate-400" /> : <ChevronRight className="w-4 h-4 text-slate-400" />}
                        </button>
                        {expandedGroups.has('edit-safety') && (
                          <div className="px-4 pb-3 border-t border-slate-200 space-y-1">
                            {renderTagInput("Toxicity Type 1", "toxicity_type_1")}
                            {renderTagInput("Toxicity Type 2", "toxicity_type_2")}
                            {renderTagInput("Toxicity Type 3", "toxicity_type_3")}
                            {renderTagInput("Toxicity Type 4", "toxicity_type_4")}
                            {renderTagInput("Toxicity Type 5", "toxicity_type_5")}
                            {renderTagInput("Toxicity Organ", "toxicity_organ")}
                            {renderTagInput("Toxicity Grade", "toxicity_grade", "e.g., Grade 3")}
                          </div>
                        )}
                      </div>

                      {/* Efficacy & Outcomes */}
                      <div className="bg-slate-50 rounded-xl overflow-hidden">
                        <button
                          type="button"
                          onClick={() => {
                            setExpandedGroups(prev => {
                              const next = new Set(prev)
                              if (next.has('edit-efficacy')) next.delete('edit-efficacy')
                              else next.add('edit-efficacy')
                              return next
                            })
                          }}
                          className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-100 transition-colors"
                        >
                          <span className="text-sm font-semibold text-slate-700">Efficacy & Outcomes</span>
                          {expandedGroups.has('edit-efficacy') ? <ChevronDown className="w-4 h-4 text-slate-400" /> : <ChevronRight className="w-4 h-4 text-slate-400" />}
                        </button>
                        {expandedGroups.has('edit-efficacy') && (
                          <div className="px-4 pb-3 border-t border-slate-200 space-y-1">
                            {renderTagInput("Efficacy Endpoint 1", "efficacy_endpoint_1", "e.g., OS, PFS")}
                            {renderTagInput("Efficacy Endpoint 2", "efficacy_endpoint_2")}
                            {renderTagInput("Efficacy Endpoint 3", "efficacy_endpoint_3")}
                            {renderTagInput("Outcome Context", "outcome_context")}
                            {renderTagInput("Clinical Benefit", "clinical_benefit")}
                          </div>
                        )}
                      </div>

                      {/* Evidence & Guidelines */}
                      <div className="bg-slate-50 rounded-xl overflow-hidden">
                        <button
                          type="button"
                          onClick={() => {
                            setExpandedGroups(prev => {
                              const next = new Set(prev)
                              if (next.has('edit-evidence')) next.delete('edit-evidence')
                              else next.add('edit-evidence')
                              return next
                            })
                          }}
                          className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-100 transition-colors"
                        >
                          <span className="text-sm font-semibold text-slate-700">Evidence & Guidelines</span>
                          {expandedGroups.has('edit-evidence') ? <ChevronDown className="w-4 h-4 text-slate-400" /> : <ChevronRight className="w-4 h-4 text-slate-400" />}
                        </button>
                        {expandedGroups.has('edit-evidence') && (
                          <div className="px-4 pb-3 border-t border-slate-200 space-y-1">
                            {renderTagInput("Guideline Source 1", "guideline_source_1", "e.g., NCCN")}
                            {renderTagInput("Guideline Source 2", "guideline_source_2")}
                            {renderTagInput("Evidence Type", "evidence_type", "e.g., Phase 3 RCT")}
                          </div>
                        )}
                      </div>

                      {/* Question Format & Quality */}
                      <div className="bg-slate-50 rounded-xl overflow-hidden">
                        <button
                          type="button"
                          onClick={() => {
                            setExpandedGroups(prev => {
                              const next = new Set(prev)
                              if (next.has('edit-quality')) next.delete('edit-quality')
                              else next.add('edit-quality')
                              return next
                            })
                          }}
                          className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-100 transition-colors"
                        >
                          <span className="text-sm font-semibold text-slate-700">Question Format & Quality</span>
                          {expandedGroups.has('edit-quality') ? <ChevronDown className="w-4 h-4 text-slate-400" /> : <ChevronRight className="w-4 h-4 text-slate-400" />}
                        </button>
                        {expandedGroups.has('edit-quality') && (
                          <div className="px-4 pb-3 border-t border-slate-200 space-y-1">
                            {renderTagInput("CME Outcome Level", "cme_outcome_level", "e.g., 3 - Knowledge")}
                            {renderTagInput("Data Response Type", "data_response_type")}
                            {renderTagInput("Stem Type", "stem_type", "e.g., Clinical vignette")}
                            {renderTagInput("Lead-in Type", "lead_in_type")}
                            {renderTagInput("Answer Format", "answer_format")}
                            {renderTagInput("Answer Length Pattern", "answer_length_pattern")}
                            {renderTagInput("Distractor Homogeneity", "distractor_homogeneity")}
                          </div>
                        )}
                      </div>

                      {/* Review Notes - for few-shot learning */}
                      <div className="bg-amber-50 rounded-xl overflow-hidden border border-amber-200">
                        <div className="px-4 py-3">
                          <label className="block text-sm font-semibold text-amber-800 mb-2">
                            Review Notes (for few-shot learning)
                          </label>
                          <textarea
                            value={reviewNotes}
                            onChange={(e) => setReviewNotes(e.target.value)}
                            placeholder="Add notes about tag corrections, reasoning, or patterns to help improve future LLM tagging..."
                            rows={3}
                            className="w-full px-3 py-2 text-sm border border-amber-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-amber-500 bg-white placeholder-amber-400"
                          />
                          <p className="text-xs text-amber-600 mt-1">
                            These notes will be saved with the question and can be used when creating few-shot examples.
                          </p>
                        </div>
                      </div>
                    </>
                  ) : (
                    // Read-Only Mode - Collapsible field groups
                    <>
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
                        hasData={!!(data.tags.topic || data.tags.disease_state || data.tags.disease_state_2 || data.tags.disease_stage || data.tags.disease_type_1 || data.tags.treatment_line)}
                      >
                        <TagBadge label="Disease State" value={data.tags.disease_state} confidence={data.tags.disease_state_confidence} tagField="disease_state" fieldKey="disease_state" color="bg-violet-100 text-violet-800" />
                        {/* Show secondary disease state if present (e.g., MM + NHL) - UPDATED 2026-01-29 */}
                        {data.tags.disease_state_2 && <TagBadge label="Disease State 2" value={data.tags.disease_state_2} tagField="disease_state" fieldKey="disease_state_2" color="bg-violet-100 text-violet-800" />}
                        <TagBadge label="Topic" value={data.tags.topic} confidence={data.tags.topic_confidence} tagField="topic" fieldKey="topic" color="bg-primary-100 text-primary-800" />
                        <TagBadge label="Disease Stage" value={data.tags.disease_stage} confidence={data.tags.disease_stage_confidence} tagField="disease_stage" fieldKey="disease_stage" color="bg-slate-200 text-slate-700" />
                        <TagBadge label="Disease Type" value={data.tags.disease_type_1} confidence={data.tags.disease_type_confidence} tagField="disease_type" fieldKey="disease_type_1" color="bg-slate-200 text-slate-700" />
                        {data.tags.disease_type_2 && <TagBadge label="Disease Type 2" value={data.tags.disease_type_2} tagField="disease_type" fieldKey="disease_type_2" color="bg-slate-200 text-slate-700" />}
                        <TagBadge label="Treatment Line" value={data.tags.treatment_line} confidence={data.tags.treatment_line_confidence} tagField="treatment_line" fieldKey="treatment_line" color="bg-orange-100 text-orange-800" />
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
                        hasData={!!(data.tags.treatment_1 || data.tags.biomarker_1 || data.tags.trial_1)}
                      >
                        {[1, 2, 3, 4, 5].map(i => {
                          const field = `treatment_${i}` as keyof typeof data.tags
                          return data.tags[field] && <TagBadge key={field} label={`Treatment ${i}`} value={data.tags[field] as string} confidence={i === 1 ? data.tags.treatment_confidence : undefined} tagField="treatment" fieldKey={field} color="bg-amber-100 text-amber-800" />
                        })}
                        {[1, 2, 3, 4, 5].map(i => {
                          const field = `biomarker_${i}` as keyof typeof data.tags
                          return data.tags[field] && <TagBadge key={field} label={`Biomarker ${i}`} value={data.tags[field] as string} confidence={i === 1 ? data.tags.biomarker_confidence : undefined} tagField="biomarker" fieldKey={field} color="bg-teal-100 text-teal-800" />
                        })}
                        {[1, 2, 3, 4, 5].map(i => {
                          const field = `trial_${i}` as keyof typeof data.tags
                          return data.tags[field] && <TagBadge key={field} label={`Trial ${i}`} value={data.tags[field] as string} confidence={i === 1 ? data.tags.trial_confidence : undefined} tagField="trial" fieldKey={field} color="bg-rose-100 text-rose-800" />
                        })}
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
                        hasData={!!(data.tags.drug_class_1 || data.tags.drug_target_1 || data.tags.prior_therapy_1 || data.tags.resistance_mechanism)}
                      >
                        {[1, 2, 3].map(i => {
                          const field = `drug_class_${i}` as keyof typeof data.tags
                          return data.tags[field] && <TagBadge key={field} label={`Drug Class ${i}`} value={data.tags[field] as string} tagField="drug_class" fieldKey={field} color="bg-cyan-100 text-cyan-800" />
                        })}
                        {[1, 2, 3].map(i => {
                          const field = `drug_target_${i}` as keyof typeof data.tags
                          return data.tags[field] && <TagBadge key={field} label={`Drug Target ${i}`} value={data.tags[field] as string} tagField="drug_target" fieldKey={field} color="bg-cyan-100 text-cyan-800" />
                        })}
                        {[1, 2, 3].map(i => {
                          const field = `prior_therapy_${i}` as keyof typeof data.tags
                          return data.tags[field] && <TagBadge key={field} label={`Prior Therapy ${i}`} value={data.tags[field] as string} tagField="prior_therapy" fieldKey={field} color="bg-cyan-100 text-cyan-800" />
                        })}
                        <TagBadge label="Resistance Mechanism" value={data.tags.resistance_mechanism} tagField="resistance_mechanism" fieldKey="resistance_mechanism" color="bg-cyan-100 text-cyan-800" />
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
                        hasData={!!(data.tags.treatment_eligibility || data.tags.age_group || data.tags.organ_dysfunction || data.tags.fitness_status || data.tags.disease_specific_factor)}
                      >
                        <TagBadge label="Treatment Eligibility" value={data.tags.treatment_eligibility} tagField="treatment_eligibility" fieldKey="treatment_eligibility" color="bg-indigo-100 text-indigo-800" />
                        <TagBadge label="Age Group" value={data.tags.age_group} tagField="age_group" fieldKey="age_group" color="bg-indigo-100 text-indigo-800" />
                        <TagBadge label="Organ Dysfunction" value={data.tags.organ_dysfunction} tagField="organ_dysfunction" fieldKey="organ_dysfunction" color="bg-indigo-100 text-indigo-800" />
                        <TagBadge label="Fitness Status" value={data.tags.fitness_status} tagField="fitness_status" fieldKey="fitness_status" color="bg-indigo-100 text-indigo-800" />
                        <TagBadge label="Disease Specific Factor" value={data.tags.disease_specific_factor} tagField="disease_specific_factor" fieldKey="disease_specific_factor" color="bg-indigo-100 text-indigo-800" />
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
                        hasData={!!(data.tags.metastatic_site_1 || data.tags.symptom_1 || data.tags.performance_status)}
                      >
                        {[1, 2, 3].map(i => {
                          const field = `metastatic_site_${i}` as keyof typeof data.tags
                          return data.tags[field] && <TagBadge key={field} label={`Metastatic Site ${i}`} value={data.tags[field] as string} tagField="metastatic_site" fieldKey={field} color="bg-pink-100 text-pink-800" />
                        })}
                        {[1, 2, 3].map(i => {
                          const field = `symptom_${i}` as keyof typeof data.tags
                          return data.tags[field] && <TagBadge key={field} label={`Symptom ${i}`} value={data.tags[field] as string} tagField="symptom" fieldKey={field} color="bg-pink-100 text-pink-800" />
                        })}
                        <TagBadge label="Performance Status" value={data.tags.performance_status} tagField="performance_status" fieldKey="performance_status" color="bg-pink-100 text-pink-800" />
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
                        hasData={!!(data.tags.toxicity_type_1 || data.tags.toxicity_organ || data.tags.toxicity_grade)}
                      >
                        {[1, 2, 3, 4, 5].map(i => {
                          const field = `toxicity_type_${i}` as keyof typeof data.tags
                          return data.tags[field] && <TagBadge key={field} label={`Toxicity Type ${i}`} value={data.tags[field] as string} tagField="toxicity_type" fieldKey={field} color="bg-red-100 text-red-800" />
                        })}
                        <TagBadge label="Toxicity Organ" value={data.tags.toxicity_organ} tagField="toxicity_organ" fieldKey="toxicity_organ" color="bg-red-100 text-red-800" />
                        <TagBadge label="Toxicity Grade" value={data.tags.toxicity_grade} tagField="toxicity_grade" fieldKey="toxicity_grade" color="bg-red-100 text-red-800" />
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
                        hasData={!!(data.tags.efficacy_endpoint_1 || data.tags.outcome_context || data.tags.clinical_benefit)}
                      >
                        {[1, 2, 3].map(i => {
                          const field = `efficacy_endpoint_${i}` as keyof typeof data.tags
                          return data.tags[field] && <TagBadge key={field} label={`Efficacy Endpoint ${i}`} value={data.tags[field] as string} tagField="efficacy_endpoint" fieldKey={field} color="bg-emerald-100 text-emerald-800" />
                        })}
                        <TagBadge label="Outcome Context" value={data.tags.outcome_context} tagField="outcome_context" fieldKey="outcome_context" color="bg-emerald-100 text-emerald-800" />
                        <TagBadge label="Clinical Benefit" value={data.tags.clinical_benefit} tagField="clinical_benefit" fieldKey="clinical_benefit" color="bg-emerald-100 text-emerald-800" />
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
                        hasData={!!(data.tags.guideline_source_1 || data.tags.evidence_type)}
                      >
                        {[1, 2].map(i => {
                          const field = `guideline_source_${i}` as keyof typeof data.tags
                          return data.tags[field] && <TagBadge key={field} label={`Guideline Source ${i}`} value={data.tags[field] as string} tagField="guideline_source" fieldKey={field} color="bg-blue-100 text-blue-800" />
                        })}
                        <TagBadge label="Evidence Type" value={data.tags.evidence_type} tagField="evidence_type" fieldKey="evidence_type" color="bg-blue-100 text-blue-800" />
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
                        hasData={!!(data.tags.cme_outcome_level || data.tags.stem_type || data.tags.answer_format)}
                      >
                        <TagBadge label="CME Outcome Level" value={data.tags.cme_outcome_level} tagField="cme_outcome_level" fieldKey="cme_outcome_level" color="bg-gray-100 text-gray-800" />
                        <TagBadge label="Data Response Type" value={data.tags.data_response_type} tagField="data_response_type" fieldKey="data_response_type" color="bg-gray-100 text-gray-800" />
                        <TagBadge label="Stem Type" value={data.tags.stem_type} tagField="stem_type" fieldKey="stem_type" color="bg-gray-100 text-gray-800" />
                        <TagBadge label="Lead-in Type" value={data.tags.lead_in_type} tagField="lead_in_type" fieldKey="lead_in_type" color="bg-gray-100 text-gray-800" />
                        <TagBadge label="Answer Format" value={data.tags.answer_format} tagField="answer_format" fieldKey="answer_format" color="bg-gray-100 text-gray-800" />
                        <TagBadge label="Answer Length Pattern" value={data.tags.answer_length_pattern} tagField="answer_length_pattern" fieldKey="answer_length_pattern" color="bg-gray-100 text-gray-800" />
                        <TagBadge label="Distractor Homogeneity" value={data.tags.distractor_homogeneity} tagField="distractor_homogeneity" fieldKey="distractor_homogeneity" color="bg-gray-100 text-gray-800" />
                        {/* Boolean flaw indicators */}
                        {data.tags.flaw_absolute_terms && <TagBadge label="Flaw: Absolute Terms" value="Yes" tagField="flaw" fieldKey="flaw_absolute_terms" color="bg-yellow-100 text-yellow-800" />}
                        {data.tags.flaw_grammatical_cue && <TagBadge label="Flaw: Grammatical Cue" value="Yes" tagField="flaw" fieldKey="flaw_grammatical_cue" color="bg-yellow-100 text-yellow-800" />}
                        {data.tags.flaw_implausible_distractor && <TagBadge label="Flaw: Implausible Distractor" value="Yes" tagField="flaw" fieldKey="flaw_implausible_distractor" color="bg-yellow-100 text-yellow-800" />}
                        {data.tags.flaw_clang_association && <TagBadge label="Flaw: Clang Association" value="Yes" tagField="flaw" fieldKey="flaw_clang_association" color="bg-yellow-100 text-yellow-800" />}
                        {data.tags.flaw_convergence_vulnerability && <TagBadge label="Flaw: Convergence Vulnerability" value="Yes" tagField="flaw" fieldKey="flaw_convergence_vulnerability" color="bg-yellow-100 text-yellow-800" />}
                        {data.tags.flaw_double_negative && <TagBadge label="Flaw: Double Negative" value="Yes" tagField="flaw" fieldKey="flaw_double_negative" color="bg-yellow-100 text-yellow-800" />}
                        {/* Computed fields */}
                        {data.tags.answer_option_count && <TagBadge label="Answer Options" value={String(data.tags.answer_option_count)} tagField="computed" fieldKey="answer_option_count" color="bg-gray-100 text-gray-800" />}
                        {data.tags.correct_answer_position && <TagBadge label="Correct Answer Position" value={data.tags.correct_answer_position} tagField="computed" fieldKey="correct_answer_position" color="bg-gray-100 text-gray-800" />}
                      </FieldGroupSection>

                      {/* Review Notes (if present) */}
                      {data.tags.review_notes && (
                        <div className="bg-amber-50 rounded-xl p-4 border border-amber-200">
                          <h4 className="text-sm font-semibold text-amber-800 mb-2">Review Notes</h4>
                          <p className="text-sm text-amber-700 whitespace-pre-wrap">{data.tags.review_notes}</p>
                        </div>
                      )}

                      {/* Show message if no tags */}
                      {!data.tags.disease_state && !data.tags.topic && !data.tags.treatment_1 && (
                        <div className="text-center py-4 bg-slate-50 rounded-xl">
                          <p className="text-slate-400 text-sm">No tags assigned yet</p>
                          {canEdit && (
                            <button
                              onClick={startEdit}
                              className="mt-2 text-sm text-primary-600 hover:text-primary-700 font-medium"
                            >
                              + Add tags
                            </button>
                          )}
                        </div>
                      )}
                    </>
                  )}
                </div>
              </div>

              {/* Source File */}
              {data.source_file && (
                <div className="text-xs text-slate-400 pt-4 border-t border-slate-100">
                  Source: {data.source_file}
                </div>
              )}
            </div>
          ) : (
            <div className="p-6 text-center text-slate-500">
              Failed to load question details
            </div>
          )}
        </div>
      </div>

      {/* Question Edit Warning Dialog */}
      {showQuestionWarning && (
        <>
          <div
            className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-[60]"
            onClick={() => setShowQuestionWarning(false)}
          />
          <div className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 z-[70] w-full max-w-md">
            <div className="bg-white rounded-2xl shadow-2xl p-6 mx-4">
              <div className="flex items-start gap-4 mb-4">
                <div className="flex-shrink-0 w-12 h-12 bg-amber-100 rounded-full flex items-center justify-center">
                  <AlertCircle className="w-6 h-6 text-amber-600" />
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-slate-900 mb-2">Edit Question Stem?</h3>
                  <p className="text-sm text-slate-600 leading-relaxed">
                    <strong>Warning:</strong> Only modify questions to correct grammar or spelling errors.
                    Changing the meaning or intent of the question may affect data integrity.
                  </p>
                  <p className="text-sm text-slate-600 mt-2">
                    Are you sure you would like to edit this question?
                  </p>
                </div>
              </div>
              <div className="flex gap-3 justify-end">
                <button
                  onClick={() => setShowQuestionWarning(false)}
                  className="px-4 py-2 text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors font-medium"
                >
                  Cancel
                </button>
                <button
                  onClick={confirmEditQuestion}
                  className="px-4 py-2 bg-amber-500 text-white hover:bg-amber-600 rounded-lg transition-colors font-medium"
                >
                  Yes, Edit Question
                </button>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Flag Question Dialog */}
      {showFlagDialog && (
        <>
          <div
            className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-[60]"
            onClick={() => {
              setShowFlagDialog(false)
              setSelectedFlagReasons([])
            }}
          />
          <div className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 z-[70] w-full max-w-md">
            <div className="bg-white rounded-2xl shadow-2xl p-6 mx-4">
              <div className="flex items-start gap-4 mb-4">
                <div className="flex-shrink-0 w-12 h-12 bg-amber-100 rounded-full flex items-center justify-center">
                  <Flag className="w-6 h-6 text-amber-600" />
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-slate-900 mb-2">Flag Question for Review</h3>
                  <p className="text-sm text-slate-600 leading-relaxed mb-4">
                    Please select one or more reasons for flagging this question:
                  </p>

                  {/* Flag Reasons Checkboxes */}
                  <div className="space-y-3">
                    <label className="flex items-start gap-3 cursor-pointer group">
                      <input
                        type="checkbox"
                        checked={selectedFlagReasons.includes('May not be an oncology question')}
                        onChange={() => toggleFlagReason('May not be an oncology question')}
                        className="mt-0.5 w-4 h-4 text-amber-600 bg-white border-slate-300 rounded focus:ring-2 focus:ring-amber-500"
                      />
                      <span className="text-sm text-slate-700 group-hover:text-slate-900">
                        May not be an oncology question
                      </span>
                    </label>

                    <label className="flex items-start gap-3 cursor-pointer group">
                      <input
                        type="checkbox"
                        checked={selectedFlagReasons.includes('Potential tag errors')}
                        onChange={() => toggleFlagReason('Potential tag errors')}
                        className="mt-0.5 w-4 h-4 text-amber-600 bg-white border-slate-300 rounded focus:ring-2 focus:ring-amber-500"
                      />
                      <span className="text-sm text-slate-700 group-hover:text-slate-900">
                        Potential tag errors
                      </span>
                    </label>

                    <label className="flex items-start gap-3 cursor-pointer group">
                      <input
                        type="checkbox"
                        checked={selectedFlagReasons.includes('Potential question errors')}
                        onChange={() => toggleFlagReason('Potential question errors')}
                        className="mt-0.5 w-4 h-4 text-amber-600 bg-white border-slate-300 rounded focus:ring-2 focus:ring-amber-500"
                      />
                      <span className="text-sm text-slate-700 group-hover:text-slate-900">
                        Potential question errors
                      </span>
                    </label>
                  </div>
                </div>
              </div>

              <div className="flex gap-3 justify-end">
                <button
                  onClick={() => {
                    setShowFlagDialog(false)
                    setSelectedFlagReasons([])
                  }}
                  disabled={saving}
                  className="px-4 py-2 text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors font-medium disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleFlagQuestion}
                  disabled={saving || selectedFlagReasons.length === 0}
                  className="px-4 py-2 bg-amber-500 text-white hover:bg-amber-600 rounded-lg transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {saving ? 'Flagging...' : 'Flag Question'}
                </button>
              </div>
            </div>
          </div>
        </>
      )}

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
              Note: The Question Explorer uses a different "Tag Status" computed from only 8 core tags (topic, disease_state, disease_stage, disease_type, treatment_line, treatment, biomarker, trial).
            </p>
          </div>
        </div>
      )}

      {/* Retagging Proposal Modal */}
      {showRetaggingModal && (
        <CreateProposalModal
          onClose={() => setShowRetaggingModal(false)}
          onCreated={() => {
            setShowRetaggingModal(false)
            // Navigate to proposals tab - use hash navigation
            window.location.hash = 'proposals'
          }}
        />
      )}

      {/* Dedup Cluster Modal */}
      {showDedupModal && data && (
        <CreateDedupClusterModal
          sourceQuestion={{
            id: questionId,
            source_id: data.source_id ? String(data.source_id) : null,
            question_stem: data.question_stem,
            correct_answer: data.correct_answer,
          }}
          onClose={() => setShowDedupModal(false)}
          onCreated={() => {
            setShowDedupModal(false)
            // Navigate to dedup review tab
            window.location.hash = 'dedup-review'
          }}
        />
      )}
    </>
  )
}
// Triggering HMR refresh
