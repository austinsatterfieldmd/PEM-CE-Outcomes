import { useState, useEffect } from 'react'
import { FileText, Calendar, AlertCircle, CloudOff } from 'lucide-react'
import type { Stats } from '../types'
import { getPendingEditCount, exportPendingEdits, checkVercelMode } from '../services/localEdits'

interface StatsCardsProps {
  stats: Stats
  onNeedsReviewClick?: () => void
}

export function StatsCards({ stats, onNeedsReviewClick }: StatsCardsProps) {
  const [pendingEdits, setPendingEdits] = useState(0)
  const [isVercelMode, setIsVercelMode] = useState(false)

  useEffect(() => {
    checkVercelMode().then(setIsVercelMode)
    setPendingEdits(getPendingEditCount())

    const handleEditsChanged = (event: Event) => {
      const customEvent = event as CustomEvent<{ count: number }>
      setPendingEdits(customEvent.detail.count)
    }
    window.addEventListener('localEditsChanged', handleEditsChanged)
    return () => window.removeEventListener('localEditsChanged', handleEditsChanged)
  }, [])
  // Safeguard against undefined values and division by zero
  const totalQuestions = stats?.total_questions ?? 0
  const taggedQuestions = stats?.tagged_questions ?? 0
  const questionsNeedReview = stats?.questions_need_review ?? 0
  const totalActivities = stats?.total_activities ?? 0

  const taggedPercentage = totalQuestions > 0
    ? ((taggedQuestions / totalQuestions) * 100).toFixed(1)
    : '0.0'
  const needsReviewPercentage = totalQuestions > 0
    ? ((questionsNeedReview / totalQuestions) * 100).toFixed(1)
    : '0.0'

  const cards = [
    {
      label: 'Total Questions',
      value: totalQuestions.toLocaleString(),
      subtext: `${taggedPercentage}% tagged`,
      icon: FileText,
      bgColor: 'bg-blue-50',
      textColor: 'text-blue-600',
      clickable: false,
    },
    {
      label: 'Activities',
      value: totalActivities.toLocaleString(),
      subtext: 'Unique activities',
      icon: Calendar,
      bgColor: 'bg-amber-50',
      textColor: 'text-amber-600',
      clickable: false,
    },
    {
      label: 'Questions Needing Review',
      value: questionsNeedReview.toLocaleString(),
      subtext: `${needsReviewPercentage}% of total`,
      icon: AlertCircle,
      bgColor: 'bg-red-50',
      textColor: 'text-red-600',
      clickable: true,
      onClick: onNeedsReviewClick,
    },
  ]

  // Add pending edits card in Vercel mode
  if (isVercelMode) {
    cards.push({
      label: 'Pending Edits',
      value: pendingEdits.toLocaleString(),
      subtext: pendingEdits > 0 ? 'Click to export' : 'Saved locally',
      icon: CloudOff,
      bgColor: pendingEdits > 0 ? 'bg-emerald-50' : 'bg-slate-50',
      textColor: pendingEdits > 0 ? 'text-emerald-600' : 'text-slate-500',
      clickable: pendingEdits > 0,
      onClick: pendingEdits > 0 ? exportPendingEdits : undefined,
    })
  }

  return (
    <div className={`grid grid-cols-1 sm:grid-cols-2 ${isVercelMode ? 'lg:grid-cols-4' : 'lg:grid-cols-3'} gap-4`}>
      {cards.map((card, index) => (
        <div
          key={card.label}
          className={`bg-white rounded-2xl p-5 border border-slate-200/60 shadow-sm shadow-slate-200/50 animate-fade-in stagger-${index + 1} ${
            card.clickable ? 'cursor-pointer hover:shadow-md hover:border-slate-300 transition-all duration-200' : ''
          }`}
          style={{ opacity: 0 }}
          onClick={card.clickable ? card.onClick : undefined}
        >
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm font-medium text-slate-500">{card.label}</p>
              <p className="mt-1 text-2xl font-bold text-slate-900">{card.value}</p>
              <p className="mt-1 text-xs text-slate-400">{card.subtext}</p>
            </div>
            <div className={`p-3 rounded-xl ${card.bgColor}`}>
              <card.icon className={`w-5 h-5 ${card.textColor}`} />
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

