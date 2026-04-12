import type { AnalysisResult } from './TopicAnalysis'

const STATUS_CONFIG = {
  persistent: { label: 'Persistent', color: '#ef4444', bg: '#fef2f2' },
  resolved: { label: 'Resolved', color: '#22c55e', bg: '#f0fdf4' },
  new: { label: 'New', color: '#eab308', bg: '#fefce8' },
} as const

export function EarlyAccessComparison({ analysisResult }: { analysisResult: AnalysisResult }) {
  const data = analysisResult.early_access_comparison
  if (!data) return null

  return (
    <div className="early-access-comparison">
      <h3>Early Access vs Post-Launch</h3>
      <div className="ea-summary" style={{ display: 'flex', gap: '1.5rem', marginBottom: '1rem', fontSize: '0.9rem', opacity: 0.8 }}>
        <span>EA Reviews: {data.ea_review_count.toLocaleString()}</span>
        <span>Post-Launch Reviews: {data.post_launch_review_count.toLocaleString()}</span>
      </div>
      <div className="lifecycle-list" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        {data.lifecycle.map(entry => {
          const config = STATUS_CONFIG[entry.status]
          const maxProp = Math.max(entry.ea_proportion, entry.post_launch_proportion, 0.01)
          return (
            <div
              key={entry.topic_id}
              className="lifecycle-card"
              style={{
                borderLeft: `4px solid ${config.color}`,
                backgroundColor: config.bg,
                padding: '0.75rem 1rem',
                borderRadius: '4px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                <span style={{ fontWeight: 600 }}>{entry.topic_label}</span>
                <span style={{ color: config.color, fontWeight: 600, fontSize: '0.85rem' }}>{config.label}</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span style={{ width: '3rem', fontSize: '0.8rem', textAlign: 'right' }}>EA</span>
                  <div style={{ flex: 1, height: '12px', backgroundColor: '#e5e7eb', borderRadius: '6px', overflow: 'hidden' }}>
                    <div style={{ width: `${(entry.ea_proportion / maxProp) * 100}%`, height: '100%', backgroundColor: config.color, borderRadius: '6px' }} />
                  </div>
                  <span style={{ width: '3.5rem', fontSize: '0.8rem' }}>{(entry.ea_proportion * 100).toFixed(1)}%</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span style={{ width: '3rem', fontSize: '0.8rem', textAlign: 'right' }}>Post</span>
                  <div style={{ flex: 1, height: '12px', backgroundColor: '#e5e7eb', borderRadius: '6px', overflow: 'hidden' }}>
                    <div style={{ width: `${(entry.post_launch_proportion / maxProp) * 100}%`, height: '100%', backgroundColor: config.color, opacity: 0.6, borderRadius: '6px' }} />
                  </div>
                  <span style={{ width: '3.5rem', fontSize: '0.8rem' }}>{(entry.post_launch_proportion * 100).toFixed(1)}%</span>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
