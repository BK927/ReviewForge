import { useEffect, useState } from 'react'
import { useApi } from '../hooks/useApi'

interface HelpfulReview {
  recommendation_id: string
  review_text: string
  voted_up: number
  votes_up: number
  playtime_at_review: number
}

export function HelpfulReviews({ appId }: { appId: number }) {
  const api = useApi()
  const [positive, setPositive] = useState<HelpfulReview[]>([])
  const [negative, setNegative] = useState<HelpfulReview[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    Promise.all([
      api.getTopHelpful(appId, true, 5) as Promise<HelpfulReview[]>,
      api.getTopHelpful(appId, false, 5) as Promise<HelpfulReview[]>,
    ]).then(([pos, neg]) => {
      setPositive(pos)
      setNegative(neg)
    }).catch(err => {
      console.error('Failed to load helpful reviews:', err)
    }).finally(() => {
      setLoading(false)
    })
  }, [appId])

  if (loading) return <div className="helpful-reviews-loading">Loading helpful reviews...</div>
  if (positive.length === 0 && negative.length === 0) return null

  return (
    <div className="helpful-reviews">
      <h3>Community Top Reviews</h3>
      <div className="helpful-grid">
        <div className="helpful-column">
          <h4 className="helpful-positive-header">Most Helpful Positive</h4>
          {positive.map(r => (
            <div key={r.recommendation_id} className="helpful-card positive">
              <div className="helpful-meta">
                <span>{Math.round(r.playtime_at_review / 60)}h played</span>
                <span>{r.votes_up} helpful</span>
              </div>
              <p className="helpful-text">{r.review_text}</p>
            </div>
          ))}
        </div>
        <div className="helpful-column">
          <h4 className="helpful-negative-header">Most Helpful Negative</h4>
          {negative.map(r => (
            <div key={r.recommendation_id} className="helpful-card negative">
              <div className="helpful-meta">
                <span>{Math.round(r.playtime_at_review / 60)}h played</span>
                <span>{r.votes_up} helpful</span>
              </div>
              <p className="helpful-text">{r.review_text}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
