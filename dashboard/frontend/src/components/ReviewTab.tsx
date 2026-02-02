/**
 * ReviewTab - Unified review interface with sub-tabs
 *
 * Contains:
 * - Questions Needing Review (tag conflicts, flagged questions)
 * - Dedup Review (duplicate cluster management)
 * - Retagging Proposals (batch tag updates)
 * - LLM Eval (accuracy metrics dashboard)
 */

import { useState } from 'react'
import { ClipboardCheck, Layers, Tag, BarChart3 } from 'lucide-react'
import DedupReviewTab from './DedupReviewTab'
import ProposalListTab from './ProposalListTab'
import LLMEvalTab from './LLMEvalTab'

type ReviewSubTab = 'questions' | 'dedup' | 'retagging' | 'eval'

interface ReviewTabProps {
  // Props passed through for Questions Needing Review
  questionsContent: React.ReactNode
  initialSubTab?: ReviewSubTab
}

export default function ReviewTab({ questionsContent, initialSubTab = 'questions' }: ReviewTabProps) {
  const [activeSubTab, setActiveSubTab] = useState<ReviewSubTab>(initialSubTab)

  return (
    <div className="space-y-6">
      {/* Sub-tab Navigation */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200/60 p-2">
        <div className="flex gap-2 flex-wrap">
          <button
            onClick={() => setActiveSubTab('questions')}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg font-medium transition-all ${
              activeSubTab === 'questions'
                ? 'bg-primary-500 text-white shadow-sm'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            <ClipboardCheck className="w-4 h-4" />
            Questions Needing Review
          </button>
          <button
            onClick={() => setActiveSubTab('dedup')}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg font-medium transition-all ${
              activeSubTab === 'dedup'
                ? 'bg-primary-500 text-white shadow-sm'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            <Layers className="w-4 h-4" />
            Dedup Review
          </button>
          <button
            onClick={() => setActiveSubTab('retagging')}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg font-medium transition-all ${
              activeSubTab === 'retagging'
                ? 'bg-primary-500 text-white shadow-sm'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            <Tag className="w-4 h-4" />
            Retagging Proposals
          </button>
          <button
            onClick={() => setActiveSubTab('eval')}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg font-medium transition-all ${
              activeSubTab === 'eval'
                ? 'bg-primary-500 text-white shadow-sm'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            <BarChart3 className="w-4 h-4" />
            LLM Eval
          </button>
        </div>
      </div>

      {/* Sub-tab Content */}
      {activeSubTab === 'questions' && questionsContent}
      {activeSubTab === 'dedup' && <DedupReviewTab />}
      {activeSubTab === 'retagging' && <ProposalListTab />}
      {activeSubTab === 'eval' && <LLMEvalTab />}
    </div>
  )
}
