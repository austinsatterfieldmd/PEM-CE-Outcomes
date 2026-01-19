// Question type
export interface Question {
  id: number
  question_stem: string
  correct_answer?: string
  incorrect_answers?: string[]
  topic?: string
  topic_confidence?: number
  disease_state?: string
  disease_state_confidence?: number
  disease_stage?: string
  disease_type?: string
  treatment_line?: string
  treatment?: string
  biomarker?: string
  trial?: string
  pre_score?: number
  post_score?: number
  knowledge_gain?: number
  sample_size?: number
  activity_count?: number
  needs_review?: boolean
  review_flags?: string[]
}

// Tags structure
export interface Tags {
  topic?: string
  disease_state?: string
  disease_stage?: string
  disease_type?: string
  treatment_line?: string
  treatment?: string
  biomarker?: string
  trial?: string
}

// V3 Voting Types
export interface ModelVote {
  model: 'gpt' | 'claude' | 'gemini'
  tags: Tags
  confidence?: number
  reasoning?: string
}

export interface VotingResult {
  id: number
  question_id: number
  iteration: number
  prompt_version: string
  gpt_tags: Tags
  claude_tags: Tags
  gemini_tags: Tags
  aggregated_tags: Tags
  agreement_level: 'unanimous' | 'majority' | 'conflict'
  needs_review: boolean
  web_searches?: WebSearch[]
  created_at: string
}

export interface WebSearch {
  query: string
  result: string
  used_for?: string
}

export interface ReviewQuestion {
  question_id: number
  question_text: string
  correct_answer?: string
  agreement_level: 'unanimous' | 'majority' | 'conflict'
  iteration: number
  gpt_tags: Tags
  claude_tags: Tags
  gemini_tags: Tags
  aggregated_tags: Tags
  created_at: string
}

export interface ReviewCorrection {
  question_id: number
  iteration: number
  corrected_tags: Tags
  disagreement_category?: string
  reviewer_notes?: string
}

export interface DisagreementPattern {
  id: number
  category: string
  frequency: number
  example_questions: number[]
  implemented: boolean
}

// Tagging job types
export interface TaggingJob {
  job_id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: TaggingProgress
  started_at?: string
  completed_at?: string
  error_message?: string
}

export interface TaggingProgress {
  total_questions: number
  completed: number
  in_progress: number
  failed: number
  unanimous_count: number
  majority_count: number
  conflict_count: number
  estimated_cost: number
}

// Filter options
export interface FilterOptions {
  topics: FilterOption[]
  disease_states: FilterOption[]
  disease_stages: FilterOption[]
  disease_types: FilterOption[]
  treatment_lines: FilterOption[]
  treatments: FilterOption[]
  biomarkers: FilterOption[]
  trials: FilterOption[]
  activities: FilterOption[]
}

export interface FilterOption {
  value: string
  count: number
}

// Search filters
export interface SearchFilters {
  topics?: string[]
  disease_states?: string[]
  disease_stages?: string[]
  disease_types?: string[]
  treatment_lines?: string[]
  treatments?: string[]
  biomarkers?: string[]
  trials?: string[]
  activities?: string[]
  min_confidence?: number
  max_confidence?: number
  has_performance_data?: boolean
  min_sample_size?: number
  needs_review?: boolean
}

// Dashboard stats
export interface Stats {
  total_questions: number
  tagged_questions: number
  total_activities: number
  questions_need_review: number
}

// Review queue stats
export interface ReviewStats {
  queue_size: number
  corrections_submitted: number
  by_iteration: Record<number, number>
  by_category: Record<string, number>
  avg_review_time_seconds: number
}

// Tagging stats
export interface TaggingStats {
  total_tagged: number
  by_agreement: Record<string, number>
  by_iteration: Record<number, number>
  review_pending: number
  total_api_cost: number
  avg_cost_per_question: number
}
