import { FileText, Calendar, AlertCircle } from 'lucide-react'
import type { Stats } from '../types'

interface StatsCardsProps {
  stats: Stats
  onNeedsReviewClick?: () => void
}

export function StatsCards({ stats, onNeedsReviewClick }: StatsCardsProps) {
  const taggedPercentage = ((stats.tagged_questions / stats.total_questions) * 100).toFixed(1)
  const needsReviewPercentage = ((stats.questions_need_review / stats.total_questions) * 100).toFixed(1)

  const cards = [
    {
      label: 'Total Questions',
      value: stats.total_questions.toLocaleString(),
      subtext: `${taggedPercentage}% tagged`,
      icon: FileText,
      bgColor: 'bg-blue-50',
      textColor: 'text-blue-600',
      clickable: false,
    },
    {
      label: 'Activities',
      value: stats.total_activities.toLocaleString(),
      subtext: 'Unique activities',
      icon: Calendar,
      bgColor: 'bg-amber-50',
      textColor: 'text-amber-600',
      clickable: false,
    },
    {
      label: 'Questions Needing Review',
      value: stats.questions_need_review.toLocaleString(),
      subtext: `${needsReviewPercentage}% of total`,
      icon: AlertCircle,
      bgColor: 'bg-red-50',
      textColor: 'text-red-600',
      clickable: true,
      onClick: onNeedsReviewClick,
    },
  ]

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
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

