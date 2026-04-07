import { useState, useEffect } from 'react'
import { useApi } from '../hooks/useApi'

interface Props {
  appId: number
  onComplete: () => void
}

export function CollectionProgress({ appId, onComplete }: Props) {
  const api = useApi()
  const [progress, setProgress] = useState({ fetched: 0, total: 0 })
  const [collecting, setCollecting] = useState(false)

  useEffect(() => {
    const cleanup = api.onProgress((data: any) => {
      if (data.type === 'fetch' && data.appId === appId) {
        setProgress({ fetched: data.fetched, total: data.total })
      }
    })
    return () => { cleanup() }
  }, [appId])

  const startFetch = async () => {
    setCollecting(true)
    try {
      await api.fetchReviews(appId)
      onComplete()
    } finally {
      setCollecting(false)
      setProgress({ fetched: 0, total: 0 })
    }
  }

  const percent = progress.total > 0 ? Math.round(progress.fetched / progress.total * 100) : 0

  return (
    <div className="collection-progress">
      <button onClick={startFetch} disabled={collecting}>
        {collecting ? `Collecting... ${progress.fetched}/${progress.total} (${percent}%)` : 'Fetch Reviews'}
      </button>
      {collecting && (
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${percent}%` }} />
        </div>
      )}
    </div>
  )
}
