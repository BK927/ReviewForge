import { useState, useEffect } from 'react'
import { useApi } from '../hooks/useApi'
import { AnalysisProgress, ProgressData } from './AnalysisProgress'
import { estimateLocalAnalysisMinutes } from '../lib/analysis-timing'
import { TopicCountMode, TopicCountModeControl } from './TopicCountModeControl'
import { TopicTimeline } from './TopicTimeline'

export interface Topic {
  id: number
  label: string
  keywords: { word: string; score: number }[]
  review_count: number
  representative_review?: string
  sample_reviews: string[]
}

export interface TopicDistributionEntry {
  topic_id: number
  topic_label: string
  count: number
  proportion: number
}

export interface SegmentTopicData {
  segment_label: string
  total_reviews: number
  positive_rate: number
  positive_topic_distribution: TopicDistributionEntry[]
  negative_topic_distribution: TopicDistributionEntry[]
}

export interface TopicTimelinePeriod {
  period: string
  total_reviews: number
  positive_rate: number
  positive_topic_distribution: TopicDistributionEntry[]
  negative_topic_distribution: TopicDistributionEntry[]
}

export interface EarlyAccessLifecycleEntry {
  topic_id: number
  topic_label: string
  status: 'persistent' | 'resolved' | 'new'
  ea_proportion: number
  post_launch_proportion: number
  ea_positive_rate: number
  post_launch_positive_rate: number
}

export interface EarlyAccessComparisonData {
  ea_review_count: number
  post_launch_review_count: number
  lifecycle: EarlyAccessLifecycleEntry[]
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
  // New: separate k per group (replaces effective_k)
  positive_k?: number | null
  negative_k?: number | null
  positive_confidence?: 'high' | 'medium' | 'low' | null
  negative_confidence?: 'high' | 'medium' | 'low' | null
  positive_reason?: string | null
  negative_reason?: string | null
  recommendation_details?: Record<string, unknown> | null
  // New: short review summary
  short_review_summary?: {
    count: number
    positive_rate: number
    frequent_phrases: { phrase: string; count: number }[]
  }
  // New: merge info
  merge_info?: {
    positive: { original_topic_count: number; merged_topic_count: number; merges: unknown[] }
    negative: { original_topic_count: number; merged_topic_count: number; merges: unknown[] }
  }
  // Segment × topic cross-analysis
  segment_topic_cross?: {
    playtime: SegmentTopicData[]
    language: SegmentTopicData[]
    steam_deck: SegmentTopicData[]
    purchase_type: SegmentTopicData[]
  }
  // Topic timeline
  topics_over_time?: {
    weekly: TopicTimelinePeriod[]
    monthly: TopicTimelinePeriod[]
  }
  // Early access comparison
  early_access_comparison?: EarlyAccessComparisonData | null
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
  const [analysisTier, setAnalysisTier] = useState<number | null>(null)
  const [showRecommendationStage, setShowRecommendationStage] = useState(false)
  const [reviewLimit, setReviewLimit] = useState<'all' | number>('all')
  const [totalReviews, setTotalReviews] = useState(0)

  useEffect(() => {
    setResult(null)
    setError(null)
    setProgress({ stage: 'idle', percent: 0, message: '', elapsed_ms: 0 })
    setAnalysisTier(null)
    setTopicCountMode('auto')
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
  const normalizedTopicCountMode: TopicCountMode = analysisTier !== null && analysisTier >= 1 ? 'auto' : topicCountMode

  const runAnalysis = async () => {
    if (analysisTier === null) return

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
        <button onClick={runAnalysis} disabled={loading || analysisTier === null}>
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
          {result.tier >= 1 ? (
            <span>Topics: Auto by HDBSCAN</span>
          ) : result.topic_count_mode === 'auto' ? (
            <>
              {result.positive_k != null && (
                <span>
                  Positive topics: {result.positive_k}
                  {result.positive_confidence && (
                    <> ({result.positive_confidence})</>
                  )}
                </span>
              )}
              {result.negative_k != null && (
                <span>
                  Negative topics: {result.negative_k}
                  {result.negative_confidence && (
                    <> ({result.negative_confidence})</>
                  )}
                </span>
              )}
            </>
          ) : (
            <span>Topics: {result.requested_k ?? nTopics}</span>
          )}
          <span>
            Reviews: {result.total_reviews.toLocaleString()}
            {result.sampled ? ` (sampled from ${result.total_available?.toLocaleString()})` : ''}
          </span>
        </div>
      )}

      {result && result.short_review_summary && result.short_review_summary.count > 0 && (
        <div className="short-review-summary">
          <h4>Short Reviews ({result.short_review_summary.count} filtered)</h4>
          <p>Positive rate: {(result.short_review_summary.positive_rate * 100).toFixed(1)}%</p>
          {result.short_review_summary.frequent_phrases.length > 0 && (
            <div className="frequent-phrases">
              {result.short_review_summary.frequent_phrases.map((fp, i) => (
                <span key={i} className="phrase-tag">
                  {fp.phrase} ({fp.count})
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {result && (
        <>
          {result.topics_over_time && (result.topics_over_time.weekly.length > 0 || result.topics_over_time.monthly.length > 0) && (
            <TopicTimeline analysisResult={result} />
          )}
          <div className="topics-grid">
            <div className="topic-column">
              <h3>Negative Topics ({result.negative_count} reviews)</h3>
              {result.merge_info?.negative && result.merge_info.negative.merges.length > 0 && (
                <p className="merge-info">
                  {result.merge_info.negative.original_topic_count} topics merged to {result.merge_info.negative.merged_topic_count}
                </p>
              )}
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
              {result.merge_info?.positive && result.merge_info.positive.merges.length > 0 && (
                <p className="merge-info">
                  {result.merge_info.positive.original_topic_count} topics merged to {result.merge_info.positive.merged_topic_count}
                </p>
              )}
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
        </>
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
      {topic.representative_review && (
        <div className="representative-review">
          <span className="representative-label">Representative:</span>
          <p className="representative-text">{topic.representative_review}</p>
        </div>
      )}
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
