import { useState, useEffect, useRef, useCallback } from 'react'
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
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const tabRefs = useRef<Map<string, HTMLButtonElement>>(new Map())
  const [indicatorStyle, setIndicatorStyle] = useState({ left: 0, width: 0 })

  // Auto-collapse/expand sidebar based on window width
  useEffect(() => {
    const handleResize = () => {
      setSidebarCollapsed(window.innerWidth < 800)
    }
    // Delay initial check to let Electron window settle
    const timer = setTimeout(handleResize, 200)
    window.addEventListener('resize', handleResize)
    return () => {
      clearTimeout(timer)
      window.removeEventListener('resize', handleResize)
    }
  }, [])

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

  const updateIndicator = useCallback(() => {
    const currentId = compareMode ? '__compare__' : activeTab
    const el = tabRefs.current.get(currentId)
    if (el) {
      setIndicatorStyle({ left: el.offsetLeft, width: el.offsetWidth })
    }
  }, [activeTab, compareMode])

  useEffect(() => {
    updateIndicator()
  }, [updateIndicator])

  useEffect(() => {
    window.addEventListener('resize', updateIndicator)
    return () => window.removeEventListener('resize', updateIndicator)
  }, [updateIndicator])

  return (
    <div className="app-layout">
      <GameSidebar
        selectedAppId={selectedAppId}
        onSelectGame={setSelectedAppId}
        compareMode={compareMode}
        compareIds={compareIds}
        onToggleCompare={handleToggleCompare}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(prev => !prev)}
      />
      <main className="main-content">
        <nav className="tab-nav">
          {TABS.map(tab => (
            <button
              key={tab.id}
              ref={el => { if (el) tabRefs.current.set(tab.id, el) }}
              className={activeTab === tab.id && !compareMode ? 'active' : ''}
              onClick={() => { setActiveTab(tab.id); setCompareMode(false) }}
            >
              {tab.label}
            </button>
          ))}
          <div className="nav-spacer" />
          <button
            ref={el => { if (el) tabRefs.current.set('__compare__', el) }}
            className={compareMode ? 'active compare-btn' : 'compare-btn'}
            onClick={() => compareMode ? exitCompare() : setCompareMode(true)}
          >
            {compareMode ? 'Exit Compare' : 'Compare'}
          </button>
          <button className="settings-btn" onClick={() => setShowSettings(true)}>⚙</button>
          <div className="tab-indicator" style={{ left: indicatorStyle.left, width: indicatorStyle.width }} />
        </nav>

        <div className="tab-content">
          <div className="tab-content-inner" key={compareMode ? 'compare' : activeTab}>
            {compareMode && compareIds.length === 2 ? (
              <CompareView appIds={compareIds as [number, number]} />
            ) : compareMode ? (
              <div className="empty-state">Select 2 games from the sidebar to compare</div>
            ) : (
              children(selectedAppId, activeTab)
            )}
          </div>
        </div>
      </main>

      <SettingsDialog open={showSettings} onClose={() => setShowSettings(false)} />
    </div>
  )
}
