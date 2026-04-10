import { useState, useEffect } from 'react'
import { useApi } from '../hooks/useApi'
import { AnalysisProgress, ProgressData } from './AnalysisProgress'
import { estimateLocalAnalysisMinutes } from '../lib/analysis-timing'

interface Topic {
  id: number
  label: string
  keywords: { word: string; score: number }[]
  review_count: number
  sample_reviews: string[]
}

interface AnalysisResult {
  positive_topics: Topic[]
  negative_topics: Topic[]
  total_reviews: number
  total_available?: number
  sampled?: boolean
  positive_count: number
  negative_count: number
  tier: number
  model: string
}

export function TopicAnalysis({ appId }: { appId: number }) {
  const api = useApi()
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState<ProgressData>({ stage: 'idle', percent: 0, message: '', elapsed_ms: 0 })
  const [error, setError] = useState<string | null>(null)
  const [expandedTopic, setExpandedTopic] = useState<string | null>(null)
  const [nTopics, setNTopics] = useState(8)
  const [reviewLimit, setReviewLimit] = useState<'all' | number>('all')
  const [totalReviews, setTotalReviews] = useState(0)

  useEffect(() => {
    setResult(null)
    setError(null)
    setProgress({ stage: 'idle', percent: 0, message: '', elapsed_ms: 0 })
    api.getGameStats(appId).then((stats: any) => {
      setTotalReviews(stats.total_collected ?? 0)
    })
  }, [appId])

  useEffect(() => {
    const cleanup = api.onProgress((data: any) => {
      if (data.type === 'analysis' && data.appId === appId) {
        setProgress({
          stage: data.stage ?? 'embedding',
          percent: data.percent ?? 0,
          message: data.message ?? '',
          elapsed_ms: data.elapsed_ms ?? 0
        })
      }
    })
    return () => { cleanup() }
  }, [appId])

  const effectiveCount = reviewLimit === 'all' ? totalReviews : Math.min(reviewLimit, totalReviews)
  const effectiveMinutes = estimateLocalAnalysisMinutes(effectiveCount)

  const runAnalysis = async () => {
    setLoading(true)
    setError(null)
    setProgress({ stage: 'idle', percent: 0, message: 'Starting analysis...', elapsed_ms: 0 })
    try {
      const config: Record<string, unknown> = { n_topics: nTopics }
      if (reviewLimit !== 'all') {
        config.maxReviews = reviewLimit
      }
      const res = await api.runAnalysis(appId, config) as AnalysisResult
      setResult(res)
    } catch (e) {
      console.error(e)
      setError(e instanceof Error ? e.message : 'Analysis failed. Check the developer console for details.')
    } finally {
      setLoading(false)
      setProgress({ stage: 'idle', percent: 0, message: '', elapsed_ms: 0 })
    }
  }

  const toggleTopic = (key: string) => {
    setExpandedTopic(expandedTopic === key ? null : key)
  }

  return (
    <div className="topic-analysis">
      <div className="analysis-controls">
        <label>
          Topics per group:
          <input type="number" value={nTopics} onChange={e => setNTopics(Number(e.target.value))} min={2} max={20} />
        </label>
        <label>
          Reviews to analyze:
          <select
            value={reviewLimit === 'all' ? 'all' : String(reviewLimit)}
            onChange={e => setReviewLimit(e.target.value === 'all' ? 'all' : Number(e.target.value))}
          >
            <option value="all">All ({totalReviews.toLocaleString()})</option>
            <option value="1000">1,000</option>
            <option value="3000">3,000</option>
            <option value="5000">5,000</option>
            <option value="10000">10,000</option>
          </select>
        </label>
        <button onClick={runAnalysis} disabled={loading}>
          {loading ? 'Analyzing...' : 'Run Analysis'}
        </button>
      </div>

      {!loading && effectiveCount > 3000 && (
        <div className="analysis-warning">
          Analyzing {effectiveCount.toLocaleString()} reviews may take approximately <strong>{effectiveMinutes} min</strong> on CPU. You can reduce the count above for faster results.
        </div>
      )}

      {error && (
        <div className="analysis-error">
          <strong>Analysis Error:</strong> {error}
        </div>
      )}

      {loading && <AnalysisProgress data={progress} />}

      {result && (
        <div className="analysis-meta">
          <span>Model: {result.model}</span>
          <span>Tier: {result.tier}</span>
          <span>Reviews: {result.total_reviews.toLocaleString()}{result.sampled ? ` (sampled from ${result.total_available?.toLocaleString()})` : ''}</span>
        </div>
      )}

      {result && (
        <div className="topics-grid">
          <div className="topic-column">
            <h3>Negative Topics ({result.negative_count} reviews)</h3>
            {result.negative_topics.map(topic => (
              <TopicCard
                key={`neg-${topic.id}`}
                topic={topic}
                type="negative"
                expanded={expandedTopic === `neg-${topic.id}`}
                onToggle={() => toggleTopic(`neg-${topic.id}`)}
              />
            ))}
          </div>
          <div className="topic-column">
            <h3>Positive Topics ({result.positive_count} reviews)</h3>
            {result.positive_topics.map(topic => (
              <TopicCard
                key={`pos-${topic.id}`}
                topic={topic}
                type="positive"
                expanded={expandedTopic === `pos-${topic.id}`}
                onToggle={() => toggleTopic(`pos-${topic.id}`)}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function TopicCard({ topic, type, expanded, onToggle }: {
  topic: Topic; type: string; expanded: boolean; onToggle: () => void
}) {
  return (
    <div className={`topic-card ${type}`}>
      <div className="topic-header" onClick={onToggle}>
        <span className="topic-label">{topic.label}</span>
        <span className="topic-count">{topic.review_count} reviews</span>
      </div>
      <div className="topic-keywords">
        {topic.keywords.map(kw => (
          <span key={kw.word} className="keyword-tag" style={{ opacity: 0.5 + kw.score * 0.5 }}>
            {kw.word}
          </span>
        ))}
      </div>
      {expanded && (
        <div className="topic-samples">
          <h4>Sample Reviews</h4>
          {topic.sample_reviews.map((review, i) => (
            <div key={i} className="sample-review">{review}</div>
          ))}
        </div>
      )}
    </div>
  )
}
