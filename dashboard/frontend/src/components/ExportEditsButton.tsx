import { useState, useEffect } from 'react'
import { CloudOff, Database, Cloud } from 'lucide-react'
import { checkVercelMode } from '../services/localEdits'

const isSupabase = import.meta.env.VITE_USE_SUPABASE === 'true'

/**
 * Export Edits Button Component
 *
 * Displays connection status indicator in the header:
 * - "Supabase" badge (green) when using Supabase backend
 * - "SQLite" badge (green) when connected to FastAPI backend
 * - "Read-Only" badge (gray) when in Vercel/offline mode (no backend)
 */
export function ExportEditsButton() {
  const [vercelMode, setVercelMode] = useState<boolean | null>(null)

  useEffect(() => {
    checkVercelMode().then(setVercelMode)
  }, [])

  // Still checking
  if (vercelMode === null) {
    return null
  }

  // Connected to backend (Supabase or SQLite)
  if (!vercelMode) {
    return (
      <div
        className="flex items-center gap-1.5 px-2.5 py-1 bg-emerald-600/80 text-white rounded-lg text-xs cursor-help"
        title={isSupabase ? "Connected to Supabase PostgreSQL. Changes are saved to the cloud." : "Connected to SQLite database. Changes are saved to the server."}
      >
        {isSupabase ? <Cloud className="w-3.5 h-3.5" /> : <Database className="w-3.5 h-3.5" />}
        <span className="hidden sm:inline">{isSupabase ? 'Supabase' : 'SQLite'}</span>
      </div>
    )
  }

  // Vercel/offline mode (no backend at all)
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
