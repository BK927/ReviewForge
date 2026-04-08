import { useState, useEffect } from 'react'
import { useApi } from '../hooks/useApi'
import { TopicsSkeleton } from './Skeleton'

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
  positive_count: number
  negative_count: number
  tier: number
  model: string
}

export function TopicAnalysis({ appId }: { appId: number }) {
  const api = useApi()
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState('')
  const [expandedTopic, setExpandedTopic] = useState<string | null>(null)
  const [nTopics, setNTopics] = useState(8)

  useEffect(() => {
    const cleanup = api.onProgress((data: any) => {
      if (data.type === 'analysis' && data.appId === appId) {
        setProgress(data.message ?? '')
      }
    })
    return () => { cleanup() }
  }, [appId])

  const runAnalysis = async () => {
    setLoading(true)
    setProgress('Starting analysis...')
    try {
      const res = await api.runAnalysis(appId, { n_topics: nTopics }) as AnalysisResult
      setResult(res)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
      setProgress('')
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
        <button onClick={runAnalysis} disabled={loading}>
          {loading ? progress || 'Analyzing...' : 'Run Analysis'}
        </button>
      </div>

      {loading && <TopicsSkeleton />}

      {result && (
        <div className="analysis-meta">
          <span>Model: {result.model}</span>
          <span>Tier: {result.tier}</span>
          <span>Reviews: {result.total_reviews}</span>
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
