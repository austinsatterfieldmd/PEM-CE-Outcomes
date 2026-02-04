import { useState, useEffect } from 'react'
import { CloudOff } from 'lucide-react'
import { checkVercelMode } from '../services/localEdits'

/**
 * Export Edits Button Component
 *
 * Displays a minimal read-only indicator in the header when running in Vercel mode.
 * Export functionality has been moved to the StatsCards component.
 */
export function ExportEditsButton() {
  const [vercelMode, setVercelMode] = useState(false)

  useEffect(() => {
    checkVercelMode().then(setVercelMode)
  }, [])

  // Don't show anything if not in Vercel mode
  if (!vercelMode) {
    return null
  }

  return (
    <div
      className="flex items-center gap-1.5 px-2.5 py-1 bg-slate-600/50 text-slate-300 rounded-lg text-xs cursor-help"
      title="Read-only mode: Edits saved locally. See Pending Edits card below."
    >
      <CloudOff className="w-3.5 h-3.5" />
      <span className="hidden sm:inline">Read-Only</span>
    </div>
  )
}

/**
 * Badge showing if a question has pending local edits
 */
export function LocalEditBadge({ questionId }: { questionId: number }) {
  const [hasPendingEdit, setHasPendingEdit] = useState(false)

  useEffect(() => {
    // Import dynamically to avoid circular deps
    import('../services/localEdits').then(({ getEditedQuestionIds }) => {
      setHasPendingEdit(getEditedQuestionIds().has(questionId))
    })

    const handleEditsChanged = () => {
      import('../services/localEdits').then(({ getEditedQuestionIds }) => {
        setHasPendingEdit(getEditedQuestionIds().has(questionId))
      })
    }

    window.addEventListener('localEditsChanged', handleEditsChanged)
    return () => window.removeEventListener('localEditsChanged', handleEditsChanged)
  }, [questionId])

  if (!hasPendingEdit) return null

  return (
    <span
      className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-amber-100 text-amber-700 rounded text-xs font-medium"
      title="This question has unsaved local edits"
    >
      <CloudOff className="w-3 h-3" />
      Local
    </span>
  )
}
