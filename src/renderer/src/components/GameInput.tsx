import { useRef, useState } from 'react'
import { useApi } from '../hooks/useApi'

interface Props {
  onGameAdded: () => void
}

export function GameInput({ onGameAdded }: Props) {
  const api = useApi()
  const inputRef = useRef<HTMLInputElement>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async () => {
    const value = inputRef.current?.value.trim() ?? ''
    if (!value) return
    setLoading(true)
    setError(null)
    try {
      await api.addGame(value)
      if (inputRef.current) inputRef.current.value = ''
      onGameAdded()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to add game')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="game-input">
      <input
        ref={inputRef}
        type="text"
        defaultValue=""
        onKeyDown={e => e.key === 'Enter' && handleSubmit()}
        placeholder="App ID or Steam Store URL"
        disabled={loading}
      />
      <button onClick={handleSubmit} disabled={loading}>
        {loading ? 'Adding...' : 'Add Game'}
      </button>
      {error && <div className="error">{error}</div>}
    </div>
  )
}
