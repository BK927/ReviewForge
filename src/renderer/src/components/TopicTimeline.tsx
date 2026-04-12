import { useState } from 'react'
import ReactECharts from 'echarts-for-react'
import type { AnalysisResult, TopicTimelinePeriod } from './TopicAnalysis'

type Granularity = 'weekly' | 'monthly'

export function TopicTimeline({ analysisResult }: { analysisResult: AnalysisResult }) {
  const [granularity, setGranularity] = useState<Granularity>('monthly')
  const [sentiment, setSentiment] = useState<'positive' | 'negative'>('negative')

  const timeline = analysisResult.topics_over_time
  if (!timeline) return null

  const periods: TopicTimelinePeriod[] = timeline[granularity] ?? []
  if (periods.length === 0) return null

  const distKey = sentiment === 'positive' ? 'positive_topic_distribution' : 'negative_topic_distribution'

  // Collect all topic IDs and labels
  const topicSet = new Map<number, string>()
  for (const p of periods) {
    for (const d of p[distKey]) {
      if (!topicSet.has(d.topic_id)) {
        topicSet.set(d.topic_id, d.topic_label)
      }
    }
  }

  const topicIds = [...topicSet.keys()].sort((a, b) => a - b)
  const periodLabels = periods.map(p => p.period)

  // Build series: one per topic
  const colors = ['#ef4444', '#f97316', '#eab308', '#22c55e', '#3b82f6', '#8b5cf6', '#ec4899', '#14b8a6']
  const series = topicIds.map((tid, i) => ({
    name: topicSet.get(tid)!,
    type: 'line' as const,
    stack: 'total',
    areaStyle: { opacity: 0.4 },
    emphasis: { focus: 'series' as const },
    data: periods.map(p => {
      const entry = p[distKey].find(d => d.topic_id === tid)
      return entry?.count ?? 0
    }),
    color: colors[i % colors.length],
  }))

  const option = {
    tooltip: {
      trigger: 'axis' as const,
      axisPointer: { type: 'cross' as const },
    },
    legend: {
      data: topicIds.map(tid => topicSet.get(tid)!),
      bottom: 0,
    },
    grid: { top: 10, right: 20, bottom: 60, left: 50 },
    xAxis: {
      type: 'category' as const,
      boundaryGap: false,
      data: periodLabels,
      axisLabel: { rotate: periodLabels.length > 12 ? 45 : 0 },
    },
    yAxis: {
      type: 'value' as const,
      name: 'Reviews',
    },
    series,
  }

  return (
    <div className="topic-timeline">
      <h3>Topic Trend Over Time</h3>
      <div className="timeline-controls">
        <label>
          Granularity:
          <select value={granularity} onChange={e => setGranularity(e.target.value as Granularity)}>
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
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
      <ReactECharts option={option} style={{ height: 350 }} />
    </div>
  )
}
