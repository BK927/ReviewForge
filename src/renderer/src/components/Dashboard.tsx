import { useEffect, useState } from 'react'
import ReactECharts from 'echarts-for-react'
import { useApi } from '../hooks/useApi'
import { useCountUp } from '../hooks/useCountUp'
import { CollectionProgress } from './CollectionProgress'
import { getLanguageDisplayName } from '../lib/steam-languages'

interface GameStats {
  total_collected: number
  positive_count: number
  negative_count: number
  positive_rate: number
  languages: string[]
}

interface Game {
  app_id: number
  app_name: string
  review_score: number
  review_score_desc: string
  total_positive: number
  total_negative: number
  total_reviews: number
}

export function Dashboard({ appId }: { appId: number }) {
  const api = useApi()
  const [game, setGame] = useState<Game | null>(null)
  const [stats, setStats] = useState<GameStats | null>(null)
  const [reviews, setReviews] = useState<any[]>([])
  const [trendMode, setTrendMode] = useState<'daily' | 'weekly' | 'monthly'>('daily')

  const loadData = async () => {
    const [g, s, r] = await Promise.all([
      api.getGame(appId) as Promise<Game>,
      api.getGameStats(appId) as Promise<GameStats>,
      api.getReviews(appId) as Promise<any[]>
    ])
    setGame(g)
    setStats(s)
    setReviews(r)
  }

  useEffect(() => { loadData() }, [appId])

  if (!game || !stats) return <div className="loading">Loading...</div>

  // Donut chart: positive/negative
  const donutOption = {
    tooltip: { trigger: 'item' },
    animationDuration: 400,
    animationEasing: 'cubicOut',
    series: [{
      type: 'pie',
      radius: ['45%', '70%'],
      data: [
        { value: stats.positive_count, name: 'Positive', itemStyle: { color: '#4ade80' } },
        { value: stats.negative_count, name: 'Negative', itemStyle: { color: '#f87171' } }
      ],
      label: { formatter: '{b}: {d}%' }
    }]
  }

  // Time trend: group reviews by day/week/month
  const bucketKey = (ts: number): string => {
    const date = new Date(ts * 1000)
    if (trendMode === 'monthly') return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
    if (trendMode === 'weekly') {
      const d = new Date(date)
      d.setDate(d.getDate() - d.getDay())
      return d.toISOString().slice(0, 10)
    }
    return date.toISOString().slice(0, 10)
  }

  const trendCounts = new Map<string, { pos: number; neg: number }>()
  for (const r of reviews) {
    const key = bucketKey(r.timestamp_created)
    const entry = trendCounts.get(key) ?? { pos: 0, neg: 0 }
    r.voted_up ? entry.pos++ : entry.neg++
    trendCounts.set(key, entry)
  }
  const sortedKeys = [...trendCounts.keys()].sort()
  const trendOption = {
    tooltip: { trigger: 'axis' },
    animationDuration: 400,
    animationEasing: 'cubicOut',
    animationDelay: (idx: number) => idx * 100,
    xAxis: { type: 'category' as const, data: sortedKeys },
    yAxis: { type: 'value' as const },
    series: [
      { name: 'Positive', type: 'bar', stack: 'total', data: sortedKeys.map(d => trendCounts.get(d)!.pos), color: '#4ade80' },
      { name: 'Negative', type: 'bar', stack: 'total', data: sortedKeys.map(d => trendCounts.get(d)!.neg), color: '#f87171' }
    ]
  }

  // Language distribution
  const langCounts = new Map<string, number>()
  for (const r of reviews) {
    langCounts.set(r.language, (langCounts.get(r.language) ?? 0) + 1)
  }
  const langSorted = [...langCounts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 15)
  const langOption = {
    tooltip: { trigger: 'axis' },
    animationDuration: 400,
    animationEasing: 'cubicOut',
    animationDelay: (idx: number) => idx * 100,
    xAxis: { type: 'category' as const, data: langSorted.map(([code]) => getLanguageDisplayName(code)), axisLabel: { rotate: 30 } },
    yAxis: { type: 'value' as const },
    series: [{ type: 'bar', data: langSorted.map(([, count]) => count), color: '#60a5fa' }]
  }

  // Last-30-day comparison
  const now = Math.floor(Date.now() / 1000)
  const thirtyDaysAgo = now - 30 * 24 * 3600
  const recent = reviews.filter(r => r.timestamp_created >= thirtyDaysAgo)
  const recentPosRate = recent.length > 0 ? recent.filter(r => r.voted_up).length / recent.length : null

  const animatedCollected = useCountUp(stats.total_collected)
  const animatedPositiveRate = useCountUp(Math.round(stats.positive_rate * 1000))
  const recentPosRateRaw = recentPosRate !== null ? Math.round(recentPosRate * 1000) : 0
  const animatedRecentRate = useCountUp(recentPosRateRaw)

  return (
    <div className="dashboard">
      <div className="game-info-card">
        <h2>{game.app_name}</h2>
        <div className="score-badge">{game.review_score_desc}</div>
        <div className="stats-row">
          <span>Total on Steam: {game.total_reviews.toLocaleString()}</span>
          <span>Collected: {animatedCollected.toLocaleString()}</span>
          <span>All-time positive: {(animatedPositiveRate / 10).toFixed(1)}%</span>
          {recentPosRate !== null && (
            <span>Last 30d positive: {(animatedRecentRate / 10).toFixed(1)}%</span>
          )}
        </div>
      </div>

      <CollectionProgress appId={appId} onComplete={loadData} />

      <div className="charts-grid">
        <div className="chart-card">
          <h3>Positive / Negative</h3>
          <ReactECharts option={donutOption} style={{ height: 300 }} />
        </div>
        <div className="chart-card">
          <div className="chart-header">
            <h3>Review Trend</h3>
            <div className="trend-toggle">
              {(['daily', 'weekly', 'monthly'] as const).map(m => (
                <button
                  key={m}
                  className={trendMode === m ? 'active' : ''}
                  onClick={() => setTrendMode(m)}
                >
                  {m[0].toUpperCase() + m.slice(1)}
                </button>
              ))}
            </div>
          </div>
          <ReactECharts option={trendOption} style={{ height: 300 }} />
        </div>
        <div className="chart-card">
          <h3>Language Distribution</h3>
          <ReactECharts option={langOption} style={{ height: 300 }} />
        </div>
      </div>
    </div>
  )
}
