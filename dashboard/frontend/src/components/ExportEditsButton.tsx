import { useState, useEffect } from 'react'
import { Download, Cloud, CloudOff, Trash2 } from 'lucide-react'
import {
  getPendingEditCount,
  exportPendingEdits,
  clearPendingEdits,
  checkVercelMode
} from '../services/localEdits'

/**
 * Export Edits Button Component
 *
 * Displays in the header when running in Vercel (read-only) mode.
 * Shows count of pending local edits and provides export functionality.
 */
export function ExportEditsButton() {
  const [editCount, setEditCount] = useState(0)
  const [vercelMode, setVercelMode] = useState(false)
  const [showConfirmClear, setShowConfirmClear] = useState(false)

  // Check Vercel mode on mount and listen for edit changes
  useEffect(() => {
    // Check if we're in Vercel mode
    checkVercelMode().then(setVercelMode)

    // Get initial edit count
    setEditCount(getPendingEditCount())

    // Listen for edit changes
    const handleEditsChanged = (event: Event) => {
      const customEvent = event as CustomEvent<{ count: number }>
      setEditCount(customEvent.detail.count)
    }

    window.addEventListener('localEditsChanged', handleEditsChanged)
    return () => window.removeEventListener('localEditsChanged', handleEditsChanged)
  }, [])

  // Don't show anything if not in Vercel mode
  if (!vercelMode) {
    return null
  }

  const handleExport = () => {
    exportPendingEdits()
  }

  const handleClear = () => {
    setShowConfirmClear(true)
  }

  const confirmClear = () => {
    clearPendingEdits()
    setShowConfirmClear(false)
  }

  return (
    <div className="flex items-center gap-2">
      {/* Vercel Mode Indicator */}
      <div className="flex items-center gap-1.5 px-2 py-1 bg-amber-500/20 text-amber-200 rounded-lg text-xs">
        <CloudOff className="w-3.5 h-3.5" />
        <span className="font-medium">Read-Only Mode</span>
      </div>

      {/* Export Button with Edit Count */}
      {editCount > 0 ? (
        <div className="flex items-center">
          <button
            onClick={handleExport}
            className="flex items-center gap-2 px-3 py-1.5 bg-emerald-500 hover:bg-emerald-600 text-white rounded-l-lg font-medium transition-colors text-sm"
            title={`Export ${editCount} pending edit${editCount !== 1 ? 's' : ''} as JSON`}
          >
            <Download className="w-4 h-4" />
            Export Edits
            <span className="ml-1 px-1.5 py-0.5 bg-white/20 rounded-full text-xs">
              {editCount}
            </span>
          </button>
          <button
            onClick={handleClear}
            className="flex items-center gap-1 px-2 py-1.5 bg-slate-500 hover:bg-slate-600 text-white rounded-r-lg font-medium transition-colors text-sm border-l border-slate-400"
            title="Clear all pending edits"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      ) : (
        <div className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-500/30 text-slate-300 rounded-lg text-sm">
          <Cloud className="w-4 h-4" />
          <span>No pending edits</span>
        </div>
      )}

      {/* Clear Confirmation Modal */}
      {showConfirmClear && (
        <>
          <div
            className="fixed inset-0 bg-black/50 z-50"
            onClick={() => setShowConfirmClear(false)}
          />
          <div className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-white rounded-xl shadow-2xl p-6 z-50 max-w-md w-full mx-4">
            <h3 className="text-lg font-bold text-slate-900 mb-2">
              Clear All Pending Edits?
            </h3>
            <p className="text-slate-600 mb-4">
              This will permanently delete {editCount} pending edit{editCount !== 1 ? 's' : ''} from your browser.
              Make sure you've exported them first if you want to keep them.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowConfirmClear(false)}
                className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={confirmClear}
                className="px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg transition-colors"
              >
                Clear All
              </button>
            </div>
          </div>
        </>
      )}
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
