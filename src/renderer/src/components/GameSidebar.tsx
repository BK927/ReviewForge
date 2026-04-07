import { useEffect, useState } from 'react'
import { useApi } from '../hooks/useApi'
import { GameInput } from './GameInput'

interface Game {
  app_id: number
  app_name: string
  review_score_desc: string
  total_reviews: number
}

interface Props {
  selectedAppId: number | null
  onSelectGame: (appId: number) => void
  compareMode?: boolean
  compareIds?: number[]
  onToggleCompare?: (appId: number) => void
}

export function GameSidebar({ selectedAppId, onSelectGame, compareMode, compareIds, onToggleCompare }: Props) {
  const api = useApi()
  const [games, setGames] = useState<Game[]>([])

  const loadGames = async () => {
    const list = await api.getGames() as Game[]
    setGames(list)
  }

  useEffect(() => { loadGames() }, [])

  const handleDelete = async (appId: number) => {
    await api.deleteGame(appId)
    loadGames()
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h1 className="app-title">ReviewForge</h1>
      </div>
      <GameInput onGameAdded={loadGames} />
      <ul className="game-list">
        {games.map(game => (
          <li
            key={game.app_id}
            className={[
              selectedAppId === game.app_id ? 'active' : '',
              compareMode && compareIds?.includes(game.app_id) ? 'compare-selected' : ''
            ].join(' ')}
            onClick={() => {
              if (compareMode && onToggleCompare) {
                onToggleCompare(game.app_id)
              } else {
                onSelectGame(game.app_id)
              }
            }}
          >
            {compareMode && (
              <input
                type="checkbox"
                checked={compareIds?.includes(game.app_id) ?? false}
                readOnly
              />
            )}
            <div className="game-info">
              <span className="game-name">{game.app_name}</span>
              <span className="game-score">{game.review_score_desc}</span>
            </div>
            <button
              className="delete-btn"
              onClick={e => { e.stopPropagation(); handleDelete(game.app_id) }}
              title="Remove game"
            >
              ×
            </button>
          </li>
        ))}
      </ul>
    </aside>
  )
}
