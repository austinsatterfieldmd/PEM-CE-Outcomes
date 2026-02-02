import { useMemo } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine
} from 'recharts'
import type { TrendDataPoint } from '../types'

interface TrendLineChartProps {
  data: TrendDataPoint[]
  title?: string
  height?: number
  showPreScore?: boolean
}

// Color palette for different segments
const SEGMENT_COLORS = [
  '#6366f1', // indigo
  '#22c55e', // green
  '#f59e0b', // amber
  '#ec4899', // pink
  '#06b6d4', // cyan
  '#8b5cf6', // violet
  '#f97316', // orange
  '#14b8a6', // teal
]

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  
  return (
    <div className="bg-slate-900 border border-slate-700 rounded-lg p-3 shadow-xl">
      <p className="font-semibold text-white mb-2">{label}</p>
      <div className="space-y-1 text-sm">
        {payload.map((entry: any, idx: number) => (
          <div key={idx} className="flex items-center gap-2">
            <span 
              className="w-3 h-3 rounded-full" 
              style={{ backgroundColor: entry.color }}
            />
            <span className="text-slate-300">{entry.name}:</span>
            <span className="font-mono text-white">
              {entry.value !== null ? `${entry.value}%` : '—'}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function TrendLineChart({
  data,
  title,
  height = 400,
  showPreScore = true
}: TrendLineChartProps) {
  // Transform data for multi-line chart
  const { chartData, segments } = useMemo(() => {
    const quarters = [...new Set(data.map(d => d.quarter))].sort()
    const segmentNames = [...new Set(data.map(d => d.segment_value))]
    
    const chartData = quarters.map(quarter => {
      const point: Record<string, any> = { quarter }
      
      segmentNames.forEach(segment => {
        const match = data.find(d => d.quarter === quarter && d.segment_value === segment)
        if (match) {
          point[`${segment}_post`] = match.avg_post_score
          point[`${segment}_pre`] = match.avg_pre_score
          point[`${segment}_n`] = match.total_n
        }
      })
      
      return point
    })
    
    return { chartData, segments: segmentNames }
  }, [data])
  
  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 bg-slate-800/50 rounded-lg border border-slate-700">
        <p className="text-slate-400">No trend data available for the selected filters</p>
      </div>
    )
  }
  
  return (
    <div className="bg-slate-800/50 rounded-lg border border-slate-700 p-4">
      {title && (
        <h3 className="text-lg font-semibold text-white mb-4">{title}</h3>
      )}
      
      <ResponsiveContainer width="100%" height={height}>
        <LineChart
          data={chartData}
          margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis 
            dataKey="quarter" 
            tick={{ fill: '#94a3b8', fontSize: 12 }}
          />
          <YAxis 
            domain={[0, 100]}
            tick={{ fill: '#94a3b8', fontSize: 12 }}
            tickFormatter={(value) => `${value}%`}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend 
            wrapperStyle={{ paddingTop: 10 }}
            formatter={(value) => <span className="text-slate-300">{value}</span>}
          />
          <ReferenceLine y={70} stroke="#475569" strokeDasharray="5 5" label={{ value: '70%', fill: '#64748b', fontSize: 10 }} />
          
          {segments.map((segment, idx) => (
            <Line
              key={`${segment}_post`}
              type="monotone"
              dataKey={`${segment}_post`}
              name={`${segment} (Post)`}
              stroke={SEGMENT_COLORS[idx % SEGMENT_COLORS.length]}
              strokeWidth={2}
              dot={{ fill: SEGMENT_COLORS[idx % SEGMENT_COLORS.length], strokeWidth: 2, r: 4 }}
              activeDot={{ r: 6, strokeWidth: 2 }}
              connectNulls
            />
          ))}
          
          {showPreScore && segments.map((segment, idx) => (
            <Line
              key={`${segment}_pre`}
              type="monotone"
              dataKey={`${segment}_pre`}
              name={`${segment} (Pre)`}
              stroke={SEGMENT_COLORS[idx % SEGMENT_COLORS.length]}
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={{ fill: 'transparent', stroke: SEGMENT_COLORS[idx % SEGMENT_COLORS.length], strokeWidth: 2, r: 3 }}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
      
      {/* Summary stats */}
      <div className="mt-4 flex flex-wrap gap-4">
        {segments.map((segment, idx) => {
          const segmentData = data.filter(d => d.segment_value === segment)
          const latestPost = segmentData[segmentData.length - 1]?.avg_post_score
          const firstPost = segmentData[0]?.avg_post_score
          const change = latestPost !== null && firstPost !== null 
            ? latestPost - firstPost 
            : null
          
          return (
            <div 
              key={segment}
              className="flex items-center gap-2 bg-slate-900/50 rounded px-3 py-2"
            >
              <span 
                className="w-3 h-3 rounded-full" 
                style={{ backgroundColor: SEGMENT_COLORS[idx % SEGMENT_COLORS.length] }}
              />
              <span className="text-sm text-slate-300">{segment}</span>
              {change !== null && (
                <span className={`text-sm font-mono ${change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {change > 0 ? '+' : ''}{change.toFixed(1)}%
                </span>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}









