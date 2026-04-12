import { useState } from 'react'
import ReactECharts from 'echarts-for-react'
import type { AnalysisResult, SegmentTopicData } from './TopicAnalysis'

type SegmentAxis = 'playtime' | 'language' | 'steam_deck' | 'purchase_type'

const AXIS_LABELS: Record<SegmentAxis, string> = {
  playtime: 'Playtime',
  language: 'Language',
  steam_deck: 'Steam Deck',
  purchase_type: 'Purchase Type',
}

export function SegmentTopicHeatmap({ analysisResult }: { analysisResult: AnalysisResult }) {
  const [axis, setAxis] = useState<SegmentAxis>('playtime')
  const [sentiment, setSentiment] = useState<'positive' | 'negative'>('negative')

  const cross = analysisResult.segment_topic_cross
  if (!cross) return null

  const segments: SegmentTopicData[] = cross[axis] ?? []
  if (segments.length === 0) return <p>No segment data available for this axis.</p>

  // Collect all topic labels for the selected sentiment
  const distKey = sentiment === 'positive' ? 'positive_topic_distribution' : 'negative_topic_distribution'
  const topicSet = new Map<number, string>()
  for (const seg of segments) {
    for (const d of seg[distKey]) {
      if (!topicSet.has(d.topic_id)) {
        topicSet.set(d.topic_id, d.topic_label)
      }
    }
  }

  const topicIds = [...topicSet.keys()].sort((a, b) => a - b)
  const topicLabels = topicIds.map(id => topicSet.get(id)!)
  const segmentLabels = segments.map(s => s.segment_label)

  // Build heatmap data: [xIndex, yIndex, value]
  const data: [number, number, number][] = []
  let maxVal = 0
  for (let xi = 0; xi < segments.length; xi++) {
    const dist = segments[xi][distKey]
    const distMap = new Map(dist.map(d => [d.topic_id, d.count]))
    for (let yi = 0; yi < topicIds.length; yi++) {
      const val = distMap.get(topicIds[yi]) ?? 0
      data.push([xi, yi, val])
      if (val > maxVal) maxVal = val
    }
  }

  const option = {
    tooltip: {
      position: 'top' as const,
      formatter: (p: { value: [number, number, number] }) => {
        const seg = segmentLabels[p.value[0]]
        const topic = topicLabels[p.value[1]]
        return `${seg} × ${topic}<br/>Reviews: ${p.value[2]}`
      },
    },
    grid: { top: 10, right: 20, bottom: 60, left: 140 },
    xAxis: {
      type: 'category' as const,
      data: segmentLabels,
      axisLabel: { rotate: segmentLabels.length > 6 ? 30 : 0 },
    },
    yAxis: {
      type: 'category' as const,
      data: topicLabels,
    },
    visualMap: {
      min: 0,
      max: maxVal || 1,
      calculable: true,
      orient: 'horizontal' as const,
      left: 'center',
      bottom: 0,
      inRange: {
        color: sentiment === 'positive'
          ? ['#f0fdf4', '#22c55e']
          : ['#fef2f2', '#ef4444'],
      },
    },
    series: [{
      type: 'heatmap',
      data,
      label: {
        show: true,
        formatter: (p: { value: [number, number, number] }) => p.value[2] > 0 ? String(p.value[2]) : '',
      },
    }],
  }

  return (
    <div className="segment-topic-heatmap">
      <div className="heatmap-controls">
        <label>
          Segment axis:
          <select value={axis} onChange={e => setAxis(e.target.value as SegmentAxis)}>
            {(Object.keys(AXIS_LABELS) as SegmentAxis[]).map(a => (
              <option key={a} value={a}>{AXIS_LABELS[a]}</option>
            ))}
          </select>
        </label>
        <label>
          Sentiment:
          <select value={sentiment} onChange={e => setSentiment(e.target.value as 'positive' | 'negative')}>
            <option value="negative">Negative Topics</option>
            <option value="positive">Positive Topics</option>
          </select>
        </label>
      </div>
      <ReactECharts option={option} style={{ height: Math.max(200, topicLabels.length * 40 + 80) }} />
    </div>
  )
}
