export type TopicCountMode = 'auto' | 'manual'

interface TopicCountModeControlProps {
  tier: number
  mode: TopicCountMode
  nTopics: number
  disabled?: boolean
  onModeChange: (mode: TopicCountMode) => void
  onNTopicsChange: (value: number) => void
}

export function TopicCountModeControl({
  tier,
  mode,
  nTopics,
  disabled = false,
  onModeChange,
  onNTopicsChange
}: TopicCountModeControlProps) {
  if (tier >= 1) {
    return (
      <div className="topic-count-mode-control locked">
        <span className="topic-count-mode-label">Topic count mode:</span>
        <span className="topic-count-mode-locked">Auto by HDBSCAN</span>
      </div>
    )
  }

  return (
    <div className="topic-count-mode-control">
      <span className="topic-count-mode-label">Topic count mode:</span>
      <label className="topic-count-mode-option">
        <input
          type="radio"
          name="topic-count-mode"
          value="auto"
          checked={mode === 'auto'}
          disabled={disabled}
          onChange={() => onModeChange('auto')}
        />
        Auto (recommended)
      </label>
      <label className="topic-count-mode-option">
        <input
          type="radio"
          name="topic-count-mode"
          value="manual"
          checked={mode === 'manual'}
          disabled={disabled}
          onChange={() => onModeChange('manual')}
        />
        Manual
      </label>
      <input
        type="number"
        value={nTopics}
        min={2}
        max={20}
        disabled={disabled || mode !== 'manual'}
        onChange={e => onNTopicsChange(Number(e.target.value))}
      />
    </div>
  )
}
