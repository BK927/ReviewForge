import { useState } from 'react'
import { GameSidebar } from './GameSidebar'
import { CompareView } from './CompareView'
import { SettingsDialog } from './SettingsDialog'

interface Props {
  children: (appId: number | null, activeTab: string) => React.ReactNode
}

const TABS = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'topics', label: 'Topics' },
  { id: 'segments', label: 'Segments' },
  { id: 'export', label: 'Export' }
]

export function Layout({ children }: Props) {
  const [selectedAppId, setSelectedAppId] = useState<number | null>(null)
  const [activeTab, setActiveTab] = useState('dashboard')
  const [compareMode, setCompareMode] = useState(false)
  const [compareIds, setCompareIds] = useState<number[]>([])
  const [showSettings, setShowSettings] = useState(false)

  const handleToggleCompare = (appId: number) => {
    setCompareIds(prev => {
      if (prev.includes(appId)) return prev.filter(id => id !== appId)
      if (prev.length >= 2) return [prev[1], appId]
      return [...prev, appId]
    })
  }

  const exitCompare = () => {
    setCompareMode(false)
    setCompareIds([])
  }

  return (
    <div className="app-layout">
      <GameSidebar
        selectedAppId={selectedAppId}
        onSelectGame={setSelectedAppId}
        compareMode={compareMode}
        compareIds={compareIds}
        onToggleCompare={handleToggleCompare}
      />
      <main className="main-content">
        <nav className="tab-nav">
          {TABS.map(tab => (
            <button
              key={tab.id}
              className={activeTab === tab.id && !compareMode ? 'active' : ''}
              onClick={() => { setActiveTab(tab.id); setCompareMode(false) }}
            >
              {tab.label}
            </button>
          ))}
          <div className="nav-spacer" />
          <button
            className={compareMode ? 'active compare-btn' : 'compare-btn'}
            onClick={() => compareMode ? exitCompare() : setCompareMode(true)}
          >
            {compareMode ? 'Exit Compare' : 'Compare'}
          </button>
          <button className="settings-btn" onClick={() => setShowSettings(true)}>⚙</button>
        </nav>

        <div className="tab-content">
          {compareMode && compareIds.length === 2 ? (
            <CompareView appIds={compareIds as [number, number]} />
          ) : compareMode ? (
            <div className="empty-state">Select 2 games from the sidebar to compare</div>
          ) : (
            children(selectedAppId, activeTab)
          )}
        </div>
      </main>

      <SettingsDialog open={showSettings} onClose={() => setShowSettings(false)} />
    </div>
  )
}
