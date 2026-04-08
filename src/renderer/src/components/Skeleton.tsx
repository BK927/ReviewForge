export function SkeletonText({ width }: { width?: 'short' | 'medium' | 'long' | string }) {
  const isPreset = width === 'short' || width === 'medium' || width === 'long'
  return (
    <div
      className={`skeleton skeleton-text${isPreset ? ` ${width}` : ''}`}
      style={!isPreset && width ? { width } : undefined}
    />
  )
}

export function SkeletonCircle({ size = 50 }: { size?: number }) {
  return <div className="skeleton skeleton-circle" style={{ width: size, height: size }} />
}

export function SkeletonChart() {
  return <div className="skeleton skeleton-chart" />
}

export function DashboardSkeleton() {
  return (
    <div className="dashboard">
      <div className="skeleton-card" style={{ marginBottom: 16 }}>
        <SkeletonText width="medium" />
        <SkeletonText width="short" />
        <div style={{ display: 'flex', gap: 20, marginTop: 12 }}>
          <SkeletonText width="120px" />
          <SkeletonText width="100px" />
          <SkeletonText width="140px" />
        </div>
      </div>
      <div className="charts-grid">
        <div className="skeleton-card"><SkeletonText width="short" /><SkeletonChart /></div>
        <div className="skeleton-card"><SkeletonText width="short" /><SkeletonChart /></div>
        <div className="skeleton-card"><SkeletonText width="short" /><SkeletonChart /></div>
      </div>
    </div>
  )
}

export function TopicsSkeleton() {
  return (
    <div className="topic-analysis">
      <div className="skeleton-card" style={{ marginBottom: 16, display: 'flex', gap: 16, alignItems: 'center' }}>
        <SkeletonText width="120px" />
        <SkeletonText width="100px" />
      </div>
      <div className="topics-grid">
        <div>
          <SkeletonText width="medium" />
          {[1, 2, 3].map(i => (
            <div key={i} className="skeleton-card" style={{ marginBottom: 8 }}>
              <SkeletonText width="long" />
              <SkeletonText width="medium" />
            </div>
          ))}
        </div>
        <div>
          <SkeletonText width="medium" />
          {[1, 2, 3].map(i => (
            <div key={i} className="skeleton-card" style={{ marginBottom: 8 }}>
              <SkeletonText width="long" />
              <SkeletonText width="medium" />
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export function SegmentsSkeleton() {
  return (
    <div className="segment-analysis">
      <div className="skeleton-card" style={{ marginBottom: 16, display: 'flex', gap: 16 }}>
        <SkeletonText width="100px" />
        <SkeletonText width="80px" />
        <SkeletonText width="80px" />
        <SkeletonText width="80px" />
      </div>
      <div className="charts-grid">
        <div className="skeleton-card"><SkeletonText width="short" /><SkeletonChart /></div>
        <div className="skeleton-card"><SkeletonText width="short" /><SkeletonChart /></div>
        <div className="skeleton-card"><SkeletonText width="short" /><SkeletonChart /></div>
      </div>
    </div>
  )
}
