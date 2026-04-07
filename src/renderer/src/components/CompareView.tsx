import { useEffect, useState } from 'react'
import ReactECharts from 'echarts-for-react'
import { useApi } from '../hooks/useApi'

interface Props {
  appIds: [number, number]
}

interface CompareData {
  app_id: number
  app_name: string
  review_score_desc: string
  total_reviews: number
  positive_rate: number
  total_collected: number
  languages: string[]
}

export function CompareView({ appIds }: Props) {
  const api = useApi()
  const [data, setData] = useState<[CompareData, CompareData] | null>(null)

  useEffect(() => {
    const load = async () => {
      const results = await Promise.all(appIds.map(async id => {
        const [game, stats] = await Promise.all([
          api.getGame(id) as Promise<any>,
          api.getGameStats(id) as Promise<any>
        ])
        return { ...game, ...stats } as CompareData
      }))
      setData(results as [CompareData, CompareData])
    }
    load()
  }, [appIds[0], appIds[1]])

  if (!data) return <div className="loading">Loading comparison...</div>

  const [a, b] = data

  const compareOption = {
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category' as const, data: ['Positive Rate (%)', 'Total Reviews (log10)'] },
    yAxis: { type: 'value' as const },
    series: [
      { name: a.app_name, type: 'bar', data: [+(a.positive_rate * 100).toFixed(1), +Math.log10(a.total_reviews + 1).toFixed(2)], color: '#60a5fa' },
      { name: b.app_name, type: 'bar', data: [+(b.positive_rate * 100).toFixed(1), +Math.log10(b.total_reviews + 1).toFixed(2)], color: '#f472b6' }
    ],
    legend: { show: true }
  }

  return (
    <div className="compare-view">
      <h2>Comparison</h2>
      <table className="compare-table">
        <thead>
          <tr><th></th><th>{a.app_name}</th><th>{b.app_name}</th></tr>
        </thead>
        <tbody>
          <tr><td>Score</td><td>{a.review_score_desc}</td><td>{b.review_score_desc}</td></tr>
          <tr><td>Total Reviews</td><td>{a.total_reviews.toLocaleString()}</td><td>{b.total_reviews.toLocaleString()}</td></tr>
          <tr><td>Collected</td><td>{a.total_collected.toLocaleString()}</td><td>{b.total_collected.toLocaleString()}</td></tr>
          <tr><td>Positive Rate</td><td>{(a.positive_rate * 100).toFixed(1)}%</td><td>{(b.positive_rate * 100).toFixed(1)}%</td></tr>
          <tr><td>Languages</td><td>{a.languages.length}</td><td>{b.languages.length}</td></tr>
        </tbody>
      </table>
      <ReactECharts option={compareOption} style={{ height: 300 }} />
    </div>
  )
}
