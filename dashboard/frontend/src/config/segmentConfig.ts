export interface SegmentDef {
  key: string
  label: string
  colors: { pre: string; post: string }
}

export const SEGMENT_DEFS: SegmentDef[] = [
  { key: 'overall', label: 'All Learners', colors: { pre: '#93c5fd', post: '#1d4ed8' } },
  { key: 'ophthalmologist', label: 'Ophthalmologists', colors: { pre: '#c4b5fd', post: '#6d28d9' } },
  { key: 'optometrist', label: 'Optometrists', colors: { pre: '#6ee7b7', post: '#047857' } },
  { key: 'app', label: 'APPs/Technicians', colors: { pre: '#fdba74', post: '#c2410c' } },
  { key: 'pharmacist', label: 'Pharmacists', colors: { pre: '#f9a8d4', post: '#be185d' } },
]

export const SEGMENT_LABELS: Record<string, string> = Object.fromEntries(
  SEGMENT_DEFS.map(s => [s.key, s.label])
)

export const SEGMENT_COLORS: Record<string, { pre: string; post: string }> = Object.fromEntries(
  SEGMENT_DEFS.map(s => [s.key, s.colors])
)
