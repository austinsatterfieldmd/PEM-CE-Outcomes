import { useState, useEffect } from 'react'
import { 
  Calendar, 
  Users, 
  FileText, 
  Save, 
  X, 
  ChevronDown,
  ChevronRight,
  AlertCircle,
  CheckCircle
} from 'lucide-react'
import { getActivities, updateActivity } from '../services/apiRouter'
import type { Activity } from '../types'
import { clsx } from 'clsx'

interface ActivityManagerProps {
  onClose?: () => void
}

export default function ActivityManager({ onClose }: ActivityManagerProps) {
  const [activities, setActivities] = useState<Activity[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [saving, setSaving] = useState<number | null>(null)
  const [saveStatus, setSaveStatus] = useState<{ id: number; success: boolean; message: string } | null>(null)
  
  // Edit state
  const [editDate, setEditDate] = useState<string>('')
  const [editAudience, setEditAudience] = useState<string>('')
  const [editDescription, setEditDescription] = useState<string>('')
  
  // Filter state
  const [filterHasDate, setFilterHasDate] = useState<boolean | undefined>(undefined)
  
  // Load activities
  useEffect(() => {
    loadActivities()
  }, [filterHasDate])
  
  const loadActivities = async () => {
    setLoading(true)
    try {
      const result = await getActivities({ has_date: filterHasDate })
      setActivities(result.activities)
    } catch (err) {
      console.error('Failed to load activities:', err)
    } finally {
      setLoading(false)
    }
  }
  
  // Expand activity for editing
  const handleExpand = (activity: Activity) => {
    if (expandedId === activity.id) {
      setExpandedId(null)
    } else {
      setExpandedId(activity.id)
      setEditDate(activity.activity_date || '')
      setEditAudience(activity.target_audience || '')
      setEditDescription(activity.description || '')
    }
  }
  
  // Save activity
  const handleSave = async (activity: Activity) => {
    setSaving(activity.id)
    setSaveStatus(null)
    
    try {
      await updateActivity(activity.activity_name, {
        activity_date: editDate || undefined,
        target_audience: editAudience || undefined,
        description: editDescription || undefined
      })
      
      setSaveStatus({ id: activity.id, success: true, message: 'Saved successfully!' })
      
      // Refresh the list
      await loadActivities()
    } catch (err) {
      setSaveStatus({ 
        id: activity.id, 
        success: false, 
        message: err instanceof Error ? err.message : 'Failed to save' 
      })
    } finally {
      setSaving(null)
    }
  }
  
  // Stats
  const totalActivities = activities.length
  const activitiesWithDates = activities.filter(a => a.activity_date).length
  const activitiesWithAudience = activities.filter(a => a.target_audience).length
  
  return (
    <div className="bg-slate-800/50 rounded-lg border border-slate-700 p-4">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-semibold text-white">Activity Metadata Manager</h2>
          <p className="text-sm text-slate-400">
            Configure dates, target audiences, and descriptions for activities
          </p>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="p-2 hover:bg-slate-700 rounded-lg text-slate-400 hover:text-white transition-colors"
          >
            <X size={20} />
          </button>
        )}
      </div>
      
      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-4">
        <div className="bg-slate-900/50 rounded-lg p-3">
          <div className="text-2xl font-bold text-white">{totalActivities}</div>
          <div className="text-xs text-slate-400">Total Activities</div>
        </div>
        <div className="bg-slate-900/50 rounded-lg p-3">
          <div className="text-2xl font-bold text-green-400">{activitiesWithDates}</div>
          <div className="text-xs text-slate-400">With Dates</div>
        </div>
        <div className="bg-slate-900/50 rounded-lg p-3">
          <div className="text-2xl font-bold text-indigo-400">{activitiesWithAudience}</div>
          <div className="text-xs text-slate-400">With Target Audience</div>
        </div>
      </div>
      
      {/* Filter */}
      <div className="flex items-center gap-2 mb-4">
        <span className="text-sm text-slate-400">Show:</span>
        <button
          onClick={() => setFilterHasDate(undefined)}
          className={clsx(
            'px-3 py-1 rounded text-sm transition-colors',
            filterHasDate === undefined
              ? 'bg-indigo-500 text-white'
              : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
          )}
        >
          All
        </button>
        <button
          onClick={() => setFilterHasDate(true)}
          className={clsx(
            'px-3 py-1 rounded text-sm transition-colors',
            filterHasDate === true
              ? 'bg-indigo-500 text-white'
              : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
          )}
        >
          With Dates
        </button>
        <button
          onClick={() => setFilterHasDate(false)}
          className={clsx(
            'px-3 py-1 rounded text-sm transition-colors',
            filterHasDate === false
              ? 'bg-indigo-500 text-white'
              : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
          )}
        >
          Missing Dates
        </button>
      </div>
      
      {/* Activity List */}
      {loading ? (
        <div className="text-center py-8 text-slate-400">Loading activities...</div>
      ) : activities.length === 0 ? (
        <div className="text-center py-8 text-slate-400">No activities found</div>
      ) : (
        <div className="space-y-2 max-h-[500px] overflow-y-auto">
          {activities.map(activity => (
            <div
              key={activity.id}
              className="bg-slate-900/50 rounded-lg border border-slate-700 overflow-hidden"
            >
              {/* Activity Header */}
              <button
                onClick={() => handleExpand(activity)}
                className="w-full flex items-center justify-between p-3 hover:bg-slate-800/50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  {expandedId === activity.id ? (
                    <ChevronDown size={16} className="text-slate-400" />
                  ) : (
                    <ChevronRight size={16} className="text-slate-400" />
                  )}
                  <div className="text-left">
                    <div className="text-sm font-medium text-white truncate max-w-md">
                      {activity.activity_name}
                    </div>
                    <div className="text-xs text-slate-400">
                      {activity.question_count} questions
                      {activity.quarter && ` • ${activity.quarter}`}
                    </div>
                  </div>
                </div>
                
                <div className="flex items-center gap-2">
                  {activity.activity_date && (
                    <span className="px-2 py-1 bg-green-500/20 text-green-400 rounded text-xs flex items-center gap-1">
                      <Calendar size={12} />
                      {activity.activity_date}
                    </span>
                  )}
                  {activity.target_audience && (
                    <span className="px-2 py-1 bg-indigo-500/20 text-indigo-400 rounded text-xs flex items-center gap-1">
                      <Users size={12} />
                      {activity.target_audience.slice(0, 20)}
                    </span>
                  )}
                </div>
              </button>
              
              {/* Expanded Edit Form */}
              {expandedId === activity.id && (
                <div className="p-4 border-t border-slate-700 space-y-4">
                  {/* Date Input */}
                  <div>
                    <label className="flex items-center gap-2 text-sm text-slate-400 mb-1">
                      <Calendar size={14} />
                      Activity Date
                    </label>
                    <input
                      type="date"
                      value={editDate}
                      onChange={(e) => setEditDate(e.target.value)}
                      className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>
                  
                  {/* Target Audience Input */}
                  <div>
                    <label className="flex items-center gap-2 text-sm text-slate-400 mb-1">
                      <Users size={14} />
                      Target Audience (Key Learners)
                    </label>
                    <input
                      type="text"
                      value={editAudience}
                      onChange={(e) => setEditAudience(e.target.value)}
                      placeholder="e.g., Medical Oncologists, NP/PA"
                      className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>
                  
                  {/* Description Input */}
                  <div>
                    <label className="flex items-center gap-2 text-sm text-slate-400 mb-1">
                      <FileText size={14} />
                      Description
                    </label>
                    <textarea
                      value={editDescription}
                      onChange={(e) => setEditDescription(e.target.value)}
                      placeholder="Brief description of the activity..."
                      rows={2}
                      className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
                    />
                  </div>
                  
                  {/* Save Status */}
                  {saveStatus && saveStatus.id === activity.id && (
                    <div className={clsx(
                      'flex items-center gap-2 text-sm rounded-lg p-2',
                      saveStatus.success 
                        ? 'bg-green-500/20 text-green-400' 
                        : 'bg-red-500/20 text-red-400'
                    )}>
                      {saveStatus.success ? (
                        <CheckCircle size={16} />
                      ) : (
                        <AlertCircle size={16} />
                      )}
                      {saveStatus.message}
                    </div>
                  )}
                  
                  {/* Save Button */}
                  <div className="flex justify-end">
                    <button
                      onClick={() => handleSave(activity)}
                      disabled={saving === activity.id}
                      className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-800 disabled:cursor-not-allowed rounded-lg text-white font-medium transition-colors"
                    >
                      <Save size={16} />
                      {saving === activity.id ? 'Saving...' : 'Save Changes'}
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}









