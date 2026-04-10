import { useState, useEffect } from 'react'
import { useApi } from '../hooks/useApi'
import { AnalysisProgress, ProgressData } from './AnalysisProgress'
import { estimateLocalAnalysisMinutes } from '../lib/analysis-timing'
import { TopicCountMode, TopicCountModeControl } from './TopicCountModeControl'

export interface Topic {
  id: number
  label: string
  keywords: { word: string; score: number }[]
  review_count: number
  sample_reviews: string[]
}

export interface AnalysisResult {
  positive_topics: Topic[]
  negative_topics: Topic[]
  total_reviews: number
  total_available?: number
  sampled?: boolean
  positive_count: number
  negative_count: number
  tier: number
  model: string
  topic_count_mode?: TopicCountMode
  requested_k?: number | null
  effective_k?: number | null
  recommendation_confidence?: 'high' | 'medium' | 'low' | null
  recommendation_reason?: string | null
  recommendation_details?: Record<string, unknown> | null
}

interface TopicAnalysisProps {
  appId: number
  onAnalysisComplete: (result: AnalysisResult | null) => void
}

export function TopicAnalysis({ appId, onAnalysisComplete }: TopicAnalysisProps) {
  const api = useApi()
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState<ProgressData>({ stage: 'idle', percent: 0, message: '', elapsed_ms: 0 })
  const [error, setError] = useState<string | null>(null)
  const [expandedTopic, setExpandedTopic] = useState<string | null>(null)
  const [nTopics, setNTopics] = useState(8)
  const [topicCountMode, setTopicCountMode] = useState<TopicCountMode>('auto')
  const [analysisTier, setAnalysisTier] = useState(0)
  const [showRecommendationStage, setShowRecommendationStage] = useState(false)
  const [reviewLimit, setReviewLimit] = useState<'all' | number>('all')
  const [totalReviews, setTotalReviews] = useState(0)

  useEffect(() => {
    setResult(null)
    setError(null)
    setProgress({ stage: 'idle', percent: 0, message: '', elapsed_ms: 0 })
    onAnalysisComplete(null)
    api.getGameStats(appId).then((stats: any) => {
      setTotalReviews(stats.total_collected ?? 0)
    })
    // Load cached analysis result if available
    api.getCachedAnalysis(appId).then((cached: any) => {
      if (cached) {
        setResult(cached)
        onAnalysisComplete(cached)
      }
    })
  }, [appId])

  useEffect(() => {
    let disposed = false
    ;(async () => {
      try {
        const settings = (await api.getSettings()) as { tier?: 'auto' | '0' | '1' }
        if (settings?.tier === '1') {
          if (!disposed) {
            setAnalysisTier(1)
            setTopicCountMode('auto')
          }
          return
        }
        if (settings?.tier === '0') {
          if (!disposed) setAnalysisTier(0)
          return
        }
        const gpu = (await api.detectGpu()) as { recommended_tier?: number }
        const resolvedTier = Number(gpu?.recommended_tier ?? 0) >= 1 ? 1 : 0
        if (!disposed) {
          setAnalysisTier(resolvedTier)
          if (resolvedTier >= 1) setTopicCountMode('auto')
        }
      } catch {
        if (!disposed) setAnalysisTier(0)
      }
    })()
    return () => { disposed = true }
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
  const normalizedTopicCountMode: TopicCountMode = analysisTier >= 1 ? 'auto' : topicCountMode

  const runAnalysis = async () => {
    setLoading(true)
    setError(null)
    setShowRecommendationStage(analysisTier === 0 && normalizedTopicCountMode === 'auto')
    setProgress({ stage: 'idle', percent: 0, message: 'Starting analysis...', elapsed_ms: 0 })
    try {
      const config: Record<string, unknown> = { n_topics: nTopics, topicCountMode: normalizedTopicCountMode }
      if (reviewLimit !== 'all') {
        config.maxReviews = reviewLimit
      }
      const res = await api.runAnalysis(appId, config) as AnalysisResult
      setResult(res)
      onAnalysisComplete(res)
    } catch (e) {
      console.error(e)
      setError(e instanceof Error ? e.message : 'Analysis failed. Check the developer console for details.')
    } finally {
      setLoading(false)
      setShowRecommendationStage(false)
      setProgress({ stage: 'idle', percent: 0, message: '', elapsed_ms: 0 })
    }
  }

  const toggleTopic = (key: string) => {
    setExpandedTopic(expandedTopic === key ? null : key)
  }

  return (
    <div className="topic-analysis">
      <div className="analysis-controls">
        <TopicCountModeControl
          tier={analysisTier}
          mode={normalizedTopicCountMode}
          nTopics={nTopics}
          disabled={loading}
          onModeChange={setTopicCountMode}
          onNTopicsChange={setNTopics}
        />
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

      {loading && (
        <AnalysisProgress
          data={progress}
          showRecommendationStage={showRecommendationStage}
        />
      )}

      {result && (
        <div className="analysis-meta">
          <span>Model: {result.model}</span>
          <span>Tier: {result.tier}</span>
          <span>Mode: {(result.topic_count_mode ?? normalizedTopicCountMode).toUpperCase()}</span>
          <span>
            Effective topics:{' '}
            {result.tier >= 1
              ? 'Auto by HDBSCAN'
              : (result.effective_k ?? result.requested_k ?? nTopics)}
          </span>
          {result.recommendation_confidence && (
            <span>Confidence: {result.recommendation_confidence}</span>
          )}
          {result.recommendation_reason && (
            <span>Reason: {result.recommendation_reason}</span>
          )}
          <span>
            Reviews: {result.total_reviews.toLocaleString()}
            {result.sampled ? ` (sampled from ${result.total_available?.toLocaleString()})` : ''}
          </span>
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
