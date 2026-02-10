/**
 * CreateProposalModal - Modal for creating a new retagging proposal
 *
 * Allows user to:
 * - Select a tag field from dropdown
 * - Enter the proposed value
 * - Enter a search query (auto-filled from value)
 * - Optionally add a reason
 * - Preview match count before creating
 */

import { useState, useEffect } from 'react'
import { X, Search, Tag, AlertCircle } from 'lucide-react'
import { createProposal, type TagProposal } from '../services/apiRouter'

interface CreateProposalModalProps {
  onClose: () => void
  onCreated: (proposal: TagProposal) => void
}

// Available tag fields organized by category
const TAG_FIELDS = {
  'Core Classification': [
    { value: 'topic', label: 'Topic' },
    { value: 'disease_state', label: 'Disease State' },
    { value: 'disease_stage', label: 'Disease Stage' },
    { value: 'disease_type_1', label: 'Disease Type 1' },
    { value: 'disease_type_2', label: 'Disease Type 2' },
    { value: 'treatment_line', label: 'Treatment Line' },
  ],
  'Treatments': [
    { value: 'treatment_1', label: 'Treatment 1' },
    { value: 'treatment_2', label: 'Treatment 2' },
    { value: 'treatment_3', label: 'Treatment 3' },
    { value: 'treatment_4', label: 'Treatment 4' },
    { value: 'treatment_5', label: 'Treatment 5' },
  ],
  'Biomarkers': [
    { value: 'biomarker_1', label: 'Biomarker 1' },
    { value: 'biomarker_2', label: 'Biomarker 2' },
    { value: 'biomarker_3', label: 'Biomarker 3' },
    { value: 'biomarker_4', label: 'Biomarker 4' },
    { value: 'biomarker_5', label: 'Biomarker 5' },
  ],
  'Clinical Trials': [
    { value: 'trial_1', label: 'Trial 1' },
    { value: 'trial_2', label: 'Trial 2' },
    { value: 'trial_3', label: 'Trial 3' },
  ],
  'Treatment Metadata': [
    { value: 'drug_class_1', label: 'Drug Class 1' },
    { value: 'drug_class_2', label: 'Drug Class 2' },
    { value: 'drug_class_3', label: 'Drug Class 3' },
    { value: 'drug_target_1', label: 'Drug Target 1' },
    { value: 'drug_target_2', label: 'Drug Target 2' },
    { value: 'drug_target_3', label: 'Drug Target 3' },
    { value: 'prior_therapy_1', label: 'Prior Therapy 1' },
    { value: 'prior_therapy_2', label: 'Prior Therapy 2' },
    { value: 'prior_therapy_3', label: 'Prior Therapy 3' },
    { value: 'resistance_mechanism', label: 'Resistance Mechanism' },
  ],
  'Clinical Context': [
    { value: 'metastatic_site_1', label: 'Metastatic Site 1' },
    { value: 'metastatic_site_2', label: 'Metastatic Site 2' },
    { value: 'symptom_1', label: 'Symptom 1' },
    { value: 'symptom_2', label: 'Symptom 2' },
    { value: 'performance_status', label: 'Performance Status' },
  ],
  'Patient Characteristics': [
    { value: 'treatment_eligibility', label: 'Treatment Eligibility' },
    { value: 'age_group', label: 'Age Group' },
    { value: 'organ_dysfunction', label: 'Organ Dysfunction' },
    { value: 'fitness_status', label: 'Fitness Status' },
    { value: 'disease_specific_factor', label: 'Disease Specific Factor' },
  ],
  'Safety/Toxicity': [
    { value: 'toxicity_type_1', label: 'Toxicity Type 1' },
    { value: 'toxicity_type_2', label: 'Toxicity Type 2' },
    { value: 'toxicity_organ', label: 'Toxicity Organ' },
    { value: 'toxicity_grade', label: 'Toxicity Grade' },
  ],
  'Efficacy/Outcomes': [
    { value: 'efficacy_endpoint_1', label: 'Efficacy Endpoint 1' },
    { value: 'efficacy_endpoint_2', label: 'Efficacy Endpoint 2' },
    { value: 'outcome_context', label: 'Outcome Context' },
    { value: 'clinical_benefit', label: 'Clinical Benefit' },
  ],
  'Evidence/Guidelines': [
    { value: 'guideline_source_1', label: 'Guideline Source 1' },
    { value: 'guideline_source_2', label: 'Guideline Source 2' },
    { value: 'evidence_type', label: 'Evidence Type' },
  ],
}

export default function CreateProposalModal({ onClose, onCreated }: CreateProposalModalProps) {
  const [fieldName, setFieldName] = useState('')
  const [proposedValue, setProposedValue] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [proposalReason, setProposalReason] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Auto-fill search query when proposed value changes
  useEffect(() => {
    if (proposedValue && !searchQuery) {
      setSearchQuery(proposedValue.toLowerCase())
    }
  }, [proposedValue])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!fieldName || !proposedValue || !searchQuery) {
      setError('Please fill in all required fields')
      return
    }

    setLoading(true)
    setError(null)
    try {
      const proposal = await createProposal({
        field_name: fieldName,
        proposed_value: proposedValue,
        search_query: searchQuery,
        proposal_reason: proposalReason || undefined,
      })
      onCreated(proposal)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create proposal')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl max-w-lg w-full mx-4">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <div className="flex items-center gap-2">
            <Tag className="h-5 w-5 text-primary-600" />
            <h2 className="text-lg font-semibold text-slate-900">Create Retagging Proposal</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-slate-100 rounded-lg transition-colors"
          >
            <X className="h-5 w-5 text-slate-500" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Field Selection */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Tag Field <span className="text-red-500">*</span>
            </label>
            <select
              value={fieldName}
              onChange={(e) => setFieldName(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              required
            >
              <option value="">Select a field...</option>
              {Object.entries(TAG_FIELDS).map(([category, fields]) => (
                <optgroup key={category} label={category}>
                  {fields.map((field) => (
                    <option key={field.value} value={field.value}>
                      {field.label}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
          </div>

          {/* Proposed Value */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Proposed Value <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={proposedValue}
              onChange={(e) => setProposedValue(e.target.value)}
              placeholder="e.g., Prophylaxis, daratumumab, KEYNOTE-024"
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              required
            />
            <p className="text-xs text-slate-500 mt-1">
              The exact value to set for matching questions
            </p>
          </div>

          {/* Search Query */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Search Query <span className="text-red-500">*</span>
            </label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="e.g., prophylaxis, daratumumab"
                className="w-full pl-9 pr-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                required
              />
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Keyword to search in question stems and correct answers
            </p>
          </div>

          {/* Reason (Optional) */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Reason (Optional)
            </label>
            <textarea
              value={proposalReason}
              onChange={(e) => setProposalReason(e.target.value)}
              placeholder="Why is this tag value being proposed?"
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              rows={2}
            />
          </div>

          {/* Error Message */}
          {error && (
            <div className="flex items-center gap-2 text-red-600 text-sm bg-red-50 px-3 py-2 rounded-lg">
              <AlertCircle className="h-4 w-4 flex-shrink-0" />
              {error}
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !fieldName || !proposedValue || !searchQuery}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Creating...' : 'Create & Find Matches'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
