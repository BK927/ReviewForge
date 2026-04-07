import { useEffect, useState } from 'react'
import ReactECharts from 'echarts-for-react'
import { useApi } from '../hooks/useApi'
import { getLanguageDisplayName } from '../lib/steam-languages'

const PLAYTIME_BRACKETS = [
  { label: '0-2h', min: 0, max: 120 },
  { label: '2-10h', min: 120, max: 600 },
  { label: '10-50h', min: 600, max: 3000 },
  { label: '50h+', min: 3000, max: Infinity }
]

export function SegmentAnalysis({ appId }: { appId: number }) {
  const api = useApi()
  const [reviews, setReviews] = useState<any[]>([])
  const [langFilter, setLangFilter] = useState('all')
  const [periodFilter, setPeriodFilter] = useState('all')
  const [playtimeFilter, setPlaytimeFilter] = useState('all')
  const [purchaseFilter, setPurchaseFilter] = useState('all')
  const [languages, setLanguages] = useState<string[]>([])

  useEffect(() => {
    const load = async () => {
      const filter: Record<string, unknown> = {}
      if (langFilter !== 'all') filter.language = langFilter

      // Period filter
      if (periodFilter !== 'all') {
        const now = Math.floor(Date.now() / 1000)
        const days = periodFilter === '30d' ? 30 : periodFilter === '90d' ? 90 : 365
        filter.period_start = now - days * 24 * 3600
      }

      // Playtime filter
      if (playtimeFilter !== 'all') {
        const bracket = PLAYTIME_BRACKETS.find(b => b.label === playtimeFilter)
        if (bracket) {
          filter.playtime_min = bracket.min
          if (bracket.max !== Infinity) filter.playtime_max = bracket.max
        }
      }

      // Purchase filter
      if (purchaseFilter === 'steam') filter.steam_purchase = 1
      else if (purchaseFilter === 'free') filter.received_for_free = 1

      const r = await api.getReviews(appId, filter) as any[]
      setReviews(r)

      const stats = await api.getGameStats(appId) as { languages: string[] }
      setLanguages(stats.languages)
    }
    load()
  }, [appId, langFilter, periodFilter, playtimeFilter, purchaseFilter])

  // Playtime bracket analysis (use full unfiltered brackets for comparison)
  const playtimeData = PLAYTIME_BRACKETS.map(bracket => {
    const inBracket = reviews.filter(r =>
      r.playtime_at_review >= bracket.min && r.playtime_at_review < bracket.max
    )
    const pos = inBracket.filter(r => r.voted_up).length
    return {
      label: bracket.label,
      total: inBracket.length,
      positive_rate: inBracket.length > 0 ? pos / inBracket.length : 0
    }
  })

  const playtimeOption = {
    tooltip: {
      trigger: 'axis',
      formatter: (p: any) => `${p[0].name}<br/>Positive: ${(p[0].value * 100).toFixed(1)}%<br/>Reviews: ${playtimeData[p[0].dataIndex].total}`
    },
    xAxis: { type: 'category' as const, data: playtimeData.map(d => d.label) },
    yAxis: { type: 'value' as const, max: 1, axisLabel: { formatter: (v: number) => `${(v * 100).toFixed(0)}%` } },
    series: [{ type: 'bar', data: playtimeData.map(d => d.positive_rate), color: '#60a5fa' }]
  }

  // Language positive rate
  const langStats = new Map<string, { pos: number; total: number }>()
  for (const r of reviews) {
    const entry = langStats.get(r.language) ?? { pos: 0, total: 0 }
    entry.total++
    if (r.voted_up) entry.pos++
    langStats.set(r.language, entry)
  }
  const langData = [...langStats.entries()]
    .map(([code, { pos, total }]) => ({ code, name: getLanguageDisplayName(code), rate: pos / total, total }))
    .sort((a, b) => b.total - a.total)
    .slice(0, 15)

  const langOption = {
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category' as const, data: langData.map(d => d.name), axisLabel: { rotate: 45 } },
    yAxis: { type: 'value' as const, max: 1, axisLabel: { formatter: (v: number) => `${(v * 100).toFixed(0)}%` } },
    series: [{
      type: 'bar',
      data: langData.map(d => ({
        value: d.rate,
        itemStyle: { color: d.rate >= 0.7 ? '#4ade80' : d.rate >= 0.4 ? '#fbbf24' : '#f87171' }
      }))
    }]
  }

  // Purchase type comparison
  const steamPurchase = reviews.filter(r => r.steam_purchase)
  const freeReceived = reviews.filter(r => r.received_for_free)
  const purchaseData = [
    { name: 'Steam Purchase', rate: steamPurchase.length > 0 ? steamPurchase.filter(r => r.voted_up).length / steamPurchase.length : 0, count: steamPurchase.length },
    { name: 'Free', rate: freeReceived.length > 0 ? freeReceived.filter(r => r.voted_up).length / freeReceived.length : 0, count: freeReceived.length }
  ]

  const purchaseOption = {
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category' as const, data: purchaseData.map(d => d.name) },
    yAxis: { type: 'value' as const, max: 1, axisLabel: { formatter: (v: number) => `${(v * 100).toFixed(0)}%` } },
    series: [{ type: 'bar', data: purchaseData.map(d => d.rate), color: '#a78bfa' }]
  }

  return (
    <div className="segment-analysis">
      <div className="filter-panel">
        <label>
          Language:
          <select value={langFilter} onChange={e => setLangFilter(e.target.value)}>
            <option value="all">All Languages</option>
            {languages.map(lang => (
              <option key={lang} value={lang}>{getLanguageDisplayName(lang)}</option>
            ))}
          </select>
        </label>
        <label>
          Period:
          <select value={periodFilter} onChange={e => setPeriodFilter(e.target.value)}>
            <option value="all">All Time</option>
            <option value="30d">Last 30 Days</option>
            <option value="90d">Last 90 Days</option>
            <option value="1y">Last Year</option>
          </select>
        </label>
        <label>
          Playtime:
          <select value={playtimeFilter} onChange={e => setPlaytimeFilter(e.target.value)}>
            <option value="all">All</option>
            <option value="0-2h">0-2h</option>
            <option value="2-10h">2-10h</option>
            <option value="10-50h">10-50h</option>
            <option value="50h+">50h+</option>
          </select>
        </label>
        <label>
          Purchase:
          <select value={purchaseFilter} onChange={e => setPurchaseFilter(e.target.value)}>
            <option value="all">All</option>
            <option value="steam">Steam Purchase</option>
            <option value="free">Free</option>
          </select>
        </label>
        <span className="filter-count">{reviews.length} reviews</span>
      </div>

      <div className="charts-grid">
        <div className="chart-card">
          <h3>Positive Rate by Playtime</h3>
          <ReactECharts option={playtimeOption} style={{ height: 300 }} />
        </div>
        <div className="chart-card">
          <h3>Positive Rate by Language</h3>
          <ReactECharts option={langOption} style={{ height: 300 }} />
        </div>
        <div className="chart-card">
          <h3>Purchase Type</h3>
          <ReactECharts option={purchaseOption} style={{ height: 300 }} />
        </div>
      </div>
    </div>
  )
}
