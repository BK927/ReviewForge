const STAGES = ['embedding', 'clustering', 'keywords'] as const
type Stage = typeof STAGES[number]

const STAGE_LABELS: Record<Stage, string> = {
  embedding: 'Embedding',
  clustering: 'Clustering',
  keywords: 'Keywords'
}

export interface ProgressData {
  stage: 'idle' | Stage | 'complete'
  percent: number
  message: string
  elapsed_ms: number
}

function getStageState(stage: Stage, current: ProgressData['stage']): 'pending' | 'active' | 'completed' {
  if (current === 'complete') return 'completed'
  const currentIdx = STAGES.indexOf(current as Stage)
  const stageIdx = STAGES.indexOf(stage)
  if (currentIdx < 0) return 'pending'
  if (stageIdx < currentIdx) return 'completed'
  if (stageIdx === currentIdx) return 'active'
  return 'pending'
}

function parseEmbeddingCounts(message: string): { processed: number; total: number } | null {
  const match = message.match(/Embedded (\d[\d,]*)\s*\/\s*(\d[\d,]*)/)
  if (!match) return null
  return {
    processed: parseInt(match[1].replace(/,/g, ''), 10),
    total: parseInt(match[2].replace(/,/g, ''), 10)
  }
}

function computeEta(elapsed_ms: number, processed: number, total: number): string | null {
  // Skip first 3 batches (192 reviews at batch_size=64) for warmup
  if (processed < 192 || elapsed_ms <= 0) return null
  const remaining = total - processed
  if (remaining <= 0) return null
  const etaMs = (elapsed_ms / processed) * remaining
  if (etaMs < 5000) return 'Almost done...'
  const etaSec = Math.round(etaMs / 1000)
  if (etaSec >= 60) {
    const min = Math.floor(etaSec / 60)
    const sec = etaSec % 60
    return `ETA ${min}m ${sec}s`
  }
  return `ETA ${etaSec}s`
}

export function AnalysisProgress({ data }: { data: ProgressData }) {
  const counts = data.stage === 'embedding' ? parseEmbeddingCounts(data.message) : null
  const eta = counts ? computeEta(data.elapsed_ms, counts.processed, counts.total) : null

  return (
    <div className="analysis-progress">
      <div className="progress-steps">
        {STAGES.map((stage, i) => {
          const state = getStageState(stage, data.stage)
          return (
            <div key={stage} className={`progress-step ${state}`}>
              <span className="step-icon">
                {state === 'completed' ? '\u2713' : state === 'active' ? '\u25CF' : '\u25CB'}
              </span>
              <span className="step-label">{STAGE_LABELS[stage]}</span>
              {i < STAGES.length - 1 && <span className="step-arrow">\u2192</span>}
            </div>
          )
        })}
      </div>

      {data.stage === 'embedding' && counts && (
        <>
          <div className="progress-bar-track">
            <div
              className="progress-bar-fill"
              style={{ width: `${Math.min(data.percent, 100)}%` }}
            />
          </div>
          <div className="progress-detail">
            <span>Embedded {counts.processed.toLocaleString()} / {counts.total.toLocaleString()} reviews</span>
            {eta && <span className="progress-eta">{eta}</span>}
          </div>
        </>
      )}

      {data.stage === 'idle' && data.message && (
        <div className="progress-detail">
          <span className="progress-spinner" />
          <span>{data.message}</span>
        </div>
      )}

      {(data.stage === 'clustering' || data.stage === 'keywords') && (
        <div className="progress-detail">
          <span className="progress-spinner" />
          <span>{data.message}</span>
        </div>
      )}
    </div>
  )
}
