import { useMemo } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  LabelList,
} from 'recharts'
import type { AggregatedMetric } from '../types'

type ChartFormat = 'single' | 'stacked' | 'grouped'

interface PerformanceBarChartProps {
  data: AggregatedMetric[]
  title?: string
  xAxisLabel?: string
  yAxisLabel?: string
  showPerformanceChange?: boolean
  height?: number
  compact?: boolean
  segments?: string[]
  chartFormat?: ChartFormat
  showN?: boolean
  whiteBackground?: boolean
}

// Segment colors for comparison view - lighter pre, darker post
const SEGMENT_COLORS: Record<string, { pre: string; post: string }> = {
  overall: { pre: '#93c5fd', post: '#1d4ed8' },           // Blue (light -> dark)
  medical_oncologist: { pre: '#c4b5fd', post: '#6d28d9' }, // Purple (light -> dark)
  surgical_oncologist: { pre: '#f9a8d4', post: '#be185d' }, // Pink (light -> dark)
  radiation_oncologist: { pre: '#fdba74', post: '#c2410c' }, // Orange (light -> dark)
  app: { pre: '#6ee7b7', post: '#047857' },               // Green (light -> dark)
  community: { pre: '#67e8f9', post: '#0e7490' },         // Cyan (light -> dark)
  academic: { pre: '#fca5a5', post: '#b91c1c' },          // Red (light -> dark)
}

// Segment display names
const SEGMENT_LABELS: Record<string, string> = {
  overall: 'All Learners',
  medical_oncologist: 'Med/Heme Oncs',
  surgical_oncologist: 'Surg Oncs',
  radiation_oncologist: 'Rad Oncs',
  app: 'APPs',
  community: 'Community',
  academic: 'Academic',
}

// Custom tooltip for charts
const ChartTooltip = ({ active, payload, label, whiteBackground }: any) => {
  if (!active || !payload?.length) return null

  return (
    <div className={`${whiteBackground ? 'bg-white border-gray-300' : 'bg-slate-900 border-slate-700'} border rounded-lg p-3 shadow-xl max-w-xs`}>
      <p className={`font-semibold ${whiteBackground ? 'text-gray-900' : 'text-white'} mb-2 text-sm`}>{label}</p>
      <div className="space-y-1.5 text-xs">
        {payload.map((entry: any, idx: number) => (
          <div key={idx} className="flex items-center gap-2">
            <span
              className="w-2.5 h-2.5 rounded-sm"
              style={{ backgroundColor: entry.color }}
            />
            <span className={whiteBackground ? 'text-gray-600' : 'text-slate-300'}>{entry.name}:</span>
            <span className={`font-mono ${whiteBackground ? 'text-gray-900' : 'text-white'}`}>
              {entry.value !== null && entry.value !== undefined ? `${entry.value}%` : '—'}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

// Custom percentage label renderer for bar tops
const renderPercentageLabel = (props: any) => {
  const { x, y, width, value } = props
  if (value === null || value === undefined) return null
  return (
    <text
      x={x + width / 2}
      y={y - 5}
      fill="#666"
      fontSize={10}
      fontWeight="500"
      textAnchor="middle"
    >
      {Math.round(value)}%
    </text>
  )
}

// Custom X-axis tick with N value
const CustomXAxisTick = ({ x, y, payload, data, whiteBackground, segments }: any) => {
  const item = data?.find((d: any) => d.displayName === payload.value || d.name === payload.value)

  const textColor = whiteBackground ? '#374151' : '#94a3b8'
  const nColor = whiteBackground ? '#6b7280' : '#64748b'

  // For grouped/segment charts, show individual N per segment
  if (item && segments && segments.length > 1) {
    const segmentNs: { label: string; n: number }[] = []
    segments.forEach((seg: string) => {
      const segN = item[`${seg}_n`]
      if (segN) {
        const shortLabel = SEGMENT_LABELS[seg]?.split(' ')[0] || seg // Get first word of label
        segmentNs.push({ label: shortLabel, n: segN })
      }
    })

    return (
      <g transform={`translate(${x},${y})`}>
        <text
          x={0}
          y={0}
          dy={12}
          textAnchor="end"
          fill={textColor}
          fontSize={11}
          transform="rotate(-45)"
        >
          {payload.value}
        </text>
        {segmentNs.map((seg, idx) => (
          <text
            key={seg.label}
            x={0}
            y={0}
            dy={26 + (idx * 11)}
            textAnchor="end"
            fill={nColor}
            fontSize={8}
            transform="rotate(-45)"
          >
            {seg.label}: N={seg.n.toLocaleString()}
          </text>
        ))}
      </g>
    )
  }

  // For single charts, show total N
  const totalN = item?.total_n || 0

  return (
    <g transform={`translate(${x},${y})`}>
      <text
        x={0}
        y={0}
        dy={12}
        textAnchor="end"
        fill={textColor}
        fontSize={11}
        transform="rotate(-45)"
      >
        {payload.value}
      </text>
      {totalN > 0 && (
        <text
          x={0}
          y={0}
          dy={26}
          textAnchor="end"
          fill={nColor}
          fontSize={9}
          transform="rotate(-45)"
        >
          (N={totalN.toLocaleString()})
        </text>
      )}
    </g>
  )
}

export default function PerformanceBarChart({
  data,
  title,
  xAxisLabel: _xAxisLabel,
  yAxisLabel = 'Score (%)',
  showPerformanceChange = true,
  height = 400,
  compact = false,
  segments,
  chartFormat = 'single',
  showN: _showN = false,
  whiteBackground = false
}: PerformanceBarChartProps) {
  // Check if this is segment comparison data
  const hasSegments = segments && segments.length > 1 && data.some(d => d.segment)

  // Transform data for different chart formats
  const chartData = useMemo(() => {
    const maxLength = compact ? 15 : 25

    if (hasSegments && segments) {
      // Group by group_value, then pivot segments into columns
      const grouped = new Map<string, any>()

      data.forEach(item => {
        if (!grouped.has(item.group_value)) {
          grouped.set(item.group_value, {
            name: item.group_value,
            displayName: item.group_value.length > maxLength
              ? item.group_value.slice(0, maxLength - 3) + '...'
              : item.group_value,
            _totalQuestions: 0,
          })
        }

        const row = grouped.get(item.group_value)!
        const seg = item.segment || 'overall'
        row[`${seg}_pre`] = item.avg_pre_score
        row[`${seg}_post`] = item.avg_post_score
        row[`${seg}_gain`] = item.knowledge_gain
        row[`${seg}_n`] = item.total_n
        row._totalQuestions = Math.max(row._totalQuestions, item.question_count)
      })

      // Convert to array and sort by total questions
      return Array.from(grouped.values())
        .sort((a, b) => b._totalQuestions - a._totalQuestions)
    }

    // Non-segment mode: original behavior
    return data.map(item => ({
      ...item,
      name: item.group_value,
      displayName: item.group_value.length > maxLength
        ? item.group_value.slice(0, maxLength - 3) + '...'
        : item.group_value
    }))
  }, [data, compact, hasSegments, segments])

  // Get data for a specific segment (for stacked format)
  const getSegmentData = (segment: string) => {
    return data
      .filter(d => d.segment === segment)
      .map(item => ({
        ...item,
        name: item.group_value,
        displayName: item.group_value.length > 25
          ? item.group_value.slice(0, 22) + '...'
          : item.group_value
      }))
  }

  if (data.length === 0) {
    return (
      <div className={`flex items-center justify-center h-64 ${whiteBackground ? 'bg-gray-50' : 'bg-slate-800/50'} rounded-lg border ${whiteBackground ? 'border-gray-200' : 'border-slate-700'}`}>
        <p className={whiteBackground ? 'text-gray-500' : 'text-slate-400'}>No data available for the selected filters</p>
      </div>
    )
  }

  // Text colors based on background
  const textColor = whiteBackground ? '#374151' : '#94a3b8'
  const _titleColor = whiteBackground ? '#111827' : '#ffffff'
  const gridColor = whiteBackground ? '#e5e7eb' : '#334155'

  // Stacked format: render multiple separate charts
  if (hasSegments && chartFormat === 'stacked' && segments) {
    return (
      <div className="space-y-8">
        {title && (
          <h3 className={`text-xl font-bold ${whiteBackground ? 'text-gray-900' : 'text-white'} text-center`}>
            {title}
          </h3>
        )}

        {segments.map(segment => {
          const segmentData = getSegmentData(segment)
          if (segmentData.length === 0) return null

          const colors = SEGMENT_COLORS[segment] || { pre: '#6366f1', post: '#22c55e' }
          const label = SEGMENT_LABELS[segment] || segment

          return (
            <div key={segment} className="space-y-2">
              <h4 className={`text-lg font-semibold ${whiteBackground ? 'text-gray-800' : 'text-white'} text-center`}>
                {label}
              </h4>
              <ResponsiveContainer width="100%" height={height}>
                <BarChart
                  data={segmentData}
                  margin={{ top: 30, right: 30, left: 20, bottom: 100 }}
                  barGap={2}
                  barCategoryGap="20%"
                >
                  <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
                  <XAxis
                    dataKey="displayName"
                    tick={(props) => <CustomXAxisTick {...props} data={segmentData} whiteBackground={whiteBackground} segments={null} />}
                    height={100}
                    interval={0}
                  />
                  <YAxis
                    domain={[0, 100]}
                    tick={{ fill: textColor, fontSize: 12 }}
                    tickFormatter={(value) => `${value}%`}
                    label={yAxisLabel ? { value: yAxisLabel, angle: -90, position: 'insideLeft', fill: textColor } : undefined}
                  />
                  <Tooltip content={<ChartTooltip whiteBackground={whiteBackground} />} />
                  <Legend
                    wrapperStyle={{ paddingTop: 10 }}
                    formatter={(value) => <span style={{ color: textColor }}>{value}</span>}
                  />
                  <Bar
                    dataKey="avg_pre_score"
                    name="Pre-Activity"
                    fill={colors.pre}
                    radius={[4, 4, 0, 0]}
                  >
                    <LabelList dataKey="avg_pre_score" content={renderPercentageLabel} />
                  </Bar>
                  <Bar
                    dataKey="avg_post_score"
                    name="Post-Activity"
                    fill={colors.post}
                    radius={[4, 4, 0, 0]}
                  >
                    <LabelList dataKey="avg_post_score" content={renderPercentageLabel} />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )
        })}
      </div>
    )
  }

  // Grouped format: all audiences side-by-side with Pre/Post for each
  if (hasSegments && chartFormat === 'grouped' && segments) {
    // Calculate dynamic bar size based on number of data points and segments
    const numCategories = chartData.length
    const numBarsPerCategory = segments.length * 2 // pre + post for each segment

    // Dynamic bar width: wider bars when fewer categories, narrower when many
    // Base width scales from ~25px (many bars) to ~50px (few bars)
    const dynamicBarSize = Math.max(12, Math.min(50, Math.floor(600 / (numCategories * numBarsPerCategory))))

    // Dynamic category gap: more space when fewer categories
    const dynamicCategoryGap = numCategories <= 4 ? '25%' : numCategories <= 6 ? '20%' : '15%'

    // Create paired bars with spacing - add invisible spacer bars between segments
    const renderGroupedBars = () => {
      const bars: JSX.Element[] = []
      segments.forEach((seg, segIndex) => {
        const colors = SEGMENT_COLORS[seg] || { pre: '#6366f1', post: '#22c55e' }
        const label = SEGMENT_LABELS[seg] || seg

        // Add spacer bar before each segment (except first) for visual separation
        if (segIndex > 0) {
          bars.push(
            <Bar
              key={`spacer_${segIndex}`}
              dataKey={() => null}
              name=""
              fill="transparent"
              barSize={Math.max(4, dynamicBarSize / 3)}
            />
          )
        }

        bars.push(
          <Bar
            key={`${seg}_pre`}
            dataKey={`${seg}_pre`}
            name={`${label} Pre`}
            fill={colors.pre}
            radius={[2, 2, 0, 0]}
            barSize={dynamicBarSize}
          >
            <LabelList dataKey={`${seg}_pre`} content={renderPercentageLabel} />
          </Bar>
        )
        bars.push(
          <Bar
            key={`${seg}_post`}
            dataKey={`${seg}_post`}
            name={`${label} Post`}
            fill={colors.post}
            radius={[2, 2, 0, 0]}
            barSize={dynamicBarSize}
          >
            <LabelList dataKey={`${seg}_post`} content={renderPercentageLabel} />
          </Bar>
        )
      })
      return bars
    }

    return (
      <div className={whiteBackground ? '' : 'bg-slate-800/50 rounded-lg border border-slate-700 p-4'}>
        {title && (
          <h3 className={`text-xl font-bold ${whiteBackground ? 'text-gray-900' : 'text-white'} mb-4 text-center`}>
            {title}
          </h3>
        )}

        <ResponsiveContainer width="100%" height={height}>
          <BarChart
            data={chartData}
            margin={{ top: 30, right: 30, left: 30, bottom: 100 + (segments.length * 10) }}
            barGap={2}
            barCategoryGap={dynamicCategoryGap}
          >
            <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
            <XAxis
              dataKey="displayName"
              tick={(props) => <CustomXAxisTick {...props} data={chartData} whiteBackground={whiteBackground} segments={segments} />}
              height={100 + (segments.length * 10)}
              interval={0}
            />
            <YAxis
              domain={[0, 100]}
              tick={{ fill: textColor, fontSize: 12 }}
              tickFormatter={(value) => `${value}%`}
              label={yAxisLabel ? { value: yAxisLabel, angle: -90, position: 'insideLeft', fill: textColor } : undefined}
            />
            <Tooltip content={<ChartTooltip whiteBackground={whiteBackground} />} />
            <Legend
              wrapperStyle={{ paddingTop: 5 }}
              formatter={(value) => <span style={{ color: textColor, fontSize: 11 }}>{value}</span>}
            />
            {renderGroupedBars()}
          </BarChart>
        </ResponsiveContainer>
      </div>
    )
  }

  // Single format (or single audience): Pre/Post bars per category
  if (compact) {
    return (
      <ResponsiveContainer width="100%" height={height}>
        <BarChart
          data={chartData}
          margin={{ top: 10, right: 10, left: 0, bottom: 40 }}
          barGap={1}
          barCategoryGap="15%"
        >
          <CartesianGrid strokeDasharray="3 3" stroke={gridColor} vertical={false} />
          <XAxis
            dataKey="displayName"
            tick={{ fill: textColor, fontSize: 10 }}
            angle={-45}
            textAnchor="end"
            height={50}
            interval={0}
          />
          <YAxis
            domain={[0, 100]}
            tick={{ fill: textColor, fontSize: 10 }}
            tickFormatter={(value) => `${value}%`}
            width={35}
          />
          <Tooltip content={<ChartTooltip whiteBackground={whiteBackground} />} />
          <Bar
            dataKey="avg_pre_score"
            name="Pre"
            fill="#6366f1"
            radius={[2, 2, 0, 0]}
          />
          <Bar
            dataKey="avg_post_score"
            name="Post"
            fill="#22c55e"
            radius={[2, 2, 0, 0]}
          />
        </BarChart>
      </ResponsiveContainer>
    )
  }

  // Full single chart
  return (
    <div className={whiteBackground ? '' : 'bg-slate-800/50 rounded-lg border border-slate-700 p-4'}>
      {title && (
        <h3 className={`text-xl font-bold ${whiteBackground ? 'text-gray-900' : 'text-white'} mb-4 text-center`}>
          {title}
        </h3>
      )}

      <ResponsiveContainer width="100%" height={height}>
        <BarChart
          data={chartData}
          margin={{ top: 30, right: 30, left: 20, bottom: 100 }}
          barGap={2}
          barCategoryGap="20%"
        >
          <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
          <XAxis
            dataKey="displayName"
            tick={(props) => <CustomXAxisTick {...props} data={chartData} whiteBackground={whiteBackground} segments={null} />}
            height={100}
            interval={0}
          />
          <YAxis
            domain={[0, 100]}
            tick={{ fill: textColor, fontSize: 12 }}
            tickFormatter={(value) => `${value}%`}
            label={yAxisLabel ? { value: yAxisLabel, angle: -90, position: 'insideLeft', fill: textColor } : undefined}
          />
          <Tooltip content={<ChartTooltip whiteBackground={whiteBackground} />} />
          <Legend
            wrapperStyle={{ paddingTop: 20 }}
            formatter={(value) => <span style={{ color: textColor }}>{value}</span>}
          />

          <Bar
            dataKey="avg_pre_score"
            name="Pre-Activity"
            fill="#6366f1"
            radius={[4, 4, 0, 0]}
          >
            <LabelList dataKey="avg_pre_score" content={renderPercentageLabel} />
          </Bar>
          <Bar
            dataKey="avg_post_score"
            name="Post-Activity"
            fill="#22c55e"
            radius={[4, 4, 0, 0]}
          >
            <LabelList dataKey="avg_post_score" content={renderPercentageLabel} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {showPerformanceChange && !whiteBackground && (
        <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2">
          {(chartData as any[]).slice(0, 12).map((item, idx) => (
            <div
              key={idx}
              className="bg-slate-900/50 rounded p-2 text-center"
            >
              <p className="text-xs text-slate-400 truncate" title={item.name}>
                {item.displayName}
              </p>
              <p className={`text-sm font-mono font-bold ${
                item.knowledge_gain !== null && item.knowledge_gain >= 0
                  ? 'text-green-400'
                  : 'text-red-400'
              }`}>
                {item.knowledge_gain !== null
                  ? `${item.knowledge_gain > 0 ? '+' : ''}${item.knowledge_gain}%`
                  : '—'
                }
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}






