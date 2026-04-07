import { useState } from 'react'
import { useApi } from '../hooks/useApi'

interface Props {
  onGameAdded: () => void
}

export function GameInput({ onGameAdded }: Props) {
  const api = useApi()
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async () => {
    if (!input.trim()) return
    setLoading(true)
    setError(null)
    try {
      await api.addGame(input.trim())
      setInput('')
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
        type="text"
        value={input}
        onChange={e => setInput(e.target.value)}
        onKeyDown={e => e.key === 'Enter' && handleSubmit()}
        placeholder="App ID or Steam Store URL"
        disabled={loading}
      />
      <button onClick={handleSubmit} disabled={loading || !input.trim()}>
        {loading ? 'Adding...' : 'Add Game'}
      </button>
      {error && <div className="error">{error}</div>}
    </div>
  )
}
